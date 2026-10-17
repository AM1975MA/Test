"""Annual source-only 2-challenger return-aware learning; BASE scores reused byte-exact."""
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from etf_trader.source_only import kernel as k
from paper_ltr_v1 import learner as v1
from paper_ltr_v1.run import annual_frames,verified_baseline
from compact21_predictive_v2.run import numerical_gate,predictions_frame
from compact21_predictive_v2.metrics import evaluate,paired_compare
from pls_xgb_v1.run import verify_keys,disagreement
from paper_ltr_v2.replay import sha
from compact21_return_v1.core import VARIANTS,KEYS,native_x,prepare_targets,recipe,sha_array

def annual_fit(train,tests,year,repeat,variant,output):
    cutoff=pd.Timestamp(year,1,1)
    if not ((train.signal_date<cutoff)&(train.exit_date_21<cutoff)).all():
        raise ValueError("Future labels in training")
    if train.duplicated(list(KEYS)).any():raise ValueError("Ambiguous training rows")
    x=native_x(train)
    te=[native_x(t) for t in tests]
    params,rounds,seeds=recipe(variant)
    labels,groups,target_audit=prepare_targets(train,variant)
    working=output/"scratch";working.mkdir(exist_ok=True)
    key=f"{year}_{repeat}_{variant}"
    source=working/f"{key}.npz"
    np.savez(source,xtrain=x,xtest=np.concatenate(te),labels=labels,groups=groups)
    scores=[];seeds_sha={}
    try:
        for seed in seeds:
            path=working/f"{key}_{seed}.npy"
            command=[sys.executable,str(ROOT/"compact21_return_v1/worker.py"),
                "--data",str(source),"--params",json.dumps(params,sort_keys=True),
                "--seed",str(seed),"--rounds",str(rounds),"--output",str(path)]
            p=subprocess.run(command,capture_output=True,text=True)
            if p.returncode:raise RuntimeError(f"Fit {key}/{seed}: {p.stderr[-5000:]}")
            prediction=np.load(path,allow_pickle=False)
            if prediction.shape!=(sum(len(t) for t in te),) or not np.isfinite(prediction).all():
                raise ValueError("Worker shape/finite failure")
            scores.append(prediction);seeds_sha[str(seed)]=sha_array(prediction)
            path.unlink()
    finally:
        if source.exists():source.unlink()
    prediction=np.mean(scores,axis=0);offset=0;parts=[]
    for t in te:
        parts.append(prediction[offset:offset+len(t)])
        offset+=len(t)
    if offset!=len(prediction):raise ValueError("Prediction split inconsistency")
    sub,val,_=v1.split_training(train,year)
    audit=dict(kind=variant,
        train_keys_sha256=v1.keys_hash(train),
        subtrain_keys_sha256=v1.keys_hash(sub),
        validation_keys_sha256=v1.keys_hash(val),
        train_matrix_sha256=v1.array_hash(v1.raw_matrix(train)),
        train_labels_sha256=v1.array_hash(v1.decile_labels(train)),
        training_input_sha256=sha_array(x),training_target=target_audit,
        actual_train_rows=len(train),query_groups=len(groups),first_year=year,
        actual_test_matrix_sha256=[sha_array(t) for t in te],
        max_signal_date=train.signal_date.max().isoformat(),
        max_exit_date_21=train.exit_date_21.max().isoformat(),
        maturity_PASS=True,source_only=True,unchanged_base_features=True,
        xgb_params=dict(params,n_estimators=rounds,seeds=seeds),
        seed_prediction_sha256=seeds_sha,
        prediction_sha256=[sha_array(p) for p in parts],
        saved_models=[],models_not_saved=True,training_only_labels=True)
    return parts,audit

