"""Prediction quality, with strict coverage and vintage-aware paired diagnostics.

Percentiles are realized ranks, never probabilities or classification accuracy.
NDCG uses linear continuous relevance and deterministic ticker ties. Aggregate
weights annual folds equally; aggregate_by_date weights mature dates equally.
Bootstrap intervals concern date-weighted paired effects, not independent
vintages, and are development diagnostics rather than a promotion certificate.
"""
from __future__ import annotations

import hashlib
import math
import numpy as np
import pandas as pd

KEYS = ["vintage", "signal_date", "ticker"]
METRICS = (
    "top1_realized_percentile", "top1_hit_exact", "top1_hit_top5",
    "top1_hit_topdecile", "top5_overlap", "ndcg5", "ndcg10", "rank_ic",
    "top1_return_regret", "top1_return_regret_vs_topdecile_mean", "top1_realized_return",
    "random_top1_realized_percentile", "random_top1_hit_exact",
    "random_top1_hit_top5", "random_top1_hit_topdecile", "random_top5_overlap",
)


def _mean(values):
    finite = [float(x) for x in values if x is not None and np.isfinite(x)]
    return float(np.mean(finite)) if finite else None


def _hash_strings(values):
    return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()


def _validated(frame):
    required = {"signal_date", "ticker", "target_rank_21", "pred"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(frame.columns))}")
    z = frame.copy()
    if z.empty:
        raise ValueError("Empty inference coverage")
    if "vintage" not in z:
        z["vintage"] = "single"
    if z[["signal_date", "ticker", "vintage"]].isna().any().any():
        raise ValueError("Missing inference keys")
    z["signal_date"] = pd.to_datetime(z.signal_date, errors="raise")
    if z.signal_date.isna().any() or z.signal_date.dt.tz is not None:
        raise ValueError("Invalid or timezone-aware signal dates")
    if not z.signal_date.eq(z.signal_date.dt.normalize()).all():
        raise ValueError("Signal dates must be midnight session dates")
    z["ticker"] = z.ticker.astype(str)
    z["vintage"] = z.vintage.astype(str)
    if z.ticker.eq("").any() or z.vintage.eq("").any() or z.duplicated(KEYS).any():
        raise ValueError("Empty or duplicate inference keys")
    z["pred"] = pd.to_numeric(z.pred, errors="raise")
    if not np.isfinite(z.pred.to_numpy(float)).all():
        raise ValueError("Nonfinite predictions in inference coverage")
    return z.sort_values(KEYS).reset_index(drop=True)


