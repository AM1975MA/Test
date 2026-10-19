#!/usr/bin/env python3
"""Direct Yahoo snapshots for 21 alternative Europe-only sector UCITS listings.

No performance-optimization, no return clipping, no pretending Yahoo volume
defines bid-ask execution quality. Existing EUR60 and original 30 untouched.
"""
from __future__ import annotations
import argparse, json, time, hashlib
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf
from europe_sector2026.download import (
    START, END_EXCLUSIVE,LAST_STUDY, diagnose_and_normalize, one, sha
)

OLD_DIR=Path("europe_sector2026/results")
CAT=Path(__file__).with_name("CATALOG.csv")

def grade(rec):
    if rec["status"]!="AVAILABLE_EUR":return "REJECT_OR_NOT_VERIFIED"
    if not rec.get("study_pre2017_252_bars",False) or not rec.get("study_reaches_july2026",False):
        return "LATE_OR_INCOMPLETE_FOR_2017_BACKTEST"
    n=max(1,int(rec["study_observed_bars"]))
    volume=float(rec["study_zero_volume"])/n
    flat=float(rec["study_flat_OHLC"])/n
    if volume<=.02 and flat<=.03:return "QUOTE_PROFILE_A"
    if volume<=.10 and flat<=.12:return "QUOTE_PROFILE_B"
    return "HIGH_YAHOO_VOLUME_OR_FLAT_BAR_RISK"

def calculate_vendor_sector_comparison(alt,old):
    existing=old.loc[old.sector_11==alt["sector"]]
    if len(existing)==0:return dict(reference_count=0)
    n=max(1,int(alt.get("study_observed_bars") or 0))
    z=float(alt.get("study_zero_volume") or 0)/n
    b=existing.assign(zero_fraction=pd.to_numeric(existing.study_zero_volume)/
                   pd.to_numeric(existing.study_observed_bars).clip(lower=1),
                    flat_fraction=pd.to_numeric(existing.study_flat_OHLC)/
                   pd.to_numeric(existing.study_observed_bars).clip(lower=1))
    best=b.sort_values(["zero_fraction","flat_fraction"],kind="stable").iloc[0]
    return dict(reference_count=len(b),
       best_prior_30_ticker=str(best.ticker),
       best_prior_30_yahoo_zero_volume_fraction=float(best.zero_fraction),
       alt_yahoo_zero_volume_fraction=float(z),
       difference_vs_prior_lowest_zero_pctpoints=
           float(100*(z-float(best.zero_fraction))),
       best_prior_30_flat_fraction=float(best.flat_fraction),
       alt_flat_fraction=float(alt.get("study_flat_OHLC",0)/n))

