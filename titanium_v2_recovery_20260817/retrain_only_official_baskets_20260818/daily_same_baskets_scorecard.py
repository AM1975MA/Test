#!/usr/bin/env python3
"""Daily path comparison using fresh-retrained scores and official baskets."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def summarize(paths: np.ndarray, dates: pd.DatetimeIndex) -> dict[str, float]:
    returns = np.zeros_like(paths, dtype=float)
    returns[:, 1:] = paths[:, 1:] / paths[:, :-1] - 1.0
    compounded = np.cumprod(1.0 + returns, axis=1)
    cagr = compounded[:, -1] ** (252.0 / len(dates)) - 1.0
    drawdown = compounded / np.maximum.accumulate(compounded, axis=1) - 1.0
    std = returns.std(axis=1, ddof=1)
    sharpe = np.sqrt(252.0) * returns.mean(axis=1) / np.where(std > 0.0, std, np.nan)
    frame = pd.DataFrame({"cagr": cagr, "maxdd": drawdown.min(axis=1), "sharpe": sharpe})
    return {
        "baskets": int(len(frame)),
        "cagr_mean": float(frame["cagr"].mean()),
        "cagr_median": float(frame["cagr"].median()),
        "maxdd_mean": float(frame["maxdd"].mean()),
        "sharpe_mean": float(frame["sharpe"].mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v6-module", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--score-panel", type=Path, required=True)
    parser.add_argument("--opportunity-panel", type=Path, required=True)
    parser.add_argument("--clusters", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--frozen-paths", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--final-date", default="2026-07-01")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    final_date = pd.Timestamp(args.final_date)

    v6 = load_module(args.v6_module.resolve(), "daily_v6")
    mats = v6.load_mats(args.data_dir.resolve())
    pred = pd.read_parquet(args.score_panel)
    opp = pd.read_csv(args.opportunity_panel)
    clusters = pd.read_csv(args.clusters)
    cal = pd.read_csv(args.calendar)
    membership = pd.read_csv(args.membership)
    for frame in (pred, opp, clusters, cal):
        frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="raise")
    for column in ("entry_date", "exit_date"):
        cal[column] = pd.to_datetime(cal[column], errors="raise")
    cal = cal.loc[cal["exit_date"].le(final_date) & cal["signal_date"].isin(pred["signal_date"].unique())].copy()
    baskets = [group["ticker"].astype(str).tolist() for _, group in membership.groupby("basket", sort=True)]
    idx, retrained_base, _direct, _router, _active, _margin, _cond, *_ = v6.simulate_all(
        baskets, pred, opp, clusters, mats, cal
    )
    live_summary = summarize(retrained_base, idx)

    frozen = np.load(args.frozen_paths)
    frozen_dates = pd.DatetimeIndex(frozen["dates"])
    mask = np.asarray(frozen_dates <= final_date)
    official_summary = summarize(frozen["BALANCED"][:, mask], frozen_dates[mask])
    gaps = {
        "cagr_mean_pp": 100.0 * (live_summary["cagr_mean"] - official_summary["cagr_mean"]),
        "maxdd_mean_pp": 100.0 * (live_summary["maxdd_mean"] - official_summary["maxdd_mean"]),
        "sharpe_mean": live_summary["sharpe_mean"] - official_summary["sharpe_mean"],
    }
    report = {
        "status": "IDENTICAL" if all(abs(x) <= 1e-12 for x in gaps.values()) else "DIFFERENT",
        "final_date": str(final_date.date()),
        "path_start": str(idx.min().date()),
        "path_end": str(idx.max().date()),
        "daily_observations": int(len(idx)),
        "official_baskets": int(len(baskets)),
        "official_frozen_v2": official_summary,
        "fresh_retrained_on_official_baskets": live_summary,
        "retrained_minus_official": gaps,
        "caveat": "The retrained path uses the current OHLC snapshot; the frozen path uses canonical frozen bytes. Selection membership, dates and strategy rules are fixed.",
    }
    np.savez_compressed(args.output_dir / "RETRAINED_OFFICIAL_BASKETS_DAILY_PATHS.npz", dates=idx.values, BASE=retrained_base)
    (args.output_dir / "DAILY_SAME_BASKETS_SCORECARD.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
