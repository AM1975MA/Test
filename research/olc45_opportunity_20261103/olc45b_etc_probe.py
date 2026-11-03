#!/usr/bin/env python3
"""OLC45-B: public-price ETC pre-screen on same E1 frozen monthly calendar.
Only ex-post opportunity, never CAGR / model backtest. Treat ETC separately from UCITS.
"""
from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results_ETC";OUT.mkdir(exist_ok=True)
BASE=ROOT.parent/"sector_opportunity_e1_20261103"/"baseline_oracle_2021_2024.csv"
ART=ROOT/"source_artifact"
TICKERS={
"VZLC.DE":("JE00B1VS3333","SILVER_PHYSICAL_ETC","XETRA_EUR"),
"PHAG.MI":("JE00B1VS3333","SILVER_PHYSICAL_ETC","MILAN_EUR_ALTERNATE_SAME_ISIN"),
"NGAS.MI":("JE00BN7KB334","NATURAL_GAS_FUTURES_ETC","MILAN_EUR"),
"OD7L.DE":("JE00BN7KB334","NATURAL_GAS_FUTURES_ETC","XETRA_EUR_ALTERNATE_SAME_ISIN"),
}
PREFER={"JE00B1VS3333":("VZLC.DE","PHAG.MI"),
        "JE00BN7KB334":("NGAS.MI","OD7L.DE")}
MIN_OBS=500

def get_prices(ticker):
    df=yf.download(ticker,start="2017-01-01",end="2025-02-15",
                   auto_adjust=True,threads=False,progress=False,interval="1d")
    if df is None or df.empty:raise ValueError("No Yahoo daily data")
    if isinstance(df.columns,pd.MultiIndex):
        df.columns=df.columns.get_level_values(0)
    df=df.rename(columns={c:c.lower() for c in df.columns})
    idx=pd.DatetimeIndex(df.index)
    if idx.tz is not None:idx=idx.tz_localize(None)
    df.index=idx.normalize()
    df=df[["open","high","low","close","volume"]].apply(pd.to_numeric,errors="coerce")
    df=df[(df.open>0)&(df.close>0)&np.isfinite(df.open)&np.isfinite(df.close)]
    if df.index.has_duplicates:raise ValueError("Duplicates")
    return df.sort_index()

