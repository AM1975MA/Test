#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, tempfile, time
from pathlib import Path
import numpy as np
import pandas as pd
from feature_ablation_v1.run_subset_benchmark import (
    ROOT, KEYS, PAIRS, load, train_frame, align, stability, quality,
    matrix, fit, compare_native
)
from etf_trader.source_only import kernel as k

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--variant",required=True)
    for i in (1,2,3): ap.add_argument(f"--r{i}",required=True)
    ap.add_argument("--variants",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    spec=json.loads(Path(a.variants).read_text())
    variants=spec["variants"]
    if a.variant not in variants: raise ValueError(f"Unknown variant {a.variant}")
    features=list(variants[a.variant])
    if len(features)!=len(set(features)): raise ValueError("Duplicate selected feature")
    if not set(features)<=set(k.F2D_FEATURES): raise ValueError("Unknown selected feature")
    years=list(range(2017,2027))
    R={i:load(Path(getattr(a,f"r{i}"))) for i in (1,2,3)}
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    res={
      "status":"COMPACT21_K12_FORWARD_BENCHMARK_COMPLETE",
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
    print(json.dumps({"status":res["status"],"variant":a.variant,"aggregate":res["aggregate"]},indent=2))
if __name__=="__main__": main()
