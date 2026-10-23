#!/usr/bin/env python3
"""L00.CS2 adaptive addition: original 125 plus 46 daily-normalized raw features; no original channel removed.

Control original CORRECTED same original 127-leaf / rank:pairwise / 360-trees,
3 seeds, annually mature-only walk-forward and 500 original baskets.
New challenger: preserve original 125 absolute/percentile/deviation features,
ADD 46 day-local minmax versions of raw original feature bases only.
Source feature values computed strictly from same-day closed and past OHLCV.
Initial training labels remain month-end 21-trading-day outcomes, NOT daily
supervised labels. Preserve original missingness, models, downstream untouched.
Scores are research only, not economic full-V2 strategy promotion.
"""
from __future__ import annotations
import argparse,json,sys,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from xgboost import XGBRanker
from normalize import normalize_same_day,audit_scaling,unit_contract

HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
ROOT=V3.parent
sys.path.insert(0,str(V3/"src"))
sys.path.insert(0,str(ROOT/"regeneration"/"campaign"))
from etf_trader_v3.source_only import kernel as v3
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder,load_baskets
from etf_trader.source_only import kernel as legacy

ARMS=("L00_CS_ADD171",)
SEEDS=(101,202,303)
SOURCE_RUN=39482809691
CONTROL_RUN=39515716383
BASKET_SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
BASE_FEATURES=v3.F2D_FEATURES
RAW_FEATURES=[f for f in BASE_FEATURES if not (f.endswith("_pct") or f.endswith("_dev"))]
ADD_FEATURES=[f+"_csminmax" for f in RAW_FEATURES]
FEATURES=BASE_FEATURES+ADD_FEATURES

def rank_ic(x,y):
    xx=np.asarray(x,float);yy=np.asarray(y,float)
    keep=np.isfinite(xx)&np.isfinite(yy)
    if keep.sum()<10 or len(np.unique(xx[keep]))<4 or len(np.unique(yy[keep]))<4:return np.nan
    return float(spearmanr(xx[keep],yy[keep]).statistic)

def scores_for_month(frame,baskets):
    frame=frame.dropna(subset=["pred","fwd_ret_21"]).sort_values(
        ["pred","ticker"],ascending=[False,True])
    if len(frame)<10:return None
    x=frame.pred.to_numpy(float);y=frame.fwd_ret_21.to_numpy(float)
    lookup={t:i for i,t in enumerate(frame.ticker)}
    allmetrics=[]
    for basket in baskets:
        ids=np.array([lookup[t] for t in basket if t in lookup],dtype=int)
        if len(ids)<2:continue
        p=x[ids];f=y[ids]
        order=np.argsort(-p,kind="stable")
        trueorder=np.argsort(-f,kind="stable")
        top=order[:min(3,len(order))]
        relevance=np.empty(len(f),dtype=float)
        # Rank-based linearly scaled relevance [0..1] for same-basket nDCG:
        # avoids exponential magnification of high-return outlier units.
        relevance[trueorder]=np.linspace(1,0,len(f))
        discount=1.0/np.log2(np.arange(2,len(top)+2))
        ideal=np.sort(relevance)[::-1][:len(top)]
        normalizer=np.dot(ideal,discount)
        ndcg=float(np.dot(relevance[top],discount)/normalizer) if normalizer else np.nan
        best=int(np.argmax(f))
        selected=int(order[0])
        truth_rank=int(np.where(trueorder==selected)[0][0])+1
        allmetrics.append((float(best==selected),float(best in top),
             float(f.max()-f[selected]),float(f[selected]-f.mean()),
             ndcg,1.0/truth_rank,float(truth_rank)))
    if not allmetrics:return None
    z=np.array(allmetrics)
    winner=int(np.argmax(y))
    universe_top=np.argsort(-x,kind="stable")[:3]
    return {"signal_date":str(frame.signal_date.iloc[0].date()),
        "year":int(frame.signal_date.iloc[0].year),
        "n_tickers":len(frame),"n_baskets":len(allmetrics),
        "universe_ic":rank_ic(x,y),
        "universe_top1":float(int(np.argmax(x))==winner),
        "universe_top3":float(winner in universe_top),
        "basket_top1":float(z[:,0].mean()),
        "basket_top3":float(z[:,1].mean()),
        "basket_regret":float(z[:,2].mean()),
        "basket_selected_excess":float(z[:,3].mean()),
        "basket_ndcg3":float(z[:,4].mean()),
        "basket_mrr_selected":float(z[:,5].mean()),
        "basket_selected_true_rank":float(z[:,6].mean())}

