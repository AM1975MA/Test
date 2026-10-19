#!/usr/bin/env python3
"""Fetch FRESH unsanitized as-of-Oct2026 Yahoo venue histories for all original
60 Europe-only EUR ETF tickers; ISIN identity comes from official Xetra+issuers.

No old EU120 >25% daily-return rejection, no OHLC envelope rewriting, no
smoothing or filling gaps. Predecessor share class guard remains explicit.
Outputs raw OHLC + AdjClose, adjusted OHLC, asof vendor fingerprints and
quantified differences with previously pre-sanitized 2026 EU120 prices.
"""
from __future__ import annotations
import argparse,hashlib,json,math,collections
from pathlib import Path
import pandas as pd
import numpy as np
from europe_sector2026.download import one,diagnose_and_normalize,sha

ROOT=Path(__file__).resolve().parents[1]
ISIN_MAPPING=ROOT/"isin_first2026/results/ISIN_ALL_CANDIDATE_REFERENCE_MAPPING.csv"
ROSTER=ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv"
LEGACY=ROOT/"data/eu120/raw_ticker_csv"
ENDO=pd.Timestamp("2026-07-01")
BEGIN=pd.Timestamp("2017-02-01")

def sane_delta(new,old):
    both=new[["Open","High","Low","Close"]].join(
        old[["Open","High","Low","Close"]],lsuffix="_new",rsuffix="_old",how="inner")
    if len(both)==0:return {"n_shared":0}
    deltas={}
    for c in ("Open","High","Low","Close"):
        x=both[c+"_new"];y=both[c+"_old"]
        mask=(x>0)&(y>0)&np.isfinite(x)&np.isfinite(y)
        if not mask.any():continue
        r=(x[mask]/y[mask]-1).abs()
        deltas[c+"_changed_gt_0_01pct_days"]=int((r>.0001).sum())
        deltas[c+"_changed_gt_1pct_days"]=int((r>.01).sum())
        deltas[c+"_max_absolute_relative_change_pct"]=float(r.max()*100)
    deltas["n_shared"]=len(both)
    deltas["max_shared_close_relative_discrepancy_pct"]=float(
       abs(both.Close_new/both.Close_old-1).replace([np.inf,-np.inf],np.nan).max()*100)
    return deltas

def old_quotes(t):
    p=LEGACY/(t+".csv")
    if not p.exists():return None,""
    z=pd.read_csv(p)
    d=next((c for c in z if c.lower()=="date"),None)
    if d is None:return None,""
    z[d]=pd.to_datetime(z[d])
    z=z.set_index(d).sort_index()
    z.index=pd.DatetimeIndex(z.index).tz_localize(None).normalize()
    return z,sha(p)

