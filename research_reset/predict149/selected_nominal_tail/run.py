#!/usr/bin/env python3
"""T149-M: chronological selected-name nominal loss and joint basket risk forecasts.

Original F3/H1 Top5 and 149 universe frozen. Every learned signal is refitted
on ONLY earlier fully matured blocks (one-block embargo). Research on a
repeatedly mined survivor cohort, NOT independently validated investment data.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from oasis149.canonical import sha, SRC
from research_reset.predict149.complementarity.run import (
    from_archive, monthly_weights, trade_policy, metrics, K
)

ROOT = Path(__file__).resolve().parents[3]
PREVIOUS = ROOT / "research_reset/predict149/complementarity/results"
SEED = 20261019
MIN_TICKER_TRAIN = 16
MIN_PORT_TRAIN = 20
BASKET_FEATURES = ("port_21vol", "mean_corr63", "port_mom63",
                   "market_mom63", "market_vol63", "port_downvol63")
TICKER_FEATURES = ("v21", "downvol63", "mom21", "mom63",
                   "corr_basket", "f3_rank", "h1_rank", "basket_vol63")
VOL_FEATURES = ("v21",)
POLICIES = ("STATIC_F3_H1_50", "M_TAIL_WITHIN", "VOL_ONLY_WITHIN")
METHODS = ("M_TAIL", "VOL_ONLY")
TARGETS = ("loss5", "intra8")


def eligible_matured(rows, signal):
    """Strict as-of: the block closing at this morning's Open is embargoed."""
    z = rows[pd.to_datetime(rows.maturity) < pd.Timestamp(signal)]
    assert len(z) == 0 or pd.to_datetime(z.maturity).max() < pd.Timestamp(signal)
    return z


def fit_binary(train, features, target):
    """Strong regularization; no after-result learner/parameter search."""
    if len(train) < 20 or min(int(train[target].sum()),
                             int(len(train) - train[target].sum())) < 6:
        return None
    m = make_pipeline(StandardScaler(),
        LogisticRegression(C=.05, max_iter=300, solver="liblinear",
                           random_state=SEED))
    # Each historical investment date receives comparable total weight.
    if "ticker" in train:
        sizes = train.groupby("block").ticker.transform("count").to_numpy()
        weights = len(train) / train.block.nunique() / sizes
    else:
        weights = np.ones(len(train))
    m.fit(train[list(features)].to_numpy(float), train[target].to_numpy(int),
          logisticregression__sample_weight=weights)
    return m


def held_weights(f, h, probabilities=None):
    """Frozen 50/50 expert budgets and exact same union of chosen names."""
    if probabilities is None:
        return monthly_weights([("F3", .5, f), ("H1", .5, h)])
    result = {}
    for selected in (f, h):
        p = np.array([probabilities[t] for t in selected], float)
        assert np.isfinite(p).all() and np.all((p >= 0) & (p <= 1))
        tilt = np.clip((.10 + p.mean()) / (.10 + p), .70, 1.30)
        tilt /= tilt.sum()
        for t, weight in zip(selected, tilt):
            result[t] = result.get(t, 0.) + .5 * float(weight)
    assert abs(sum(result.values()) - 1.) < 1e-11
    assert set(result) == set(f + h)
    return result


def future_nominal(prices, index, tickers, weight):
    """Next-entry-Open to next 21-session Open: not a close-to-close label."""
    p = prices.loc[index, tickers].to_numpy(float)
    assert p.shape == (K + 1, len(tickers))
    assert np.isfinite(p).all() and np.all(p > 0)
    path = (p / p[0]) @ np.asarray(weight, float)
    return (p[-1] / p[0] - 1.), float(path[-1] - 1.), float(path.min() - 1.)


