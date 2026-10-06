#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
STAGE19_PATH = HERE.parent / "source" / "stage19_architecture.py"

_campaign_root = os.environ.get("ETF_TRAINER_V2_CAMPAIGN_ROOT")
if _campaign_root:
    source_root = Path(_campaign_root).resolve() / "src"
else:
    source_root = REPO_ROOT / "src"
if not source_root.is_dir():
    raise FileNotFoundError(f"source root missing: {source_root}")
sys.path.insert(0, str(source_root))

from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.source_only.baskets import (
    BASKET_COUNT,
    BASKET_SEED,
    PER_CATEGORY,
    build_canonical_baskets,
)
from etf_trader.ma3 import producer


def load_stage19():
    spec = importlib.util.spec_from_file_location("v2_stage19_preflight", STAGE19_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load frozen Stage19 source")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def validate_membership(
    membership: pd.DataFrame,
    tickers: list[str],
    *,
    expected_baskets: int = BASKET_COUNT,
    expected_size: int = 24,
) -> dict[str, object]:
    required = {"basket", "ticker"}
    if not required.issubset(membership.columns):
        raise ValueError(
            f"membership missing columns: {sorted(required - set(membership.columns))}"
        )

    z = membership[["basket", "ticker"]].copy()
    z["ticker"] = z["ticker"].astype(str)
    ids = sorted(map(int, z["basket"].unique()))
    if ids != list(range(expected_baskets)):
        raise ValueError("basket ids are not the exact contiguous expected range")

    sizes = z.groupby("basket").size()
    if not sizes.eq(expected_size).all():
        raise ValueError(
            f"basket size mismatch: min={int(sizes.min())} "
            f"max={int(sizes.max())} expected={expected_size}"
        )

    duplicate_rows = int(z.duplicated(["basket", "ticker"]).sum())
    if duplicate_rows:
        raise ValueError(f"duplicate basket/ticker rows: {duplicate_rows}")

    unknown = sorted(set(z["ticker"]) - set(map(str, tickers)))
    if unknown:
        raise ValueError(f"unknown productive ticker(s): {unknown[:10]}")

    return {
        "status": "PASS",
        "baskets": expected_baskets,
        "rows": int(len(z)),
        "size_each": expected_size,
        "duplicates": 0,
        "unknown_tickers": 0,
    }


def validate_score(
    score: np.ndarray,
    calendar: pd.DataFrame,
    tickers: list[str],
    basket_matrix: np.ndarray,
    basket_valid: np.ndarray,
) -> dict[str, object]:
    expected_shape = (len(calendar), len(tickers))
    if score.shape != expected_shape:
        raise ValueError(f"score shape {score.shape} != {expected_shape}")

    bad = np.argwhere(~np.isfinite(score))
    if len(bad):
        raise ValueError(
            f"non-finite productive score cells: {len(bad)} "
            f"first={bad[0].tolist()}"
        )

    for m in range(score.shape[0]):
        S = np.where(
            basket_valid,
            score[m, basket_matrix],
            -np.inf,
        )
        valid_values = S[basket_valid]
        if (~np.isfinite(valid_values)).any():
            raise ValueError(f"non-finite basket score at signal row {m}")

        ordered = np.sort(S, axis=1)[:, ::-1]
        if ordered.shape[1] < 3:
            raise ValueError("basket width <3; cannot audit top2 cutoff")

        top1_tie = ordered[:, 0] == ordered[:, 1]
        top2_cutoff_tie = ordered[:, 1] == ordered[:, 2]
        if top1_tie.any() or top2_cutoff_tie.any():
            b = int(np.where(top1_tie | top2_cutoff_tie)[0][0])
            raise ValueError(
                f"ambiguous exact selection tie at signal row {m}, basket {b}, "
                f"top={ordered[b, :3].tolist()}"
            )

    return {
        "status": "PASS",
        "shape": list(score.shape),
        "nonfinite": 0,
        "top1_ties": 0,
        "top2_cutoff_ties": 0,
    }


def validate_entry_execution(
    mats: dict[str, pd.DataFrame],
    calendar: pd.DataFrame,
    tickers: list[str],
) -> dict[str, object]:
    checked = 0
    for field in ("Open", "Low", "Close"):
        if field not in mats:
            raise KeyError(f"raw matrix missing {field}")

    aligned = {
        field: mats[field].reindex(columns=tickers)
        for field in ("Open", "Low", "Close")
    }

    for d in pd.to_datetime(calendar["entry_date"].dropna().unique()):
        if d not in aligned["Open"].index:
            raise ValueError(f"entry date absent from raw calendar: {d}")

        for field, frame in aligned.items():
            row = frame.loc[d].to_numpy(float)
            if not np.isfinite(row).all():
                raise ValueError(
                    f"{field} has non-finite entry cells on {d.date()}: "
                    f"{int((~np.isfinite(row)).sum())}"
                )
            if (row <= 0).any():
                raise ValueError(f"{field} has non-positive entry cells on {d.date()}")
        checked += 1

    return {
        "status": "PASS",
        "entry_dates_checked": checked,
        "tickers_checked": len(tickers),
    }


def run_preflight(
    *,
    raw_dir: Path,
    titanium_path: Path,
    predictions_path: Path,
) -> dict[str, object]:
    raw_dir = Path(raw_dir).resolve()
    titanium_path = Path(titanium_path).resolve()
    predictions_path = Path(predictions_path).resolve()

    mats, _, _ = load_ticker_csv_folder(raw_dir)
    tickers = list(map(str, mats["Open"].columns))

    titanium = pd.read_csv(
        titanium_path,
        parse_dates=["signal_date", "entry_date", "exit_date"],
    )
    calendar = (
        titanium[["signal_date", "entry_date", "exit_date"]]
        .drop_duplicates()
        .sort_values("signal_date")
        .reset_index(drop=True)
    )
    predictions = pd.read_csv(predictions_path, parse_dates=["signal_date"])

    stage19 = load_stage19()
    score = stage19.score_matrix(predictions, calendar, tickers)

    universe = pd.read_csv(raw_dir / "universe.csv")
    membership = build_canonical_baskets(
        universe,
        tickers,
        seed=BASKET_SEED,
        basket_count=BASKET_COUNT,
        per_category=PER_CATEGORY,
    )

    membership_report = validate_membership(membership, tickers)
    BM, BOK = producer.basket_arrays(
        membership,
        tickers,
        n_baskets=BASKET_COUNT,
    )
    score_report = validate_score(score, calendar, tickers, BM, BOK)
    execution_report = validate_entry_execution(mats, calendar, tickers)

    return {
        "status": "PASS",
        "guard": "ETF_TRAINER_V2_FAIL_CLOSED_PREFLIGHT_V1",
        "membership": membership_report,
        "scores": score_report,
        "execution": execution_report,
        "candidate_metrics_opened": False,
        "strategy_decisions_changed": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--titanium", required=True)
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    report = run_preflight(
        raw_dir=Path(args.raw_dir),
        titanium_path=Path(args.titanium),
        predictions_path=Path(args.predictions),
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
