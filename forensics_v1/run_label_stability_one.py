#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys,tempfile
from pathlib import Path
import numpy as np,pandas as pd
from etf_trader.source_only import kernel as k

KEYS=["signal_date","ticker"]

def load(root):
    f=pd.read_parquet(Path(root)/"TI_COMPACT.parquet").copy()
    f["signal_date"]=pd.to_datetime(f["signal_date"])
    f["exit_date_21"]=pd.to_datetime(f["exit_date_21"])
    return f

def frame(f,year,train):
    valid=f[k.F2D_FEATURES].notna().sum(axis=1)>=30
    if train:
        c=pd.Timestamp(year,1,1)
        z=f[(f.signal_date<c)&(f.exit_date_21<c)&f.target_rank_21.notna()&valid]
    else:
        z=f[(f.signal_date.dt.year==year)&valid]
    return z.sort_values(KEYS).copy()

def align(a,b):
    keys=a[KEYS].merge(b[KEYS],on=KEYS,how="inner").drop_duplicates().sort_values(KEYS)
    return keys.merge(a,on=KEYS,how="left",validate="one_to_one"),keys.merge(b,on=KEYS,how="left",validate="one_to_one")

def mat(df,dec):
    X=df[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan).to_numpy(float)
    return np.round(X,decimals=dec) if dec is not None else X

def labels(df,bins):
    return (df.target_rank_21*bins).round().astype(int).to_numpy()

def groups(df):
    return df.groupby("signal_date",sort=True).size().to_numpy()

def run(Xtr,yv,gr,Xte,tmp,tag):
    params=dict(k.COMPACT_PARAMS)
    rounds=int(params.pop("n_estimators"));params.pop("n_jobs",None)
    worker=Path(k.__file__).with_name("_xgb_worker.py")
    data=tmp/f"{tag}.npz";np.savez(data,Xtr=Xtr,Xte=Xte,y=yv,groups=gr)
    pj=json.dumps(params,separators=(",",":"),sort_keys=True);ps=[]
    for seed in k.COMPACT_SEEDS:
        out=tmp/f"{tag}_{seed}.npy"
        subprocess.run([sys.executable,str(worker),"--data",str(data),"--seed",str(int(seed)),"--threads","1","--rounds",str(rounds),"--params-json",pj,"--output",str(out)],check=True)
        ps.append(np.load(out))
    return np.mean(ps,axis=0)

def metric(keys,pa,pb):
    A=keys.copy();B=keys.copy();A["p"]=pa;B["p"]=pb
    A["r"]=A.groupby("signal_date")["p"].rank(method="average",pct=True)
    B["r"]=B.groupby("signal_date")["p"].rank(method="average",pct=True)
    d=np.abs(pa-pb);rd=np.abs(A.r.to_numpy()-B.r.to_numpy());ss=[];td=[]
    for dt,ga in A.groupby("signal_date"):
        gb=B.loc[ga.index]
        rr=ga.r.corr(gb.r,method="spearman")
        if np.isfinite(rr):ss.append(rr)
        td.append(ga.loc[ga.r.idxmax(),"ticker"]!=gb.loc[gb.r.idxmax(),"ticker"])
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

def exact(a,b):
    m=np.isfinite(a)&np.isfinite(b)
    return float(np.mean(a[m]==b[m])) if m.any() else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--r1",required=True);ap.add_argument("--r3",required=True)
    ap.add_argument("--year",type=int,required=True)
    ap.add_argument("--variant",choices=["BASE","L50","Q4_L50"],required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    dec=4 if a.variant=="Q4_L50" else None
    bins=100 if a.variant=="BASE" else 50
    f1,f3=load(a.r1),load(a.r3)
    tr1,tr3=align(frame(f1,a.year,True),frame(f3,a.year,True))
    te1,te3=align(frame(f1,a.year,False),frame(f3,a.year,False))
    with tempfile.TemporaryDirectory() as td:
        p1=run(mat(tr1,dec),labels(tr1,bins),groups(tr1),mat(te1,dec),Path(td),"r1")
        p3=run(mat(tr3,dec),labels(tr3,bins),groups(tr3),mat(te3,dec),Path(td),"r3")
    q=metric(te1[KEYS],p1,p3)
    q.update({
      "status":"COMPACT21_LABEL_STABILITY_CELL_COMPLETE",
      "year":a.year,"variant":a.variant,"feature_decimals":dec,"label_bins":bins,
      "train_feature_exact_fraction":exact(mat(tr1,dec),mat(tr3,dec)),
      "test_feature_exact_fraction":exact(mat(te1,dec),mat(te3,dec)),
      "label_disagreement_fraction":float(np.mean(labels(tr1,bins)!=labels(tr3,bins)))
    })
    Path(a.out).write_text(json.dumps(q,indent=2)+"\n")
    print(json.dumps(q,indent=2))

if __name__=="__main__":
    main()
