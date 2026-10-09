"""Independent aggregation and fixed stability/quality gates for clean-data XGB."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src")]
from compact21_semidev_v1.view import sha
from compact21_predictive_v2.summarize import load_variant, normalized_numeric, stability_by_date
from compact21_predictive_v2.metrics import evaluate, paired_compare
from compact21_blockbag_v1.summarize import decision_gates

LINE="COMPACT21_CLEAN_DOWNVOL_TRAINING_V1"
KEYS=["signal_date","ticker"]
YEARS=tuple(range(2017,2027))


def summarize(years,refdir):
    base=load_variant(refdir,"BASE")
    br=base["result"]
    fingerprints=None
    natives=[];commons=[]
    for year in YEARS:
        root=years/f"cleaned-model-{year}"
        result=json.loads((root/"RESULT.json").read_text())
        if (result.get("line")!=LINE or result.get("status")!=LINE+"_COMPLETE"
           or result.get("year")!=year
           or any(result.get(name) is not False for name in
                 ("production_adoption","portfolio_evaluation","negative_feedback_changed"))
           or result.get("repeated_fit_exact") is not True
           or result.get("eligibility_preserved") is not True
           or set(result.get("fit_audits",{}))!={"1","2","3"}
           or not all(z["refit_byte_exact"] and z["original_labels_and_groups_exact"]
                      for z in result["fit_audits"].values())):
            raise ValueError(f"Annual cleaned model failure: {year}")
        expected=(result["source_sha256"],result["raw_original_sha256"],
            result["preregistration_sha256"],result["source_impl_sha256"],
            result["reference_baseline_sha256"],normalized_numeric(result["numeric_contract"]))
        if fingerprints is None:fingerprints=expected
        elif fingerprints!=expected:raise ValueError("Mixed cleaned input/source/numeric contracts across years")
        if result["reference_baseline_sha256"] != sha(refdir/"RESULT.json"):
            raise ValueError("Original BASE reference changed")
        for filename,digest in result["prediction_sha256"].items():
            if sha(root/filename)!=digest:
                raise ValueError("Prediction artifact corrupt")
        for attr,destination in (("NATIVE_PREDICTIONS.parquet",natives),("COMMON_PREDICTIONS.parquet",commons)):
            df=pd.read_parquet(root/attr)
            if df.signal_date.dt.year.nunique()!=1 or df.signal_date.dt.year.iloc[0]!=year:
                raise ValueError("Annual prediction year mismatch")
            if df.duplicated(["vintage"]+KEYS).any():
                raise ValueError("Duplicate test keys")
            destination.append(df)
    n=pd.concat(natives,ignore_index=True).sort_values(["vintage"]+KEYS).reset_index(drop=True)
    c=pd.concat(commons,ignore_index=True).sort_values(["vintage"]+KEYS).reset_index(drop=True)
    for tag,actual,old in (("native",n,base["native"]),("common",c,base["common"])):
        if actual.signal_date.nunique()!=114 or actual.vintage.nunique()!=3:
            raise ValueError("Original 114-month or vintage support missing")
        if len(actual)!=len(old):
            raise ValueError("Row coverage changed")
        pd.testing.assert_frame_equal(actual.drop(columns="pred"),
                                     old.drop(columns="pred"),check_exact=True)
        if not np.isfinite(actual.pred.to_numpy(dtype=float)).all():
            raise ValueError("Nonfinite cleaned model output")
    ev=evaluate(n,quality_exit_cutoff="2026-07-01",expected_keys=base["native"][["vintage"]+KEYS])
    paired=paired_compare(ev,base["eval"])
    candidate_common=stability_by_date(c);candidate_native=stability_by_date(n)
    base_common=stability_by_date(base["common"]);base_native=stability_by_date(base["native"])
    gates=decision_gates(ev,base["eval"],paired,candidate_common,candidate_native,
                         base_common,base_native,controls=True)
    return {"status":LINE+"_SUMMARY_COMPLETE",
          "sources":["Original149 frozen raw from run 37121749852",
                     "Original TI from 37150436612",
                     "Cleanup preparation run 37936573578",
                     "Original predictive BASE run 37229180477"],
          "cleaned_input_sha256":fingerprints[0],
          "original_input_sha256":fingerprints[1],
          "preregistration_sha256":fingerprints[2],
          "transformation_sha256":fingerprints[3],
          "baseline_reference_sha256":fingerprints[4],
          "years":list(YEARS),"months":114,
          "original_baseline_quality":base["eval"]["aggregate_by_date"],
          "cleaned_candidate_quality":ev["aggregate_by_date"],
          "paired_quality_vs_original_BASE":paired,
          "original_baseline_stability":{"common":base_common,"native":base_native},
          "cleaned_candidate_stability":{"common":candidate_common,"native":candidate_native},
          "gates":gates,
          "economic_replay_authorized":bool(gates["STABILITY_PILOT_PASS"] and gates["QUALITY_CONSERVATION_PASS"]),
          "actual_cagr_computed":False,
          "production_adoption":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--years",type=Path,required=True)
    p.add_argument("--reference",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("Fresh summary directory")
    args.out.mkdir(parents=True,exist_ok=True)
    s=summarize(args.years,args.reference)
    (args.out/"SUMMARY.json").write_text(json.dumps(s,indent=2,allow_nan=False)+"\n")
    g=s["gates"]
    b=s["original_baseline_stability"];c=s["cleaned_candidate_stability"]
    q=s["cleaned_candidate_quality"];o=s["original_baseline_quality"]
    lines=["# Single-treatment cleaned data comparison: three Original149 acquisitions","",
       "Only the 9 features of the downvol21/63/126 family changed; model XGB, labels and cohort are frozen.",
       "",
       "| Metric | Original BASE | Cleaned-input BASE |","|---|---:|---:|",
       f"| Common Rank-MAD | {b['common']['mean']['rank_mad']:.6f} | {c['common']['mean']['rank_mad']:.6f} |",
       f"| Native Top1 disagreement | {b['native']['mean']['top1_disagreement']:.2%} | {c['native']['mean']['top1_disagreement']:.2%} |",
       f"| Realized mature Top1 percentile | {o['top1_realized_percentile']:.6f} | {q['top1_realized_percentile']:.6f} |",
       f"| Mature realized Precision@5 | {o['top5_overlap']:.6f} | {q['top5_overlap']:.6f} |",
       f"| Mature NDCG@5 | {o['ndcg5']:.6f} | {q['ndcg5']:.6f} |",
       "",
       f"- Stability pilot pass: **{g['STABILITY_PILOT_PASS']}**",
       f"- Quality conservation pass: **{g['QUALITY_CONSERVATION_PASS']}**",
       f"- Near-repeatability pass: **{g['NEAR_REPEATABILITY_PASS']}**",
       f"- Full economic replay authorized by locked gates: **{s['economic_replay_authorized']}**",
       "- CAGR: **NOT YET COMPUTED**. Never infer CAGR from this ranker study.",
       "- No production adoption; original Etf_trader unchanged.","",
       "## Pairwise common-input rank disagreement",""]
    for key,v in c["common"]["pairs"].items():
        old=b["common"]["pairs"][key]["mean"]["rank_mad"]
        lines.append(f"- {key}: cleaned {v['mean']['rank_mad']:.6f}; BASE {old:.6f}")
    lines += ["","## Pairwise native Top1 decision disagreement",""]
    for key,v in c["native"]["pairs"].items():
        old=b["native"]["pairs"][key]["mean"]["top1_disagreement"]
        lines.append(f"- {key}: cleaned {v['mean']['top1_disagreement']:.2%}; BASE {old:.2%}")
    lines += ["","## Full gate details","", "```json",json.dumps(g,indent=2),"```"]
    (args.out/"SUMMARY.md").write_text("\n".join(lines)+"\n")
    print((args.out/"SUMMARY.md").read_text(),flush=True)

if __name__=="__main__":
    main()
