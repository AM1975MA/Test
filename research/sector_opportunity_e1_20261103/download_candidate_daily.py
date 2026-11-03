"""Download and freeze adjusted daily OHLCV of candidate ETFs (separate from portfolio backtest)."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
import pandas as pd
import numpy as np
import yfinance as yf

D=Path(__file__).resolve().parent
OUT=D/"results"/"candidate_daily"
OUT.mkdir(parents=True,exist_ok=True)
CANDIDATES={"EU":["G2X.DE","USPY.DE","CMOD.MI","WTIC.DE","2B76.DE"],
            "USA":["BOTZ","LIT","PAVE"]}
qa=[]
for market,tickers in CANDIDATES.items():
    for ticker in tickers:
        try:
            d=yf.download(ticker,start="2017-01-01",end="2026-07-05",
                          auto_adjust=True,progress=False,threads=False,interval="1d")
            if d.empty: raise RuntimeError("Empty Yahoo history")
            if isinstance(d.columns,pd.MultiIndex):
                d.columns=d.columns.get_level_values(0)
            d=d.reset_index()
            d.columns=[str(c).lower() for c in d.columns]
            if "date" not in d.columns and "datetime" in d.columns:d.rename(columns={"datetime":"date"},inplace=True)
            d["date"]=pd.to_datetime(d["date"]).dt.tz_localize(None).dt.date.astype(str)
            wanted=["date","open","high","low","close","volume"]
            d=d[wanted]
            for c in wanted[1:]:d[c]=pd.to_numeric(d[c],errors="coerce")
            d=d[(d["open"]>0)&(d["close"]>0)&np.isfinite(d["open"])&np.isfinite(d["close"])]
            if d["date"].duplicated().any():raise RuntimeError("Duplicate dates")
            d=d.sort_values("date")
            bad=int(((d.low>d.high)|(d.low>d.open)|(d.low>d.close)|(d.high<d.open)|(d.high<d.close)).sum())
            dest=OUT/(ticker.replace(".","_")+".csv.gz")
            d.to_csv(dest,index=False,float_format="%.10f",compression="gzip")
            qa.append({"market":market,"ticker":ticker,"n":len(d),"first":d.date.min(),"last":d.date.max(),
                       "bad_ohlc":bad,"sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
                       "status":"ok"})
            print("OK",ticker,len(d),d.date.min(),d.date.max(),"bad ohlc",bad,flush=True)
        except Exception as e:
            qa.append({"market":market,"ticker":ticker,"status":"ERROR","reason":repr(e)})
            print("ERROR",ticker,repr(e),flush=True)
pd.DataFrame(qa).to_csv(OUT/"quality.csv",index=False)
(OUT/"manifest.json").write_text(json.dumps({"generated_utc":datetime.now(timezone.utc).isoformat(),
"vendor":"Yahoo through yfinance","price_adjustment":"yfinance auto_adjust=True",
"no_updating_original_OHLC":True,"role":"research price input, not broker-validated","notes":
"Quote as-of history is not PIT evidence that an ETF was listed throughout; use first observed bar and eligibility guards."},indent=2))
if any(q["status"]=="ERROR" for q in qa): raise RuntimeError("Not all candidate histories available")
