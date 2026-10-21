#!/usr/bin/env python3
"""ETF-Trader V3 L00: isolated missingness-regime feature-family ablation.

A priori candidates, not selected based on OOS:
  CORRECTED: known frozen 125-feature V2 corrected baseline (no refit)
  LEGACY: old 125-feature baseline (no refit)
  V3_GATE128: corrected 125 + 3 explicit binary legacy-availability gates.
  V3_CONDSTD128: corrected 125 + 3 legacy conditional negative-return std's,
                 with honest distinct names (no longer masquerading as downside risk).

Only the two new arms are trained from scratch. Both baseline score streams
come from the independently fitted and score-for-score certified run 39515716383.
Walk-forward annual 127-leaf/360-tree/3-seed, same legacy 30/125 eligibility,
identical labels, mature exit dates, raw ETF time series and basket membership.
"""
from __future__ import annotations
import sys, argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from xgboost import XGBRanker

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
V3ROOT=HERE.parents[1]
sys.path.insert(0,str(V3ROOT/"src"))
sys.path.insert(0,str(ROOT/"regeneration"/"campaign"))
from etf_trader_v3.source_only import kernel as corrected
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder,load_baskets
from etf_trader.source_only import kernel as legacy

HORIZONS=(21,63,126)
ARMS={"V3_GATE128":"gate","V3_CONDSTD128":"std"}
SEEDS=(101,202,303)
ORACLE_RUN=39515716383
BASKET_SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"

def month_ic(a,b):
    x=np.asarray(a,float);y=np.asarray(b,float);ok=np.isfinite(x)&np.isfinite(y)
    if ok.sum()<10 or len(np.unique(x[ok]))<4 or len(np.unique(y[ok]))<4:return np.nan
    return float(spearmanr(x[ok],y[ok]).statistic)

def eval_month(t,baskets):
    t=t.dropna(subset=["pred","fwd_ret_21"]).sort_values(
        ["pred","ticker"],ascending=[False,True])
    if len(t)<10:return None
    y=t.fwd_ret_21.to_numpy(float);p=t.pred.to_numpy(float)
    winner=int(np.argmax(y))
    t3=set(np.argsort(-p,kind="stable")[:3]);lookup={v:i for i,v in enumerate(t.ticker)}
    bs=[]
    for basket in baskets:
        ids=[lookup[x] for x in basket if x in lookup]
        if len(ids)<2:continue
        yy=y[ids];pp=p[ids];w=int(np.argmax(yy));s=int(np.argmax(pp))
        bs.append((int(w==s),int(w in set(np.argsort(-pp,kind="stable")[:3])),
                   yy.max()-yy[s],yy[s]-yy.mean()))
    if not bs:return None
    z=np.array(bs,float)
    return {"signal_date":str(t.signal_date.iloc[0].date()),
        "year":int(t.signal_date.iloc[0].year),
        "n_tickers":len(t),"n_baskets":len(bs),
        "universe_ic":month_ic(p,y),"universe_top1":float(np.argmax(p)==winner),
        "universe_top3":float(winner in t3),
        "universe_regret":float(y.max()-y[int(np.argmax(p))]),
        "universe_selected_excess":float(y[int(np.argmax(p))]-y.mean()),
        "basket_top1":float(z[:,0].mean()),"basket_top3":float(z[:,1].mean()),
        "basket_regret":float(z[:,2].mean()),
        "basket_selected_excess":float(z[:,3].mean())}

