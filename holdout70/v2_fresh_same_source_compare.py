#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANON = HERE / "v2_canonical_same_source_compare.py"
spec = importlib.util.spec_from_file_location("canonical_compare", CANON)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

# The functions below are the canonical V2 source-only build/replay functions.
# This wrapper changes only the acceptance contract: both universes are freshly
# downloaded in the same job, so historical 149 hashes are reported but are not
# used as an acceptance criterion for this controlled apples-to-apples lane.
c.FROZEN149 = Path(os.environ["FRESH_149_ROOT"]).resolve() / "etf_trader_raw"
c.FROZEN70 = Path(os.environ["FRESH_70_ROOT"]).resolve() / "raw_ticker_csv"
c.OUT = HERE / "fresh_same_source_results"


def main() -> None:
    if c.OUT.exists():
        shutil.rmtree(c.OUT)
    c.OUT.mkdir(parents=True)

    u149, u70 = c.load_universe(c.FROZEN149), c.load_universe(c.FROZEN70)
    if len(u149) != 149 or u149.ticker.nunique() != 149:
        raise RuntimeError("fresh original universe is not 149 unique ETFs")
    if len(u70) != 70 or u70.ticker.nunique() != 70:
        raise RuntimeError("fresh holdout universe is not 70 unique ETFs")
    overlap = sorted(set(u149.ticker) & set(u70.ticker))
    if overlap:
        raise RuntimeError(f"holdout70 overlap with original149: {overlap}")

    print("=== FRESH ORIGINAL149 / CANONICAL V2 SOURCE ===", flush=True)
    s149 = c.build_source_only_state("original149", c.FROZEN149)
    r149 = c.replay_full_universe(s149)

    print("=== FRESH HOLDOUT70 / IDENTICAL CANONICAL V2 SOURCE ===", flush=True)
    s70 = c.build_source_only_state("holdout70", c.FROZEN70)
    r70 = c.replay_full_universe(s70)

    m149 = r149["v2_full_universe"]
    m70 = r70["v2_full_universe"]
    hist = c.CANONICAL149
    historical_reference_delta = {
        "cagr_pp": float((m149["cagr"] - hist["cagr"]) * 100),
        "maxdd_pp": float((m149["maxdd"] - hist["maxdd"]) * 100),
        "sharpe": float(m149["sharpe"] - hist["sharpe"]),
    }

    result = {
        "status": "CONTROLLED_FRESH_SAME_SOURCE_149_VS_70_COMPLETE",
        "interpretation_contract": {
            "purpose": "compare original149 and disjoint holdout70 under one fresh Yahoo vintage and one identical canonical V2 source/execution stack",
            "historical_43pct_used_as_input": False,
            "historical_scores_or_paths_consumed": False,
            "same_download_job": True,
            "same_downloader": True,
            "same_price_semantics": True,
            "same_model_source": True,
            "same_execution_source": True,
            "infrastructure_refs_for_holdout70": "SPY/HYG/IEF/BIL/SHV may be supplied from fresh149 only as nonselectable infrastructure; economic top1/top2 and V6 alternates remain restricted to the 70 candidates"
        },
        "historical_canonical149_reference": hist,
        "fresh149_minus_historical_reference": historical_reference_delta,
        "original149": r149,
        "holdout70": r70,
        "delta_70_minus_149": {
            "cagr_pp": float((m70["cagr"] - m149["cagr"]) * 100),
            "maxdd_pp": float((m70["maxdd"] - m149["maxdd"]) * 100),
            "sharpe": float(m70["sharpe"] - m149["sharpe"]),
        },
    }
    (c.OUT / "COMPARISON.json").write_text(json.dumps(result, indent=2) + "\n")
    print("FINAL_FRESH_COMPARISON", json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