def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for x in ("raw_vendor","adj_price"): (out/x).mkdir()
    ids=pd.read_csv(ISIN_MAPPING).fillna("")
    ids=ids[ids.in_original_EUR60.astype(str).str.lower()=="true"].copy()
    assert len(ids)==60 and ids.ticker.nunique()==60
    assert ids["isin"].str.len().eq(12).all()
    roster=pd.read_csv(ROSTER)
    assert set(ids.ticker)==set(roster.ticker)
    rows=[]
    for i,rec in enumerate(ids.itertuples(index=False),1):
        t=rec.ticker
        d=dict(ticker=t,isin=rec.isin,market=rec.market,
           old_source="EU120_2026_SANITIZED",reference=rec.status,
           class_inception=str(rec.share_class_inception),
           source_identity_url=str(rec.manual_isin_evidence_url))
        try:
            q,md,warnings=one(t)
            r,a,stat=diagnose_and_normalize(q)
            path=out/"raw_vendor"/(t+".csv")
            adjusted=out/"adj_price"/(t+".csv")
            r.to_csv(path,float_format="%.16g")
            a.to_csv(adjusted,float_format="%.16g")
            vendor_ccy=str(md.get("currency") or "").upper()
            valid_ccy=vendor_ccy=="EUR"
            if not valid_ccy:
                # Archive quote observations but explicitly quarantine from
                # EUR trading simulations if Yahoo exchange currency != EUR.
                status=("CURRENCY_UNKNOWN" if not vendor_ccy else "NON_EUR_VENDOR")
            else: status="EUR_VENDOR_CONFIRMED"
            old,oldhash=old_quotes(t)
            compare=sane_delta(a.loc[BEGIN:ENDO],old.loc[BEGIN:ENDO]) if old is not None else {}
            bad_class=bool(d["class_inception"] and
                   r.index.min()<pd.Timestamp(d["class_inception"]))
            d.update(status=status,yahoo_quote_currency=vendor_ccy,
                yahoo_short_name=str(md.get("shortName") or md.get("longName") or ""),
                yahoo_instrumentType=str(md.get("instrumentType") or ""),
                yahoo_exchange=str(md.get("exchangeName") or md.get("exchange") or ""),
                warning=";".join(warnings),
                sha256_fresh_raw=sha(path),sha256_fresh_adjusted=sha(adjusted),
                sha256_legacy_old=oldhash,
                historical_precurrent_shareclass_QUARANTINE=bad_class,
                old_vs_new_quoted_adjusted_OHLC=compare,
                **stat)
            print("EUR60_FRESH_UNSANITIZED",i,len(ids),t,rec.isin,status,
                  stat["source_rows"],stat["source_first"],stat["source_last"],
                  "zero",stat["study_zero_volume"],"env",stat["study_bad_ohlc_envelope"],
                  "old_fresh_change",compare.get("Close_changed_gt_0_01pct_days"),
                  flush=True)
        except Exception as ex:
            d.update(status="DOWNLOAD_FAILED",
                     error=type(ex).__name__+": "+str(ex)[:500])
            print("EUR60_FRESH_FAIL",i,t,d["error"],flush=True)
        rows.append(d)
    pd.DataFrame(rows).to_csv(out/"ALL_60_FRESH_RAW_PRICE_AND_OLD_SOURCE_DIFFERENCES.csv",index=False)
    success=[x for x in rows if x["status"]=="EUR_VENDOR_CONFIRMED"]
    diffs=sum(z.get("old_vs_new_quoted_adjusted_OHLC",{}).get(
        "Close_changed_gt_0_01pct_days",0) for z in success)
    hist_good=sum(z.get("study_common_2017_2026_eligible",False) for z in success)
    manifest=dict(status="EUR60_ISIN_MATCHED_FRESH_UNMODIFIED_YAHOO_VENUE_SOURCE",
      source="Yahoo via pinned yfinance 0.2.65, October 2026 fresh",
      source_ISIN_mapping_sha=sha(ISIN_MAPPING),
      source_roster_sha=sha(ROSTER),
      attempted_original60=60,
      downloaded_EUR_quote_tickers=len(success),
      quote_statuses=dict(collections.Counter(x["status"] for x in rows)),
      full_2017_to_july2026_with252_prior_bars=hist_good,
      ETF_ISIN_distinct=len(set(x["isin"] for x in rows)),
      same_ISIN_multiple_venues=60-len(set(x["isin"] for x in rows)),
      total_days_old_vs_new_Close_gt_0_01pct=diffs,
      preexisting_EU120_old_bars_were_sanitized=True,
      fresh_ohlc_has_NOT_been_repaired=True,
      raw_AdjClose_and_Dividends_preserved=True,
      current_2026_survivor_roster_not_asof2017=True,
      past_ETF_strategy_training_and_backtests_NOT_RERUN=True,
      historical_issuer_class_pre2018_quarantine=True,
      no_justETF_scraping=True,
      retrieved_utc=str(pd.Timestamp.now(tz="UTC")))
    (out/"RESULT.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
       sha(p)+"  "+str(p.relative_to(out))+"\n" for p in sorted(out.rglob("*.csv")))+
       sha(out/"RESULT.json")+"  RESULT.json\n")
    print("EUR60_ISIN_FRESH_RAW_SUCCESS "+json.dumps(manifest),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    main(p.parse_args().out)
