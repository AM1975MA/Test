#!/usr/bin/env python3
"""V3 L02 Tail intrinsic event-capture metrics only; no CAGR."""
from pathlib import Path
import argparse,json
import numpy as np,pandas as pd
p=argparse.ArgumentParser()
p.add_argument("--root",default="runs/v3_l02_shards")
p.add_argument("--out",default="runs/v3_l02_complete")
args=p.parse_args()
root=Path(args.root);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
files=sorted(root.glob("**/PAIRED_MONTHLY.csv"))
if len(files)!=3:raise RuntimeError(f"Expected 3 annual folds: {files}")
df=pd.concat([pd.read_csv(f) for f in files],ignore_index=True)
df.signal_date=pd.to_datetime(df.signal_date,format="mixed")
arms=["TAIL_FULL60","TAIL_DEDUP45"]
assert set(df.variant)==set(arms)
assert not df.duplicated(["variant","signal_date"]).any()
a=df[df.variant==arms[0]].sort_values("signal_date").reset_index(drop=True)
b=df[df.variant==arms[1]].sort_values("signal_date").reset_index(drop=True)
for name in ["signal_date","n_tickers","n_baskets","tail_event_rate"]:
    pd.testing.assert_series_equal(a[name],b[name])
assert len(a)>=90 and set(a.year)==set(range(2018,2027))
metrics=["tail_event_ap","tail_event_auc","tail_elite_recall_top15",
         "tail_elite_precision_top15","tail_rank_ic","basket_tail_top1",
         "basket_tail_top3","basket_tail_regret","basket_bottom_decile_false_selection"]
s=df.groupby("variant")[metrics].mean()
s.insert(0,"months",df.groupby("variant").size())
s.to_csv(out/"RESULTS.csv")
df.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
df.groupby(["year","variant"],as_index=False)[metrics].mean().to_csv(out/"YEARLY.csv",index=False)
rows=[]
for col in metrics:
    dif=(b[col]-a[col]).to_numpy(float)
    assert np.isfinite(dif).all()
    n=len(dif);rng=np.random.default_rng(20261021)
    nrep=6000;block=6
    starts=rng.integers(0,n,size=(nrep,int(np.ceil(n/block))))
    pos=((starts[:,:,None]+np.arange(block))%n).reshape(nrep,-1)[:,:n]
    sims=dif[pos].mean(axis=1)
    rows.append({"arm":"TAIL_DEDUP45","reference":"TAIL_FULL60",
        "metric":col,"delta":float(dif.mean()),
        "ci95_low":float(np.quantile(sims,.025)),
        "ci95_high":float(np.quantile(sims,.975)),
        "months":n,"method":"paired 6-month circular blocks, 6000 replicates"})
pd.DataFrame(rows).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
scorepaths=sorted(root.glob("**/OOS_SCORES.csv"));assert len(scorepaths)==3
scores=pd.concat([pd.read_csv(f) for f in scorepaths],ignore_index=True)
scores.signal_date=pd.to_datetime(scores.signal_date,format="mixed")
assert not scores.duplicated(["variant","signal_date","ticker"]).any()
scores.to_csv(out/"OOS_SCORES.csv",index=False)
auditfiles=sorted(root.glob("**/FIT_AUDIT.json"))
audits=[]
for f in auditfiles:audits.extend(json.loads(f.read_text()))
assert len(audits)==18
(out/"FIT_AUDIT.json").write_text(json.dumps(audits,indent=2))
dupfiles=sorted(root.glob("**/DUPLICATE_ALIAS_AUDIT.json"))
assert len(dupfiles)==3 and all(len(json.loads(x.read_text()))==15 for x in dupfiles)
(out/"DUPLICATE_ALIAS_AUDIT.json").write_text(dupfiles[0].read_text())
(out/"MANIFEST.json").write_text(json.dumps({
  "experiment":"V3-L02 Tail dedup only",
  "n_mature_63d_label_months":len(a),"source_run":39482809691,
  "two_arms":["TAIL_FULL60","TAIL_DEDUP45"],
  "true_tail_objective":"y_tailmix of matured cross-sectional return percentiles",
  "primary_tail_metrics":["tail_event_ap","tail_elite_recall_top15","basket_tail_top3"],
  "false_selection_metric":"21D future worst-decile ETF selected",
  "ranker_and_feature_definition":"frozen corrected V3 no modifications",
  "cagr_used":False,"risk_macro_blend_allocation":False,
  "holdout":"2018-2026 historically explored; not untouched holdout"},indent=2))
(out/"SUMMARY.md").write_text("# V3 L02 Tail signal alone: upper-event classification and recall\n\n"+
   "Same 149 ETFs, 500 baskets, expanding annual train, matured 63D targets. "+
   "Ridge(alpha=30) identical; remove 15 exact duplicate Tail column aliases only. "+
   "No CAGR or fused ranker.\n\n"+s.round(6).to_markdown()+"\n")
print("V3_L02_METRICS\n",s.to_string(),flush=True)
