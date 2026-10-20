"""Independent exact-date and same-universe 476-week RMT direct feature ablation audit."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
NEW=("B_RMT_GLOBAL","C_RMT_ETF","D_RMT_BOTH","E_SIMPLE_CORREL")
def resolve(root):
    js=list(Path(root).rglob("RESULT.json"))
    if len(js)!=1:raise ValueError(f"Expected one RESULT.json in {root} got {js}")
    return json.loads(js[0].read_text()),js[0].parent
def interval(delta,seed=20261020,draws=2000,block=5):
    d=np.asarray(delta,dtype=float);n=len(d)
    if n!=476 or not np.isfinite(d).all():raise ValueError("Noncomparable weekly contrast")
    rng=np.random.default_rng(seed)
    results=np.empty(draws)
    for j in range(draws):
        starts=rng.integers(n,size=int(np.ceil(n/block)))
        ix=(starts[:,None]+np.arange(block))%n
        results[j]=d[ix.ravel()[:n]].mean()
    return [float(v) for v in np.quantile(results,[.025,.975])]
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",required=True)
    p.add_argument("--newroot",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    base,broot=resolve(a.baseline)
    if base["status"]!="R1R2_DAILY_ABLATION_COMPLETE" or base["variant"]!="E_XGB_BASE":
        raise ValueError("Wrong immutable 125-feature XGB baseline")
    if base["oos_weekly_dates"]!=476:raise ValueError("Wrong baseline weeks")
    sha=base["original149_roster_sha256"]
    b=pd.read_csv(broot/"OOS_WEEKLY_SELECTIONS.csv").sort_values("date").reset_index(drop=True)
    if len(b)!=476 or b.date.nunique()!=476:raise ValueError("Baseline not 476 weeks")
    comparison={"A_XGB125":b}
    metrics={"A_XGB125":base["metrics"]}
    cache_sha=None
    for name in NEW:
        result,root=resolve(Path(a.newroot)/name)
        if result["status"]!="ORIGINAL149_RMT_XGB_FEATURE_ABLATION_COMPLETE":
            raise ValueError(name+" wrong status")
        if result["variant"]!=name or result["roster_sha"]!=sha or result["oos_weeks"]!=476:
            raise ValueError(name+" roster, identity or date count inconsistent")
        if result["feature_count"]!=(135 if name=="D_RMT_BOTH" else 130):
            raise ValueError(name+" feature count")
        f=pd.read_csv(root/"OOS_WEEKLY_SELECTIONS.csv").sort_values("date").reset_index(drop=True)
        if f.date.tolist()!=b.date.tolist() or f.t_idx.tolist()!=b.t_idx.tolist():
            raise ValueError(name+" date/t_idx mismatch")
        if f.n.tolist()!=b.n.tolist():raise ValueError("Eligible ETF count mismatch")
        scr=pd.read_parquet(root/"ALL_OOS_SCORES.parquet")
        if scr.date.nunique()!=476 or not np.isfinite(scr.realized_future_5d_return).all():
            raise ValueError("Missing per-ETF scoring")
        comparison[name]=f
        metrics[name]=result["metrics"]
    paired={}
    for candidate in NEW:
        paired[candidate]={}
        x=comparison[candidate]
        for baseline in comparison:
            if baseline==candidate:continue
            y=comparison[baseline]
            assert x.date.tolist()==y.date.tolist()
            paired[candidate][baseline]={}
            for key in ("rank_ic","top5_overlap","top5_mean_future_return"):
                d=x[key].to_numpy(dtype=float)-y[key].to_numpy(dtype=float)
                paired[candidate][baseline][key]=dict(delta=float(np.mean(d)),bootstrap_block5_95=interval(d))
    rows=[]
    for name,df in comparison.items():
        for year,z in df.groupby(df.date.str.slice(0,4)):
            q=(1-.002)*(1+z.top5_mean_future_return.to_numpy(float))
            rows.append(dict(model=name,year=int(year),n_weeks=len(z),
                costed_return=float(np.prod(q)-1),mean_rank_ic=float(z.rank_ic.mean()),
                mean_top5_overlap=float(z.top5_overlap.mean()),
                mean_top5_return=float(z.top5_mean_future_return.mean())))
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame([dict(model=k,**v) for k,v in metrics.items()]).to_csv(out/"PERFORMANCE.csv",index=False)
    pd.DataFrame(rows).to_csv(out/"ANNUAL_COMPARISON.csv",index=False)
    doc=dict(status="ORIGINAL149_RMT_DIRECT_FULL_INDEPENDENT_AUDIT_SUCCESS",
        original_roster_sha=sha,all_same_dates=True,
        all_same_eligible_counts=True,all_experiment_weeks=476,
        models=metrics,paired_differences=paired,
        original_baseline_run=39479754815,
        caution="Repeated Original149 OOS mined heavily; bootstrap descriptive not independent validation")
    (out/"AUDIT.json").write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n")
    print(json.dumps(dict(status=doc["status"],models={k:{q:v.get(q) for q in ("rank_ic","cagr","maxdd","sharpe","top5_overlap")} for k,v in metrics.items()},
        vs_125={k:paired[k]["A_XGB125"] for k in NEW}),indent=2),flush=True)
if __name__=="__main__":main()
