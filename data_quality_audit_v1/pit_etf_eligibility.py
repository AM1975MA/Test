"""Research-only no-lookahead ETF feature availability gate. No pipeline mutation.

Eligibility is source chronological Close history: 253 complete observed daily bars
at signal, and a separate Compact21 all-125-feature completeness diagnostic.
These are NOT claimed as comprehensive Tail/MA3 feature eligibility.
"""
from pathlib import Path
import argparse,json,ast
import numpy as np,pandas as pd
def features():
 t=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
 return next(ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=="F2D_FEATURES" for x in n.targets))
def main():
 p=argparse.ArgumentParser()
 for k in ["raw1","raw2","raw3","panel1","panel2","panel3","out"]:p.add_argument("--"+k,required=True)
 a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 ff=features();rows=[];aggregate=[]
 for i in (1,2,3):
  d=pd.read_parquet(Path(getattr(a,f"panel{i}"))/"TI_COMPACT.parquet")
  d["signal_date"]=pd.to_datetime(d.signal_date)
  d=d.sort_values(["signal_date","ticker"]).reset_index(drop=True)
  elig30=np.isfinite(d[ff].to_numpy(float)).sum(axis=1)>=30
  full=np.isfinite(d[ff].to_numpy(float)).all(axis=1)
  raw=Path(getattr(a,f"raw{i}"));m={}
  for ticker in d.ticker.unique():
   source=pd.read_csv(raw/f"{ticker}.csv",parse_dates=["date"]).sort_values("date")
   source=source.drop_duplicates("date")
   valid=np.isfinite(source.Close.to_numpy(float))&(source.Close.to_numpy(float)>0)
   # Consecutive-valid count resets after invalid observation; do not fill gaps.
   counts=np.empty(len(source),dtype=int);carry=0
   for j,ok in enumerate(valid):
    carry=(carry+1) if ok else 0;counts[j]=carry
   m[ticker]=pd.Series(counts,index=pd.DatetimeIndex(source.date))
  d["raw_lookback_bars"]=[int(m[t].get(date,0)) for t,date in zip(d.ticker,d.signal_date)]
  d["raw253"]=d.raw_lookback_bars>=253
  d["prior_compact30"]=elig30;d["compact_all125"]=full
  d["pit_raw253_and_30"]=d.raw253 & d.prior_compact30
  d["pit_raw253_and_125"]=d.raw253 & d.compact_all125
  start=d[d.signal_date>=pd.Timestamp("2017-01-01")].copy()
  grouped=start.groupby("signal_date").agg(
     candidate_tickers=("ticker","nunique"),raw253_tickers=("raw253","sum"),
     existing30_tickers=("prior_compact30","sum"),
     eligible_raw253_30=("pit_raw253_and_30","sum"),
     eligible_raw253_125=("pit_raw253_and_125","sum")).reset_index()
  grouped["repeat"]=i
  grouped.to_csv(out/f"DAILY_ELIGIBILITY_REPEAT{i}.csv",index=False)
  # Provide per-ticker/date decisions for verifiability, no backtest.
  start[["signal_date","ticker","raw_lookback_bars","raw253","prior_compact30","compact_all125","pit_raw253_and_30","pit_raw253_and_125"]].to_csv(out/f"TICKER_ELIGIBILITY_REPEAT{i}.csv",index=False)
  aggregate.append({"repeat":i,"operational_signal_dates":len(grouped),
    "operational_ticker_dates":len(start),
    "failed_raw253":int((~start.raw253).sum()),
    "failed_existing30":int((~start.prior_compact30).sum()),
    "failed_raw253_and30":int((~start.pit_raw253_and_30).sum()),
    "failed_strict125":int((~start.pit_raw253_and_125).sum()),
    "dates_with_less_than_149_raw253":int((grouped.raw253_tickers<149).sum()),
    "min_daily_eligible_raw253_30":int(grouped.eligible_raw253_30.min()),
    "median_daily_eligible_raw253_30":float(grouped.eligible_raw253_30.median())})
 report={"status":"POINT_IN_TIME_COMPACT_RAW_253_AUDIT","summary":aggregate,
 "caveats":["Source calendar recorded bars may include non-trading zero-volume bars","This is a raw Close-window test + Compact21 count, NOT validated full MA3/Tail/Macro gate","No historical membership change, no training or CAGR"],"no_production_change":True}
 (out/"RESULT.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2))
if __name__=="__main__":main()
