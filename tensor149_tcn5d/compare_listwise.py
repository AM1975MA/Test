"""Independent, date-paired retrospective comparison of frozen Pointwise vs 3 Listwise TCNs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

def get_results(root):
    files=list(Path(root).rglob("RESULT.json"))
    return [(p,json.loads(p.read_text())) for p in files]

def draw_block_means(vals,block=5,draws=2000,seed=20261020):
    """Circular 5-week moving-block bootstrap, paired on OOS decision dates, descriptive only."""
    vals=np.asarray(vals,dtype=float)
    if not np.isfinite(vals).all():raise ValueError("Missing paired value")
    n=len(vals); rng=np.random.default_rng(seed)
    length=int(np.ceil(n/block))
    means=np.empty(draws)
    for i in range(draws):
        starts=rng.integers(0,n,size=length)
        indices=(starts[:,None]+np.arange(block)[None,:])%n
        means[i]=vals[indices.ravel()[:n]].mean()
    return [float(x) for x in np.quantile(means,[.025,.975])]

def summarize(old,newroot,scope,out):
    oldlist=get_results(old)
    if len(oldlist)!=1:raise ValueError(f"Expected one frozen baseline, got {len(oldlist)}")
    oldp,old_result=oldlist[0]
    olddate=pd.read_csv(oldp.parent/"OOS_WEEKLY_PREDICTIONS.csv")
    if olddate.duplicated(["date","model"]).any():raise ValueError("Duplicate baseline dates")
    newlist=get_results(newroot)
    required={"LISTNET_ALL","LISTMLE_TOP5","LISTNET_RETURN_HYBRID"}
    by_variant={d["variant"]:(p,d) for p,d in newlist if d.get("status")=="TENSOR149_CAUSAL_LISTWISE_COMPLETE"}
    if set(by_variant)!=required:raise ValueError(f"Missing challenger: {set(by_variant)^required}")
    if scope=="pilot":target_dates=100
    else:target_dates=476
    b=olddate[olddate.model=="TCN_30x125"].sort_values("date")
    if len(b)!=target_dates:raise ValueError(f"Frozen Pointwise OOS count {len(b)} != expected {target_dates}")
    if len(set(b.date))!=len(b):raise ValueError("Duplicate baseline signal date")
    contrasts={};scorecards={}
    for variant,(p,d) in by_variant.items():
        s=pd.read_csv(p.parent/"OOS_WEEKLY_SELECTIONS.csv").sort_values("date")
        if len(s)!=target_dates or s.duplicated("date").any():raise ValueError("Wrong challenger OOS coverage")
        if s.date.tolist()!=b.date.tolist():raise ValueError("Signal dates do not match Pointwise benchmark")
        for col in ("rank_ic","top1_realized_rank_pct","topdecile_regret","top5_overlap"):
            if col not in b or col not in s:raise ValueError("Metrics column absent: "+col)
        diffs={m:np.asarray(s[m])-np.asarray(b[m]) for m in
               ("rank_ic","top1_realized_rank_pct","topdecile_regret","top5_overlap")}
        contrasts[variant]={m:{"mean_delta":float(np.mean(z)),"paired_block95_ci":draw_block_means(z)} for m,z in diffs.items()}
        scorecards[variant]=d["performance"]
    for name,d in old_result["metrics"].items():scorecards[name]=d
    comparison={"status":"MATCHED_TCN_LISTWISE_PAIRED_COMPARISON_COMPLETE",
        "scope":scope,"dates":target_dates,"baseline":"TCN_30x125",
        "same_date_support":True,"n_models":len(scorecards),
        "prediction_metrics_by_model":scorecards,"paired_vs_pointwise":contrasts,
        "statistical_warning":"Reused mined dates, highly correlated markets, paired circular 5-week block CI is descriptive, not independent evidence"}
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    (dest/"COMPARISON.json").write_text(json.dumps(comparison,indent=2,allow_nan=False)+"\n")
    pd.DataFrame([{"model":name,**r} for name,r in scorecards.items()]).to_csv(dest/"COMPARISON.csv",index=False)
    print(json.dumps({"status":comparison["status"],"dates":target_dates,
      "models":{name:{"cagr":r["cagr"],"maxdd":r["maxdd"],"rank_ic":r["rank_ic"],"top5_overlap":r["top5_overlap"]}
       for name,r in scorecards.items()},
      "paired_vs_pointwise":contrasts},indent=2),flush=True)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--old",required=True);p.add_argument("--newroot",required=True)
    p.add_argument("--out",required=True);p.add_argument("--scope",choices=["pilot","full"],required=True)
    a=p.parse_args()
    summarize(a.old,a.newroot,a.scope,a.out)
if __name__=="__main__":main()
