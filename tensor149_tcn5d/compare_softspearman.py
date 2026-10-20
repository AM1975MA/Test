"""Independent same-date frozen 2017-26 SoftSpearman vs registered pointwise and mom21.

No model training or post-hoc objective choices; verifies strictly matched original
dates and manifest roster, computes descriptive circular 5-week paired intervals.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

VARIANTS=("SOFTSPEARMAN","SOFTSPEARMAN_RETURN","SOFTSPEARMAN_TOP5")
CONTROL=("TCN_30x125","MOM21","RIDGE_125")
def findone(root):
    paths=list(Path(root).rglob("RESULT.json"))
    if len(paths)!=1:raise ValueError("Expected exactly one result "+str(root))
    p=paths[0]
    return json.loads(p.read_text()),p.parent

def ci_block(x,block=5,draws=2000,seed=20261020):
    x=np.asarray(x,dtype=float);n=len(x)
    if n<40 or not np.isfinite(x).all():raise ValueError("Paired block input invalid")
    rng=np.random.default_rng(seed)
    means=np.empty(draws)
    for j in range(draws):
        idx=(rng.integers(n,size=int(np.ceil(n/block)))[:,None]+np.arange(block))%n
        means[j]=x[idx.reshape(-1)[:n]].mean()
    return list(map(float,np.quantile(means,[.025,.975])))

def run(args):
    old,oldp=findone(args.baseline)
    if old["status"]!="TENSOR149_TCN5D_EXPERIMENT_COMPLETE":raise ValueError("Baseline not pointwise")
    bf=pd.read_csv(oldp/"OOS_WEEKLY_PREDICTIONS.csv")
    baseline={k:bf[bf.model==k].sort_values("date").reset_index(drop=True) for k in CONTROL}
    anchor=baseline["MOM21"].date.tolist()
    if len(anchor)!=args.expected_weeks or len(set(anchor))!=len(anchor):
        raise ValueError("Bad baseline weekly date support")
    for k,df in baseline.items():
        if df.date.tolist()!=anchor:raise ValueError("Unmatched original baseline "+k)
    refsha=old["original_roster_sha256"]
    metrics={k:old["metrics"][k] for k in CONTROL}
    models=dict(baseline)
    for variant in VARIANTS:
        d,p=findone(Path(args.challenge)/variant)
        if d["status"]!="TENSOR149_SOFTSPEARMAN_COMPLETE" or d["variant"]!=variant:
            raise ValueError("Incorrect challenger status")
        if d["source_sha256"]!=refsha:raise ValueError("Original149 source hash mismatch")
        df=pd.read_csv(p/"OOS_WEEKLY_SELECTIONS.csv")
        if df.model.nunique()!=1 or df.model.iloc[0]!=variant:raise ValueError("Unexpected selection model")
        df=df.sort_values("date").reset_index(drop=True)
        if df.date.tolist()!=anchor:raise ValueError("Challenger changed signal dates")
        if df.duplicated(["date","model"]).any():raise ValueError("Duplicate OOS")
        models[variant]=df
        metrics[variant]=d["performance"]
    paired={}
    for variant in VARIANTS:
        a=models[variant];paired[variant]={}
        for ref in ("TCN_30x125","MOM21"):
            b=models[ref]
            metrics_deltas={}
            for col in ("rank_ic","top5_overlap","top5_mean_future_return"):
                if col not in a or col not in b:raise ValueError("Missing "+col)
                delta=a[col].to_numpy(dtype=float)-b[col].to_numpy(dtype=float)
                metrics_deltas[col]=dict(mean_delta=float(delta.mean()),paired_block95=ci_block(delta))
            paired[variant][ref]=metrics_deltas
    annual=[]
    for name,df in models.items():
        for yr,group in df.groupby(df.date.str[:4]):
            dr=(1.-.002)*(1.+group.top5_mean_future_return.to_numpy(dtype=float))
            wealth=np.cumprod(np.r_[1.,dr])
            annual.append(dict(year=int(yr),model=name,n_weeks=int(len(group)),
                costed_cumulative_weekly=float(wealth[-1]-1),
                weekly_exit_maxdd=float((wealth/np.maximum.accumulate(wealth)-1).min()),
                mean_forward_basket=float(group.top5_mean_future_return.mean()),
                raw_rankic_mean=float(group.rank_ic.mean())))
    year_df=pd.DataFrame(annual).sort_values(["year","model"])
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    payload=dict(status="SOFTSPEARMAN_INDEPENDENT_PAIRED_AUDIT_COMPLETE",
        original149_manifest_sha=refsha,expected_weeks=args.expected_weeks,
        exact_dated_signal_support=True,untuned_prior_pointwise=True,
        reported_metrics=metrics,paired=paired,
        statistical_warning="Block bootstrap confidence intervals descriptive only: extensive previous model mining and retrospective Original149 roster")
    (out/"COMPARISON.json").write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n")
    year_df.to_csv(out/"YEAR_BY_YEAR_COSTED.csv",index=False)
    pd.DataFrame([{"model":k,**v} for k,v in metrics.items()]).to_csv(out/"MODEL_METRICS.csv",index=False)
    print(json.dumps({"status":payload["status"],"weeks":args.expected_weeks,
        "metrics":{k:{q:v.get(q) for q in ("cagr","maxdd","sharpe","rank_ic","top5_overlap")} for k,v in metrics.items()},
        "paired":paired},indent=2),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",required=True)
    p.add_argument("--challenge",required=True)
    p.add_argument("--expected-weeks",type=int,choices=[100,476],required=True)
    p.add_argument("--out",required=True)
    run(p.parse_args())