def historical_block(p, roster, closes, opens, days, signals, b, f, h):
    """Freeze features using completed signal Close; future opens only for labels."""
    k = b * K
    signal = pd.Timestamp(signals[k])
    chosen = sorted(set(f + h))
    base = held_weights(f, h)
    w = np.array([base[t] for t in chosen])
    original = p.loc[p.block == b].set_index("ticker")
    assert len(original) == 149
    tail = closes.loc[:signal, chosen + ["SPY"]].dropna().tail(128)
    assert len(tail) == 128 and tail.index[-1] == signal
    logs = np.log(tail)
    d = logs.diff().dropna()
    ret = d[chosen].tail(63).to_numpy(float)
    market = d.SPY.tail(63).to_numpy(float)
    cov = np.cov(ret, rowvar=False)
    assert cov.shape == (len(chosen), len(chosen))
    # 50% diagonal shrinkage is frozen; correlated picks cannot be counted
    # as independent. All estimators use past Close data ONLY.
    shrunk = .5 * cov + .5 * np.diag(np.diag(cov))
    portvol = float(np.sqrt(max(1e-14, w @ shrunk @ w)))
    gross63 = ret @ w
    corr = np.corrcoef(ret, rowvar=False)
    if not np.isfinite(corr).all():
        raise AssertionError("Missing/constant historical returns")
    pair = corr[np.triu_indices(len(chosen), 1)]
    features = dict(
        port_21vol=portvol * np.sqrt(21.),
        mean_corr63=float(pair.mean()),
        port_mom63=float(np.dot(w, logs[chosen].iloc[-1] -
                                      logs[chosen].iloc[-64])),
        market_mom63=float(logs.SPY.iloc[-1] - logs.SPY.iloc[-64]),
        market_vol63=float(np.std(market, ddof=1) * np.sqrt(21.)),
        port_downvol63=float(np.sqrt(np.mean(np.minimum(gross63, 0)**2))*np.sqrt(21.)))
    forecasts = original[["B0_F3_FROZEN", "H1_FACTOR_ONLY"]].rank(pct=True)
    diag = np.sqrt(np.diag(cov))
    basket_correlation = np.array([
        np.mean(np.delete(corr[i], i)) for i in range(len(chosen))])
    priceindex = days[k:k+K+1]
    rawret, basketreturn, basketmin = future_nominal(
        opens, priceindex, chosen, w)
    maturity = str(pd.Timestamp(days[k+K]).date())
    row = dict(block=b, signal=str(signal.date()), maturity=maturity,
               **features, future_return=basketreturn,
               future_min_from_entry=basketmin,
               loss5=int(basketreturn < -.05),
               intra8=int(basketmin < -.08),
               gaussian_p_loss5=float(norm.cdf(-.05/max(1e-8, features["port_21vol"]))),
               gaussian_p_intra8=float(min(1, 2*norm.cdf(
                   -.08/max(1e-8, features["port_21vol"])))))
    positions = []
    for j, t in enumerate(chosen):
        sample = ret[:, j]
        moment = logs[t]
        positions.append(dict(
            block=b, ticker=t, signal=str(signal.date()), maturity=maturity,
            in_f3=int(t in f), in_h1=int(t in h),
            frozen_weight=base[t],
            v21=float(sample[-21:].std(ddof=1)*np.sqrt(21)),
            downvol63=float(np.sqrt(np.mean(np.minimum(sample,0)**2))*np.sqrt(21)),
            mom21=float(moment.iloc[-1]-moment.iloc[-22]),
            mom63=float(moment.iloc[-1]-moment.iloc[-64]),
            corr_basket=float(basket_correlation[j]),
            f3_rank=float(forecasts.loc[t, "B0_F3_FROZEN"]),
            h1_rank=float(forecasts.loc[t, "H1_FACTOR_ONLY"]),
            basket_vol63=float(features["port_21vol"]),
            realized_21d_nominal_return=float(rawret[j]),
            loss5=int(rawret[j] < -.05)))
    return row, positions


def ci_month(gains, seed, n=2500):
    arr = np.asarray(gains, float)
    assert len(arr) > 20 and np.isfinite(arr).all()
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n):
        ids = []
        while len(ids) < len(arr):
            j = int(rng.integers(len(arr)))
            ids.extend((j+s) % len(arr) for s in range(3))
        draws.append(float(arr[np.asarray(ids[:len(arr)], int)].mean()))
    return dict(mean=float(arr.mean()), ci95=np.quantile(draws, [.025,.975]).tolist())


def brier(y, p):
    return (np.asarray(y,float)-np.asarray(p,float))**2