def main():
    parser=argparse.ArgumentParser()
    for i in (1,2,3):parser.add_argument(f"--r{i}",required=True)
    parser.add_argument("--baseline",required=True);parser.add_argument("--out",required=True)
    a=parser.parse_args()
    num=numerical_gate()
    panels={};hashes={}
    for i in (1,2,3):
        file=Path(getattr(a,f"r{i}"))/"TI_COMPACT.parquet"
        hashes[str(i)]=sha(file)
        frame=pd.read_parquet(file)
        for col in ("signal_date","exit_date_21"):frame[col]=pd.to_datetime(frame[col])
        panels[i]=frame
    control,baseline_audit=verified_baseline(a.baseline,hashes,panels)
    base={name:pd.read_parquet(Path(a.baseline)/name) for name in ("NATIVE_PREDICTIONS.parquet","COMMON_PREDICTIONS.parquet")}
    out=Path(a.out)
    if out.exists() and any(out.iterdir()):raise ValueError("Output exists")
    out.mkdir(parents=True)
    result=dict(status="RUNNING",source_only=True,variants=list(VARIANTS),
        input_sha256=hashes,baseline_sha256=sha(Path(a.baseline)/"RESULT.json"),
        numeric_contract=num,protocol_sha256=sha(ROOT/"compact21_return_v1/PROTOCOL.md"),
        code_sha256={p.name:sha(p) for p in sorted((ROOT/"compact21_return_v1").glob("*.py"))},
        new_xgb_seed_fits=0,production_adoption=False)
    (out/"INPUT_CONTRACT.json").write_text(json.dumps(result,indent=2)+"\n")
    native={v:[] for v in VARIANTS};common={v:[] for v in VARIANTS}
    audits={v:{} for v in VARIANTS}
    try:
        for year in range(2017,2027):
            trains,tests,shared=annual_frames(panels,year)
            for v in VARIANTS:audits[v][str(year)]={}
            for i in (1,2,3):
                for v in VARIANTS:
                    (sharedpred,nativepred),audit=annual_fit(trains[i],[shared,tests[i]],year,i,v,out)
                    native[v].append(predictions_frame(tests[i],nativepred,i))
                    cc=shared[list(KEYS)].copy()
                    cc["pred"]=sharedpred;cc["vintage"]=i
                    common[v].append(cc)
                    audits[v][str(year)][str(i)]=audit
                    result["new_xgb_seed_fits"]+=3
            print(json.dumps(dict(year=year,fits=result["new_xgb_seed_fits"])),flush=True)
            (out/"PROGRESS.json").write_text(json.dumps(dict(year=year,fits=result["new_xgb_seed_fits"]))+"\n")
        if result["new_xgb_seed_fits"]!=180:raise ValueError("180 seed fits required")
        base_quality=evaluate(base["NATIVE_PREDICTIONS.parquet"],quality_exit_cutoff="2026-07-01")
        qualities={"BASE":base_quality};common_stability={"BASE":disagreement(base["COMMON_PREDICTIONS.parquet"])}
        comparisons={}
        for v in VARIANTS:
            folder=out/v;folder.mkdir()
            n=pd.concat(native[v],ignore_index=True);c=pd.concat(common[v],ignore_index=True)
            verify_keys(n,base["NATIVE_PREDICTIONS.parquet"])
            verify_keys(c,base["COMMON_PREDICTIONS.parquet"])
            # Every realized target is identical to BASE on exactly the same native keys.
            a0=n.sort_values(["vintage","signal_date","ticker"]).reset_index(drop=True)
            b0=base["NATIVE_PREDICTIONS.parquet"].copy().sort_values(["vintage","signal_date","ticker"]).reset_index(drop=True)
            for col in ("target_rank_21","target_ret_21"):
                if col not in a0 or col not in b0 or not a0[col].equals(b0[col]):
                    raise ValueError(f"Canonical realized {col} mismatch")
            n.to_parquet(folder/"NATIVE_PREDICTIONS.parquet",index=False)
            c.to_parquet(folder/"COMMON_PREDICTIONS.parquet",index=False)
            qa=evaluate(n,quality_exit_cutoff="2026-07-01")
            qualities[v]=qa;common_stability[v]=disagreement(c)
            output=dict(status="PAPER_LTR_V2_COMPLETE",variant=v,
                input_sha256=hashes,
                per_year={str(year):dict(transforms=items,maturity_PASS=True) for year,items in audits[v].items()},
                ALL_MATURITY_PASS=True,source_only=True,production_adoption=False,
                new_xgb_seed_fits=90,models_not_saved=True,
                predictive=qa,stability=common_stability[v],
                protocol_sha256=result["protocol_sha256"],
                files_sha256={file:sha(folder/file) for file in ("NATIVE_PREDICTIONS.parquet","COMMON_PREDICTIONS.parquet")})
            (folder/"RESULT.json").write_text(json.dumps(output,indent=2,allow_nan=False)+"\n")
            p=paired_compare(qa,base_quality,block_lengths=(3,6,12),n_bootstrap=1000,seed=20261017)
            comparisons[v]=dict(difference=p["difference"],bootstrap=p["bootstrap"],reference="BASE",
                 direction="Lower regret is favorable; higher Top1, Top5 and realized return is favorable.")
        result.update(status="COMPACT21_RETURN_PREDICTIVE_COMPLETE",
          common_stability=common_stability,
          date_weighted={v:q["aggregate_by_date"] for v,q in qualities.items()},
          yearly={v:q["per_year"] for v,q in qualities.items()},
          comparisons=comparisons,baseline_reused_without_refit=True,
          maturity_cutoff="2026-07-01",not_independent_holdout=True)
        (out/"SUMMARY.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
        print(json.dumps(dict(status=result["status"],date_weighted=result["date_weighted"],stability=common_stability),indent=2),flush=True)
    except Exception as e:
        result.update(status="FAILED",error=str(e))
        (out/"FAILURE.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
        raise

if __name__=="__main__":main()
