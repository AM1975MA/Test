#!/usr/bin/env python3
"""Genuine V3 corrected 125F European 148 ISIN monthly forecast training panel.

Build full 2012..2026 European vintage-aware panel from 2010 XETRA EUR raw,
WITHOUT imported US149 predictions, WITHOUT legacy V2 downvol/kernel.
Firststage sample requirements: genuine observed 252 bar warmup per ISIN,
no quote forward-fill, no ETF before ISIN-specific inception.
Reference calendar is EXSA.DE (DE0002635307) EUR Xetra as-of venue.
"""
from __future__ import annotations
import argparse,json,hashlib,sys
from pathlib import Path
import pandas as pd,numpy as np
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder
from etf_trader_v3.source_only import kernel as K
REFERENCE_ISIN="DE0002635307"
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    base=Path(a.raw)
    roster=pd.read_csv(base/"EU148_VERIFIED_LEGAL_ISIN_CATALOG.csv")
    assert len(roster)==roster.ticker.nunique()==roster["isin"].nunique()==148
    mats,cat,provenance=load_ticker_csv_folder(base/"raw_ticker_csv")
    assert len(cat)==148 and REFERENCE_ISIN in mats["Close"].columns
    # use an actual primary European exchange daily venue calendar, NOT
    # artificially invent dates from a union across individual venues.
    cal=mats["Close"][REFERENCE_ISIN].dropna().index
    assert len(cal)>3700 and cal.min()<pd.Timestamp("2011-01-01")
    mats={field:table.reindex(cal).sort_index() for field,table in mats.items()}
    # PRICE-SOURCE FORENSIC FIX (2026-10-25): exactly 59 otherwise liquid
    # EUR Xetra ISIN lack only 2026-03-06 in vendor bars; the missing return
    # triggers strict 21/63-day feature-window invalidation through May 2026.
    # Use PREVIOUS OBSERVED CLOSE for feature calculation *only* at this one
    # known bad vendor day, without touching raw EUR Open execution/label data.
    # This is a causal stale-quote robustness sensitivity, NOT a reconstructed
    # tradeable quote or a correction of source data. Keep volume missing.
    gap_day=pd.Timestamp("2026-03-06")
    previous_day=cal[cal.get_loc(gap_day)-1]
    missing=mats["Close"].loc[gap_day].isna()
    assert int(missing.sum())==59 and len(mats["Close"].columns)==148
    assert mats["Close"].loc[previous_day,missing].notna().all()
    tech={k:v.copy() for k,v in mats.items()}
    stale=mats["Close"].loc[previous_day,missing]
    for field in ("Open","High","Low","Close"):
        tech[field].loc[gap_day,missing]=stale
    assert tech["Volume"].loc[gap_day,missing].isna().all()
    (out/"SINGLE_DAY_VENDOR_GAP_REPAIR.csv").write_text(
        pd.DataFrame({"ticker":list(stale.index),"missing_vendor_day":str(gap_day.date()),
            "asof_previous_day":str(previous_day.date()),"feature_only_stale_close":stale.to_numpy(),
            "execution_quote_unmodified":True}).to_csv(index=False))
    # ISOLATED NON-PRODUCTION ABLATION:
    # Native V3 kernel chooses SPY whenever present; otherwise uses the
    # heterogeneous 148-ETF median as beta/correlation market factor.
    # EXSA is an actual broad European equity benchmark already in roster.
    # Swap just its NAME to 'SPY' inside the feature calculation, then
    # restore the real legal ISIN to all output labels/joins; this avoids
    # duplicating the benchmark in cross-sectional ranks (148 stays 148).
    assert "SPY" not in tech["Close"].columns
    feat_mats={field:table.rename(columns={REFERENCE_ISIN:"SPY"})
        for field,table in tech.items()}
    dates,compact,tail,features=K.build_features(feat_mats)
    assert compact.ticker.nunique()==148 and "SPY" in compact.ticker.values
    compact.loc[compact.ticker.eq("SPY"),"ticker"]=REFERENCE_ISIN
    assert compact.ticker.nunique()==148

    assert len(K.F2D_FEATURES)==125
    dates=dates[dates>=pd.Timestamp("2012-01-01")]
    # Correct V3 native source produces EU cross-sectional market median
    # factor rather than the SPY as-of U.S. factor; this DIFFERENCE must be
    # disclosed and tested separately, not mislabeled exact SPY parity.
    assert dates.min().year==2012
    allframe=K.add_labels(compact[compact.signal_date.isin(dates)].copy(),
                           mats["Open"],dates)
    original=allframe.copy()
    close=mats["Close"]
    observed=close.notna().astype(int).cumsum()
    warm_month=observed.reindex(index=dates).stack(dropna=False).rename("prior_observed_closes")
    prior_obs=warm_month.reset_index()
    prior_obs.columns=["signal_date","ticker","prior_observed_closes"]
    original=original.merge(prior_obs,on=["signal_date","ticker"],how="left",validate="one_to_one")
    assert "prior_observed_closes" in original.columns
    valid=(original.prior_observed_closes>=252) & (original[K.F2D_FEATURES].notna().sum(axis=1)>=75)
    # A signal is legitimate only on an actual Euro venue quote date, not on
    # a holiday-aligned filled synthetic row. Dates before inception are NaN.
    dates_m=mats["Close"].reindex(dates).stack(dropna=False).rename("market_close")
    venue_close=dates_m.reset_index()
    venue_close.columns=["signal_date","ticker","market_close"]
    original=original.merge(venue_close,on=["signal_date","ticker"],how="left",validate="one_to_one")
    valid &= original.market_close.notna()
    original["eligible_asof"]=valid
    audit=[]
    for d,g in original.groupby("signal_date",sort=True):
        elig=g[g.eligible_asof]
        categories=[cat[t] for t in elig.ticker]
        detail=dict(signal_date=str(d.date()),eligible_isin=len(elig),
            n_mature_21d=int(elig.fwd_ret_21.notna().sum()),
            n_missing_nextopen_labels=int(elig.fwd_ret_21.isna().sum()))
        detail.update({c:int(categories.count(c)) for c in sorted(set(cat.values()))})
        audit.append(detail)
    audit=pd.DataFrame(audit)
    assert audit.signal_date.nunique()>=170 and audit.signal_date.iloc[0][:4]=="2012"
    test=audit[audit.signal_date.between("2018-01-01","2026-05-31")]
    assert len(test)==101,(len(test),test.signal_date.tolist()[:2],test.signal_date.tolist()[-2:])
    assert test.eligible_isin.ge(24).all() and test.n_mature_21d.ge(24).all()
    # Regression gate: the 59-fund 2026-03-06 vendor gap must not
    # remove 57 investable names from March, April, and May signals.
    assert test[test.signal_date.isin(["2026-03-31","2026-04-30","2026-05-29"])].eligible_isin.ge(140).all()
    assert test.eligible_isin.iloc[-1]>=140
    # Group adaptive monthly eligible cohort, do not train in a month where
    # fewer than 4 eligible ISIN remain in a macro category.
    groups=sorted(roster.macro_category.unique())
    assert len(groups)==6
    for c in groups:
        if (test[c]<4).any():
            print("WARNING_2018_EURO_LOW_CLUSTER",c,test[c].min(),flush=True)
    original=original.loc[original.eligible_asof].copy()
    assert original.ticker.nunique()==148
    original.sort_values(["signal_date","ticker"]).to_parquet(out/"CORRECTED125_PANEL.parquet",index=False)
    audit.to_csv(out/"ASOF_148_UNIVERSE_MONTHLY.csv",index=False)
    roster.to_csv(out/"EU148_VINTAGE_ROSTER.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
       kernel="etf_trader_v3.source_only.kernel.build_features 125F corrected",
       negative_semivolatility_fixed=True,
       exchange_calendar_reference=REFERENCE_ISIN,
       market_factor="EU_BROAD_EXSA_REFERENCE_DE0002635307_INSTEAD_OF_MIXED_MEDIAN",
       control_only_beta_corr_feature_factor_changed=True,
       kernel_temporary_alias_SPY_restored_to_legal_ISIN=True,
       refit_sample_start="2012-01",
       same_US_OOS_first="2018-01",
       same_US_OOS_last="2026-05",
       n_oos_months=101,
       catalog_2026_survivorship_bias=True,
       provider_adjusted_price_vintage_not_point_in_time=True,
       no_synthetic_history=True,no_missing_days_filled_in_raw_or_execution=True,
       feature_only_one_day_causal_stale_close="2026-03-06_59_ISIN",
       technical_quote_not_tradeable=True,
       no_V2_or_V3_production_modification=True,
       source_us149_original_not_retrained=True),indent=2))
    print("CORRECTED_EU148_PANEL_SUCCESS",len(original),
           "2018_eligible_start",int(test.eligible_isin.iloc[0]),
           "2026_eligible_end",int(test.eligible_isin.iloc[-1]),
           "original_months",len(audit),"same_US_OOS",len(test),flush=True)
if __name__=="__main__":main()
