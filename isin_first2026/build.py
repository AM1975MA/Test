#!/usr/bin/env python3
"""Build provenance-aware European ETF daily price dataset keyed by official ISIN.

Deutsche Börse current public XETR instrument file supplies legal identifier;
previously downloaded Yahoo venue OHLCV supplies actual date-indexed bars.
NEVER collapse two traded venue Open prices into a synthetic one. Only a single
confirmed EUR security per ISIN can be selected for exploratory cleaned data.
NOT real PIT/security master and NOT a backtest or live execution feed.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, math, re, urllib.request
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
URL="https://www.cashmarket.deutsche-boerse.com/resource/blob/1528/a31c10e3183f4c5dd721f9c7f9eaaaea/data/t7-xetr-allTradableInstruments.csv"
STUDY_START=pd.Timestamp("2017-02-01")
STUDY_END=pd.Timestamp("2026-07-01")
WARM_START=pd.Timestamp("2017-01-01")
REQUIRED_COLS=("Open","High","Low","Close","Volume")
VENUE_GROUP={"DE":"XETR","MI":"XMIL","AS":"XAMS","PA":"XPAR",
    "MC":"XMAD","SG":"XSTU","SW":"XSWX","L":"XLON"}

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as fd:
        for z in iter(lambda:fd.read(1<<20),b""):h.update(z)
    return h.hexdigest()

def check_isin(x):
    if not re.fullmatch(r"[A-Z]{2}[0-9A-Z]{9}[0-9]",str(x)):return False
    x="".join(str(int(v,36)) for v in x)
    return sum(sum(divmod(int(ch)*(2 if j%2 else 1),10)) for j,ch in enumerate(x[::-1]))%10==0

def canonical(row):
    return {str(k).strip():str(v).strip() for k,v in row.items() if k is not None}

def download_xetra():
    req=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0",
                                            "Accept":"text/csv,*/*"})
    with urllib.request.urlopen(req,timeout=35) as response:
        raw=response.read(20_000_000)
        assert response.status==200 and b"ISIN" in raw[:8000]
    # Official cash instrument guide: line1 market, line2 date, line3 headers.
    txt=raw.decode("utf-8-sig")
    lines=txt.splitlines()
    assert lines[0].startswith("Market:;XETR")
    assert lines[2].startswith("Product Status;")
    catalog=[canonical(z) for z in csv.DictReader(io.StringIO("\n".join(lines[2:])),
                                           delimiter=";")]
    assert len(catalog)>5000
    assert all(q in catalog[0] for q in ("ISIN","Mnemonic","Currency","Instrument Type"))
    records=defaultdict(list)
    bad=0
    for row in catalog:
        sym=row["Mnemonic"].upper()
        isin=row["ISIN"].upper()
        if not check_isin(isin):
            bad+=1;continue
        records[sym].append(row)
    return records,dict(url=URL,market="XETR",last_update=lines[1],
      records=len(catalog),invalid_isins=bad,source_SHA256=hashlib.sha256(raw).hexdigest())

def add_candidate(out,ticker,source,category="",isin="",family="",label=""):
    ticker=str(ticker).strip().upper()
    if not ticker or "." not in ticker:return
    record=out.setdefault(ticker,dict(ticker=ticker,catalogs=[],macro_categories=set(),
                      proposed_isins=set(),families=set(),subsectors=set()))
    if source not in record["catalogs"]:record["catalogs"].append(source)
    if category:record["macro_categories"].add(str(category).strip())
    if isin and str(isin).strip() not in ("nan","UNKNOWN"):
        record["proposed_isins"].add(str(isin).upper().strip())
    if family:record["families"].add(str(family).strip())
    if label:record["subsectors"].add(str(label).strip())

def load_proposals():
    p={}
    roster=pd.read_csv(ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv").fillna("")
    assert len(roster)==60 and roster.ticker.nunique()==60
    for x in roster.itertuples(index=False):
        add_candidate(p,x.ticker,"EUR60_FROZEN",category=x.macro_category)
    a=pd.read_csv(ROOT/"europe_sector2026/CATALOG.csv").fillna("")
    assert len(a)==30
    for x in a.itertuples(index=False):
        add_candidate(p,x.ticker,"30_EU_SECTORS_YAHOO",
                      category=x.sector_11,isin=x.isin_issuer_verified,
                      family=x.provider,label=x.sector_name)
    a=pd.read_csv(ROOT/"europe_sector2026/alternatives/CATALOG.csv").fillna("")
    assert len(a)==21
    for x in a.itertuples(index=False):
        add_candidate(p,x.ticker,"21_ALT_PROPOSED",
                      category=x.sector,isin=x.isin,family=x.issuer,
                      label=x.index_name)
    a=pd.read_csv(ROOT/"europe_sector2026/aliases/CATALOG.csv").fillna("")
    assert len(a)==8
    for x in a.itertuples(index=False):
        add_candidate(p,x.ticker,"8_SAME_ISIN_OR_XETRA_ALIASES",
                      category=x.sector,isin=x.isin,family=x.issuer,
                      label=x.comparison_type)
        add_candidate(p,x.original_ticker,"8_ALIAS_ORIGIN",
                      category=x.sector,isin=x.isin,family=x.issuer,
                      label=x.comparison_type)
    evidence=pd.read_csv(ROOT/"isin_first2026/MANUALLY_VERIFIED_NON_XETRA_EUR60_ISINS.csv").fillna("")
    assert len(evidence)==22 and evidence.ticker.nunique()==22
    for x in evidence.itertuples(index=False):
        assert check_isin(x.isin) and x.evidence_url.startswith("https://")
        assert x.ticker in p and "EUR60_FROZEN" in p[x.ticker]["catalogs"]
        add_candidate(p,x.ticker,"SOURCED_MANUAL_ISSUER_OR_SECONDARY_ISIN",
                      isin=x.isin,family=x.evidence_quality)
        p[x.ticker]["manual_isin_evidence_url"]=x.evidence_url
        p[x.ticker]["manual_isin_evidence_quality"]=x.evidence_quality
        p[x.ticker]["manual_linked_xetra"]=x.xetra_reference_mnemonic
        p[x.ticker]["manual_class_launch"]=x.share_class_inception_date
    return p

def identify(proposals,xetra):
    identified=[]
    for t,r in sorted(proposals.items()):
        suffix=t.rsplit(".",1)[1]
        src=sorted(r["proposed_isins"])
        related_mnemonic=(t[:-3] if suffix=="DE" else
                          r.get("manual_linked_xetra",""))
        official=xetra.get(related_mnemonic,[]) if related_mnemonic else []
        # Exact issuer supplied same-ISIN Xetra crosslisting is proof only
        # if the official current Xetra master independently matches.
        official_ids=sorted({u["ISIN"] for u in official
                            if u["MIC Code"]=="XETR" and
                            u["Product Status"]=="Active" and
                            u["Instrument Status"]=="Active" and
                            u["Instrument Type"]=="ETF"})
        if len(src)>1 or len(official_ids)>1:
            status="IDENTITY_COLLISION";ident=""
        elif src and official_ids and src[0]!=official_ids[0]:
            status="ISIN_CONFLICT_ISSUER_VS_XETRA";ident=""
        elif official_ids:
            status=("XETRA_2026_OFFICIAL" if suffix=="DE"
                else "SAME_ISIN_CONFIRMED_BY_XETRA_AND_ISSUER") + (
                "_ISSUER_CROSSCHECK" if src and suffix=="DE" else "")
            ident=official_ids[0]
        elif src:
            status=("SECONDARY_PROFILE_ONLY_UNCONFIRMED" if
               r.get("manual_isin_evidence_quality","").startswith("SECONDARY")
               else "ISSUER_CATALOG_ONLY_NO_XETRA_MATCH")
            ident=src[0]
        else:
            status="UNRESOLVED_ISIN_NO_EVIDENCE";ident=""
        official_info=official[0] if official and len(official_ids)==1 else {}
        ccy=str(official_info.get("Currency","") or official_info.get("Settlement Currency","")).upper()
        if ccy and ccy!="EUR":
            status="NON_EUR_OFFICIAL_XETRA";ident=""
        if ident and not check_isin(ident):
            status="INVALID_DECLARED_ISIN";ident=""
        identified.append(dict(ticker=t,isin=ident,status=status,
             vendor_known_identifiers="|".join(src),
             xetra_candidate_isins="|".join(official_ids),
             issuer_proposed=len(src)>0,reference_currency=ccy,
             reference_first_trading=str(official_info.get("First Trading Date","")),
             related_xetra_mnemonic=related_mnemonic,
             manual_isin_evidence_url=r.get("manual_isin_evidence_url",""),
             evidence_quality=r.get("manual_isin_evidence_quality",""),
             share_class_inception=r.get("manual_class_launch",""),
             reference_instrument_name=str(official_info.get("Instrument","")),
             reference_instrument_type=str(official_info.get("Instrument Type","")),
             market=VENUE_GROUP.get(suffix,suffix),
             in_original_EUR60="EUR60_FROZEN" in r["catalogs"],
             source_catalogs="|".join(r["catalogs"]),
             macro_categories="|".join(sorted(r["macro_categories"])),
             etf_families="|".join(sorted(r["families"])),
             quoted_sector="|".join(sorted(r["subsectors"]))))
    return pd.DataFrame(identified)

def previous_path(t):
    # Prefer independent raw-vendor quoted data already explicitly archived
    # (adjusted copy), not the old EU120 adjusted OHLC which had High/Low fixes.
    q=[
        ("2026_STOXX_SPDR_VENDOR_ASOF_DOWNLOAD",ROOT/"europe_sector2026/results/adj_price"/(t+".csv")),
        ("2026_AMUNDI_XTRACKERS_VENDOR_ASOF_DOWNLOAD",
           ROOT/"europe_sector2026/alternatives/results/adj_price"/(t+".csv")),
        ("2026_XETRA_MILAN_ALIAS_VENDOR_ASOF_DOWNLOAD",
           ROOT/"europe_sector2026/aliases/results/adj_price"/(t+".csv")),
        ("2026_LEGACY_EU120_OHLC_ENVELOPE_SANITIZED",
           ROOT/"data/eu120/raw_ticker_csv"/(t+".csv")),
    ]
    for source,path in q:
        if path.exists():return source,path
    return "",None

def read_prices(t):
    source,path=previous_path(t)
    if path is None:return None,None,None
    z=pd.read_csv(path)
    datefield=next((c for c in z.columns if c.lower() in ("date","datetime")),None)
    if datefield is None:return None,source,path
    z[datefield]=pd.to_datetime(z[datefield],errors="coerce")
    z=z.dropna(subset=[datefield]).set_index(datefield).sort_index()
    z.index=pd.DatetimeIndex(z.index).tz_localize(None).normalize()
    if any(k not in z for k in REQUIRED_COLS):return None,source,path
    z=z.loc[~z.index.duplicated(keep="first"),list(REQUIRED_COLS)].copy()
    for c in REQUIRED_COLS:z[c]=pd.to_numeric(z[c],errors="coerce")
    z.index.name="date"
    return z,source,path

def assess(t,row,z,path,source):
    stats=dict(ticker=t,isin=row.isin,market=row.market,
        category=row.macro_categories,reference=row.status,
        source_quote_type=source,source_sha256=sha(path) if path else "",
        asset_history_claim="YEAR_2026_SURVIVOR_NOT_TRUE_PIT",
        future_filter_universe_retro_curated=True)
    if z is None or z.empty:
        return dict(stats,status="MISSING_OR_INVALID_VENDOR_CSV")
    window=z.loc[STUDY_START:STUDY_END]
    pre=z.loc[:pd.Timestamp("2017-01-31")]
    finite=np.isfinite(window[list(REQUIRED_COLS)].to_numpy(float)).all(axis=1)
    valid=finite & (window[["Open","High","Low","Close"]]>0).all(axis=1) & (window.Volume>=0)
    mx=window[["Open","High","Low","Close"]].max(axis=1)
    mn=window[["Open","High","Low","Close"]].min(axis=1)
    flat=((mx-mn).abs()<1e-9)&valid
    bad=(window["High"] < window[["Open","Low","Close"]].max(axis=1)-1e-8) | (
         window["Low"] > window[["Open","High","Close"]].min(axis=1)+1e-8)
    last=window.index.max() if len(window) else pd.NaT
    zrate=float((window.Volume.eq(0)&valid).sum()/len(window)) if len(window) else math.nan
    frate=float(flat.sum()/len(window)) if len(window) else math.nan
    ret=np.log(window.Close.where(window.Close>0)).diff()
    hist=bool(len(pre)>=252 and pd.notna(last) and last>=STUDY_END)
    # The current Amundi share class was first introduced in 2018, whereas
    # legacy Yahoo has prices as early as 2008 under the surviving ticker.
    # Do not let retrospective predecessor bars masquerade as 2017 prices
    # belonging to the 2018 legal ISIN until issuer continuity is proven.
    class_date=pd.to_datetime(getattr(row,"share_class_inception",""),errors="coerce")
    invalid_preclass=bool(pd.notna(class_date) and z.index.min()<class_date)
    suspicious=(window.loc[valid,"Close"].pct_change().abs()>.25).sum()
    grade=("QUARANTINE_PRECLASS_HISTORY" if invalid_preclass else
           "NOT_READY_2017_2026" if not hist else
           "BAD_SOURCE_BAR_RECORDS" if (~valid).sum()>len(window)*.015 or bad.sum()>len(window)*.01 else
           "A_QUOTE_CLEAN" if zrate<=.02 and frate<=.03 else
           "B_QUOTE_REVIEW" if zrate<=.10 and frate<=.12 else
           "C_SPARSE_OR_STALE_YAHOO")
    stats.update(dict(status="HAS_HISTORICAL_VENDOR_QUOTES",
        first_vendor=str(z.index.min().date()),last_vendor=str(z.index.max().date()),
        pre2017_bars=len(pre),study_bars=len(window),
        invalid_ohlc_volume=int((~valid).sum()),bad_envelope=int(bad.sum()),
        zero_vendor_volume=int((window.Volume.eq(0)&valid).sum()),
        zero_vendor_volume_pct=100*zrate,flat_ohlc=int(flat.sum()),
        flat_ohlc_pct=100*frate,unadjusted_outliers_gt25pct=int(suspicious),
        daily_adjusted_log_vol=float(ret.std()),grade=grade,
        issuer_share_class_first_date=(str(class_date.date()) if pd.notna(class_date) else ""),
        disallowed_legacy_pre_current_isin_bars=int((z.index<class_date).sum()) if pd.notna(class_date) else 0))
    return stats

def pair_compare(a,b,meta,prices):
    p=prices[a];q=prices[b]
    p=p.loc[STUDY_START:STUDY_END];q=q.loc[STUDY_START:STUDY_END]
    prices_common=pd.DataFrame(dict(a=p.Close,b=q.Close)).dropna()
    n=len(prices_common)
    if n<200:return dict(isin=meta,first=a,second=b,n_common=n,
                         status="INSUFFICIENT_OVERLAP")
    returns=np.log(prices_common).diff().dropna()
    d=(returns.a-returns.b).abs()
    pct=(prices_common.a/prices_common.b-1).abs()
    # SAME-ISIN 2 venues in EUR but very different adjusted base due to
    # different corporate action timing and historical vendor revisions.
    # Use daily RETURNS for price-quality triangulation, not level deviation.
    return dict(isin=meta,first=a,second=b,n_common=n,
       status="SAME_ISIN_VENUE_OVERLAP",
       daily_return_corr=float(returns.a.corr(returns.b)),
       median_absolute_return_difference_bps=float(d.median()*10000),
       p95_abs_return_difference_bps=float(d.quantile(.95)*10000),
       frac_day_return_diff_gt1pct=float((d>.01).mean()),
       frac_day_return_diff_gt2pct=float((d>.02).mean()),
       median_relative_price_level_diff_pct=float(pct.median()*100),
       first_venue_zero_volume_pct=float((p.Volume==0).mean()*100),
       second_venue_zero_volume_pct=float((q.Volume==0).mean()*100))

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    (out/"ISIN_DAILY_ADJUSTED_OHLCV").mkdir()
    official,provenance=download_xetra()
    universe=load_proposals()
    identified=identify(universe,official)
    assert len(identified)>80 and identified.ticker.nunique()==len(identified)
    if not any((identified.ticker=="EXV1.DE")&(identified["isin"]=="DE000A0F5UJ7")):
        raise AssertionError("Canonical EXV1 xetra reference mismatch")
    identified.to_csv(out/"ISIN_ALL_CANDIDATE_REFERENCE_MAPPING.csv",index=False)
    # Output a small local instrument reference snapshot scoped ONLY to
    # matched fund ISINs; do not redistribute all 5,516 exchange instruments.
    ref={t:official.get(t[:-3],[]) for t in identified.ticker if t.endswith(".DE")}
    mini=[dict(ticker=t+".DE",isin=r["ISIN"],name=r["Instrument"],
          reference_currency=r["Currency"],first_trading_date=r["First Trading Date"],
          type=r["Instrument Type"],status=r["Instrument Status"])
          for t,v in ((k[:-3],v) for k,v in ref.items()) for r in v
          if r["ISIN"] in set(identified["isin"]) and r["Instrument Type"]=="ETF"]
    pd.DataFrame(mini).to_csv(out/"OFFICIAL_XETRA_MATCHED_ETF_SECURITY_MASTER.csv",index=False)
    price_data={}
    audit=[]
    for row in identified.itertuples(index=False):
        if not row.isin or row.status in ("IDENTITY_COLLISION","ISIN_CONFLICT_ISSUER_VS_XETRA"):
            audit.append(dict(ticker=row.ticker,isin="",status="NO_VERIFIED_ISIN",
                             reference=row.status,grade="UNRESOLVED_NO_DATA"));continue
        z,source,path=read_prices(row.ticker)
        audit.append(assess(row.ticker,row,z,path,source))
        if z is not None and not z.empty:price_data[row.ticker]=z
    audit=pd.DataFrame(audit)
    audit.to_csv(out/"ALL_QUOTES_WITH_ISIN_HISTORICAL_QUALITY.csv",index=False)
    identified_ok=identified[identified["isin"].str.len()==12]
    mapping=dict(zip(identified_ok.ticker,identified_ok["isin"]))
    grouped=defaultdict(list)
    for t in price_data:
        if t in mapping and check_isin(mapping[t]):grouped[mapping[t]].append(t)
    pairs=[]
    for isin,tickers in sorted(grouped.items()):
        if len(tickers)>=2:
            for j,t in enumerate(tickers):
                for s in tickers[j+1:]:
                    if t==s:continue
                    pairs.append(pair_compare(t,s,isin,price_data))
    pd.DataFrame(pairs,columns=["isin","first","second","n_common","status",
        "daily_return_corr","median_absolute_return_difference_bps",
        "p95_abs_return_difference_bps","frac_day_return_diff_gt1pct",
        "frac_day_return_diff_gt2pct","median_relative_price_level_diff_pct",
        "first_venue_zero_volume_pct","second_venue_zero_volume_pct"]).to_csv(
        out/"INDEPENDENT_TRADING_VENUE_SAME_ISIN_CLOSE_COMPARISON.csv",index=False)
    # Grade selection is on hindsight market data, ONLY as exploratory data
    # QC candidate, not ex-ante investability or live portfolio eligibility.
    eligible=audit[(audit["isin"].str.len()==12)&audit.grade.isin(
                        ("A_QUOTE_CLEAN","B_QUOTE_REVIEW"))].copy()
    eligible["grade_rank"]=eligible.grade.map(
                         {"A_QUOTE_CLEAN":0,"B_QUOTE_REVIEW":1})
    eligible["source_rank"]=eligible.source_quote_type.str.contains(
                   "LEGACY_EU120").astype(int)
    eligible=eligible.sort_values(["isin","grade_rank","zero_vendor_volume_pct",
                 "flat_ohlc_pct","source_rank","ticker"],kind="mergesort")
    unique=eligible.drop_duplicates("isin").copy()
    rows_export=0
    for r in unique.itertuples(index=False):
        src=price_data[r.ticker].copy()
        slice_=src.loc[:STUDY_END].reset_index()
        slice_.insert(0,"isin",r.isin)
        slice_.insert(1,"ticker",r.ticker)
        slice_.insert(2,"venue",VENUE_GROUP.get(r.ticker.rsplit(".",1)[-1],"UNKNOWN"))
        p=out/"ISIN_DAILY_ADJUSTED_OHLCV"/(r.isin+".csv")
        slice_.to_csv(p,index=False,float_format="%.12g")
        rows_export+=len(slice_)
    unique.drop(columns=["grade_rank","source_rank"]).to_csv(
           out/"RESEARCH_QUALITY_SELECTED_ONE_VENUE_PER_ISIN.csv",index=False)
    s=Counter(audit.grade.fillna("UNRESOLVED"))
    statuses=Counter(identified.status)
    all_diff=pd.DataFrame(pairs)
    xtra=identified[(identified.in_original_EUR60)&identified.status.str.startswith("XETRA_")]
    observed_countries=Counter(str(i[:2]) for i in unique["isin"])
    manifest=dict(status="XETRA_OFFICIAL_ISIN_FIRST_HISTORICAL_EU_ETF_QUOTE_BUILD",
        run_date_utc=str(pd.Timestamp.now(tz="UTC")),
        official_reference=provenance,
        n_all_source_ticker_candidates=len(identified),
        identified_count=int((identified["isin"].str.len()==12).sum()),
        euro60_source_XETRA_official_matched=int(len(xtra)),
        euro60_unresolved_or_nonXetra=int(60-len(xtra)),
        euro60_verified_other_venues=int(identified[
            (identified.in_original_EUR60)&identified.status.str.startswith(
                 "SAME_ISIN_CONFIRMED_BY_XETRA_AND_ISSUER")].shape[0]),
        euro60_verified_total_current_isins=int(identified[
            (identified.in_original_EUR60)&identified["isin"].str.len().eq(12)].shape[0]),
        identity_statuses=dict(statuses),
        source_quality_classes=dict(s),
        knowingly_quarantined_pre2018_shareclass=int(
          (audit.grade=="QUARANTINE_PRECLASS_HISTORY").sum()),
        with_parsed_yahoo_OHLCV=len(price_data),
        unique_ISIN_with_any_quotes=len(grouped),
        clean_A_B_one_per_ISIN=int(len(unique)),
        exported_actual_market_quote_rows=rows_export,
        duplicate_isin_with_at_least_two_venues=int(sum(len(v)>=2 for v in grouped.values())),
        venue_price_pair_tests=len(all_diff),
        issuer_domicile_prefixes_observed=dict(observed_countries),
        no_justETF_automated_requests=True,
        no_source_data_synthetic_NAV_used=True,
        pseudo_independent_venues_share_yahoo_vintage=True,
        original_eu120_contributed_low_trust_price_source=True,
        licensed_as_of_2017_fund_universe_not_proven=True,
        not_a_trade_execution_or_model_signal_certification=True,
        source_notes=[
         "Deutsche Boerse official 19-Oct-2026 ISIN mnemonic currency ETF mapping, not 2017 historical listing membership",
         "Data from already-archived original Yahoo vendor sources (raw-to-adjusted OHLC) and legacy EU120 sanitized price bars",
         "Yahoo vol=0 can be vendor reporting gap and Open is not executable without quoted spread/venue proof",
         "One ISIN may have many currency/venue ticker lines; one per ISIN selected for exploratory quality after 2026",
         "Venue return correlations validate agreement in value, do not produce actual independent second price VENDOR",
         "No justETF website scraping, no undocumented justETF performance API access",
         "Non-Xetra EUR60 tickers without issuer-backed legal IDs intentionally stay unmatched",
         "No ex-post ETF Trader F3 H1 retraining; development roster date biases remain."
        ])
    (out/"RESULT.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
        sha(p)+"  "+str(p.relative_to(out))+"\n"
        for p in sorted(out.rglob("*.csv")))+
        sha(out/"RESULT.json")+"  RESULT.json\n")
    print("ISIN_FIRST_SUCCESS "+json.dumps(manifest),flush=True)
    return manifest

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    run(p.parse_args().out)
