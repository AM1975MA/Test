#!/usr/bin/env python3
"""L00 feature-family ablation: aggregate paired calendar months and models.

Two new arms plus two archived controls; 500 overlapping baskets aggregated
within each month. No outcome selection using the test data.
"""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

p=argparse.ArgumentParser()
p.add_argument("--root",default="runs/v3_l00_shards")
p.add_argument("--out",default="runs/v3_l00_complete")
args=p.parse_args()
root=Path(args.root);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
paths=sorted(root.glob("**/PAIRED_MONTHLY.csv"))
if len(paths)!=3:raise RuntimeError(f"Expected three training shards, got {paths}")
df=pd.concat([pd.read_csv(f) for f in paths],ignore_index=True)
df["signal_date"]=pd.to_datetime(df.signal_date,format="mixed")
arms=["LEGACY","CORRECTED","V3_GATE128","V3_CONDSTD128"]
assert set(df.variant.unique())==set(arms),df.variant.unique()
assert not df[["variant","signal_date"]].duplicated().any()
base=df[df.variant=="LEGACY"].sort_values("signal_date").reset_index(drop=True)
assert len(base)==101
assert sorted(base.year.unique())==list(range(2018,2027))
for arm in arms[1:]:
    candidate=df[df.variant==arm].sort_values("signal_date").reset_index(drop=True)
    for field in ["signal_date","n_tickers","n_baskets"]:
        pd.testing.assert_series_equal(base[field],candidate[field])
df.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
metrics=["universe_ic","universe_top1","universe_top3","universe_regret",
         "universe_selected_excess","basket_top1","basket_top3","basket_regret",
         "basket_selected_excess"]
summary=df.groupby("variant")[metrics].mean()
summary.insert(0,"months",df.groupby("variant").size())
summary.to_csv(out/"RESULTS.csv")
df.groupby(["year","variant"],as_index=False)[metrics].mean().to_csv(out/"YEARLY.csv",index=False)
rows=[]
for arm in arms[1:]:
    for ref in ["LEGACY","CORRECTED"]:
        if arm==ref:continue
        t=df[df.variant==arm].sort_values("signal_date").reset_index(drop=True)
        b=df[df.variant==ref].sort_values("signal_date").reset_index(drop=True)
        for metric in metrics:
            d=(t[metric]-b[metric]).to_numpy(float)
            if not np.isfinite(d).all():raise RuntimeError((arm,metric))
            rng=np.random.default_rng(20261021)
            reps=6000;block=6;n=len(d)
            starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
            ix=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
            sim=d[ix].mean(axis=1)
            rows.append({"arm":arm,"reference":ref,"metric":metric,"months":n,
                "mean_delta":float(d.mean()),"ci95_low":float(np.quantile(sim,.025)),
                "ci95_high":float(np.quantile(sim,.975)),
                "bootstrap":"shared calendar-month, 6-month circular blocks, 6000 replicates"})
pd.DataFrame(rows).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
scs=sorted(root.glob("**/OOS_SCORES.csv"))
assert len(scs)==3
sc=pd.concat([pd.read_csv(f) for f in scs],ignore_index=True)
sc["signal_date"]=pd.to_datetime(sc.signal_date,format="mixed")
assert not sc[["variant","signal_date","ticker"]].duplicated().any()
base_keys=sc[sc.variant=="LEGACY"][["signal_date","ticker"]].sort_values(["signal_date","ticker"]).reset_index(drop=True)
for arm in arms[1:]:
    k=sc[sc.variant==arm][["signal_date","ticker"]].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(k,base_keys)
sc.to_csv(out/"OOS_SCORES.csv",index=False)
auditfiles=sorted(root.glob("**/FIT_AUDIT.json"));assert len(auditfiles)==3
audits=[]
for path in auditfiles:audits.extend(json.loads(path.read_text()))
assert len(audits)==18 # 9 years * 2 new 128-column arms
(out/"FIT_AUDIT.json").write_text(json.dumps(audits,indent=2))
feature=sorted(root.glob("**/FEATURE_AUDIT.json"));assert len(feature)==3
(out/"FEATURE_AUDIT.json").write_text(feature[0].read_text())
(out/"MANIFEST.json").write_text(json.dumps({
    "protocol":"V3_L00_DOWNVOL_REGIME_20261021",
    "n_mature_months":len(base),
    "n_etfs":149,"n_baskets":500,"basket_size":24,
    "candidate_models":["V3_GATE128","V3_CONDSTD128"],
    "reference_models":["LEGACY","CORRECTED"],
    "historical_oracle_run":39515716383,"source_raw_run":39482809691,
    "data_label_eligibility_paired":True,
    "ranker_params":"XGBRanker 127 leaves, 360 trees, 3 seeds",
    "tail_macro_risk_disabled":True,
    "uncertainty_note":"Historical dates previously used extensively. Exploratory only; not virgin confirmation.",
    "production_promotion":False},indent=2))
(out/"SUMMARY.md").write_text("# V3 L00: downvol-regime representation research\n\n"+
  "Predeclared 2 challenger tests; old 125 and corrected 125 controls are independently "+
  "frozen. Identical 149 ETF-month observations, expanding annual OOS, 500 baskets. "+
  "The 101 months are historical *exploratory* data, NOT a virgin holdout.\n\n"+
  summary.round(6).to_markdown()+"\n")
print("V3_L00_AGGREGATED\n"+summary.to_string(),flush=True)
