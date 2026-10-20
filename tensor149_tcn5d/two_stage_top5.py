"""Fixed causal 2-stage ETF Top5 vs single-depth XGB125 benchmark experiment.

No fit. Use only original annual expanding-walkforward frozen OOS predictions.
Data manifest/date/labels validated before combining any two models.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from tensor149_tcn5d.features import load_frozen
from tensor149_tcn5d.run import scoring_frame,nav_path,HORIZON
from tensor149_tcn5d.compare_xgb125_depth import read_result,bootstrap

DEPTHS=(2,3,4,5,6,7)
TWO_STAGE={
 "STAGE3_20_4":(3,20,4),
 "STAGE3_20_7":(3,20,7),
 "STAGE3_30_7":(3,30,7),
 "STAGE2_20_7":(2,20,7)
}
BLENDS={"BLEND3_4":(3,4),"BLEND3_7":(3,7)}
SINGLES=tuple(f"XGB_D{d}" for d in DEPTHS)
METHODS=SINGLES+tuple(TWO_STAGE)+tuple(BLENDS)
SIGNAL_END=pd.Timestamp("2026-06-30")

def rank_percentile(a):
    arr=np.asarray(a,dtype=float)
    if arr.ndim!=1 or len(arr)<100 or not np.isfinite(arr).all():
        raise ValueError("Incorrect ranking input")
    return pd.Series(arr).rank(pct=True,method="average").to_numpy(dtype=float)

def staged_scores(primary,secondary,shortlist_size):
    """Entire-universe score: outside shortlist in primary order, inside in secondary order.
    A strict gap ensures the Top5 is always chosen only within shortlist.
    """
    p=rank_percentile(primary)
    q=rank_percentile(secondary)
    if shortlist_size<5 or shortlist_size>=len(p):raise ValueError("Bad cutoff")
    # Stable and reproducible, sorted ETF identifiers on source records.
    allowed=np.argsort(-np.asarray(primary),kind="stable")[:shortlist_size]
    mask=np.zeros(len(p),dtype=bool)
    mask[allowed]=True
    ans=np.where(mask,1.+q,-1.+p)
    if not np.array_equal(np.sort(np.argsort(-ans,kind="stable")[:5]),np.sort(allowed[np.argsort(-secondary[allowed],kind="stable")[:5]])):
        raise ValueError("Stage shortlist rerank inconsistent")
    return ans

def candidate_scores(scores):
    ans={f"XGB_D{d}":np.asarray(scores[d],dtype=float) for d in DEPTHS}
    for name,(p,k,s) in TWO_STAGE.items():
        ans[name]=staged_scores(ans[f"XGB_D{p}"],ans[f"XGB_D{s}"],k)
    for name,(a,b) in BLENDS.items():
        ans[name]=0.5*rank_percentile(ans[f"XGB_D{a}"])+0.5*rank_percentile(ans[f"XGB_D{b}"])
    return ans

def assert_archive_identity(folder):
    reports,dirs,frame={}, {}, {}
    manifest=None;ground=None
    identity=["date","t_idx","ticker_id","ticker"]
    outcomes=["realized_fwd_percentile_centered","realized_future_5d_return"]
    for depth in DEPTHS:
        doc,where=read_result(Path(folder)/f"depth{depth}")
        if doc.get("status")!="ORIGINAL149_XGB125_DEPTH_WALKFORWARD_COMPLETE" or doc.get("depth")!=depth:
            raise ValueError("Not a verified original OOS depth")
        if doc.get("oos_weekly_dates")!=476 or doc.get("feature_count")!=125:
            raise ValueError("Not original 476-week 125-feature OOS")
        roster=doc.get("original_roster_sha256")
        if manifest is None:manifest=roster
        if roster!=manifest:raise ValueError("Contradictory roster SHA")
        z=pd.read_parquet(where/"ALL_OOS_SCORES.parquet").sort_values(
            ["date","t_idx","ticker_id"]).reset_index(drop=True)
        if len(z)!=70924 or z.date.nunique()!=476:
            raise ValueError("Unexpected eligible ETF score observations")
        if ground is None:ground=z
        else:
            for field in identity:
                if not z[field].equals(ground[field]):
                    raise ValueError(f"Different eligible ETF identity: {field}")
            for field in outcomes:
                if not np.allclose(z[field],ground[field],rtol=1e-6,atol=1e-7):
                    raise ValueError(f"Mismatch in realized return/target {field}")
        frame[depth]=z
        dirs[depth]=where
        reports[depth]=doc
    return ground,frame,reports,manifest

def paired_stats(score_table,reference):
    result={}
    anchor=score_table[score_table.model==reference].sort_values("date").reset_index(drop=True)
    for name in METHODS:
        if name==reference:continue
        other=score_table[score_table.model==name].sort_values("date").reset_index(drop=True)
        if other.date.tolist()!=anchor.date.tolist():raise ValueError("Paired dates not equal")
        result[name]={key:dict(mean_delta=float((other[key]-anchor[key]).mean()),
                ci95_block5=bootstrap((other[key]-anchor[key]).to_numpy(dtype=float)))
            for key in ("rank_ic","top5_overlap","top5_mean_future_return")}
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",default="evidence_v1/data/original149")
    ap.add_argument("--scores",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    root=Path(args.out);root.mkdir(parents=True,exist_ok=True)
    ground,panels,models,sha=assert_archive_identity(args.scores)
    mats,meta,sha2=load_frozen(args.raw)
    if sha!=sha2:raise ValueError("Original frozen roster changed")
    dates=mats["Open"].index
    names=list(mats["Open"].columns)
    if len(names)!=149:raise ValueError("Original149 roster changed")
    if not all(ground.ticker_id.between(0,148)):raise ValueError("Ticker index out of range")
    selected=[];details=[];weeks=0
    for date,idx in ground.groupby("date",sort=True).groups.items():
        rows=ground.loc[idx].sort_values("ticker_id")
        ti=int(rows.t_idx.iloc[0])
        if pd.Timestamp(date)!=dates[ti] or dates[ti]>SIGNAL_END:
            raise ValueError("Unexpected evaluation date")
        ids=rows.ticker_id.to_numpy(dtype=int)
        if [names[k] for k in ids]!=rows.ticker.tolist():
            raise ValueError("Ticker-id mapping different from frozen OHLCV")
        expected_by_depth={}
        for depth in DEPTHS:
            # Only signal-time pred_score changes by depth; labels are verified same.
            s=panels[depth].loc[idx].sort_values("ticker_id")
            expected_by_depth[depth]=s.pred_score.to_numpy(dtype=float)
        outcomes=rows.realized_future_5d_return.to_numpy(dtype=float)
        y=rows.realized_fwd_percentile_centered.to_numpy(dtype=float)
        returns=np.full(len(names),np.nan,dtype=float)
        label=np.full(len(names),np.nan,dtype=float)
        returns[ids]=outcomes
        label[ids]=y
        pred=candidate_scores(expected_by_depth)
        # Prefix-only as-of methods with a fixed candidate mask from frozen OOS scores.
        sub=scoring_frame(dates[ti],ids,returns,label,pred,names)
        for line in sub:
            line["t_idx"]=ti
            line["is_hybrid"]=line["model"] not in SINGLES
        selected.extend(sub)
        details.append(dict(date=date,t_idx=ti,candidate_n=len(ids),
             primary_rank_top20_d3=",".join(names[ids[j]] for j in np.argsort(-expected_by_depth[3],kind="stable")[:20]),
             primary_rank_top30_d3=",".join(names[ids[j]] for j in np.argsort(-expected_by_depth[3],kind="stable")[:30])))
        weeks+=1
    if weeks!=476:raise ValueError(f"Wrong OOS dates {weeks}")
    df=pd.DataFrame(selected).sort_values(["date","model"]).reset_index(drop=True)
    df.to_csv(root/"OOS_WEEKLY_SELECTIONS.csv",index=False)
    pd.DataFrame(details).to_csv(root/"SHORTLISTS_AS_OF.csv",index=False)
    # Audit every replay against the same frozen depth results, prior to any hybrid inference.
    for depth in DEPTHS:
        name=f"XGB_D{depth}"
        actual=df[df.model==name].sort_values("date").reset_index(drop=True)
        frozen=pd.read_csv(panels_dir(args.scores,depth)/"OOS_WEEKLY_SELECTIONS.csv").sort_values("date").reset_index(drop=True)
        if actual.date.tolist()!=frozen.date.tolist() or actual.selected.tolist()!=frozen.selected.tolist():
            raise ValueError(f"Single-depth Top5 not reproduced for {depth}")
        for k in ("rank_ic","top5_overlap","top5_mean_future_return"):
            if not np.allclose(actual[k],frozen[k],atol=1e-10,rtol=1e-10):
                raise ValueError(f"Single-depth OOS metrics not replicated {depth}: {k}")
    stats=[];curves=[]
    for method in METHODS:
        curve,eco=nav_path(df,dates,mats,method)
        curves.append(curve.rename(method))
        group=df[df.model==method]
        stats.append(dict(model=method,**eco,
             rank_ic=float(group.rank_ic.mean()),
             top5_overlap=float(group.top5_overlap.mean()),
             top5_mean_future_return=float(group.top5_mean_future_return.mean()),
             topdecile_regret=float(group.topdecile_regret.mean()),
             top1_mean_future_return=float(group.top1_return.mean()),
             worst_weekly_basket_return=float(group.top5_mean_future_return.min())))
    pd.concat(curves,axis=1).to_csv(root/"DAILY_NET_EQUITY.csv",index_label="date")
    pd.DataFrame(stats).to_csv(root/"PERFORMANCE.csv",index=False)
    yearly=[]
    for method in METHODS:
        sub=df[df.model==method]
        for year,g in sub.groupby(sub.date.str.slice(0,4)):
            w=(1-.002)*(1+g.top5_mean_future_return.to_numpy(dtype=float))
            yearly.append(dict(model=method,year=int(year),n_weeks=len(g),
                 weekly_compounded_net_return=float(np.prod(w)-1),
                 mean_rank_ic=float(g.rank_ic.mean()),
                 mean_top5_future_return=float(g.top5_mean_future_return.mean()),
                 top5_overlap=float(g.top5_overlap.mean())))
    pd.DataFrame(yearly).to_csv(root/"ANNUAL_BY_MODEL.csv",index=False)
    paired={baseline:paired_stats(df,baseline) for baseline in ("XGB_D3","XGB_D4","XGB_D7")}
    payload=dict(status="ORIGINAL149_TWOSTAGE_TOP5_476W_AUDITED_COMPLETE",
       date_count=476,score_rows=70924,
       unchanged_original_roster_sha256=sha,
       frozen_out_of_sample_experts_no_refit=True,
       signal_cutoff="close t, next open entry and open+5 exit",
       original_costs_20bps_roundtrip=True,
       exact_individual_model_top5_and_weekly_metric_replication=True,
       methods=list(METHODS),stage_rules=TWO_STAGE,blend_rules=BLENDS,
       results=stats,paired_bootstrap=paired,
       warning="Same heavily mined 2017-2026 retrospective Original149: descriptive bootstrap cannot establish prospective outperformance.")
    (root/"REPORT.json").write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n")
    print(json.dumps(dict(status=payload["status"],date_count=weeks,
         baseline_comparisons={m:paired["XGB_D4"][m] for m in TWO_STAGE.keys()},
         metrics=stats),indent=2),flush=True)

def panels_dir(scores,depth):
    _,p=read_result(Path(scores)/f"depth{depth}")
    return p

if __name__=="__main__":main()
