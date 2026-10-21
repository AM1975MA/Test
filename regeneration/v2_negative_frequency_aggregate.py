#!/usr/bin/env python3
"""Aggregate strict calendar-matched V2 frequency-feature experiment."""
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
p=argparse.ArgumentParser()
p.add_argument("--root",default="runs/v2_negative_frequency_shards")
p.add_argument("--out",default="runs/v2_negative_frequency_complete")
args=p.parse_args()
root=Path(args.root);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
files=sorted(root.glob("**/PAIRED_MONTHLY.csv"))
if len(files)!=3:raise RuntimeError(f"Expect 3 disjoint year shards: {files}")
df=pd.concat([pd.read_csv(x) for x in files],ignore_index=True)
# Historical OOS controls serialize midnight timestamps; new month stats use ISO dates.
# Compare semantic trading dates, never raw string representation.
df["signal_date"]=pd.to_datetime(df["signal_date"],format="mixed")
names=["LEGACY","CORRECTED","CORRECTED_PLUS_FREQ"]
assert set(df.variant.unique())==set(names)
assert not df.duplicated(["signal_date","variant"]).any()
ref=df[df.variant=="LEGACY"].sort_values("signal_date").reset_index(drop=True)
assert len(ref)==101,("Unexpected historical months",len(ref))
assert set(ref.year)==set(range(2018,2027))
for name in names[1:]:
    item=df[df.variant==name].sort_values("signal_date").reset_index(drop=True)
    for col in ("signal_date","n_tickers","n_baskets"):
        pd.testing.assert_series_equal(item[col],ref[col])
df.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
metrics=["universe_ic","universe_top1","universe_top3","universe_regret",
    "universe_selected_excess","basket_top1","basket_top3","basket_regret",
    "basket_selected_excess"]
summary=df.groupby("variant")[metrics].mean()
summary.insert(0,"months",df.groupby("variant").size())
summary.to_csv(out/"RESULTS.csv")
years=df.groupby(["year","variant"],as_index=False)[metrics].mean()
years.to_csv(out/"YEARLY.csv",index=False)
def compare(new_name,old_name,metric):
    one=df[df.variant==new_name].sort_values("signal_date")[metric].to_numpy(float)
    other=df[df.variant==old_name].sort_values("signal_date")[metric].to_numpy(float)
    delta=one-other;n=len(delta)
    rng=np.random.default_rng(20261021)
    reps=6000;window=6
    starts=rng.integers(0,n,size=(reps,int(np.ceil(n/window))))
    ix=((starts[:,:,None]+np.arange(window))%n).reshape(reps,-1)[:,:n]
    sim=delta[ix].mean(axis=1)
    return {"arm":new_name,"reference":old_name,"metric":metric,"months":n,
        "mean_delta":float(delta.mean()),"ci95_lower":float(np.quantile(sim,.025)),
        "ci95_upper":float(np.quantile(sim,.975)),
        "method":"paired monthly circular 6-month block bootstrap; 6000 resamples"}
rows=[compare(arm,base,metric) for arm,base in
    (("CORRECTED_PLUS_FREQ","LEGACY"),("CORRECTED_PLUS_FREQ","CORRECTED"),
     ("CORRECTED","LEGACY")) for metric in metrics]
pd.DataFrame(rows).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
scores=sorted(root.glob("**/OOS_SCORES.csv"))
if len(scores)!=3:raise RuntimeError("Not all three score shards present")
sc=pd.concat([pd.read_csv(x) for x in scores],ignore_index=True)
sc["signal_date"]=pd.to_datetime(sc["signal_date"],format="mixed")
if sc.duplicated(["variant","signal_date","ticker"]).any():raise RuntimeError("Duplicate score keys")
for name in names:
    key=sc[sc.variant==name][["signal_date","ticker"]].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    base=sc[sc.variant==names[0]][["signal_date","ticker"]].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    assert key.equals(base),name
sc.to_csv(out/"OOS_SCORES.csv",index=False)
fitsa=sorted(root.glob("**/FIT_AUDIT.json"))
audits=[]
for f in fitsa:audits.extend(json.loads(f.read_text()))
assert len(fitsa)==3 and len(audits)==9
(out/"FIT_AUDIT.json").write_text(json.dumps(audits,indent=2))
featurea=sorted(root.glob("**/FEATURE_AUDIT.json"))
assert len(featurea)==3
for f in featurea:
    data=json.loads(f.read_text())
    assert len(data)==3 and set(v["feature"] for v in data)==set(
        "negative_day_fraction"+str(h) for h in [21,63,126])
(out/"FEATURE_AUDIT.json").write_text(json.dumps(json.loads(featurea[0].read_text()),indent=2))
(out/"MANIFEST.json").write_text(json.dumps({"snapshot_run":39482809691,
    "baseline_complete_run":39515716383,
    "new_ensemble":"CORRECTED_PLUS_FREQ","features":128,
    "new_signals":["negative_day_fraction21","negative_day_fraction63","negative_day_fraction126"],
    "period":"2018-2026","mature_months":101,"shards":[str(x) for x in files],
    "ensemble_model":"rank:pairwise; 127 leaves, 360 trees, seeds 101/202/303",
    "prior_scores":"original from prior frozen matched annual retrain",
    "evaluation":"exploratory historically examined dates; no independent holdout",
    "risk_tail_macro":"disabled","production_change":False},indent=2))
(out/"SUMMARY.md").write_text("# V2 explicit negative-day frequency test\n\n"+
    "Corrected 125 + 3 explicit causal trailing fractions. Fully retrained annual 127-leaf ranker. "+
    "Prior two controls were retrained in successful 39515716383, not updated. "+
    "101 calendar-matched matured months, 149 ETFs and 500 fixed baskets; no Tail/Macro/risk. "+
    "The same market years have been researched previously, not untouched holdout.\n\n"+
    summary.round(6).to_markdown()+"\n")
print("AGGREGATE_OK\n"+summary.to_string(),flush=True)
