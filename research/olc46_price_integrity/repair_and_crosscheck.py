#!/usr/bin/env python3
"""OLC46-D1: conservative market-data correction and independent cross-venue checks.

Never fabricate High/Low. For bars failing O/H/L/C integrity, retain observed
Open/Close (subject to independent checks) and set High/Low to NaN, plus an
explicit status. Intraday risk execution is BLOCKED on instruments with any
unresolved historical bad bars. This is NOT a full-native OLC19 backtest.

Source: Yahoo Finance (raw, repair=False; diagnostic repair=True), optional
Stooq independently sourced same-venue price feed (diagnostic only); peer
venues identified from issuer listings but NOT assumed identical intra-day.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib, io, json, math, traceback
import numpy as np
import pandas as pd
import requests
import yfinance as yf

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"
OUT.mkdir(parents=True,exist_ok=True)
START="2017-01-01"
END="2026-07-05"
PRODUCTS={
 "PHAG.MI":{
   "isin":"JE00B1VS3333","market":"MILAN","currency":"EUR","legal_form":"ETC",
   "peers":["PHAG.AS","PHAG.L","PHSP.L"],
   "same_currency":["PHAG.AS"],
   "stooq":["phag.it","phag.mi"],
   "issuer":"https://www.wisdomtree.com/it/products/commodities/wisdomtree-physical-silver"},
 "NGAS.MI":{
   "isin":"JE00BN7KB334","market":"MILAN","currency":"EUR","legal_form":"ETC",
   "peers":["NGAS.PA","OD7L.DE","NGAS.L"],
   "same_currency":["NGAS.PA","OD7L.DE"],
   "stooq":["ngas.it","ngas.mi"],
   "issuer":"https://www.wisdomtree.com/it/products/commodities/wisdomtree-natural-gas"},
 "CMOD.MI":{
   "isin":"IE00BD6FTQ80","market":"MILAN","currency":"EUR","legal_form":"ETF_UCITS",
   "peers":["CMOD.L","CMOD.AS","CMOD.DE"],
   "same_currency":["CMOD.AS","CMOD.DE"],
   "stooq":["cmod.it","cmod.mi"],
   "issuer":"https://www.borsaitaliana.it/borsa/etf/scheda/IE00BD6FTQ80-ETFP.html"},
}
# Historically VZLC.DE was *incorrectly* treated as the same ISIN as PHAG.MI.
# A 2022 issuer factsheet lists DE000A0N62F2 for VZLC.DE. Do not merge.
IDENTITY_ALERTS=[{"ticker":"VZLC.DE","previously_assigned_isin":"JE00B1VS3333",
                  "historical_issuer_factsheet_isin":"DE000A0N62F2",
                  "decision":"NO_AUTOMATIC_ISIN_EQUIVALENCE"}]

def yf_quotes(ticker:str,repair:bool=False)->pd.DataFrame:
    # .history avoids some downloader global state; Yahoo may be unavailable.
    h=yf.Ticker(ticker).history(start=START,end=END,auto_adjust=False,
                                repair=repair,actions=False,interval="1d")
    if h is None or h.empty:raise ValueError("NO_YAHOO_HISTORY")
    if isinstance(h.columns,pd.MultiIndex):
        h.columns=h.columns.get_level_values(0)
    h.columns=[str(v).lower().replace(" ","_") for v in h.columns]
    ts=pd.DatetimeIndex(h.index)
    if ts.tz is not None:ts=ts.tz_localize(None)
    h.index=ts.normalize()
    if h.index.duplicated().any():raise ValueError("DUPLICATE_INDEX")
    for field in ["open","high","low","close"]:
        h[field]=pd.to_numeric(h[field],errors="coerce")
    if "adj_close" not in h.columns:h["adj_close"]=h["close"]
    if "volume" not in h.columns:h["volume"]=np.nan
    return h.sort_index()

def invariant(h:pd.DataFrame):
    val=h[["open","high","low","close"]]
    valid_price=np.isfinite(val).all(axis=1)&(val>0).all(axis=1)
    low_above_high=h.low>h.high
    open_below_low=h.open<h.low
    close_below_low=h.close<h.low
    open_above_high=h.open>h.high
    close_above_high=h.close>h.high
    reasons=pd.DataFrame({"nonpositive_or_missing":~valid_price,
             "low_above_high":low_above_high,
             "open_below_low":open_below_low,
             "close_below_low":close_below_low,
             "open_above_high":open_above_high,
             "close_above_high":close_above_high},index=h.index).fillna(False)
    bad=reasons.any(axis=1)
    # Severity: distance by which Open/Close lies outside the stated range,
    # measured in basis points relative to its own price.
    hi=np.maximum(h.open,h.close)
    lo=np.minimum(h.open,h.close)
    out_hi=np.maximum(0,hi-h.high)/hi*1e4
    out_lo=np.maximum(0,h.low-lo)/lo*1e4
    severity=np.maximum(out_hi,out_lo)
    return bad,reasons,severity

def stooq_quotes(code):
    url="https://stooq.com/q/d/l/"
    r=requests.get(url,params={"s":code,"i":"d","d1":"20170101",
                                "d2":"20260704"},timeout=20,
                   headers={"User-Agent":"Mozilla/5.0 OLC46 historical data audit"})
    if r.status_code!=200 or not r.text.strip().startswith("Date,"):
        raise ValueError(f"STOOQ_UNAVAILABLE_http{r.status_code}_body{r.text[:70]!r}")
    df=pd.read_csv(io.StringIO(r.text),parse_dates=["Date"])
    if len(df)<200:raise ValueError("STOOQ_TOO_SHORT")
    df=df.rename(columns=str.lower).set_index("date")
    if not {"open","high","low","close"}.issubset(df.columns):
        raise ValueError("STOOQ_COLUMNS_MISSING")
    df.index=pd.DatetimeIndex(df.index).normalize()
    if df.index.duplicated().any():raise ValueError("STOOQ_DUPLICATE")
    return df.sort_index()

def provider_comparison(main,alt,source, ticker):
    common=main.index.intersection(alt.index)
    if len(common)<50:return {"primary":ticker,"other":source,"status":"TOO_FEW_MATCHES",
                              "n_match":len(common)}
    a=main.loc[common];b=alt.loc[common]
    valid=(a.close>0)&(b.close>0)&np.isfinite(a.close)&np.isfinite(b.close)
    a=a.loc[valid];b=b.loc[valid]
    if len(a)<50:return {"primary":ticker,"other":source,"status":"NO_VALID_PAIRS",
                         "n_match":len(a)}
    delta=np.abs(np.log(b.close/a.close))
    # Different venue, same ISIN, currency does not imply identical high/low!
    return {"primary":ticker,"other":source,"status":"COMPARE_ONLY",
            "n_match":len(a),"median_abs_close_gap_pct":float(np.median(delta)*100),
            "p95_abs_close_gap_pct":float(np.quantile(delta,.95)*100),
            "raw_log_close_return_corr":float(np.corrcoef(np.log(a.close).diff().dropna(),
                              np.log(b.close).diff().dropna())[0,1]),
            "other_invalid_ohlc":int(invariant(b)[0].sum()),
            "first_match":str(common.min().date()),
            "last_match":str(common.max().date())}

def main():
    qsummary=[];cross=[];bad_detail=[];raw_manifest={}
    for ticker,p in PRODUCTS.items():
        h=yf_quotes(ticker,repair=False)
        raw_bad,reasons,severity=invariant(h)
        raw_manifest[ticker]={"raw_n":len(h),
                              "raw_first":str(h.index.min().date()),
                              "raw_last":str(h.index.max().date())}
        # Try Yahoo's built-in repair only for diagnosis. It is *not*
        # independent evidence, so it is NEVER silently substituted.
        try:
            repaired=yf_quotes(ticker,repair=True)
            c=h.index.intersection(repaired.index)
            fixed_bad,_reason,_sev=invariant(repaired.loc[c])
            fixed_on_bad=int((raw_bad.loc[c] & ~fixed_bad).sum())
            status="download_ok"
            raw_manifest[ticker].update({"yahoo_repair_status":status,
                                         "yahoo_repair_resolved":fixed_on_bad,
                                         "repaired_n":len(repaired)})
        except Exception as e:
            fixed_on_bad=0
            raw_manifest[ticker]["yahoo_repair_status"]=repr(e)
        qsummary.append({"ticker":ticker,"isin":p["isin"],"venue":p["market"],
              "currency":p["currency"],"n":len(h),
              "original_invalid_bars":int(raw_bad.sum()),
              "invalid_pct":float(raw_bad.mean()*100),
              "yahoo_repair_fixed_unverified":fixed_on_bad,
              "p50_severity_bp":float(np.nanmedian(severity.loc[raw_bad])) if raw_bad.any() else 0,
              "p95_severity_bp":float(np.nanquantile(severity.loc[raw_bad],.95)) if raw_bad.any() else 0,
              "max_severity_bp":float(np.nanmax(severity.loc[raw_bad])) if raw_bad.any() else 0,
              "intraday_status":"NOT_CERTIFIED_ON_BAD_DAYS"})
        for t in h.index[raw_bad]:
            vals=h.loc[t]
            reasons_here=[k for k,v in reasons.loc[t].items() if bool(v)]
            bad_detail.append({"ticker":ticker,"date":str(t.date()),
                 "raw_open":float(vals.open),"raw_high":float(vals.high),
                 "raw_low":float(vals.low),"raw_close":float(vals.close),
                 "severity_bp":float(severity.loc[t]),
                 "reasons":";".join(reasons_here),
                 "repair_action":"HL_SET_MISSING_NO_FABRICATION"})
        # Correct the analytical dataset: never promote an impossible bar.
        out=pd.DataFrame(index=h.index)
        out["date"]=h.index.strftime("%Y-%m-%d")
        out["open"]=h.open
        out["high"]=h.high.where(~raw_bad,np.nan)
        out["low"]=h.low.where(~raw_bad,np.nan)
        out["close"]=h.close
        out["volume"]=h.volume
        out["ohlc_status"]=np.where(raw_bad,"HL_MISSING_SOURCE_INCONSISTENT","RAW_OHLC_VALID")
        out["high_low_confirmed"]=False  # no independent same-venue confirmation
        out["bar_ohlc_internally_consistent"]=~raw_bad
        # No instrument-level backtest with intraday stops until independently
        # validated for EVERY needed future session. Never look ahead to skip
        # only the days that were later found corrupted.
        out["instrument_intraday_backtest_eligible"]=False
        out["refit_native_model_eligible_O_C"]=np.isfinite(h.open)&np.isfinite(h.close)&(h.open>0)&(h.close>0)
        # repair performed = reject invalid H/L, not inferred replacement values.
        dest=OUT/(ticker.replace(".","_")+"_quality_masked.csv.gz")
        # Integrity and no fabricated High/Low are mandatory invariants.
        assert out.loc[raw_bad,["high","low"]].isna().all().all()
        assert np.allclose(out.open.to_numpy(),h.open.to_numpy(),equal_nan=True)
        assert np.allclose(out.close.to_numpy(),h.close.to_numpy(),equal_nan=True)
        assert not out.instrument_intraday_backtest_eligible.any()
        out.to_csv(dest,index=False,compression="gzip")
        raw_manifest[ticker]["corrected_sha256"]=hashlib.sha256(dest.read_bytes()).hexdigest()
        raw_manifest[ticker]["missing_intraday_hl"]=int(out.high.isna().sum())
        for peer in p["peers"]:
            try:
                alt=yf_quotes(peer,False)
                v=provider_comparison(h,alt,f"YAHOO_CROSS_VENUE_{peer}",ticker)
                v["same_currency"]=peer in p["same_currency"]
                v["identity_status"]="issuer_confirmed_same_isin" if peer!="CMOD.DE" else "unverified"
                cross.append(v)
            except Exception as e:
                cross.append({"primary":ticker,"other":peer,
                              "status":"PEER_NOT_AVAILABLE","error":repr(e)})
        for code in p["stooq"]:
            try:
                v=provider_comparison(h,stooq_quotes(code),f"STOOQ_{code}",ticker)
                v["same_currency"]=True
                v["identity_status"]="symbol_mapping_requires_issuer_check"
                cross.append(v)
            except Exception as e:
                cross.append({"primary":ticker,"other":"STOOQ_"+code,
                              "status":"PROVIDER_NOT_AVAILABLE","error":repr(e)})
    pd.DataFrame(qsummary).to_csv(OUT/"quality_summary.csv",index=False)
    pd.DataFrame(cross).to_csv(OUT/"cross_venue_provider_diagnostic.csv",index=False)
    pd.DataFrame(bad_detail).to_csv(OUT/"bad_bar_audit.csv",index=False)
    pd.DataFrame(IDENTITY_ALERTS).to_csv(OUT/"identity_corrections.csv",index=False)
    raw_manifest["generated_at"]=datetime.now(timezone.utc).isoformat()
    raw_manifest["period"]={"start":START,"end_exclusive":END}
    raw_manifest["raw_source"]="Yahoo historical no auto-adjust no repair"
    raw_manifest["same_venue_external_source_required_to_rebuild_true_HL"]=True
    raw_manifest["intraday_stop_policy"]="block risky ETC until validated; do not use H/L missing days for stop backtests"
    raw_manifest["repair_definition"]="invalid High/Low converted to NaN, O/C retained as unverified Yahoo observations"
    raw_manifest["no_lookahead_oracle_in_repairs"]=True
    (OUT/"manifest.json").write_text(json.dumps(raw_manifest,indent=2))
    print("=== Quality of primary data ===")
    print(pd.DataFrame(qsummary).to_string(index=False),flush=True)
    print("=== Cross-venue and independent source availability ===")
    print(pd.DataFrame(cross).to_string(index=False),flush=True)
    assert all(x["original_invalid_bars"]>0 for x in qsummary)
    print("SUCCESS: bad High/Low isolated and masked; no fabricated OHLC.",flush=True)

if __name__=="__main__":main()
