#!/usr/bin/env python3
"""V3 L00 CS: same-day 125-feature minmax [-1,+1] ranking evaluation only, no portfolio/CAGR.

Source controls and challengers share month/ETF/labels; basket overlap is
handled by aggregating to month before paired block resampling.
"""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
p=argparse.ArgumentParser()
p.add_argument("--root",default="runs/v3_l00_cs_shards")
p.add_argument("--out",default="runs/v3_l00_cs_complete")
a=p.parse_args()
root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
paths=sorted(root.glob("**/PAIRED_MONTHLY.csv"))
assert len(paths)==3,paths
d=pd.concat([pd.read_csv(f) for f in paths],ignore_index=True)
d["signal_date"]=pd.to_datetime(d.signal_date,format="mixed")
arms=["CORRECTED","L00_CS_MINMAX125"]
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
# Exactly ONE feature-normalization candidate, no multi-arm Holm search.
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
# Feature audits for every signal date/feature from all three independently
# reproduced raw 149 panels, require consistent as-of transforms.
pfa=sorted(root.glob("**/FEATURE_NORMALIZATION_AUDIT.csv"))
assert len(pfa)==3
feature_audit=pd.read_csv(pfa[0])
assert feature_audit.feature.nunique()==125
for file in pfa[1:]:
    other_audit=pd.read_csv(file)
    pd.testing.assert_frame_equal(feature_audit,other_audit)
feature_audit.to_csv(out/"FEATURE_NORMALIZATION_AUDIT.csv",index=False)
fit=[]
for f in sorted(root.glob("**/FIT_AUDIT.json")):
    fit.extend(json.loads(f.read_text()))
assert len(fit)==9
(out/"FIT_AUDIT.json").write_text(json.dumps(fit,indent=2))
(out/"MANIFEST.json").write_text(json.dumps({
    "layer":"L00 CS_MINMAX 125 corrected daily cross-section",
    "preregistered":"all 125 input feature columns per as-of signal date min/max to -1/+1, otherwise SAME 127-leaf pairwise model 360 rounds 3 seeds",
    "baseline_source_run":39515716383,"raw_source_run":39482809691,
    "frozen_feature_count":125,"n_months":101,"n_tickers":149,"n_baskets":500,
    "primary_metrics":["basket_top3","basket_ndcg3","basket_regret"],
    "other_metrics":["universe_ic","basket_top1","basket_mrr_selected"],
    "model":"same 3 seeds, same 360 rounds, same 127 leaves, chronological expanding annual fit",
    "normalization":"same day observable ETF cross-sectional minmax, keep NaNs, zero for constant",
    "training_labels_frequency":"monthly 21-trading-day future labels, daily-compatible transforms",
    "no_cross_date_scaling_or_fits":True,
    "no_tail_macro_blend_allocation_risk":True,
    "return_metrics_evaluated":False,"cagr_evaluated":False,
    "historical_data_explored_not_virgin_holdout":True},indent=2))
(out/"SUMMARY.md").write_text(
    "# V3 L00 CS: cross-sectional day-local minmax feature normalization\n\n"+
    "Frozen corrected-125 raw feature definitions and same 149 original ETF records. "+
    "This report deliberately contains no CAGR or backtested portfolio P&L. "+
    "The 101 months are exploratory historical, NOT a previously untouched holdout.\n\n"+
    summary.round(6).to_markdown()+"\n\n"+
    bs[bs.metric.isin(["basket_top3","basket_ndcg3","basket_regret","universe_ic"])]
      .round(6).to_markdown(index=False)+"\n")
print("V3_L00_CS_MINMAX_METRICS\n",summary.to_string(),flush=True)
