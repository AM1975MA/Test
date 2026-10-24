#!/usr/bin/env python3
"""Locked original V3 127-leaf XGBRanker plus five regressors, on EUROPE 48 ISINs.

This is a *genuine EUR48 refit*, NOT importing USA149 ticker predictions.
Features are native source 125F, including the pre-European-session US SPY
market regressor exactly as prior Euro48 certified source. All model
hyperparameters and seeds fixed from v3 rank_reg_fusion/evaluate.py (2026-10-24).
Six historical 2021-26 chronological folds use 2017+ fully mature labels.
EU48 original 125F annual OOS labels/tickers must match byte-level causal
source computation. Never alter immutable US149, EU48 V2, or production.
"""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from xgboost import XGBRanker,XGBRegressor
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from isin_first2026.compact21_base48.run import strict_build_spy
from isin_first2026.predict48.tournament import price_data,monthly_data
from isin_first2026.v2_usref48.original_us_references import asof_quotes
from isin_first2026.compact21_base48.run import ROOT
SEEDS=(101,202,303)
VOL_BASE={"vol21","vol63","vol126","downvol21","downvol63","downvol126","vol_ratio_21_126","gkvol21"}
F=list(k.F2D_FEATURES)
NO_VOL=[v for v in F if v.split("_pct")[0].split("_dev")[0] not in VOL_BASE]
ARMS={"CORRECTED":F,"REG_REL125":F,"REG_REL101":NO_VOL,
      "REG_ABS125":F,"REG_ABS101":NO_VOL,"REG_HUBER125":F}
REFERENCE="isin_first2026/compact21_base48/results/FITTED_3SEED_ANNUAL/BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv"
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--years",required=True)
    p.add_argument("--prep",required=True)
    p.add_argument("--us",required=True)
    p.add_argument("--fx",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    years=[int(x) for x in args.years.split(",")]
    assert years and len(set(years))==len(years) and set(years)<=set(range(2021,2027))
    output=Path(args.out);output.mkdir(parents=True,exist_ok=True)
    mats,cat,_=load_ticker_csv_folder(Path(args.prep)/"raw_ticker_csv")
    assert len(cat)==48
    roster=pd.read_csv(Path(args.prep)/"raw_ticker_csv/universe.csv")
    assert roster.ticker.nunique()==roster["isin"].nunique()==48
    asof_dir=output/"SPY_REFERENCE";asof_quotes(args.us,mats["Close"].index,args.fx,asof_dir)
    prior=pd.read_csv(asof_dir/"STRICT_PRIOR_US_CLOSE_FOR_EU_FEATURES_AND_CASH_EUR.csv",parse_dates=["date"])
    dates,compact,_,_=strict_build_spy(mats,prior)
    full=k.add_labels(compact,mats["Open"],dates)
    valid=full[F].notna().sum(axis=1)>=30
    assert len(F)==125 and len(NO_VOL)==101
    assert set(ARMS)=={"CORRECTED","REG_REL125","REG_REL101","REG_ABS125","REG_ABS101","REG_HUBER125"}
    historical=pd.read_csv(REFERENCE,parse_dates=["signal_date"])
    assert len(historical)==65*48
    result=[];audit=[]
    for year in years:
        t0=pd.Timestamp(f"{year}-01-01")
        tr=full[(full.signal_date>=pd.Timestamp("2017-01-01"))&
                (full.signal_date<t0)&(full.exit_date_21<t0)&
                full.target_rank_21.notna()&valid].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        te=full[full.signal_date.dt.year.eq(year)&
                full.signal_date.isin(historical.signal_date)&valid].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        saved=historical[historical.signal_date.dt.year.eq(year)].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        assert len(tr)>=2200 and not te.empty
        assert te[["signal_date","ticker"]].equals(saved[["signal_date","ticker"]])
        np.testing.assert_allclose(te.fwd_ret_21,saved.fwd_ret_21,rtol=0,atol=1e-12)
        assert tr.groupby("signal_date").size().eq(48).all()
        assert te.groupby("signal_date").size().eq(48).all()
        group=tr.groupby("signal_date").size().to_numpy(int)
        labels=np.rint(100*tr.target_rank_21.to_numpy(float)).astype(int)
        log_r=np.log1p(tr.fwd_ret_21.clip(lower=-.95).astype(float))
        y_abs=100*log_r.clip(-.25,.25).to_numpy(float)
        y_rel=100*(log_r-log_r.groupby(tr.signal_date).transform("median")).clip(-.25,.25).to_numpy(float)
        config=dict(k.COMPACT_PARAMS,max_depth=0,grow_policy="lossguide",max_leaves=127)
        for arm,names in ARMS.items():
            matrix=tr[names].replace([np.inf,-np.inf],np.nan)
            inference=te[names].replace([np.inf,-np.inf],np.nan)
            pconfig=dict(config)
            if arm=="CORRECTED":
                model_cls=XGBRanker; y=labels
            else:
                model_cls=XGBRegressor
                pconfig.update(objective="reg:squarederror",eval_metric="rmse")
                y=y_rel if arm.startswith("REG_REL") or arm=="REG_HUBER125" else y_abs
                if arm=="REG_HUBER125":
                    pconfig.update(objective="reg:pseudohubererror",eval_metric="mae",huber_slope=1.0)
            preds=[]
            for seed in SEEDS:
                model=model_cls(**pconfig,random_state=seed)
                if arm=="CORRECTED":model.fit(matrix,y,group=group,verbose=False)
                else:model.fit(matrix,y,verbose=False)
                preds.append(model.predict(inference))
            pred=np.mean(np.stack(preds),axis=0)
            assert len(pred)==len(te) and np.isfinite(pred).all()
            frame=te[["signal_date","ticker","fwd_ret_21"]].copy()
            frame["variant"]=arm
            frame["pred"]=pred
            result.append(frame)
            audit.append(dict(variant=arm,year=year,n_train=len(tr),n_test=len(te),
                n_train_months=tr.signal_date.nunique(),
                last_mature_train_target=str(tr.exit_date_21.max().date()),
                source_train_start=str(tr.signal_date.min().date()),
                feature_count=len(names),three_seeds=list(SEEDS),max_leaves=127,
                n_estimators=int(pconfig["n_estimators"]),parameter_values=pconfig))
            print("EU48_V3_HEAD_PASS",year,arm,len(tr),len(te),flush=True)
    df=pd.concat(result,ignore_index=True)
    assert not df.duplicated(["variant","signal_date","ticker"]).any()
    assert set(df.variant)==set(ARMS)
    assert df.groupby(["variant","signal_date"]).size().eq(48).all()
    df.to_csv(output/"EU48_V3_FIRSTSTAGE_SCORES.csv",index=False)
    (output/"FIT_AUDIT.json").write_text(json.dumps(audit,indent=2,default=str))
    (output/"MANIFEST.json").write_text(json.dumps(dict(
         project="ETF Trader V3 corrected",
         geographic_universe="48 unique Europe exposed UCITS EUR listed ISIN",
         train_start="2017-01-01",years=years,
         exact_125feature_source_spy_market_prior_europe_open=True,
         frozen_127_leaf_ranker_and_five_regressor_config=True,
         source_125_europe_reference_65_months_validated=True,
         baskets_not_in_learner_training=True,
         forward_21d_label_maturity_annual=True,
         research_only=True,no_V2_modifications=True),indent=2))
    print("EU48_V3_YEAR_BATCH_PASSED",years,len(df),flush=True)
if __name__=="__main__":main()
