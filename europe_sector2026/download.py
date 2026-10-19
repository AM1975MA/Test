#!/usr/bin/env python3
"""Download issuer-vetted Xetra/EUR European sector UCITS via yfinance.

Keep raw Yahoo OHLC alongside (independently) adjusted OHLC for subsequent
forensic/retraining. Never repair suspicious bars or throw away failures.
Requires the frozen CATALOG.csv; 2026 membership is retrospective, NOT PIT.
"""
from __future__ import annotations
import argparse, hashlib, json, time, traceback
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
import yfinance as yf

START="2004-01-01"
END_EXCLUSIVE="2026-10-20"
LAST_STUDY="2026-07-01"
STUDY_BEGIN="2017-02-01"
FIELDS=("Open","High","Low","Close","Adj Close","Volume","Dividends","Stock Splits")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def one(ticker):
    errors=[]
    for attempt in range(2):
        try:
            asset=yf.Ticker(ticker)
            data=asset.history(start=START,end=END_EXCLUSIVE,
                 auto_adjust=False,back_adjust=False,actions=True,
                 repair=False,raise_errors=True)
            if data.empty:
                raise RuntimeError("No historical quotes")
            hist={}
            try:hist=asset.get_history_metadata() or {}
            except Exception as e:errors.append("META_"+type(e).__name__)
            return data,hist,errors
        except Exception as e:
            errors.append(type(e).__name__+": "+str(e)[:200])
            if attempt==0:time.sleep(1.)
    raise RuntimeError("; ".join(errors))

def diagnose_and_normalize(data):
    df=data.copy()
    df.index=pd.to_datetime(df.index).tz_localize(None).normalize()
    df=df.sort_index()
    repeated=int(df.index.duplicated().sum())
    if repeated:
        df=df.loc[~df.index.duplicated(keep="first")]
    for col in FIELDS:
        if col not in df:df[col]=np.nan if col in ("Open","High","Low","Close","Adj Close","Volume") else 0.0
    df=df[list(FIELDS)].copy()
    for col in FIELDS:df[col]=pd.to_numeric(df[col],errors="coerce")
    raw=df.copy()
    raw.index.name="date"
    base=df[["Open","High","Low","Close"]]
    complete=np.isfinite(base).all(axis=1)&(base>0).all(axis=1)
    valid_adj=np.isfinite(df["Adj Close"])&(df["Adj Close"]>0)
    valid_volume=np.isfinite(df["Volume"])&(df["Volume"]>=0)
    invalid=(~complete)|(~valid_adj)|(~valid_volume)
    hi=base[["Open","Close","Low"]].max(axis=1)>base["High"]+1e-8
    lo=base[["Open","Close","High"]].min(axis=1)<base["Low"]-1e-8
    invalid_envelope=(hi|lo)&complete
    ratio=(df["Adj Close"]/df["Close"]).where(complete&valid_adj)
    adjusted=base.mul(ratio,axis=0)
    adjusted["Volume"]=df["Volume"]
    adjusted=adjusted.loc[~invalid].copy()
    adjusted.index.name="date"
    log=np.log(df["Adj Close"].where(valid_adj)).diff()
    study=(df.index>=pd.Timestamp(STUDY_BEGIN))&(df.index<=pd.Timestamp(LAST_STUDY))
    zero=(df["Volume"]==0)&study
    flat=(base.max(axis=1)-base.min(axis=1)).abs()<1e-12
    study_mask=study&complete
    stale=0;current=0
    for z in df.loc[study,"Close"].dropna().to_numpy(float):
        if not np.isfinite(z):current=0
        elif z==stale:current+=1
        else:current=0
        stale=z
    metrics=dict(
       source_rows=len(df),source_first=str(df.index.min().date()),
       source_last=str(df.index.max().date()),
       source_pre2017_rows=int((df.index<pd.Timestamp("2017-02-01")).sum()),
       study_observed_bars=int(study.sum()),
       source_valid_price_rows=int(complete.sum()),
       adjusted_rows=int(len(adjusted)),
       source_duplicated_dates=repeated,
       source_invalid_price_or_adjustment=int(invalid.sum()),
       study_bad_ohlc_envelope=int((invalid_envelope&study).sum()),
       study_zero_volume=int(zero.sum()),
       study_flat_OHLC=int((flat&study_mask).sum()),
       study_abs_adjusted_ret_over_10pct=int((log.abs()>.10).loc[study].sum()),
       study_abs_adjusted_ret_over_25pct=int((log.abs()>.25).loc[study].sum()),
       study_missing_adjclose=int((~valid_adj&study).sum()),
       study_reaches_july2026=bool(df.index.max()>=pd.Timestamp(LAST_STUDY)),
       study_pre2017_252_bars=bool((df.index<pd.Timestamp("2017-02-01")).sum()>=252),
       study_common_2017_2026_eligible=bool(
          df.index.max()>=pd.Timestamp(LAST_STUDY) and
          (df.index<pd.Timestamp("2017-02-01")).sum()>=252))
    return raw,adjusted,metrics

