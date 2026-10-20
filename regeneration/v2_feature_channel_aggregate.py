#!/usr/bin/env python3
"""Aggregate strictly paired monthly folds across exploratory years."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
p=argparse.ArgumentParser()
p.add_argument("--root",default="runs/v2_feature_channel_shards")
p.add_argument("--out",default="runs/v2_feature_channel_complete")
args=p.parse_args()
root=Path(args.root); out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
paths=sorted(root.glob("**/PAIRED_MONTHLY.csv"))
if not paths:raise RuntimeError("No shards found")
df=pd.concat([pd.read_csv(f) for f in paths],ignore_index=True)
if df.duplicated(["variant","signal_date"]).any():raise RuntimeError("duplicate signal and variant")
df=df.sort_values(["signal_date","variant"]).reset_index(drop=True)
names=sorted(df.variant.unique())
dates=sorted(df.signal_date.unique())
assert "BASE125" in names and len(dates)>=24 and len(df)==len(names)*len(dates)
assert set(df.groupby("variant").signal_date.nunique())=={len(dates)}
df.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
cols=["universe_ic","universe_top1","universe_top3","universe_regret",
      "universe_selected_excess","basket_top1","basket_top3","basket_regret",
      "basket_selected_excess"]
summary=df.groupby("variant")[cols].mean()
summary.insert(0,"months",df.groupby("variant").size())
summary.to_csv(out/"RESULTS.csv")
base=df[df.variant=="BASE125"].set_index("signal_date").sort_index()
rows=[]
for name in names:
    if name=="BASE125":continue
    cand=df[df.variant==name].set_index("signal_date").sort_index()
    assert base.index.equals(cand.index)
    for metric in cols:
        delta=(cand[metric]-base[metric]).to_numpy(float)
        assert np.isfinite(delta).all()
        rng=np.random.default_rng(20261021)
        n=len(delta);window=min(6,n); repeats=5000
        starts=rng.integers(0,n,size=(repeats,int(np.ceil(n/window))))
        positions=((starts[:,:,None]+np.arange(window))%n).reshape(repeats,-1)[:,:n]
        sims=delta[positions].mean(axis=1)
        rows.append({"variant":name,"metric":metric,"months":n,
                     "mean_delta":float(delta.mean()),"ci95_low":float(np.quantile(sims,.025)),
                     "ci95_high":float(np.quantile(sims,.975)),
                     "method":"Paired common-month 6-month circular block bootstrap (exploratory)"})
pd.DataFrame(rows).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
(out/"MANIFEST.json").write_text(json.dumps({
    "shards":[str(x) for x in paths],"years":sorted(int(y) for y in df.year.unique()),
    "months":len(dates),"variants":names,"paired":True,"baseline":"BASE125",
    "regime":"exploratory, not virgin holdout","snapshot_run":39482809691},indent=2))
(out/"SUMMARY.md").write_text("# V2 127-leaf feature-channel ablation\n\n"
    "Identical 149-ETF source, seeds, training rows and forward labels. "
    "XGB-only raw ranking; no Tail, Macro or risk control. Monthly cross-basket aggregation. "
    "Exploratory comparison, not independent performance confirmation.\n\n"
    +summary.round(5).to_markdown()+"\n")
print(summary.to_string(),flush=True)
