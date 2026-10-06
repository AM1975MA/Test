#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from etf_trader.source_only import kernel as k

YEARS=(2017,2020,2023,2026)
KEYS=["signal_date","ticker"]

def load(root):
    f=pd.read_parquet(Path(root)/"TI_COMPACT.parquet").copy()
    f["signal_date"]=pd.to_datetime(f["signal_date"])
    f["exit_date_21"]=pd.to_datetime(f["exit_date_21"])
    return f

def frame(f,year,train):
    valid=f[k.F2D_FEATURES].notna().sum(axis=1)>=30
    if train:
        cutoff=pd.Timestamp(year,1,1)
        z=f[(f.signal_date<cutoff)&(f.exit_date_21<cutoff)&f.target_rank_21.notna()&valid]
    else:
        z=f[(f.signal_date.dt.year==year)&valid]
    return z.sort_values(KEYS).copy()

def mat(df,decimals):
    X=df[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan).to_numpy(float)
    if decimals is not None:
        X=np.round(X,decimals=decimals)
    return X

def y(df):
    return (df.target_rank_21*100).round().astype(int).to_numpy()

def groups(df):
    return df.groupby("signal_date",sort=True).size().to_numpy()

def run(Xtr,yv,gr,Xte,tmp,tag):
    params=dict(k.COMPACT_PARAMS)
    rounds=int(params.pop("n_estimators")); params.pop("n_jobs",None)
    worker=Path(k.__file__).with_name("_xgb_worker.py")
    data=tmp/f"{tag}.npz"; np.savez(data,Xtr=Xtr,Xte=Xte,y=yv,groups=gr)
    ps=[]
    pj=json.dumps(params,separators=(",",":"),sort_keys=True)
    for seed in k.COMPACT_SEEDS:
        out=tmp/f"{tag}_{seed}.npy"
        subprocess.run([sys.executable,str(worker),"--data",str(data),"--seed",str(int(seed)),"--threads","1","--rounds",str(rounds),"--params-json",pj,"--output",str(out)],check=True)
        ps.append(np.load(out))
    return np.mean(ps,axis=0)

def common_test(a,b):
    keys=a[KEYS].merge(b[KEYS],on=KEYS,how="inner").drop_duplicates().sort_values(KEYS)
    return keys.merge(a,on=KEYS,how="left",validate="one_to_one"),keys.merge(b,on=KEYS,how="left",validate="one_to_one")

def metric(keys,pa,pb):
    A=keys.copy();B=keys.copy();A["p"]=pa;B["p"]=pb
    A["r"]=A.groupby("signal_date")["p"].rank(method="average",pct=True)
    B["r"]=B.groupby("signal_date")["p"].rank(method="average",pct=True)
    d=np.abs(pa-pb); rd=np.abs(A.r.to_numpy()-B.r.to_numpy())
    ss=[]; td=[]
    for dt,ga in A.groupby("signal_date"):
        idx=ga.index
        gb=B.loc[idx]
        rr=ga["r"].corr(gb["r"],method="spearman")
        if np.isfinite(rr): ss.append(rr)
        td.append(ga.loc[ga["r"].idxmax(),"ticker"] != gb.loc[gb["r"].idxmax(),"ticker"])
    return {
      "n":int(len(keys)),
      "raw_mean_abs":float(np.mean(d)),
      "raw_max_abs":float(np.max(d)),
      "rank_mean_abs":float(np.mean(rd)),
      "rank_p99_abs":float(np.quantile(rd,.99)),
      "rank_max_abs":float(np.max(rd)),
      "mean_daily_spearman":float(np.mean(ss)),
      "top1_disagreement_fraction":float(np.mean(td)),
    }

def exact_fraction(X1,X3):
    m=np.isfinite(X1)&np.isfinite(X3)
    return float(np.mean(X1[m]==X3[m])) if m.any() else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--r1",required=True);ap.add_argument("--r2",required=True);ap.add_argument("--r3",required=True);ap.add_argument("--out",required=True)
    a=ap.parse_args()
    R={1:load(a.r1),2:load(a.r2),3:load(a.r3)}
    variants={"BASE":None,"Q4":4,"Q3":3}
    res={"status":"FEATURE_QUANTIZATION_V1_COMPLETE","years":list(YEARS),"variants":{}}
    with tempfile.TemporaryDirectory() as td:
      tmp=Path(td)
      for v,dec in variants.items():
        vr={"decimals":dec,"per_year":{}}
        for yr in YEARS:
            tr={i:frame(R[i],yr,True) for i in (1,2,3)}
            te={i:frame(R[i],yr,False) for i in (1,2,3)}
            te1,te3=common_test(te[1],te[3])
            Xtr1=mat(tr[1],dec); Xtr3=mat(tr[3],dec)
            Xte1=mat(te1,dec); Xte3=mat(te3,dec)
            p1=run(Xtr1,y(tr[1]),groups(tr[1]),Xte1,tmp,f"{v}_{yr}_r1")
            p3=run(Xtr3,y(tr[3]),groups(tr[3]),Xte3,tmp,f"{v}_{yr}_r3")
            q=metric(te1[KEYS],p1,p3)
            # aligned feature equality at inference
            q["test_feature_exact_fraction"]=exact_fraction(Xte1,Xte3)
            # training exact fraction on common keys
            ckeys=tr[1][KEYS].merge(tr[3][KEYS],on=KEYS,how="inner").drop_duplicates().sort_values(KEYS)
            c1=ckeys.merge(tr[1],on=KEYS,how="left",validate="one_to_one")
            c3=ckeys.merge(tr[3],on=KEYS,how="left",validate="one_to_one")
            q["train_feature_exact_fraction"]=exact_fraction(mat(c1,dec),mat(c3,dec))
            q["integer_label_disagreement_fraction"]=float(np.mean(y(c1)!=y(c3)))
            vr["per_year"][str(yr)]=q
        fields=["raw_mean_abs","rank_mean_abs","mean_daily_spearman","top1_disagreement_fraction","test_feature_exact_fraction","train_feature_exact_fraction"]
        vr["aggregate_mean"]={f:float(np.mean([vr["per_year"][str(y0)][f] for y0 in YEARS])) for f in fields}
        res["variants"][v]=vr
    base=res["variants"]["BASE"]["aggregate_mean"]
    for v in ("Q4","Q3"):
        cur=res["variants"][v]["aggregate_mean"]
        cur["rank_mean_abs_reduction_vs_base_pct"]=float(100*(base["rank_mean_abs"]-cur["rank_mean_abs"])/base["rank_mean_abs"]) if base["rank_mean_abs"] else None
        cur["top1_disagreement_reduction_vs_base_pct"]=float(100*(base["top1_disagreement_fraction"]-cur["top1_disagreement_fraction"])/base["top1_disagreement_fraction"]) if base["top1_disagreement_fraction"] else None
    Path(a.out).write_text(json.dumps(res,indent=2)+"\n")
    print(json.dumps(res,indent=2))
if __name__=="__main__": main()
