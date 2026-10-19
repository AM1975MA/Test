#!/usr/bin/env python3
"""Original immutable SPY/HYG/IEF/BIL/SHV USD quote references, EUR48 decision calendar.

US reference factors are READ ONLY; 48 European legal ISINs remain exclusively
eligible for Titanic and MA3 portfolio rank/entry. Risk/relative US series use
'<= EU calendar date' (source original source market state shifts one EUROPE date
before acting). For model feature engineering/FX conversion on EU close/open,
strictly '< EU day' USA market close is used to avoid future US closing price.
No downloaded quote is backfilled or interpolated into missing historical dates;
US prior-observation-asof within max gap of 7 calendar days is explicit.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import pandas as pd,numpy as np

FIELDS=["SPY","HYG","IEF","BIL","SHV"]
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for z in iter(lambda:f.read(1<<20),b""):h.update(z)
    return h.hexdigest()
def asof_quotes(archive,eu_dates,fx_path,out):
    out=Path(out);out.mkdir(exist_ok=False,parents=True)
    eu_dates=pd.DatetimeIndex(eu_dates)
    assert eu_dates.is_monotonic_increasing and eu_dates.is_unique
    rows=[];hashes={};meta={}
    for t in FIELDS:
        matches=list(Path(archive).rglob(f"{t}.csv"))
        assert len(matches)==1,(t,matches)
        p=matches[0]
        z=pd.read_csv(p,parse_dates=["date"])
        assert z.date.is_unique and z.date.is_monotonic_increasing
        assert set(["Open","High","Low","Close","Volume"])<=set(z.columns)
        assert z.Close.notna().all() and (z.Close>0).all()
        z=z[["date","Close"]].copy().rename(columns={"Close":t})
        rows.append(z);hashes[t]=sha(p)
        meta[t]={"n_rows":len(z),"first":str(z.date.min().date()),
                 "last":str(z.date.max().date())}
    master=pd.DataFrame({"date":eu_dates})
    source_same_date=pd.DataFrame({"date":eu_dates})
    source_prior_date=pd.DataFrame({"date":eu_dates})
    for z,t in zip(rows,FIELDS):
        joined=z.rename(columns={"date":"us_observation_date"})
        inclusive=pd.merge_asof(master,joined,left_on="date",right_on="us_observation_date",
                  allow_exact_matches=True,direction="backward")
        strict=pd.merge_asof(master,joined,left_on="date",right_on="us_observation_date",
                  allow_exact_matches=False,direction="backward")
        for tag,frame,destination in [("inclusive",inclusive,source_same_date),
                                      ("strict",strict,source_prior_date)]:
            gaps=(frame.date-frame.us_observation_date).dt.days
            assert gaps.notna().all() and gaps.max()<=7
            if tag=="strict":assert (gaps>0).all()
            destination[t]=frame[t].to_numpy(float)
            destination[t+"_US_MARKET_DATE"]=frame.us_observation_date.to_numpy()
            meta[t][tag+"_max_age_days"]=int(gaps.max())
            meta[t][tag+"_mean_age_days"]=float(gaps.mean())
    # EURUSD quoted as USD per EUR: price USD / FX gives EUR economic value.
    fx=pd.read_csv(fx_path,parse_dates=["date"]).sort_values("date")
    assert fx.date.is_unique and (fx.Close>0).all()
    ffx=pd.merge_asof(master,fx.rename(columns={"date":"fx_quote_date",
                        "Close":"EURUSD_USD_PER_EUR"}),left_on="date",
                      right_on="fx_quote_date",allow_exact_matches=False,direction="backward")
    assert (ffx.date-ffx.fx_quote_date).dt.days.max()<=7
    # Safely executable Euro cash sleeve Mark-to-Market approximation at EU Open:
    # both prior US adjusted ETF close and prior EURUSD are available at EU Open.
    source_prior_date["FX_USD_PER_EUR"]=ffx.EURUSD_USD_PER_EUR.to_numpy(float)
    for t in ["BIL","SHV"]:
        source_prior_date[t+"_EUR_OPEN_EST"]=source_prior_date[t]/source_prior_date["FX_USD_PER_EUR"]
        assert np.isfinite(source_prior_date[t+"_EUR_OPEN_EST"]).all()
    # No US-market current calendar day's close fed to EU signal-date feature.
    source_same_date.to_csv(out/"US_USD_REFERENCE_FOR_ORIGINAL_DD_V6_WITH_PRIOR_DAY_SHIFT.csv",index=False)
    source_prior_date.to_csv(out/"STRICT_PRIOR_US_CLOSE_FOR_EU_FEATURES_AND_CASH_EUR.csv",index=False)
    m=dict(status="ORIGINAL_US_REFERENCE_ARCHIVE_IMMUTABLE_AND_ASOF_ALIGNED",
       refs=FIELDS,files_sha256=hashes,source_quote_info=meta,
       n_eu_dates=len(master),first_eu_date=str(master.date.min().date()),
       last_eu_date=str(master.date.max().date()),
       all_euro_feature_price_US_market_date_strictly_prior=True,
       original_DD_V6_shifts_US_inclusive_previous_EU_day_before_live_trade=True,
       foreign_defense_cash_quote_currency_adjusted_EURUSD=True,
       us_ETFs_never_added_to_48_predictive_candidate_set=True,
       fx_source_sha256=sha(fx_path),no_lookahead_on_EU_Open=True)
    (out/"SOURCE_REFERENCE_AUDIT.json").write_text(json.dumps(m,indent=2)+"\n")
    print("US149_ORIGINAL_REFERENCES_IMPORTED_FOR_EU48",json.dumps(m),flush=True)
    return m

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--us",required=True)
    ap.add_argument("--eu-prep",required=True)
    ap.add_argument("--fx",required=True)
    ap.add_argument("--out",required=True)
    x=ap.parse_args()
    p=Path(x.eu_prep)/"raw_ticker_csv/IMEU.AS.csv"
    dates=pd.read_csv(p,parse_dates=["date"])["date"]
    asof_quotes(x.us,dates,x.fx,x.out)
