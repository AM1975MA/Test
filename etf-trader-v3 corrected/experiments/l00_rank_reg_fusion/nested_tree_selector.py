#!/usr/bin/env python3
"""Nested chronological meta-tree configuration choice, no refitting the frozen heads.

All 36 tree configurations have independently out-of-time predictions.
For test month t, a configuration may be selected only from observations dated
strictly earlier than t-60 calendar days (conservative 21D outcome maturity).
Exploratory study: meta-selection RULE FAMILY is not a pristine unseen holdout.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

M=("basket_top1","basket_top3","basket_ndcg3","basket_regret",
   "basket_selected_excess","basket_loss10_top1")
STRATEGIES={
    "NESTED_24_EXCESS":(24,"excess"),
    "NESTED_24_TOP1_GUARD":(24,"top1_guard"),
    "NESTED_36_TOP1_GUARD":(36,"top1_guard"),
    "NESTED_24_CONSERVATIVE":(24,"conservative"),
    "NESTED_36_CONSERVATIVE":(36,"conservative"),
}
BASE="CORRECTED"

def run(monthly_file,corrections_file,out_dir):
    d=pd.read_csv(monthly_file,parse_dates=["signal_date"])
    c=pd.read_csv(corrections_file,parse_dates=["signal_date"])
    dates=np.sort(d.signal_date.unique().astype("datetime64[ns]"))
    arms=[BASE]+sorted(set(d.variant)-{BASE})
    assert len(dates)==101 and len(arms)==37, (len(dates),len(arms))
    arr=np.full((len(dates),len(arms),len(M)),np.nan)
    fixes=np.zeros((len(dates),len(arms),4),dtype=float)
    for j,arm in enumerate(arms):
        z=d[d.variant==arm].sort_values("signal_date")
        assert np.array_equal(z.signal_date.values,dates)
        assert z.n_baskets.eq(500).all()
        arr[:,j,:]=z[list(M)].to_numpy(dtype=float)
        if j:
            s=c[c.variant==arm].sort_values("signal_date")
            assert np.array_equal(s.signal_date.values,dates)
            fixes[:,j,:]=s[["changed","changes_better","changes_worse","n_baskets"]].to_numpy(dtype=float)
    assert np.isfinite(arr).all()
    assert np.allclose(arr[:,:,1],arr[:,0:1,1],rtol=0,atol=1e-12), "Meta tree must preserve Top3"
    delta=arr-arr[:,0:1,:]
    selected={}; months=[]; decisions=[]
    for strategy,(trailing,objective) in STRATEGIES.items():
        choices=[]
        for i,date in enumerate(dates):
            history=np.flatnonzero(dates<date-np.timedelta64(60,"D"))[-trailing:]
            choice=0;value=0.
            # Lookbacks are from meta-OOF scores of each separately fitted tree,
            # never from raw first-stage in-sample fitted scores.
            if len(history)>=24:
                x=delta[history,1:,:]
                mu=x.mean(axis=0)
                excess=mu[:,4];top1=mu[:,0]
                if objective=="excess":
                    score=excess
                elif objective=="top1_guard":
                    score=np.where((excess>0)&(top1>=0),excess,-1e10)
                elif objective=="conservative":
                    se=x[:,:,4].std(axis=0,ddof=1)/np.sqrt(len(history))
                    score=excess-1.64*se
                if score.max()>0:
                    choice=int(np.argmax(score))+1
                    value=float(score[choice-1])
            choices.append(choice)
            decisions.append(dict(strategy=strategy,signal_date=str(pd.Timestamp(date).date()),
                chosen=arms[choice],history_months=len(history),
                maximum_mature_signal_date=str(pd.Timestamp(date-np.timedelta64(60,"D")).date()),
                historical_selection_objective=value))
        choices=np.asarray(choices,dtype=int)
        path=arr[np.arange(len(dates)),choices,:]
        edits=fixes[np.arange(len(dates)),choices,:]
        selected[strategy]=(path,choices,edits)
        for i,date in enumerate(dates):
            rec=dict(strategy=strategy,signal_date=str(pd.Timestamp(date).date()),
                     year=int(pd.Timestamp(date).year),chosen=arms[choices[i]],
                     changed=int(edits[i,0]),changes_better=int(edits[i,1]),
                     changes_worse=int(edits[i,2]))
            rec.update(dict(zip(M,path[i])))
            months.append(rec)
    # Bootstrap whole calendar blocks, not overlapping 500 baskets.
    rng=np.random.default_rng(20261024);n=len(dates)
    boot=np.empty((3000,n),dtype=int)
    for i in range(len(boot)):
        starts=rng.integers(0,n,size=(n+5)//6)
        boot[i]=np.concatenate([(s+np.arange(6))%n for s in starts])[:n]
    summary=[];intervals=[]
    periods={"full":np.ones(n,dtype=bool),
             "pre2026":dates<np.datetime64("2026-01-01"),
             "post2020":dates>=np.datetime64("2021-01-01")}
    for strategy,(path,choices,edits) in selected.items():
        for period,mask in periods.items():
            current=path[mask].mean(axis=0)
            baseline=arr[mask,0,:].mean(axis=0)
            changes=edits[mask].sum(axis=0)
            r=dict(strategy=strategy,period=period,months=int(mask.sum()),
                meta_months=int(np.count_nonzero(choices[mask])),
                changes=int(changes[0]),corrections_better=int(changes[1]),
                corrections_worse=int(changes[2]),
                changes_better_rate=float(changes[1]/max(1,changes[1]+changes[2])))
            for j,metric in enumerate(M):
                r[metric]=float(current[j])
                r["delta_"+metric]=float(current[j]-baseline[j])
            summary.append(r)
        for j,metric in enumerate(M):
            diff=path[:,j]-arr[:,0,j]
            rep=diff[boot].mean(axis=1)
            intervals.append(dict(strategy=strategy,metric=metric,mean=float(diff.mean()),
                lo=float(np.quantile(rep,.025)),hi=float(np.quantile(rep,.975)),
                n_boot=3000,bootstrap_block_months=6))
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(summary).to_csv(out/"NESTED_SUMMARY.csv",index=False)
    pd.DataFrame(months).to_csv(out/"NESTED_MONTHLY.csv",index=False)
    pd.DataFrame(decisions).to_csv(out/"NESTED_SELECTION_AUDIT.csv",index=False)
    pd.DataFrame(intervals).to_csv(out/"NESTED_BOOTSTRAP.csv",index=False)
    (out/"NESTED_MANIFEST.json").write_text(json.dumps(dict(
        methodology="chronological asof matured meta hyperparameter selection",
        source_run=40031144599,months=101,etfs=149,baskets=500,
        candidate_tree_variants=36,lag_calendar_days=60,
        window_months_min=24,strategies=STRATEGIES,
        statistical_unit="calendar month, six month circular paired bootstrap",
        previously_researched_history=True,pristine_holdout=False,
        production_modified=False),indent=2))
    print("NESTED_SUCCESS",flush=True)
    print(pd.DataFrame(summary).query('period=="full"').to_string(index=False),flush=True)
    print("CONFIDENCE_INTERVAL_EXCESS",flush=True)
    print(pd.DataFrame(intervals).query('metric=="basket_selected_excess"').to_string(index=False),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--monthly",required=True)
    p.add_argument("--corrections",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    run(args.monthly,args.corrections,args.out)
