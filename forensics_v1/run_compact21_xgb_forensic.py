#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from etf_trader.source_only import kernel as k

YEARS=(2017,2020,2023,2026)
KEYS=["signal_date","ticker"]

def load(root):
    f=pd.read_parquet(root/"TI_COMPACT.parquet").copy()
    f["signal_date"]=pd.to_datetime(f["signal_date"])
    f["exit_date_21"]=pd.to_datetime(f["exit_date_21"])
    s=pd.read_parquet(root/"TI_MODEL_RAW_SCORES.parquet").copy()
    s["signal_date"]=pd.to_datetime(s["signal_date"])
    return f,s

def train_frame(f,year):
    cutoff=pd.Timestamp(year,1,1)
    valid=f[k.F2D_FEATURES].notna().sum(axis=1)>=30
    return f[(f.signal_date<cutoff)&(f.exit_date_21<cutoff)&f.target_rank_21.notna()&valid].sort_values(KEYS).copy()

def test_frame(f,year):
    valid=f[k.F2D_FEATURES].notna().sum(axis=1)>=30
    return f[(f.signal_date.dt.year==year)&valid].sort_values(KEYS).copy()

def align(frames):
    keys=frames[0][KEYS].copy()
    for z in frames[1:]:
        keys=keys.merge(z[KEYS],on=KEYS,how="inner")
    keys=keys.drop_duplicates().sort_values(KEYS).reset_index(drop=True)
    out=[]
    for z in frames:
        out.append(keys.merge(z,on=KEYS,how="left",validate="one_to_one"))
    return out

def xmat(df):
    return df[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan).to_numpy()

def run_ensemble(Xtr,y,groups,Xtests,tmp,tag):
    params=dict(k.COMPACT_PARAMS); rounds=int(params.pop("n_estimators")); params.pop("n_jobs",None)
    worker=Path(k.__file__).with_name("_xgb_worker.py")
    data=tmp/f"{tag}.npz"
    sizes=[len(x) for x in Xtests]
    Xte=np.vstack(Xtests)
    np.savez(data,Xtr=Xtr,Xte=Xte,y=y,groups=groups)
    preds=[]
    params_json=json.dumps(params,separators=(",",":"),sort_keys=True)
    for seed in k.COMPACT_SEEDS:
        out=tmp/f"{tag}_{seed}.npy"
        cmd=[sys.executable,str(worker),"--data",str(data),"--seed",str(int(seed)),"--threads","1","--rounds",str(rounds),"--params-json",params_json,"--output",str(out)]
        subprocess.run(cmd,check=True)
        preds.append(np.load(out))
    p=np.mean(preds,axis=0)
    ans=[]; pos=0
    for n in sizes:
        ans.append(p[pos:pos+n]); pos+=n
    return ans

def ranks(keys,p):
    z=keys.copy(); z["p"]=p
    z["r"]=z.groupby("signal_date")["p"].rank(method="average",pct=True)
    return z

def compare(keys,pa,pb):
    A=ranks(keys,pa); B=ranks(keys,pb)
    d=np.abs(pa-pb); rd=np.abs(A.r.to_numpy()-B.r.to_numpy())
    ss=[]
    topdiff=[]
    for dt,g in A.assign(rb=B.r.to_numpy()).groupby("signal_date"):
        if len(g)>=3:
            rr=g["r"].corr(g["rb"],method="spearman")
            if np.isfinite(rr): ss.append(rr)
            ia=int(g["r"].to_numpy().argmax()); ib=int(g["rb"].to_numpy().argmax())
            topdiff.append(ia!=ib)
    return {
      "n":int(len(keys)),"raw_mean_abs":float(np.mean(d)),"raw_max_abs":float(np.max(d)),
      "rank_mean_abs":float(np.mean(rd)),"rank_p99_abs":float(np.quantile(rd,.99)),"rank_max_abs":float(np.max(rd)),
      "mean_daily_spearman":float(np.mean(ss)) if ss else None,
      "top1_disagreement_fraction":float(np.mean(topdiff)) if topdiff else None,
    }

def groups_for(tr):
    return tr.groupby("signal_date",sort=True).size().to_numpy()

