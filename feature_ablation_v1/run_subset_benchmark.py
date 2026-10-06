#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, tempfile, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src")]
from etf_trader.source_only import kernel as k
from ranker_stability_v1.run_ranker_benchmark_full import load, train_frame, align, stability, quality

KEYS=["signal_date","ticker"]
PAIRS=((1,2),(1,3),(2,3))
VARIANTS=("BASE125","K8","K12","K16","K24","K32","K40","FAMILY46")

def load_sets(path:Path):
    r=json.loads(path.read_text())
    ladders=r["ladders"]
    expected={"K8","K12","K16","K24","K32","K40","FAMILY46"}
    if set(ladders)!=expected: raise ValueError("Frozen feature ladder mismatch")
    return ladders

def selected_features(variant,ladders):
    return list(k.F2D_FEATURES) if variant=="BASE125" else list(ladders[variant])

def matrix(df,features):
    return df[features].replace([np.inf,-np.inf],np.nan)

def fit(train,tests,features,tmp,tag):
    X=matrix(train,features)
    T=[matrix(t,features) for t in tests]
    y=(train.target_rank_21.clip(0,1)*100).round().astype(int).to_numpy()
    groups=train.groupby("signal_date",sort=True).size().to_numpy()
    if not len(train) or not all(len(z) for z in tests): raise ValueError("Empty fit or inference")
    if not np.array_equal(train[KEYS].to_numpy(),train.sort_values(KEYS)[KEYS].to_numpy()): raise ValueError("Ungrouped rows")
    params=dict(k.COMPACT_PARAMS); rounds=int(params.pop("n_estimators")); params.pop("n_jobs",None)
    path=tmp/f"{tag}.npz"; np.savez(path,Xtr=X.to_numpy(),Xte=pd.concat(T).to_numpy(),y=y,groups=groups)
    preds=[]; start=time.perf_counter()
    for seed in k.COMPACT_SEEDS:
        out=tmp/f"{tag}_{int(seed)}.npy"
        subprocess.run([
            sys.executable,str(Path(k.__file__).with_name("_xgb_worker.py")),
            "--data",str(path),"--seed",str(int(seed)),"--threads","1",
            "--rounds",str(rounds),"--params-json",json.dumps(params),
            "--output",str(out)
        ],check=True,capture_output=True,text=True)
        preds.append(np.load(out))
    p=np.mean(preds,axis=0)
    if not np.isfinite(p).all(): raise ValueError("Nonfinite predictions")
    ans=[]; pos=0
    for z in T:
        ans.append(p[pos:pos+len(z)]); pos+=len(z)
    return ans,time.perf_counter()-start

