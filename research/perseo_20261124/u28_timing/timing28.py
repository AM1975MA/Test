"""Compare causal rotation schedules with the recovered Perseo U27 baseline."""

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "u27"))
from run27 import leg_correlation, previous
import verify24

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from matched import make_labels, window_engine

DURATIONS = (1, 2, 3, 4, 5)
SCENARIOS = ((15, 0, 0), (30, 0, 0), (15, 1, 0), (30, 1, 100))
MODES = (*(f"OPEN{n}" for n in DURATIONS), "MINVAR_OPEN3",
         "RULE_OPEN3", "RULE_UPTO5", "WF_1_OR_3", "WF_1_TO_5")
FEATURES = ("turnover", "est_cost_bp", "fallback", "proxy_corr", "tracking",
            "rel_mom5", "rel_mom21", "spread_vol21", "gross_cap")


def pairs(q):
    return np.column_stack([q["d1"][0], q["d2"][0]])


def with_pairs(q, matrix):
    return dict(q, d1=matrix[:, 0][None, :], d2=matrix[:, 1][None, :])


def prior_quotes(q, start, end, ids):
    x = q["C"][start:end, ids]
    if "low_observed" in q:
        x = np.where(q["low_observed"][start:end, ids], x, np.nan)
    return np.where(x > 0, x, np.nan)


def market_events(q, market):
    matrix = pairs(q)
    dates = pd.DatetimeIndex(q["dates"])
    events = np.flatnonzero(q["events"])
    if market != "USA":
        path = ROOT.parent / "u20" / "results" / f"{market}_TRANSFER_MAPPING.csv"
        proxies = pd.read_csv(path, parse_dates=["execution_date", "last_data_date"])
        proxies = {day: rows for day, rows in proxies.groupby("execution_date")}
    result = []
    for k in events[1:]:
        if k == len(dates)-1:
            continue
        nxt, old = matrix[k], matrix[k-1]
        delta = {int(t): (nxt == t).mean() - (old == t).mean() for t in np.union1d(nxt, old)}
        turnover = sum(abs(x) for x in delta.values())
        estimated = 15*turnover + sum(abs(x)>1e-12 for x in delta.values())
        rel = {}
        for h in (5, 21):
            if k <= h:
                rel[h] = np.nan
                continue
            t = prior_quotes(q, k-h-1, k, np.r_[nxt, old])
            p = t[-1] / t[0] - 1
            rel[h] = float(np.mean(p[:2]) - np.mean(p[2:]))
        path = prior_quotes(q, max(0,k-22), k, np.r_[nxt, old])
        day_diff = path[1:]/path[:-1]-1
        diff = day_diff[:, :2].mean(axis=1) - day_diff[:, 2:].mean(axis=1)
        spread = np.std(diff[np.isfinite(diff)], ddof=1) if np.isfinite(diff).sum() >= 15 else np.nan
        if market == "USA":
            coverage = 0, 1., 0.
        else:
            proxy = proxies[dates[k]]
            assert len(proxy) == 2 and (proxy.last_data_date < dates[k]).all()
            coverage = int((~proxy.passed).sum()), float(proxy.correlation.median()), float(proxy.tracking_ratio.median())
        fallback, correlation, tracking = coverage
        weak = fallback > 0 or correlation < .80 or tracking > .70
        wait = turnover >= 1 and rel[5] < 0 and (weak or turnover >= 1.5)
        close_at_signal = prior_quotes(q,k-1,k,np.r_[nxt,old])[0]
        recover = 5
        if wait:
            for n in (2, 3, 4):
                obs = prior_quotes(q,k+n-2,k+n-1,np.r_[nxt,old])[0]
                r = obs / close_at_signal - 1
                if r[:2].mean() >= r[2:].mean():
                    recover = n
                    break
        dated_end = dates[k+10] if k+10 < len(dates) else pd.NaT
        result.append(dict(market=market, date=dates[k], last_close=dates[k-1],
                           month=dates[k].to_period("M"), index=k, changed=turnover>1e-12,
                           label_index=k+10, label_end=dated_end, turnover=turnover,
                           est_cost_bp=estimated, fallback=fallback, proxy_corr=correlation,
                           tracking=tracking, rel_mom5=rel[5], rel_mom21=rel[21],
                           spread_vol21=spread, gross_cap=q["g"][k],
                           rule_fixed=3 if wait else 1, rule_dynamic=recover if wait else 1,
                           old_pair="|".join(q["tickers"][old]), new_pair="|".join(q["tickers"][nxt])))
    return pd.DataFrame(result)


