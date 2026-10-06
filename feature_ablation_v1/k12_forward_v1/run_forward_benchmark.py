#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sys, tempfile, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src")]
from etf_trader.source_only import kernel as k
from ranker_stability_v1.run_ranker_benchmark_full import load, train_frame, align, stability, quality
from feature_ablation_v1.run_subset_benchmark import fit, compare_native, KEYS, PAIRS

STATUS="COMPACT21_K12_FORWARD_BENCHMARK_COMPLETE"

def load_sets(path:Path):
    r=json.loads(path.read_text())
    if r.get("schema")!="COMPACT21_K12_CONDITIONAL_FORWARD_ABLATION_V1":
        raise ValueError("Wrong frozen set schema")
    return r["variants"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--variant",required=True)
    for i in (1,2,3): ap.add_argument(f"--r{i}",required=True)
    ap.add_argument("--sets",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--years",default=",".join(map(str,range(2017,2027))))
    a=ap.parse_args()
    years=[int(x) for x in a.years.split(",") if x.strip()]
    if years!=list(range(2017,2027)): raise ValueError("Frozen benchmark requires 2017-2026")
    variants=load_sets(Path(a.sets))
    if a.variant not in variants: raise ValueError("Unknown frozen candidate")
    features=list(variants[a.variant])
    if len(features)!=len(set(features)) or not set(features)<=set(k.F2D_FEATURES):
        raise ValueError("Invalid selected features")
    if len(features) not in (12,13,14,15,16): raise ValueError("Unexpected feature count")
    R={i:load(Path(getattr(a,f"r{i}"))) for i in (1,2,3)}
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    res={"status":STATUS,"variant":a.variant,"feature_count":len(features),"features":features,"years":years,
         "input_sha256":{str(i):hashlib.sha256((Path(getattr(a,f"r{i}"))/"TI_COMPACT.parquet").read_bytes()).hexdigest() for i in (1,2,3)},
         "per_year":{}}
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
            mask=(tests[i].target_rank_21.notna()&tests[i].exit_date_21.notna()&(tests[i].exit_date_21<=pd.Timestamp("2026-07-01"))).to_numpy()
            if not mask.any(): raise ValueError("No mature quality rows")
            qualities[str(i)]=quality(tests[i].loc[mask],pns[i][mask])
        matpass=all(bool((trains[i].signal_date<cutoff).all()&(trains[i].exit_date_21<cutoff).all()) for i in (1,2,3))
        cell={
          "common_inference":{f"{i}-{j}":stability(common[KEYS],pcs[i],pcs[j]) for i,j in PAIRS},
          "native_inference":compare_native(tests,pns),
          "quality":qualities,
          "maturity_PASS":matpass,
          "determinism":{"max_abs":delta,"PASS":delta==0.0},
          "fit_seconds":times
        }
        res["per_year"][str(year)]=cell
        out.write_text(json.dumps(res,indent=2,allow_nan=False)+"\n")
        print(json.dumps({"variant":a.variant,"year":year,"rank_mad":np.mean([q["rank_mean_abs"] for q in cell["common_inference"].values()]),"top1":np.mean([q["top1_disagreement_fraction"] for q in cell["common_inference"].values()])}),flush=True)
    res["aggregate"]={}
    for scope in ("common_inference","native_inference","quality"):
        rows=[q for y in res["per_year"].values() for q in y[scope].values()]
        res["aggregate"][scope]={f:float(np.mean([z[f] for z in rows])) for f in rows[0]}
    res["ALL_MATURITY_PASS"]=all(z["maturity_PASS"] for z in res["per_year"].values())
    res["ALL_DETERMINISM_PASS"]=all(z["determinism"]["PASS"] for z in res["per_year"].values())
    out.write_text(json.dumps(res,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":STATUS,"variant":a.variant,"feature_count":len(features),"aggregate":res["aggregate"]},indent=2))
if __name__=="__main__": main()
