#!/usr/bin/env python3
"""OLC45-C quote integrity: differentiate raw-source OHLC defects from adjustments.
Do not 'repair' raw prints without a second independently grounded venue/provider.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yfinance as yf
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results_RAW_QA";OUT.mkdir(exist_ok=True)
TICKERS=["PHAG.MI","NGAS.MI","CMOD.MI"]
START="2017-01-01";END="2025-02-15"
def hist(t,adjust):
 d=yf.download(t,start=START,end=END,auto_adjust=adjust,actions=False,
               progress=False,threads=False,interval="1d")
 if d is None or d.empty:raise RuntimeError(f"No quotes: {t}")
 if isinstance(d.columns,pd.MultiIndex):
  d.columns=d.columns.get_level_values(0)
 d=d.rename(columns={k:k.lower().replace(" ","_") for k in d.columns})
 d.index=pd.DatetimeIndex(d.index).tz_localize(None).normalize()
 return d
def qa(d):
 a=d[["open","high","low","close"]].apply(pd.to_numeric,errors="coerce")
 valid=a.notna().all(axis=1) & (a>0).all(axis=1)
 x=a.loc[valid]
 checks={"low_above_high":x.low>x.high,
         "low_above_open":x.low>x.open,
         "low_above_close":x.low>x.close,
         "high_below_open":x.high<x.open,
         "high_below_close":x.high<x.close}
 bad=pd.DataFrame(checks).any(axis=1)
 return valid,bad,checks
def main():
 results=[];outliers=[]
 for t in TICKERS:
  try:
   r=hist(t,False)
   a=hist(t,True)
   common=r.index.intersection(a.index)
   r=r.loc[common];a=a.loc[common]
   _,rb,rc=qa(r);_,ab,ac=qa(a)
   fac=r["adj_close"]/r["close"]
   manual=r[["open","high","low","close"]].multiply(fac,axis=0)
   _,mb,mc=qa(manual)
   if not rb.index.equals(ab.index):raise RuntimeError("Open/Close valid date mismatch")
   same=((rb==ab)&(rb==mb)).all()
   results.append({
     "ticker":t,"n_overlapping_days":len(common),
     "raw_bad_days":int(rb.sum()),"auto_adjust_bad_days":int(ab.sum()),
     "manually_uniform_adjusted_bad_days":int(mb.sum()),
     "same_invalid_dates_raw_and_adjusted":bool(same),
     "median_adjustment_factor":float(fac.median()),
     "max_abs_log_change_adjustment_factor":float(np.abs(np.log(fac/fac.shift(1))).max()),
     "raw_finite_price_rows":int(r[["open","high","low","close"]].notna().all(axis=1).sum()),
     "status":"ok"
   })
   for dt in rb.index[rb|ab]:
    outliers.append({"ticker":t,"date":str(dt.date()),
       "raw_open":float(r.loc[dt,"open"]),"raw_high":float(r.loc[dt,"high"]),
       "raw_low":float(r.loc[dt,"low"]),"raw_close":float(r.loc[dt,"close"]),
       "adj_close":float(r.loc[dt,"adj_close"]),
       "adjustment_factor":float(fac.loc[dt]),
       "raw_bad":bool(rb.loc[dt]),"adjusted_bad":bool(ab.loc[dt])})
  except Exception as e:
   results.append({"ticker":t,"status":"error","message":repr(e)})
 print(pd.DataFrame(results).to_string(index=False),flush=True)
 pd.DataFrame(results).to_csv(OUT/"olc45c_quote_adjustment_diagnostic.csv",index=False)
 pd.DataFrame(outliers).to_csv(OUT/"olc45c_invalid_bar_examples.csv",index=False)
 (OUT/"manifest.json").write_text(json.dumps({"ticker":TICKERS,"source":"Yahoo via yfinance adjusted vs raw",
 "period":[START,END],"purpose":"diagnose integrity only, never repair without independent source",
 "expected_adjustment":"single positive daily factor preserves O/H/L/C ordering",
 "interpretation":"if raw and adjusted invalid on same dates, the issue is upstream OHLC itself"},indent=2))
 if any(x["status"]!="ok" for x in results):raise RuntimeError("Some provider quote data missing")
if __name__=="__main__":main()