def compare_native(tests,predictions):
    frames=[]
    for i in (1,2,3):
        z=tests[i][KEYS].copy(); z["p"]=predictions[i]; frames.append(z)
    a=align(frames)
    return {f"{i}-{j}":stability(a[0][KEYS],a[i-1].p.to_numpy(),a[j-1].p.to_numpy()) for i,j in PAIRS}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--variant",choices=VARIANTS,required=True)
    for i in (1,2,3): ap.add_argument(f"--r{i}",required=True)
    ap.add_argument("--sets",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--years",default=",".join(map(str,range(2017,2027))))
    a=ap.parse_args()
    years=[int(x) for x in a.years.split(",") if x.strip()]
    if years!=list(range(2017,2027)): raise ValueError("Frozen benchmark requires 2017-2026")
    ladders=load_sets(Path(a.sets)); features=selected_features(a.variant,ladders)
    if len(features)!=len(set(features)): raise ValueError("Duplicate selected feature")
    if not set(features)<=set(k.F2D_FEATURES): raise ValueError("Unknown selected feature")
    expected=125 if a.variant=="BASE125" else (46 if a.variant=="FAMILY46" else int(a.variant[1:]))
    if len(features)!=expected: raise ValueError("Feature-count contract violation")
    R={i:load(Path(getattr(a,f"r{i}"))) for i in (1,2,3)}
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    res={
      "status":"COMPACT21_ORTHOGONAL_SUBSET_BENCHMARK_COMPLETE",
      "variant":a.variant,"feature_count":len(features),"features":features,"years":years,
      "input_sha256":{str(i):hashlib.sha256((Path(getattr(a,f"r{i}"))/"TI_COMPACT.parquet").read_bytes()).hexdigest() for i in (1,2,3)},
      "per_year":{}
    }
    with tempfile.TemporaryDirectory() as td:
      tmp=Path(td)
      for year in years:
        cutoff=pd.Timestamp(year,1,1)
        trains={i:train_frame(R[i],year) for i in (1,2,3)}
        tests={}
        for i in (1,2,3):
            f=R[i]
            valid=f[k.F2D_FEATURES].notna().sum(axis=1)>=30
            tests[i]=f[(f.signal_date.dt.year==year)&(f.signal_date<="2026-06-30")&valid].sort_values(KEYS).reset_index(drop=True)
            if tests[i].duplicated(KEYS).any() or trains[i].duplicated(KEYS).any(): raise ValueError("Duplicate keys")
        common=align([tests[i] for i in (1,2,3)])[1]
        if common.empty: raise ValueError("No common evaluation rows")
        pcs={}; pns={}; times={}
        for i in (1,2,3):
            p,t=fit(trains[i],[common,tests[i]],features,tmp,f"{a.variant}_{year}_{i}")
            pcs[i],pns[i]=p; times[str(i)]=t
        pp,_=fit(trains[2],[common],features,tmp,f"{a.variant}_{year}_det")
        delta=float(np.max(np.abs(pp[0]-pcs[2])))
        qualities={}
        for i in (1,2,3):
            eval_mask=(tests[i].target_rank_21.notna()&tests[i].exit_date_21.notna()&(tests[i].exit_date_21<=pd.Timestamp("2026-07-01"))).to_numpy()
            if not eval_mask.any(): raise ValueError("No mature quality rows")
            qualities[str(i)]=quality(tests[i].loc[eval_mask],pns[i][eval_mask])
        matpass=all(bool((trains[i].signal_date<cutoff).all()&(trains[i].exit_date_21<cutoff).all()) for i in (1,2,3))
        cell={
          "common_inference":{f"{i}-{j}":stability(common[KEYS],pcs[i],pcs[j]) for i,j in PAIRS},
          "native_inference":compare_native(tests,pns),
          "quality":qualities,
          "train_rows":{str(i):len(trains[i]) for i in (1,2,3)},
          "test_rows":{str(i):len(tests[i]) for i in (1,2,3)},
          "common_test_rows":len(common),
          "maturity_PASS":matpass,
          "determinism":{"max_abs":delta,"PASS":delta==0.0},
          "fit_seconds":times
        }
        res["per_year"][str(year)]=cell
        out.write_text(json.dumps(res,indent=2,allow_nan=False)+"\n")
        print(json.dumps({"variant":a.variant,"year":year,"rank_mad":np.mean([q["rank_mean_abs"] for q in cell["common_inference"].values()]),"top1":np.mean([q["top1_disagreement_fraction"] for q in cell["common_inference"].values()]),"det":delta}),flush=True)
    res["aggregate"]={}
    for scope in ("common_inference","native_inference","quality"):
        rows=[q for y in res["per_year"].values() for q in y[scope].values()]
        res["aggregate"][scope]={f:float(np.mean([z[f] for z in rows])) for f in rows[0]}
    res["aggregate_by_pair"]={scope:{pair:{f:float(np.mean([z[scope][pair][f] for z in res["per_year"].values()])) for f in next(iter(res["per_year"].values()))[scope][pair]} for pair in ("1-2","1-3","2-3")} for scope in ("common_inference","native_inference")}
    res["ALL_MATURITY_PASS"]=all(z["maturity_PASS"] for z in res["per_year"].values())
    res["ALL_DETERMINISM_PASS"]=all(z["determinism"]["PASS"] for z in res["per_year"].values())
    out.write_text(json.dumps(res,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":res["status"],"variant":a.variant,"feature_count":len(features),"aggregate":res["aggregate"]},indent=2))
if __name__=="__main__": main()
