#!/usr/bin/env python3
"""Predefined V3 nested meta-tree robustness checks against immutable OOS labels.

Unit of uncertainty: 101 calendar months, NEVER 50,500 overlapping baskets.
No model fitting and no parameter selection.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
CHANGED_COL="top1_changed"
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--scores",required=True)
    p.add_argument("--decisions",required=True)
    p.add_argument("--nested-monthly",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    files=sorted(Path(a.scores).glob("regression/s*/OOS_SCORES.csv"))
    assert len(files)==3
    d=pd.concat((pd.read_csv(file) for file in files),ignore_index=True)
    d=d[d.variant.eq("CORRECTED")].copy()
    assert not d.duplicated(["signal_date","ticker"]).any()
    assert d.signal_date.nunique()==102 and d.ticker.nunique()==149
    source=d.set_index(["signal_date","ticker"])[["fwd_ret_21","pred"]]
    choices=pd.read_csv(a.decisions)
    assert len(choices)==50500 and choices.signal_date.nunique()==101
    assert choices.groupby("signal_date").basket.nunique().eq(500).all()
    assert choices[CHANGED_COL].sum()==2209
    results=pd.read_csv(a.nested_monthly)
    results=results[results.strategy.eq("NESTED_24_TOP1_GUARD")].sort_values("signal_date")
    assert len(results)==101
    for col in ("base_top1","tree_top1","top2","top3"):
        index=pd.MultiIndex.from_frame(choices[["signal_date",col]].rename(columns={col:"ticker"}))
        choices["ret_"+col]=source.fwd_ret_21.reindex(index).to_numpy()
        choices["pred_"+col]=source.pred.reindex(index).to_numpy()
    assert choices.filter(regex="^(pred|ret)_").notna().all().all()
    choices["delta"]=choices.ret_tree_top1-choices.ret_base_top1
    choices["year"]=choices.signal_date.str[:4].astype(int)
    ch=choices[choices[CHANGED_COL].eq(1)].copy()
    monthly=choices.groupby("signal_date").delta.mean().sort_index()
    expected=results.set_index("signal_date")["basket_selected_excess"]
    overall_b0=results["basket_selected_excess"].mean()-monthly.mean()
    assert abs(overall_b0-0.007122)<2e-5
    assert len(monthly)==101
    assert ch.signal_date.nunique()==41
    agg=ch.groupby(["signal_date","base_top1","tree_top1"]).agg(
        delta=("delta","first"),n_repeated_baskets=("basket","size")).reset_index()
    assert len(agg)==786 and agg.n_repeated_baskets.sum()==2209
    # Reconstruct the original runner-up from the fixed original ranker scores,
    # not from the tree-reordered candidate display order.
    candidates=np.column_stack([choices.pred_tree_top1,choices.pred_top2,choices.pred_top3])
    futures=np.column_stack([choices.ret_tree_top1,choices.ret_top2,choices.ret_top3])
    order=np.argsort(-candidates,axis=1,kind="stable")
    ix=order[:,1]
    choices["second_forward"]=futures[np.arange(len(choices)),ix]
    # Fixed actual tree intervention mask, not a newly optimized gate.
    choices["trigger_second_delta"]=np.where(choices[CHANGED_COL].eq(1),
                                            choices.second_forward-choices.ret_base_top1,0.)
    changes2=choices[choices[CHANGED_COL].eq(1)]
    summary=dict(months=101,dependent_basket_decisions=50500,
        monthly_n_baskets=500,decisions_changed=2209,
        months_with_changes=41,unique_ticker_pairs_per_month=786,
        tree_change_winrate=float((ch.delta>0).mean()),
        tree_mean_selected_forward_excess_change=float(monthly.mean()),
        trigger_second_mean_forward_excess_change=float(choices.trigger_second_delta.mean()),
        tree_vs_runnerup_mean_change=float((choices.delta-choices.trigger_second_delta).mean()),
        original_top1_forward_excess_mean=float(overall_b0),
        clipped_plus_minus_5pct_mean=float(np.clip(choices.delta,-.05,.05).mean()),
        clipped_plus_minus_10pct_mean=float(np.clip(choices.delta,-.10,.10).mean()),
        unique_pair_unweighted_mean=float(agg.delta.mean()),
        unique_pair_winrate=float((agg.delta>0).mean()))
    (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2))
    yearly=choices.groupby("year").agg(mean_delta=("delta","mean"),
        changes=(CHANGED_COL,"sum"),n_basket_decisions=("basket","size"),
        trigger_second_mean=("trigger_second_delta","mean"))
    yearly.to_csv(out/"YEARLY.csv")
    split=choices.assign(fixed_basket_quintile=choices.basket%5).groupby("fixed_basket_quintile").agg(
        mean_delta=("delta","mean"),changed=(CHANGED_COL,"sum"),
        total=("basket","size"))
    split.to_csv(out/"FIXED_BASKET_QUINTILES.csv")
    agg.to_csv(out/"UNIQUE_TICKER_PAIR_EVENTS.csv",index=False)
    group_drop=[]
    years=sorted(choices.year.unique())
    for omit in [[],[2026],[2022],[2025],[2022,2025],[2022,2025,2026]]:
        keep=choices[~choices.year.isin(omit)]
        group_drop.append(dict(excluded_years=",".join(map(str,omit)) or "NONE",
            months=keep.signal_date.nunique(),
            mean_delta=float(keep.delta.mean()),
            n_changed=int(keep[CHANGED_COL].sum())))
    pd.DataFrame(group_drop).to_csv(out/"YEAR_EXCLUSION_STRESS.csv",index=False)
    rng=np.random.default_rng(20261024)
    n=len(monthly);rep=3000
    ix=((rng.integers(0,n,size=(rep,(n+5)//6))[:,:,None]
         +np.arange(6))%n).reshape(rep,-1)[:,:n]
    report=[]
    for label,delta in [
        ("unclipped",choices.delta),("clip_20pct",choices.delta.clip(-.2,.2)),
        ("clip_10pct",choices.delta.clip(-.1,.1)),
        ("clip_05pct",choices.delta.clip(-.05,.05)),
        ("clip_03pct",choices.delta.clip(-.03,.03)),
        ("second_trigger",choices.trigger_second_delta),
        ("tree_minus_second",choices.delta-choices.trigger_second_delta)]:
        by_month=pd.Series(delta.to_numpy(),index=choices.signal_date).groupby(level=0).mean()
        assert by_month.index.equals(monthly.index)
        boot=by_month.to_numpy()[ix].mean(axis=1)
        report.append(dict(contrast=label,mean=float(by_month.mean()),
             ci025=float(np.quantile(boot,.025)),ci975=float(np.quantile(boot,.975)),
             bootstrap_calendar_block=6,reps=rep))
    pd.DataFrame(report).to_csv(out/"ROBUSTNESS_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
      metadata_only=False,source_model_run=40016809498,
      nested_selection_run=40032282233,economic_decisions_run=40032693599,
      exact_149_ETFs=True,canonical_500x24_baskets=True,
      identical_101_OOS_months=True,model_parameter_tuning=False,
      economic_CAGR_evaluated=False,future_label_used_only_for_evaluation=True,
      previously_researched_calendar=True,independent_holdout=False,
      original_production_modified=False),indent=2))
    print("ROBUSTNESS_COMPLETED",json.dumps(summary,indent=2),flush=True)
    print("REGIME",pd.DataFrame(group_drop).to_string(index=False),flush=True)
    print("BOOTS",pd.DataFrame(report).to_string(index=False),flush=True)
if __name__=="__main__":main()
