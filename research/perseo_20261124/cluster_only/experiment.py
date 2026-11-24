"""Causal monthly clustering, cluster-level training, and neutral execution."""

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from panels import load_inputs

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "u24"))
from broker_cost import solve_budget

LOOKBACK = 126
FAMILIES = ("CORRELATION", "LEGACY", "ECONOMIC_EU")
BASELINES = ("MOM21", "MOM_BLEND")
MODELS = ("RIDGE", "HGB")
FEATURES = (
    "r5", "r21", "r63", "r126", "breadth21", "breadth63", "disp21", "vol21",
    "vol63", "drawdown63", "downside63", "beta63", "cohesion", "log_members",
    "market_r21", "market_r63", "market_vol63", "market_breadth63",
)
RANKED = tuple(key for key in FEATURES if not key.startswith("market_"))
MODEL_COLUMNS = (*FEATURES, *(f"{key}_rank" for key in RANKED))


def month_positions(market):
    months = market.dates.to_period("M")
    return np.flatnonzero(np.r_[True, months[1:] != months[:-1]])


def data_at_open(market, start):
    sl = slice(max(0, start - LOOKBACK - 3), start)
    if market.history_usable is not None:
        sl = np.flatnonzero(market.history_usable[:start])[-LOOKBACK - 3:]
    available = market.observed[sl]
    raw = pd.DataFrame(market.close[sl]).where(available)
    hist = raw.ffill(limit=2).to_numpy()[-LOOKBACK - 1:]
    daily = hist[1:] / hist[:-1] - 1
    observed_fraction = available[-LOOKBACK - 1:].mean(axis=0)
    if market.volume is None:
        liquidity = observed_fraction
    else:
        observed_cash_volume = np.where(
            market.observed[start - 63:start],
            market.volume[start - 63:start] * market.close[start - 63:start], 0
        )
        liquidity = np.median(np.nan_to_num(observed_cash_volume), axis=0)
    valid = np.isfinite(daily).all(axis=0) & (observed_fraction >= 0.90) & market.eligible
    if market.volume is not None:
        valid &= liquidity >= 100_000
    return hist, daily, liquidity, valid


def correlations(daily):
    center = daily - daily.mean(axis=0)
    norms = np.linalg.norm(center, axis=0)
    standard = np.divide(center, norms, out=np.zeros_like(center), where=norms > 1e-12)
    matrix = np.clip(standard.T @ standard, -1.0, 1.0)
    np.fill_diagonal(matrix, 1.0)
    return matrix


def membership(market, start, family, old, econ, valid, daily):
    ids = np.flatnonzero(valid)
    known = market.dates[start - 1]
    if family == "CORRELATION":
        if len(ids) < 2:
            return {}, known
        corr = correlations(daily[:, ids])
        distance = 1.0 - corr
        distance = (distance + distance.T) / 2
        np.fill_diagonal(distance, 0)
        labels = fcluster(linkage(squareform(distance, checks=False), method="complete"),
                          t=0.15, criterion="distance")
        return {label: ids[labels == label] for label in np.unique(labels)}, known
    if family == "LEGACY":
        dates, snapshots = old[market.name]
        k = dates.searchsorted(known, side="right") - 1
        if k < 0:
            return {}, known
        known = dates[k]
        groups = snapshots[known]
    else:
        groups = econ
    return {label: np.asarray(members)[valid[np.asarray(members, dtype=int)]].astype(int)
            for label, members in groups.items()}, known