def main(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    for k in ("raw_vendor","adj_price"): (out/k).mkdir()
    catalog=pd.read_csv(CAT).fillna("")
    assert len(catalog)==21 and catalog.ticker.nunique()==21
    assert catalog.ticker.str.endswith(".DE").all()
    old=pd.read_csv(OLD_DIR/"DOWNLOAD_AUDIT.csv")
    rows=[]
    for j,candidate in enumerate(catalog.itertuples(index=False),1):
        t=candidate.ticker
        record=dict(ticker=t,issuer=candidate.issuer,
           sector=candidate.sector,index_name=candidate.index_name,
           issuer_ISIN=candidate.isin,
           index_family=candidate.index_family)
        try:
            raw,metadata,warnings=one(t)
            vendor,adjusted,m=diagnose_and_normalize(raw)
            vendor_path=out/"raw_vendor"/(t+".csv")
            adjusted_path=out/"adj_price"/(t+".csv")
            vendor.to_csv(vendor_path,float_format="%.16g")
            adjusted.to_csv(adjusted_path,float_format="%.16g")
            currency=str(metadata.get("currency") or "").upper()
            instrument_type=str(metadata.get("instrumentType") or "")
            long_name=str(metadata.get("shortName") or metadata.get("longName") or "")
            exchange=str(metadata.get("exchangeName") or metadata.get("exchange") or "")
            status="AVAILABLE_EUR" if currency=="EUR" else ("UNKNOWN_CURRENCY" if not currency
                   else "WRONG_CURRENCY")
            record.update(m)
            record.update(status=status,history_currency=currency,
               yahoo_instrumentType=instrument_type,shortName=long_name,
               exchangeName=exchange,history_warnings=";".join(warnings),
               raw_sha256=sha(vendor_path),adjusted_sha256=sha(adjusted_path))
            record["quote_profile"]=grade(record)
            print("ALTERNATIVE_EU_SECTOR",j,t,currency,record["quote_profile"],
                  m["source_rows"],m["source_first"],m["source_last"],
                  "zero",m["study_zero_volume"],"flat",m["study_flat_OHLC"],
                  flush=True)
        except Exception as e:
            record.update(status="DOWNLOAD_FAILED",
                error=type(e).__name__+": "+str(e)[:400],
                quote_profile="REJECT_OR_NOT_VERIFIED")
            print("ALTERNATIVE_EU_SECTOR_FAILED",j,t,record["error"],flush=True)
        record.update(calculate_vendor_sector_comparison(record,old)
                      if record["status"]!="DOWNLOAD_FAILED"
                      else dict(reference_count=0))
        rows.append(record)
        time.sleep(.2)
    df=pd.DataFrame(rows)
    df.to_csv(out/"ALTERNATIVES_QUALITY_AND_BASELINE_COMPARISON.csv",index=False)
    success=df.loc[df.status=="AVAILABLE_EUR"]
    shortlist=df.loc[(df.quote_profile=="QUOTE_PROFILE_A") &
                     (df.status=="AVAILABLE_EUR")]
    summary=dict(status="EUROPE_UCITS_SECTOR_ALTERNATIVES_YAHOO_RETRIEVED",
      source="Yahoo/yfinance downloaded direct vs issuer and independent exchange",
      yfinance_version=yf.__version__,
      roster_proposed=len(df),issuer_split=dict(Counter(df.issuer)),
      source_catalog_sha256=sha(CAT),
      xetra_eur_success=len(success),
      source_statuses=dict(Counter(df.status)),
      quote_profile_counts=dict(Counter(df.quote_profile)),
      high_confidence_quote_A=shortlist.ticker.tolist(),
      historical_2017_2026_full_coverage=int(
        (df.study_pre2017_252_bars.astype(str).str.lower()=="true").where(
            df.status=="AVAILABLE_EUR",False).sum() &
        (df.study_reaches_july2026.astype(str).str.lower()=="true").where(
            df.status=="AVAILABLE_EUR",False).sum()
      ) if False else int(
        ((df.study_pre2017_252_bars.astype(str).str.lower()=="true") &
         (df.study_reaches_july2026.astype(str).str.lower()=="true") &
         (df.status=="AVAILABLE_EUR")).sum()),
      alternative_exchange_and_quote_data_not_same_as_live_executable_spread=True,
      official_index_families_not_interchangeable=True,
      had_missing_ISIN_identifiers=sorted(df.loc[df.issuer_ISIN=="UNKNOWN","ticker"].tolist()),
      additional_yahoo_volume_audits_have_unknown_reporting_completeness=True,
      date_fetched_utc=str(pd.Timestamp.now(tz="UTC")),
      original_30_download_sha=sha(OLD_DIR/"DOWNLOAD_MANIFEST.json"),
      data_source_sha_canonical=True,
      impact_scope="No trade, no ETF Trader model or portfolio changes")
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
       sha(p)+"  "+str(p.relative_to(out))+"\n"
       for p in sorted(out.rglob("*.csv")))+
       sha(out/"RESULT.json")+"  RESULT.json\n")
    print("ALTERNATIVES_FINAL",json.dumps(summary),flush=True)
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    main(p.parse_args().out)