def y_for(tr):
    return (tr.target_rank_21*100).round().astype(int).to_numpy()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--r1",required=True);ap.add_argument("--r2",required=True);ap.add_argument("--r3",required=True);ap.add_argument("--out",required=True)
    a=ap.parse_args()
    R={1:load(Path(a.r1)),2:load(Path(a.r2)),3:load(Path(a.r3))}
    res={"status":"COMPACT21_XGB_FORENSIC_V1_COMPLETE","years":list(YEARS),"pair":"1-3","per_year":{}}
    with tempfile.TemporaryDirectory() as td:
      tmp=Path(td)
      for year in YEARS:
        trs={i:train_frame(R[i][0],year) for i in (1,2,3)}
        tes={i:test_frame(R[i][0],year) for i in (1,2,3)}
        ct1,ct2,ct3=align([tes[1],tes[2],tes[3]])
        ctr1,ctr2,ctr3=align([trs[1],trs[2],trs[3]])
        Xtest={1:xmat(ct1),2:xmat(ct2),3:xmat(ct3)}
        q={}

        # Inference-only: identical Repeat2 model, variant test features.
        pi=run_ensemble(xmat(trs[2]),y_for(trs[2]),groups_for(trs[2]),[Xtest[1],Xtest[2],Xtest[3]],tmp,f"y{year}_infer")
        q["inference_features_1_vs_3"]=compare(ct2[KEYS],pi[0],pi[2])
        q["inference_features_1_vs_2"]=compare(ct2[KEYS],pi[0],pi[1])
        q["inference_features_2_vs_3"]=compare(ct2[KEYS],pi[1],pi[2])

        # Total training perturbation: native train1/train3, identical Repeat2 test features.
        p1=run_ensemble(xmat(trs[1]),y_for(trs[1]),groups_for(trs[1]),[Xtest[2]],tmp,f"y{year}_tr1")[0]
        p3=run_ensemble(xmat(trs[3]),y_for(trs[3]),groups_for(trs[3]),[Xtest[2]],tmp,f"y{year}_tr3")[0]
        q["training_total_1_vs_3"]=compare(ct2[KEYS],p1,p3)

        # Training-feature only on common rows, fixed Repeat2 labels.
        y2=y_for(ctr2); grp=groups_for(ctr2)
        pf1=run_ensemble(xmat(ctr1),y2,grp,[Xtest[2]],tmp,f"y{year}_feat1")[0]
        pf3=run_ensemble(xmat(ctr3),y2,grp,[Xtest[2]],tmp,f"y{year}_feat3")[0]
        q["training_features_only_1_vs_3"]=compare(ct2[KEYS],pf1,pf3)

        # Training-label only on fixed Repeat2 features, common rows.
        pl1=run_ensemble(xmat(ctr2),y_for(ctr1),grp,[Xtest[2]],tmp,f"y{year}_lab1")[0]
        pl3=run_ensemble(xmat(ctr2),y_for(ctr3),grp,[Xtest[2]],tmp,f"y{year}_lab3")[0]
        q["training_labels_only_1_vs_3"]=compare(ct2[KEYS],pl1,pl3)
        q["training_common_rows"]=int(len(ctr2)); q["test_common_rows"]=int(len(ct2))
        q["integer_label_disagreement_fraction_1_3"]=float(np.mean(y_for(ctr1)!=y_for(ctr3)))

        # Native sanity against stored compact21 for r2.
        pn=run_ensemble(xmat(trs[2]),y_for(trs[2]),groups_for(trs[2]),[xmat(tes[2])],tmp,f"y{year}_sanity")[0]
        art=R[2][1]
        art=art[art.signal_date.dt.year==year][KEYS+["compact21"]].sort_values(KEYS)
        native=tes[2][KEYS].merge(art,on=KEYS,how="inner",validate="one_to_one")
        if len(native)!=len(tes[2]): raise RuntimeError("sanity key mismatch")
        sd=np.abs(pn-native.compact21.to_numpy(float))
        q["repeat2_native_sanity"]={"n":len(sd),"max_abs":float(np.max(sd)),"mean_abs":float(np.mean(sd)),"PASS":bool(np.max(sd)<1e-7)}
        res["per_year"][str(year)]=q

    # Aggregate simple means across predeclared years for attribution.
    names=["inference_features_1_vs_3","training_total_1_vs_3","training_features_only_1_vs_3","training_labels_only_1_vs_3"]
    agg={}
    for n in names:
        vals=[res["per_year"][str(y)][n] for y in YEARS]
        agg[n]={k:float(np.mean([v[k] for v in vals])) for k in ["raw_mean_abs","rank_mean_abs","mean_daily_spearman","top1_disagreement_fraction"]}
    res["aggregate_mean_across_years"]=agg
    res["SANITY_PASS"]=bool(all(res["per_year"][str(y)]["repeat2_native_sanity"]["PASS"] for y in YEARS))
    Path(a.out).write_text(json.dumps(res,indent=2)+"\n")
    print(json.dumps(res,indent=2))
if __name__=="__main__": main()
