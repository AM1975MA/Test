#!/usr/bin/env python3
"""2026 European ETF research quote warehouse: Europe-only, one ISIN one venue.

Immutable vendor data lives in fresh60_results and europe_sector2026 archives.
A/B quality grade only tests historical quote integrity. It NEVER represents
true 2017 point-in-time constituent membership or executable bid/ask fills.
"""
from __future__ import annotations
import json,hashlib,math,collections
from pathlib import Path
import pandas as pd
import numpy as np
from isin_first2026.build import check_isin,sha

ROOT=Path(__file__).resolve().parents[2]
STUDY_START=pd.Timestamp("2017-02-01")
STUDY_END=pd.Timestamp("2026-07-01")
RAW="raw_vendor"
ADJ="adj_price"
SOURCES=[
 ("NEW_FRESH60",ROOT/"isin_first2026/fresh60_results",0),
 ("STOXX_AND_SPDR30",ROOT/"europe_sector2026/results",1),
 ("XTRACKERS_ALTERNATIVES",ROOT/"europe_sector2026/alternatives/results",2),
 ("OFFICIAL_XETRA_ALIAS_AND_EUR_MILAN",ROOT/"europe_sector2026/aliases/results",3),
 ("JUSTETF_PUBLISHED_ISIN5",ROOT/"isin_first2026/five_isin_yfinance/results",4),
 ("JUSTETF_PUBLISHED_ISIN5_OTHER_VENUES",ROOT/"isin_first2026/five_isin_yfinance/second_pass/results",5),
]
BREAKS={
 "LU1681046931":("2018-02-14","Amundi current shareclass not 2008 prices, former French fund"),
 "LU1681039480":("2018-01-31","Amundi current shareclass not 2009 predecessor prices"),
 "LU1681042518":("2018-04-18","Amundi issuer explicitly dates post-merger shareclass 2018, first economic NAV 2009"),
}
EXCLUDE_GLOBAL_ISINS={"LU1900066033","NL0011683594"}
EXCLUDE_ALL_NON_EUROPE=True

def find_source(sym):
    for lab,loc,rank in SOURCES:
        rawdir="yahoo_unmodified" if lab=="JUSTETF_PUBLISHED_ISIN5" else RAW
        adjdir="yahoo_adjusted" if lab=="JUSTETF_PUBLISHED_ISIN5" else ADJ
        p=loc/rawdir/(sym+".csv")
        q=loc/adjdir/(sym+".csv")
        if p.exists() and q.exists():
            return lab,loc,rank,p,q
    return None

def load_prices(raw_path,adj_path):
    raw=pd.read_csv(raw_path,parse_dates=["date"]).set_index("date").sort_index()
    adj=pd.read_csv(adj_path,parse_dates=["date"]).set_index("date").sort_index()
    raw.index=pd.DatetimeIndex(raw.index).tz_localize(None).normalize()
    adj.index=pd.DatetimeIndex(adj.index).tz_localize(None).normalize()
    assert raw.index.is_unique and adj.index.is_unique
    assert all(z in raw.columns for z in ("Open","High","Low","Close","Adj Close","Volume"))
    assert all(z in adj.columns for z in ("Open","High","Low","Close","Volume"))
    for z in ("Open","High","Low","Close","Adj Close","Volume"):
        raw[z]=pd.to_numeric(raw[z],errors="coerce")
    for z in ("Open","High","Low","Close","Volume"):
        adj[z]=pd.to_numeric(adj[z],errors="coerce")
    return raw,adj

