#!/usr/bin/env python3
"""Paired US149/EU148 fully native corrected 125F feature/label panel.

Both markets use exactly the SPY/EXSA calendar INTERSECTION, monthly last
joint session, 21 subsequent common sessions for training labels. Only
original USD price features for US, EUR price features for EU. Legitimate
EU 2026 one-day feature-only stale repair; trade quotes untouched.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from etf_trader_v3.source_only import kernel as K

def read(folder,roster):
    mats={}
    for field in ("Open","High","Low","Close","Volume"):
        a={}
        for ticker in roster.ticker:
            f=Path(folder)/(ticker+".csv")
            assert f.is_file(),f
            d=pd.read_csv(f,parse_dates=["date"]).drop_duplicates("date",keep="last").set_index("date").sort_index()
            a[ticker]=d[field]
        mats[field]=pd.concat(a,axis=1).sort_index()
    return mats

def main():
    p=argparse.ArgumentParser();p.add_argument("--us",required=True);p.add_argument("--eu",required=True)
    p.add_argument("--out",required=True);a=p.parse_args()
    us=pd.read_csv(Path(a.us)/"universe.csv")
    eu=pd.read_csv(Path(a.eu)/"EU148_VERIFIED_LEGAL_ISIN_CATALOG.csv")
    assert len(us)==us.ticker.nunique()==149 and len(eu)==eu.ticker.nunique()==148
    print("READ_US_149",flush=True)
    U=read(a.us,us)
    print("READ_EU_148",flush=True)
    E=read(Path(a.eu)/"raw_ticker_csv",eu)
    common=U["Close"]["SPY"].dropna().index.intersection(E["Close"]["DE0002635307"].dropna().index).sort_values()
    common=common[(common>=pd.Timestamp("2010-01-01"))&(common<=pd.Timestamp("2026-07-01"))]
    assert len(common)>3900 and common[-1]==pd.Timestamp("2026-07-01")
    save=Path(a.out);save.mkdir(parents=True,exist_ok=True)
    monthdates=pd.Series(common,index=common)
    monthdates=monthdates.loc["2018-01-01":"2026-05-31"].groupby(monthdates.loc["2018-01-01":"2026-05-31"].index.to_period("M")).last()
    assert len(monthdates)==101 and monthdates.iloc[0]==pd.Timestamp("2018-01-31") and monthdates.iloc[-1]==pd.Timestamp("2026-05-29")
    monthdates.rename("common_signal_date").to_csv(save/"PAIRED_COMMON_101_SIGNAL_DATES.csv")
    for market,mats,roster in (("US149",U,us),("EU148",E,eu)):
        print("BUILD_REAL_V3_125",market,flush=True)
        mats={k:v.reindex(common) for k,v in mats.items()}
        technical={k:v.copy() for k,v in mats.items()}
        repaired=0
        if market=="EU148":
            gap=pd.Timestamp("2026-03-06")
            assert gap in common
            prev=common[common.get_loc(gap)-1]
            missing=mats["Close"].loc[gap].isna()
            repaired=int(missing.sum())
            assert 50<=repaired<=65,repaired
            stale=mats["Close"].loc[prev,missing]
            assert stale.notna().all()
            for f in ("Open","High","Low","Close"):
                technical[f].loc[gap,missing]=stale
            assert technical["Volume"].loc[gap,missing].isna().all()
        dates,compact,tail,full=K.build_features(technical)
        assert len(K.F2D_FEATURES)==125 and len(dates)>150
        dates=dates[(dates>=pd.Timestamp("2012-01-01"))&(dates<=pd.Timestamp("2026-05-31"))]
        native=K.add_labels(compact[compact.signal_date.isin(dates)].copy(),mats["Open"],dates)
        # Group labels in final fit only, based on past matured forward21.
        observed=mats["Close"].notna().astype(int).cumsum()
        seen=observed.reindex(dates).stack(dropna=False).rename("seen").reset_index()
        seen.columns=["signal_date","ticker","seen"]
        visible=mats["Close"].reindex(dates).stack(dropna=False).rename("visible_close").reset_index()
        visible.columns=["signal_date","ticker","visible_close"]
        native=native.merge(seen,on=["signal_date","ticker"],how="left",validate="one_to_one")
        native=native.merge(visible,on=["signal_date","ticker"],how="left",validate="one_to_one")
        eligible=native.seen.ge(252)&native.visible_close.notna()&native[list(K.F2D_FEATURES)].notna().sum(axis=1).ge(75)
        native=native[eligible].copy()
        native=native.sort_values(["signal_date","ticker"]).reset_index(drop=True)
        assert native.ticker.nunique()==len(roster)
        osa=native[native.signal_date.between("2018-01-01","2026-05-31")]
        assert osa.signal_date.nunique()==101
        assert osa.groupby("signal_date").ticker.nunique().ge(25).all()
        assert (osa.groupby("signal_date").ticker.nunique().loc[pd.Timestamp("2026-05-29")]>=140)
        assert list(osa.signal_date.drop_duplicates())==list(monthdates.to_numpy())
        result=save/market;result.mkdir(exist_ok=True)
        native.to_parquet(result/"CORRECTED125_PANEL.parquet",index=False)
        grp=native.groupby("signal_date").agg(n_eligible=("ticker","nunique"),n_mature_21d=("fwd_ret_21","count")).reset_index()
        grp.to_csv(result/"ASOF_MONTHLY.csv",index=False)
        (result/"MANIFEST.json").write_text(json.dumps(dict(
          market=market,roster=len(roster),n_rows=len(native),n_2018plus=len(osa),
          corrected_native_125=True,price_ccy="USD" if market=="US149" else "EUR",
          market_factor="SPY_NATIVE_USD" if market=="US149" else "CROSS_SECTION_EUR_MEDIAN",
          common_calendar=True,common_sessions_per_target=21,n_common_signals=101,
          same_training_start_2012=True,one_day_gap_feature_only= "2026-03-06" if repaired else None,
          n_feature_only_stale_quote_repairs=repaired,
          execution_prices_always_original=True,
          label_use_is_only_in_matured_training=True,
          no_future_label_test_filter=True,universe_vintage_252_actual_closes=True
        ),indent=2))
        print("NATIVE_V3_125_PAIRED_PANEL_PASS",market,len(native),
              "FIRST_OS",osa.groupby("signal_date").ticker.nunique().iloc[0],
              "LAST_OS",osa.groupby("signal_date").ticker.nunique().iloc[-1],flush=True)
if __name__=="__main__":main()
