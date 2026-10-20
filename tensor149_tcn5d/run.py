"""Leakage-fenced, weekly Original149 TCN experiment. Research only."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import random
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
import torch
from torch import nn
from torch.nn import functional as F

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src")]
from tensor149_tcn5d.features import FIELDS,load_frozen,daily_compact,labels_next_open,eligible

SEED=20261020
LOOKBACK=30
HORIZON=5
LAST_MATURE=pd.Timestamp("2026-07-01")
FEE=0.001
CONFIG=dict(lookback=LOOKBACK,horizon_trading_sessions=HORIZON,epochs=5,batch=256,
            lr=0.001,dropout=.35,channels=24,regularization_weight_decay=.003,
            candidate_universe=149,cost_per_side=FEE,source="frozen Original149 2026-07")

class TinyTCN(nn.Module):
    def __init__(self):
        super().__init__()
        self.c1=nn.Conv1d(125,24,3)
        self.c2=nn.Conv1d(24,24,3,dilation=2)
        self.n1=nn.LayerNorm(24)
        self.n2=nn.LayerNorm(24)
        self.head=nn.Sequential(nn.Linear(48,24),nn.GELU(),nn.Dropout(.35),nn.Linear(24,1))
    def forward(self,x):
        # x [batch, lookback, canonical 125 features]; strictly left-causal convolution.
        x=F.dropout(x.transpose(1,2),p=.35,training=self.training)
        z=F.gelu(self.n1(self.c1(F.pad(x,(2,0))).transpose(1,2))).transpose(1,2)
        z=F.dropout(z,p=.35,training=self.training)
        z=F.gelu(self.n2(self.c2(F.pad(z,(4,0))).transpose(1,2))).transpose(1,2)
        return self.head(torch.cat([z[:,:,-1],z.mean(dim=2)],dim=1)).ravel()

def set_seed():
    random.seed(SEED);np.random.seed(SEED);torch.manual_seed(SEED)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)

def anchor_indices(dates):
    # Fixed global calendar grid: never choose dates using future returns.
    return np.arange(280,len(dates)-HORIZON-1,HORIZON,dtype=np.int32)

def sample_pairs(anchors,dates,avail,y,exit_before,signal_before=None,signal_after=None):
    selected=[]
    for t in anchors:
        if dates[t+1+HORIZON] >= exit_before: continue
        if signal_before is not None and dates[t]>=signal_before:continue
        if signal_after is not None and dates[t]<signal_after:continue
        good=np.where(avail[t] & np.isfinite(y[t]))[0]
        if len(good)>0:
            selected.extend((int(t),int(n)) for n in good)
    return np.asarray(selected,dtype=np.int32).reshape(-1,2)

def normalize(x,dates,train_cut):
    # One scaler fitted on *past-only* raw daily feature cells; never entire time axis.
    pre=x[dates < train_cut].astype(np.float64,copy=False)
    mean=np.nanmean(pre,axis=(0,1))
    std=np.nanstd(pre,axis=(0,1))
    mean=np.where(np.isfinite(mean),mean,0.)
    std=np.where(np.isfinite(std)&(std>1e-6),std,1.)
    z=(x-mean.astype(np.float32))/std.astype(np.float32)
    z=np.nan_to_num(z,nan=0.,posinf=0.,neginf=0.)
    np.clip(z,-6,6,out=z)
    return z,dict(mean_sha=hashlib.sha256(mean.tobytes()).hexdigest(),
                  std_sha=hashlib.sha256(std.tobytes()).hexdigest())

def fit_fold(x,y,dates,avail,anchors,year,epochs=5):
    year0=pd.Timestamp(year=year,month=1,day=1)
    val0=pd.Timestamp(year=year-1,month=1,day=1)
    train=sample_pairs(anchors,dates,avail,y,exit_before=val0,signal_after=pd.Timestamp("2008-01-01"))
    valid=sample_pairs(anchors,dates,avail,y,exit_before=year0,signal_after=val0)
    if len(train)<2000 or len(valid)<200:raise ValueError(f"Underpowered fold {year}: train {len(train)} val {len(valid)}")
    z,scaler=normalize(x,dates,val0)
    from numpy.lib.stride_tricks import sliding_window_view
    # view: [T-29, ETF, features, 30] -> [T-29, ETF, 30, features].
    seq=sliding_window_view(z,window_shape=LOOKBACK,axis=0).transpose(0,1,3,2)
    def windows(p):return np.ascontiguousarray(seq[p[:,0]-(LOOKBACK-1),p[:,1]],dtype=np.float32)
    def last(p):return np.ascontiguousarray(z[p[:,0],p[:,1]])
    baseline=Ridge(alpha=300.)
    baseline.fit(last(train),y[train[:,0],train[:,1]])
    set_seed();net=TinyTCN();opt=torch.optim.AdamW(net.parameters(),lr=CONFIG["lr"],weight_decay=CONFIG["regularization_weight_decay"])
    best=float("inf");best_state=None;history=[];patience=0
    rng=np.random.default_rng(SEED+year)
    for ep in range(epochs):
        net.train()
        perm=rng.permutation(len(train))
        weighted_losses=[]
        for sub in np.array_split(perm,max(1,int(np.ceil(len(train)/CONFIG["batch"])))):
            p=train[sub]; xb=torch.from_numpy(windows(p)); target=torch.from_numpy(y[p[:,0],p[:,1]])
            out=net(xb)
            # Double the tails, retain every ETF for cross-sectional ordering.
            w=torch.where(target.abs()>=.6,2.,1.)
            loss=(w*F.smooth_l1_loss(out,target,reduction="none",beta=.2)).mean()
            opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(net.parameters(),1.)
            opt.step()
            weighted_losses.append(float(loss.item()))
        net.eval();err=0.;seen=0
        with torch.no_grad():
            for part in np.array_split(valid,max(1,int(np.ceil(len(valid)/512)))):
                p=part;out=net(torch.from_numpy(windows(p)))
                target=torch.from_numpy(y[p[:,0],p[:,1]])
                err+=float(F.smooth_l1_loss(out,target,reduction="sum",beta=.2).item());seen+=len(p)
        val=err/seen
        history.append(dict(epoch=ep+1,train_loss=float(np.mean(weighted_losses)),validation_loss=float(val)))
        if val<best-1e-6:
            best=val;best_state={key:t.detach().cpu().clone() for key,t in net.state_dict().items()};patience=0
        else:
            patience+=1
            if patience>=2:break
    if best_state is None: raise ValueError("No validated checkpoint")
    net.load_state_dict(best_state);net.eval()
    audit=dict(year=year,train_rows=len(train),validation_rows=len(valid),
               max_train_exit=str(dates[train[:,0].max()+1+HORIZON].date()),
               max_validation_exit=str(dates[valid[:,0].max()+1+HORIZON].date()),
               train_cutoff=str(val0.date()),validation_cutoff=str(year0.date()),
               training_target="cross_sectional_future_5d_percentile",
               scaler=scaler,epochs_run=len(history),early_stop_validation_loss=best,
               epoch_history=history,no_future_label_gate=True)
    assert dates[train[:,0].max()+1+HORIZON]<val0
    assert dates[valid[:,0].max()+1+HORIZON]<year0
    def predict(t,ids):
        pairs=np.column_stack([np.full(len(ids),t,dtype=np.int32),ids.astype(np.int32)])
        p_r=baseline.predict(last(pairs))
        preds=[]
        with torch.no_grad():
            for q in np.array_split(pairs,max(1,int(np.ceil(len(pairs)/256)))):
                preds.extend(net(torch.from_numpy(windows(q))).numpy().tolist())
        return np.asarray(preds),p_r
    return predict,audit

def scoring_frame(date,ids,ret,y,models,tickers):
    rows=[]
    for name,pred in models.items():
        order=np.argsort(-pred,kind="stable")
        top=ids[order[:5]]
        ranks=y[ids]
        good=np.isfinite(ret[ids])
        if not np.all(good):raise ValueError("Scoring contains missing matured labels")
        ic=spearmanr(pred,ranks).statistic if len(ids)>3 else np.nan
        actual_top=set(ids[np.argsort(-ret[ids],kind="stable")[:5]])
        decile=np.sort(ret[ids])[-max(1,int(np.ceil(.1*len(ids)))):]
        rows.append(dict(date=str(date.date()),model=name,n=len(ids),
            rank_ic=float(ic),top1_realized_rank=float(y[top[0]]),
            top1_return=float(ret[top[0]]),topdecile_regret=float(decile.mean()-ret[top[0]]),
            top5_overlap=len(set(top)&actual_top)/5.,
            top5_mean_future_return=float(np.mean(ret[top])),
            selected=",".join(tickers[q] for q in top)))
    return rows

def nav_path(scores,dates,mats,model):
    O=mats["Open"].to_numpy(dtype=float)
    tickers=list(mats["Open"].columns)
    lookup={t:i for i,t in enumerate(tickers)}
    signals=scores[scores.model==model].sort_values("t_idx")
    wealth=1.;points={}
    for row in signals.itertuples(index=False):
        t=int(row.t_idx)
        picks=[lookup[q] for q in row.selected.split(",")]
        if not np.isfinite(O[t+1:t+HORIZON+2,picks]).all():
            raise ValueError(f"Untradeable selected ETF after signal {row.date}")
        entry=O[t+1,picks]
        # Conservative charge: full 10 bp entry and 10 bp exit on every 5-session hold.
        wealth*=1-2*FEE
        for k in range(t+1,t+HORIZON+2):
            points[dates[k]]=wealth*float(np.mean(O[k,picks]/entry))
        wealth=points[dates[t+HORIZON+1]]
    ser=pd.Series(points,dtype=float).sort_index()
    if len(ser)<30:raise ValueError("Cannot calculate daily portfolio path")
    dr=ser.pct_change().dropna()
    years=(ser.index[-1]-ser.index[0]).days/365.25
    return ser,dict(cagr=float((ser.iloc[-1]/ser.iloc[0])**(1/years)-1),
                    maxdd=float((ser/ser.cummax()-1).min()),
                    sharpe=float(np.sqrt(252)*dr.mean()/dr.std(ddof=0)) if dr.std(ddof=0)>0 else None,
                    final_wealth=float(ser.iloc[-1]),decision_weeks=len(signals),
                    conservative_roundtrip_cost_bps=20)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="evidence_v1/data/original149")
    p.add_argument("--years",default="2024,2025")
    p.add_argument("--epochs",type=int,default=5)
    p.add_argument("--out",default="_tensor149")
    a=p.parse_args()
    if a.epochs<1 or a.epochs>12:raise ValueError("Epoch range 1..12")
    years=list(map(int,a.years.split(",")))
    if sorted(set(years))!=years or min(years)<2017 or max(years)>2026:raise ValueError("Bad test years")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    mats,audit,roster_sha=load_frozen(a.raw)
    dates=mats["Open"].index
    assert len(mats["Open"].columns)==149
    x=daily_compact(mats)
    ret,y=labels_next_open(mats,HORIZON)
    avail=eligible(x,mats["Open"].to_numpy(float))
    anchors=anchor_indices(dates)
    allrows=[];folds={}
    for year in years:
        infer,meta=fit_fold(x,y,dates,avail,anchors,year,epochs=a.epochs)
        weeks=0
        for t in anchors:
            if dates[t].year!=year or dates[t]>pd.Timestamp("2026-06-30"):continue
            if dates[t+1+HORIZON]>LAST_MATURE:continue
            ids=np.where(avail[t])[0]
            if len(ids)<100:raise ValueError(f"ETF eligibility below 100: {dates[t]}, {len(ids)}")
            s_tcn,s_ridge=infer(t,ids)
            s_mom=x[t,ids,FIELDS.index("mom21")]
            preds={"TCN_30x125":s_tcn,"RIDGE_125":s_ridge,"MOM21":s_mom}
            if any(not np.isfinite(z).all() for z in preds.values()):raise ValueError("Nonfinite score")
            if not np.isfinite(ret[t,ids]).all():raise ValueError("Absent mature target for eligible ticker")
            rows=scoring_frame(dates[t],ids,ret[t],y[t],preds,mats["Open"].columns)
            for q in rows:q["t_idx"]=int(t)
            allrows.extend(rows);weeks+=1
        meta["prediction_weeks"]=weeks
        folds[str(year)]=meta
        print(json.dumps({"year":year,"test_weeks":weeks,"train_rows":meta["train_rows"],"val_loss":meta["early_stop_validation_loss"]}),flush=True)
    score=pd.DataFrame(allrows)
    if score.empty:raise ValueError("No matured OOS prediction weeks")
    score.to_csv(out/"OOS_WEEKLY_PREDICTIONS.csv",index=False)
    metrics={};paths=[]
    for name,group in score.groupby("model"):
        path,econ=nav_path(score,dates,mats,name)
        paths.append(path.rename(name))
        metrics[name]=dict(**econ,rank_ic=float(group.rank_ic.mean()),
             top1_mean_realized_pct=float(group.top1_realized_rank.mean()),
             topdecile_regret=float(group.topdecile_regret.mean()),
             top5_overlap=float(group.top5_overlap.mean()),
             top1_absolute_future_return=float(group.top1_return.mean()))
    pd.concat(paths,axis=1).to_csv(out/"OOS_DAILY_EQUITY.csv",index_label="date")
    result=dict(status="TENSOR149_TCN5D_EXPERIMENT_COMPLETE",production_modified=False,
                original_tickers=149,original_roster_sha256=roster_sha,
                raw_manifest=audit,raw_last=str(dates.max().date()),
                first_oos_year=years[0],last_oos_year=years[-1],eval_signal_cutoff="2026-06-30",
                feature_count=len(FIELDS),daily_feature_rows=len(dates),
                tensor_lookback=LOOKBACK,target_horizon=HORIZON,
                train_anchor_stride=HORIZON,prediction_anchor_stride=HORIZON,
                evaluation_weeks=int(score[score.model=="TCN_30x125"].shape[0]),
                total_eligible_ticker_days=int(avail.sum()),
                hyperparam_selection_only_previous_year=True,
                frozen_original_f3_h1_control_not_replayed=True,
                experimental_model_not_independent_holdout=True,
                settings={**CONFIG,"epochs":a.epochs},
                folds=folds,metrics=metrics,environment=dict(python=sys.version,torch=torch.__version__,
                  numpy=np.__version__,pandas=pd.__version__))
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":result["status"],"metrics":metrics},indent=2),flush=True)

if __name__=="__main__":
    main()