def make_snapshot(market, start, end, family, old, econ):
    hist, daily, liquidity, valid = data_at_open(market, start)
    groups, last_membership = membership(market, start, family, old, econ, valid, daily)
    groups = {label: ids for label, ids in groups.items() if len(ids) >= 2}
    assert sum(len(ids) for ids in groups.values()) == len({j for ids in groups.values() for j in ids})
    if len(groups) < 4:
        return []
    benchmark = daily[-63:, market.benchmark]
    if not np.isfinite(benchmark).all():
        return []
    market_vol = float(np.std(benchmark, ddof=1))
    if market_vol <= 1e-9:
        return []
    row_common = dict(
        market=market.name, family=family, day=market.dates[start],
        close_cutoff=market.dates[start - 1], member_cutoff=last_membership,
        label_end=market.dates[end], month=str(market.dates[start].to_period("M")),
        market_r21=float(hist[-1, market.benchmark] / hist[-22, market.benchmark] - 1),
        market_r63=float(hist[-1, market.benchmark] / hist[-64, market.benchmark] - 1),
        market_vol63=market_vol,
        market_breadth63=float((hist[-1, valid] > hist[-64, valid]).mean()),
        eligible_tickers=int(valid.sum()),
    )
    rows = []
    for label, members in groups.items():
        tickers = market.tickers[members]
        neutral = sorted(members, key=lambda i: (-float(liquidity[i]), market.tickers[i]))[:2]
        values = hist[:, members]
        changes = {h: values[-1] / values[-h-1] - 1 for h in (5, 21, 63, 126)}
        rates = daily[:, members]
        composite = rates.mean(axis=1)
        cum = np.r_[1.0, np.cumprod(1 + composite[-63:])]
        relation = correlations(rates)
        msize = len(members)
        cohesion = (relation.sum() - msize) / (msize * (msize - 1))
        beta = np.cov(composite[-63:], benchmark, ddof=1)[0, 1] / market_vol**2
        entry = market.open_observed[start, members]
        exit_quote = market.open_observed[end, members]
        forwards = np.zeros(msize)
        entered = members[entry]
        forwards[entry] = market.open_mark[end, entered] / market.opening[start, entered] - 1
        direct_end = entry & exit_quote
        group_id = str(label) if family != "CORRELATION" else hashlib.sha1(
            "|".join(sorted(tickers)).encode()).hexdigest()[:13]
        rows.append(dict(
            row_common, cluster=group_id, members=msize,
            tickers="|".join(sorted(tickers)), neutral="|".join(market.tickers[neutral]),
            **{f"r{h}": float(np.mean(value)) for h, value in changes.items()},
            breadth21=float((changes[21] > 0).mean()), breadth63=float((changes[63] > 0).mean()),
            disp21=float(np.std(changes[21], ddof=1)), vol21=float(composite[-21:].std(ddof=1)),
            vol63=float(composite[-63:].std(ddof=1)),
            drawdown63=float(np.min(cum / np.maximum.accumulate(cum) - 1)),
            downside63=float(np.sqrt(np.mean(np.minimum(composite[-63:], 0)**2))),
            beta63=float(beta), cohesion=float(cohesion), log_members=float(np.log(msize)),
            forward=float(forwards.mean()), realized_observed=float(direct_end.mean()),
            realized_pairwise=float(forwards[direct_end].mean()) if direct_end.any() else np.nan,
        ))
    return rows


