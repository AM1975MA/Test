#!/usr/bin/env python3
"""Assemble auditable, 2016-warmed, ISIN-deduplicated EUROPE UCITS ETF histories.

Frozen asof-2026 fund list: not historically point-in-time! Never call this an
unbiased 2017 study cohort. Unrepaired Yahoo venue-adjusted OHLC, no return
cap, no future-dependent ML model. Euro corporate ETFs that may hold issuers
outside Europe remain a separate, NON-STRICT research pool.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from isin_first2026.build import check_isin, sha
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"isin_first2026"
HERE=Path(__file__).resolve().parent
FIRST_SIGNAL=pd.Timestamp("2017-01-31")
WARM_START=pd.Timestamp("2016-01-01")
STUDY_BEGIN=pd.Timestamp("2017-02-01")
STUDY_END=pd.Timestamp("2026-07-01")
SOURCES=[
 ("fresh60",DATA/"fresh60_results/adj_price"),
 ("sector30",ROOT/"europe_sector2026/results/adj_price"),
 ("alts21",ROOT/"europe_sector2026/alternatives/results/adj_price"),
 ("alias8",ROOT/"europe_sector2026/aliases/results/adj_price"),
 ("bond16",HERE/"bonds_results/vendor_adjusted"),
 ("isin5_16",DATA/"five_isin_yfinance/results/yahoo_adjusted"),
 ("isin5_4",DATA/"five_isin_yfinance/second_pass/results/adj_price")
]
GEO_STRICT="STRICT_EUROPE_EXPOSURE"
GEO_OTHER="EUR_DENOMINATED_GLOBAL_ISSUER_CREDIT_NOT_STRICT_EUROPE"
SECTORS=set(("COMMUNICATION_SERVICES","CONSUMER_DISCRETIONARY",
             "CONSUMER_STAPLES","ENERGY","FINANCIALS","HEALTH_CARE",
             "INDUSTRIALS","INFORMATION_TECHNOLOGY","MATERIALS",
             "REAL_ESTATE","UTILITIES"))

def row_provenance():
    cur=pd.read_csv(DATA/"results/ISIN_ALL_CANDIDATE_REFERENCE_MAPPING.csv").fillna("")
    mapping={}
    for d in cur.itertuples(index=False):
        id_=str(d.isin)
        if not check_isin(id_):continue
        mapping[d.ticker]=dict(ticker=d.ticker,isin=id_,
            current_isin_provenance=d.status,reference_market=d.market,
            first_trading_date=d.reference_first_trading or "",
            share_class_inception=d.share_class_inception or "",
            first_ever_issuer_class_unproven=bool(d.share_class_inception and
                                      str(d.share_class_inception)>"2017-01-31"),
            original_EU60=bool(d.in_original_EUR60),
            geographic_scope=GEO_STRICT,
            original_macro_category=d.macro_categories,
            sector_11="",index_subsector="",underlying_bucket="",
            reason_for_label="Official issuer sector or frozen EU underlying audit")
    # Base original categorizations
    for d in mapping.values():
        label=d["original_macro_category"]
        d["underlying_bucket"]=("SOVEREIGN_EUR" if "EU_SOVEREIGN" in label else
            "EU_PROPERTY" if "EU_PROPERTY" in label else
            "EU_EQUITY_FACTOR" if "EU_FACTOR" in label else
            "EU_EQUITY_COUNTRY" if "EU_COUNTRY" in label else
            "EU_EQUITY_BROAD" if "EU_BROAD" in label else
            "EU_EQUITY_SECTOR" if "EU_SECTOR" in label else "")
    sector_csv=pd.read_csv(ROOT/"europe_sector2026/CATALOG.csv").fillna("")
    for x in sector_csv.itertuples(index=False):
        t=x.ticker
        if t in mapping:
            meta=mapping[t];meta["sector_11"]=x.sector_11
            meta["index_subsector"]=x.sector_name
            meta["underlying_bucket"]=("EU_PROPERTY" if x.sector_11=="REAL_ESTATE"
                  else "EU_EQUITY_SECTOR")
    alt_csv=pd.read_csv(ROOT/"europe_sector2026/alternatives/CATALOG.csv").fillna("")
    for x in alt_csv.itertuples(index=False):
        if x.ticker not in mapping:continue
        m=mapping[x.ticker]
        m["sector_11"]=x.sector
        m["index_subsector"]=x.index_name
        m["underlying_bucket"]=("EU_PROPERTY" if x.sector=="REAL_ESTATE"
                                  else "EU_EQUITY_SECTOR")
    alias_csv=pd.read_csv(ROOT/"europe_sector2026/aliases/CATALOG.csv").fillna("")
    for x in alias_csv.itertuples(index=False):
        if x.ticker not in mapping:continue
        m=mapping[x.ticker];m["sector_11"]=x.sector
        m["underlying_bucket"]=("EU_PROPERTY" if x.sector=="REAL_ESTATE"
                                  else "EU_EQUITY_SECTOR")
        m["index_subsector"]="2026 alias / alternate EUR venue"
    bonds=pd.read_csv(HERE/"BOND_ISIN_CANDIDATES.csv").fillna("")
    for x in bonds.itertuples(index=False):
        m=mapping.setdefault(x.ticker,dict(ticker=x.ticker,isin=x.isin,
           original_EU60=False,reference_market=x.ticker.rsplit(".",1)[-1],
           first_trading_date="",share_class_inception="",
           first_ever_issuer_class_unproven=False,
           current_isin_provenance="2026_OFFICIAL_ISSUER_AND_XETRA_TO_CHECK",
           geographic_scope=GEO_STRICT,original_macro_category="",
           sector_11="",index_subsector="",underlying_bucket=""))
        assert m["isin"]==x.isin
        m["geographic_scope"]=(GEO_STRICT if x.underlying_scope=="EURO_SOVEREIGN"
                         else GEO_OTHER)
        m["underlying_bucket"]=("SOVEREIGN_EUR" if x.underlying_scope=="EURO_SOVEREIGN"
                                 else "EUR_CREDIT_MIXED")
        m["index_subsector"]=x.segment
        m["reason_for_label"]=x.description
    extra=pd.read_csv(DATA/"five_isin_yfinance/CATALOG.csv").fillna("")
    for x in extra.itertuples(index=False):
        if x.underlying_geo!="EUROPE_ONLY":continue
        m=mapping.setdefault(x.yahoo_ticker,dict(ticker=x.yahoo_ticker,
           isin=x.isin,original_EU60=False,reference_market=x.yahoo_ticker.rsplit(".",1)[-1],
           first_trading_date="",share_class_inception="",
           first_ever_issuer_class_unproven=False,
           current_isin_provenance="JUSTETF_PUBLIC_2026_PROFILE_NOT_REGULATOR_PROOF",
           geographic_scope=GEO_STRICT,original_macro_category="",
           sector_11="",index_subsector="",underlying_bucket="EU_EQUITY_SECTOR"))
        assert m["isin"]==x.isin
        if x.isin=="LU1681042518":
            m["underlying_bucket"]="EU_EQUITY_FACTOR"
            m["index_subsector"]="MSCI Europe Value Factor"
        else:
            m["sector_11"]="FINANCIALS"
            m["index_subsector"]="Europe Insurance"
    for x in pd.read_csv(DATA/"five_isin_yfinance/second_pass/CATALOG.csv").fillna("").itertuples(index=False):
        if x.underlying_geo!="EUROPE_ONLY":continue
        if x.yahoo_ticker not in mapping:
            mapping[x.yahoo_ticker]=dict(ticker=x.yahoo_ticker,isin=x.isin,
              original_EU60=False,reference_market=x.yahoo_ticker.rsplit(".",1)[-1],
              first_trading_date="",share_class_inception="",
              first_ever_issuer_class_unproven=False,
              current_isin_provenance="JUSTETF_PUBLIC_2026_PROFILE_NOT_REGULATOR_PROOF",
              geographic_scope=GEO_STRICT,original_macro_category="",
              sector_11="FINANCIALS",index_subsector="Europe Insurance",
              underlying_bucket="EU_EQUITY_SECTOR")
    return mapping

def vendor_overrides():
    out={}
    p=HERE/"bonds_results/BOND_ISIN_QUOTE_AUDIT.csv"
    assert p.exists(),"Bond source archive required before basket build"
    for z in pd.read_csv(p).fillna("").itertuples(index=False):
        out[z.ticker]=dict(bond_download_status=z.download_status,
                  official_xetra_verified=str(z.official_Xetra_isin_confirmed)=="True")
    return out

def readbars(path):
    z=pd.read_csv(path)
    if "date" not in z or not set(("Open","High","Low","Close","Volume")).issubset(z):
        return None
    z["date"]=pd.to_datetime(z["date"],errors="coerce")
    z=z.dropna(subset=["date"]).set_index("date").sort_index()
    z.index=pd.DatetimeIndex(z.index).tz_localize(None).normalize()
    z=z.loc[~z.index.duplicated(keep="first")]
    for k in ("Open","High","Low","Close","Volume"):z[k]=pd.to_numeric(z[k],errors="coerce")
    z=z[["Open","High","Low","Close","Volume"]]
    z.index.name="date"
    return z

def quality(meta,source,path,z,bond_data):
    before=z.loc[:FIRST_SIGNAL-pd.Timedelta(days=1)]
    warm=z.loc[WARM_START:FIRST_SIGNAL-pd.Timedelta(days=1)]
    test=z.loc[STUDY_BEGIN:STUDY_END]
    valid_ohlc=(np.isfinite(test[["Open","High","Low","Close"]]).all(axis=1)&
       (test[["Open","High","Low","Close"]]>0).all(axis=1))
    valid_vol=np.isfinite(test.Volume)&(test.Volume>=0)
    valid=valid_ohlc&valid_vol
    high=test["High"]
    low=test["Low"]
    upper=test[["Open","Low","Close"]].max(axis=1)
    lower=test[["Open","High","Close"]].min(axis=1)
    ohlc_bad=valid&( (high<upper-1e-9) | (low>lower+1e-9) )
    flat=valid&(test[["Open","High","Low","Close"]].max(axis=1)-
                   test[["Open","High","Low","Close"]].min(axis=1)<1e-10)
    blank=test.Volume.eq(0)&valid
    ratio=lambda count: (float(count)/len(test) if len(test) else 1.0)
    # Strict first-seen 2016 warmup, no assumed synthetic bars.
    warm252=len(before)>=252
    warm126=len(before)>=126
    first_available=str(z.index.min().date())
    issuer_break=bool(meta.get("first_ever_issuer_class_unproven",False))
    first_trading=meta.get("first_trading_date","")
    # Xetra modern first-trade info is as-of 2026 and may not represent
    # alternative venue listing 2017, so only unequivocal issuer class
    # launch >=2018 is used to quarantine.
    no_2017=issuer_break or not warm252
    if meta.get("underlying_bucket")=="EUR_CREDIT_MIXED":
        scope="MIXED_GEOGRAPHY_EXCLUDE_STRICT"
    else:scope="STRICT_EUROPE"
    isbond=source=="bond16"
    bond_ver=bool(bond_data.get(meta["ticker"],{}).get("official_xetra_verified"))
    if isbond and meta["ticker"].endswith(".DE") and not bond_ver:
        identity_status="REJECT_XETRA_IDENTITY"
    elif isbond:
        identity_status=bond_data.get(meta["ticker"],{}).get("bond_download_status","NO_BOND_STATUS")
    else:identity_status=meta["current_isin_provenance"]
    enough_test=len(test)>=2250 and test.index.max()>=STUDY_END
    if no_2017:decision="NO_2017_ISIN_LINEAGE_OR_WARMUP"
    elif isbond and meta["ticker"].endswith(".DE") and not bond_ver:
        decision="NO_OFFICIAL_XETRA_BOND_MATCH"
    elif not enough_test:decision="INCOMPLETE_2017_2026_PRICE_SERIES"
    elif ratio((~valid).sum())>.015:decision="INVALID_DAILY_QUOTES_OVER_1_5PCT"
    elif ratio(ohlc_bad.sum())>.01:decision="BROKEN_OHLC_OVER_1PCT"
    elif ratio(blank.sum())>.10 or ratio(flat.sum())>.12:
        decision="THIN_OR_STALE_DAILY_QUOTES"
    else:decision="A" if ratio(blank.sum())<=.02 and ratio(flat.sum())<=.03 else "B"
    # Data quality measured over entire sample: this is an exploratory,
    # ex-post fixed *data-source* cohort, not PIT investability.
    return dict(ticker=meta["ticker"],isin=meta["isin"],
        source=source,source_sha256=sha(path),
        benchmark_bucket=meta["underlying_bucket"],
        underlying_scope=scope,sector_11=meta["sector_11"],
        index_subsector=meta["index_subsector"],
        original_EU60=meta["original_EU60"],
        reference=identity_status,
        reference_currency_2026="EUR",
        bar_first=first_available,bar_last=str(z.index.max().date()),
        bars_before_first_signal=len(before),
        bars_within_2016_to_signal=len(warm),
        year2016_rows=int((z.index.year==2016).sum()),
        sufficient_126_warmup=warm126,
        sufficient_252_warmup=warm252,
        bars_in_2017_to_July2026=len(test),
        invalid_price_rows=int((~valid).sum()),
        bad_ohlc_envelope_rows=int(ohlc_bad.sum()),
        broken_ohlc_envelope_pct=ratio(ohlc_bad.sum())*100,
        vendor_zero_volume_rows=int(blank.sum()),
        vendor_zero_volume_pct=ratio(blank.sum())*100,
        vendor_flat_OHLC_rows=int(flat.sum()),
        vendor_flat_OHLC_pct=ratio(flat.sum())*100,
        known_2018_current_class_quarantine=issuer_break,
        current_class_first_seen=meta.get("share_class_inception",""),
        decision=decision)

def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    (out/"isin_daily_ohlcv_eur").mkdir()
    mp=row_provenance()
    bond_data=vendor_overrides()
    qualities=[];price_by_ticker={}
    miss=[]
    for ticker,meta in sorted(mp.items()):
        if not check_isin(meta["isin"]):continue
        for source,root in SOURCES:
            p=root/(ticker+".csv")
            if not p.exists():continue
            z=readbars(p)
            if z is None or z.empty:continue
            audit=quality(meta,source,p,z,bond_data)
            qualities.append(audit)
            # Duplicated vendor snapshots: preserve diagnostic rows, choose
            # source priority (fresh60 > sectors > alternatives > bonds...);
            # DO NOT pick by future returns.
            if ticker not in price_by_ticker:
                price_by_ticker[ticker]=(z,audit)
        if ticker not in price_by_ticker:miss.append(ticker)
    audits=pd.DataFrame(qualities)
    assert len(audits)>=75, len(audits)
    audits.to_csv(out/"ALL_EUROPE_ISIN_QUOTES_SOURCE_QUALITY.csv",index=False)
    selected_rows=pd.DataFrame([x[1] for x in price_by_ticker.values()])
    strict=selected_rows[(selected_rows.underlying_scope=="STRICT_EUROPE")&
                         (selected_rows.decision.isin(("A","B")))].copy()
    # Predeclared fixed deterministic quote choice, by 2016-26 QUOTE quality
    # not by returns. Actual first-period portfolio universe would need PIT.
    strict["quality_rank"]=strict.decision.map({"A":0,"B":1})
    strict["source_rank"]=strict.source.map(
       {"fresh60":0,"sector30":1,"alts21":2,"alias8":3,"bond16":4,
        "isin5_16":5,"isin5_4":6})
    strict=strict.sort_values(["isin","quality_rank","vendor_zero_volume_pct",
           "broken_ohlc_envelope_pct","source_rank","ticker"],kind="mergesort")
    strict_unique=strict.drop_duplicates("isin",keep="first").copy()
    strict_unique.drop(columns=["quality_rank","source_rank"]).to_csv(
           out/"STRICT_EUROPE_2017_WARM_2016_UNIQUE_ISIN.csv",index=False)
    mixed=selected_rows[(selected_rows.underlying_scope!="STRICT_EUROPE")&
                         (selected_rows.decision.isin(("A","B")))].copy()
    mixed=mixed.sort_values(["isin","vendor_zero_volume_pct","ticker"]).drop_duplicates("isin")
    mixed.to_csv(out/"SEPARATE_EUR_DENOMINATED_GLOBAL_ISSUER_CREDIT.csv",index=False)
    # ETF uniqueness strict
    assert strict_unique["isin"].is_unique and all(strict_unique["isin"].map(check_isin))
    date_strict={}
    for x in strict_unique.itertuples(index=False):
        z=price_by_ticker[x.ticker][0].loc[WARM_START:STUDY_END].copy()
        z.insert(0,"isin",x.isin)
        z.insert(1,"ticker",x.ticker)
        z.insert(2,"venue",x.ticker.rsplit(".",1)[-1])
        z.reset_index().to_csv(
            out/"isin_daily_ohlcv_eur"/(x.isin+".csv"),index=False,
            float_format="%.14g")
        date_strict[x.isin]=z
    frame={}
    for k in ("Open","Close","Volume"):
        frame[k]=pd.concat([v[k].rename(isin) for isin,v in date_strict.items()],
            axis=1).sort_index()
        frame[k].index.name="date"
        frame[k].to_csv(out/("WIDE_DAILY_"+k.upper()+"_2016_2026.csv"),
            float_format="%.14g",date_format="%Y-%m-%d")
    categories=dict(collections.Counter(strict_unique.benchmark_bucket))
    sectors=dict(collections.Counter(strict_unique.sector_11))
    old60=selected_rows[selected_rows.original_EU60.astype(bool)]
    original_isin=set(old60["isin"])
    selected_isin=set(strict_unique["isin"])
    if len(original_isin)!=44:raise RuntimeError(
        "Original EUR60 ISIN 44 expected, got "+str(len(original_isin)))
    summary=dict(status="ISIN_DEDUP_EUROPE_PRICE_COHORT_2016_2026",
       research_use_only_current_2026_survivor_universe=True,
       data_quality_window_future_cohort_selection_warning=True,
       no_historical_point_in_time_security_membership_proven=True,
       no_future_return_selection_or_model_training=True,
       first_signal="2017-01-31",source_price_adjusted_EUR_market_bars=True,
       source_venue_Open_not_guaranteed_executable=True,
       all_quote_source_copies_inspected=len(audits),
       all_distinct_retrieved_tickers=len(price_by_ticker),
       all_distinct_europe_isins_with_any_source=len(set(
           item["isin"] for item in mp.values() if
           item["geographic_scope"]==GEO_STRICT)),
       original60_ticker_count=int(old60.shape[0]),
       original60_ISIN_distinct=int(len(original_isin)),
       original60_2017_252day_warmup=int(old60[
           old60.sufficient_252_warmup].ticker.nunique()),
       original60_2016_full_observations_mean=float(old60.year2016_rows.mean()),
       original60_2016_full_observations_min=int(old60.year2016_rows.min()),
       selected_Strict_Europe_unique_ISIN_count=len(strict_unique),
       selected_new_ISIN_not_in_original_EUR60=int(len(selected_isin-original_isin)),
       selected_strict_macro_buckets=categories,
       selected_strict_11sector_coverage={
          s:int(sectors.get(s,0)) for s in sorted(SECTORS)},
       selected_strict_sector_count=sum(s in sectors for s in SECTORS),
       separate_eurodenominated_mixed_credit_ISIN=len(mixed),
       excluded_for_insufficient_start_or_warmup=int(
           (selected_rows.decision=="NO_2017_ISIN_LINEAGE_OR_WARMUP").sum()),
       excluded_for_bad_ohlc=int(
           (selected_rows.decision=="BROKEN_OHLC_OVER_1PCT").sum()),
       excluded_thin_or_stale=int(
           (selected_rows.decision=="THIN_OR_STALE_DAILY_QUOTES").sum()),
       original_etf_trader_unmodified=True,backtest_not_executed=True,
       source_catalogs_provenance=[
          "2026 stockmaster Xetra and issuer ISIN mapping",
          "fresh Oct2026 vendor 60 EU120 ticker copies",
          "STOXX Europe 600 + SPDR Europe 30 daily issuer EUR venues",
          "Xtrackers + Amundi alternatives 21/aliases 8",
          "official euro-government 1-3 3-5 15-30 inflation government",
          "euro corporate IG high yield 1-5 mixed geography not strict"],
       source_missing_tickers=miss,
       assembled_at_utc=str(pd.Timestamp.now(tz="UTC")))
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
        sha(p)+"  "+str(p.relative_to(out))+"\n"
        for p in sorted(out.rglob("*.csv")))+
        sha(out/"RESULT.json")+"  RESULT.json\n")
    print("EUROPE_ISIN_WARM_2016_BASKET_DONE",json.dumps(summary),flush=True)

if __name__=="__main__":
    q=argparse.ArgumentParser();q.add_argument("--out",required=True)
    main(q.parse_args().out)
