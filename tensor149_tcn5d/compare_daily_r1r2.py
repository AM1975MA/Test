"""Independent Original149 R1/R2 6-way ablation vs immutable A weekly TCN.

Enforces same manifest, same OOS signal dates, and raw Top5 costed-economics
comparison for every model. Evaluates RankIC and Top5 separately, descriptively.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

NEW=("B_DAILY_BASE","C_DAILY_R1","D_DAILY_R1R2",
     "E_XGB_BASE","E_XGB_R1R2","E_CAT_R1R2")
OLD=("TCN_30x125","RIDGE_125","MOM21")
def one(root):
    arr=list(Path(root).rglob("RESULT.json"))
    if len(arr)!=1:raise ValueError(f"Expected one result under {root}: {len(arr)}")
    return json.loads(arr[0].read_text()),arr[0].parent
def block_ci(x,nboot=1600,block=5,seed=20261020):
    x=np.asarray(x,dtype=float)
    if len(x)<50 or not np.isfinite(x).all():raise ValueError("Bad paired difference")
    n=len(x);rng=np.random.default_rng(seed);out=np.empty(nboot)
    for k in range(nboot):
        s=rng.integers(0,n,size=int(np.ceil(n/block)))
        ix=(s[:,None]+np.arange(block))%n
        out[k]=x[ix.reshape(-1)[:n]].mean()
    return [float(v) for v in np.quantile(out,[.025,.975])]
def run(args):
    frozen,root=one(args.baseline)
    if frozen["status"]!="TENSOR149_TCN5D_EXPERIMENT_COMPLETE":raise ValueError("Wrong A baseline")
    source_sha=frozen["original_roster_sha256"]
    old=pd.read_csv(root/"OOS_WEEKLY_PREDICTIONS.csv")
    select={name:old.loc[old.model==name].sort_values("date").reset_index(drop=True) for name in OLD}
    weekly_dates=select["TCN_30x125"].date.tolist()
    if len(weekly_dates)!=args.weeks or len(set(weekly_dates))!=len(weekly_dates):raise ValueError("Unexpected date support")
    for k in OLD:
        if select[k].date.tolist()!=weekly_dates:raise ValueError("Baseline date mismatch")
    metrics={k:frozen["metrics"][k] for k in OLD}
    audits={}
    for variant in NEW:
        r,path=one(Path(args.newroot)/variant)
        if r.get("status")!="R1R2_DAILY_ABLATION_COMPLETE" or r.get("variant")!=variant:
            raise ValueError("Not a completed ablation")
        if r["original149_roster_sha256"]!=source_sha:raise ValueError("Manifest SHA mismatch")
        if r["oos_weekly_dates"]!=args.weeks:raise ValueError("Wrong weeks")
        df=pd.read_csv(path/"OOS_WEEKLY_SELECTIONS.csv").sort_values("date").reset_index(drop=True)
        if len(df)!=args.weeks or df.model.nunique()!=1 or df.date.tolist()!=weekly_dates:
            raise ValueError("New dated OOS mismatch "+variant)
        select[variant]=df
        metrics[variant]=r["metrics"]
        audits[variant]={"folds":r["folds"],"features":r["feature_count"]}
    comparison={}
    for variant in NEW:
        a=select[variant];comparison[variant]={}
        for ref in ("TCN_30x125","MOM21","B_DAILY_BASE","C_DAILY_R1","D_DAILY_R1R2","E_XGB_BASE"):
            if variant==ref:continue
            b=select[ref]
            report={}
            for key in ("rank_ic","top5_overlap","top5_mean_future_return"):
                if key not in a or key not in b:raise ValueError("Missing pair "+key)
                delta=a[key].to_numpy(dtype=float)-b[key].to_numpy(dtype=float)
                report[key]={"mean_delta":float(delta.mean()),"block95":block_ci(delta)}
            comparison[variant][ref]=report
    annual=[]
    for name,df in select.items():
        for yr,g in df.groupby(df.date.str[:4]):
            h=(1-.002)*(1+g.top5_mean_future_return.to_numpy(dtype=float))
            wealth=np.cumprod(np.r_[1.,h])
            annual.append({"model":name,"year":int(yr),"n_weeks":len(g),
                           "weekly_costed_cum_return":float(wealth[-1]-1),
                           "weekly_exit_drawdown":float((wealth/np.maximum.accumulate(wealth)-1).min()),
                           "mean_rank_ic":float(g.rank_ic.mean()),
                           "mean_top5_forward_nominal_return":float(g.top5_mean_future_return.mean()),
                           "fraction_profitable_after_cost":float((h>1).mean())})
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    report=dict(status="ORIGINAL149_DAILY_R1R2_INDEPENDENT_AUDIT_SUCCESS",
       matched_dates=True,dates=args.weeks,sha=source_sha,
       frozen_baseline=OLD,models=metrics,matched_paired=comparison,fold_audits=audits,
       warning="Retrospective data-mined 2017-26 interval, multiple models; block CI descriptive not prospective")
    (out/"REPORT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    pd.DataFrame([{"model":name,**v} for name,v in metrics.items()]).to_csv(out/"PERFORMANCE.csv",index=False)
    pd.DataFrame(annual).to_csv(out/"ANNUAL_BY_MODEL.csv",index=False)
    print(json.dumps({"status":report["status"],"weeks":args.weeks,
      "models":{k:{v:metrics[k].get(v) for v in ("cagr","maxdd","sharpe","rank_ic","top5_overlap")} for k in metrics},
      "comparisons_vs_A_and_momentum":{k:{ref:val for ref,val in comparison[k].items()
                    if ref in ("TCN_30x125","MOM21")} for k in NEW}},indent=2),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",required=True)
    p.add_argument("--newroot",required=True)
    p.add_argument("--weeks",type=int,choices=(100,476),required=True)
    p.add_argument("--out",required=True)
    run(p.parse_args())
