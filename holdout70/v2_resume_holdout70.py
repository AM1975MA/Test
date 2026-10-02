#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent

# Canonical module reads these at import time.
os.environ["FROZEN_149_ROOT"] = os.environ["FRESH_149_ROOT"]
os.environ["FROZEN_HOLDOUT70_ROOT"] = os.environ["FRESH_70_ROOT"]

spec = importlib.util.spec_from_file_location(
    "canonical_compare", HERE / "v2_canonical_same_source_compare.py"
)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

c.FROZEN149 = Path(os.environ["FRESH_149_ROOT"]).resolve() / "etf_trader_raw"
c.FROZEN70 = Path(os.environ["FRESH_70_ROOT"]).resolve() / "raw_ticker_csv"
c.OUT = HERE / "fresh_same_source_results"
PARTIAL = Path(os.environ["PARTIAL_RESULTS_ROOT"]).resolve()

# ddfirst.market_state() canonically requires SPY/HYG/IEF.  They are market
# infrastructure, not economic candidates.  Keep the unmodified productive
# ddfirst source and inject those three reference series only into its market
# state input when the disjoint holdout does not contain them.  Top1/top2,
# MA3 membership and V6 alternates remain restricted to the 70 candidates.
_orig_sync = c.ddfirst.sync_c95_m75_gross
_ref_mats, _, _ = c.load_ticker_csv_folder(c.FROZEN149)


def _sync_c95_with_market_refs(close: pd.DataFrame):
    needed = [t for t in ("SPY", "HYG", "IEF") if t not in close.columns]
    if not needed:
        return _orig_sync(close)
    refs = _ref_mats["Close"][needed].reindex(close.index).ffill().bfill()
    risk_close = pd.concat([close, refs], axis=1)
    return _orig_sync(risk_close)


c.ddfirst.sync_c95_m75_gross = _sync_c95_with_market_refs


def main() -> None:
    if c.OUT.exists():
        shutil.rmtree(c.OUT)
    c.OUT.mkdir(parents=True)

    # Resume exactly from the completed original149 leg of run 37017928047.
    src149 = PARTIAL / "original149"
    if not (src149 / "RESULT.json").exists():
        raise RuntimeError("completed original149 RESULT.json missing from partial artifact")
    shutil.copytree(src149, c.OUT / "original149")
    r149 = json.loads((c.OUT / "original149" / "RESULT.json").read_text())
    if r149.get("candidate_count") != 149 or r149.get("sessions") != 2366:
        raise RuntimeError("partial original149 result has unexpected contract")

    print("RESUME_ORIGINAL149_RESULT", json.dumps(r149["v2_full_universe"]), flush=True)
    print("=== RESUME ONLY HOLDOUT70 / IDENTICAL CANONICAL V2 SOURCE ===", flush=True)

    # This is the only expensive leg that must be rebuilt because the previous
    # artifact did not retain its prediction panel.  All files are written
    # before replay so the workflow can checkpoint them even on downstream fail.
    s70 = c.build_source_only_state("holdout70", c.FROZEN70)
    r70 = c.replay_full_universe(s70)

    m149 = r149["v2_full_universe"]
    m70 = r70["v2_full_universe"]
    hist = c.CANONICAL149
    result = {
        "status": "RESUMED_CONTROLLED_FROZEN_FRESH_SAME_SOURCE_149_VS_70_COMPLETE",
        "resume_contract": {
            "original149_reused_from_run": 37017928047,
            "original149_recomputed": False,
            "holdout70_recomputed": True,
            "raw_reused_from_run": 37017429560,
            "raw_redownloaded": False,
            "holdout70_candidates": 70,
            "market_risk_refs_nonselectable": ["SPY", "HYG", "IEF"],
            "cash_refs_nonselectable": ["BIL", "SHV"],
            "historical_scores_or_paths_consumed": False,
        },
        "historical_canonical149_reference": hist,
        "fresh149_minus_historical_reference": {
            "cagr_pp": float((m149["cagr"] - hist["cagr"]) * 100),
            "maxdd_pp": float((m149["maxdd"] - hist["maxdd"]) * 100),
            "sharpe": float(m149["sharpe"] - hist["sharpe"]),
        },
        "original149": r149,
        "holdout70": r70,
        "delta_70_minus_149": {
            "cagr_pp": float((m70["cagr"] - m149["cagr"]) * 100),
            "maxdd_pp": float((m70["maxdd"] - m149["maxdd"]) * 100),
            "sharpe": float(m70["sharpe"] - m149["sharpe"]),
        },
    }
    (c.OUT / "COMPARISON.json").write_text(json.dumps(result, indent=2) + "\n")
    print("FINAL_RESUMED_COMPARISON", json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
