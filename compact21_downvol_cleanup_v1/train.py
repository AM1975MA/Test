"""Annual frozen source-cleaned Compact21 fit: unchanged canonical XGB."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src")]
from compact21_semidev_v1.run import select_original_frames, FROZEN_TI
from compact21_semidev_v1.view import sha
from compact21_learner_swap_v1 import learners
from compact21_learner_swap_v1.run_benchmark import evaluation_coverage, compare_native
from compact21_feature_ablation_v1.run import frozen_reference
from compact21_predictive_v2.run import numerical_gate, predictions_frame
from ranker_stability_v1.run_ranker_benchmark_full import load, stability, quality

LINE="COMPACT21_CLEAN_DOWNVOL_TRAINING_V1"
KEYS=["signal_date","ticker"]
PAIRS=((1,2),(1,3),(2,3))


def prep_contract(paths):
    manifests={}
    frames={}
    for i in (1,2,3):
        root=paths[i]
        m=json.loads((root/"SOURCE_PROVENANCE.json").read_text())
        if (m.get("status")!="CLEANED_SOURCE_PANEL_COMPLETE" or m.get("acquisition")!=i
            or m.get("original_ti_sha256")!=FROZEN_TI[str(i)]
            or m.get("cleaned_ti_sha256")!=sha(root/"TI_COMPACT.parquet")
            or m.get("original_eligibility_preserved") is not True
            or m.get("all_non_downvol_columns_byte_exact") is not True):
            raise ValueError("Unverified cleaned source "+str(i))
        manifests[i]=m
        frames[i]=load(root)
    if len({m["cleaning_source_sha256"] for m in manifests.values()})!=1:
        raise ValueError("One frozen cleaning source must be used independently")
    if len({m["preregistration_sha256"] for m in manifests.values()})!=1:
        raise ValueError("Different prospective protocols")
    return manifests,frames


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--year",type=int,choices=range(2017,2027),required=True)
    for name in ("r1","r2","r3","reference","out"):
        ap.add_argument("--"+name,type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists() and any(a.out.iterdir()):
        raise ValueError("Annual output must be fresh")
    a.out.mkdir(parents=True,exist_ok=True)
    numeric=numerical_gate()
    paths={i:getattr(a,f"r{i}") for i in (1,2,3)}
    manifests,frames=prep_contract(paths)
    baseline,sources,ref_native,ref_common=frozen_reference(a.reference,FROZEN_TI,numeric)
    if not baseline.get("ALL_DETERMINISM_PASS") or not baseline.get("LEGACY_PARITY_PASS"):
        raise ValueError("Original retained BASE parity unavailable")
    trains,tests,common=select_original_frames(frames,a.year)
    source_coverage=evaluation_coverage(trains,tests,common)
    old=baseline["per_year"][str(a.year)]
    if source_coverage!=old["evaluation_coverage"]:
        raise ValueError("Cleaning changed original training, inference or outcome cohort")
    model_meta={}
    nframes=[]
    cframes=[]
    with tempfile.TemporaryDirectory() as td:
        for i in (1,2,3):
            learners.validate(trains[i],[common,tests[i]],a.year)
            pp,meta,_,elapsed=learners.fit(trains[i],[common,tests[i]],"BASE",a.year,Path(td),f"clean_{a.year}_{i}")
            again,other,_,_=learners.fit(trains[i],[common,tests[i]],"BASE",a.year,Path(td),f"clean_{a.year}_{i}_refit")
            if meta!=other or any(x.dtype!=y.dtype or x.tobytes()!=y.tobytes() for x,y in zip(pp,again)):
                raise ValueError("Candidate reproducibility failure")
            source_old=old["transforms"][str(i)]
            if (meta["train_labels_sha256"] != source_old["train_labels_sha256"]
                or meta["train_groups_sha256"] != source_old["train_groups_sha256"]):
                raise ValueError("Label or training groups changed")
            if meta["train_matrix_sha256"]==source_old["train_matrix_sha256"]:
                raise ValueError("Candidate treatment absent: original and cleaned matrix equal")
            n=predictions_frame(tests[i],pp[1],i)
            c=common[KEYS].copy()
            c["pred"]=pp[0]
            c["vintage"]=i
            nframes.append(n)
            cframes.append(c)
            model_meta[str(i)]={"transforms":meta,"seconds":elapsed,"refit_byte_exact":True,
                                 "original_labels_and_groups_exact":True}
    native=pd.concat(nframes,ignore_index=True)
    cframe=pd.concat(cframes,ignore_index=True)
    original_native=ref_native.loc[ref_native.signal_date.dt.year.eq(a.year)].sort_values(["vintage"]+KEYS).reset_index(drop=True)
    cand_native=native.sort_values(["vintage"]+KEYS).reset_index(drop=True)
    pd.testing.assert_frame_equal(
        cand_native.drop(columns="pred"),
        original_native.drop(columns="pred"),
        check_exact=True)
    original_common=ref_common.loc[ref_common.signal_date.dt.year.eq(a.year)].sort_values(["vintage"]+KEYS).reset_index(drop=True)
    candidate_common=cframe.sort_values(["vintage"]+KEYS).reset_index(drop=True)
    pd.testing.assert_frame_equal(candidate_common.drop(columns="pred"),original_common.drop(columns="pred"),check_exact=True)
    native.to_parquet(a.out/"NATIVE_PREDICTIONS.parquet",index=False)
    cframe.to_parquet(a.out/"COMMON_PREDICTIONS.parquet",index=False)
    results={
       "status":LINE+"_COMPLETE","line":LINE,"year":a.year,
       "years":[a.year],"variant":"CLEAN_SEMIDEV_9",
       "source_prep_run":37936573578,
       "source_sha256":{str(i):manifests[i]["cleaned_ti_sha256"] for i in (1,2,3)},
       "raw_original_sha256":FROZEN_TI,
       "preregistration_sha256":sha(ROOT/"compact21_downvol_cleanup_v1/TRAINING_PREREGISTRATION.md"),
       "source_impl_sha256":manifests[1]["cleaning_source_sha256"],
       "reference_baseline_sha256":sha(a.reference/"RESULT.json"),
       "numeric_contract":numeric,
       "cohort":source_coverage,
       "fit_audits":model_meta,
       "quality_by_vintage":{
           str(i):quality(tests[i].loc[tests[i].target_rank_21.notna()
             & tests[i].exit_date_21.le(pd.Timestamp("2026-07-01"))],
             nframes[i-1].pred.to_numpy()[(tests[i].target_rank_21.notna()
             & tests[i].exit_date_21.le(pd.Timestamp("2026-07-01"))).to_numpy()])
           for i in (1,2,3)},
       "pair_metrics_common":{f"{i}-{j}":stability(common[KEYS],
             cframes[i-1].pred.to_numpy(),cframes[j-1].pred.to_numpy())
             for i,j in PAIRS},
       "pair_metrics_native":compare_native(tests,{i:nframes[i-1].pred.to_numpy() for i in (1,2,3)}),
       "prediction_sha256":{
           f.name:sha(f) for f in a.out.glob("*.parquet")},
       "eligibility_preserved":True,"repeated_fit_exact":True,
       "production_adoption":False,"portfolio_evaluation":False,
       "negative_feedback_changed":False}
    (a.out/"RESULT.json").write_text(json.dumps(results,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"year":a.year,"status":results["status"],
        "common_rank_mad":{k:v["rank_mean_abs"] for k,v in results["pair_metrics_common"].items()}}),flush=True)


if __name__=="__main__":
    main()
