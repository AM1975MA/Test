"""Independent dated compare of risk-target TCN vs same-date native and frozen controls.

Inputs are immutable GitHub Actions artifacts for each registered 2017–26 run.
5-week circular block CIs are *descriptive*, not post-hoc proof of alpha.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

CHALLENGERS=("RAW_EXCESS_DIST","VOL_EXCESS_DIST","BETA_VOL_RESID_DIST")
CONTROLS=("MOM21","MOM21_RISK","BETA_MOM21_RISK","VOL63","INV_VOL63")
HEADLINES=("TCN_30x125","RIDGE_125","MOM21")
KEY_METRICS=("cagr","maxdd","sharpe","rank_ic","top5_overlap","top5_risk_oracle_overlap",
  "avg_selected_benchmark_excess","avg_selected_beta_residual",
  "avg_selected_annualized_vol63","avg_selected_beta63")

def block_ci(delta,nsim=1500,block=5,seed=20261020):
    data=np.asarray(delta,dtype=float)
    if len(data)<40 or not np.isfinite(data).all():raise ValueError("Invalid paired support")
    n=len(data);rng=np.random.default_rng(seed);length=int(np.ceil(n/block))
    means=np.zeros(nsim)
    for i in range(nsim):
        starts=rng.integers(n,size=length)
        ix=(starts[:,None]+np.arange(block))%n
        means[i]=data[ix.reshape(-1)[:n]].mean()
    return [float(k) for k in np.quantile(means,[.025,.975])]

def results_one(root):
    rr=list(Path(root).rglob("RESULT.json"))
    if len(rr)!=1:raise ValueError(f"Expected a single result under {root}; found {len(rr)}")
    data=json.loads(rr[0].read_text())
    return data,rr[0].parent

def run(args):
    old,older=results_one(args.baseline)
    if old["status"]!="TENSOR149_TCN5D_EXPERIMENT_COMPLETE":raise ValueError("Incorrect frozen baseline")
    o=pd.read_csv(older/"OOS_WEEKLY_PREDICTIONS.csv").sort_values(["date","model"])
    reports={};series={};scores={};roster_shas=set()
    for variant in CHALLENGERS:
        record,path=results_one(Path(args.challenge)/variant)
        if record["variant"]!=variant or record["status"]!="TENSOR149_RISK_RELATIVE_DISTRIBUTION_COMPLETE":
            raise ValueError("Wrong variant artifact")
        roster_shas.add(record["source_sha256"])
        report=record["performance"]
        if not set((variant,*CONTROLS)).issubset(set(report)):raise ValueError("Missing control")
        sel=pd.read_csv(path/"OOS_WEEKLY_SELECTIONS.csv")
        if sel.duplicated(["date","model"]).any():raise ValueError("Repeated signal")
        reports[variant]=record
        scores[variant]=sel
        for name in (variant,*CONTROLS):
            rows=sel[sel.model==name].sort_values("date")
            if len(rows)!=args.expected_weeks:raise ValueError(f"Bad date count {variant}/{name}")
            if rows.date.duplicated().any():raise ValueError("Duplicate dates")
            series[name if name==variant else f"{variant}:{name}"]=rows.reset_index(drop=True)
    if len(roster_shas)!=1 or old["original_roster_sha256"] not in roster_shas:
        raise ValueError("Frozen roster mismatch")
    original= o[o.model=="TCN_30x125"].sort_values("date").reset_index(drop=True)
    if len(original)!=args.expected_weeks:raise ValueError("Frozen old support differs")
    frozen={name:o[o.model==name].sort_values("date").reset_index(drop=True) for name in HEADLINES}
    for name,df in {**series,**frozen}.items():
        if df.date.tolist()!=original.date.tolist():raise ValueError("Signal dates differ "+name)
    # All risk-only controls MUST be identical in each target job.
    for control in CONTROLS:
        a=series["RAW_EXCESS_DIST:"+control]
        for variant in CHALLENGERS[1:]:
            b=series[variant+":"+control]
            if not (a.selected.tolist()==b.selected.tolist() and
                    np.allclose(a.top5_mean_future_return,b.top5_mean_future_return)):
                raise ValueError("Control results dependent on chosen future label: "+control)
    metrics={name:old["metrics"][name] for name in HEADLINES}
    for name in CHALLENGERS:metrics[name]=reports[name]["performance"][name]
    for name in CONTROLS:metrics[name]=reports[CHALLENGERS[0]]["performance"][name]
    refs=("MOM21","TCN_30x125","MOM21_RISK","BETA_MOM21_RISK","VOL63","INV_VOL63")
    paired={}
    for challenger in CHALLENGERS:
        a=series[challenger]
        paired[challenger]={}
        for ref in refs:
            b=frozen[ref] if ref in ("MOM21","TCN_30x125") else series["RAW_EXCESS_DIST:"+ref]
            delta=(a.top5_mean_future_return-b.top5_mean_future_return).to_numpy()
            raw_overlap=(a.top5_overlap-b.top5_overlap).to_numpy()
            paired[challenger][ref]={
                "mean_weekly_top5_return_delta":float(delta.mean()),
                "weekly_top5_return_delta_block95":block_ci(delta),
                "mean_true_top5_overlap_delta":float(raw_overlap.mean()),
                "top5_overlap_delta_block95":block_ci(raw_overlap)}
    # Compound the same costed 5-session single-hold P&L into calendar-year
    # tables without resetting out-of-sample refits or picking training years.
    annual=[]
    for name,df in {**{k:series[k] for k in CHALLENGERS},
                    **{k:series["RAW_EXCESS_DIST:"+k] for k in CONTROLS},
                    **frozen}.items():
        for year,g in df.groupby(df.date.str[:4]):
            weekly=(1-.002)*(1+g.top5_mean_future_return.to_numpy(dtype=float))
            curve=np.cumprod(np.r_[1.,weekly])
            ann_dd=float((curve/np.maximum.accumulate(curve)-1).min())
            annual.append(dict(model=name,year=int(year),n_weeks=len(g),
                cumulative_costed_5d=float(curve[-1]-1),
                maxdd_at_weekly_exits=float(ann_dd),
                mean_raw_future_5d=float(g.top5_mean_future_return.mean()),
                fraction_profitable_costed_week=float((weekly>1).mean())))
    annual_df=pd.DataFrame(annual).sort_values(["year","model"])
    out=dict(status="RISKRELATIVE_COMPARISON_COMPLETED",
             test_dates=int(args.expected_weeks),all_weekly_dates_and_roster_exact=True,
             controls_identical_across_target_variants=True,
             original_roster_sha=old["original_roster_sha256"],
             metrics=metrics,paired=paired,
             caveat="All targets have been mined on Original149 historically; circular-block 95% intervals exploratory; do not infer live alpha")
    out_dir=Path(args.out);out_dir.mkdir(parents=True,exist_ok=True)
    (out_dir/"COMPARISON.json").write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    pd.DataFrame([{"model":k,**{m:r.get(m) for m in KEY_METRICS}} for k,r in metrics.items()]).to_csv(out_dir/"METRICS.csv",index=False)
    annual_df.to_csv(out_dir/"ANNUAL_WEEKLY_REPLAY.csv",index=False)
    pd.DataFrame([{"variant":q,"control":ref,**v} for q,compar in paired.items()
                  for ref,v in compar.items()]).to_json(out_dir/"PAIRED.json",orient="records",indent=2)
    print(json.dumps({"status":out["status"],"dates":out["test_dates"],
      "models":{k:{"cagr":v["cagr"],"maxdd":v["maxdd"],"sharpe":v["sharpe"],
        "rank_ic":v["rank_ic"],"top5_overlap":v["top5_overlap"],
        "avg_selected_beta_residual":v.get("avg_selected_beta_residual"),
        "avg_selected_annualized_vol63":v.get("avg_selected_annualized_vol63")} for k,v in metrics.items()},
      "paired":paired},indent=2),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",required=True)
    p.add_argument("--challenge",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--expected-weeks",type=int,choices=[100,476],required=True)
    run(p.parse_args())
