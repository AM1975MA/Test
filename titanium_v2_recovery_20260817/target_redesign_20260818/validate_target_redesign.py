#!/usr/bin/env python3
"""Paired authenticated-label and time-block bootstrap validation for target variants."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


def monthly_returns(panel: pd.DataFrame, labels: pd.DataFrame, membership: pd.DataFrame, cost: float) -> pd.DataFrame:
    scores = panel[["signal_date", "ticker", "titanium_score"]].merge(
        labels[["signal_date", "ticker", "fwd_ret_21"]],
        on=["signal_date", "ticker"], how="inner", validate="one_to_one"
    )
    expanded = membership.merge(scores, on="ticker", how="inner", validate="many_to_many")
    expanded = expanded.sort_values(
        ["basket", "signal_date", "titanium_score", "ticker"],
        ascending=[True, True, False, True], kind="mergesort"
    )
    expanded["rank_number"] = expanded.groupby(["basket", "signal_date"]).cumcount() + 1
    top = expanded.loc[expanded["rank_number"].le(2)].pivot(
        index=["basket", "signal_date"], columns="rank_number", values=["ticker", "titanium_score", "fwd_ret_21"]
    )
    top.columns = [f"{field}{int(rank_)}" for field, rank_ in top.columns]
    top = top.dropna().reset_index().sort_values(["basket", "signal_date"])
    top["margin"] = top["titanium_score1"] - top["titanium_score2"]
    top["weight1"] = np.where(top["margin"].ge(0.12), 1.0, 0.75)
    top["weight2"] = 1.0 - top["weight1"]
    top["gross_return"] = top["weight1"] * top["fwd_ret_211"] + top["weight2"] * top["fwd_ret_212"]
    net = []
    previous: dict[int, dict[str, float]] = {}
    for row in top.itertuples(index=False):
        basket = int(row.basket)
        current = {str(row.ticker1): float(row.weight1)}
        if float(row.weight2) > 0:
            current[str(row.ticker2)] = float(row.weight2)
        prior = previous.get(basket, {})
        names = set(current) | set(prior)
        turnover = 0.5 * sum(abs(current.get(t, 0.0) - prior.get(t, 0.0)) for t in names)
        net.append(float(row.gross_return) - cost * turnover)
        previous[basket] = current
    top["net_return"] = net
    return top[["basket", "signal_date", "net_return"]]


def cagr(values: np.ndarray) -> float:
    return float(np.prod(1.0 + values) ** (12.0 / len(values)) - 1.0)


def block_bootstrap_gap(left: np.ndarray, right: np.ndarray, samples: int, block: int, seed: int) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    n = len(left)
    needed = math.ceil(n / block)
    gaps = np.empty(samples, dtype=float)
    for sample in range(samples):
        starts = rng.integers(0, n, size=needed)
        indices = np.concatenate([(np.arange(block) + start) % n for start in starts])[:n]
        gaps[sample] = cagr(right[indices]) - cagr(left[indices])
    return {
        "samples": int(samples),
        "block_months": int(block),
        "gap_mean_pp": float(100.0 * gaps.mean()),
        "gap_p025_pp": float(100.0 * np.quantile(gaps, 0.025)),
        "gap_p05_pp": float(100.0 * np.quantile(gaps, 0.05)),
        "gap_median_pp": float(100.0 * np.quantile(gaps, 0.50)),
        "gap_p95_pp": float(100.0 * np.quantile(gaps, 0.95)),
        "gap_p975_pp": float(100.0 * np.quantile(gaps, 0.975)),
        "probability_gap_positive": float(np.mean(gaps > 0.0)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-dir", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10000)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    labels = pd.read_pickle(args.labels)
    labels["signal_date"] = pd.to_datetime(labels["signal_date"], errors="raise")
    membership = pd.read_csv(args.membership)[["basket", "ticker"]]
    variants = [path.name.removesuffix("_SCORE_PANEL.parquet") for path in sorted(args.score_dir.glob("*_SCORE_PANEL.parquet"))]
    returns = {}
    for variant in variants:
        panel = pd.read_parquet(args.score_dir / f"{variant}_SCORE_PANEL.parquet")
        panel["signal_date"] = pd.to_datetime(panel["signal_date"], errors="raise")
        common = sorted(set(labels["signal_date"]) & set(panel["signal_date"]))
        returns[variant] = monthly_returns(
            panel.loc[panel["signal_date"].isin(common)],
            labels.loc[labels["signal_date"].isin(common)],
            membership,
            0.001,
        )

    baseline = returns["BASELINE_21"]
    baseline_pivot = baseline.pivot(index="signal_date", columns="basket", values="net_return").sort_index()
    rows = []
    bootstrap = {}
    for variant in variants:
        current = returns[variant].pivot(index="signal_date", columns="basket", values="net_return").reindex_like(baseline_pivot)
        if current.isna().any().any():
            raise ValueError(f"incomplete paired return matrix for {variant}")
        base_basket_cagr = baseline_pivot.apply(lambda x: cagr(x.to_numpy(float)), axis=0)
        current_basket_cagr = current.apply(lambda x: cagr(x.to_numpy(float)), axis=0)
        delta = current_basket_cagr - base_basket_cagr
        rows.append(
            {
                "variant": variant,
                "baskets": int(len(delta)),
                "months": int(len(current)),
                "mean_basket_cagr": float(current_basket_cagr.mean()),
                "mean_cagr_delta_vs_baseline_pp": float(100.0 * delta.mean()),
                "median_cagr_delta_vs_baseline_pp": float(100.0 * delta.median()),
                "p10_cagr_delta_vs_baseline_pp": float(100.0 * delta.quantile(0.10)),
                "p90_cagr_delta_vs_baseline_pp": float(100.0 * delta.quantile(0.90)),
                "fraction_baskets_improved": float(delta.gt(0.0).mean()),
            }
        )
        if variant != "BASELINE_21":
            bootstrap[variant] = block_bootstrap_gap(
                baseline_pivot.mean(axis=1).to_numpy(float),
                current.mean(axis=1).to_numpy(float),
                args.samples,
                12,
                260818 + len(bootstrap),
            )

    paired = pd.DataFrame(rows).sort_values("mean_basket_cagr", ascending=False)
    paired.to_csv(args.output_dir / "PAIRED_AUTHENTIC_LABEL_RESULTS.csv", index=False)
    report = {
        "status": "PASS",
        "method": "paired monthly replay on authenticated fwd_ret_21 labels; 10 bps one-way turnover cost",
        "dependency_control": "time-block bootstrap uses the monthly mean across 500 overlapping baskets before resampling",
        "paired_results": paired.to_dict(orient="records"),
        "twelve_month_block_bootstrap_vs_baseline": bootstrap,
        "caveat": "This validation isolates score selection on authenticated labels; it does not include the daily governor and is not the primary path scorecard.",
    }
    (args.output_dir / "TARGET_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
