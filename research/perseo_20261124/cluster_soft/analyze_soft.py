"""Quantify paired net performance, switch frequency, and concentration."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def compare_accounts(summary):
    metrics = ["active_cagr", "active_maxdd", "full_cagr", "full_maxdd", "orders", "cost_currency"]
    base = summary.loc[summary["mode"].eq("U27"), ["bps", "lag", *metrics]]
    table = summary.merge(base, on=["bps", "lag"], suffixes=("", "_u27"), validate="many_to_one")
    for pct in metrics[:4]:
        table[f"{pct}_delta_pp"] = 100 * (table[pct] - table[f"{pct}_u27"])
    return table


def decision_metrics(choices):
    rows = []
    for name, frame in choices.groupby("mode"):
        swapped = frame[frame.changed_legs.gt(0)]
        rows.append(dict(
            mode=name, months=len(frame), changed_months=len(swapped),
            replaced_legs=frame.changed_legs.sum(),
            pair_same_cluster=(frame.cluster_a == frame.cluster_b).mean(),
            outside_top_cluster_legs=frame.outside_best.sum(),
            average_gross_delta_pp=100 * frame.gross_delta.mean(),
            gross_delta_pp_when_swapped=100 * swapped.gross_delta.mean(),
            swapped_positive=int(swapped.gross_delta.gt(0).sum()),
            swapped_negative=int(swapped.gross_delta.lt(0).sum()),
        ))
    return pd.DataFrame(rows)


def bootstrap(monthly):
    table = monthly.query("bps == 15 and lag == 0").pivot(index="month", columns="mode", values="ret")
    assert not table.isna().any().any() and len(table) == 57
    baseline = np.log1p(table.pop("U27"))
    spread = np.log1p(table).sub(baseline, axis=0)
    rng = np.random.default_rng(20261124)
    n = len(table)
    draws = rng.integers(0, n, size=(5000, int(np.ceil(n / 6)), 1))
    idx = ((draws + np.arange(6)) % n).reshape(5000, -1)[:, :n]
    vals = spread.to_numpy()
    estimate = vals.mean(axis=0) * 1200
    samples = vals[idx].mean(axis=1) * 1200
    std = samples.std(axis=0, ddof=1)
    valid = std > 1e-12
    max_t = np.abs((samples[:, valid] - estimate[valid]) / std[valid]).max(axis=1)
    critical = np.quantile(max_t, 0.95)
    lo, hi = np.quantile(samples, [0.025, 0.975], axis=0)
    diagnostics = []
    for j, mode in enumerate(table):
        effects = vals[:, j]
        largest = np.argsort(np.abs(effects))[-2:]
        diagnostics.append(dict(
            mode=mode, pp_log_ann=estimate[j], low_nominal=lo[j], high_nominal=hi[j],
            low_simultaneous=estimate[j]-critical*std[j], high_simultaneous=estimate[j]+critical*std[j],
            months_up_5bp=int((effects > 0.0005).sum()), months_down_5bp=int((effects < -0.0005).sum()),
            largest_abs_month=table.index[largest[-1]], second_abs_month=table.index[largest[0]],
            pp_log_ann_ex_top2=np.delete(effects, largest).mean() * 1200,
        ))
    return pd.DataFrame(diagnostics), spread.stack().rename("log_delta").reset_index()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, default=HERE / "results")
    args = p.parse_args()
    root = args.results
    summary = compare_accounts(pd.read_csv(root / "SUMMARY.csv"))
    decisions = decision_metrics(pd.read_csv(root / "CHOICES.csv"))
    confidence, attribution = bootstrap(pd.read_csv(root / "MONTHLY.csv"))
    summary.to_csv(root / "COMPARISON.csv", index=False)
    decisions.to_csv(root / "SWITCH_SUMMARY.csv", index=False)
    confidence.to_csv(root / "BOOTSTRAP.csv", index=False)
    attribution.to_csv(root / "MONTHLY_LOG_DELTAS.csv", index=False)
    names = ["mode", "active_cagr", "active_maxdd", "active_cagr_delta_pp", "orders"]
    print(summary.query("bps == 15 and lag == 0")[names].round(4).to_string(index=False))
    print(decisions.round(4).to_string(index=False))
    print(confidence.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
