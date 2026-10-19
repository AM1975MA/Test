#!/usr/bin/env python3
"""ISIN -> issuer/public justETF listing -> actual Yahoo ticker OHLCV pilot.

No calls to justETF! Catalog frozen by human-reviewed public pages. Validate
XETRA identities against official live Xetra ISIN file, preserve all Yahoo
raw OHLC/dividend data; never infer venue executable prices from ISIN alone.
"""
import json,hashlib,collections,time,traceback
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf
from isin_first2026.build import download_xetra,check_isin
from europe_sector2026.download import diagnose_and_normalize,one,sha

HERE=Path(__file__).resolve().parent
WINDOW_START=pd.Timestamp("2017-02-01")
WINDOW_END=pd.Timestamp("2026-07-01")

def run(outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=False)
    (out/"yahoo_unmodified").mkdir()
    (out/"yahoo_adjusted").mkdir()
    candidates=pd.read_csv(HERE/"CATALOG.csv").fillna("")
    assert len(candidates)==16 and candidates.isin.nunique()==5
    assert candidates.yahoo_ticker.nunique()==len(candidates)
    assert candidates.isin.map(check_isin).all()
    official,master_meta=download_xetra()
    raw_rows=[];ys={}
    for i,r in enumerate(candidates.itertuples(index=False),start=1):
        ticker=r.yahoo_ticker;isin=r.isin
        suffix=ticker.split(".")[-1]
        xetra=[q for q in official.get(ticker[:-3],[])
               if q["Instrument Type"]=="ETF" and
                  q["MIC Code"]=="XETR" and q["Product Status"]=="Active"]
        ids=sorted({q["ISIN"] for q in xetra})
        ccy=sorted({q["Currency"] for q in xetra})
        status=("XETRA_2026_EXACT_ISIN" if ids==[isin] and ccy==["EUR"]
          else "XETRA_2026_WRONG_ISIN_REJECT" if ids and ids!=[isin]
          else "XETRA_2026_WRONG_CURRENCY_REJECT" if ids==[isin] and ccy!=["EUR"]
          else "JUSTETF_PUBLISHED_LISTING_NO_OFFICIAL_XETRA_MATCH" if suffix=="DE"
          else "NON_XETRA_JUSTETF_LISTING_PENDING_ISSUER_CROSSCHECK")
        info=dict(isin=isin,ticker=ticker,classification=r.underlying_geo,
            expected_fund=r.fund_name,
            listing_evidence=r.discovery_evidence,
            xetra_reference=status,xetra_reference_ids="|".join(ids),
            xetra_reference_currency="|".join(ccy),
            first_trading_date_xetra=xetra[0].get("First Trading Date","") if xetra else "")
        try:
            data,metadata,warnings=one(ticker)
            raw,adjusted,stats=diagnose_and_normalize(data)
            rawpath=out/"yahoo_unmodified"/(ticker+".csv")
            adjpath=out/"yahoo_adjusted"/(ticker+".csv")
            raw.to_csv(rawpath,float_format="%.16g")
            adjusted.to_csv(adjpath,float_format="%.16g")
            vendor_ccy=str(metadata.get("currency") or "").upper()
            n=int(stats["study_observed_bars"]);n=max(1,n)
            # For DE listings, require official ISIN equal requested;
            # for other venues, only public justETF evidence at this stage.
            identity_good=not(status.endswith("_REJECT") or (
                suffix=="DE" and not ids))
            full=bool(stats["study_common_2017_2026_eligible"])
            close_series=adjusted.loc[WINDOW_START:WINDOW_END,"Close"]
            observed_n=int(close_series.count())
            non_nan=pd.to_numeric(close_series,errors="coerce")
            ret=np.log(non_nan.where(non_nan>0)).diff()
            info.update(
              download_status="YAHOO_CURRENCY_EUR_AND_XETRA_IDENTITY_OK" if (
                 vendor_ccy=="EUR" and identity_good)
              else ("YAHOO_NON_EUR_QUOTE" if vendor_ccy!="EUR" else
                    "YAHOO_HISTORY_IDENTITY_UNPROVEN"),
              quote_currency_yahoo=vendor_ccy,
              instrumentType_yahoo=str(metadata.get("instrumentType","")),
              exchange_yahoo=str(metadata.get("exchangeName") or metadata.get("exchange") or ""),
              name_yahoo=str(metadata.get("shortName") or metadata.get("longName") or ""),
              history_warning=";".join(warnings),
              current_ISIN_reference_confirmed=bool(status=="XETRA_2026_EXACT_ISIN"),
              history_pre2017_warmup_252=stats["study_pre2017_252_bars"],
              history_through_2026_07_01=stats["study_reaches_july2026"],
              full_2017_2026_with_prior_warmup=full,
              study_adjusted_close_count=observed_n,
              yahoo_zero_volume_fraction=float(stats["study_zero_volume"])/n,
              yahoo_flat_bar_fraction=float(stats["study_flat_OHLC"])/n,
              yahoo_bad_ohlc_envelope=stats["study_bad_ohlc_envelope"],
              study_log_return_volatility=float(ret.std()),
              source_first=stats["source_first"],source_last=stats["source_last"],
              source_bars=stats["source_rows"],study_observed_bars=stats["study_observed_bars"],
              raw_sha256=sha(rawpath),adj_sha256=sha(adjpath))
            # Eligibility is a QUOTE DIAGNOSTIC, not verified 2017
            # investibility and no future performance selection.
            info["historical_quote_quality_flag"]=(
              "REJECT_IDENTITY_OR_CURRENCY" if
                info["download_status"]!="YAHOO_CURRENCY_EUR_AND_XETRA_IDENTITY_OK" else
              "NOT_FULL_HISTORICAL_COVERAGE" if not full else
              "A_LOW_ZERO_VENDOR_VOLUME" if info["yahoo_zero_volume_fraction"]<=.02
                       and info["yahoo_flat_bar_fraction"]<=.03 else
              "B_MODERATE_MISSING_VOLUME" if info["yahoo_zero_volume_fraction"]<=.10
                       and info["yahoo_flat_bar_fraction"]<=.12 else
              "C_SPARSE_OR_STALE_YAHOO")
            ys[ticker]=adjusted
            print("ISIN_YFINANCE",i,isin,ticker,
                  info["download_status"],info["historical_quote_quality_flag"],
                  info["source_first"],info["source_last"],
                  "zero%",round(info["yahoo_zero_volume_fraction"]*100,2),
                  flush=True)
        except Exception as exc:
            info.update(download_status="YFINANCE_DOWNLOAD_FAILED",
                error=type(exc).__name__+": "+str(exc)[:300])
            print("ISIN_YFINANCE_FAILED",isin,ticker,info["error"],flush=True)
        raw_rows.append(info)
        time.sleep(.12)
    audit=pd.DataFrame(raw_rows)
    audit.to_csv(out/"TICKER_BY_ISIN_CURRENCY_HISTORY_QUALITY.csv",index=False)
    # Multiple venue returns, strictly same fund ISIN but independent exchange
    # Yahoo snapshots are NOT independent raw market data vendors.
    pairs=[]
    for isin, group in candidates.groupby("isin"):
        syms=[v for v in group.yahoo_ticker if v in ys]
        for ai,a in enumerate(syms):
            for b in syms[ai+1:]:
                t=pd.DataFrame({"a":ys[a].Close,"b":ys[b].Close}).loc[
                    WINDOW_START:WINDOW_END].dropna()
                if len(t)<90:continue
                d=np.log(t).diff().dropna()
                err=(d.a-d.b).abs()
                pairs.append(dict(isin=isin,venue1=a,venue2=b,n_common=len(t),
                    daily_close_return_corr=float(d.a.corr(d.b)),
                    median_absolute_log_return_gap_bps=float(err.median()*1e4),
                    p95_absolute_log_return_gap_bps=float(err.quantile(.95)*1e4),
                    pct_days_abs_return_gap_gt1pct=float((err>.01).mean()*100),
                    pct_days_abs_return_gap_gt2pct=float((err>.02).mean()*100)))
    pd.DataFrame(pairs,columns=["isin","venue1","venue2","n_common",
       "daily_close_return_corr","median_absolute_log_return_gap_bps",
       "p95_absolute_log_return_gap_bps","pct_days_abs_return_gap_gt1pct",
       "pct_days_abs_return_gap_gt2pct"]).to_csv(
         out/"SAME_ISIN_DIFFERENT_VENUES_QUOTE_CONSISTENCY.csv",index=False)
    # one quality candidate per ISIN, however none is automatically moved to
    # old EUR60 or endorsed for live trading.
    chosen=audit[audit.download_status=="YAHOO_CURRENCY_EUR_AND_XETRA_IDENTITY_OK"].copy()
    rank={"A_LOW_ZERO_VENDOR_VOLUME":0,"B_MODERATE_MISSING_VOLUME":1,
          "C_SPARSE_OR_STALE_YAHOO":2,"NOT_FULL_HISTORICAL_COVERAGE":3}
    chosen["rank"]=chosen.historical_quote_quality_flag.map(rank).fillna(4)
    chosen["official_rank"]=(~chosen.current_ISIN_reference_confirmed.astype(bool)).astype(int)
    chosen=chosen.sort_values(["isin","rank","official_rank","yahoo_zero_volume_fraction",
                               "ticker"],kind="mergesort").drop_duplicates("isin")
    chosen.drop(columns=["rank","official_rank"]).to_csv(
        out/"ONE_BEST_VENDOR_QUOTE_PER_ISIN_RESEARCH_ONLY.csv",index=False)
    outinfo=dict(status="JUSTETF_HUMAN_PUBLIC_ISIN_TO_YFINANCE_PILOT_COMPLETE",
       source_discovery="Public search-accessible justETF ETF profiles and listing tables ONLY",
       no_automated_justETF_scraping=True,source_xetra=master_meta,
       isin_examples=candidates.isin.nunique(),ticker_candidates=len(candidates),
       isins_europe_only=sorted(candidates.loc[
           candidates.underlying_geo=="EUROPE_ONLY","isin"].unique().tolist()),
       isins_global_excluded=sorted(candidates.loc[
           candidates.underlying_geo=="GLOBAL_EXCLUDE","isin"].unique().tolist()),
       source_yfinance_version=yf.__version__,
       downloaded_vendor_EUR=(audit.download_status=="YAHOO_CURRENCY_EUR_AND_XETRA_IDENTITY_OK").sum().item(),
       download_failures=(audit.download_status=="YFINANCE_DOWNLOAD_FAILED").sum().item(),
       source_quote_grades=dict(collections.Counter(audit.historical_quote_quality_flag.fillna("FAILED"))),
       full_2017_2026_euro_venue_quote_tickers=int(((audit.full_2017_2026_with_prior_warmup.astype(str).str.lower()=="true")&
                  (audit.download_status=="YAHOO_CURRENCY_EUR_AND_XETRA_IDENTITY_OK")).sum()),
       one_per_isin_usable_vendor_quote_candidates=len(chosen),
       daily_same_isin_venue_crosscheck_count=len(pairs),
       original_ETF_TRADER_and_EUR60_unmodified=True,
       no_true_historical_point_in_time_universe_claim=True,
       no_Nav_or_Xetra_executable_price_from_justETF_claim=True,
       asof_utc=str(pd.Timestamp.now(tz="UTC")))
    (out/"RESULT.json").write_text(json.dumps(outinfo,indent=2,default=str)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
          sha(p)+"  "+str(p.relative_to(out))+"\n"
          for p in sorted(out.rglob("*.csv")))+
          sha(out/"RESULT.json")+"  RESULT.json\n")
    print("ISIN_YFINANCE_PILOT_DONE",json.dumps(outinfo,default=str),flush=True)

if __name__=="__main__":
    import argparse
    q=argparse.ArgumentParser()
    q.add_argument("--out",required=True)
    run(q.parse_args().out)
