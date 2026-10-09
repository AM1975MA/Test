"""One fixed XGB75 / Ridge25 within-query percentile blend; no retraining."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/etf_trader_v2/src")]

from compact21_predictive_v2.summarize import load_variant, stability_by_date, normalized_numeric
from compact21_predictive_v2.metrics import evaluate, paired_compare
from compact21_blockbag_v1.summarize import decision_gates
from compact21_semidev_v1.view import sha

LINE = "COMPACT21_XGB75_RIDGE25_V1"
KEYS = ["signal_date", "ticker"]
ORDER = ["vintage", *KEYS]
WEIGHT_XGB = .75
WEIGHT_RIDGE = .25
N_MONTHS = 114


def blend_percentiles(base, ridge):
    if not set(ORDER + ["pred"]).issubset(base) or not set(ORDER + ["pred"]).issubset(ridge):
        raise ValueError("Incomplete frozen score vectors")
    b = base.sort_values(ORDER).reset_index(drop=True).copy()
    r = ridge.sort_values(ORDER).reset_index(drop=True).copy()
    if len(b) != len(r) or b.duplicated(ORDER).any() or r.duplicated(ORDER).any():
        raise ValueError("Different/duplicate score coverage")
    pd.testing.assert_frame_equal(b[ORDER], r[ORDER], check_exact=True)
    # Quality outcome fields must be identical, including exit-date maturity and returns.
    pd.testing.assert_frame_equal(b.drop(columns="pred"), r.drop(columns="pred"), check_exact=True)
    if not np.isfinite(b.pred.to_numpy(float)).all() or not np.isfinite(r.pred.to_numpy(float)).all():
        raise ValueError("Nonfinite original source scores")
    qb = b.groupby(["vintage", "signal_date"], sort=False).pred.rank(method="average", pct=True)
    qr = r.groupby(["vintage", "signal_date"], sort=False).pred.rank(method="average", pct=True)
    b["pred"] = WEIGHT_XGB * qb.to_numpy(dtype=np.float64) + WEIGHT_RIDGE * qr.to_numpy(dtype=np.float64)
    if not np.isfinite(b.pred).all():
        raise ValueError("Nonfinite hybrid score")
    return b


def run(reference):
    base=load_variant(reference, "BASE")
    ridge=load_variant(reference, "RIDGE")
    for field in ("input_sha256", "input_contract", "sources", "preregistration_sha256", "environment"):
        if base["result"][field] != ridge["result"][field]:
            raise ValueError("Original reference contracts differ: " + field)
    if normalized_numeric(base["result"]["numeric_contract"]) != normalized_numeric(ridge["result"]["numeric_contract"]):
        raise ValueError("Original numeric profile differs")
    for name,r in (("BASE",base),("RIDGE",ridge)):
        if r["result"]["LEGACY_PARITY_PASS"] is not True or r["result"]["ALL_DETERMINISM_PASS"] is not True:
            raise ValueError("Original predictive refit/legacy evidence failed: " + name)
    native=blend_percentiles(base["native"],ridge["native"])
    common=blend_percentiles(base["common"],ridge["common"])
    if common.signal_date.nunique()!=N_MONTHS or native.signal_date.nunique()!=N_MONTHS:
        raise ValueError("Original 114-month coverage lost")
    tested=evaluate(native,quality_exit_cutoff="2026-07-01",
                    expected_keys=base["native"][ORDER])
    paired=paired_compare(tested,base["eval"])
    sbc=stability_by_date(base["common"])
    sbn=stability_by_date(base["native"])
    sc=stability_by_date(common)
    sn=stability_by_date(native)
    gates=decision_gates(tested,base["eval"],paired,sc,sn,sbc,sbn,controls=True)
    if len({x["signal_date"] for x in tested["per_date"]}) != 113:
        raise ValueError("Missing mature 113-month outcome coverage")
    if base["result"]["input_sha256"] != ridge["result"]["input_sha256"]:
        raise ValueError("Not common raw snapshot identities")
    result={"status":LINE+"_SUMMARY_COMPLETE","variant":"XGB75_RIDGE25",
            "source_runs":[37229180477],"baseline_id":base["sha256"],
            "ridge_id":ridge["sha256"],
            "input_sha256":base["result"]["input_sha256"],
            "numeric_contract":normalized_numeric(base["result"]["numeric_contract"]),
            "input_contract":base["result"]["input_contract"],
            "original_production_adoption":False,
            "production_adoption":False,"portfolio_evaluation":False,
            "negative_feedback_changed":False,
            "weights":{"XGB":WEIGHT_XGB,"RIDGE":WEIGHT_RIDGE},
            "predictive":tested,
            "paired_vs_BASE":paired,
            "base_quality":base["eval"]["aggregate_by_date"],
            "candidate_quality":tested["aggregate_by_date"],
            "baseline_stability":{"common":sbc,"native":sbn},
            "candidate_stability":{"common":sc,"native":sn},
            "gates":gates}
    return result,native,common


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reference",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("Fresh destination required")
    args.out.mkdir(parents=True, exist_ok=True)
    r,n,c=run(args.reference)
    n.to_parquet(args.out/"NATIVE_PREDICTIONS.parquet",index=False)
    c.to_parquet(args.out/"COMMON_PREDICTIONS.parquet",index=False)
    r["evidence_sha256"]={
        "protocol":sha(ROOT/"compact21_xgb_ridge_hybrid_v1/PREREGISTRATION.md"),
        "code":sha(ROOT/"compact21_xgb_ridge_hybrid_v1/evaluate.py"),
        "native":sha(args.out/"NATIVE_PREDICTIONS.parquet"),
        "common":sha(args.out/"COMMON_PREDICTIONS.parquet")}
    (args.out/"SUMMARY.json").write_text(json.dumps(r,indent=2,allow_nan=False)+"\n")
    g=r["gates"]
    sm=r["candidate_stability"]
    sb=r["baseline_stability"]
    q=r["candidate_quality"];b=r["base_quality"]
    lines=["# Frozen XGB75-Ridge25 experimental result","",
        "Single prespecified blend of existing models; 3 synchronized data vintages and 114 monthly dates. This is NOT a full-strategy CAGR.",
        "",
        "| Metric | BASE | 75/25 hybrid |","|---|---:|---:|",
        f"| Common rank-MAD | {sb['common']['mean']['rank_mad']:.6f} | {sm['common']['mean']['rank_mad']:.6f} |",
        f"| Native Top1 disagreement | {sb['native']['mean']['top1_disagreement']:.2%} | {sm['native']['mean']['top1_disagreement']:.2%} |",
        f"| Mature Top1 realized percentile | {b['top1_realized_percentile']:.6f} | {q['top1_realized_percentile']:.6f} |",
        f"| Precision@5 | {b['top5_overlap']:.6f} | {q['top5_overlap']:.6f} |",
        f"| NDCG@5 | {b['ndcg5']:.6f} | {q['ndcg5']:.6f} |",
        "",
        f"- Pilot stability pass: **{g['STABILITY_PILOT_PASS']}**",
        f"- Quality conservation pass: **{g['QUALITY_CONSERVATION_PASS']}**",
        f"- Near operational repeatability pass: **{g['NEAR_REPEATABILITY_PASS']}**",
        f"- Stable and conserved quality: **{g['STABLE_WITH_CONSERVED_QUALITY']}**",
        "- Full strategy CAGR: **NOT COMPUTED**, requires stability and quality gates first.",
        "- Production adoption: **FALSE**. No change to Etf_trader.",
        "",
        "## Detailed gate evidence","", "```json",json.dumps(g,indent=2),"```"]
    (args.out/"SUMMARY.md").write_text("\n".join(lines)+"\n")
    print((args.out/"SUMMARY.md").read_text(),flush=True)


if __name__=="__main__":
    main()
