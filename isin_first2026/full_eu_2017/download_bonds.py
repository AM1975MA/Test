#!/usr/bin/env python3
"""Acquire 16 issuer-certified Euro sovereign and EUR-credit market tickers.

EUR corporate issuers can be non-European. Keep in external/mixed credit pool,
not in the strictly geographic Europe-only core.
"""
from __future__ import annotations
import argparse,json,collections
from pathlib import Path
import pandas as pd
from isin_first2026.build import download_xetra,check_isin
from europe_sector2026.download import one,diagnose_and_normalize,sha
HERE=Path(__file__).resolve().parent

def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    (out/"vendor_original").mkdir();(out/"vendor_adjusted").mkdir()
    names=pd.read_csv(HERE/"BOND_ISIN_CANDIDATES.csv").fillna("")
    assert len(names)==16 and names["isin"].nunique()==7
    assert names["isin"].map(check_isin).all()
    off,ref=download_xetra()
    result=[]
    for i,c in enumerate(names.itertuples(index=False),1):
        r=dict(ticker=c.ticker,isin=c.isin,underlying_scope=c.underlying_scope,
           segment=c.segment,issuer_url=c.issuer_url,issuer_description=c.description)
        suffix=c.ticker.split(".")[-1]
        # IBEI.DE is Bloomberg/Reuters quote alias to officially Xetra IBCI.
        requested=(c.ticker[:-3] if suffix=="DE" else "")
        official_alias="IBCI" if c.ticker=="IBEI.DE" else requested
        matching=[p for p in off.get(official_alias,[]) if
                  p.get("Instrument Type")=="ETF" and p.get("MIC Code")=="XETR" and
                  p.get("Product Status")=="Active"]
        official_isin=sorted({p["ISIN"] for p in matching})
        currency=sorted({p["Currency"] for p in matching})
        official_ok=official_isin==[c.isin] and currency==["EUR"]
        r.update(reference_name=official_alias,reference_xetra_isin="|".join(official_isin),
           reference_xetra_currency="|".join(currency),
           official_Xetra_isin_confirmed=official_ok,
           reference_status="XETRA_2026_EXACT" if official_ok else
             "XETRA_IDENTITY_CONFLICT_REJECT" if official_isin else
             "NON_XETRA_ISSUER_LISTING_UNCONFIRMED")
        try:
            vendor,md,w=one(c.ticker)
            raw,adj,quality=diagnose_and_normalize(vendor)
            path1=out/"vendor_original"/(c.ticker+".csv")
            path2=out/"vendor_adjusted"/(c.ticker+".csv")
            raw.to_csv(path1,float_format="%.16g")
            adj.to_csv(path2,float_format="%.16g")
            yccy=str(md.get("currency") or "").upper()
            typ=str(md.get("instrumentType") or "").upper()
            valid_currency=yccy=="EUR"
            bad_xetra=(suffix=="DE" and not official_ok)
            status=("REJECT_NON_EUR_OR_NOT_ETF" if not valid_currency or typ!="ETF"
                 else "REJECT_XETRA_IDENTITY" if bad_xetra
                 else "EUR_OFFICIAL_ISIN_VERIFIED" if official_ok
                 else "EUR_ISSUER_NONXETRA_LISTING")
            n=max(1,quality["study_observed_bars"])
            r.update(download_status=status,yahoo_currency=yccy,
              yahoo_exchange=str(md.get("exchangeName") or md.get("exchange") or ""),
              yahoo_name=str(md.get("shortName") or md.get("longName") or ""),
              raw_sha256=sha(path1),adjusted_sha256=sha(path2),
              zero_volume_pct=100*quality["study_zero_volume"]/n,
              flat_ohlc_pct=100*quality["study_flat_OHLC"]/n,**quality)
            print("ISIN_BOND_YAHOO",i,c.ticker,c.isin,status,
                  quality["source_first"],quality["source_last"],
                  "volume0",quality["study_zero_volume"],flush=True)
        except Exception as e:
            r.update(download_status="DOWNLOAD_FAILED",error=type(e).__name__+": "+str(e)[:350])
            print("ISIN_BOND_FAIL",c.ticker,r["error"],flush=True)
        result.append(r)
    pd.DataFrame(result).to_csv(out/"BOND_ISIN_QUOTE_AUDIT.csv",index=False)
    meta=dict(source="Issuer identities + Xetra Oct2026 reference + yfinance",
       attempted=len(result),distinct_isins=names["isin"].nunique(),
       statuses=dict(collections.Counter(x["download_status"] for x in result)),
       original_full_year_2016_or_earlier=sum(x.get("source_first","9999")<"2016-01-01"
           for x in result),
       historic_2017_full_with_252_warmup=sum(
          x.get("study_common_2017_2026_eligible",False) and x["download_status"] in
          ("EUR_OFFICIAL_ISIN_VERIFIED","EUR_ISSUER_NONXETRA_LISTING") for x in result),
       no_justetf_scraping=True,no_promotion_EURO_CREDIT_MIXED_ISSUERS_to_strict_EU=True,
       no_fund_performance_ranking=True,
       download_utc=str(pd.Timestamp.now(tz="UTC")),
       issuer_catalog_hash=sha(HERE/"BOND_ISIN_CANDIDATES.csv"),
       official_ref=ref)
    (out/"RESULT.json").write_text(json.dumps(meta,indent=2)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
        sha(p)+"  "+str(p.relative_to(out))+"\n"
        for p in sorted(out.rglob("*.csv")))+
        sha(out/"RESULT.json")+"  RESULT.json\n")
    print("EUROPE_BOND_DONORS_DONE",json.dumps(meta),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    main(p.parse_args().out)