def model_panel(markets, old, econ):
    rows = []
    checks = []
    for name, market in markets.items():
        bounds = month_positions(market)
        periods = [(start, end) for start, end in zip(bounds, bounds[1:]) if start > LOOKBACK]
        for family in FAMILIES:
            if family == "ECONOMIC_EU" and name != "EU":
                continue
            snapshots = [make_snapshot(market, s, e, family, old, econ) for s, e in periods]
            for date_rows in snapshots:
                rows.extend(date_rows)
            for k in (len(periods) // 4, len(periods) // 2, len(periods) * 3 // 4):
                start, end = periods[k]
                altered = market.close.copy()
                altered[start:] *= np.linspace(0.8, 1.2, altered.shape[1])
                change = make_snapshot(replace(market, close=altered), start, end, family, old, econ)
                pd.testing.assert_frame_equal(pd.DataFrame(snapshots[k]), pd.DataFrame(change))
                checks.append(dict(market=name, family=family, cutoff=str(market.dates[start].date()),
                                   clusters=len(change)))
            print("SNAPSHOTS", family, name, sum(map(bool, snapshots)), "months", flush=True)
    panel = pd.DataFrame(rows)
    grouping = ["family", "market", "day"]
    g = panel.groupby(grouping, sort=False)
    counts = g.cluster.transform("size")
    for col in (*RANKED, "forward"):
        panel[f"{col}_rank"] = (g[col].rank(method="average") - 0.5) / counts - 0.5
    assert np.isfinite(panel[list(MODEL_COLUMNS)]).all().all()
    assert (panel.member_cutoff <= panel.close_cutoff).all() and (panel.close_cutoff < panel.day).all()
    return panel.sort_values(grouping + ["cluster"]).reset_index(drop=True), checks


def estimated_models(training):
    fitted = {}
    x = training[list(MODEL_COLUMNS)].to_numpy()
    y = training.forward_rank.to_numpy()
    count = training.groupby(["market", "day"]).cluster.transform("count").to_numpy()
    raw_weight = 1 / count
    weights = raw_weight / raw_weight.mean()
    ridge = make_pipeline(StandardScaler(), Ridge(alpha=32.0))
    ridge.fit(x, y, standardscaler__sample_weight=weights, ridge__sample_weight=weights)
    fitted["RIDGE"] = ridge
    hgb = HistGradientBoostingRegressor(max_iter=90, learning_rate=0.06, max_leaf_nodes=7,
                                       min_samples_leaf=45, l2_regularization=3,
                                       early_stopping=False, random_state=2711)
    fitted["HGB"] = hgb.fit(x, y, sample_weight=weights)
    return fitted


def history(rows, cutoff):
    return rows[(rows.label_end < cutoff) &
                (rows.day >= cutoff - pd.DateOffset(months=48))]


def walkforward(panel):
    predictions, fit_audit = [], []
    invariance = 0
    for family, groups in panel.groupby("family"):
        available = groups.day.drop_duplicates().sort_values()
        check_dates = set(available.iloc[[-offset for offset in (36, 18, 4) if offset <= len(available)]])
        for day, rows in groups.groupby("day", sort=True):
            if day < pd.Timestamp("2020-01-01"):
                continue
            past = history(groups, day)
            if past.month.nunique() < 24:
                continue
            assert past.label_end.max() < day
            scores = rows.copy()
            scores["MOM21"] = scores.r21_rank
            scores["MOM_BLEND"] = scores[["r21_rank", "r63_rank", "r126_rank"]].mean(axis=1)
            fitted = estimated_models(past)
            x = scores[list(MODEL_COLUMNS)].to_numpy()
            for nm, model in fitted.items():
                scores[nm] = model.predict(x)
            if day in check_dates:
                mutated = groups.copy()
                mutated.loc[mutated.label_end >= day, "forward_rank"] *= -99
                alt = estimated_models(history(mutated, day))
                for nm, model in alt.items():
                    np.testing.assert_array_equal(scores[nm].to_numpy(), model.predict(x))
                invariance += 1
            fit_audit.append(dict(family=family, day=str(day.date()), first_train=str(past.day.min().date()),
                                  latest_label=str(past.label_end.max().date()), months=past.month.nunique(),
                                  samples=len(past), train_paniere_mese=len(past.groupby(["market", "month"]))))
            predictions.append(scores)
    scored = pd.concat(predictions, ignore_index=True)
    assert not scored.duplicated(["market", "family", "month", "cluster"]).any()
    return scored, pd.DataFrame(fit_audit), invariance


def selection(scored, methods=(*BASELINES, *MODELS)):
    decisions = []
    for (family, market, day), group in scored.groupby(["family", "market", "day"], sort=True):
        n = len(group)
        returns = group.forward.to_numpy()
        win, quartile = returns.max(), int(np.ceil(n / 4))
        common = dict(family=family, market=market, day=day, month=group.month.iloc[0],
                      n_clusters=n, chance_top1=float((returns == win).mean()),
                      chance_top_quartile=quartile / n, pool=float(returns.mean()),
                      observed_outcomes=group.realized_observed.mean(),
                      n_members=group.members.mean(), eligible_tickers=int(group.eligible_tickers.iloc[0]))
        for method in methods:
            changed = group.sort_values([method, "cluster"], ascending=[False, True])
            first, second = (row for _, row in changed.iloc[:2].iterrows())
            quartile_hit = int((returns > first.forward).sum()) < quartile
            rank_ic = float(spearmanr(group[method], group.forward).statistic)
            decisions.append(dict(
                common, method=method, top1=first.cluster, top2=second.cluster,
                top1_members=first.tickers, top2_members=second.tickers,
                neutral_1=first.neutral, neutral_2=second.neutral,
                top1_hit=int(first.forward == win), top_quartile_hit=int(quartile_hit), rank_ic=rank_ic,
                top1_return=first.forward, top2_return=(first.forward + second.forward) / 2,
                top2_observed=(first.realized_observed + second.realized_observed) / 2,
                top2_pairwise=(first.realized_pairwise + second.realized_pairwise) / 2,
                benchmark_pairwise=float(group.realized_pairwise.mean()),
            ))
    return pd.DataFrame(decisions)


def account(market, considered, bps):
    first = market.dates.get_loc(considered.day.min())
    last_day = considered.day.max()
    next_open = month_positions(market)
    last = next_open[market.dates[next_open].searchsorted(last_day, side="right")]
    name_to_idx = {ticker: j for j, ticker in enumerate(market.tickers)}
    orders, series = [], []
    units = np.zeros(len(market.tickers))
    cash = 10_000.0
    target = None
    intended_date = None
    events = considered.set_index("day")
    max_error = 0.0
    for k in range(first, last + 1):
        date = market.dates[k]
        held = units > 0
        equity = cash + units[held] @ market.open_mark[k, held]
        series.append(dict(day=date, nav=equity))
        if k == last:
            break
        if date in events.index:
            row = events.loc[date]
            target = np.zeros_like(units)
            intended_date = date
            for basket in (row.neutral_1, row.neutral_2):
                indices = [name_to_idx[t] for t in basket.split("|")]
                target[indices] += 0.5 / len(indices)
        if target is not None:
            involved = held | (target > 0)
            if not market.open_observed[k, involved].all():
                continue
            price = market.opening[k, involved]
            old = units[involved] * price
            newval, fee, tickets = solve_budget(equity, old, target[involved], 1.0, bps / 10000)
            proposed = newval * target[involved]
            diff = proposed - old
            legal_order = np.abs(diff) > max(1e-12, equity * 1e-10)
            assert legal_order.sum() == tickets
            assert abs(fee - tickets - bps / 10000 * np.abs(diff[legal_order]).sum()) < 1e-7
            residual = equity - fee - proposed.sum()
            assert residual > -1e-7
            cash = max(0.0, residual)
            units[involved] = proposed / price
            max_error = max(max_error, abs(cash + units[involved] @ price + fee - equity))
            orders.append(dict(day=date, intended_day=intended_date, orders=tickets,
                               delay_sessions=k - market.dates.get_loc(intended_date),
                               turnover=float(np.abs(diff).sum() / equity), fee=fee))
            target = None
    curve = pd.DataFrame(series)
    rebalance = pd.DataFrame(orders)
    assert max_error < 1e-7 and (curve.nav > 0).all()
    return curve, rebalance, max_error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", default=HERE / "results", type=Path)
    parser.add_argument("--skip-tr-outages", action="store_true")
    args = parser.parse_args()
    destination = args.output
    destination.mkdir(parents=True, exist_ok=True)
    markets, legacy, taxonomy, source_paths = load_inputs(args.inputs)
    ignored = []
    if args.skip_tr_outages:
        market = markets["TR"]
        degree = pd.Series(market.observed[:, market.eligible].sum(axis=1))
        baseline = degree.rolling(63, min_periods=30).median().shift(1)
        usable = ~(degree < 0.20 * baseline).to_numpy()
        ignored = [str(date.date()) for date in market.dates[~usable]]
        markets["TR"] = replace(market, history_usable=usable)
    panel, feature_checks = model_panel(markets, legacy, taxonomy)
    scored, fits, label_checks = walkforward(panel)
    picks = selection(scored)
    accounts, paths, trades = [], [], []
    for (family, name, method), groups in picks.groupby(["family", "market", "method"]):
        for bps in (15, 30):
            curve, orders, error = account(markets[name], groups, bps)
            start, end = curve.day.iloc[[0, -1]]
            fields = dict(family=family, market=name, method=method, bps=bps)
            years = (end - start).days / 365.2425
            ratio = curve.nav.iloc[-1] / curve.nav.iloc[0]
            accounts.append(dict(
                fields, start=start, end=end, months=len(groups), cagr=ratio**(1/years)-1,
                drawdown=float((curve.nav / curve.nav.cummax() - 1).min()),
                orders=orders.orders.sum(), fees=orders.fee.sum(), ledger_error=error,
                latest_delay=int(orders.delay_sessions.max()), missed_rebalances=len(groups) - len(orders),
            ))
            paths.append(curve.assign(**fields))
            trades.append(orders.assign(**fields))
    checks = dict(
        status="PASS", snapshots=len(picks) // 4, feature_prefix_checks=feature_checks,
        label_perturbation_checks=label_checks, portfolio_accounts=len(accounts),
        observation_sources={name: market.observation_source for name, market in markets.items()},
        dropped_tr_feature_sessions=ignored,
        input_sha256={path.name: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
                      for path in source_paths},
    )
    tables = dict(SNAPSHOT_PANEL=panel, SCORED_CLUSTERS=scored, FIT_CUTOFFS=fits,
                  MONTHLY_PICKS=picks, ACCOUNT_SUMMARY=pd.DataFrame(accounts),
                  ACCOUNT_PATHS=pd.concat(paths), ACCOUNT_TRADES=pd.concat(trades))
    for name, table in tables.items():
        suffix = ".csv.gz" if name in ("SNAPSHOT_PANEL", "SCORED_CLUSTERS", "ACCOUNT_PATHS") else ".csv"
        table.to_csv(destination / f"{name}{suffix}", index=False)
    (destination / "QA.json").write_text(json.dumps(checks, indent=2) + "\n")
    print("CLUSTER_ONLY_QA_PASS", len(scored), len(accounts), label_checks, flush=True)


if __name__ == "__main__":
    main()
