"""Read-only earliest-training-history gate for Compact21 annual 2017 warmup.
This is NOT approval to truncate data: other V2 learning modules and features
must pass prefix-replay invariance before any history can be removed.
"""
import ast,json
from pathlib import Path
import pandas as pd,numpy as np
t=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
ff=next(ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and any(isinstance(z,ast.Name) and z.id=="F2D_FEATURES" for z in n.targets))
o=Path("_report");o.mkdir(exist_ok=True)
results=[];ticker=[]
for i in (1,2,3):
 d=pd.read_parquet(f"_panels/alpha_1/repeat_{i}/TI_COMPACT.parquet")
 d.signal_date=pd.to_datetime(d.signal_date)
 avail=d[ff].notna().sum(axis=1)
 d["elig30"]=avail.ge(30)
 d["complete125"]=avail.eq(125)
 train=d[(d.signal_date<pd.Timestamp("2017-01-01")) & d.elig30]
 dates=sorted(train.signal_date.unique())
 if not dates:raise RuntimeError("No pre-2017 feature-eligible history")
 # Existence of prior month signals is NOT proof labels have matured; train gate
 # is <= exit_date_21 and subject to actual full training pipeline.
 yearly=train.groupby(train.signal_date.dt.year).agg(
   rows=("ticker","size"),etfs=("ticker","nunique"),signals=("signal_date","nunique"),
   complete=("complete125","sum")).reset_index().rename(columns={"signal_date":"year"})
 for row in yearly.to_dict("records"):row["repeat"]=i;results.append(row)
 for k,g in d[d.signal_date<pd.Timestamp("2017-01-01")].groupby("ticker"):
  q=g[g.elig30].sort_values("signal_date")
  ticker.append({"repeat":i,"ticker":k,"first_30_feature_date":str(q.signal_date.min().date()) if len(q) else None,
    "last_pre2017_date":str(q.signal_date.max().date()) if len(q) else None,
    "pre2017_eligible_signals":int(q.signal_date.nunique())})
 (o/f"SUMMARY_REPEAT{i}.json").write_text(json.dumps({
   "repeat":i,"earliest_pre2017_eligible_signal":str(pd.Timestamp(dates[0]).date()),
   "pre2017_eligible_unique_monthly_signals":len(dates),
   "max_train_cutoff":"2017-01-01",
   "first2017_minimum60_monthly_signals_possible":len(dates)>=60,
   "labels_and_full_v2_not_verified":True},indent=2))
pd.DataFrame(results).to_csv(o/"PRE2017_COMPACT_MONTHLY_TRAINING_COVERAGE.csv",index=False)
pd.DataFrame(ticker).to_csv(o/"PER_TICKER_PRE2017_ELIGIBILITY.csv",index=False)
first=min(pd.to_datetime([x["first_30_feature_date"] for x in ticker if x["first_30_feature_date"]]))
result={"status":"PRE2017_COMPACT_FEATURE_COVERAGE_ONLY","earliest_first_eligible":str(first.date()),
 "trained_model_history_retention_decision":"NO_CUTOFF_CERTIFIED",
 "reason":"Removing any pre-2017 training dates can change annual model fits; 60-signal minimum is only minimum, not finite fixed history window.",
 "other_models_not_yet_audited":True,"no_data_deleted":True,"no_training":True}
(o/"RESULT.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result,indent=2))
