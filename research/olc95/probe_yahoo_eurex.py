#!/usr/bin/env python3
"""OLC95: probe Yahoo symbols for Eurex futures FESX and FGBL.
IMPORTANT: only verified contract metadata is acceptable as futures. Index proxies must be labelled separately.
"""
import csv, json, time, re, hashlib
from pathlib import Path
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd

OUT=Path("research/olc95/probe_output")
OUT.mkdir(parents=True,exist_ok=True)
SYMBOLS={
    "FESX=F": "FESX candidate", "FGBL=F": "FGBL candidate",
    "FESX.DE": "FESX candidate", "FGBL.DE": "FGBL candidate",
    "FESX.F": "FESX candidate", "FGBL.F": "FGBL candidate",
    "FESX": "FESX candidate", "FGBL": "FGBL candidate",
    "EUBL=F": "FGBL candidate", "BUND=F": "FGBL candidate",
    "^STOXX50E": "INDEX_PROXY_ONLY", "^GDAXI": "INDEX_PROXY_ONLY",
    "^DE10Y": "YIELD_PROXY_ONLY"
}
rows=[]
for symbol, group in SYMBOLS.items():
    result={"symbol":symbol,"group":group,"status":"NO_DATA",
            "futures_verified":False,"first":"","last":"","n_rows":0}
    try:
        h=yf.Ticker(symbol).history(start="2018-01-01",end="2026-11-12",
           interval="1d",auto_adjust=False,actions=False,repair=False)
        if h is not None and not h.empty:
            d=h.copy().reset_index()
            datecol="Date" if "Date" in d.columns else d.columns[0]
            d["date"]=pd.to_datetime(d[datecol]).dt.strftime("%Y-%m-%d")
            d=d.sort_values("date").drop_duplicates("date")
            if "Close" in d and d.Close.notna().sum()>0:
                dest=OUT/(re.sub(r"[^A-Za-z0-9_-]","_",symbol)+".csv")
                pd.DataFrame({"date":d.date,"close":pd.to_numeric(d.Close,errors="coerce"),
                    "volume":pd.to_numeric(d.Volume,errors="coerce") if "Volume" in d else None}).to_csv(dest,index=False)
                result.update(status="DOWNLOADED_UNVERIFIED_INSTRUMENT",
                    n_rows=int(len(d)),first=d.date.min(),last=d.date.max(),
                    file=dest.name,
                    sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
                # Never infer official Eurex futures solely from a Yahoo symbol.
                try:
                    info=yf.Ticker(symbol).get_info() or {}
                    result["shortName"]=str(info.get("shortName",""))[:200]
                    result["longName"]=str(info.get("longName",""))[:200]
                    result["quoteType"]=str(info.get("quoteType",""))[:50]
                    result["exchange"]=str(info.get("exchange",""))[:50]
                except Exception as exc:
                    result["metadata_error"]=str(exc)[:180]
    except Exception as exc:
        result.update(status="ERROR",error=str(exc)[:300])
    print(symbol,result["status"],result["n_rows"],flush=True)
    rows.append(result)
    time.sleep(1)
cols=["symbol","group","status","futures_verified","n_rows","first","last",
      "shortName","longName","quoteType","exchange","file","sha256","metadata_error","error"]
with (OUT/"coverage.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
manifest={"retrieved_at":datetime.now(timezone.utc).isoformat(),
   "source":"Yahoo Finance yfinance",
   "warning":"Instrument identity NOT verified by download; contracts require exchange code and expiry, index proxies are not futures. Historical continuous data are not PIT immutable.",
   "records":rows}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2))
print("COMPLETED",len(rows),"downloaded",sum(r["n_rows"]>0 for r in rows))
