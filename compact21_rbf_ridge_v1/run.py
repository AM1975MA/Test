"""Annual RBF_RIDGE cloud trial; all original BASE and RIDGE controls precede fit."""
from __future__ import annotations
import argparse
import importlib.metadata
import json
from pathlib import Path
import sys
import tempfile
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src")]
from compact21_learner_swap_v1 import learners
from compact21_learner_swap_v1.run_benchmark import evaluation_coverage,score_gap,compare_native
from compact21_predictive_v2.run import numerical_gate,predictions_frame
from compact21_predictive_v2.summarize import normalized_numeric
from compact21_semidev_v1.run import (select_original_frames,original_controls,source_gate,
    retained_slice,compare_retained,FROZEN_TI)
from compact21_semidev_v1.view import sha
from ranker_stability_v1.run_ranker_benchmark_full import load,stability,quality
from compact21_rbf_ridge_v1.model import fit,PARAMS

LINE="COMPACT21_RBF_RIDGE_V1"
VARIANT="RBF_RIDGE"
KEYS=["signal_date","ticker"]
PAIRS=((1,2),(1,3),(2,3))


def retained_reference(directory,variant,hashes,numeric):
    p=directory/"RESULT.json";r=json.loads(p.read_text())
    if r.get("status")!="COMPACT21_PREDICTIVE_V2_COMPLETE" or r.get("variant")!=variant or r.get("input_sha256")!=hashes:
        raise ValueError("Wrong retained "+variant+" reference")
    if normalized_numeric(numeric)!=normalized_numeric(r["numeric_contract"]):
        raise ValueError("Numeric profile differs from "+variant)
    source_gate(r)
    for n in ("NATIVE_PREDICTIONS.parquet","COMMON_PREDICTIONS.parquet"):
        if r.get("files_sha256",{}).get(n)!=sha(directory/n):raise ValueError("Retained reference hash mismatch")
    return r,pd.read_parquet(directory/"NATIVE_PREDICTIONS.parquet"),pd.read_parquet(directory/"COMMON_PREDICTIONS.parquet")


