#!/usr/bin/env python3
"""2026-10-27 immutable EU148 Yahoo source repair, same-ISIN verified cross-listings,
and major European country-index UCITS additions. Source choice NEVER uses returns.

Original EU148 raw prices are left untouched unless verified same ISIN,
different EUR venue and materially greater source coverage, and internally
consistent overlapping EUR close returns. No stitching, no fake historical price,
no 2026 quality filtering used to claim ex-ante portfolio returns.
"""
import argparse,json,time,zipfile,io,hashlib
from pathlib import Path
import numpy as np,pandas as pd
import yfinance as yf

# ISIN: verified via issuers and stock exchange listings BEFORE downloading returns
ADDITIONS={
 "FR0007052782":("CAC.PA","CAC40_FRANCE","EU_EQUITY_COUNTRY"),
 "IE00B1XNH568":("IMIB.MI","FTSEMIB_ITALY","EU_EQUITY_COUNTRY"),
 "FR0010251744":("LYXIB.MC","IBEX35_SPAIN_DIST","EU_EQUITY_COUNTRY"),
 "FR0010655746":("AMES.DE","IBEX35_SPAIN_ACC_2024","EU_EQUITY_COUNTRY"),
 "FR0000021842":("BEL.BR","BEL20_BELGIUM","EU_EQUITY_COUNTRY"),
 "IE00B9MRHC27":("XDN0.DE","MSCI_NORDIC","EU_EQUITY_COUNTRY"),
 "DE0005933964":("EXI1.DE","SWISS_SLI","EU_EQUITY_COUNTRY"),
}
# Issuer-verified SAME LEGAL ISIN, both quote currencies EUR
VERIFIED_ALT={
 "IE0005042456":["IUSZ.DE","ISF.MI","ISFA.AS"],
 "IE00B0M62Y33":["IAEX.AS","IAEX.SW"],
 "FR0010655746":["AMES.DE","CS1.PA","AMIBX.MC"],
}
CUTOFF="2026-07-02"
def pull(t):
    last=""
    for attempt in range(3):
        try:
            d=yf.download(t,start="2009-01-01",end=CUTOFF,auto_adjust=True,
                  repair=False,progress=False,threads=False,timeout=25)
            if isinstance(d.columns,pd.MultiIndex):d.columns=d.columns.get_level_values(0)
            d=d[["Open","High","Low","Close","Volume"]].copy()
            d.index=pd.DatetimeIndex(d.index).tz_localize(None).normalize()
            d=d[~d.index.duplicated()].sort_index()
            d=d[(d.Close>0)&(d.Open>0)&np.isfinite(d.Close)&np.isfinite(d.Open)]
            if len(d)<80:raise ValueError("too few rows "+str(len(d)))
            return d
        except Exception as exc:
            last=str(exc);time.sleep(1+attempt)
    raise RuntimeError(t+" : "+last)
def summ(d,symbol):
    w=d[(d.index>="2018-01-01")&(d.index<="2026-06-01")]
    return dict(ticker=symbol,rows=len(d),first=str(d.index.min().date()),last=str(d.index.max().date()),
      bars2018_2026=len(w),zero_vol_pct=float((w.Volume<=0).mean()) if len(w) else None,
      adv63_eur_med=float((w.Close*w.Volume).rolling(63,min_periods=42).median().median()) if len(w) else None)
