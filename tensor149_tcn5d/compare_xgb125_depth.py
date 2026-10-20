"""Independent paired depth sweep audit: exact original XGB125 depth4 check.

Hard failure if baseline roster, dates, original ETF IDs, depth4 top5 differ.
Paired 5-week circular bootstrap on 476 dated weekly observations.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
DEPTHS=(2,3,4,5,6,7)
def read_result(directory):
    js=list(Path(directory).rglob("RESULT.json"))
    if len(js)!=1:raise ValueError(f"Expected precisely one RESULT.json under {directory}: {js}")
    return json.loads(js[0].read_text()),js[0].parent

def bootstrap(delta,draws=2400,block=5,seed=20261020):
    delta=np.asarray(delta,dtype=float)
    n=len(delta)
    if n!=476 or not np.isfinite(delta).all():raise ValueError("Invalid paired return/IC")
    rng=np.random.default_rng(seed)
    samples=np.empty(draws)
    for j in range(draws):
        ix=(rng.integers(0,n,size=int(np.ceil(n/block)))[:,None]+np.arange(block))%n
        samples[j]=delta[ix.ravel()[:n]].mean()
    return [float(q) for q in np.quantile(samples,[.025,.975])]

def run(args):
    reference,old=read_result(args.baseline)
    if reference.get("status")!="R1R2_DAILY_ABLATION_COMPLETE" or reference.get("variant")!="E_XGB_BASE":
        raise ValueError("Not frozen XGB125 original")
    if reference.get("oos_weekly_dates")!=476:raise ValueError("Reference wrong period")
    sha=reference["original149_roster_sha256"]
    older=pd.read_csv(old/"OOS_WEEKLY_SELECTIONS.csv").sort_values("date").reset_index(drop=True)
    if len(older)!=476 or older.date.nunique()!=476:raise ValueError("Baseline OOS selection length")
    old_scores=pd.read_parquet(old/"ALL_OOS_SCORES.parquet").sort_values(
        ["date","t_idx","ticker_id"]).reset_index(drop=True)
    datasets={4:older}
    results={}
    selection_cols=["date","t_idx","n","selected"]
    full_models={}
    leaf_summary=[]
    for depth in DEPTHS:
        obj,path=read_result(Path(args.candidates)/f"depth{depth}")
        if obj.get("status")!="ORIGINAL149_XGB125_DEPTH_WALKFORWARD_COMPLETE":
            raise ValueError("No valid depth "+str(depth))
        if obj["depth"]!=depth or obj["nominal_max_leaves"]!=2**depth:
            raise ValueError("Wrong depth/leaf label")
        if obj["original_roster_sha256"]!=sha or obj["feature_count"]!=125:
            raise ValueError("Manifest or feature set mismatch")
        if obj["oos_weekly_dates"]!=476:raise ValueError("Wrong OOS count")
        df=pd.read_csv(path/"OOS_WEEKLY_SELECTIONS.csv").sort_values("date").reset_index(drop=True)
        if df.date.tolist()!=older.date.tolist() or df.t_idx.tolist()!=older.t_idx.tolist() or df.n.tolist()!=older.n.tolist():
            raise ValueError("Misaligned dated eligible ETF universe")
        predicted=pd.read_parquet(path/"ALL_OOS_SCORES.parquet").sort_values(
            ["date","t_idx","ticker_id"]).reset_index(drop=True)
        for field in ("date","t_idx","ticker_id","ticker"):
            if not predicted[field].equals(old_scores[field]):
                raise ValueError("Original exact eligible ticker identities differ: "+field)
        for field in ("realized_fwd_percentile_centered","realized_future_5d_return"):
            if not np.allclose(predicted[field],old_scores[field],atol=1e-7,rtol=1e-6):
                raise ValueError("Divergent target/realized 5-session future returns")
        folds=obj.get("folds",{})
        if len(folds)!=10 or any(f["leaves_max"]>2**depth or f["leaves_min"]<1 or f["trees"]!=240 for f in folds.values()):
            raise ValueError("Leaves statistic or per-year model missing")
        for year,f in folds.items():
            leaf_summary.append(dict(depth=depth,year=int(year),
                max_possible_leaves=2**depth,mean_actual_leaves=f["leaves_mean"],
                median_actual_leaves=f["leaves_median"],maximum_actual_leaves=f["leaves_max"],
                fraction_full=f["fraction_full"],train_rows=f["train_rows"],
                val_rows=f["validation_rows"]))
        if depth==4:
            same=(df.selected.to_numpy()==older.selected.to_numpy())
            if not same.all():
                bad=np.flatnonzero(~same)
                raise ValueError(f"Depth4 fails immutable old XGB portfolio re-test: {len(bad)} weeks, first {older.date.iloc[bad[0]]}")
            score_delta=np.max(np.abs(predicted.pred_score.to_numpy(float)-old_scores.pred_score.to_numpy(float)))
            if not np.isfinite(score_delta) or score_delta>1e-4:
                raise ValueError(f"Depth4 scores not numerically reproduced: max diff {score_delta}")
            for name in ("rank_ic","top5_overlap","top5_mean_future_return"):
                diff=np.max(np.abs(df[name].to_numpy()-older[name].to_numpy()))
                if diff>1e-6:raise ValueError(f"Depth4 {name} differs from original {diff}")
            if abs(obj["metrics"]["cagr"]-reference["metrics"]["cagr"])>1e-8:
                raise ValueError("Baseline CAGR changed")
            reproducibility=dict(same_weekly_portfolios=True,identical_weekly_rankic=True,
              score_max_abs_difference=float(score_delta),same_gross_returns=True,
              cagr_difference=float(obj["metrics"]["cagr"]-reference["metrics"]["cagr"]),
              score_rows=int(len(predicted)))
        datasets[depth]=df
        results[depth]=obj
        full_models[depth]=obj["metrics"]
    paired={}
    for d in DEPTHS:
        if d==4:continue
        paired[d]={}
        for k in ("rank_ic","top5_overlap","top5_mean_future_return"):
            dval=datasets[d][k].to_numpy(float)-older[k].to_numpy(float)
            paired[d][k]=dict(mean_delta=float(dval.mean()),ci95_block5=bootstrap(dval))
    annual=[]
    for depth,df in datasets.items():
        if not isinstance(depth,int):continue
        for yr,g in df.groupby(df.date.str[:4]):
            rr=(1-.002)*(1+g.top5_mean_future_return.to_numpy(float))
            annual.append(dict(depth=depth,max_possible_leaves=2**depth,year=int(yr),
                n_weeks=len(g),mean_rankic=float(g.rank_ic.mean()),
                annual_weekly_costed_compound_return=float(np.prod(rr)-1),
                top5_overlap=float(g.top5_overlap.mean())))
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(annual).to_csv(out/"YEARLY_COSTED.csv",index=False)
    pd.DataFrame(leaf_summary).to_csv(out/"REALIZED_LEAF_COUNTS_BY_YEAR.csv",index=False)
    pd.DataFrame([dict(depth=d,leaves_upper_bound=2**d,**m) for d,m in full_models.items()
      ]).sort_values("depth").to_csv(out/"PERFORMANCE.csv",index=False)
    report=dict(status="ORIGINAL149_XGB125_DEPTH_476W_INDEPENDENT_AUDIT_SUCCESS",
        dates=476,manifests_identical=True,same_eligible_tickers=True,
        baseline_run=39479754815,control_depth=4,control_replication=reproducibility,
        model_metrics={str(d):m for d,m in full_models.items()},
        paired_vs_depth4={str(k):v for k,v in paired.items()},
        caution="Original149 retrospectively selected and repeatedly mined; CI not prospective, multiple comparisons not controlled")
    (out/"REPORT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:report[k] for k in ("status","dates","control_replication","model_metrics","paired_vs_depth4")},indent=2),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",required=True)
    p.add_argument("--candidates",required=True)
    p.add_argument("--out",required=True)
    run(p.parse_args())
if __name__=="__main__":main()
