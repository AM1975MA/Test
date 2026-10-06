#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

import run_nf_v1_c as core


def run_one(raw: Path, compare_script: Path, out: Path):
    os.environ["FROZEN_149_ROOT"] = str(raw.parent)
    os.environ["FROZEN_HOLDOUT70_ROOT"] = str(raw.parent)
    mod = core.load_module(compare_script)
    mod.FROZEN149 = raw
    mod.FROZEN70 = raw
    mod.OUT = out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    uu = mod.load_universe(raw)
    if len(uu) != 149 or uu.ticker.nunique() != 149:
        raise RuntimeError(f"unexpected universe size: {len(uu)}")

    state = mod.build_source_only_state("original149", raw)
    baseline = mod.replay_full_universe(state)
    base_dir = state["base"]
    for fn in ["RESULT.json", "DAILY_LEADERS.csv", "FULL_UNIVERSE_PATH.npz"]:
        p = base_dir / fn
        if p.exists():
            shutil.copyfile(p, base_dir / ("BASELINE_" + fn))

    audit, daily_gain, feedback_stats = core.build_feedback_gain(mod, state)
    audit.to_csv(base_dir / "CONFIDENCE_FEEDBACK_STATE_AUDIT.csv", index=False)

    # Technical wiring fix only: canonical confidence weighting must see the
    # canonical (unmodified) risk state.  Only simulate_arch receives de-risked
    # gross.  Controller formula/parameters are unchanged from preregistration.
    old_risk = mod.stage19.risk_gross_transform
    old_conf = mod.stage19.confidence_weights
    holder = {}

    def feedback_risk(gross):
        canonical = np.asarray(old_risk(gross), dtype=float)
        if len(canonical) != len(daily_gain):
            raise RuntimeError(("daily gain shape mismatch", len(canonical), len(daily_gain)))
        holder["canonical_g"] = canonical.copy()
        out_g = canonical * daily_gain
        if np.any(out_g > canonical + 1e-15):
            raise RuntimeError("feedback increased risk above canonical")
        return out_g

    def canonical_confidence(base, g_risk, agree_models, agree_all, mode):
        canonical = holder.get("canonical_g")
        if canonical is None:
            raise RuntimeError("canonical gross unavailable before confidence weighting")
        return old_conf(base, canonical, agree_models, agree_all, mode)

    mod.stage19.risk_gross_transform = feedback_risk
    mod.stage19.confidence_weights = canonical_confidence
    try:
        feedback = mod.replay_full_universe(state)
    finally:
        mod.stage19.risk_gross_transform = old_risk
        mod.stage19.confidence_weights = old_conf

    for fn in ["RESULT.json", "DAILY_LEADERS.csv", "FULL_UNIVERSE_PATH.npz"]:
        p = base_dir / fn
        if p.exists():
            shutil.copyfile(p, base_dir / ("FEEDBACK_" + fn))

    b_npz = np.load(base_dir / "BASELINE_FULL_UNIVERSE_PATH.npz")
    f_npz = np.load(base_dir / "FEEDBACK_FULL_UNIVERSE_PATH.npz")
    identity = {
        "d1_exact": bool(np.array_equal(b_npz["d1"], f_npz["d1"])),
        "d2_exact": bool(np.array_equal(b_npz["d2"], f_npz["d2"])),
        "weight1_exact": bool(np.array_equal(b_npz["weight1"], f_npz["weight1"])),
        "margin_exact": bool(np.array_equal(b_npz["margin"], f_npz["margin"])),
    }
    leaders_b = pd.read_csv(base_dir / "BASELINE_DAILY_LEADERS.csv")
    leaders_f = pd.read_csv(base_dir / "FEEDBACK_DAILY_LEADERS.csv")
    identity["top1_exact"] = bool(leaders_b.top1.equals(leaders_f.top1))
    identity["top2_exact"] = bool(leaders_b.top2.equals(leaders_f.top2))
    identity["PASS"] = bool(all(identity.values()))
    if not identity["PASS"]:
        raise RuntimeError(("decision identity failed", identity))

    b = baseline["v2_full_universe"]
    f = feedback["v2_full_universe"]
    summary = {
        "status": "NF_V1_C_COMPLETE",
        "experiment": "NF_V1_C_CONFIDENCE_FEEDBACK",
        "technical_wiring": "canonical confidence sees canonical gross; only simulation gross is feedback-scaled",
        "controller": {
            "alpha": core.ALPHA,
            "min_matured_dates": core.MIN_MATURED_DATES,
            "null_pairwise_accuracy": core.NULL_PAIRWISE_ACCURACY,
            "gain_rule": "gain=min(1,max(0,2*q_ewma))",
            "ranking_modified": False,
            "risk_can_only_decrease": True,
        },
        "feedback_state": feedback_stats,
        "decision_identity": identity,
        "baseline": b,
        "feedback": f,
        "economic_delta": {
            "cagr_pp": 100.0 * (f["cagr"] - b["cagr"]),
            "maxdd_pp": 100.0 * (f["maxdd"] - b["maxdd"]),
            "sharpe": f["sharpe"] - b["sharpe"],
            "turnover": f["annualized_turnover"] - b["annualized_turnover"],
        },
    }
    (base_dir / "NF_V1_C_RESULT.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--compare-script", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    run_one(Path(args.raw).resolve(), Path(args.compare_script).resolve(), Path(args.out).resolve())


if __name__ == "__main__":
    main()
