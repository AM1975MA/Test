#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

KEYS = ["signal_date","ticker"]

def load_one(root: Path):
    s = pd.read_parquet(root/"TI_MODEL_RAW_SCORES.parquet").copy()
    s["signal_date"] = pd.to_datetime(s["signal_date"])
    for c in ["compact21","tail","macro_gap"]:
        s[c] = pd.to_numeric(s[c], errors="coerce")
    s["COMPACT21_RANK"] = s.groupby("signal_date")["compact21"].rank(method="average", pct=True)
    s["TAIL_RANK"] = s.groupby("signal_date")["tail"].rank(method="average", pct=True)
    s["MIX_70_30"] = .70*s["COMPACT21_RANK"] + .30*s["TAIL_RANK"]
    cond = (
        (s["macro_category"] == s["top_macro"])
        & (s["macro_gap"] >= .75)
        & (s["TAIL_RANK"] >= .80)
    )
    s["MACRO_CONDITION"] = cond.astype(np.int8)
    s["MACRO_BOOST"] = .15*s["MACRO_CONDITION"]
    s["PRE_FINAL"] = s["MIX_70_30"] + s["MACRO_BOOST"]
    s["TIT_R_REBUILT"] = s.groupby("signal_date")["PRE_FINAL"].rank(method="average", pct=True)
    tit = pd.read_parquet(root/"TIT_R.parquet")[KEYS+["TIT_R"]].copy()
    tit["signal_date"] = pd.to_datetime(tit["signal_date"])
    z = s.merge(tit,on=KEYS,how="inner",validate="one_to_one")
    d = np.abs(z["TIT_R_REBUILT"].to_numpy(float)-z["TIT_R"].to_numpy(float))
    sanity = {
        "n": int(len(z)),
        "max_abs_rebuild_vs_canonical": float(np.nanmax(d)),
        "changed_gt1e12": int(np.sum(d>1e-12)),
        "PASS": bool(not np.any(d>1e-12)),
    }
    return z, sanity

def metric(A,B,col):
    x=A[KEYS+[col]].merge(B[KEYS+[col]],on=KEYS,suffixes=("_a","_b"),how="inner")
    u=pd.to_numeric(x[col+"_a"],errors="coerce").to_numpy(float)
    v=pd.to_numeric(x[col+"_b"],errors="coerce").to_numpy(float)
    m=np.isfinite(u)&np.isfinite(v)
    d=np.abs(u-v)
    out={
        "n":int(m.sum()),
        "changed_fraction_gt1e12":float(np.mean(d[m]>1e-12)) if m.any() else None,
        "mean_abs":float(np.mean(d[m])) if m.any() else None,
        "p99_abs":float(np.quantile(d[m],.99)) if m.any() else None,
        "max_abs":float(np.max(d[m])) if m.any() else None,
    }
    vals=[]
    xa=x.loc[m,["signal_date",col+"_a",col+"_b"]].copy()
    for _,g in xa.groupby("signal_date"):
        if len(g)>=3:
            r=g[col+"_a"].corr(g[col+"_b"],method="spearman")
            if np.isfinite(r): vals.append(r)
    out["mean_daily_spearman"]=float(np.mean(vals)) if vals else None
    return out

def bool_metric(A,B,col):
    x=A[KEYS+[col]].merge(B[KEYS+[col]],on=KEYS,suffixes=("_a","_b"),how="inner")
    a=x[col+"_a"].astype(int).to_numpy()
    b=x[col+"_b"].astype(int).to_numpy()
    return {
        "n":int(len(x)),
        "disagreement_fraction":float(np.mean(a!=b)),
        "count_a":int(a.sum()),
        "count_b":int(b.sum()),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    root=Path(a.root)
    R={}
    sanity={}
    for i in (1,2,3):
        R[i],sanity[str(i)]=load_one(root/f"repeat{i}")
    cols=["compact21","tail","COMPACT21_RANK","TAIL_RANK","MIX_70_30","MACRO_BOOST","PRE_FINAL","TIT_R_REBUILT","TIT_R"]
    res={"status":"TITANIUM_COMPONENT_ABLATION_COMPLETE","sanity":sanity,"pairs":{}}
    for aa,bb in ((1,2),(1,3),(2,3)):
        q={c:metric(R[aa],R[bb],c) for c in cols}
        q["MACRO_CONDITION"]=bool_metric(R[aa],R[bb],"MACRO_CONDITION")
        res["pairs"][f"{aa}-{bb}"]=q
    res["PASS_REBUILD"]=bool(all(x["PASS"] for x in sanity.values()))
    Path(a.out).write_text(json.dumps(res,indent=2)+"\n")
    print(json.dumps(res,indent=2))
if __name__=="__main__":
    main()