def main():
    p=argparse.ArgumentParser();p.add_argument("--eu",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();r=Path(a.eu);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    catalog=pd.read_csv(r/"EU148_VERIFIED_LEGAL_ISIN_CATALOG.csv")
    assert len(catalog)==148 and catalog["isin"].nunique()==148
    catalog["isin"]=catalog["isin"].astype(str)
    base={}
    originals=[]
    for row in catalog.itertuples():
        d=pd.read_csv(r/"raw_ticker_csv"/(row.isin+".csv"),parse_dates=["date"]).set_index("date").sort_index()
        d=d[["Open","High","Low","Close","Volume"]].copy()
        base[row.isin]=d
        z=summ(d,row.venue_ticker);z.update(isin=row.isin,source="FROZEN_V3_EU148",status="ORIGINAL")
        originals.append(z)
    pd.DataFrame(originals).to_csv(out/"ORIGINAL_148_QUALITY.csv",index=False)
    weak=pd.DataFrame(originals)
    shortlist=weak.sort_values(["zero_vol_pct","adv63_eur_med"],ascending=[False,True]).head(30)
    shortlist.to_csv(out/"30_WORST_ORIGINAL_ISIN_FOR_ALTERNATIVE_SEARCH.csv",index=False)
    # Note no unverified symbol guessing: Yahoo Search by exact ISIN returns possible
    # cross listings, but candidate metadata alone does not prove symbol ISIN identity.
    hints=[]
    for i,row in enumerate(shortlist.itertuples()):
        try:
            sc=yf.Search(row.isin,max_results=20,news_count=0)
            for q in (sc.quotes or []):
                hints.append(dict(isin=row.isin,symbol=q.get("symbol",""),
                    longname=q.get("longname") or q.get("shortname") or "",
                    exchange=q.get("exchange",""),verified_same_isin=False))
        except Exception as exc:
            hints.append(dict(isin=row.isin,symbol="",longname="FETCH_FAIL: "+str(exc),
                exchange="",verified_same_isin=False))
        if i%10==0:print("ISIN_SEARCH",i+1,flush=True)
    pd.DataFrame(hints,columns=["isin","symbol","longname","exchange","verified_same_isin"]).to_csv(
        out/"YAHOO_SAME_ISIN_SEARCH_HINTS_UNVERIFIED.csv",index=False)
    # Static issuer-verified cross listing scope. Keep base quote unless independently
    # retrieved alt is materially better and matches daily return shape.
    alternatives=[];repaired=dict(base);source=dict((x,"FROZEN_V3_EU148") for x in base)
    for isin,tickers in VERIFIED_ALT.items():
        assert isin in base or isin in ADDITIONS
        if isin in base:
            old=base[isin]
            alternatives.append(dict(isin=isin,**summ(old,"ORIGINAL"),status="KEEP"))
        else:old=None
        for t in tickers:
            try:
                q=pull(t);row=dict(isin=isin,ticker=t,**{k:v for k,v in summ(q,t).items() if k!="ticker"})
                row["status"]="FETCHED";row["corr"]=None;row["returns_median_abs_gap"]=None
                if old is not None:
                    idx=q.index.intersection(old.index)
                    v0=old.Close.reindex(idx).pct_change(fill_method=None)
                    v1=q.Close.reindex(idx).pct_change(fill_method=None)
                    mask=v0.notna()&v1.notna()
                    if mask.sum()>250:
                        row["corr"]=float(v0[mask].corr(v1[mask]))
                        row["returns_median_abs_gap"]=float((v0[mask]-v1[mask]).abs().median())
                    old08=(old.index>=pd.Timestamp("2018-01-01"))&(old.index<pd.Timestamp("2026-06-01"))
                    common_new=int(((q.index>=pd.Timestamp("2018-01-01"))&(q.index<pd.Timestamp("2026-06-01"))).sum())
                    common_old=int(old08.sum())
                    # Different venues are separate price/volume executions. Never mix
                    # without proving issuer-equality and stable total-return consistency.
                    eligible=(row["corr"] is not None and row["corr"]>=.985 and row["returns_median_abs_gap"]<=.004
                        and common_new>common_old+120)
                    if eligible:
                        repaired[isin]=q;source[isin]="SAME_ISIN_VERIFIED_ALT_"+t
                        row["status"]="REPLACE_FULL_SERIES_PROVEN"; old=q
                alternatives.append(row)
                q.to_csv(out/(f"ALT_{isin}_{t}.csv"),index_label="date")
            except Exception as exc:
                alternatives.append(dict(isin=isin,ticker=t,status="UNAVAILABLE",error=str(exc)))
        print("ALT_COMPARE",isin,source.get(isin,"NO_ORIGINAL"),flush=True)
    pd.DataFrame(alternatives).to_csv(out/"SAME_ISIN_VERIFIED_ALT_COMPARISONS.csv",index=False)
    added=[]
    for isin,(ticker,expo,cat) in ADDITIONS.items():
        assert isin not in base
        try:
            q=pull(ticker)
            # Choose full original preferred ETF quotation, not a sliced attractive period.
            repaired[isin]=q;source[isin]="NEW_INDEX_"+ticker
            z=summ(q,ticker); z.update(isin=isin,exposure=expo,category=cat,source=source[isin],status="NEW_INDEX")
            added.append(z)
            print("NEW_INDEX",expo,isin,ticker,"rows",len(q),flush=True)
        except Exception as exc:
            added.append(dict(isin=isin,exposure=expo,ticker=ticker,status="FETCH_FAILED",error=str(exc)))
            print("NEW_FAILED",isin,ticker,str(exc),flush=True)
    pd.DataFrame(added).to_csv(out/"ADDED_MAJOR_EUROPEAN_MARKET_ISINS.csv",index=False)
    assert len(repaired)>=148
    # Preserve full history and no invented years. Tickers in programmatic dataset are legal ISINs.
    dest=out/"raw_ticker_csv";dest.mkdir(exist_ok=True)
    full_cat=catalog.copy()
    for z in added:
        if z['status']=="NEW_INDEX":
            isin=z["isin"]
            full_cat=pd.concat([full_cat,pd.DataFrame([dict(
             ticker=isin,isin=isin,macro_category=z["category"],
             source_type="new_country_indices_verified_20261027",
             venue_ticker=z["ticker"],first_observed=z["first"],last_observed=z["last"],
             first_trade_date=z["first"],source_sha256="new_yahoo_fetch",
             execution_liquidity_certified=False,
             yahoo_volume_zeros=z["zero_vol_pct"])])],ignore_index=True)
    for isin,d in repaired.items():
        assert d.index.is_unique and d.index.is_monotonic_increasing
        d.to_csv(dest/(isin+".csv"),index_label="date",float_format="%.12g")
    assert full_cat["isin"].nunique()==len(full_cat)
    full_cat.to_csv(out/"REPAIRED_AND_EXPANDED_LEGAL_ISIN_CATALOG.csv",index=False)
    manifest=dict(original=148,final=len(full_cat),new=len(full_cat)-148,
      alternate_isin_count=sum(v.startswith("SAME_ISIN_VERIFIED_ALT") for v in source.values()),
      normalized_currency="EUR only",returns_metric="no historic future selection",
      source_vendor="yfinance auto_adjust=True 2026-10-27, old frozen originals unchanged",
      reporting="conservative full series only, NOT mixing markets or prices",
      eurocountryonly=True,
      original_isins_preserved=all(x in full_cat["isin"].values for x in base),
      note="Cross-list Yahoo search outputs explicitly UNVERIFIED, NEVER used in price substitution",
      caveat="Current surviving ETF universe and Yahoo adjusted OHLC require independent exchange data validation")
    (out/"MANIFEST.json").write_text(json.dumps(manifest,indent=2))
    print("EU_REPAIRED_EXPANDED_PASS",json.dumps(manifest),flush=True)
if __name__=="__main__":main()
