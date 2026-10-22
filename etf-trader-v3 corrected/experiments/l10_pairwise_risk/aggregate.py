#!/usr/bin/env python3
"""V3 L01: intrinsic predictive ranking evaluation only, no portfolio/CAGR.

Source controls and challengers share month/ETF/labels; basket overlap is
handled by aggregating to month before paired block resampling.
"""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
p=argparse.ArgumentParser()
p.add_argument("--root",default="runs/v3_l01_shards")
p.add_argument("--out",default="runs/v3_l01_complete")
a=p.parse_args()
root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
paths=sorted(root.glob("**/PAIRED_MONTHLY.csv"))
assert len(paths)==3,paths
d=pd.concat([pd.read_csv(f) for f in paths],ignore_index=True)
d["signal_date"]=pd.to_datetime(d.signal_date,format="mixed")
arms=["CORRECTED","L10_TOP5_PAIR127","L10_TOP5_RISKTIER127"]
assert set(d.variant)==set(arms)
assert not d.duplicated(["signal_date","variant"]).any()
base=d[d.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
assert len(base)==101
for name in arms[1:]:
    x=d[d.variant==name].sort_values("signal_date").reset_index(drop=True)
    for field in ["signal_date","n_tickers","n_baskets"]:
        pd.testing.assert_series_equal(base[field],x[field])
metrics=["universe_ic","universe_top1","universe_top3","basket_top1","basket_top3",
         "basket_ndcg3","basket_mrr_selected","basket_selected_true_rank",
         "basket_regret","basket_selected_excess"]
summary=d.groupby("variant")[metrics].mean()
summary.insert(0,"months",d.groupby("variant").size())
summary.to_csv(out/"RESULTS.csv")
d.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
d.groupby(["year","variant"],as_index=False)[metrics].mean().to_csv(out/"YEARLY.csv",index=False)
bootstrap=[]
for name in arms[1:]:
    other=d[d.variant==name].sort_values("signal_date").reset_index(drop=True)
    for metric in metrics:
        diff=(other[metric]-base[metric]).to_numpy(float)
        assert np.isfinite(diff).all(),(name,metric)
        rng=np.random.default_rng(20261021)
        N=len(diff);block=6;reps=6000
        starts=rng.integers(0,N,size=(reps,int(np.ceil(N/block))))
        ix=((starts[:,:,None]+np.arange(block))%N).reshape(reps,-1)[:,:N]
        samples=diff[ix].mean(axis=1)
        # Centered bootstrap null approximation: exploratory only.
        diffbar=float(diff.mean())
        centered=samples-diffbar
        p2=min(1.,2.*min(float(np.mean(centered>=diffbar)),
                          float(np.mean(centered<=diffbar))))
        bootstrap.append({"variant":name,"metric":metric,"n_months":N,
           "delta":diffbar,"ci95_low":float(np.quantile(samples,.025)),
           "ci95_high":float(np.quantile(samples,.975)),
           "exploratory_two_sided_p":p2,
           "unit":"paired calendar-month 6-month circular blocks, 6000 reps"})
bs=pd.DataFrame(bootstrap)
# Two newly tested objective/capacity arms => Holm multiplicity correction
for metric in ["basket_top3","basket_ndcg3","universe_ic","basket_regret"]:
    ix=bs.metric.eq(metric); tmp=bs.loc[ix].sort_values("exploratory_two_sided_p")
    if len(tmp)!=2:raise RuntimeError("Expected two hypotheses per metric")
    adjusted={}
    prev=0.
    for i,(idx,row) in enumerate(tmp.iterrows()):
        adj=min(1.,max(prev,row.exploratory_two_sided_p*(len(tmp)-i)))
        adjusted[idx]=adj;prev=adj
    for idx,adjusted_p in adjusted.items():bs.loc[idx,"holm_p"]=adjusted_p
bs.to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
scorepaths=sorted(root.glob("**/OOS_SCORES.csv"))
assert len(scorepaths)==3
sc=pd.concat([pd.read_csv(f) for f in scorepaths],ignore_index=True)
sc["signal_date"]=pd.to_datetime(sc.signal_date,format="mixed")
assert not sc.duplicated(["variant","signal_date","ticker"]).any()
b=sc[sc.variant=="CORRECTED"][["signal_date","ticker"]].sort_values(
    ["signal_date","ticker"]).reset_index(drop=True)
for name in arms[1:]:
    q=sc[sc.variant==name][["signal_date","ticker"]].sort_values(
        ["signal_date","ticker"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(q,b)
sc.to_csv(out/"OOS_SCORES.csv",index=False)
fit=[]
for f in sorted(root.glob("**/FIT_AUDIT.json")):
    fit.extend(json.loads(f.read_text()))
assert len(fit)==18
(out/"FIT_AUDIT.json").write_text(json.dumps(fit,indent=2))
(out/"MANIFEST.json").write_text(json.dumps({
    "layer":"L10 pairwise top5 and risk-tier label ablation",
    "preregistered":"stage A original ordinal rank label topk5 pairwise vs default and stage B same topk5 with severe absolute loss below -10% assigned lowest ordered label, original ranker unchanged",
    "baseline_source_run":39515716383,"raw_source_run":39482809691,
    "frozen_feature_count":125,"n_months":101,"n_tickers":149,"n_baskets":500,
    "primary_metrics":["basket_top3","basket_ndcg3","basket_regret"],
    "other_metrics":["universe_ic","basket_top1","basket_mrr_selected"],
    "model":"3 seeds, 360 rounds, chronological expanding annual fit",
    "no_tail_macro_blend_allocation_risk":True,
    "return_metrics_evaluated":False,"cagr_evaluated":False,
    "historical_data_explored_not_virgin_holdout":True},indent=2))
(out/"SUMMARY.md").write_text(
    "# V3 L01: intrinsic ranking capability\n\n"+
    "Frozen corrected-125 inputs and same 149 original ETF records. "+
    "This report deliberately contains no CAGR or backtested portfolio P&L. "+
    "The 101 months are exploratory historical, NOT a previously untouched holdout.\n\n"+
    summary.round(6).to_markdown()+"\n\n"+
    bs[bs.metric.isin(["basket_top3","basket_ndcg3","basket_regret","universe_ic"])]
      .round(6).to_markdown(index=False)+"\n")
print("V3_L01_METRICS\n",summary.to_string(),flush=True)