def evaluate(outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=False)
    original, old, roster, O, C, days, signals, ids, selected = from_archive()
    assert len(ids) == 64 and ids == list(range(48,112))
    ticker_blocks = []
    basket_blocks = []
    for b in ids:
        k = ids.index(b)
        row, pos = historical_block(original, roster, C, O, days, signals,
                                    b, selected["F3"][k], selected["H1"][k])
        ticker_blocks.extend(pos)
        basket_blocks.append(row)
    tickers = pd.DataFrame(ticker_blocks)
    baskets = pd.DataFrame(basket_blocks)
    assert len(baskets) == 64
    assert len(tickers) >= 64*5 and len(tickers) <= 64*10
    assert tickers[["block","ticker"]].duplicated().sum() == 0
    assert all(pd.Timestamp(q.maturity) > pd.Timestamp(q.signal)
               for q in baskets.itertuples())
    for c in TICKER_FEATURES:
        assert np.isfinite(tickers[c]).all()
    for c in BASKET_FEATURES:
        assert np.isfinite(baskets[c]).all()

    scores = []
    portfolios = []
    weightpaths = {x: [] for x in POLICIES}
    positions = []
    for i, b in enumerate(ids):
        sig = baskets.loc[baskets.block==b, "signal"].iloc[0]
        tr_t = eligible_matured(tickers, sig)
        tr_b = eligible_matured(baskets, sig)
        # Historical selected constituents strictly precede the signal.
        assert set(tr_t.block) == set(tr_b.block)
        assert list(sorted(tr_b.block)) == ids[:max(0, i-1)]
        f, h = selected["F3"][i], selected["H1"][i]
        now = tickers[tickers.block==b].copy()
        present = baskets[baskets.block==b].copy()
        assert len(present) == 1
        stat = dict(block=b, signal=sig, maturity=present.maturity.iloc[0],
                    trained_ticker_blocks=len(tr_b), trained_basket_blocks=len(tr_b))
        current_baseline = held_weights(f,h)
        pmodels = {}
        if len(tr_b) >= MIN_TICKER_TRAIN:
            for method, features in (
                ("M_TAIL", TICKER_FEATURES), ("VOL_ONLY", VOL_FEATURES)):
                model = fit_binary(tr_t, features, "loss5")
                prior = float(tr_t.loss5.mean())
                pmodels[method] = (
                    model.predict_proba(now[list(features)].to_numpy(float))[:,1]
                    if model is not None else np.full(len(now),prior))
        else:
            pmodels = {method: np.full(len(now), np.nan) for method in METHODS}
        for method in METHODS:
            now["p_"+method] = pmodels[method]
        now["p_prior"] = float(tr_t.loss5.mean()) if len(tr_t) else np.nan
        for policy in POLICIES:
            if policy == "STATIC_F3_H1_50" or len(tr_b) < MIN_TICKER_TRAIN:
                w = current_baseline
            else:
                method = "M_TAIL" if policy=="M_TAIL_WITHIN" else "VOL_ONLY"
                by_name = dict(zip(now.ticker, now["p_"+method]))
                w = held_weights(f, h, by_name)
            assert set(w) == set(current_baseline) and abs(sum(w.values())-1)<1e-12
            weightpaths[policy].append(w)
            for t in w:
                if policy == "STATIC_F3_H1_50":
                    positions.append(dict(block=b,ticker=t,signal=sig,
                                          base_weight=w[t]))
        scores.append(now)

        # Risk of the fully invested fixed 50/50 portfolio is forecast
        # separately from any selected constituent's conditional loss.
        r = present.iloc[0]
        prior_pred = {}
        for target in TARGETS:
            pr = float(tr_b[target].mean()) if len(tr_b) else np.nan
            prior_pred[target] = pr
            if len(tr_b) >= MIN_PORT_TRAIN:
                model = fit_binary(tr_b, BASKET_FEATURES, target)
                pred = float(model.predict_proba(
                    present[list(BASKET_FEATURES)].to_numpy(float))[0,1]
                    ) if model is not None else pr
            else:
                pred = np.nan
            stat["p_model_"+target] = pred
            stat["p_prior_"+target] = pr
            stat["p_gaussian_"+target] = float(r[
                "gaussian_p_"+target])
            stat["event_"+target] = int(r[target])
        portfolios.append(stat)

    observed = pd.concat(scores, ignore_index=True)
    estimates = pd.DataFrame(portfolios)
    for method in METHODS:
        assert observed.loc[observed.block>=ids[MIN_TICKER_TRAIN+1],
                            "p_"+method].notna().all()
    unique = observed[observed.block>=ids[MIN_PORT_TRAIN+1]].copy()
    ev = estimates[estimates.block>=ids[MIN_PORT_TRAIN+1]].copy()
    assert len(ev) == 43 and len(unique.block.unique()) == 43
    ticker_gains = {}
    for method in METHODS:
        by_block = []
        for b,g in unique.groupby("block", sort=True):
            yy = g.loss5.to_numpy(float)
            prior = g.p_prior.to_numpy(float)
            p = g["p_"+method].to_numpy(float)
            by_block.append(np.mean(brier(yy,prior)-brier(yy,p)))
        ticker_gains[method] = ci_month(by_block, SEED + (5 if method=="M_TAIL" else 6))
    comparison = {}
    for target in TARGETS:
        y=ev["event_"+target].to_numpy(float)
        null=ev["p_prior_"+target].to_numpy(float)
        p=ev["p_model_"+target].to_numpy(float)
        gauss=ev["p_gaussian_"+target].to_numpy(float)
        comparison[target] = dict(
            positives=int(y.sum()), evaluated_anchors=len(y),
            observed_rate=float(y.mean()),
            predicted_rate=float(p.mean()),
            brier_model=float(brier(y,p).mean()),
            brier_prior=float(brier(y,null).mean()),
            brier_gaussian=float(brier(y,gauss).mean()),
            model_minus_prior_gain=ci_month(brier(y,null)-brier(y,p),SEED+17),
            model_minus_gaussian_gain=ci_month(brier(y,gauss)-brier(y,p),SEED+18))

    window=days[ids[0]*K:(ids[-1]+1)*K+1]
    oldcurve=pd.read_csv(PREVIOUS/"EXPERTS_AND_REAL_COSTED_MIXTURES_DAILY.csv")
    curves={};economic={};pair={}
    for method,weightlist in weightpaths.items():
        curve, trades = trade_policy(weightlist, O, days, ids, list(roster.ticker))
        curves[method]=curve
        economic[method]=metrics(curve,window,trades)
    assert np.max(np.abs(curves["STATIC_F3_H1_50"] -
                         oldcurve.STATIC_F3_H1_50.to_numpy(float))) < 1e-9
    baseline=curves["STATIC_F3_H1_50"]
    yrs=np.array([pd.Timestamp(signals[b*K]).year for b in ids])
    for method in POLICIES[1:]:
        diff=np.diff(np.log(curves[method][::K])) - np.diff(np.log(baseline[::K]))
        check=ci_month(diff,SEED+19)
        eras=(float(diff[yrs<=2023].mean()),float(diff[yrs>=2024].mean()))
        pair[method]=dict(net_log_gain_per_21d_block=check, eras=eras,
            maxdd_improves=economic[method]["maxdd_daily_open"]>=
                           economic["STATIC_F3_H1_50"]["maxdd_daily_open"],
            es5_improves=economic[method]["es5_daily"]>=
                         economic["STATIC_F3_H1_50"]["es5_daily"])

    # The exact composite scientific gate was written BEFORE the training run.
    # Both conditional proper scores must beat historical prior with strictly
    # positive lower CIs; basket loss + intraperiod breaches must beat their
    # own prior and Gaussian baselines; realized gain and risk must not regress.
    ticker_gate = all(ticker_gains[m]["ci95"][0] > 0 for m in METHODS)
    port_gate = all(
        comparison[t]["model_minus_prior_gain"]["ci95"][0] > 0 and
        comparison[t]["model_minus_gaussian_gain"]["ci95"][0] > 0
        for t in TARGETS)
    net = pair["M_TAIL_WITHIN"]
    economic_gate=(net["net_log_gain_per_21d_block"]["ci95"][0]>0
                   and net["maxdd_improves"] and net["es5_improves"]
                   and all(x>0 for x in net["eras"]))
    verdict = bool(ticker_gate and port_gate and economic_gate)
    daily=pd.DataFrame({"day":window})
    for m,curve in curves.items():daily[m]=curve
    daily.to_csv(out/"DAILY_NEXT_OPEN_FULLY_COSTED_EQUITIES.csv",index=False)
    observed.to_csv(out/"SELECTED_ETF_ASOF_NOMINAL_TAIL_FORECASTS.csv",index=False)
    baskets.to_csv(out/"BASKET_ASOF_FEATURES_REALIZED_TARGETS.csv",index=False)
    estimates.to_csv(out/"BASKET_PREQUENTIAL_RISK_FORECASTS.csv",index=False)
    pd.DataFrame(positions).to_csv(out/"FROZEN_HOLDINGS.csv",index=False)
    result=dict(
        status="T149_M_SELECTED_NOMINAL_TAIL_CHRONOLOGY_COMPLETE",
        universe_count=149, original149_universe_sha256=sha(SRC/"universe.csv"),
        total_evaluation_blocks=64, minimum_prior_matured_ticker=MIN_TICKER_TRAIN,
        minimum_prior_matured_basket=MIN_PORT_TRAIN,
        strict_previous_block_embargo=True, same_f3_h1_top5=True,
        exact_static_share_parity=True, n_scored_portfolio_dates=43,
        n_scored_held_rows=int(len(unique)),
        label_definition="raw ETF 21d entry Open to exit Open < -5%; baseline 50/50 gross 21d <-5%; intramonth basket minimum relative to entry Open <-8%",
        covariance_definition="prior 63 completed Close daily log returns, 50 percent diagonal shrink",
        ticker_brier_gain=ticker_gains,
        portfolio_proper_scores=comparison,
        economics=economic, paired_economics=pair,
        gate_ticker=ticker_gate, gate_portfolio=port_gate,
        gate_economics=economic_gate, scientific_GO=verdict,
        preregistered_hypothesis_not_independent=True,
        known_limitations=["2021-26 repeatedly mined US survivor list",
                           "43 effective dates, not independent ticker rows",
                           "same chronology does not constitute fresh holdout",
                           "no true point-in-time ETF membership",
                           "FX, live spreads, taxes and EU brokerage untested"])
    (out/"RESULT.json").write_text(json.dumps(result,indent=2)+"\n")
    print("T149_M_SELECTED_NOMINAL_TAIL_RESULT "+json.dumps(result),flush=True)
    return result


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    evaluate(ap.parse_args().out)