def minvar(q, k):
    if k < 64:
        return .5
    legs = pairs(q)[k]
    if legs[0] == legs[1]:
        return .5
    close = prior_quotes(q, k-64,k,legs)
    daily = np.log(close[1:]/close[:-1])
    valid = np.isfinite(daily).all(axis=1)
    if valid.sum() < 51:
        return .5
    a, b, v = np.cov(daily[valid].T)[[0,1,0],[0,1,1]]
    if min(a,b) <= 1e-15 or a+b-2*v <= 1e-13:
        return .5
    return float(np.clip((b-v)/(a+b-2*v),.25,.75))


def assign(q, opening, alloc=False):
    legs = pairs(q)
    events = np.flatnonzero(q["events"])
    assert np.diff(events).min() > 5
    assert events[0] == 0
    scheduled = legs.copy()
    out = dict(q, events=q["events"].copy(), weights=q["weights"].copy())
    audited = []
    for k, nxt in zip(events, np.r_[events[1:], len(legs)]):
        if k == len(legs)-1:
            break
        wait = opening.get(k,1)-1 if k else 0
        dest = min(k+wait, nxt-1)
        w = minvar(q,k) if alloc else .5
        if dest > k:
            scheduled[k:dest] = legs[k-1]
            out["events"][k] = False
        out["events"][dest] = True
        out["weights"][0,dest:nxt] = w
        if dest > k:
            out["weights"][0,k:dest] = out["weights"][0,k-1]
        audited.append((k,dest,w))
    return with_pairs(out,scheduled), audited


def weight_history(rows, decision, cutoff):
    past = rows[(rows.month < decision) & (rows.label_end < cutoff)].dropna(subset=["log_gain_2"])
    if past.month.nunique() < 18:
        return None, past
    x = past[list(FEATURES)]
    y = past[[f"log_gain_{n}" for n in DURATIONS[1:]]]
    model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                          Ridge(alpha=32))
    return model.fit(x,y), past


def walkforward(info, label_frame):
    joined = info.merge(label_frame, on=["market","index","bps"], how="left", validate="one_to_one")
    records = []
    check = 0
    for bps, group in joined.groupby("bps"):
        for month, rows in group.groupby("month"):
            cutoff = rows.last_close.min()
            model, past = weight_history(group,month,cutoff)
            forecasts = model.predict(rows[list(FEATURES)]) if model else np.full((len(rows),4),np.nan)
            if model and month.month == 6:
                perturbed = group.copy()
                perturbed.loc[(perturbed.month>=month)|(perturbed.label_end>=cutoff),
                              [f"log_gain_{n}" for n in DURATIONS[1:]]] = 999.
                refit, _ = weight_history(perturbed,month,cutoff)
                np.testing.assert_array_equal(forecasts,refit.predict(rows[list(FEATURES)]))
                check += 1
            for row, mu in zip(rows.itertuples(), forecasts):
                shortest, longest = 1, 1
                if row.changed and np.isfinite(mu).all():
                    if mu[1] > .002:
                        shortest = 3
                    if mu.max() > .002:
                        longest = int(np.argmax(mu))+2
                records.append(dict(market=row.market, bps=bps, index=row.index, date=row.date,
                                    train_cutoff=cutoff, train_size=len(past), train_months=past.month.nunique(),
                                    last_outcome=past.label_end.max(), WF_1_OR_3=shortest, WF_1_TO_5=longest,
                                    **{f"pred{n}": v for n,v in zip(DURATIONS[1:],mu)}))
    assert check >= 4
    return pd.DataFrame(records), check


