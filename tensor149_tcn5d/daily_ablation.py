"""Fixed weekly 2017-2026 OOS Original149 causal daily-train / R1 R2 ablation.

A is an external immutable original weekly-trained TCN control. B,C,D keep
pointwise original SmoothL1 and TCN policy exactly except training-date stride
and stated feature block. E XGBoost ranking & CatBoost ranking, same D features.
No future date may enter feature engineering, scaler or train/val labels.
"""
from __future__ import annotations
import argparse,hashlib,json,random,sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.nn import functional as F
from scipy.stats import spearmanr
from tensor149_tcn5d.features import FIELDS,load_frozen,daily_compact,labels_next_open,eligible
from tensor149_tcn5d.run import (
  TinyTCN,SEED,LOOKBACK,HORIZON,LAST_MATURE,CONFIG,anchor_indices,
  sample_pairs,normalize,scoring_frame,nav_path,set_seed
)
from tensor149_tcn5d.relational_features import make_r1r2

VARIANTS=("B_DAILY_BASE","C_DAILY_R1","D_DAILY_R1R2",
          "E_XGB_BASE","E_XGB_R1R2","E_CAT_R1R2")
RAW_TO_VARIANT={
 "B_DAILY_BASE":"base","C_DAILY_R1":"r1","D_DAILY_R1R2":"r1r2",
 "E_XGB_BASE":"base","E_XGB_R1R2":"r1r2","E_CAT_R1R2":"r1r2"}
TOPOLOGY=dict(channels=24,dropout=.35,head_hidden=24,weight_decay=.003,
              optimizer="AdamW",loss="original pointwise tail-weighted SmoothL1")

class DynamicTinyTCN(nn.Module):
    """Source original TCN exactly, except first Conv1d n_features."""
    def __init__(self,n_features):
        super().__init__()
        self.c1=nn.Conv1d(n_features,24,3)
        self.c2=nn.Conv1d(24,24,3,dilation=2)
        self.n1=nn.LayerNorm(24)
        self.n2=nn.LayerNorm(24)
        self.head=nn.Sequential(nn.Linear(48,24),nn.GELU(),nn.Dropout(.35),nn.Linear(24,1))
    def forward(self,x):
        z=F.dropout(x.transpose(1,2),p=.35,training=self.training)
        z=F.gelu(self.n1(self.c1(F.pad(z,(2,0))).transpose(1,2))).transpose(1,2)
        z=F.dropout(z,p=.35,training=self.training)
        z=F.gelu(self.n2(self.c2(F.pad(z,(4,0))).transpose(1,2))).transpose(1,2)
        return self.head(torch.cat([z[:,:,-1],z.mean(dim=2)],dim=1)).ravel()

def signal_train_dates(dates,stride):
    if stride==1:
        return np.arange(280,len(dates)-HORIZON-1,1,dtype=np.int32)
    if stride==5:return anchor_indices(dates)
    raise ValueError(stride)

def tensor_windows(z):
    from numpy.lib.stride_tricks import sliding_window_view
    return sliding_window_view(z,window_shape=LOOKBACK,axis=0).transpose(0,1,3,2)

def prepare(x,r1,r2,variant):
    which=RAW_TO_VARIANT[variant]
    if which=="base":return x,tuple(FIELDS)
    if which=="r1":return np.concatenate([x,r1],axis=-1),tuple(FIELDS)+tuple(f"R1_{j}" for j in range(r1.shape[-1]))
    return np.concatenate([x,r1,r2],axis=-1),tuple(FIELDS)+tuple(f"R1_{j}" for j in range(r1.shape[-1]))+tuple(f"R2_{j}" for j in range(r2.shape[-1]))

def training_pairs(anchors,dates,avail,y,year):
    val0=pd.Timestamp(year-1,1,1)
    year0=pd.Timestamp(year,1,1)
    return (sample_pairs(anchors,dates,avail,y,exit_before=val0,
                         signal_after=pd.Timestamp("2008-01-01")),
            sample_pairs(anchor_indices(dates),dates,avail,y,exit_before=year0,
                         signal_after=val0),val0,year0)

