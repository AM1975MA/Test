#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, os, subprocess, sys, tempfile, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import ndcg_score
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"vendor/etf_trader_v2/src"))
from etf_trader.source_only import kernel as k

DEFAULT_YEARS=(2017,2020,2023,2026)
KEYS=["signal_date","ticker"]
SEEDS=(101,202,303)

def load(p:Path):
    f=pd.read_parquet(p/"TI_COMPACT.parquet").copy()
    f["signal_date"]=pd.to_datetime(f["signal_date"])
    f["exit_date_21"]=pd.to_datetime(f["exit_date_21"])
    return f

def train_frame(f,year):
    cutoff=pd.Timestamp(year,1,1)
    valid=f[k.F2D_FEATURES].notna().sum(axis=1)>=30
    return f[(f.signal_date<cutoff)&(f.exit_date_21<cutoff)&f.target_rank_21.notna()&valid].sort_values(KEYS).copy()

def test_frame(f,year):
    valid=f[k.F2D_FEATURES].notna().sum(axis=1)>=30
    return f[(f.signal_date.dt.year==year)&f.target_rank_21.notna()&valid].sort_values(KEYS).copy()

def align(frames):
    keys=frames[0][KEYS].copy()
    for z in frames[1:]: keys=keys.merge(z[KEYS],on=KEYS,how="inner")
    keys=keys.drop_duplicates().sort_values(KEYS).reset_index(drop=True)
    return [keys.merge(z,on=KEYS,how="left",validate="one_to_one") for z in frames]

def X(df):
    return df[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)

def y_int(df):
    return (df.target_rank_21.clip(0,1)*100).round().astype(int).to_numpy()

def groups(df):
    return df.groupby("signal_date",sort=True).size().to_numpy()

def group_ids(df):
    return pd.factorize(df["signal_date"],sort=True)[0]

def fit_predict(model,tr,tests,tmp:Path,tag:str):
    Xtr=X(tr); y=y_int(tr); gs=groups(tr)
    Xtests=[X(t) for t in tests]
    t0=time.perf_counter()

    if model=="XGB_CANONICAL":
        params=dict(k.COMPACT_PARAMS)
        rounds=int(params.pop("n_estimators")); params.pop("n_jobs",None)
        worker=Path(k.__file__).with_name("_xgb_worker.py")
        sizes=[len(z) for z in Xtests]; Xte=pd.concat(Xtests,axis=0).to_numpy()
        data=tmp/f"{tag}.npz"
        np.savez(data,Xtr=Xtr.to_numpy(),Xte=Xte,y=y,groups=gs)
        preds=[]
        pj=json.dumps(params,separators=(",",":"),sort_keys=True)
        for seed in SEEDS:
            out=tmp/f"{tag}_{seed}.npy"
            subprocess.run([sys.executable,str(worker),"--data",str(data),"--seed",str(seed),"--threads","1","--rounds",str(rounds),"--params-json",pj,"--output",str(out)],check=True)
            preds.append(np.load(out))
        p=np.mean(preds,axis=0)
        ans=[]; pos=0
        for n in sizes: ans.append(p[pos:pos+n]); pos+=n

    elif model in ("LGBM_XENDCG","LGBM_LAMBDARANK"):
        from lightgbm import LGBMRanker
        objective="rank_xendcg" if model=="LGBM_XENDCG" else "lambdarank"
        bytest=[]
        for seed in SEEDS:
            m=LGBMRanker(
                objective=objective,n_estimators=360,learning_rate=0.035,
                max_depth=4,num_leaves=15,min_child_samples=40,
                subsample=0.85,subsample_freq=1,colsample_bytree=0.8,
                reg_lambda=8.0,reg_alpha=0.1,random_state=seed,n_jobs=1,
                deterministic=True,force_col_wise=True,verbosity=-1,
                label_gain=list(range(101)),
            )
            m.fit(Xtr,y,group=gs)
            bytest.append([m.predict(z) for z in Xtests])
        ans=[np.mean([bytest[s][j] for s in range(len(SEEDS))],axis=0) for j in range(len(Xtests))]

    elif model=="CAT_YETI":
        from catboost import CatBoostRanker
        bytest=[]
        gid=group_ids(tr)
        for seed in SEEDS:
            m=CatBoostRanker(
                loss_function="YetiRankPairwise",
                iterations=360,depth=4,learning_rate=0.035,l2_leaf_reg=8.0,
                random_seed=seed,thread_count=1,verbose=False,allow_writing_files=False,
            )
            m.fit(Xtr,y,group_id=gid,verbose=False)
            bytest.append([m.predict(z) for z in Xtests])
        ans=[np.mean([bytest[s][j] for s in range(len(SEEDS))],axis=0) for j in range(len(Xtests))]

    elif model=="RIDGE_POINTWISE":
        m=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=30.0))
        m.fit(Xtr,tr.target_rank_21.to_numpy(float))
        ans=[m.predict(z) for z in Xtests]
    else:
        raise ValueError(model)

    return ans, time.perf_counter()-t0