def evaluate(frame, quality_exit_cutoff=None, expected_keys=None):
    """Evaluate all mature queries without filtering on future labels.

    If cutoff is supplied, exit_date_21 is required and only exits <= cutoff
    enter quality metrics. Predictions and keys are validated on ALL inference
    rows first. Query-level partial maturity is rejected. expected_keys, when
    supplied, must match the entire inference key set exactly.
    """
    z = _validated(frame)
    if expected_keys is not None:
        e = expected_keys.copy()
        if "vintage" not in e:
            e["vintage"] = "single"
        if not set(KEYS).issubset(e) or e[KEYS].isna().any().any():
            raise ValueError("Invalid expected coverage keys")
        e["signal_date"] = pd.to_datetime(e.signal_date, errors="raise")
        e["ticker"] = e.ticker.astype(str)
        e["vintage"] = e.vintage.astype(str)
        if e.duplicated(KEYS).any() or not z[KEYS].equals(e[KEYS].sort_values(KEYS).reset_index(drop=True)):
            raise ValueError("Inference coverage differs from expected keys")
    mask = pd.Series(True, index=z.index)
    cutoff_text = None
    if quality_exit_cutoff is not None:
        if "exit_date_21" not in z:
            raise ValueError("Quality cutoff requires exit_date_21")
        cutoff = pd.Timestamp(quality_exit_cutoff)
        if pd.isna(cutoff) or cutoff.tz is not None:
            raise ValueError("Invalid quality cutoff")
        exits = pd.to_datetime(z.exit_date_21, errors="raise")
        if exits.dt.tz is not None:
            raise ValueError("Timezone-aware exits")
        if (exits.notna() & (exits <= z.signal_date)).any():
            raise ValueError("Exit must follow signal date")
        mask = exits.notna() & (exits <= cutoff)
        cutoff_text = cutoff.isoformat()
        counts = mask.groupby([z.vintage, z.signal_date]).agg(["sum", "count"])
        if ((counts["sum"] > 0) & (counts["sum"] < counts["count"])).any():
            raise ValueError("Partially mature query would change the eligible cohort")
    mature = z.loc[mask].copy()
    if mature.empty:
        raise ValueError("No mature quality queries")
    mature["target_rank_21"] = pd.to_numeric(mature.target_rank_21, errors="raise")
    target = mature.target_rank_21.to_numpy(float)
    if not np.isfinite(target).all() or ((target < 0) | (target > 1)).any():
        raise ValueError("Invalid mature percentile targets")
    has_returns = "target_ret_21" in mature
    if has_returns:
        mature["target_ret_21"] = pd.to_numeric(mature.target_ret_21, errors="raise")
        if not np.isfinite(mature.target_ret_21.to_numpy(float)).all():
            raise ValueError("Nonfinite mature realized returns")
    records = []
    for (vintage, date), g in mature.groupby(["vintage", "signal_date"], sort=True):
        g = g.sort_values("ticker").reset_index(drop=True)
        n = len(g)
        if n < 2:
            raise ValueError("Quality query requires at least two tickers")
        pred_order = g.sort_values(["pred", "ticker"], ascending=[False, True], kind="stable").index.to_numpy()
        true_order = g.sort_values(["target_rank_21", "ticker"], ascending=[False, True], kind="stable").index.to_numpy()
        k = min(5, n)
        winner = int(pred_order[0])
        gains = g.target_rank_21.to_numpy(float)
        ndcgs = {}
        for requested in (5, 10):
            limit = min(requested, n)
            discounts = 1.0 / np.log2(np.arange(2, limit + 2))
            ideal = float(gains[true_order[:limit]] @ discounts)
            if ideal <= 0:
                raise ValueError("NDCG undefined for all-zero relevance")
            ndcgs[f"ndcg{requested}"] = float(gains[pred_order[:limit]] @ discounts / ideal)
        rp = g.pred.rank(method="average").to_numpy(float)
        rt = g.target_rank_21.rank(method="average").to_numpy(float)
        ic = float(np.corrcoef(rp, rt)[0, 1]) if np.ptp(rp) > 0 and np.ptp(rt) > 0 else None
        target_hash = hashlib.sha256(np.asarray(gains, dtype="<f8").tobytes()).hexdigest()
        record = dict(vintage=str(vintage), signal_date=pd.Timestamp(date).isoformat(),
            year=int(date.year), n_tickers=n, coverage_sha256=_hash_strings(g.ticker.tolist()),
            target_sha256=target_hash, selected_ticker=str(g.loc[winner, "ticker"]),
            predicted_top5=g.loc[pred_order[:k],"ticker"].tolist(),
            realized_top5=g.loc[true_order[:k],"ticker"].tolist(),
            top1_realized_percentile=float(gains[winner]),
            top1_hit_exact=float(winner == true_order[0]),
            top1_hit_top5=float(winner in true_order[:k]),
            top1_hit_topdecile=float(winner in true_order[:math.ceil(n / 10)]),
            top5_overlap=float(len(set(pred_order[:k]) & set(true_order[:k])) / k),
            rank_ic=ic, top1_return_regret=None,
            top1_return_regret_vs_topdecile_mean=None, top1_realized_return=None,
            prediction_tied_rows=int(g.pred.duplicated(keep=False).sum()),
            target_tied_rows=int(g.target_rank_21.duplicated(keep=False).sum()),
            pred_top1_tie_count=int(g.pred.eq(g.loc[winner, "pred"]).sum()),
            pred_top5_boundary_tie_count=int(g.pred.eq(g.loc[pred_order[k-1], "pred"]).sum()),
            target_top1_tie_count=int(g.target_rank_21.eq(gains[true_order[0]]).sum()),
            target_top5_boundary_tie_count=int(g.target_rank_21.eq(gains[true_order[k-1]]).sum()),
            target_topdecile_boundary_tie_count=int(g.target_rank_21.eq(gains[true_order[math.ceil(n/10)-1]]).sum()),
            random_top1_realized_percentile=float(gains.mean()),
            random_top1_hit_exact=1.0 / n, random_top1_hit_top5=k / n,
            random_top1_hit_topdecile=math.ceil(n / 10) / n,
            random_top5_overlap=k / n, **ndcgs)
        if has_returns:
            returns = g.target_ret_21.to_numpy(float)
            record["return_target_sha256"] = hashlib.sha256(np.asarray(returns, dtype="<f8").tobytes()).hexdigest()
            record["top1_realized_return"] = float(returns[winner])
            record["top1_return_regret"] = float(returns.max() - returns[winner])
            record["top1_return_regret_vs_topdecile_mean"] = float(returns[true_order[:math.ceil(n/10)]].mean() - returns[winner])
        records.append(record)
    # Average vintage values within a date BEFORE year/date aggregation.
    q = pd.DataFrame(records)
    by_date = []
    for date, g in q.groupby("signal_date", sort=True):
        by_date.append(dict(signal_date=date, year=int(g.year.iloc[0]), vintages=len(g),
            **{m: _mean(g[m]) for m in METRICS}))
    years = []
    for year in sorted({r["year"] for r in by_date}):
        rows = [r for r in by_date if r["year"] == year]
        years.append(dict(year=year, mature_dates=len(rows),
            **{m: _mean(r[m] for r in rows) for m in METRICS},
            defined_date_counts={m: sum(r[m] is not None for r in rows) for m in METRICS}))
    return dict(per_date=records, by_date=by_date, per_year=years,
        aggregate={m: _mean(r[m] for r in years) for m in METRICS},
        aggregate_by_date={m: _mean(r[m] for r in by_date) for m in METRICS},
        weighting="aggregate: equal annual folds, dates within folds, vintages within dates; aggregate_by_date: equal dates",
        coverage=dict(inference_rows=len(z), mature_rows=len(mature),
            immature_rows=len(z)-len(mature), mature_dates=len(by_date), vintage_queries=len(records),
            quality_exit_cutoff=cutoff_text),
        tie_policy="descending value, ascending ticker; exact winner uses same realized tie rule",
        ndcg_gain="linear continuous target_rank_21; deterministic prediction ties",
        topdecile_regret_definition="signed realized topdecile mean return minus selected return; may be negative")


