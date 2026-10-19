#!/usr/bin/env python3
"""Download original European evaluation EURUSD=X reference, not portfolio funds.

At an EU previous Close use ONLY previous-US-day FX + US ETF price.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
import pandas as pd
import yfinance as yf

def main(out):
    p=Path(out);p.mkdir(parents=True,exist_ok=False)
    d=yf.Ticker("EURUSD=X").history(start="2015-01-01",
          end="2026-07-08",auto_adjust=False,actions=False,raise_errors=True)
    if d.empty:raise AssertionError("Yahoo EURUSD=X missing")
    v=d[["Close"]].copy()
    v.index=pd.to_datetime(v.index).tz_localize(None).normalize()
    v=v[~v.index.duplicated(keep="first")].sort_index()
    v["Close"]=v.Close.astype(float)
    if (not np.isfinite(v.Close).all() or (v.Close<=0).any()
        or v.index.min()>pd.Timestamp("2015-06-01")
        or v.index.max()<pd.Timestamp("2026-06-25")):
        raise AssertionError("Incomplete EURUSD history")
    v.index.name="date"
    filename=p/"EURUSD_PRIOR_US_CLOSE.csv"
    v.to_csv(filename,float_format="%.12g")
    manifest=dict(ticker="EURUSD=X",vendor="Yahoo yfinance",
        source_url="https://finance.yahoo.com/quote/EURUSD=X/",
        start=str(v.index.min().date()),end=str(v.index.max().date()),
        row_count=len(v),asof_rule="US market close & EURUSD one calendar day lag at EU signal",
        latest_retrieval=str(pd.Timestamp.now(tz="UTC")),
        sha256=hashlib.sha256(filename.read_bytes()).hexdigest(),
        point_in_time_vintage=False,
        portfolio_EUR_currency_verified=False)
    (p/"SOURCE_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("EURUSD_FX_DOWNLOAD "+json.dumps(manifest),flush=True)
if __name__=="__main__":
    q=argparse.ArgumentParser();q.add_argument("--out",required=True)
    main(q.parse_args().out)