def ranked(keys,p):
    z=keys.copy(); z["pred"]=np.asarray(p,float)
    z["rank"]=z.groupby("signal_date")["pred"].rank(method="average",pct=True)
    return z

def stability(keys,pa,pb):
    A=ranked(keys,pa); B=ranked(keys,pb)
    rd=np.abs(A["rank"].to_numpy()-B["rank"].to_numpy())
    spears=[]; topdiff=[]; jacc=[]
    for dt,ga in A.groupby("signal_date"):
        gb=B[B.signal_date==dt]
        if len(ga)!=len(gb): continue
        aa=ga.sort_values("ticker"); bb=gb.sort_values("ticker")
        r=aa["rank"].corr(bb["rank"],method="spearman")
        if np.isfinite(r): spears.append(float(r))
        ta=aa.nlargest(1,"rank").ticker.iloc[0]; tb=bb.nlargest(1,"rank").ticker.iloc[0]
        topdiff.append(ta!=tb)
        sa=set(aa.nlargest(5,"rank").ticker); sb=set(bb.nlargest(5,"rank").ticker)
        jacc.append(len(sa&sb)/len(sa|sb))
    return {
        "rank_mean_abs":float(np.mean(rd)),
        "rank_p99_abs":float(np.quantile(rd,.99)),
        "mean_daily_spearman":float(np.mean(spears)),
        "top1_disagreement_fraction":float(np.mean(topdiff)),
        "top5_jaccard":float(np.mean(jacc)),
    }