def ridge_controls(trains,tests,common,year,reference,native_reference,common_reference,scratch):
    controls={};audits={};native=[];common_frames=[]
    for i in (1,2,3):
        p,a,_,elapsed=learners.fit(trains[i],[common,tests[i]],"RIDGE",year,scratch,f"ridge_control_{year}_{i}")
        if a!=reference["per_year"][str(year)]["transforms"][str(i)]:
            raise ValueError("Original RIDGE complete audit differs")
        native.append(compare_retained(tests[i],p[1],retained_slice(native_reference,year,i),True))
        common_frames.append(compare_retained(common,p[0],retained_slice(common_reference,year,i),False))
        audits[str(i)]=a
        controls[str(i)]={"native_bytes_exact":True,"common_bytes_exact":True,"metadata_exact":True,
                          "legacy_hashes_exact":True,"fit_seconds":elapsed}
    if evaluation_coverage(trains,tests,common)!=reference["per_year"][str(year)]["evaluation_coverage"]:
        raise ValueError("Original RIDGE coverage differs")
    return controls,audits,pd.concat(native,ignore_index=True),pd.concat(common_frames,ignore_index=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year",type=int,required=True,choices=range(2017,2027))
    for n in ("r1","r2","r3","reference","ridge-reference","out"):
        parser.add_argument("--"+n,type=Path,required=True)
    a=parser.parse_args();numeric=numerical_gate()
    if a.out.exists() and any(a.out.iterdir()):raise ValueError("Output must be fresh")
    a.out.mkdir(parents=True,exist_ok=True)
    paths={i:getattr(a,f"r{i}") for i in (1,2,3)}
    hashes={str(i):sha(p/"TI_COMPACT.parquet") for i,p in paths.items()}
    if hashes!=FROZEN_TI:raise ValueError("Wrong frozen TI inputs")
    base,bn,bc=retained_reference(a.reference,"BASE",hashes,numeric)
    ridge,rn,rc=retained_reference(a.ridge_reference,"RIDGE",hashes,numeric)
    if base["input_contract"]!=ridge["input_contract"]:raise ValueError("Different original BASE/RIDGE input contracts")
    canonical_sources=source_gate(base)
    frames={i:load(p) for i,p in paths.items()};trains,tests,common=select_original_frames(frames,a.year)
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    sources.update(canonical_sources)
    helpers=("compact21_semidev_v1/run.py","compact21_semidev_v1/view.py","compact21_semidev_v1/summarize.py",
        "compact21_predictive_v2/metrics.py","compact21_predictive_v2/summarize.py","compact21_predictive_v2/additive.py",
        "compact21_learner_swap_v1/run_benchmark.py","compact21_learner_swap_v1/prepare_ma3.py",
        "compact21_blockbag_v1/summarize.py")
    sources.update({p:sha(ROOT/p) for p in helpers})
    result={"status":"RUNNING","line":LINE,"variant":VARIANT,"years":[a.year],"input_sha256":hashes,
        "per_year":{},"numeric_contract":numeric,"python":sys.version,"sources":sources,"fit_sources":canonical_sources,
        "environment":{n:importlib.metadata.version(n) for n in ("numpy","pandas","scipy","scikit-learn","xgboost","lightgbm","pyarrow")},
        "baseline_input_contract":base["input_contract"],
        "preregistration_sha256":sha(Path(__file__).with_name("PREREGISTRATION.md")),
        "input_contract":{"line":LINE,"original_ti_sha256":hashes,"signal_cutoff":"2026-06-30",
            "quality_exit_cutoff":"2026-07-01","common_inference_repeat":2,"train_cohorts":"original_native_frozen",
            "changed_columns":[],"recipe":PARAMS,"ref_base_result_sha256":sha(a.reference/"RESULT.json"),
            "ref_ridge_result_sha256":sha(a.ridge_reference/"RESULT.json"),
            "reference_prediction_sha256":base["files_sha256"],"ridge_reference_prediction_sha256":ridge["files_sha256"]},
        "negative_feedback_changed":False,"portfolio_evaluation":False,"production_adoption":False}
    (a.out/"INPUT_CONTRACT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    pcs={};pns={};audits={};times={};refits={};native=[];common_frames=[];seed_vectors={};retained_states={}
    with tempfile.TemporaryDirectory() as td:
        scratch=Path(td)
        controls,control_audits,cn,cc=original_controls(trains,tests,common,a.year,base,bn,bc,scratch)
        rcontrols,ra,rcontroln,rcontrolc=ridge_controls(trains,tests,common,a.year,ridge,rn,rc,scratch)
        # Both sets of original controls must pass before any RBF candidate fit.
        for n,f in (("CONTROL_NATIVE_PREDICTIONS",cn),("CONTROL_COMMON_PREDICTIONS",cc),
                    ("RIDGE_CONTROL_NATIVE_PREDICTIONS",rcontroln),("RIDGE_CONTROL_COMMON_PREDICTIONS",rcontrolc)):
            f.to_parquet(a.out/(n+".parquet"),index=False)
        (a.out/"CONTROL_GATE.json").write_text(json.dumps({"PASS":True,"BASE":controls,"RIDGE":rcontrols},indent=2)+"\n")
        for i in (1,2,3):
            tag=f"rbf_{a.year}_{i}"
            p,audit,_,elapsed=fit(trains[i],[common,tests[i]],a.year,scratch,tag)
            again,refit_audit,_,_=fit(trains[i],[common,tests[i]],a.year,scratch,tag+"_refit")
            if audit!=refit_audit or any(x.dtype!=y.dtype or x.tobytes()!=y.tobytes() for x,y in zip(p,again)):
                raise ValueError("Independent RBF candidate refit differs")
            sv=np.load(scratch/f"{tag}_SEED_PREDICTIONS.npy",allow_pickle=False)
            rv=np.load(scratch/f"{tag}_refit_SEED_PREDICTIONS.npy",allow_pickle=False)
            if sv.dtype!=rv.dtype or sv.tobytes()!=rv.tobytes():raise ValueError("Seed refit vectors differ")
            seed_vectors[f"predictions_{i}"]=sv
            with np.load(scratch/f"{tag}_STATES.npz",allow_pickle=False) as st, np.load(scratch/f"{tag}_refit_STATES.npz",allow_pickle=False) as rst:
                if set(st.files)!=set(rst.files):raise ValueError("Refit state schema differs")
                for key in st.files:
                    if st[key].dtype!=rst[key].dtype or st[key].shape!=rst[key].shape or st[key].tobytes()!=rst[key].tobytes():
                        raise ValueError("Refit fitted state differs")
                    retained_states[f"v{i}_{key}"]=st[key].copy()
            pcs[i],pns[i]=p;audits[str(i)]=audit;times[str(i)]=elapsed
            refits[str(i)]={"common_bytes_exact":True,"native_bytes_exact":True,"learned_audit_exact":True,
                "fitted_states_bytes_exact":True,"seed_vectors_bytes_exact":True,
                "refit_audit":refit_audit,"prediction_sha256":refit_audit["prediction_sha256"]}
            native.append(predictions_frame(tests[i],pns[i],i));common_frames.append(common[KEYS].assign(pred=pcs[i],vintage=i))
    qualities={}
    for i in (1,2,3):
        mask=(tests[i].target_rank_21.notna()&tests[i].exit_date_21.notna()&tests[i].exit_date_21.le(pd.Timestamp("2026-07-01"))).to_numpy()
        if not mask.any():raise ValueError("Empty annual quality cohort")
        qualities[str(i)]=quality(tests[i].loc[mask],pns[i][mask])
    result["per_year"][str(a.year)]={"quality":qualities,"evaluation_coverage":evaluation_coverage(trains,tests,common),
        "common_inference":{f"{i}-{j}":stability(common[KEYS],pcs[i],pcs[j]) for i,j in PAIRS},
        "native_inference":compare_native(tests,pns),"common_score_gap":{f"{i}-{j}":score_gap(common[KEYS],pcs[i],pcs[j]) for i,j in PAIRS},
        "transforms":audits,"fit_seconds":times,"determinism_PASS":True,"legacy_control":controls,
        "control_transforms":control_audits,"ridge_control":rcontrols,"ridge_control_transforms":ra,"independent_refits":refits}
    pd.concat(native,ignore_index=True).to_parquet(a.out/"NATIVE_PREDICTIONS.parquet",index=False)
    pd.concat(common_frames,ignore_index=True).to_parquet(a.out/"COMMON_PREDICTIONS.parquet",index=False)
    np.savez(a.out/"SEED_PREDICTIONS.npz",**seed_vectors)
    np.savez(a.out/"FITTED_STATES.npz",**retained_states)
    result.update(ALL_DETERMINISM_PASS=True,LEGACY_PARITY_PASS=True,RIDGE_PARITY_PASS=True)
    result["files_sha256"]={p.name:sha(p) for p in a.out.iterdir() if p.suffix in (".npz",".parquet")}
    result["status"]=LINE+"_COMPLETE"
    (a.out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"year":a.year,"variant":VARIANT,"status":result["status"]}),flush=True)


if __name__=="__main__":main()
