#!/usr/bin/env python3
"""Assemble 148 distinct European ETF ISIN, preserve true 2010-2026 vintages.

6 macro clusters; exactly 100 new price-verified + 48 already certified original.
Price bars are observed on specific EUR Xetra venues; don't forward fill missing
days, don't make before-inception synthetic prices. First admitted signal needs
>=252 genuinely observed sessions on/after exact legal Xetra trading date.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import pandas as pd,numpy as np
CLUSTERS=("EU_EQUITY_BROAD","EU_EQUITY_SECTOR","EU_EQUITY_COUNTRY",
          "EU_EQUITY_FACTOR","SOVEREIGN_EUR","EU_PROPERTY")
QUOTAS=(16,22,21,18,18,5)
DATE_START=pd.Timestamp("2010-01-01")
FIRST_SIGNAL=pd.Timestamp("2018-01-31")
LAST_SIGNAL=pd.Timestamp("2026-05-29")
COLS=["Open","High","Low","Close","Volume"]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--original",required=True)
    ap.add_argument("--oldref",required=True)
    ap.add_argument("--newroot",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    universe=out/"raw_ticker_csv";universe.mkdir(exist_ok=True)
    oldref=pd.read_csv(args.oldref);assert len(oldref)==oldref["isin"].nunique()==48
    oldpass=pd.read_csv(Path(args.original)/"ORIGINAL48_PRICE_PASS.csv")
    if not (out/"CHECKPOINT.txt").exists(): (out/"CHECKPOINT.txt").write_text("Research only; original prices and production never overwritten.\n")
    allparts=[];records=[];quality=[]
    for cl,quota in zip(CLUSTERS,QUOTAS):
        src=Path(args.newroot)/cl
        accept=pd.read_csv(src/"PRICE_QUALITY_PASS.csv")
        selected=pd.read_csv(src/"SELECTED_LEGAL_ISIN.csv")
        assert len(accept)==len(selected)==quota,(cl,len(accept),len(selected),quota)
        assert accept["isin"].is_unique and selected["isin"].is_unique
        for a in accept.to_dict("records"):
            isin=a["isin"];q=src/"raw_by_isin"/(isin+".csv")
            assert sha(q)==a["price_sha256"]
            df=pd.read_csv(q,parse_dates=["date"])
            assert len(df)==a["n_bars"]
            records.append(dict(isin=isin,ticker=str(a["ticker"]),macro_category=cl,
                source_type="new_100_verified",historical_first_vendor_bar=a["first_vendor_bar"],
                venue_date=a["first_xetra_bar"],europe_exposure_2026=a["europe_exposure_percent_2026"],
                first_trade_date=a["earliest_legal_price"],
                execution_liquidity_certified=bool(a["execution_liquidity_certified"]),
                yahoo_volume_zeros=a["zero_volume_fraction"],old_certified=False,
                source_sha256=sha(q)))
            allparts.append((isin,df))
    assert len(records)==100
    newISIN={r["isin"] for r in records}
    for a in oldref.to_dict("records"):
        isin=a["isin"];cl=a["benchmark_bucket"]
        assert cl in CLUSTERS and isin not in newISIN
        recent=Path(args.original)/"original48_raw_by_isin"/(isin+".csv")
        if recent.exists():
            d=pd.read_csv(recent,parse_dates=["date"])
            typ="existing48_true_xetra_refetch"
            venue=oldpass.loc[oldpass["isin"].eq(isin)].iloc[0]["first_xetra_bar"]
        else:
            d=pd.read_csv(Path(args.oldref).parent/"isin_daily_ohlcv_eur"/(isin+".csv"),parse_dates=["date"])
            typ="existing48_2016_certified_original"
            venue=str(d.date.iloc[0].date())
        assert len(d)>=400,(isin,len(d))
        key=str(a["ticker"])
        records.append(dict(isin=isin,ticker=key,macro_category=cl,
            source_type=typ,historical_first_vendor_bar=str(d.date.iloc[0].date()),
            venue_date=str(venue),europe_exposure_2026=100.,
            first_trade_date=str(max(pd.Timestamp(d.date.iloc[0]),pd.Timestamp(venue)).date()),
            execution_liquidity_certified=bool(typ=="existing48_2016_certified_original"),
            yahoo_volume_zeros=np.nan,old_certified=True,
            source_sha256=sha(recent) if recent.exists() else sha(Path(args.oldref).parent/"isin_daily_ohlcv_eur"/(isin+".csv"))))
        allparts.append((isin,d))
    assert len(records)==148 and len(set(d["isin"] for d in records))==148
    counts=pd.DataFrame(records).macro_category.value_counts()
    assert all(counts.loc[k]>=8 for k in CLUSTERS),counts.to_dict()
    rows=[]
    for rec,(isin,d) in zip(records,allparts):
        d=d.drop_duplicates("date").sort_values("date")
        assert (d.date<=pd.Timestamp("2026-10-24")).all()
        first=pd.Timestamp(rec["first_trade_date"])
        # Old certified quotes kept as they are; current external vintage
        # strictly cannot precede the venue's legal first quote date.
        d=d.loc[d.date>=first].copy()
        # Quarantine two independently observed PRE-2018 vendor discontinuities.
        # No split data available for XASX: rather than assume a corporate
        # conversion factor for the 2015-07-30 permanent +43.6% jump on zero
        # volume, discard its older unhomogeneous price vintage altogether.
        # Both instruments remain in EU148 for eligible as-of 2018+ testing.
        rec["historical_vendor_quarantine"]=None
        if isin=="LU0292097747":
            pre=d[d.date==pd.Timestamp("2015-07-29")]
            post=d[d.date==pd.Timestamp("2015-07-30")]
            assert len(pre)==len(post)==1 and int(post.Volume.iloc[0])==0
            assert 1.40<float(post.Close.iloc[0]/pre.Close.iloc[0])<1.48
            d=d[d.date>=pd.Timestamp("2015-07-30")].copy()
            rec["historical_vendor_quarantine"]="before_2015-07-30_unresolved_xasx_zero_volume_level_break"
        if isin=="LU0274209237":
            bad=d[d.date==pd.Timestamp("2014-11-06")]
            prev=d[d.date==pd.Timestamp("2014-11-05")]
            nxt=d[d.date==pd.Timestamp("2014-11-07")]
            assert len(bad)==len(prev)==len(nxt)==1
            assert int(bad.Volume.iloc[0])==0
            assert float(bad.Close.iloc[0]/prev.Close.iloc[0])>1.20
            assert abs(float(nxt.Close.iloc[0]/prev.Close.iloc[0])-1)<0.03
            # Remove a proven isolated non-executable 0-volume quote.
            # Reindex later leaves genuine NaN; no interpolation/price fill.
            d=d[d.date!=pd.Timestamp("2014-11-06")].copy()
            rec["historical_vendor_quarantine"]="2014-11-06_single_zero_volume_xmeu_transient_quote"
        # KNOWN CORPORATE ACTION (BNP Paribas Easy prospectus, April 2020):
        # LU0192223062 QD-DIS share class was split 26-for-1 on 2018-07-06.
        # Vendor unadjusted pre-split OHLC create a fictitious ~-96% daily
        # loss, corrupting 21D labels and EU148 cross-sectional features.
        # Work only on derived research bars, never on archived provider raw.
        rec["corporate_action_split_adjusted"]=False
        if isin=="LU0192223062":
            split_date=pd.Timestamp("2018-07-06")
            prior=d[d.date<split_date]
            later=d[d.date>=split_date]
            assert len(prior)>120 and len(later)>120,isin
            before=float(prior.Close.iloc[-1])
            after=float(later.Close.iloc[0])
            assert 24.0<before/after<28.0,(isin,before,after)
            mask=d.date<split_date
            for f in ("Open","High","Low","Close"):
                d.loc[mask,f]=d.loc[mask,f]/26.0
            # Proportional share-unit adjustment preserves EUR volume notional.
            d.loc[mask,"Volume"]=d.loc[mask,"Volume"]*26.0
            rec["corporate_action_split_adjusted"]=True
            rec["split_effective_date"]="2018-07-06"
            rec["split_factor_new_shares_per_old_share"]=26
            rec["split_source"]="https://www.ciireland.com/wp-content/uploads/2019/09/BNP-PARIBAS_Prospectus_042020.pdf"
            rec["pre_split_close_raw"]=before
            rec["post_split_close_raw"]=after
            rec["pre_split_close_backadjusted"]=before/26.0
        arr=d[COLS[:4]].to_numpy(float)
        assert len(d)>300 and (np.isfinite(arr)&(arr>0)).all(),isin
        assert d.date.is_monotonic_increasing and d.date.is_unique
        d=d[["date"]+COLS].copy()
        # Catch unadjusted nominal corporate events before modeling returns.
        z=d[d.date>=pd.Timestamp("2018-01-01")].Close.pct_change(fill_method=None).abs()
        if z.max()>0.40:
            raise RuntimeError(f"Unresolved >40% single-day return in EUR adjusted ISIN {isin}: {z.max():.4f}")
        # Preserve authentic EUR Open/Close except source-documented split
        # adjustment above; only correct derived High/Low
        # containing historical vendor OHLC envelope errors. Separately log
        # every change; original source files are never overwritten.
        invalid=(d.Low>d[["Open","Close"]].min(axis=1)+1e-8)|(
                 d.High<d[["Open","Close"]].max(axis=1)-1e-8)
        nbad=int(invalid.sum())
        if nbad/len(d)>.01:raise RuntimeError(f"Bad price envelope over 1% for {isin}: {nbad}")
        if nbad:
            d["High"]=np.maximum(d.High,d[["Open","Close"]].max(axis=1))
            d["Low"]=np.minimum(d.Low,d[["Open","Close"]].min(axis=1))
        rec["derived_OHLC_envelope_fixes"]=nbad
        d.date=d.date.dt.strftime("%Y-%m-%d")
        # Filename by legal ISIN so exchange ticker changes do not split a fund.
        q=universe/(isin+".csv")
        d.to_csv(q,index=False,float_format="%.12g")
        rec["total_bars"]=len(d)
        rec["first_observed"]=str(d.date.iloc[0])
        rec["last_observed"]=str(d.date.iloc[-1])
        rec["n_pre2012"]=int((pd.to_datetime(d.date)<pd.Timestamp("2012-01-01")).sum())
        rec["n_2012"]=int(pd.to_datetime(d.date).dt.year.eq(2012).sum())
        rec["n_2017"]=int(pd.to_datetime(d.date).dt.year.eq(2017).sum())
        rec["n_2018"]=int(pd.to_datetime(d.date).dt.year.eq(2018).sum())
        rec["research_price_sha256"]=sha(q)
        rows.append(rec)
    roster=pd.DataFrame(rows)
    assert roster["isin"].is_unique
    assert roster["macro_category"].nunique()==6
    # Explicit legal ISIN as unique ticker; do not silently conflate
    # multiple Xetra tickers or same product across exchange venues.
    roster["venue_ticker"]=roster.pop("ticker")
    roster.insert(0,"ticker",roster["isin"])
    roster.to_csv(out/"EU148_VERIFIED_LEGAL_ISIN_CATALOG.csv",index=False)
    roster[["ticker","macro_category"]].to_csv(universe/"universe.csv",index=False)
    source_cut=roster[roster.n_pre2012.ge(126)&roster.n_2012.ge(180)]
    source_cut.to_csv(out/"AVAILABLE_PRE2012_FULL_WARMUP.csv",index=False)
    for dt in pd.date_range(FIRST_SIGNAL,LAST_SIGNAL,freq="ME"):
        # Snapshot eligibility is computed in the next stage from actually
        # observed signal month and full 252-session warmup per legal ISIN.
        prior=roster[roster.first_observed.le(dt.strftime("%Y-%m-%d"))]
        quality.append(dict(asof_calendar_month=dt.strftime("%Y-%m"),
             existing_funds=len(prior),
             existing_by_cluster=json.dumps(prior.macro_category.value_counts().to_dict())))
    pd.DataFrame(quality).to_csv(out/"VINTAGE_COHORT_COUNTS.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
        original_48=48,new_100=100,unique_legal_isin=148,
        documented_share_split_repairs=[{"isin":"LU0192223062","ratio":26,"date":"2018-07-06"}],
        raw_vendor_files_unchanged=True,
        pre_2018_vendor_quarantines=["LU0292097747_before_2015-07-30","LU0274209237_2014-11-06"],
        all_6_cluster_counts=counts.to_dict(),pre2012_genuine_126_warmup=int(len(source_cut)),
        reference_first_model_month="2018-01",
        last_same_US_OOS_month="2026-05",
        original_market_universe=149,comparison_US_OOS_months=101,
        legal_isin_vintage_respected=True,
        no_synthetic_pre_inception_history=True,
        no_quote_interpolation=True,
        cluster_vintage_changes_by_month=True,
        some_vendor_volume_unverified=True,
        no_provider_PIT_survivor_control=True,
        no_backtest_ran_in_builder=True,
        production_changed=False,
        files=roster[["isin","research_price_sha256"]].to_dict("records")),indent=2))
    print("EU148_COHORT_PRICE_PASS",len(roster),"PRE2012_126WARM",len(source_cut),"counts",counts.to_dict(),flush=True)
if __name__=="__main__":main()
