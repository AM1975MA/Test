#!/usr/bin/env python3
"""Merge chronological V2 formula migration folds and compute paired inference."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
p=argparse.ArgumentParser()
p.add_argument("--root",default="runs/v2_formula_shards")
p.add_argument("--out",default="runs/v2_formula_complete")
a=p.parse_args()
root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
files=sorted(root.glob("**/PAIRED_MONTHLY.csv"))
if len(files)!=3:raise RuntimeError(f"Expected 3 year-disjoint shards, got {files}")
df=pd.concat([pd.read_csv(f) for f in files],ignore_index=True)
if df.duplicated(["variant","signal_date"]).any():raise RuntimeError("Duplicate variant/date")
df=df.sort_values(["signal_date","variant"]).reset_index(drop=True)
names=sorted(df.variant.unique())
assert set(names)=={"LEGACY","DOWNVOL_ONLY","CORRECTED"},names
ref=df[df.variant=="LEGACY"].set_index("signal_date").sort_index()
dates=pd.to_datetime(ref.index)
assert len(dates)>=100 and int(dates.year.min())==2018 and int(dates.year.max())==2026
assert ref.year.to_numpy().min()==2018
for name in names:
    test=df[df.variant==name].set_index("signal_date").sort_index()
    assert test.index.equals(ref.index),f"Unpaired dates: {name}"
    assert test[["n_tickers","n_baskets"]].equals(ref[["n_tickers","n_baskets"]])
df.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
metrics=["universe_ic","universe_top1","universe_top3","universe_regret",
         "universe_selected_excess","basket_top1","basket_top3","basket_regret",
         "basket_selected_excess"]
s=df.groupby("variant")[metrics].mean();s.insert(0,"months",df.groupby("variant").size());s.to_csv(out/"RESULTS.csv")
rows=[]
for name in names:
    if name=="LEGACY":continue
    other=df[df.variant==name].set_index("signal_date").sort_index()
    for metric in metrics:
        diff=(other[metric]-ref[metric]).to_numpy(float)
        assert np.isfinite(diff).all(),(name,metric)
        n=len(diff);reps=6000;block=6
        rng=np.random.default_rng(20261021)
        starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
        ix=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
        sims=diff[ix].mean(axis=1)
        # Also show year-by-year deltas for robustness audit (not independent CIs).
        rows.append({"variant":name,"metric":metric,"n_months":n,
            "mean_delta":float(diff.mean()),"ci95_lower":float(np.quantile(sims,.025)),
            "ci95_upper":float(np.quantile(sims,.975)),
            "method":"paired circular 6-calendar-month block bootstrap, all OOS months 2018-26"})
pd.DataFrame(rows).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
years=df.groupby(["year","variant"],as_index=False)[metrics].mean()
years.to_csv(out/"YEARLY.csv",index=False)
out_scores=sorted(root.glob("**/OOS_SCORES.csv"))
if len(out_scores)!=3:raise RuntimeError(f"Expected 3 fold score files, got {len(out_scores)}")
fullscores=pd.concat([pd.read_csv(f) for f in out_scores],ignore_index=True)
if fullscores.duplicated(["variant","signal_date","ticker"]).any():
    raise RuntimeError("Duplicate OOS score keys")
fullscores.to_csv(out/"OOS_SCORES.csv",index=False)
audit=sorted(root.glob("**/FIT_AUDIT.json"))
manifest=sorted(root.glob("**/MANIFEST.json"))
assert len(audit)==len(manifest)==3
all_audit=[]
for f in audit:all_audit+=json.loads(f.read_text())
(out/"FIT_AUDIT.json").write_text(json.dumps(all_audit,indent=2))
(out/"MANIFEST.json").write_text(json.dumps({"status":"FULL_CHRONOLOGICAL_RETRAIN_EVALUATED",
    "months_with_matured_labels":len(dates),"variants":names,
    "years":sorted(df.year.unique().astype(int).tolist()),
    "frozen_raw_run":39482809691,
    "source_kernel_sha":"351307d549fa70dea70f77cbefddfc24894b6882",
    "gating":"No production promotion. Used explored historical years.",
    "risk_overlays_enabled":False,
    "note":"Labels, eligibility, time and raw inputs identical; all variant models refitted."},indent=2))
(out/"SUMMARY.md").write_text("# V2 125 feature formula correction: matched full annual OOS\n\n"+
    "Corrected vs legacy 127-leaf XGB-only ranking, 2018-2026, same frozen raw snapshot.\n"
    "Bootstrap resamples only chronological months, *not* overlapping canonical baskets.\n\n"+
    s.round(5).to_markdown()+"\n")
print("FORMULA_COMPARE_DONE\n",s.to_string(),flush=True)
