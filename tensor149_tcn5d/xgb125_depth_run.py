"""Original149 XGB125 depth-only ablation: max_depth 2..7, identical other settings.

Research only. Full daily-training, annual expanding walkforward 2017-2026.
Depth 4 must be byte/selection comparable to archived E_XGB_BASE.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBRanker, __version__ as xgboost_version
from tensor149_tcn5d.features import load_frozen,daily_compact,labels_next_open,eligible
from tensor149_tcn5d.run import HORIZON,LAST_MATURE,SEED,anchor_indices,sample_pairs,scoring_frame,nav_path
from tensor149_tcn5d.daily_ablation import signal_train_dates

DEPTHS=(2,3,4,5,6,7)
N_ESTIMATORS=240
PARAMS=dict(objective="rank:pairwise",eval_metric="rmse",n_estimators=240,
            learning_rate=.035,subsample=.85,colsample_bytree=.8,
            min_child_weight=8,reg_lambda=8.,reg_alpha=.1,tree_method="hist",
            n_jobs=2,verbosity=0,random_state=SEED)

def leaf_statistics(model):
    """Observed leaves per boosted binary tree, NOT theoretical 2**depth."""
    trees=model.get_booster().get_dump(dump_format="json")
    if len(trees)!=N_ESTIMATORS:raise ValueError("Unexpected number of XGBoost trees")
    # Dump leaf nodes contain the JSON key "leaf"; count exact occurrences.
    counts=np.asarray([raw.count('"leaf"') for raw in trees],dtype=int)
    if np.any(counts<1):raise ValueError("Tree has zero leaves")
    return dict(trees=int(len(trees)),leaves_mean=float(counts.mean()),
        leaves_median=float(np.median(counts)),leaves_max=int(counts.max()),
        leaves_min=int(counts.min()),leaves_p90=float(np.quantile(counts,.90)),
        fraction_full=float(np.mean(counts==2**model.max_depth)))

def fit_fold(X,y,dates,avail,year,depth,out):
    val0=pd.Timestamp(year-1,1,1)
    year0=pd.Timestamp(year,1,1)
    train=sample_pairs(signal_train_dates(dates,1),dates,avail,y,
        exit_before=val0,signal_after=pd.Timestamp("2008-01-01"))
    validation=sample_pairs(anchor_indices(dates),dates,avail,y,
        exit_before=year0,signal_after=val0)
    if len(train)<4000 or len(validation)<200:raise ValueError("Underpowered fold")
    train_exit=dates[train[:,0].max()+1+HORIZON]
    valid_exit=dates[validation[:,0].max()+1+HORIZON]
    if train_exit>=val0 or valid_exit>=year0:raise ValueError("Future labels in fold")
    counts_train=np.unique(train[:,0],return_counts=True)[1]
    counts_valid=np.unique(validation[:,0],return_counts=True)[1]
    model=XGBRanker(max_depth=depth,**PARAMS)
    model.fit(X[train[:,0],train[:,1]],y[train[:,0],train[:,1]],
       group=counts_train,
       eval_set=[(X[validation[:,0],validation[:,1]],
                  y[validation[:,0],validation[:,1]])],
       eval_group=[counts_valid],verbose=False)
    dest=out/f"XGB125_depth{depth}_year{year}.json"
    model.save_model(str(dest))
    statistics=leaf_statistics(model)
    if statistics["leaves_max"]>2**depth:raise ValueError("Exceeded max possible tree leaves")
    def predict(t,ids):
        return np.asarray(model.predict(np.asarray(X[t,ids],dtype=np.float32)),
                          dtype=np.float64).reshape(-1)
    audit=dict(year=year,depth=depth,nominal_max_leaves=2**depth,
      train_rows=int(len(train)),validation_rows=int(len(validation)),
      train_days=len(counts_train),validation_days=len(counts_valid),
      train_mature_exit=str(train_exit.date()),
      validation_mature_exit=str(valid_exit.date()),
      train_before=str(val0.date()),validation_before=str(year0.date()),
      model_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
      **statistics)
    return predict,audit

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="evidence_v1/data/original149")
    p.add_argument("--depth",type=int,required=True,choices=DEPTHS)
    p.add_argument("--years",default="2017,2018,2019,2020,2021,2022,2023,2024,2025,2026")
    p.add_argument("--out",required=True)
    args=p.parse_args()
    years=list(map(int,args.years.split(",")))
    if sorted(set(years))!=years or years[0]<2017 or years[-1]>2026:
        raise ValueError("Only original expanding annual OOS 2017-2026 support")
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    mats,raw_audit,roster_sha=load_frozen(args.raw)
    dates=mats["Open"].index
    names=list(mats["Open"].columns)
    if len(names)!=149:raise ValueError("Unchanged Original149 required")
    x=daily_compact(mats)
    if x.shape!=(len(dates),149,125):raise ValueError("Wrong features")
    ret,y=labels_next_open(mats,HORIZON)
    avail=eligible(x,mats["Open"].to_numpy(float))
    anchors=anchor_indices(dates)
    all_predictions=[];weekly=[];folds={}
    name=f"XGB125_DEPTH_{args.depth}"
    for year in years:
        predict,meta=fit_fold(x,y,dates,avail,year,args.depth,out)
        n=0
        for t in anchors:
            if dates[t].year!=year or dates[t]>pd.Timestamp("2026-06-30"):continue
            if dates[t+1+HORIZON]>LAST_MATURE:continue
            ids=np.flatnonzero(avail[t])
            if len(ids)<100 or not np.isfinite(ret[t,ids]).all():
                raise ValueError(f"Original availability/maturity mismatch {dates[t]}")
            scores=predict(int(t),ids)
            if len(scores)!=len(ids) or not np.isfinite(scores).all():
                raise ValueError("Invalid scores")
            frame=scoring_frame(dates[t],ids,ret[t],y[t],{name:scores},names)
            for row in frame:row["t_idx"]=int(t)
            weekly.extend(frame)
            all_predictions.extend((str(dates[t].date()),int(t),names[k],int(k),float(s),
               float(y[t,k]),float(ret[t,k])) for k,s in zip(ids,scores))
            n+=1
        folds[str(year)]={**meta,"oos_weeks":n}
        (out/"FOLDS.json").write_text(json.dumps(folds,indent=2)+"\n")
        print(json.dumps(dict(year=year,depth=args.depth,nominal_max_leaves=2**args.depth,
            actual_mean_leaves=meta["leaves_mean"],actual_max_leaves=meta["leaves_max"],
            oos_weeks=n,train_rows=meta["train_rows"])),flush=True)
    weekly=pd.DataFrame(weekly)
    if weekly.empty:raise ValueError("No OOS")
    weekly.to_csv(out/"OOS_WEEKLY_SELECTIONS.csv",index=False)
    pd.DataFrame(all_predictions,columns=("date","t_idx","ticker","ticker_id","pred_score",
          "realized_fwd_percentile_centered","realized_future_5d_return")).to_parquet(
          out/"ALL_OOS_SCORES.parquet",index=False)
    curve,econ=nav_path(weekly,dates,mats,name)
    curve.rename(name).to_csv(out/"DAILY_NET_EQUITY.csv",index_label="date")
    metrics=dict(**econ,rank_ic=float(weekly.rank_ic.mean()),
          top5_overlap=float(weekly.top5_overlap.mean()),
          top5_mean_future_return=float(weekly.top5_mean_future_return.mean()),
          topdecile_regret=float(weekly.topdecile_regret.mean()),
          top1_mean_future_return=float(weekly.top1_return.mean()))
    summary=dict(status="ORIGINAL149_XGB125_DEPTH_WALKFORWARD_COMPLETE",depth=args.depth,
        nominal_max_leaves=int(2**args.depth),original_roster_sha256=roster_sha,
        source_frozen=True,production_modified=False,feature_count=125,
        objective="rank:pairwise",target="open t+1 to open t+6 nominal percentile",
        training_stride=1,evaluation_stride=5,
        oos_weekly_dates=int(len(weekly)),eval_end="2026-06-30",
        config={**PARAMS,"max_depth":args.depth},xgboost_version=xgboost_version,
        raw_audit=raw_audit,folds=folds,metrics=metrics)
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:summary[k] for k in ("status","depth","nominal_max_leaves",
        "oos_weekly_dates","metrics")},indent=2),flush=True)
if __name__=="__main__":main()