def source_receipts(path):
    import hashlib
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"results")
    parser.add_argument("--prior-fixed",type=Path)
    args = parser.parse_args()
    folder = args.output
    folder.mkdir(exist_ok=True,parents=True)
    engine = window_engine(previous.simulate)
    infos, labels, baseline_nav = [], [], {}
    published = pd.read_csv(ROOT.parent/"u27"/"results"/"SUMMARY.csv").query("rule=='CORR70'")
    old_trials = None if args.prior_fixed is None else pd.read_csv(args.prior_fixed)
    for market in previous.MARKETS:
        q = previous.state(market)
        info = market_events(q,market)
        matrix = pairs(q)
        corr = (leg_correlation(q) < .70).astype(int)
        alt, _ = assign(q,{k:5 for k in info["index"]})
        old_corr = (leg_correlation(alt) < .70).astype(int)
        built = previous.signals(q,market)
        for bps in (15,30):
            result, nav = make_labels(q,matrix,corr,old_corr,built,previous.BM[market],engine,info,bps)
            labels.append(result.assign(market=market))
            baseline_nav[market,bps] = nav
            infos.append(info.assign(bps=bps))
        print("MATCHED",market,len(info),flush=True)
    info = pd.concat(infos,ignore_index=True)
    label = pd.concat(labels,ignore_index=True)
    fitted, checks = walkforward(info,label)
    results, annual, months, timings = [],[],[],[]
    with TemporaryDirectory(prefix="u28_timing_") as scratch:
        previous.OUT = verify24.OUT = Path(scratch)
        for market in previous.MARKETS:
            q = previous.state(market)
            dates = pd.DatetimeIndex(q["dates"])
            z = info.query("market == @market and bps == 15")
            model_rows = fitted[fitted.market.eq(market)]
            original = previous.simulate
            for mode in MODES:
                choices = {}
                for bps in (15,30):
                    if mode.startswith("OPEN"):
                        choice = {k:int(mode[-1]) for k in z["index"]}
                    elif mode=="MINVAR_OPEN3":
                        choice = {k:3 for k in z["index"]}
                    elif mode.startswith("RULE"):
                        choice = z.set_index("index")["rule_fixed" if mode=="RULE_OPEN3" else "rule_dynamic"].to_dict()
                    else:
                        choice = model_rows[model_rows.bps.eq(bps)].set_index("index")[mode].to_dict()
                    signature = tuple(choice.items())
                    if signature not in choices:
                        state, audit = assign(q,choice,alloc=mode=="MINVAR_OPEN3")
                        choices[signature]=(state,previous.signals(state,market),
                                            (leg_correlation(state)<.70).astype(int),audit)
                    state, signal, corr, audit = choices[signature]
                    timings.extend(dict(market=market,mode=mode,bps=bps,date=dates[k],target_date=dates[e],
                                        opening=e-k+1,weight=w) for k,e,w in audit if k)
                    for fee, lag, slip in SCENARIOS:
                        if bps != fee:
                            continue
                        configured = dict(state,risk_mode=np.r_[corr[0],corr[:-1]] if lag else corr)

                        def simulate(*args, **kwargs):
                            kwargs["stop_friction"] = slip/10000
                            return original(*args,**kwargs)

                        with patch.object(previous,"simulate",simulate):
                            row, account, _ = previous.run(market,"PROFIT_RAMP",bps,lag,configured,signal)
                        nav = account["ledger"][:,0]
                        audit_nav = verify24.replay(SimpleNamespace(market=market,rule="PROFIT_RAMP",bps=bps,lag=lag),configured)
                        if mode=="OPEN1" and not lag:
                            np.testing.assert_array_equal(nav,baseline_nav[market,bps])
                        if mode=="OPEN1" and slip==0:
                            ref = published.query("market == @market and bps == @bps and lag == @lag").iloc[0]
                            np.testing.assert_allclose([row["cagr"],row["maxdd"],row["orders"]],
                                                       [ref.cagr,ref.maxdd,ref.orders],atol=1e-12,rtol=0)
                        if old_trials is not None and mode in ("OPEN3","MINVAR_OPEN3") and slip==0:
                            old_mode = "DELAY3_PRIMARY" if mode=="OPEN3" else "MINVAR_DELAY3"
                            ref = old_trials.query("market == @market and bps == @bps and lag == @lag and mode == @old_mode").iloc[0]
                            np.testing.assert_allclose([row["cagr"],row["maxdd"],row["orders"]],
                                                       [ref.cagr,ref.maxdd,ref.orders],atol=1e-12,rtol=0)
                        meta = dict(market=market, mode=mode, bps=bps, lag=lag, stop_slippage_bps=slip)
                        cut = dates.searchsorted("2023-01-03")
                        early = previous.metrics(dates[:cut+1],nav[:cut+1])
                        late = previous.metrics(dates[cut:],nav[cut:])
                        results.append(dict(meta,**{k:row[k] for k in ("cagr","maxdd","orders","stops","cost_currency")},
                                            early_cagr=early["cagr"],early_maxdd=early["maxdd"],late_cagr=late["cagr"],
                                            late_maxdd=late["maxdd"],units_error=audit_nav["units_error"],
                                            cash_error=audit_nav["cash_error"]))
                        seq = previous.months(dates,nav)
                        months.extend(dict(meta,month=str(m),ret=v) for m,v in seq.items())
                        agg = (1+seq).groupby(seq.index.year).prod()-1
                        annual.extend(dict(meta,year=int(y),ret=v) for y,v in agg.items())
                        del account,nav
                print("PATH",market,mode,flush=True)
    tables = dict(SUMMARY=results, MONTHLY=months, ANNUAL=annual, TIMING=timings,
                  FEATURES=info, MATCHED_LABELS=label, WALKFORWARD=fitted)
    for name, value in tables.items():
        pd.DataFrame(value).to_csv(folder/f"{name}.csv",index=False)
    qa = dict(status="PASS", accounts=len(results), matched_rotations=len(label)//2,
              matched_windows=len(label)*5, label_future_mutations=checks,
              original_controls=9, prior_open3_controls=18 if old_trials is not None else 0,
              source_sha256={m:source_receipts(previous.INPUT/f"{m}_STATE.npz") for m in previous.MARKETS})
    (folder/"QA.json").write_text(json.dumps(qa,indent=2)+"\n")
    print(qa,flush=True)


if __name__=="__main__":
    main()
