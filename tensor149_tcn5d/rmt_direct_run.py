"""Preregistered four new XGBRanker feature ablations against immutable XGB125.

Same date/ticker/target/maturity/parameters/trading rules as archived frozen XGB.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBRanker, __version__ as xgboost_version
from tensor149_tcn5d.features import FIELDS, load_frozen, daily_compact, labels_next_open, eligible
from tensor149_tcn5d.run import HORIZON, LAST_MATURE, SEED, anchor_indices, sample_pairs, scoring_frame, nav_path
from tensor149_tcn5d.daily_ablation import signal_train_dates

VARIANTS=("B_RMT_GLOBAL","C_RMT_ETF","D_RMT_BOTH","E_SIMPLE_CORREL")
EXTRAS={"B_RMT_GLOBAL":5,"C_RMT_ETF":5,"D_RMT_BOTH":10,"E_SIMPLE_CORREL":5}

def open_cache(cache_file,dates,names,sha):
    cache=np.load(cache_file,allow_pickle=False)
    if str(cache["roster_sha"].item())!=sha:raise ValueError("Changed Original149 roster")
    if not np.array_equal(cache["dates"],np.asarray(dates.strftime("%Y-%m-%d"),dtype="U10")):
        raise ValueError("RMT cache time index mismatch")
    if not np.array_equal(cache["tickers"],np.asarray(names,dtype="U32")):
        raise ValueError("RMT cache ticker order mismatch")
    return (np.asarray(cache["global_rmt"],dtype=np.float32),
            np.asarray(cache["etf_rmt"],dtype=np.float32),
            np.asarray(cache["control"],dtype=np.float32))

def prepare_variant(base,global_rmt,etf_rmt,control,variant):
    if variant not in VARIANTS:raise ValueError(variant)
    n=base.shape[1];T=base.shape[0]
    assert base.shape[-1]==125 and global_rmt.shape==(T,5) and etf_rmt.shape==(T,n,5)
    assert control.shape==etf_rmt.shape
    if variant=="B_RMT_GLOBAL": extra=np.broadcast_to(global_rmt[:,None,:],(T,n,5))
    elif variant=="C_RMT_ETF":extra=etf_rmt
    elif variant=="D_RMT_BOTH":extra=np.concatenate([np.broadcast_to(global_rmt[:,None,:],(T,n,5)),etf_rmt],axis=2)
    else:extra=control
    X=np.concatenate([base,extra],axis=2)
    if X.shape[-1]!=125+EXTRAS[variant]:raise ValueError("Unexpected count")
    return X

def fit_year(X,y,dates,avail,year,variant,out):
    val0=pd.Timestamp(year-1,1,1)
    year0=pd.Timestamp(year,1,1)
    train=sample_pairs(signal_train_dates(dates,1),dates,avail,y,exit_before=val0,
                      signal_after=pd.Timestamp("2008-01-01"))
    val=sample_pairs(anchor_indices(dates),dates,avail,y,exit_before=year0,signal_after=val0)
    if len(train)<4000 or len(val)<200:raise ValueError(f"Underpowered yearly fold {year}")
    assert dates[train[:,0].max()+1+HORIZON]<val0
    assert dates[val[:,0].max()+1+HORIZON]<year0
    group_train=np.unique(train[:,0],return_counts=True)[1]
    group_val=np.unique(val[:,0],return_counts=True)[1]
    model=XGBRanker(objective="rank:pairwise",eval_metric="rmse",n_estimators=240,
        max_depth=4,learning_rate=.035,subsample=.85,colsample_bytree=.8,
        min_child_weight=8,reg_lambda=8.,reg_alpha=.1,tree_method="hist",
        n_jobs=2,verbosity=0,random_state=SEED)
    model.fit(X[train[:,0],train[:,1]],y[train[:,0],train[:,1]],group=group_train,
        eval_set=[(X[val[:,0],val[:,1]],y[val[:,0],val[:,1]])],
        eval_group=[group_val],verbose=False)
    path=out/f"model_{variant}_{year}.json"
    model.save_model(str(path))
    def predict(t,ids):return np.asarray(model.predict(X[t,ids,:]),dtype=float).reshape(-1)
    audit=dict(year=year,train_rows=len(train),val_rows=len(val),
        train_days=int(len(group_train)),val_days=int(len(group_val)),
        train_last_exit=str(dates[train[:,0].max()+1+HORIZON].date()),
        val_last_exit=str(dates[val[:,0].max()+1+HORIZON].date()),
        train_before=str(val0.date()),val_before=str(year0.date()),
        model_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return predict,audit

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--raw",default="evidence_v1/data/original149")
    parser.add_argument("--cache",required=True)
    parser.add_argument("--variant",choices=VARIANTS,required=True)
    parser.add_argument("--years",default="2017,2018,2019,2020,2021,2022,2023,2024,2025,2026")
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    years=list(map(int,args.years.split(",")))
    if not years or sorted(set(years))!=years or years[0]<2017 or years[-1]>2026:raise ValueError("Invalid requested years")
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    mats,raw_audit,sha=load_frozen(args.raw)
    dates=mats["Open"].index;names=list(mats["Open"].columns)
    base=daily_compact(mats)
    G,E,C=open_cache(args.cache,dates,names,sha)
    features=prepare_variant(base,G,E,C,args.variant)
    returns,y=labels_next_open(mats,HORIZON)
    original_eligibility=eligible(base,mats["Open"].to_numpy(float))
    anchors=anchor_indices(dates)
    allrows=[];allsc=[];audits={}
    for yr in years:
        predict,fold=fit_year(features,y,dates,original_eligibility,yr,args.variant,out)
        n=0
        for t in anchors:
            if dates[t].year!=yr or dates[t]>pd.Timestamp("2026-06-30"):continue
            if dates[t+1+HORIZON]>LAST_MATURE:continue
            ids=np.flatnonzero(original_eligibility[t])
            if len(ids)<100:raise ValueError(f"Failed 100 eligible at {dates[t]}")
            target=returns[t,ids]
            if not np.isfinite(target).all():raise ValueError("Unmatured OOS future")
            score=predict(int(t),ids)
            if not np.isfinite(score).all():raise ValueError("Nonfinite XGB score")
            rows=scoring_frame(dates[t],ids,returns[t],y[t],{args.variant:score},names)
            for row in rows:row["t_idx"]=int(t)
            allrows.extend(rows)
            allsc.extend((str(dates[t].date()),int(t),names[q],int(q),float(s),
                  float(y[t,q]),float(returns[t,q])) for q,s in zip(ids,score))
            n+=1
        audits[str(yr)]={**fold,"weekly_oos_decisions":n}
        (out/"FOLDS.json").write_text(json.dumps(audits,indent=2)+"\n")
        print(json.dumps(dict(year=yr,variant=args.variant,weeks=n,train_rows=fold["train_rows"],
          val_rows=fold["val_rows"])),flush=True)
    weekly=pd.DataFrame(allrows)
    if weekly.empty:raise ValueError("No OOS weeks")
    weekly.to_csv(out/"OOS_WEEKLY_SELECTIONS.csv",index=False)
    pd.DataFrame(allsc,columns=("date","t_idx","ticker","ticker_id","pred_score",
        "realized_fwd_percentile_centered","realized_future_5d_return")).to_parquet(
            out/"ALL_OOS_SCORES.parquet",index=False)
    wealth,eco=nav_path(weekly,dates,mats,args.variant)
    wealth.rename(args.variant).to_csv(out/"DAILY_NET_EQUITY.csv",index_label="date")
    metrics=dict(**eco,rank_ic=float(weekly.rank_ic.mean()),
         top5_overlap=float(weekly.top5_overlap.mean()),
         top5_mean_future_return=float(weekly.top5_mean_future_return.mean()))
    result=dict(status="ORIGINAL149_RMT_XGB_FEATURE_ABLATION_COMPLETE",
        variant=args.variant,roster_sha=sha,feature_count=int(features.shape[-1]),
        same_original_eligibility=True,target="cross-sectional percentile of future open(t+1) to open(t+6) returns",
        oos_weeks=len(weekly),weekly_oos_2017_26=len(weekly)==476,
        research_branch_only=True,
        xgboost_version=xgboost_version,hyperparams=dict(n_estimators=240,max_depth=4,
            lr=.035,subsample=.85,colsample_bytree=.8,min_child_weight=8,
            reg_lambda=8.,reg_alpha=.1,objective="rank:pairwise",eval_metric="rmse"),
        folds=audits,raw_audit=raw_audit,metrics=metrics)
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(dict(status=result["status"],variant=args.variant,
              weeks=len(weekly),metrics=metrics),indent=2),flush=True)

if __name__=="__main__":main()