def candidate_universe():
    m=pd.read_csv(ROOT/"isin_first2026/results/ISIN_ALL_CANDIDATE_REFERENCE_MAPPING.csv").fillna("")
    assert len(m)==100 and m.ticker.nunique()==100
    allmap={r["ticker"]:dict(r) for _,r in m.iterrows()}
    for ticker,d in allmap.items():
        d["underlying_allowed"]="EUROPE_ONLY_FROM_PREVIOUS_AUDIT"
    # All 100 preselected tickers (60 exact-Europe old + Europe-only sector
    # provider catalogs), but five-isins contributed 3 Europe-only funds
    # (LU1834987973 already in 100 candidate). Exclude other two globals.
    new=[
       ("LU1681042518","CV9.PA","EU_FACTOR","Euronext Paris","ISSUER_AMUNDI_2018_CLASS"),
       ("LU1681042518","VCEU.MI","EU_FACTOR","Borsa Italiana","ISSUER_AMUNDI_2018_CLASS"),
       ("LU1834987973","INS.PA","EU_SECTOR_INSURANCE","Euronext Paris","ISSUER_AMUNDI_2024_QUOTE"),
       ("LU1834987973","INS.MI","EU_SECTOR_INSURANCE","Borsa Italiana","ISSUER_AMUNDI_2024_QUOTE"),
       ("IE00B5MTXJ97","SC0Y.DE","EU_SECTOR_INSURANCE","Xetra","XETRA_OFFICIAL_VALIDATED_OCT2026")
    ]
    for isin,tick,category,venue,proof in new:
        assert check_isin(isin)
        if tick in allmap:
            assert allmap[tick]["isin"]==isin
        allmap[tick]=dict(ticker=tick,isin=isin,status=proof,
           market={"Xetra":"XETR","Euronext Paris":"XPAR","Borsa Italiana":"XMIL"}[venue],
           macro_categories=category,in_original_EUR60=False,
           reference_currency="EUR",related_xetra_mnemonic=("SC0Y" if tick=="SC0Y.DE" else ""),
           reference_first_trading="",share_class_inception=BREAKS.get(isin,("",""))[0],
           manual_isin_evidence_url="",
           underlying_allowed="EUROPE_ONLY_ISSUER_CHECKED",
           etf_families="AMUNDI" if isin.startswith("LU") else "INVESCO",
           quoted_sector="INSURANCE" if "INS" in category else "EUROPE_VALUE")
    # Cross-check published 2026 issuer vs official Xetra legal share ID: all
    # existing 100 have already been identified; no orphan source aliases.
    assert len(allmap)==105
    assert len(set(d["isin"] for d in allmap.values()))>=75
    assert all(check_isin(d["isin"]) for d in allmap.values())
    assert not any(d["isin"] in EXCLUDE_GLOBAL_ISINS for d in allmap.values())
    return allmap