def setup(raw,bfile):
    if hashlib.sha256(Path(bfile).read_bytes()).hexdigest()!=BASKET_SHA:
        raise RuntimeError("Basket checksum mismatch")
    if len(legacy.F2D_FEATURES)!=125 or corrected.F2D_FEATURES!=legacy.F2D_FEATURES:
        raise RuntimeError("Changed canonical 125 feature schema")
    mats,cats,_=load_ticker_csv_folder(raw)
    assert len(cats)==149
    mats={n:x.loc[x.index>=pd.Timestamp("2011-01-01")] for n,x in mats.items()}
    baskets=load_baskets(bfile,cats)
    assert len(baskets)==500 and all(len(b)==24 for b in baskets)
    for module in (legacy,corrected):
        module.ALL_TICKERS=sorted(cats)
        module.TICKER_CATEGORY=cats
        module.CATEGORY_TICKERS={c:sorted(x for x in cats if cats[x]==c)
             for c in sorted(set(cats.values()))}
    dates=legacy.month_end_dates(mats["Close"].index)
    if len(dates) and dates[-1]==mats["Close"].index[-1]:dates=dates[:-1]
    _,lo,_,_=legacy.build_features(mats)
    original=legacy.add_labels(lo[lo.signal_date.isin(dates)],mats["Open"],dates)
    _,co,_,_=corrected.build_features(mats)
    co=co[co.signal_date.isin(dates)].reset_index(drop=True)
    keys=["signal_date","ticker"]
    pd.testing.assert_frame_equal(original[keys],co[keys])
    # The model sees identical corrected source across the two challengers.
    df=original[[x for x in original if x not in legacy.F2D_FEATURES]].merge(
        co[keys+corrected.F2D_FEATURES],on=keys,validate="one_to_one",sort=False)
    pd.testing.assert_frame_equal(original[keys],df[keys])
    lr=np.log(mats["Close"].where(mats["Close"]>0)).diff()
    extra={}
    for h in HORIZONS:
        valid=lr.notna().rolling(h,min_periods=h).sum().eq(h)
        nneg=lr.lt(0).where(lr.notna()).rolling(h,min_periods=h).sum()
        gate=nneg.ge(max(10,h//2)).astype(float).where(valid)
        explicit_std=legacy.rolling_downvol(lr,h)
        # The gate exactly recovers legacy downvol's NaN routing for fully
        # observed windows, and has no forward-time dependence.
        same=(gate.eq(1)&valid).reindex(dates)
        oldvalid=explicit_std.reindex(dates).notna()
        if ((same!=oldvalid)&valid.reindex(dates)).any().any():
            raise RuntimeError(f"Legacy missingness gate parity failure at horizon {h}")
        extra[f"legacy_downvol_valid{h}"]=gate
        extra[f"negative_only_std{h}"]=explicit_std
    for name,matrix in extra.items():
        wide=matrix.reindex(dates)
        column=wide.stack(dropna=False).rename(name).reset_index()
        column.columns=[*keys,name]
        df=df.merge(column,on=keys,validate="one_to_one",sort=False)
        if len(df)!=len(original):raise RuntimeError(name+" changed observation grain")
    df=df.sort_values(keys).reset_index(drop=True)
    original=original.sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(original[keys],df[keys])
    audit=[]
    for col in extra:
        z=df[col]
        audit.append({"name":col,"non_missing":int(z.notna().sum()),
            "missing_fraction":float(z.isna().mean()),
            "mean":float(z.mean()),"min":float(z.min()),"max":float(z.max())})
    assert all(a["non_missing"]>1000 for a in audit)
    return original,df,baskets,audit

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--prior",default="runs/v2_corrected_oracle")
    p.add_argument("--years",default="2018,2019,2020")
    p.add_argument("--arms",default="V3_GATE128,V3_CONDSTD128")
    p.add_argument("--out",default="runs/v3_l00")
    args=p.parse_args()
    years=[int(y) for y in args.years.split(",")]
    arms=[n.strip() for n in args.arms.split(",")]
    assert years and len(set(years))==len(years) and set(years)<=set(range(2018,2027))
    assert arms and len(set(arms))==len(arms) and set(arms)<=set(ARMS)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    original,df,baskets,features_audit=setup(args.raw,args.baskets)
    (out/"FEATURE_AUDIT.json").write_text(json.dumps(features_audit,indent=2))
    prior=Path(args.prior)
    refscores=pd.read_csv(prior/"OOS_SCORES.csv",parse_dates=["signal_date"])
    refmonth=pd.read_csv(prior/"PAIRED_MONTHLY.csv")
    refscores=refscores.loc[
        refscores.variant.isin(["LEGACY","CORRECTED"])&
        refscores.signal_date.dt.year.isin(years)].copy()
    refmonth=refmonth.loc[
        refmonth.variant.isin(["LEGACY","CORRECTED"])&
        pd.to_datetime(refmonth.signal_date).dt.year.isin(years)].copy()
    # Legacy 30-of-125 feature eligibility, frozen across all challengers.
    valid=original[legacy.F2D_FEATURES].notna().sum(axis=1)>=30
    params=dict(legacy.COMPACT_PARAMS,max_depth=0,grow_policy="lossguide",max_leaves=127)
    assert params["n_estimators"]==360
    results=[];scores=[];fit_audit=[]
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        trainmask=((original.signal_date>=pd.Timestamp("2012-01-01"))&
            (original.signal_date<cutoff)&(original.exit_date_21<cutoff)&
            original.target_rank_21.notna()&valid)
        testmask=original.signal_date.dt.year.eq(year)&valid
        train=df.loc[trainmask].sort_values(["signal_date","ticker"])
        test=df.loc[testmask].sort_values(["signal_date","ticker"])
        origtrain=original.loc[trainmask].sort_values(["signal_date","ticker"])
        assert train.signal_date.nunique()>=60 and len(test)>0
        assert origtrain.exit_date_21.max()<cutoff
        groups=train.groupby("signal_date",sort=True).size().to_numpy()
        y=np.rint(100*origtrain.target_rank_21.to_numpy(float)).astype(int)
        assert groups.sum()==len(y)
        for arm in arms:
            h=ARMS[arm]
            features=corrected.F2D_FEATURES+[
                ("legacy_downvol_valid" if h=="gate" else "negative_only_std")+str(n)
                 for n in HORIZONS]
            X=train[features].replace([np.inf,-np.inf],np.nan)
            Xt=test[features].replace([np.inf,-np.inf],np.nan)
            ensembles=[]
            for seed in SEEDS:
                model=XGBRanker(**params,random_state=seed)
                model.fit(X,y,group=groups,verbose=False)
                ensembles.append(model.predict(Xt))
            current=test[["signal_date","ticker","fwd_ret_21"]].copy()
            current["pred"]=np.mean(ensembles,axis=0)
            current.insert(0,"variant",arm)
            scores.append(current)
            for date,g in current.groupby("signal_date",sort=True):
                m=eval_month(g,baskets)
                if m is not None:results.append({"variant":arm,**m})
            fit_audit.append({"year":year,"variant":arm,"features":features,
                "seed":list(SEEDS),"train_rows":len(train),"test_rows":len(test),
                "max_mature_exit":str(origtrain.exit_date_21.max()),
                "train_months":int(origtrain.signal_date.nunique()),
                "model_parameters":params,
                "input_raw_run":39482809691,"oracle_run":ORACLE_RUN})
            print("V3_L00_FIT",year,arm,len(train),len(test),flush=True)
    month=pd.DataFrame(results)
    sc=pd.concat(scores,ignore_index=True)
    allmonth=pd.concat([refmonth,month],ignore_index=True)
    allscore=pd.concat([refscores,sc],ignore_index=True)
    allmonth["signal_date"]=pd.to_datetime(allmonth.signal_date,format="mixed")
    allscore["signal_date"]=pd.to_datetime(allscore.signal_date,format="mixed")
    assert not allmonth[["variant","signal_date"]].duplicated().any()
    assert not allscore[["variant","signal_date","ticker"]].duplicated().any()
    m0=allmonth.loc[allmonth.variant=="LEGACY"].sort_values("signal_date").reset_index(drop=True)
    p0=allscore.loc[allscore.variant=="LEGACY"].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    for arm in ["CORRECTED",*arms]:
        mr=allmonth.loc[allmonth.variant==arm].sort_values("signal_date").reset_index(drop=True)
        pr=allscore.loc[allscore.variant==arm].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        assert mr.signal_date.equals(m0.signal_date),arm
        assert mr.n_baskets.equals(m0.n_baskets),arm
        assert mr.n_tickers.equals(m0.n_tickers),arm
        pd.testing.assert_frame_equal(pr[["signal_date","ticker"]],p0[["signal_date","ticker"]])
        np.testing.assert_allclose(pr.fwd_ret_21,p0.fwd_ret_21,rtol=0,atol=1e-14,equal_nan=True)
    metrics=["universe_ic","universe_top1","universe_top3","universe_regret",
             "universe_selected_excess","basket_top1","basket_top3","basket_regret",
             "basket_selected_excess"]
    summary=allmonth.groupby("variant")[metrics].mean()
    summary.insert(0,"months",allmonth.groupby("variant").size())
    summary.to_csv(out/"RESULTS.csv")
    allmonth.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    allscore.to_csv(out/"OOS_SCORES.csv",index=False)
    (out/"FIT_AUDIT.json").write_text(json.dumps(fit_audit,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
        "version":"ETF_TRADER_V3_L00_20261021","years":years,
        "arms":arms,"feature_counts":{v:128 for v in arms},
        "training":"annual refit, matured labels, 127 leaves, 360 rounds, 3 seeds",
        "oracle_run":ORACLE_RUN,"raw_snapshot_run":39482809691,
        "same_orig_eligibility":True,
        "tail_macro_allocation_risk":False,
        "holdout":"exploratory historically examined months; no untouched OOS"},indent=2))
    print("V3_L00_RESULTS\n"+summary.to_string(),flush=True)

if __name__=="__main__":main()