def freeze_data(raw,baskets_file):
    assert hashlib.sha256(Path(baskets_file).read_bytes()).hexdigest()==BASKET_SHA
    mats,cats,_=load_ticker_csv_folder(raw)
    assert len(cats)==149
    mats={f:x.loc[x.index>=pd.Timestamp("2011-01-01")] for f,x in mats.items()}
    baskets=load_baskets(baskets_file,cats)
    assert len(baskets)==500 and all(len(b)==24 for b in baskets)
    assert len(BASE_FEATURES)==125 and BASE_FEATURES==legacy.F2D_FEATURES
    assert len(RAW_FEATURES)==46 and len(FEATURES)==171
    assert list(v3.COMPACT_SEEDS)==list(legacy.COMPACT_SEEDS)==list(SEEDS)
    for mod in (v3,legacy):
        mod.ALL_TICKERS=sorted(cats)
        mod.TICKER_CATEGORY=cats
        mod.CATEGORY_TICKERS={c:sorted(t for t in cats if cats[t]==c)
              for c in sorted(set(cats.values()))}
    dates=legacy.month_end_dates(mats["Close"].index)
    if len(dates) and dates[-1]==mats["Close"].index[-1]:dates=dates[:-1]
    _,old,_,_=legacy.build_features(mats)
    old=legacy.add_labels(old[old.signal_date.isin(dates)],mats["Open"],dates)
    _,co,_,_=v3.build_features(mats)
    co=co[co.signal_date.isin(dates)].reset_index(drop=True)
    keys=["signal_date","ticker"]
    pd.testing.assert_frame_equal(old[keys],co[keys])
    panel=old[[f for f in old if f not in FEATURES]].merge(
        co[keys+BASE_FEATURES],on=keys,validate="one_to_one",sort=False)
    assert len(panel)==len(old)
    pd.testing.assert_frame_equal(panel[keys],old[keys])
    valid=old[BASE_FEATURES].notna().sum(axis=1)>=30
    return old,panel,valid,baskets

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--prior",default="runs/v2_corrected_oracle")
    p.add_argument("--years",default="2018,2019,2020")
    p.add_argument("--out",default="runs/v3_l01")
    args=p.parse_args()
    years=[int(x) for x in args.years.split(",")]
    assert years and set(years)<=set(range(2018,2027))
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    unit_contract()
    old,panel,valid,baskets=freeze_data(args.raw,args.baskets)
    before=panel[BASE_FEATURES].copy()
    scaled=normalize_same_day(panel,RAW_FEATURES)
    fa=audit_scaling(panel,scaled,RAW_FEATURES)
    fa.to_csv(out/"FEATURE_NORMALIZATION_AUDIT.csv",index=False)
    for original,new in zip(RAW_FEATURES,ADD_FEATURES):
        panel[new]=scaled[original].to_numpy(float)
    pd.testing.assert_frame_equal(panel[BASE_FEATURES],before)
    assert len(panel)==len(old)
    assert np.array_equal(panel[ADD_FEATURES].isna().to_numpy(),
                          before[RAW_FEATURES].replace([np.inf,-np.inf],np.nan).isna().to_numpy())
    assert fa.signal_date.nunique()>=100 and fa.feature.nunique()==46
    prior=Path(args.prior)
    scores=pd.read_csv(prior/"OOS_SCORES.csv",parse_dates=["signal_date"])
    controls=scores.loc[(scores.variant=="CORRECTED")&
         scores.signal_date.dt.year.isin(years)].copy()
    assert len(controls)>500
    baseline_month=[]
    for date,g in controls.groupby("signal_date",sort=True):
        m=scores_for_month(g,baskets)
        if m is not None:baseline_month.append({"variant":"CORRECTED",**m})
    output_scores=[controls]
    output_month=baseline_month
    audits=[]
    params=dict(v3.COMPACT_PARAMS,max_depth=0,grow_policy="lossguide",max_leaves=127)
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        train=((old.signal_date>=pd.Timestamp("2012-01-01"))&
               (old.signal_date<cutoff)&
               (old.exit_date_21<cutoff)&old.target_rank_21.notna()&valid)
        test=old.signal_date.dt.year.eq(year)&valid
        tr=panel.loc[train].sort_values(["signal_date","ticker"])
        te=panel.loc[test].sort_values(["signal_date","ticker"])
        assert tr.signal_date.nunique()>=60 and len(te)>0
        assert tr.exit_date_21.max()<cutoff
        groups=tr.groupby("signal_date",sort=True).size().to_numpy()
        y=np.rint(100*tr.target_rank_21.to_numpy(float)).astype(int)
        assert groups.sum()==len(y)
        X=tr[FEATURES].replace([np.inf,-np.inf],np.nan)
        Xt=te[FEATURES].replace([np.inf,-np.inf],np.nan)
        for arm in ARMS:
            cfg=dict(params)
            preds=[]
            for seed in SEEDS:
                model=XGBRanker(**cfg,random_state=seed)
                model.fit(X,y,group=groups,verbose=False)
                preds.append(model.predict(Xt))
            pred=te[["signal_date","ticker","fwd_ret_21"]].copy()
            pred["pred"]=np.mean(preds,axis=0)
            pred.insert(0,"variant",arm)
            output_scores.append(pred)
            for date,g in pred.groupby("signal_date",sort=True):
                m=scores_for_month(g,baskets)
                if m is not None:output_month.append({"variant":arm,**m})
            audits.append({"arm":arm,"year":year,
                "last_train_exit":str(tr.exit_date_21.max()),
                "first_test_signal":str(te.signal_date.min()),
                "train_months":int(tr.signal_date.nunique()),"train_rows":len(tr),
                "test_rows":len(te),"features":len(FEATURES),"params":cfg,"seeds":list(SEEDS),
                "scaling":"Original 125 EXACT + extra 46 day-local [-1,1] raw features, NaN mask preserved",
                "non_lookahead_normalization":True,
                "original_rank_objective":True,
                "frozen_inputs":True,"downstream_layers_enabled":False})
            print("V3_L01_FIT_DONE",year,arm,len(tr),len(te),flush=True)
    merged=pd.concat(output_scores,ignore_index=True)
    merged["signal_date"]=pd.to_datetime(merged.signal_date,format="mixed")
    m=pd.DataFrame(output_month)
    m["signal_date"]=pd.to_datetime(m.signal_date,format="mixed")
    assert not merged.duplicated(["variant","signal_date","ticker"]).any()
    assert not m.duplicated(["variant","signal_date"]).any()
    expected=merged[merged.variant=="CORRECTED"].sort_values(
        ["signal_date","ticker"]).reset_index(drop=True)
    xbase=m[m.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
    for arm in ARMS:
        x=merged[merged.variant==arm].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(x[["signal_date","ticker"]],expected[["signal_date","ticker"]])
        np.testing.assert_allclose(x.fwd_ret_21,expected.fwd_ret_21,atol=1e-14,rtol=0,equal_nan=True)
        y=m[m.variant==arm].sort_values("signal_date").reset_index(drop=True)
        pd.testing.assert_series_equal(y.signal_date,xbase.signal_date)
    merged.to_csv(out/"OOS_SCORES.csv",index=False)
    m.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    summary=m.groupby("variant").mean(numeric_only=True).drop(columns=["year"],errors="ignore")
    summary.insert(0,"months",m.groupby("variant").size())
    summary.to_csv(out/"RESULTS.csv")
    (out/"FIT_AUDIT.json").write_text(json.dumps(audits,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({"layer":"L00 CS2 adaptive original125 plus46 day-cross-sectional",
        "baseline":"CORRECTED_127_PAIRWISE_FROM_SUCCESSFUL_39515716383",
        "challengers":list(ARMS),"frozen_features":125,
        "model_features":171,"additional_features":46,
        "new_feature_representation":"original 125 untouched plus original raw46 same-day relative features [-1,+1]",
        "preprocessing_temporal_train_fit":False,
        "daily_compatible_but_monthly_supervised_signals":True,
        "objective":"intrinsic ranking accuracy, NOT CAGR",
        "no_model_architecture_or_label_change":True,
        "positive_relevance":"within-basket ordinal return rank, nDCG@3",
        "source_run":SOURCE_RUN,"control_run":CONTROL_RUN,
        "normalization_audit":"FEATURE_NORMALIZATION_AUDIT.csv",
        "backtested_history_exploratory_not_virgin":True,
        "risk_tail_macro_allocation":False},indent=2))
    print("V3_L00_CS2_ADD171_RESULT\n",summary.to_string(),flush=True)

if __name__=="__main__":main()