def assess(t,d,raw,adj,source):
    period=raw.loc[STUDY_START:STUDY_END]
    a=adj.loc[STUDY_START:STUDY_END]
    cols=["Open","High","Low","Close"]
    prices=period[cols]
    valid=(np.isfinite(prices).all(axis=1)&(prices>0).all(axis=1)&
         np.isfinite(period.Volume)&(period.Volume>=0)&
         np.isfinite(period["Adj Close"])&(period["Adj Close"]>0))
    envelope=((prices.High+1e-7>=prices[["Open","Low","Close"]].max(axis=1))&
              (prices.Low-1e-7<=prices[["Open","High","Close"]].min(axis=1)))
    invalid=(~valid)|(~envelope)
    flat=((prices.max(axis=1)-prices.min(axis=1)).abs()<1e-12)&valid
    zero=(period.Volume==0)&valid
    source_days=len(period)
    denom=max(1,source_days)
    coverage=(period.index.max()>=STUDY_END and
              len(raw.loc[:pd.Timestamp("2017-01-31")])>=252 and
              source_days>=2250) if source_days else False
    last_date=str(period.index.max().date()) if source_days else ""
    early_date=str(raw.index.min().date()) if len(raw) else ""
    first_s=pd.to_datetime(d.get("reference_first_trading") or "",errors="coerce")
    first_class=pd.to_datetime(BREAKS.get(d["isin"],("",""))[0],errors="coerce")
    # Quote may come from old fund or after merger under newer share class.
    preclass=bool(pd.notna(first_class) and
                  (len(raw)>0 and raw.index.min()<first_class))
    # The authoritative first-listed date applies to the German line only;
    # do not transfer Xetra first trading date to same-ISIN Paris/Amsterdam.
    listing=bool(t.endswith(".DE") and pd.notna(first_s) and
                 len(raw)>0 and raw.index.min()+pd.Timedelta(days=10)<first_s and
                 first_s>pd.Timestamp("2017-02-01"))
    missing_adj_dates=len(period.index.difference(a.index))
    bad_count=int(invalid.sum());flat_count=int(flat.sum());zero_count=int(zero.sum())
    pct_zero=zero_count/denom; pct_flat=flat_count/denom;pct_bad=bad_count/denom
    if preclass:
        grade="QUARANTINE_CURRENT_SHARE_CLASS_PREDECESSOR"
    elif listing:
        grade="QUARANTINE_LISTING_CONTINUITY_CONFLICT"
    elif not coverage:
        grade="NOT_FULL_2017_2026_QUOTE_HISTORY"
    elif pct_bad>.01 or missing_adj_dates/denom>.01:
        grade="HIGH_INVALID_OHLC_OR_MISSING_PRICE"
    elif pct_zero<=.02 and pct_flat<=.03:
        grade="A_CLEAN_VENDOR_QUOTES"
    elif pct_zero<=.10 and pct_flat<=.12:
        grade="B_REVIEW_REQUIRED"
    else:
        grade="C_SPORADIC_OR_STALE_QUOTE"
    ret=np.log(period.Close.where(period.Close>0)).diff()
    raw_invalid=int((ret.abs()>.25).sum())
    return dict(ticker=t,isin=d["isin"],market=d.get("market",""),
        ref_status=d.get("status",""),macro_category=d.get("macro_categories",""),
        issuer=d.get("etf_families",""),index_or_sector=d.get("quoted_sector",""),
        source_vendor="YAHOO_YFINANCE_2026",source_snapshot=source[0],
        raw_sha256=sha(source[3]),adjusted_sha256=sha(source[4]),
        venue_currency="EUR",security_type="ETF",source_first=early_date,
        source_last=str(raw.index.max().date()),reference_first_trading=
          d.get("reference_first_trading",""),source_bars=len(raw),
        observed_2017_2026=source_days,valid_ohlc_2017_2026=int((~invalid).sum()),
        first_2017_2026_quote=str(period.index.min().date()) if source_days else "",
        last_2017_2026_quote=last_date,
        prior_2017_02_bars=int(len(raw.loc[:pd.Timestamp("2017-01-31")])),
        volume_zero_bars=zero_count,volume_zero_pct=pct_zero*100,
        flat_price_bars=flat_count,flat_price_pct=pct_flat*100,
        bad_ohlc_and_missing_rows=bad_count,bad_ohlc_pct=pct_bad*100,
        missing_vendor_adjusted_rows=missing_adj_dates,
        huge_raw_close_return_gt25pct=raw_invalid,
        quote_grade=grade,
        breaks_current_shareclass=preclass,
        issuer_class_date=str(first_class.date()) if pd.notna(first_class) else "",
        german_first_trading_conflict=listing,
        historic_2017_full_quote_coverage=bool(coverage),
        original_eu60=bool(str(d.get("in_original_EUR60","")).lower()=="true"),
        indicative_market_price_not_executable=True,
        current_2026_membership_not_historical_asof2017=True)

