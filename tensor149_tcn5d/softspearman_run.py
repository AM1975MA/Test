"""Fully source-frozen, date-grouped genuine torchsort SoftSpearman TCN challenge.
Does not modify source_only producer, original pointwise baseline, or portfolio policy.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import torch
import torchsort
from tensor149_tcn5d.features import FIELDS,load_frozen,daily_compact,labels_next_open,eligible
from tensor149_tcn5d.softspearman_losses import VARIANTS,softspearman_loss
from tensor149_tcn5d.run import (
    SEED,LOOKBACK,HORIZON,LAST_MATURE,FEE,TinyTCN,set_seed,
    anchor_indices,sample_pairs,normalize,scoring_frame,nav_path
)

def group_by_date(pairs):
    """One date per query, no mixing ETF rows from different signal dates."""
    if pairs.ndim!=2 or pairs.shape[1]!=2:raise ValueError("Invalid samples")
    dates,idx,counts=np.unique(pairs[:,0],return_index=True,return_counts=True)
    if not np.all(np.diff(dates)>=1):raise ValueError("Nonascending dates")
    return [(int(t),pairs[i:i+n,1].astype(np.int32)) for t,i,n in zip(dates,idx,counts) if n>=10]

def assemble_group(seq,t,ids):
    a=seq[t-(LOOKBACK-1),ids]
    return torch.from_numpy(np.ascontiguousarray(a,dtype=np.float32))

def train_fold(z,ret,y,dates,avail,anchors,year,variant,out,epochs):
    year0=pd.Timestamp(year,1,1)
    val0=pd.Timestamp(year-1,1,1)
    train=sample_pairs(anchors,dates,avail,y,exit_before=val0,signal_after=pd.Timestamp("2008-01-01"))
    valid=sample_pairs(anchors,dates,avail,y,exit_before=year0,signal_after=val0)
    tr_groups=group_by_date(train);va_groups=group_by_date(valid)
    if len(train)<2000 or len(valid)<200 or len(tr_groups)<80 or len(va_groups)<25:
        raise ValueError(f"Insufficient complete temporal groups Y={year} train={len(train)} valid={len(valid)}")
    if dates[train[:,0].max()+HORIZON+1]>=val0 or dates[valid[:,0].max()+HORIZON+1]>=year0:
        raise ValueError("Non-mature train or validation labels")
    # Per-fold scaler strictly fit on feature cells dated before training/validation boundary.
    z,scaler_audit=normalize(z,dates,val0)
    from numpy.lib.stride_tricks import sliding_window_view
    seq=sliding_window_view(z,window_shape=LOOKBACK,axis=0).transpose(0,1,3,2)
    set_seed()
    net=TinyTCN()
    opt=torch.optim.AdamW(net.parameters(),lr=.001,weight_decay=.003)
    rng=np.random.default_rng(SEED+year)
    history=[];best_loss=float("inf");best_state=None;patience=0
    # Fixed 4-date query batch: preserve query identity for each group loss.
    for ep in range(epochs):
        net.train()
        order=rng.permutation(len(tr_groups))
        losses=[]
        for chunk in np.array_split(order,max(1,int(np.ceil(len(order)/4)))):
            opt.zero_grad()
            batch_losses=[]
            for index in chunk:
                t,ids=tr_groups[index]
                targets=torch.from_numpy(y[t,ids].astype(np.float32))
                realized=torch.from_numpy(ret[t,ids].astype(np.float32))
                if not (torch.isfinite(targets).all() and torch.isfinite(realized).all()):
                    raise ValueError("Nonfinite matured group label")
                p=net(assemble_group(seq,t,ids))
                batch_losses.append(softspearman_loss(p,targets,realized,variant))
            loss=torch.stack(batch_losses).mean()
            if not torch.isfinite(loss):raise ValueError(f"Nonfinite train loss Y={year}")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(),1.)
            opt.step()
            losses.append(float(loss.item()))
        net.eval();v_losses=[]
        with torch.no_grad():
            for t,ids in va_groups:
                p=net(assemble_group(seq,t,ids))
                label=torch.from_numpy(y[t,ids].astype(np.float32))
                realized=torch.from_numpy(ret[t,ids].astype(np.float32))
                val=softspearman_loss(p,label,realized,variant)
                if not torch.isfinite(val):raise ValueError("Nonfinite validation loss")
                v_losses.append(float(val.item()))
        mean=float(np.mean(v_losses))
        history.append(dict(epoch=ep+1,training_loss=float(np.mean(losses)),validation_loss=mean))
        if mean < best_loss-1e-6:
            best_loss=mean
            best_state={k:v.detach().cpu().clone() for k,v in net.state_dict().items()}
            patience=0
        else:
            patience+=1
            if patience>=2:break
    if best_state is None:raise ValueError("No validated checkpoint")
    net.load_state_dict(best_state);net.eval()
    checkpoint=out/f"model_{variant}_{year}.pt"
    torch.save({ "year":year,"variant":variant,"state_dict":best_state,"epoch_history":history,
                 "scaler":scaler_audit },checkpoint)
    def predict(t,ids):
        with torch.no_grad():
            result=net(assemble_group(seq,t,ids)).numpy()
        if not np.isfinite(result).all():raise ValueError("Nonfinite infer scores")
        return result
    evidence=dict(year=year,train_ticker_rows=int(len(train)),train_groups=len(tr_groups),
                  valid_ticker_rows=int(len(valid)),valid_groups=len(va_groups),
                  max_train_label_exit=str(dates[train[:,0].max()+HORIZON+1].date()),
                  max_validation_label_exit=str(dates[valid[:,0].max()+HORIZON+1].date()),
                  annual_train_cutoff=str(val0.date()),test_cutoff=str(year0.date()),
                  best_validation_softspearman_group_loss=best_loss,epoch_history=history,
                  checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                  per_date_groups=True,leakage_gate_pass=True,scaler=scaler_audit)
    return predict,evidence

def run(args):
    if args.variant not in VARIANTS:raise ValueError("Unknown objective")
    years=[int(q) for q in args.years.split(",")]
    if sorted(set(years))!=years or min(years)<2017 or max(years)>2026:raise ValueError("Bad test years")
    if args.epochs<1 or args.epochs>12:raise ValueError("Invalid epoch budget")
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    mats,raw_audit,roster_hash=load_frozen(args.raw)
    dates=mats["Open"].index
    x=daily_compact(mats)
    ret,y=labels_next_open(mats,HORIZON)
    avail=eligible(x,mats["Open"].to_numpy(dtype=float))
    anchors=anchor_indices(dates)
    ticker_names=list(mats["Open"].columns)
    rows=[];scores_all=[];evidence={}
    for year in years:
        infer,fold=train_fold(x,ret,y,dates,avail,anchors,year,args.variant,out,args.epochs)
        n_dates=0
        for t in anchors:
            if dates[t].year!=year or dates[t]>pd.Timestamp("2026-06-30"):continue
            if dates[t+HORIZON+1]>LAST_MATURE:continue
            ids=np.flatnonzero(avail[t])
            if len(ids)<100:raise ValueError("Fewer than 100 tradeable names "+str(dates[t]))
            if not np.isfinite(ret[t,ids]).all():raise ValueError("Future return missing in evaluation")
            p=infer(int(t),ids)
            result=scoring_frame(dates[t],ids,ret[t],y[t],{args.variant:p},ticker_names)
            for o in result:o["t_idx"]=int(t)
            rows.extend(result)
            for j,i in enumerate(ids):
                scores_all.append((str(dates[t].date()),int(t),ticker_names[int(i)],int(i),
                                   float(p[j]),float(y[t,i]),float(ret[t,i])))
            n_dates+=1
        fold["evaluation_dates"]=n_dates
        evidence[str(year)]=fold
        print(json.dumps({"variant":args.variant,"year":year,"train_rows":fold["train_ticker_rows"],
                          "validation_loss":fold["best_validation_softspearman_group_loss"],"test_weeks":n_dates}),flush=True)
        (out/"PER_FOLD.json").write_text(json.dumps(evidence,indent=2)+"\n")
    score=pd.DataFrame(rows)
    if score.empty:raise ValueError("No OOS weekly decisions")
    score.to_csv(out/"OOS_WEEKLY_SELECTIONS.csv",index=False)
    long=pd.DataFrame(scores_all,columns=["date","t_idx","ticker","ticker_id","pred_score",
             "realized_fwd_percentile_centered","realized_future_5d_return"])
    if long.duplicated(["date","ticker"]).any():raise ValueError("Duplicate OOS row")
    long.to_parquet(out/"ALL_OOS_SCORES.parquet",index=False)
    nav,econ=nav_path(score,dates,mats,args.variant)
    nav.rename("NAV").to_csv(out/"DAILY_NET_EQUITY.csv",index_label="date")
    n_dates=int(len(score))
    metrics=dict(**econ,rank_ic=float(score.rank_ic.mean()),
        top1_mean_realized_percentile=float(score.top1_realized_rank_pct.mean()),
        topdecile_regret=float(score.topdecile_regret.mean()),
        top5_overlap=float(score.top5_overlap.mean()),
        top1_mean_future_return=float(score.top1_return.mean()),
        top5_mean_future_return=float(score.top5_mean_future_return.mean()))
    summary=dict(status="TENSOR149_SOFTSPEARMAN_COMPLETE",variant=args.variant,
        method="torchsort.soft_rank l2 strength=1.0; Spearman corr via Pearson ranks; group score standardization",
        target_top5_weight=5.0,hybrid_return_smooth_l1_weight=0.30,
        torchsort_version=getattr(torchsort,"__version__","0.1.10"),
        source="frozen Original149 existing CSV and manifest",source_sha256=roster_hash,
        production_modified=False,number_etfs=149,number_features=len(FIELDS),
        lookback=LOOKBACK,horizon=HORIZON,training_stride=HORIZON,eval_stride=HORIZON,
        training_group_identity="same signal date all eligible tickers",epochs_max=args.epochs,
        numerical_environment=dict(torch=torch.__version__,pandas=pd.__version__,numpy=np.__version__,
                                   python=sys.version),folds=evidence,
        total_prediction_dates=n_dates,total_oos_etf_scores=int(len(long)),
        performance=metrics,
        economic_assumption="Top5, next adjusted open to open+5, full 10bp each side, equal-weight",
        known_limits=["research-mined historical market","ETF survival/selection bias",
            "Yahoo adjusted prices not executable","not independently prospective","long-only beta not neutralized"],
        raw_audit=raw_audit,
        output_sha256={q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in out.iterdir() if q.is_file()})
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":summary["status"],"variant":args.variant,
                      "n_dates":n_dates,"performance":metrics},indent=2),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--variant",required=True,choices=VARIANTS)
    p.add_argument("--raw",default="evidence_v1/data/original149")
    p.add_argument("--years",default="2024,2025")
    p.add_argument("--epochs",type=int,default=5)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    run(args)

if __name__=="__main__":
    main()