def main():
    orig=pd.read_csv(BASE)
    assert orig[orig.market=="EU"].shape[0]==48
    c=pd.read_csv(ART/"candidate_monthly_labels.csv")
    c=c[(c.market=="EU")&c.ticker.isin(["G2X.DE","USPY.DE","WTIC.DE","2B76.DE"])]
    assert c.groupby("signal_date").size().eq(4).all()
    sets=c.groupby("signal_date").apply(
        lambda x:dict(zip(x.ticker,x.candidate_logbp)),include_groups=False
    ).to_dict()
    eu=orig[orig.market=="EU"].copy()
    hist={};quality=[]
    for ticker,(isin,theme,venue) in TICKERS.items():
        try:
            d=get_prices(ticker)
            bad=((d.low>d.high)|(d.low>d.open)|(d.low>d.close)|
                 (d.high<d.open)|(d.high<d.close))
            daily_jump=np.abs(np.log(d.close/d.close.shift(1)))
            hist[ticker]=d
            quality.append(dict(ticker=ticker,isin=isin,theme=theme,venue=venue,
                      status="quote_download_ok",n_dates=len(d),first=str(d.index.min().date()),
                      last=str(d.index.max().date()),ohlc_bad=int(bad.sum()),
                      daily_jumps_over_60pct=int((daily_jump>np.log(1.6)).sum()),
                      max_abs_close_logjump=float(daily_jump.max())))
        except Exception as e:
            quality.append(dict(ticker=ticker,isin=isin,theme=theme,venue=venue,
                                status="missing",error=repr(e)))
    pd.DataFrame(quality).to_csv(OUT/"etc_quote_quality.csv",index=False)
    rows=[]
    for r in eu.itertuples(index=False):
        sig=pd.Timestamp(r.signal_date);en=pd.Timestamp(r.entry_date);ex=pd.Timestamp(r.exit_date)
        old_first=float(r.oracle_top1_logbp)
        base4=max([old_first]+list(sets[r.signal_date].values()))
        old_second=2*float(r.oracle_top2_logbp)-old_first
        base4_top2=np.mean(sorted([old_first,old_second]+list(sets[r.signal_date].values()),reverse=True)[:2])
        newvals={}
        for isin,venues in PREFER.items():
            for v in venues:
                if v not in hist:continue
                d=hist[v]
                prior=int((d.index<sig).sum())
                if prior<MIN_OBS or en not in d.index or ex not in d.index:continue
                z=10000*np.log(float(d.loc[ex,"open"]/d.loc[en,"open"]))
                newvals[isin]=(v,z,prior);break # only one venue per ISIN
        validlist=[z for v,z,_ in newvals.values()]
        newbest=max([base4]+validlist)
        newtop2=np.mean(sorted([old_first,old_second]+list(sets[r.signal_date].values())+validlist,reverse=True)[:2])
        leader=max(newvals,key=lambda isin:newvals[isin][1]) if newvals else None
        leader=(leader if leader and newvals[leader][1]>base4 else "")
        rows.append(dict(signal_date=r.signal_date,entry_date=r.entry_date,exit_date=r.exit_date,
                         original_top1_logbp=old_first,ucits4_top1_logbp=base4,
                         ucits4_top2_logbp=base4_top2,
                         n_ETC_eligible=len(newvals),
                         etc_plus_ucits4_top1_logbp=newbest,
                         etc_plus_ucits4_top2_logbp=newtop2,
                         incremental_top1_logbp=newbest-base4,
                         incremental_top2_logbp=newtop2-base4_top2,
                         new_winning_etc_isin=leader,
                         silver_etc_bp=newvals.get("JE00B1VS3333",(None,np.nan,None))[1],
                         gas_etc_bp=newvals.get("JE00BN7KB334",(None,np.nan,None))[1],
                         silver_primary_venue=newvals.get("JE00B1VS3333",("",np.nan,None))[0],
                         gas_primary_venue=newvals.get("JE00BN7KB334",("",np.nan,None))[0]))
    df=pd.DataFrame(rows)
    df.to_csv(OUT/"olc45b_etc_monthly.csv",index=False)
    s=df.agg({"n_ETC_eligible":["min","mean","max"],
              "incremental_top1_logbp":["mean","sum","max"],
              "incremental_top2_logbp":["mean","sum","max"]})
    summary=pd.DataFrame([{
        "months":len(df),
        "months_eligible_both_etc":int((df.n_ETC_eligible==2).sum()),
        "new_winner_months":int((df.incremental_top1_logbp>1e-8).sum()),
        "silver_best_months":int((df.new_winning_etc_isin=="JE00B1VS3333").sum()),
        "gas_best_months":int((df.new_winning_etc_isin=="JE00BN7KB334").sum()),
        "incremental_top1_mean_logbp_per_month":float(df.incremental_top1_logbp.mean()),
        "incremental_top2_mean_logbp_per_month":float(df.incremental_top2_logbp.mean()),
        "gross_only":True,
        "risk_quote_inconsistency_detected":sum(int(r.get("ohlc_bad",0)) for r in quality),
    }])
    summary.to_csv(OUT/"olc45b_etc_summary.csv",index=False)
    vols=df[["silver_etc_bp","gas_etc_bp"]].corr()
    (OUT/"etc_cross_correlations.json").write_text(json.dumps({
         "silver_vs_gas_monthly_returns_corr":float(vols.iloc[0,1]),
         "n_months_both_with_prices":int(df[["silver_etc_bp","gas_etc_bp"]].dropna().shape[0])},indent=2))
    print("=== ETC quote quality ===")
    print(pd.DataFrame(quality).to_string(index=False),flush=True)
    print("=== ETC opportunity, EX-POST only ===")
    print(summary.to_string(index=False),flush=True)
    (OUT/"manifest.json").write_text(json.dumps({
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "source_calendar":"frozen OLC32 48 EU months 2021-2024",
        "primary_venues":{"silver":"VZLC.DE","gas":"NGAS.MI"},
        "alternative_venue_isin_dedup":PREFER,"min_prior_observed":MIN_OBS,
        "pricing":"Yahoo adjusted Open exact entry/exit, NO forward fill",
        "no_ETC_in_production":True,
        "caveats":["ETC legal structure and futures roll/spot risk",
                   "source-adjusted vintage is not broker verified",
                   "venue and ISIN history must be PIT verified",
                   "maturity of old labels never used for strategy",
                   "ex-post upper bound, no new CAGR or predictive skill"],
    },indent=2))
if __name__=="__main__":main()