def src_metadata(t,source):
    # These archives previously validated vendor EUR through yfinance, but
    # fresh60 separately has currency evidence for each original60.
    base=source[1]
    key=source[0]
    if key=="NEW_FRESH60":
        df=pd.read_csv(base/"ALL_60_FRESH_RAW_PRICE_AND_OLD_SOURCE_DIFFERENCES.csv").fillna("")
        z=df[df.ticker==t]
        return bool(len(z)==1 and z.iloc[0]["status"]=="EUR_VENDOR_CONFIRMED" and
             str(z.iloc[0]["yahoo_quote_currency"]).upper()=="EUR" and
             str(z.iloc[0]["yahoo_instrumentType"]).upper()=="ETF")
    fname=({"STOXX_AND_SPDR30":"DOWNLOAD_AUDIT.csv",
          "XTRACKERS_ALTERNATIVES":"ALTERNATIVES_QUALITY_AND_BASELINE_COMPARISON.csv",
          "OFFICIAL_XETRA_ALIAS_AND_EUR_MILAN":"ALIAS_AUDIT.csv",
          "JUSTETF_PUBLISHED_ISIN5":"TICKER_BY_ISIN_CURRENCY_HISTORY_QUALITY.csv",
          "JUSTETF_PUBLISHED_ISIN5_OTHER_VENUES":
                    "ALIAS2_REAL_QUOTES_AND_ORIGINAL_ISIN_VALIDATION.csv"}[key])
    d=pd.read_csv(base/fname).fillna("")
    v=d[d.ticker==t]
    if len(v)!=1:return False
    r=v.iloc[0]
    if key=="STOXX_AND_SPDR30":
        return r["status"]=="AVAILABLE_EUR" and str(r["history_currency"]).upper()=="EUR" and str(r["yahoo_instrumentType"]).upper()=="ETF"
    if key=="XTRACKERS_ALTERNATIVES":
        return r["status"]=="AVAILABLE_EUR" and str(r["history_currency"]).upper()=="EUR" and str(r["yahoo_instrumentType"]).upper()=="ETF"
    if key=="OFFICIAL_XETRA_ALIAS_AND_EUR_MILAN":
        # alias has only currency metadata, separate exact name/ISIN provenance.
        return str(r["status"])=="AVAILABLE_EUR" and str(r["yahoo_currency"]).upper()=="EUR"
    if key=="JUSTETF_PUBLISHED_ISIN5":
        return str(r["download_status"])=="YAHOO_CURRENCY_EUR_AND_XETRA_IDENTITY_OK" and str(r["quote_currency_yahoo"])=="EUR" and str(r["instrumentType_yahoo"]).upper()=="ETF"
    if key=="JUSTETF_PUBLISHED_ISIN5_OTHER_VENUES":
        return str(r["result"])=="EUR_YAHOO_ETF_CANDIDATE" and str(r["currency"]).upper()=="EUR" and str(r["instrument_type"]).upper()=="ETF"
    return False

def same_isin_venue_comparison(candidates,rawquotes):
    pairs=[]
    group=collections.defaultdict(list)
    for k,r in candidates.items():
        if k in rawquotes: group[r["isin"]].append(k)
    for isin,ts in group.items():
        if len(ts)<2:continue
        for i,t in enumerate(ts):
            for oth in ts[i+1:]:
                a=rawquotes[t].loc[STUDY_START:STUDY_END]
                b=rawquotes[oth].loc[STUDY_START:STUDY_END]
                close=pd.DataFrame({"a":a["Adj Close"],"b":b["Adj Close"]}).dropna()
                if len(close)<90:continue
                returns=np.log(close).diff().dropna()
                d=(returns.a-returns.b).abs()
                pairs.append(dict(isin=isin,first_ticker=t,second_ticker=oth,
                   overlap_dates=len(close),daily_log_return_corr=
                       float(returns.a.corr(returns.b)),
                   median_abs_return_spread_bps=float(d.median()*1e4),
                   p95_abs_return_spread_bps=float(d.quantile(.95)*1e4),
                   days_return_disagreement_gt1pct=int((d>.01).sum()),
                   days_return_disagreement_gt2pct=int((d>.02).sum())))
    return pd.DataFrame(pairs,columns=[
        "isin","first_ticker","second_ticker","overlap_dates",
        "daily_log_return_corr","median_abs_return_spread_bps",
        "p95_abs_return_spread_bps","days_return_disagreement_gt1pct",
        "days_return_disagreement_gt2pct"])