def fit_tcn(x,y,dates,avail,year,variant,epochs,out):
    train,val,val0,year0=training_pairs(signal_train_dates(dates,1),dates,avail,y,year)
    if len(train)<4000 or len(val)<200:raise ValueError("Underpowered fold")
    if dates[train[:,0].max()+HORIZON+1]>=val0 or dates[val[:,0].max()+HORIZON+1]>=year0:raise ValueError("Unmatured label")
    z,scaler=normalize(x,dates,val0)
    seq=tensor_windows(z)
    def w(p):return torch.from_numpy(np.ascontiguousarray(
        seq[p[:,0]-(LOOKBACK-1),p[:,1]],dtype=np.float32))
    set_seed()
    model=DynamicTinyTCN(x.shape[-1]);opt=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.003)
    best=float("inf");best_state=None;hist=[];patience=0
    rng=np.random.default_rng(SEED+year)
    for ep in range(epochs):
        model.train()
        perm=rng.permutation(len(train))
        losses=[]
        for chunk in np.array_split(perm,int(np.ceil(len(train)/256))):
            p=train[chunk]
            pred=model(w(p))
            target=torch.from_numpy(y[p[:,0],p[:,1]].astype(np.float32))
            weight=torch.where(target.abs()>=.6,2.,1.)
            loss=(weight*F.smooth_l1_loss(pred,target,reduction="none",beta=.2)).mean()
            if not torch.isfinite(loss):raise ValueError("Nonfinite neural loss")
            opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step()
            losses.append(float(loss.item()))
        model.eval();error=0;observations=0
        with torch.no_grad():
            for chunk in np.array_split(val,int(np.ceil(len(val)/512))):
                pred=model(w(chunk))
                target=torch.from_numpy(y[chunk[:,0],chunk[:,1]])
                error+=float(F.smooth_l1_loss(pred,target,reduction="sum",beta=.2).item())
                observations+=len(chunk)
        vloss=error/observations
        hist.append(dict(epoch=ep+1,train_loss=float(np.mean(losses)),val_loss=vloss))
        if vloss<best-1e-6:
            best=vloss;best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()};patience=0
        else:
            patience+=1
            if patience>=2:break
    if best_state is None:raise ValueError("No best checkpoint")
    model.load_state_dict(best_state);model.eval()
    path=out/f"model_{variant}_{year}.pt"
    torch.save(dict(year=year,variant=variant,state_dict=best_state,scaler=scaler,
                    hist=hist,feature_count=int(x.shape[-1])),path)
    def predict(t,ids):
        p=np.column_stack((np.full(len(ids),t,dtype=np.int32),ids))
        with torch.no_grad():
            outpred=[]
            for block in np.array_split(p,int(np.ceil(len(p)/256))):
                outpred.extend(model(w(block)).numpy().tolist())
        return np.asarray(outpred)
    meta=dict(year=year,model=variant,train_rows=len(train),val_rows=len(val),
        train_dates=int(len(np.unique(train[:,0]))),val_dates=int(len(np.unique(val[:,0]))),
        train_max_exit=str(dates[train[:,0].max()+HORIZON+1].date()),
        validation_max_exit=str(dates[val[:,0].max()+HORIZON+1].date()),
        scaler_fit_before=str(val0.date()),prediction_after=str(year0.date()),
        best_validation_loss=best,train_stride=1,validation_stride=5,
        epoch_history=hist,checkpoint_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return predict,meta

def fit_tree(x,y,dates,avail,year,variant,out):
    train,val,val0,year0=training_pairs(signal_train_dates(dates,1),dates,avail,y,year)
    if dates[train[:,0].max()+HORIZON+1]>=val0 or dates[val[:,0].max()+HORIZON+1]>=year0:
        raise ValueError("Unmatured tree data")
    # Tree feature input is last signal-day snapshot (daily Compact21 observations),
    # not TCN temporal sequences; exact same information *at t* is available.
    Xtr=x[train[:,0],train[:,1]]
    Xva=x[val[:,0],val[:,1]]
    # Features are already stationary ratios/ranks. No global train/test scaler for trees.
    yt=y[train[:,0],train[:,1]]
    yv=y[val[:,0],val[:,1]]
    trgroup=np.unique(train[:,0],return_counts=True)[1]
    vagroup=np.unique(val[:,0],return_counts=True)[1]
    if variant.startswith("E_XGB"):
        from xgboost import XGBRanker
        model=XGBRanker(objective="rank:pairwise",eval_metric="rmse",n_estimators=240,max_depth=4,
            learning_rate=.035,subsample=.85,colsample_bytree=.8,
            min_child_weight=8,reg_lambda=8.,reg_alpha=.1,tree_method="hist",
            n_jobs=2,verbosity=0,random_state=SEED)
        model.fit(Xtr,yt,group=trgroup,eval_set=[(Xva,yv)],eval_group=[vagroup],verbose=False)
        model.save_model(str(out/f"model_{variant}_{year}.json"))
    elif variant=="E_CAT_R1R2":
        from catboost import CatBoostRanker,Pool
        train_pool=Pool(data=Xtr,label=yt,group_id=train[:,0].astype(np.int64))
        val_pool=Pool(data=Xva,label=yv,group_id=val[:,0].astype(np.int64))
        model=CatBoostRanker(loss_function="QueryRMSE",iterations=240,depth=5,
            learning_rate=.035,l2_leaf_reg=8.,thread_count=2,random_seed=SEED,
            verbose=False,allow_writing_files=False)
        model.fit(train_pool,eval_set=val_pool,verbose=False)
        model.save_model(str(out/f"model_{variant}_{year}.cbm"))
    else:raise ValueError(variant)
    def predict(t,ids):
        return np.asarray(model.predict(np.asarray(x[t,ids],dtype=np.float32)),dtype=float).reshape(-1)
    meta=dict(year=year,model=variant,train_rows=len(train),val_rows=len(val),
        train_dates=int(len(trgroup)),validation_dates=int(len(vagroup)),
        train_max_exit=str(dates[train[:,0].max()+HORIZON+1].date()),
        validation_max_exit=str(dates[val[:,0].max()+HORIZON+1].date()),
        train_stride=1,validation_stride=5,
        prediction_after=str(year0.date()),
        params=dict(trees_or_iterations=240,tree_depth=4 if variant.startswith("E_XGB") else 5,
                    label="original cross-sectional realized 5day percentile",
                    loss="XGB rank:pairwise" if variant.startswith("E_XGB") else "CatBoost QueryRMSE"))
    return predict,meta

def run(args):
    if args.variant not in VARIANTS:raise ValueError(args.variant)
    years=list(map(int,args.years.split(",")))
    if sorted(set(years))!=years or years[0]<2017 or years[-1]>2026:raise ValueError(years)
    if args.epochs!=5:raise ValueError("Use prespecified 5 epochs")
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    mats,raw_audit,roster=load_frozen(args.raw)
    dates=mats["Open"].index;names=list(mats["Open"].columns)
    original=daily_compact(mats)
    r1,r1fields,r2,r2fields=make_r1r2(mats,Path(args.raw)/"universe.csv")
    x,fields=prepare(original,r1,r2,args.variant)
    if x.shape[-1] not in (125,139,159):raise ValueError("Unexpected dimensionality")
    ret,y=labels_next_open(mats,HORIZON)
    avail=eligible(original,mats["Open"].to_numpy(float))
    anchors=anchor_indices(dates)
    rows=[];scores=[];folds={}
    for year in years:
        if args.variant.startswith("E_"):
            inference,meta=fit_tree(x,y,dates,avail,year,args.variant,out)
        else:
            inference,meta=fit_tcn(x,y,dates,avail,year,args.variant,args.epochs,out)
        n=0
        for t in anchors:
            if dates[t].year!=year or dates[t]>pd.Timestamp("2026-06-30"):continue
            if dates[t+1+HORIZON]>LAST_MATURE:continue
            ids=np.flatnonzero(avail[t])
            if len(ids)<100:raise ValueError("Too few ETF on weekly signal")
            if not np.isfinite(ret[t,ids]).all():raise ValueError("Missing matured OOS outcome")
            s=inference(int(t),ids)
            if not np.isfinite(s).all():raise ValueError("Nonfinite scores")
            frame=scoring_frame(dates[t],ids,ret[t],y[t],{args.variant:s},names)
            for line in frame:line["t_idx"]=int(t)
            rows.extend(frame)
            for j,k in enumerate(ids):
                scores.append((str(dates[t].date()),int(t),names[k],int(k),
                    float(s[j]),float(y[t,k]),float(ret[t,k])))
            n+=1
        folds[str(year)]={**meta,"oos_weeks":n}
        (out/"FOLDS.json").write_text(json.dumps(folds,indent=2)+"\n")
        print(json.dumps({"year":year,"variant":args.variant,"week_count":n,
              "train_rows":meta["train_rows"],"valid_rows":meta["val_rows"]}),flush=True)
    weekly=pd.DataFrame(rows)
    if weekly.empty:raise ValueError("No weekly predictions")
    weekly.to_csv(out/"OOS_WEEKLY_SELECTIONS.csv",index=False)
    pd.DataFrame(scores,columns=["date","t_idx","ticker","ticker_id","pred_score",
        "realized_fwd_percentile_centered","realized_future_5d_return"]).to_parquet(
        out/"ALL_OOS_SCORES.parquet",index=False)
    curve,eco=nav_path(weekly,dates,mats,args.variant)
    curve.rename(args.variant).to_csv(out/"DAILY_NET_EQUITY.csv",index_label="date")
    metrics=dict(**eco,rank_ic=float(weekly.rank_ic.mean()),
         top5_overlap=float(weekly.top5_overlap.mean()),
         topdecile_regret=float(weekly.topdecile_regret.mean()),
         top5_mean_future_return=float(weekly.top5_mean_future_return.mean()),
         top1_mean_future_return=float(weekly.top1_return.mean()))
    summary=dict(status="R1R2_DAILY_ABLATION_COMPLETE",variant=args.variant,
        original149_roster_sha256=roster,source_frozen=True,production_modified=False,
        training_target="next open to next open+5 cross sectional percentile",
        horizon_days=5,train_stride=1,validation_stride=5,eval_stride=5,
        feature_count=int(x.shape[-1]),r1_feature_names=list(r1fields),r2_feature_names=list(r2fields),
        oos_weekly_dates=int(len(weekly)),original_eligible_mask_reused=True,
        frozen_eval_end="2026-06-30",parameters=TOPOLOGY,environment=dict(
            python=sys.version,torch=torch.__version__,pandas=pd.__version__,numpy=np.__version__),
        raw_audit=raw_audit,folds=folds,metrics=metrics)
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":summary["status"],"variant":args.variant,
           "oos_weeks":len(weekly),"metrics":metrics},indent=2),flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",default="evidence_v1/data/original149")
    ap.add_argument("--variant",choices=VARIANTS,required=True)
    ap.add_argument("--years",default="2024,2025")
    ap.add_argument("--epochs",type=int,default=5)
    ap.add_argument("--out",required=True)
    run(ap.parse_args())
if __name__=="__main__":main()