def quality(df,p):
    z=df[KEYS+["target_rank_21"]].copy(); z["pred"]=p
    spears=[]; n5=[]; n10=[]; top1=[]; ov5=[]
    for _,g in z.groupby("signal_date"):
        if len(g)<10: continue
        r=g["pred"].corr(g["target_rank_21"],method="spearman")
        if np.isfinite(r): spears.append(float(r))
        yt=g["target_rank_21"].to_numpy(float)[None,:]
        yp=g["pred"].to_numpy(float)[None,:]
        n5.append(float(ndcg_score(yt,yp,k=5)))
        n10.append(float(ndcg_score(yt,yp,k=10)))
        top1.append(float(g.loc[g["pred"].idxmax(),"target_rank_21"]))
        sp=set(g.nlargest(5,"pred").ticker); st=set(g.nlargest(5,"target_rank_21").ticker)
        ov5.append(len(sp&st)/5.0)
    return {
        "daily_spearman_vs_target":float(np.mean(spears)),
        "ndcg5":float(np.mean(n5)),
        "ndcg10":float(np.mean(n10)),
        "pred_top1_mean_realized_pct":float(np.mean(top1)),
        "top5_realized_overlap":float(np.mean(ov5)),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",required=True,choices=["XGB_CANONICAL","LGBM_XENDCG","LGBM_LAMBDARANK","CAT_YETI","RIDGE_POINTWISE"])
    ap.add_argument("--r1",required=True); ap.add_argument("--r2",required=True); ap.add_argument("--r3",required=True)
    ap.add_argument("--out",required=True); ap.add_argument("--years",default="2017,2020,2023,2026")
    a=ap.parse_args()
    R={1:load(Path(a.r1)),2:load(Path(a.r2)),3:load(Path(a.r3))}
    res={"status":"RANKER_STABILITY_V1_MODEL_COMPLETE","model":a.model,"years":list(YEARS),"per_year":{}}
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td)
        for year in years:
            trs={i:train_frame(R[i],year) for i in (1,2,3)}
            tes={i:test_frame(R[i],year) for i in (1,2,3)}
            tr1,tr2,tr3=align([trs[1],trs[2],trs[3]])
            te1,te2,te3=align([tes[1],tes[2],tes[3]])

            # Stability: native Repeat1 vs Repeat3 training, common fixed Repeat2 test features.
            p1,t1=fit_predict(a.model,tr1,[te2],tmp,f"{a.model}_{year}_r1")
            p3,t3=fit_predict(a.model,tr3,[te2],tmp,f"{a.model}_{year}_r3")
            stab=stability(te2[KEYS],p1[0],p3[0])

            # Quality and determinism: Repeat2 native training/testing, repeated independently.
            p2,t2=fit_predict(a.model,tr2,[te2],tmp,f"{a.model}_{year}_r2a")
            p2b,t2b=fit_predict(a.model,tr2,[te2],tmp,f"{a.model}_{year}_r2b")
            det=np.abs(np.asarray(p2[0])-np.asarray(p2b[0]))
            qual=quality(te2,p2[0])

            cutoff=pd.Timestamp(year,1,1)
            maturity=bool((tr2.exit_date_21<cutoff).all())
            res["per_year"][str(year)]={
                "stability":stab,"quality":qual,
                "timing_seconds":{"repeat1":t1,"repeat3":t3,"repeat2a":t2,"repeat2b":t2b,"mean_fit_predict":float(np.mean([t1,t3,t2,t2b]))},
                "determinism":{"max_abs":float(np.max(det)),"mean_abs":float(np.mean(det)),"PASS":bool(np.max(det)<1e-12)},
                "train_rows":int(len(tr2)),"test_rows":int(len(te2)),"maturity_PASS":maturity,
            }

    def mean(path):
        vals=[]
        for y in years:
            q=res["per_year"][str(y)]
            for p in path: q=q[p]
            vals.append(q)
        return float(np.mean(vals))
    res["aggregate_mean"]={
        "rank_mean_abs":mean(["stability","rank_mean_abs"]),
        "mean_daily_spearman_stability":mean(["stability","mean_daily_spearman"]),
        "top1_disagreement_fraction":mean(["stability","top1_disagreement_fraction"]),
        "top5_jaccard":mean(["stability","top5_jaccard"]),
        "daily_spearman_vs_target":mean(["quality","daily_spearman_vs_target"]),
        "ndcg5":mean(["quality","ndcg5"]),
        "ndcg10":mean(["quality","ndcg10"]),
        "pred_top1_mean_realized_pct":mean(["quality","pred_top1_mean_realized_pct"]),
        "top5_realized_overlap":mean(["quality","top5_realized_overlap"]),
        "mean_fit_predict_seconds":mean(["timing_seconds","mean_fit_predict"]),
    }
    res["ALL_MATURITY_PASS"]=bool(all(res["per_year"][str(y)]["maturity_PASS"] for y in years))
    res["ALL_DETERMINISM_PASS"]=bool(all(res["per_year"][str(y)]["determinism"]["PASS"] for y in YEARS))
    Path(a.out).write_text(json.dumps(res,indent=2)+"\n")
    print(json.dumps(res,indent=2))
if __name__=="__main__":
    main()
