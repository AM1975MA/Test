#!/usr/bin/env python3
"""Repair live-availability stability metrics to the 113 official evaluation dates."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


VARIANTS = ("BASELINE_21", "MULTI_45_35_20", "CONSENSUS_MULTI")


def load_runner(path: Path):
    spec = importlib.util.spec_from_file_location("robust_runner", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reference-score-dir", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    args = parser.parse_args()
    runner = load_runner(args.runner.resolve())
    membership = pd.read_csv(args.membership)[["basket", "ticker"]]
    membership["ticker"] = membership["ticker"].astype(str).str.upper().str.strip()
    calendar = pd.read_csv(args.calendar)
    calendar["signal_date"] = pd.to_datetime(calendar["signal_date"], errors="raise")
    calendar["exit_date"] = pd.to_datetime(calendar["exit_date"], errors="raise")
    official_dates = set(calendar.loc[calendar["exit_date"].le(pd.Timestamp("2026-07-01")), "signal_date"])
    references = {}
    for variant in VARIANTS:
        panel = pd.read_parquet(args.reference_score_dir / f"{variant}_SCORE_PANEL.parquet")
        panel["signal_date"] = pd.to_datetime(panel["signal_date"], errors="raise")
        panel["ticker"] = panel["ticker"].astype(str).str.upper().str.strip()
        references[variant] = panel.loc[panel["signal_date"].isin(official_dates)].copy()

    repaired = 0
    for scenario_dir in sorted(args.output_dir.glob("LIVE_MISSING_*")):
        spec = json.loads((scenario_dir / "SCENARIO_SPEC.json").read_text(encoding="utf-8"))
        dropped = set(
            runner.stable_ticker_sample(
                sorted(membership["ticker"].unique()),
                float(spec["inference_ticker_dropout"]),
                int(spec["scenario_seed"]),
            )
        )
        summary_path = scenario_dir / "SCENARIO_SUMMARY.csv"
        summary = pd.read_csv(summary_path)
        for variant in VARIANTS:
            reference = references[variant]
            stress = reference.loc[~reference["ticker"].isin(dropped)].copy()
            stability = runner.selection_stability(stress, reference, membership)
            mask = summary["variant"].eq(variant)
            for key, value in stability.items():
                summary.loc[mask, key] = value
        summary.to_csv(summary_path, index=False)
        repaired += 1
    print(json.dumps({"status": "PASS", "scenarios_repaired": repaired, "official_signal_dates": len(official_dates)}))


if __name__ == "__main__":
    main()
