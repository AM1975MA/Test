"""Summarize paired out-of-sample cluster choices and test sampling uncertainty."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

KEYS = ["family", "market", "month"]


def scorecard(picks):
    rows = []
    for (family, market, method), g in picks.groupby(["family", "market", "method"]):
        slices = {
            "ALL": g, "BEFORE_2024": g[g.month < "2024-01"], "FROM_2024": g[g.month >= "2024-01"],
        }
        for label, data in slices.items():
            if data.empty:
                continue
            observations = data[["top2_pairwise", "mom_pairwise"]].dropna()
            rows.append(dict(
                family=family, market=market, method=method, window=label,
                first_month=data.month.min(), last_month=data.month.max(), months=len(data),
                mean_clusters=data.n_clusters.mean(), mean_members=data.n_members.mean(),
                mean_eligible_tickers=data.eligible_tickers.mean(),
                top1_hit=data.top1_hit.mean(), chance_top1=data.chance_top1.mean(),
                top_quartile_hit=data.top_quartile_hit.mean(), chance_quartile=data.chance_top_quartile.mean(),
                rank_ic=data.rank_ic.mean(), mean_top1=data.top1_return.mean(), mean_top2=data.top2_return.mean(),
                top2_minus_pool_pp=(data.top2_return - data.pool).mean() * 100,
                top2_minus_mom_pp=(data.top2_return - data.momtop2).mean() * 100,
                top2_minus_mom21_pp=(data.top2_return - data.mom21top2).mean() * 100,
                endpoint_sensitivity_pp=(observations.top2_pairwise - observations.mom_pairwise).mean() * 100,
                coverage_selected_observed=data.top2_observed.mean(),
                positive_months=int((data.top2_return - data.momtop2 > 1e-10).sum()),
                negative_months=int((data.top2_return - data.momtop2 < -1e-10).sum()),
            ))
    return pd.DataFrame(rows)


def finite_axis_mean(values, axis):
    numerator = np.nansum(values, axis=axis)
    count = np.sum(np.isfinite(values), axis=axis)
    return np.divide(numerator, count, out=np.full_like(numerator, np.nan), where=count > 0)


def inference(picks):
    candidates = picks[picks.method.ne("MOM_BLEND")].copy()
    candidates["delta_mom_pp"] = (candidates.top2_return - candidates.momtop2) * 100
    candidates["delta_mom21_pp"] = (candidates.top2_return - candidates.mom21top2) * 100
    candidates["delta_equal_pool_pp"] = (candidates.top2_return - candidates.pool) * 100
    candidates["delta_top1_chance_pp"] = (candidates.top1_hit - candidates.chance_top1) * 100
    columns = ["delta_mom_pp", "delta_mom21_pp", "delta_equal_pool_pp", "delta_top1_chance_pp", "rank_ic"]
    records = []
    rng = np.random.default_rng(20261124)
    for outcome in columns:
        wide = candidates.pivot(index="month", columns=["family", "market", "method"], values=outcome)
        months = pd.period_range(wide.index.min(), wide.index.max(), freq="M").astype(str)
        wide = wide.reindex(months)
        values = wide.to_numpy()
        length = len(values)
        starts = rng.integers(0, length, size=(5000, int(np.ceil(length / 6)), 1))
        sampled = ((starts + np.arange(6)) % length).reshape(5000, -1)[:, :length]
        boot = finite_axis_mean(values[sampled], axis=1)
        mean = finite_axis_mean(values, axis=0)
        scale = np.nanstd(boot, axis=0, ddof=1)
        informative = scale > 1e-12
        scaled = np.abs((boot[:, informative] - mean[informative]) / scale[informative])
        max_stats = np.nanmax(scaled, axis=1)
        critical = np.nanquantile(max_stats, 0.95)
        lo, hi = np.nanquantile(boot, (0.025, 0.975), axis=0)
        for j, (family, market, method) in enumerate(wide.columns):
            records.append(dict(
                family=family, market=market, method=method, metric=outcome,
                months=int(np.isfinite(values[:, j]).sum()), estimate=mean[j],
                low_nominal=lo[j], high_nominal=hi[j], low_simultaneous=mean[j]-critical*scale[j],
                high_simultaneous=mean[j]+critical*scale[j],
            ))
    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args()
    picks = pd.read_csv(args.results / "MONTHLY_PICKS.csv")
    if (args.results / "NATIVE_MONTHLY_PICKS.csv").is_file():
        picks = pd.concat([picks, pd.read_csv(args.results / "NATIVE_MONTHLY_PICKS.csv")])
    baseline = picks.loc[picks.method.eq("MOM_BLEND"), KEYS + ["top2_return", "top2_pairwise"]]
    baseline = baseline.rename(columns={"top2_return":"momtop2","top2_pairwise":"mom_pairwise"})
    momentum = picks.loc[picks.method.eq("MOM21"), KEYS + ["top2_return"]]
    momentum = momentum.rename(columns={"top2_return": "mom21top2"})
    picks = picks.merge(baseline, on=KEYS, validate="many_to_one")
    picks = picks.merge(momentum, on=KEYS, validate="many_to_one")
    assert not picks.duplicated(KEYS + ["method"]).any()
    info = scorecard(picks)
    uncertainty = inference(picks)
    info.to_csv(args.results / "SIGNAL_SCORECARD.csv", index=False)
    uncertainty.to_csv(args.results / "BOOTSTRAP.csv", index=False)
    fields = ["family", "market", "method", "months", "mean_clusters", "top1_hit",
              "chance_top1", "top_quartile_hit", "rank_ic", "top2_minus_pool_pp", "top2_minus_mom_pp"]
    print(info.query("window == 'ALL'")[fields].round(4).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
