#!/usr/bin/env python3
"""L02 upper-decile event-classification skill vs frozen 45 Tail regression."""
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
p=argparse.ArgumentParser()
p.add_argument("--root",default="runs/v3_l02_event_shards")
p.add_argument("--out",default="runs/v3_l02_event_complete")
a=p.parse_args()
root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
files=sorted(root.glob("**/PAIRED_MONTHLY.csv"))
if len(files)!=3:raise RuntimeError(f"Missing year folds: {files}")
df=pd.concat([pd.read_csv(f) for f in files],ignore_index=True)
df.signal_date=pd.to_datetime(df.signal_date,format="mixed")
refname="TAIL_EVENT_LOGIT45";candname="TAIL_ELITE_BAD25"
assert set(df.variant)=={refname,candname}
assert not df.duplicated(["variant","signal_date"]).any()
ref=df[df.variant==refname].sort_values("signal_date").reset_index(drop=True)
cand=df[df.variant==candname].sort_values("signal_date").reset_index(drop=True)
assert len(ref)==98
for field in ("signal_date","n_tickers","n_baskets","tail_event_rate"):
    pd.testing.assert_series_equal(ref[field],cand[field])
metrics=["tail_event_ap","tail_event_auc","tail_elite_recall_top15",
"tail_elite_precision_top15","tail_rank_ic","basket_tail_top1",
"basket_tail_top3","basket_tail_regret","basket_bottom_decile_false_selection"]
df.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
summ=df.groupby("variant")[metrics].mean()
summ.insert(0,"months",df.groupby("variant").size())
summ.to_csv(out/"RESULTS.csv")
df.groupby(["year","variant"],as_index=False)[metrics].mean().to_csv(out/"YEARLY.csv",index=False)
rows=[]
for metric in metrics:
    delta=(cand[metric]-ref[metric]).to_numpy(float)
    assert np.isfinite(delta).all(),metric
    n=len(delta);rng=np.random.default_rng(20261021);nrep=6000;block=6
    starts=rng.integers(0,n,size=(nrep,int(np.ceil(n/block))))
    ix=((starts[:,:,None]+np.arange(block))%n).reshape(nrep,-1)[:,:n]
    sims=delta[ix].mean(axis=1)
    rows.append({"arm":candname,"reference":refname,"metric":metric,
        "mean_delta":float(delta.mean()),
        "ci95_low":float(np.quantile(sims,.025)),
        "ci95_high":float(np.quantile(sims,.975)),
        "months":n,"resampling":"paired month 6-month blocks, 6000 reps"})
pd.DataFrame(rows).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
scores=sorted(root.glob("**/OOS_SCORES.csv"));assert len(scores)==3
outscore=pd.concat([pd.read_csv(s) for s in scores],ignore_index=True)
outscore.signal_date=pd.to_datetime(outscore.signal_date,format="mixed")
assert not outscore.duplicated(["variant","signal_date","ticker"]).any()
base=outscore[outscore.variant==refname].sort_values(["signal_date","ticker"])
test=outscore[outscore.variant==candname].sort_values(["signal_date","ticker"])
assert len(base)==len(test)
outscore.to_csv(out/"OOS_SCORES.csv",index=False)
fit=[]
for f in sorted(root.glob("**/FIT_AUDIT.json")):
    fit.extend(json.loads(f.read_text()))
assert len(fit)==9
(out/"FIT_AUDIT.json").write_text(json.dumps(fit,indent=2))
riskfiles=sorted(root.glob("**/BAD_HEAD_CALIBRATION.csv"))
if len(riskfiles)!=3:raise RuntimeError("Missing risk-head OOS calibration shards")
risk=pd.concat([pd.read_csv(f) for f in riskfiles],ignore_index=True)
risk.signal_date=pd.to_datetime(risk.signal_date,format="mixed")
assert not risk.signal_date.duplicated().any()
risk.to_csv(out/"BAD_HEAD_CALIBRATION.csv",index=False)
(out/"BAD_HEAD_SUMMARY.json").write_text(json.dumps({
  "observed_months":len(risk),"bottom_event_AP_mean":float(risk.bottom_event_ap.mean()),
  "bottom_event_AUC_mean":float(risk.bottom_event_auc.mean()),
  "bottom_event_Brier_mean":float(risk.bottom_event_brier.mean()),
  "bottom_event_base_rate_mean":float(risk.bottom_event_rate.mean()),
  "calibration_note":"Brier includes rare-event prevalence and cannot alone establish predictive calibration"
},indent=2))
(out/"MANIFEST.json").write_text(json.dumps({
    "experiment":"V3 L02 penalize false bottom-decile ETF selections with independent head",
    "period":"2018–2026, 98 months with fully matured 63D labels",
    "reference":"TAIL_EVENT_LOGIT45 frozen binary elite head",
    "challenger":"TAIL_ELITE_BAD25 risk-penalized score with additional bad-head Logistic C0.2",
    "evaluation":"Tail AP, upper-elite recall@15, Tail IC, basket Tail Top3, extreme false selection",
    "inputs_source_run":39482809691,"controls_from_run":39655513813,
    "cagr":False,"allocation_macro_risk":False,"not_virgin_holdout":True},indent=2))
(out/"SUMMARY.md").write_text("# V3 L02 Tail: direct rare-winner event classification\n\n"+
    "same 45 corrected Tail inputs; frozen elite logistic vs elite minus risk penalty "+
    "with mature future 63D training only. No CAGR.\n\n"+summ.round(6).to_markdown()+"\n")
print("V3_L02_BAD_HEAD_RESULT\n"+summ.to_string(),flush=True)