def main(target):
    out=Path(target)
    out.mkdir(parents=True,exist_ok=False)
    (out/"raw_vendor").mkdir()
    (out/"adj_price").mkdir()
    catalog=pd.read_csv(Path(__file__).with_name("CATALOG.csv")).fillna("")
    assert len(catalog)==30 and catalog.ticker.is_unique
    assert catalog.ticker.str.endswith(".DE").all()
    metrics=[]
    for j,row in enumerate(catalog.itertuples(index=False),start=1):
        sym=row.ticker
        r=dict(ticker=sym,provider=row.provider,sector_11=row.sector_11,
               sector_name=row.sector_name,issuer_ISIN=row.isin_issuer_verified)
        try:
            history,md,warnings=one(sym)
            raw,adj,quality=diagnose_and_normalize(history)
            if len(raw)<100:
                raise AssertionError("Too few quote observations")
            f=out/"raw_vendor"/(sym+".csv")
            q=out/"adj_price"/(sym+".csv")
            raw.to_csv(f,float_format="%.16g",date_format="%Y-%m-%d")
            adj.to_csv(q,float_format="%.16g",date_format="%Y-%m-%d")
            currency=str(md.get("currency") or "").upper()
            md_ex=str(md.get("exchangeName") or md.get("exchange") or "")
            # Full vendor raw saved regardless of any fail below, never
            # suppress a proven currency mismatch.
            flag=("REJECT_CURRENCY" if currency not in ("","EUR") else
                  "REVIEW_CURRENCY_NOT_IN_YAHOO" if not currency else
                  "AVAILABLE_EUR")
            if len(adj)<100:flag="REJECT_DATA"
            r.update(status=flag,history_currency=currency,
              exchange_metadata=md_ex,
              yahoo_instrumentType=str(md.get("instrumentType") or ""),
              yahoo_shortName=str(md.get("shortName") or md.get("longName") or ""),
              quote_source_errors=";".join(warnings),
              raw_sha256=sha(f),adjusted_sha256=sha(q),**quality)
            print("EUROPE_SECTOR_YF",j,len(catalog),sym,flag,
                  quality["source_rows"],quality["source_first"],quality["source_last"],
                  "zero_volume",quality["study_zero_volume"],flush=True)
        except Exception as e:
            r.update(status="DOWNLOAD_FAILED",error=type(e).__name__+": "+str(e)[:300])
            print("EUROPE_SECTOR_YF_FAILED",sym,r["error"],flush=True)
        metrics.append(r)
        time.sleep(.16)
    pd.DataFrame(metrics).to_csv(out/"DOWNLOAD_AUDIT.csv",index=False)
    summary=dict(status="EUROPE_EQUITY_SECTOR_YFINANCE_ARCHIVE",
         total_proposed=len(catalog),sectors_requested=sorted(set(catalog.sector_11)),
         statuses=dict(Counter(x["status"] for x in metrics)),
         roster_first_fixed="2026-10-19",
         yahoo_start=START,yahoo_end_exclusive=END_EXCLUSIVE,
         study_cutoff=LAST_STUDY,
         source="Yahoo Finance through yfinance",
         version_yfinance=yf.__version__,
         source_catalog_sha256=sha(Path(__file__).with_name("CATALOG.csv")),
         requested_30=sorted(catalog.ticker.tolist()),
         successful_eur=sorted(r["ticker"] for r in metrics if r["status"]=="AVAILABLE_EUR"),
         available_but_unknown_currency=sorted(r["ticker"] for r in metrics if r["status"]=="REVIEW_CURRENCY_NOT_IN_YAHOO"),
         rejected_or_failed=sorted(r["ticker"] for r in metrics if r["status"] in ("REJECT_CURRENCY","REJECT_DATA","DOWNLOAD_FAILED")),
         timestamp_utc=str(pd.Timestamp.now(tz="UTC")),
         lineage=["Issuer catalog (iShares 2026 current, SPDR 2026 current)",
           "Yahoo archived vendor prices in raw_vendor; no OHLC envelope correction",
           "adj_price retro-adjusted using Yahoo as-of-download Adj Close/Close daily ratio",
           "No price zero-volume filter, no 25% cap, no cherry-picked 2017-2026 returns",
           "2026 survivor and euro stock metadata are NOT a historical PIT universe",
           "EUR price currency is verified when Yahoo get_history_metadata reports EUR",
           "Ticker classes classified as 11 approximate equity macro sector mappings; STOXX ICB differs from MSCI GICS",
           "Selected European ETF pricing venue is Xetra DE, not US domiciled ETFs",
           "No forecasts/backtests/prod changes in this operation"])
    (out/"DOWNLOAD_MANIFEST.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
       sha(p)+"  "+str(p.relative_to(out))+"\n"
       for p in sorted(out.rglob("*.csv")))+
       sha(out/"DOWNLOAD_MANIFEST.json")+"  DOWNLOAD_MANIFEST.json\n")
    print("EUROPE_EQUITY_SECTORS_DOWNLOAD_DONE "+json.dumps(summary),flush=True)
    # An incomplete universe is transparently archived and should NOT be
    # portrayed as a complete download. Workflow gets the manifest regardless.
    return summary

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    main(parser.parse_args().out)