def paired_compare(candidate, baseline, block_lengths=(3, 1, 6), n_bootstrap=20000, seed=20261004):
    """Noncircular moving CALENDAR-month bootstrap of matched per-date effects.

    All vintage comparisons for a date are averaged together and stay together
    in resampling. Two-sided 95% and one-sided 95% bounds are unadjusted.
    The one-sided 98.75% bound is the nominal Bonferroni alpha .05/four-
    challenger endpoint bound. All are descriptive development diagnostics.
    Positive differences favor candidate except return regret metrics.
    Undefined IC is compared only when both sides are defined and its coverage
    is reported; optional returns require matching availability and hashes.
    """
    if int(n_bootstrap) != n_bootstrap or n_bootstrap < 100 or not block_lengths or any(int(b) != b or b <= 0 for b in block_lengths):
        raise ValueError("Invalid bootstrap replication or block lengths")
    if len(set(block_lengths)) != len(block_lengths):
        raise ValueError("Duplicate block lengths")
    if candidate["coverage"]["quality_exit_cutoff"] != baseline["coverage"]["quality_exit_cutoff"]:
        raise ValueError("Paired quality cutoff mismatch")
    a = pd.DataFrame(candidate["per_date"]).set_index(["signal_date", "vintage"]).sort_index()
    b = pd.DataFrame(baseline["per_date"]).set_index(["signal_date", "vintage"]).sort_index()
    if not a.index.is_unique or not b.index.is_unique or not a.index.equals(b.index):
        raise ValueError("Paired date/vintage coverage mismatch")
    for field in ("n_tickers", "coverage_sha256", "target_sha256"):
        if not a[field].equals(b[field]):
            raise ValueError(f"Paired target/cohort mismatch: {field}")
    if ("return_target_sha256" in a) != ("return_target_sha256" in b):
        raise ValueError("Paired returns availability mismatch")
    if "return_target_sha256" in a and not a.return_target_sha256.equals(b.return_target_sha256):
        raise ValueError("Paired realized return targets differ")
    differences = {}
    for m in METRICS:
        av = pd.to_numeric(a[m], errors="raise")
        bv = pd.to_numeric(b[m], errors="raise")
        differences[m] = av - bv
    delta = pd.DataFrame(differences).groupby(level="signal_date").mean()
    dates = pd.DatetimeIndex(delta.index)
    months = pd.period_range(dates.min().to_period("M"), dates.max().to_period("M"), freq="M")
    month_rows = [np.flatnonzero(dates.to_period("M") == month) for month in months]
    if len(months) < max(block_lengths):
        raise ValueError("History shorter than largest calendar-month block")
    values_matrix = delta.to_numpy(float)
    boot = {}
    for block in block_lengths:
        rng = np.random.default_rng(seed)
        samples = {m: [] for m in METRICS}
        empty_draws = 0
        for _ in range(n_bootstrap):
            starts = rng.integers(0, len(months) - block + 1, size=math.ceil(len(months) / block))
            sampled_months = np.concatenate([start + np.arange(block) for start in starts])[:len(months)]
            ix = np.concatenate([month_rows[j] for j in sampled_months])
            if not len(ix):
                empty_draws += 1
                continue
            draw = values_matrix[ix]
            valid = np.isfinite(draw)
            counts = valid.sum(axis=0)
            sums = np.where(valid, draw, 0.).sum(axis=0)
            for j, m in enumerate(METRICS):
                if counts[j]:
                    samples[m].append(float(sums[j] / counts[j]))
        intervals = {}
        for m in METRICS:
            if not samples[m]:
                intervals[m] = None
            else:
                low, high, lower95, lower9875 = np.quantile(samples[m], [.025, .975, .05, .0125])
                intervals[m] = dict(lower=float(low), upper=float(high),
                    lower95_one_sided=float(lower95),
                    lower98_75_one_sided=float(lower9875), valid_draws=len(samples[m]))
        boot[str(block)] = dict(block_calendar_months=int(block), intervals_95pct=intervals, empty_draws=empty_draws)
    yearly = []
    for year in sorted(set(dates.year)):
        yy = delta.loc[dates.year == year]
        yearly.append(dict(year=int(year), paired_dates=len(yy), **{m: _mean(yy[m]) for m in METRICS}))
    return dict(estimand="candidate minus baseline, equal matched dates; vintages averaged within each date",
        paired_dates=len(delta), paired_vintage_queries=len(a),
        difference={m: _mean(delta[m]) for m in METRICS},
        defined_paired_date_counts={m: int(delta[m].notna().sum()) for m in METRICS},
        per_year=yearly, bootstrap=boot, seed=int(seed), n_bootstrap=int(n_bootstrap),
        primary_block_calendar_months=int(block_lengths[0]),
        bootstrap_scheme="noncircular moving calendar-month blocks; sample length truncated to observed calendar months",
        lower98_75_interpretation="one-sided percentile lower bound at 1.25%; Bonferroni nominal alpha .05 across four preregistered challengers for one endpoint",
        interpretation="development diagnostics; three vintages are not independent markets; no automatic adoption")
