"""Frozen factorial run using old BASE and MATCHED controls; fit only two missing arms."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from etf_trader.source_only import kernel as k
from paper_ltr_v1 import learner as v1
from paper_ltr_v1.run import annual_frames,verified_baseline
from paper_ltr_monthly_v1.run import ANNUAL_SHA,write
from paper_ltr_v2.replay import sha
from compact21_predictive_v2.run import numerical_gate,predictions_frame
from compact21_predictive_v2.metrics import evaluate,paired_compare
from pls_xgb_v1.run import verify_keys,disagreement
from xgb125_factorial_v1.core import NEW_VARIANTS,ALL_VARIANTS,fit_two

def ref_output(folder,result,expected,hashes):
    if result["variant"]!=expected or result["input_sha256"]!=hashes:
        raise ValueError("Wrong reference identity "+expected)
    frames={}
    for name in ("NATIVE_PREDICTIONS.parquet","COMMON_PREDICTIONS.parquet"):
        path=folder/name
        if sha(path)!=result["files_sha256"][name]:raise ValueError("Reference parquet changed "+str(path))
        frames[name]=pd.read_parquet(path)
    return frames

def main():
    parser=argparse.ArgumentParser()
    for i in (1,2,3):parser.add_argument(f"--r{i}",required=True)
    parser.add_argument("--annual",required=True)
    parser.add_argument("--baseline",required=True)
    parser.add_argument("--previous",required=True)
    parser.add_argument("--out",required=True)
    a=parser.parse_args()
    annual_root=Path(a.annual)
    if sha(annual_root/"RESULT.json")!=ANNUAL_SHA:raise ValueError("Invalid frozen annual reference")
    annual=json.loads((annual_root/"RESULT.json").read_text())
    if annual["variant"]!="LINEAR_NUMERICAL_REPAIR" or annual["status"]!="PAPER_LTR_V2_COMPLETE":
        raise ValueError("Annual reference not completed")
    numerical=numerical_gate()
    frames={};hashes={}
    for i in (1,2,3):
        file=Path(getattr(a,f"r{i}"))/"TI_COMPACT.parquet"
        hashes[str(i)]=sha(file)
        frames[i]=pd.read_parquet(file)
        for c in ("signal_date","exit_date_21"):frames[i][c]=pd.to_datetime(frames[i][c])
    if hashes!=annual["input_sha256"]:raise ValueError("Input hashes not matched to annual")
    baseline,base_audit=verified_baseline(a.baseline,hashes,frames)
    old=Path(a.previous)/"XGB125_MATCHED"
    old_result=json.loads((old/"RESULT.json").read_text())
    if old_result["status"]!="PAPER_LTR_V2_COMPLETE" or old_result["ALL_MATURITY_PASS"] is not True:
        raise ValueError("Matched control incomplete")
    base_outputs=ref_output(Path(a.baseline),baseline,"BASE",hashes)
    match_outputs=ref_output(old,old_result,"XGB125_MATCHED",hashes)
    for name in base_outputs:verify_keys(match_outputs[name],base_outputs[name])
    out=Path(a.out)
    if out.exists() and any(out.iterdir()):raise ValueError("Not new output directory")
    out.mkdir(parents=True,exist_ok=True)
    all_meta={v:{} for v in NEW_VARIANTS}
    native={v:[] for v in NEW_VARIANTS};common={v:[] for v in NEW_VARIANTS}
    status=dict(status="RUNNING",reference_sha256=ANNUAL_SHA,base_sha256=sha(Path(a.baseline)/"RESULT.json"),
        matched_sha256=sha(old/"RESULT.json"),input_sha256=hashes,baseline_audit=base_audit,
        numerical_contract=numerical,variants=list(ALL_VARIANTS),new_xgb_seed_fits=0,
        protocol_sha256=sha(ROOT/"xgb125_factorial_v1/PROTOCOL.md"),production_adoption=False)
    (out/"INPUT_CONTRACT.json").write_text(json.dumps(status,indent=2)+"\n")
    try:
        for year in range(2017,2027):
            trains,tests,shared=annual_frames(frames,year)
            for variant in NEW_VARIANTS:all_meta[variant][str(year)]={}
            for i in (1,2,3):
                computed=fit_two(trains[i],[shared,tests[i]],year,i,out,annual)
                for variant,(scores,meta) in computed.items():
                    common_score,native_score=scores
                    native[variant].append(predictions_frame(tests[i],native_score,i))
                    m=shared[v1.KEYS].copy()
                    m["pred"]=common_score;m["vintage"]=i
                    common[variant].append(m)
                    all_meta[variant][str(year)][str(i)]=meta
                    status["new_xgb_seed_fits"]+=3
            (out/"PROGRESS.json").write_text(json.dumps(dict(year=year,fits=status["new_xgb_seed_fits"]))+"\n")
            print(json.dumps(dict(year=year,seed_fits=status["new_xgb_seed_fits"])),flush=True)
        if status["new_xgb_seed_fits"]!=180:raise ValueError("Unexpected fit count")
        quality={};stability={};comparator={}
        refs={"BASE":base_outputs,"XGB125_MATCHED":match_outputs}
        for variant in NEW_VARIANTS:
            folder=out/variant;folder.mkdir()
            n=pd.concat(native[variant],ignore_index=True)
            c=pd.concat(common[variant],ignore_index=True)
            verify_keys(n,base_outputs["NATIVE_PREDICTIONS.parquet"])
            verify_keys(c,base_outputs["COMMON_PREDICTIONS.parquet"])
            n.to_parquet(folder/"NATIVE_PREDICTIONS.parquet",index=False)
            c.to_parquet(folder/"COMMON_PREDICTIONS.parquet",index=False)
            aud=dict(status="PAPER_LTR_V2_COMPLETE",variant=variant,
                input_sha256=hashes,per_year={year:dict(transforms=per_source,maturity_PASS=True)
                    for year,per_source in all_meta[variant].items()},
                baseline=base_audit,ALL_MATURITY_PASS=True,new_xgb_seed_fits=90,
                protocol_sha256=status["protocol_sha256"],production_adoption=False,
                files_sha256={name:sha(folder/name) for name in ("NATIVE_PREDICTIONS.parquet","COMMON_PREDICTIONS.parquet")},
                predictive=evaluate(n,quality_exit_cutoff="2026-07-01"),
                stability=disagreement(c),recipe=k.COMPACT_PARAMS,seeds=k.COMPACT_SEEDS,
                models_not_persisted=True)
            write(folder,aud)
            refs[variant]={name:(n if name.startswith("NATIVE") else c)
                for name in ("NATIVE_PREDICTIONS.parquet","COMMON_PREDICTIONS.parquet")}
        for variant,data in refs.items():
            qa=evaluate(data["NATIVE_PREDICTIONS.parquet"],quality_exit_cutoff="2026-07-01")
            quality[variant]=qa
            stability[variant]=disagreement(data["COMMON_PREDICTIONS.parquet"])
        for variant in NEW_VARIANTS:
            comparator[variant]={}
            for baseline_name in ("BASE","XGB125_MATCHED"):
                paired=paired_compare(quality[variant],quality[baseline_name],block_lengths=(6,12),
                    n_bootstrap=1000,seed=20261017)
                comparator[variant][baseline_name]=dict(difference=paired["difference"],
                    ci6={name:paired["bootstrap"]["6"]["intervals_95pct"][name] for name in
                        ("top1_realized_percentile","ndcg5","rank_ic")})
        primary={variant:quality[variant]["aggregate_by_date"] for variant in ALL_VARIANTS}
        # Keep effect decomposition explicit; factor interactions must be computed from four scores.
        effects={}
        for metric in ("top1_realized_percentile","ndcg5","rank_ic"):
            A=primary["BASE"][metric];B=primary["XGB_FULL_PREP"][metric]
            C=primary["XGB_REDUCED_NATIVE"][metric];D=primary["XGB125_MATCHED"][metric]
            effects[metric]=dict(full_preprocessing=B-A,reduced_preprocessing=D-C,
                reduction_with_native=C-A,reduction_with_preprocessing=D-B,
                interaction=(D-C)-(B-A))
        status.update(status="XGB125_FACTORIAL_PREDICTIVE_COMPLETE",
            primary_quality=primary,stability=stability,quality_per_year={
                name:quality[name]["per_year"] for name in ALL_VARIANTS},
            factor_effects=effects,paired_exploratory=comparator,
            every_source_uses_same_native_and_common_query_keys=True,
            references_reused_without_refit=True,no_future_training_labels=True,
            not_independent_holdout=True)
        (out/"SUMMARY.json").write_text(json.dumps(status,indent=2,allow_nan=False)+"\n")
        print(json.dumps(dict(status=status["status"],quality=primary,stability=stability,
             factorial_effects=effects),indent=2),flush=True)
    except Exception as err:
        status.update(status="XGB125_FACTORIAL_FAILED",failure=str(err))
        (out/"FAILURE.json").write_text(json.dumps(status,indent=2)+"\n")
        raise

if __name__=="__main__":main()