def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    clean_dir=out/"ISIN_2017_TO_2026_EUR_OHLCV_ADJUSTED"
    recent_dir=out/"POST2017_STOCK_HISTORY_REVIEW"
    clean_dir.mkdir();recent_dir.mkdir()
    proposals=candidate_universe()
    grades=[];quotes={}
    for t,r in sorted(proposals.items()):
        src=find_source(t)
        base=dict(ticker=t,isin=r["isin"],
           macro_category=r.get("macro_categories",""),
           reference_status=r.get("status",""),evidence_url=r.get("manual_isin_evidence_url",""),
           status_reason="NO_VENDOR_HISTORICAL_SOURCE" if not src else "")
        if src is None:
            grades.append(base);continue
        if not src_metadata(t,src):
            base.update(status_reason="VENDOR_CURRENCY_OR_SECURITY_TYPE_NOT_CERTIFIED")
            grades.append(base);continue
        if r["isin"] in EXCLUDE_GLOBAL_ISINS:
            raise AssertionError("GLOBAL_TICKER_ENTERED_ONLY_EUROPE_REFERENCE")
        try:
            raw,adj=load_prices(src[3],src[4])
            scores=assess(t,r,raw,adj,src)
            scores["evidence_url"]=r.get("manual_isin_evidence_url","")
            scores["status_reason"]=scores["quote_grade"]
            grades.append(scores)
            quotes[t]=(raw,adj,src)
        except Exception as e:
            base.update(status_reason="READ_VALIDATE_FAILED:"+type(e).__name__+":"+str(e)[:160])
            grades.append(base)
    grade=pd.DataFrame(grades)
    grade.to_csv(out/"ALL_EUROPE_CANDIDATES_AND_QUOTE_QUALITY.csv",index=False)
    scored=grade[grade["quote_grade"].isin(["A_CLEAN_VENDOR_QUOTES","B_REVIEW_REQUIRED"])].copy()
    ranking={"A_CLEAN_VENDOR_QUOTES":0,"B_REVIEW_REQUIRED":1}
    scored["grade_rank"]=scored["quote_grade"].map(ranking)
    # Include quality class first, then the actual quote health, then prior
    # source lineage priority. These are historical quality choices in 2026.
    scored["source_rank"]=scored["source_snapshot"].map({v[0]:v[2] for v in SOURCES})
    scored=scored.sort_values(["isin","grade_rank","volume_zero_pct",
       "flat_price_pct","bad_ohlc_pct","source_rank","ticker"],kind="mergesort")
    chosen=scored.drop_duplicates("isin").copy()
    assert chosen["isin"].is_unique
    exports=0;dates=0
    for _,r in chosen.iterrows():
        sym=r["ticker"];raw,adj,_=quotes[sym]
        z=adj.loc[:STUDY_END].copy()
        p=raw.reindex(z.index)
        envelope=(p.High+1e-7>=p[["Open","Low","Close"]].max(axis=1)) & (
                  p.Low-1e-7<=p[["Open","High","Close"]].min(axis=1))
        good=(np.isfinite(p[["Open","High","Low","Close","Adj Close","Volume"]]).all(axis=1)&
              (p[["Open","High","Low","Close","Adj Close"]]>0).all(axis=1)&
              (p.Volume>=0)&envelope)
        z=z.loc[good]
        z=z.rename(columns={"Open":"Open","High":"High","Low":"Low","Close":"Close",
                             "Volume":"Volume"})
        z.index.name="date"
        z.to_csv(clean_dir/(r["isin"]+".csv"),float_format="%.16g")
        exports+=1;dates+=len(z)
    chosen.drop(columns=["grade_rank","source_rank"]).to_csv(
         out/"ACCEPTED_ONE_LISTING_PER_UNIQUE_ISIN.csv",index=False)
    recent=grade[(grade["quote_grade"]=="NOT_FULL_2017_2026_QUOTE_HISTORY")].copy()
    recent.to_csv(out/"RECENT_ONLY_EUROPE_ETF_CANDIDATES.csv",index=False)
    verdicts=grade[(~grade.index.isin(chosen.index))].copy()
    verdicts.to_csv(out/"NOT_SELECTED_OR_QUARANTINED.csv",index=False)
    pair=same_isin_venue_comparison(proposals,{
        t:raw for t,(raw,adj,src) in quotes.items()})
    pair.to_csv(out/"SAME_ISIN_MULTI_VENUE_ADJUSTED_RETURN_COMPARE.csv",index=False)
    oldoriginal={t:row["isin"] for t,row in proposals.items()
                 if str(row.get("in_original_EUR60","")).lower()=="true"}
    assert len(oldoriginal)==60 and len(set(oldoriginal.values()))==44
    dupgroup={id:sorted(t for t,v in oldoriginal.items() if v==id)
              for id in set(oldoriginal.values())
              if list(oldoriginal.values()).count(id)>1}
    (out/"ORIGINAL_EUR60_DUPLICATE_ISINS.json").write_text(
          json.dumps(dupgroup,indent=2,sort_keys=True)+"\n")
    labels=collections.Counter(grade["quote_grade"].fillna("NO_QUOTES"))
    status=collections.Counter(grade["status_reason"].fillna(""))
    groups=collections.Counter(chosen["macro_category"].fillna("UNKNOWN"))
    summary=dict(title="FREE_EUROPE_ONLY_UNREPAIRED_ISIN_OHLCV_FOR_CLEAN_RESEARCH",
        source="Yahoo via pinned yfinance 0.2.65; independent Xetra/issuer 2026 legal ISIN check",
        total_europe_ticker_candidates=len(proposals),
        original_eur60_tickers=60,
        original_eur60_unique_isins=44,
        duplicated_older_eur60_quote_lines=16,
        known_non_europe_isins_excluded=sorted(EXCLUDE_GLOBAL_ISINS),
        accessible_vendor_quote_tickers=len(quotes),
        source_categories=dict(collections.Counter(z[2][0] for z in quotes.values())),
        grade_counts=dict(labels),reason_counts=dict(status),
        accepted_unique_fund_isins=exports,
        accepted_grade_A=int((chosen["quote_grade"]=="A_CLEAN_VENDOR_QUOTES").sum()),
        accepted_grade_B=int((chosen["quote_grade"]=="B_REVIEW_REQUIRED").sum()),
        accepted_pre2017_warmup_252=True,
        2017_to_2026_real_vendor_quote_exported_csv=exports,
        exported_total_date_rows=dates,
        accepted_macro_groups=dict(groups),
        recent_quote_lines_not_suitable_full2017=len(recent),
        alternative_quote_duplicate_isin_venue_pairs=len(pair),
        issuer_known_preclass_breaks=BREAKS,
        false_if_PIT_historical_membership=True,
        received_actual_vendor_market_OHLCV_not_Nav=True,
        no_synthetic_high_low_repair=True,
        vendor_currency_check_required=True,
        data_rejected_on_future_return_performance=False,
        current_2026_survivor_sample_bias_remains=True,
        no_model_fitted_no_portfolio_test_or_production_changes=True,
        generated_utc=str(pd.Timestamp.now(tz="UTC")))
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
       sha(p)+"  "+str(p.relative_to(out))+"\n"
       for p in sorted(out.rglob("*.csv")))+
       sha(out/"RESULT.json")+"  RESULT.json\n"+
       sha(out/"ORIGINAL_EUR60_DUPLICATE_ISINS.json")+"  ORIGINAL_EUR60_DUPLICATE_ISINS.json\n")
    print("FREE_EUROPE_ISIN_OHLCV_FROZEN_RESULT "+json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    main(parser.parse_args().out)
