#!/usr/bin/env python3
"""Predeclared V2 negative-day regime information experiment.

Arm CORRECTED_PLUS_FREQ: corrected 125 compact inputs plus exactly 3 causal
negative-session ratios, h=[21,63,126]. Baselines LEGACY and CORRECTED are
the *already fully retrained* scores from immutable successful run 39515716383.

The NEW treatment is fit from scratch by yearly expanding-window XGBRanker:
127 leaves, 360 trees, 3 seeds, same frozen 149 ETFs, matured training labels,
eligibility and 500 baskets. No Tail, Macro, risk or portfolio selection gate.

This is a tested-history exploratory robustness experiment, NOT untouched OOS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRanker

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"regeneration"/"campaign"))
import v2_formula_retrain as prior
import v2_feature_pruning as benchmark
from etf_trader.source_only import kernel as current
from etf_trader.source_only.raw_io import load_ticker_csv_folder

FREQ_HORIZONS=(21,63,126)
FREQ_NAMES=tuple(f"negative_day_fraction{h}" for h in FREQ_HORIZONS)
FEATURES=tuple(current.F2D_FEATURES)+FREQ_NAMES
SEEDS=(101,202,303)
VARIANT="CORRECTED_PLUS_FREQ"
REFERENCE_NAMES=("LEGACY","CORRECTED")

def make_negative_fraction(mats,dates):
    close=mats["Close"]
    lr=np.log(close.where(close>0)).diff()
    # Important: WHERE retains NaN when price/return is not observable.
    # Binary negative-session indicator is not equivalent to imputing missing=0.
    blocks=[]
    for h,col in zip(FREQ_HORIZONS,FREQ_NAMES):
        fraction=(lr<0).where(lr.notna()).rolling(h,min_periods=h).mean()
        assert fraction.ge(0).fillna(True).all().all()
        assert fraction.le(1).fillna(True).all().all()
        f=fraction.reindex(dates).stack(dropna=False).rename(col)
        blocks.append(f)
    panel=pd.concat(blocks,axis=1).reset_index()
    panel.columns=["signal_date","ticker",*FREQ_NAMES]
    return panel

def load_all(raw,baskets_path):
    panels,baskets,delta,source,basket_sha=prior.panel_set(raw,baskets_path)
    assert list(current.F2D_FEATURES)==list(prior.legacy.F2D_FEATURES)
    corrected=panels["CORRECTED"]
    assert len(corrected)>0 and len(baskets)==500
    mats,cats,_=load_ticker_csv_folder(raw)
    assert len(cats)==149
    mats={key:mat.loc[mat.index>=pd.Timestamp("2011-01-01")] for key,mat in mats.items()}
    month_dates=pd.DatetimeIndex(sorted(corrected.signal_date.unique()))
    freq=make_negative_fraction(mats,month_dates)
    x=corrected.merge(freq,on=["signal_date","ticker"],how="left",validate="one_to_one",sort=False)
    assert len(x)==len(corrected)
    assert x[["signal_date","ticker"]].equals(corrected[["signal_date","ticker"]])
    assert all(n in x for n in FEATURES)
    assert not set(FREQ_NAMES)&set(current.F2D_FEATURES)
    # Corrected feature vector must be byte/numeric-identical to previous arm;
    # nothing is overwritten by feature augmentation.
    pd.testing.assert_frame_equal(x[list(current.F2D_FEATURES)],
                                  corrected[list(current.F2D_FEATURES)])
    feature_audit=[]
    for name in FREQ_NAMES:
        z=x[name]
        assert z.notna().sum()>0,name
        assert z.dropna().between(0,1).all(),name
        feature_audit.append({"feature":name,"count":int(z.notna().sum()),
            "missing_fraction":float(z.isna().mean()),
            "mean":float(z.mean()),"min":float(z.min()),"max":float(z.max()),
            "horizon":int(name.replace("negative_day_fraction",""))})
    return panels,x,baskets,feature_audit,basket_sha

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--prior",default="runs/prior_v2_formula")
    p.add_argument("--years",default="2018,2019,2020")
    p.add_argument("--out",default="runs/v2_negative_frequency_shards")
    args=p.parse_args()
    years=[int(y) for y in args.years.split(",")]
    assert years and len(years)==len(set(years)) and set(years)<=set(range(2018,2027))
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    panels,aug,baskets,feature_audit,sha=load_all(args.raw,args.baskets)
    (out/"FEATURE_AUDIT.json").write_text(json.dumps(feature_audit,indent=2))
    prior_dir=Path(args.prior)
    hist=pd.read_csv(prior_dir/"OOS_SCORES.csv",parse_dates=["signal_date"])
    hist_month=pd.read_csv(prior_dir/"PAIRED_MONTHLY.csv",parse_dates=["signal_date"])
    assert {"variant","signal_date","ticker","pred","fwd_ret_21"}<=set(hist.columns)
    assert set(REFERENCE_NAMES)<=set(hist.variant.unique())
    assert set(REFERENCE_NAMES)<=set(hist_month.variant.unique())
    dates_idx=pd.to_datetime(hist.signal_date)
    hist=hist.loc[dates_idx.dt.year.isin(years)&hist.variant.isin(REFERENCE_NAMES)].copy()
    hist_month=hist_month.loc[hist_month.signal_date.dt.year.isin(years)&
        hist_month.variant.isin(REFERENCE_NAMES)].copy()
    assert not hist[["variant","signal_date","ticker"]].duplicated().any()
    assert not hist_month[["variant","signal_date"]].duplicated().any()

    orig=panels["LEGACY"]
    valid=orig[list(current.F2D_FEATURES)].notna().sum(axis=1)>=30
    assert valid.any()
    cfg=dict(prior.legacy.COMPACT_PARAMS,max_depth=0,grow_policy="lossguide",max_leaves=127)
    assert cfg["objective"]=="rank:pairwise" and cfg["n_estimators"]==360
    monthly=[];predictions=[];audits=[]
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        trmask=((orig.signal_date>=pd.Timestamp("2012-01-01"))&
                (orig.signal_date<cutoff)&(orig.exit_date_21<cutoff)&
                orig.target_rank_21.notna()&valid)
        temask=orig.signal_date.dt.year.eq(year)&valid
        tr=aug.loc[trmask].sort_values(["signal_date","ticker"])
        te=aug.loc[temask].sort_values(["signal_date","ticker"])
        tr0=orig.loc[trmask].sort_values(["signal_date","ticker"])
        te0=orig.loc[temask].sort_values(["signal_date","ticker"])
        assert len(tr)>0 and len(te)>0 and tr.signal_date.nunique()>=60
        pd.testing.assert_frame_equal(tr[["signal_date","ticker"]],tr0[["signal_date","ticker"]])
        pd.testing.assert_frame_equal(te[["signal_date","ticker"]],te0[["signal_date","ticker"]])
        assert tr0.exit_date_21.max()<cutoff
        groups=tr.groupby("signal_date",sort=True).size().to_numpy()
        target=np.rint(100*tr.target_rank_21.to_numpy(float)).astype(int)
        assert int(groups.sum())==len(tr)
        X=tr[list(FEATURES)].replace([np.inf,-np.inf],np.nan)
        XP=te[list(FEATURES)].replace([np.inf,-np.inf],np.nan)
        preds=[]
        for seed in SEEDS:
            model=XGBRanker(**cfg,random_state=seed)
            model.fit(X,target,group=groups,verbose=False)
            preds.append(model.predict(XP))
        forecast=te[["signal_date","ticker","fwd_ret_21"]].copy()
        forecast["pred"]=np.mean(preds,axis=0)
        forecast.insert(0,"variant",VARIANT)
        predictions.append(forecast)
        for _,frame in forecast.groupby("signal_date",sort=True):
            result=benchmark.eval_month(frame,baskets)
            if result:monthly.append({"variant":VARIANT,**result})
        audits.append({"year":year,"variant":VARIANT,"train_rows":len(tr),
            "test_rows":len(te),"train_dates":int(tr.signal_date.nunique()),
            "max_mature_label":str(tr.exit_date_21.max()),
            "features":list(FEATURES),"seeds":list(SEEDS),"params":cfg,
            "missing_frequency_train_fraction":float(X[list(FREQ_NAMES)].isna().to_numpy().mean()),
            "same_legacy_eligibility":True})
        print("FREQ_FIT_DONE",year,"rows",len(tr),len(te),flush=True)

    newscore=pd.concat(predictions,ignore_index=True)
    newmonth=pd.DataFrame(monthly)
    # Strict expected identical ETF-date universe, including months with no
    # matured labels (which still appear in OOS_SCORES for economic replay).
    for variant in REFERENCE_NAMES:
        ref=hist.loc[hist.variant.eq(variant)].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        cand=newscore.sort_values(["signal_date","ticker"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(ref[["signal_date","ticker"]],
                                      cand[["signal_date","ticker"]])
        np.testing.assert_allclose(ref.fwd_ret_21,cand.fwd_ret_21,equal_nan=True,rtol=0,atol=0)
        assert len(ref)>1000

    combined_scores=pd.concat([hist,newscore],ignore_index=True)
    combined_month=pd.concat([hist_month,newmonth],ignore_index=True)
    assert not combined_scores[["variant","signal_date","ticker"]].duplicated().any()
    assert not combined_month[["variant","signal_date"]].duplicated().any()
    baseline=combined_month[combined_month.variant=="LEGACY"].sort_values("signal_date").reset_index(drop=True)
    for name in ["CORRECTED",VARIANT]:
        other=combined_month[combined_month.variant==name].sort_values("signal_date").reset_index(drop=True)
        pd.testing.assert_series_equal(baseline.signal_date,other.signal_date)
        pd.testing.assert_series_equal(baseline.n_tickers,other.n_tickers)
        pd.testing.assert_series_equal(baseline.n_baskets,other.n_baskets)
    combined_scores.to_csv(out/"OOS_SCORES.csv",index=False)
    combined_month.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    metrics=["universe_ic","universe_top1","universe_top3","universe_regret",
        "universe_selected_excess","basket_top1","basket_top3","basket_regret",
        "basket_selected_excess"]
    summary=combined_month.groupby("variant")[metrics].mean()
    summary.insert(0,"months",combined_month.groupby("variant").size())
    summary.to_csv(out/"RESULTS.csv")
    (out/"FIT_AUDIT.json").write_text(json.dumps(audits,indent=2,default=str))
    (out/"MANIFEST.json").write_text(json.dumps({
        "date":"2026-10-21","source":"original 149-ETF snapshot run 39482809691",
        "prior_models_fitted_from_scratch_run":39515716383,
        "reused_baseline_variants":list(REFERENCE_NAMES),
        "new_from_scratch_variant":VARIANT,"new_features":list(FREQ_NAMES),
        "n_input_features":len(FEATURES),"source_labels":"legacy frozen",
        "training":"annual expanding OOS, fully mature 21D labels, 360 rounds, 127 leaves, 3 seeds",
        "years":years,"basket_sha256":sha,"no_tail_macro_risk":True,
        "causality":"all 3 indicators require full trailing observed daily returns",
        "eligible_rows":"exact frozen original 30/125 mask",
        "holdout":"repeatedly examined historical calendar, NOT independent virgin holdout"
    },indent=2))
    print("SUMMARY\n"+summary.to_string(),flush=True)

if __name__=="__main__":main()
