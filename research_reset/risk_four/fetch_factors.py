#!/usr/bin/env python3
"""Capture Yahoo factor-proxy raw daily Close series, verify coverage, provenance."""
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf

FACTORS=("SPY","TLT","GLD","USO","HYG","UUP","VNQ","XLE")
START="2016-05-01"
END="2026-07-03"

def download_factors(folder):
    d=Path(folder)
    d.mkdir(parents=True,exist_ok=False)
    cols={}
    provenance={}
    for ticker in FACTORS:
        z=yf.Ticker(ticker).history(start=START,end=END,auto_adjust=False,
                                    actions=False,raise_errors=True)
        if z.empty or "Close" not in z:
            raise RuntimeError("Yahoo factor proxy unavailable: "+ticker)
        # Close, not Adj Close: avoid retroactively altering PAST closes for
        # dividends paid only in the future. Yahoo itself still split-revises.
        x=z[["Close"]].copy()
        x.index=pd.to_datetime(x.index).tz_localize(None).normalize()
        x=x[~x.index.duplicated(keep="first")]
        c=x.Close.astype(float)
        if not np.isfinite(c.to_numpy()).all() or (c<=0).any():
            raise ValueError("bad proxy price "+ticker)
        if c.index.min()>pd.Timestamp("2016-12-01") or c.index.max()<pd.Timestamp("2026-06-25"):
            raise ValueError("insufficient historical factor price "+ticker)
        cols[ticker]=c
        provenance[ticker]=dict(source="Yahoo yfinance",first=str(c.index.min().date()),
                                last=str(c.index.max().date()),observations=len(c),
                                auto_adjust=False,price_field="Close")
        print("R149_R_YAHOO",ticker,len(c),flush=True)
    frame=pd.concat(cols,axis=1).sort_index()
    fname=d/"YAHOO_FACTOR_CLOSE.csv"
    frame.index.name="date"
    frame.to_csv(fname,float_format="%.12g")
    digest=hashlib.sha256(fname.read_bytes()).hexdigest()
    manifest=dict(source="yfinance Yahoo historical quoted Close",
                  retrieved_utc=str(pd.Timestamp.now(tz="UTC")),
                  request_start=START,request_end_exclusive=END,
                  factors=provenance,sha256=digest,
                  point_in_time_vintage=False,
                  no_trade_on_proxy=True)
    (d/"YAHOO_FACTOR_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    download_factors(p.parse_args().out)
