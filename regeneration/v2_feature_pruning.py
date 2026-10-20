#!/usr/bin/env python3
"""Frozen ETF Trader V2 127-leaf feature-pruning pilot; no portfolio overlays.
The subset order was frozen independently from pre-2017 labels in the
6 Oct 2026 COMPACT21_ORTHOGONAL_FEATURE_ABLATION_V1 artifact (11441633998).
The original 125-feature model is refitted on exactly the same rows, dates,
snapshot, hyperparameters and seeds as each pruned contender.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from xgboost import XGBRanker

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"regeneration"/"campaign"))
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder,load_baskets

BASKET_SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
PRIOR_ARTIFACT_ID=11441633998
FAMILY_ORDER="""mom252_dev gkvol21_pct corr_mkt126_dev acc_mom_21_63_dev acc_mom_5_21_dev mom63_dev log_adv63_pct volume_surprise21_pct kurt63_dev beta_mkt126_dev efficiency126_dev mom126_pct autocorr1_63 efficiency21_dev skew63_dev mom10_dev drawdown21 breakout_pos252_pct vol126_dev mom5_dev mom42_dev mom252_ex21_dev mom21_dev efficiency63_dev beta_mkt63_dev mom126_ex21_dev vol_ratio_21_126 corr_mkt63_dev ma_gap200_pct max_loss63_pct vol21_dev ema_gap20 sign_entropy63 vol63_dev positive_frac63 ema_gap50 max_gain63_pct cvar10_63 drawdown63_pct rsi14 ma_gap50_pct breakout_pos126_pct drawdown126_pct downvol126_dev downvol63_pct downvol21_pct""".split()
SUBSETS={"BASE125":k.F2D_FEATURES}
SUBSETS.update({f"K{n}":FAMILY_ORDER[:n] for n in (8,16,24,32,40,46)})
SETS_TO_RUN=("BASE125","K16","K32","K46")
SEEDS=(101,202,303)

def check_contract():
    assert len(k.F2D_FEATURES)==125 and len(set(k.F2D_FEATURES))==125
    assert len(FAMILY_ORDER)==46 and len(set(FAMILY_ORDER))==46
    for name,features in SUBSETS.items():
        assert len(features)==len(set(features)) and set(features)<=set(k.F2D_FEATURES),name
    p=k.COMPACT_PARAMS
    assert p["objective"]=="rank:pairwise" and p["n_estimators"]==360
    assert p["max_depth"]==4 and list(k.COMPACT_SEEDS)==list(SEEDS)

def load_compact(raw,baskets_file):
    sha=hashlib.sha256(Path(baskets_file).read_bytes()).hexdigest()
    assert sha==BASKET_SHA,"500 canonical baskets changed"
    mats,cats,_=load_ticker_csv_folder(raw)
    assert len(cats)==149,"Expected 149 frozen tickers"
    mats={key:v.loc[v.index>=pd.Timestamp("2011-01-01")] for key,v in mats.items()}
    baskets=load_baskets(baskets_file,cats)
    assert len(baskets)==500 and all(len(b)==24 for b in baskets)
    k.ALL_TICKERS=sorted(cats)
    k.TICKER_CATEGORY=cats
    k.CATEGORY_TICKERS={c:sorted(t for t in cats if cats[t]==c) for c in sorted(set(cats.values()))}
    dates=k.month_end_dates(mats["Close"].index)
    if len(dates) and dates[-1]==mats["Close"].index[-1]:dates=dates[:-1]
    _,compact,_,_=k.build_features(mats)
    compact=k.add_labels(compact[compact.signal_date.isin(dates)],mats["Open"],dates)
    assert set(k.F2D_FEATURES)<=set(compact.columns)
    return compact,baskets

def ic(x,y):
    a=np.asarray(x,float);b=np.asarray(y,float)
    good=np.isfinite(a)&np.isfinite(b)
    if good.sum()<10 or np.unique(a[good]).size<4 or np.unique(b[good]).size<4:return float("nan")
    return float(spearmanr(a[good],b[good]).statistic)

def feature_diagnostics(compact,out):
    # Discovery for diagnostics only: strictly mature labels before 2017.
    cutoff=pd.Timestamp("2017-01-01")
    g=compact[(compact.signal_date>=pd.Timestamp("2012-01-01"))&
              (compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&
              compact.target_rank_21.notna()]
    rows=[]
    for name in k.F2D_FEATURES:
        vals=[ic(part[name],part.target_rank_21) for _,part in g.groupby("signal_date",sort=True)]
        rows.append({"feature":name,"family":name.removesuffix("_pct").removesuffix("_dev"),
                     "months":int(np.isfinite(vals).sum()),
                     "mean_monthly_ic_pre2017":float(np.nanmean(vals)),
                     "std_monthly_ic_pre2017":float(np.nanstd(vals)),
                     "missing_fraction_pre2017":float(g[name].isna().mean()),
                     "in_family46":int(name in FAMILY_ORDER),
                     "in_K16":int(name in SUBSETS["K16"])})
    pd.DataFrame(rows).to_csv(out/"PRE2017_FEATURE_DIAGNOSTICS.csv",index=False)
    return g

def eval_month(g,baskets):
    g=g.dropna(subset=["pred","fwd_ret_21"]).sort_values(["pred","ticker"],ascending=[False,True])
    if len(g)<10:return None
    y=g.fwd_ret_21.to_numpy(float);p=g.pred.to_numpy(float)
    winner=int(np.argmax(y))
    top3=set(np.argsort(-p,kind="stable")[:3])
    order={ticker:i for i,ticker in enumerate(g.ticker)}
    bs=[]
    for basket in baskets:
        idx=[order[t] for t in basket if t in order]
        if len(idx)<2:continue
        yy=y[idx];pp=p[idx]
        best=int(np.argmax(yy)); selected=int(np.argmax(pp))
        btop3=set(np.argsort(-pp,kind="stable")[:3])
        bs.append((float(best==selected),float(best in btop3),float(yy.max()-yy[selected]),float(yy[selected]-yy.mean())))
    if not bs:return None
    b=np.asarray(bs)
    return {"signal_date":str(g.signal_date.iloc[0].date()),"year":int(g.signal_date.iloc[0].year),
            "n_tickers":len(g),"n_baskets":len(bs),"universe_ic":ic(p,y),
            "universe_top1":float(int(np.argmax(p))==winner),
            "universe_top3":float(winner in top3),
            "universe_regret":float(y.max()-y[int(np.argmax(p))]),
            "universe_selected_excess":float(y[int(np.argmax(p))]-y.mean()),
            "basket_top1":float(b[:,0].mean()),"basket_top3":float(b[:,1].mean()),
            "basket_regret":float(b[:,2].mean()),"basket_selected_excess":float(b[:,3].mean())}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",default="etf_trader_raw")
    ap.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    ap.add_argument("--out",default="runs/v2_feature_pruning")
    ap.add_argument("--years",default="2018,2022,2025")
    ap.add_argument("--sets",default=",".join(SETS_TO_RUN))
    args=ap.parse_args()
    check_contract()
    years=[int(v) for v in args.years.split(",")]
    names=[v.strip() for v in args.sets.split(",")]
    assert len(set(years))==len(years) and set(years)<=set(range(2018,2027))
    assert names and len(names)==len(set(names)) and set(names)<=set(SUBSETS)
    assert "BASE125" in names
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    compact,baskets=load_compact(args.raw,args.baskets)
    feature_diagnostics(compact,out)
    valid=(compact[k.F2D_FEATURES].notna().sum(axis=1)>=30)
    records=[]; audits=[]
    params=dict(k.COMPACT_PARAMS,max_depth=0,grow_policy="lossguide",max_leaves=127)
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        train=compact[(compact.signal_date>=pd.Timestamp("2012-01-01"))&
                      (compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&
                      compact.target_rank_21.notna()&valid].sort_values(["signal_date","ticker"])
        test=compact[(compact.signal_date.dt.year==year)&valid].sort_values(["signal_date","ticker"])
        assert len(train)>0 and train.signal_date.nunique()>=60
        assert train.exit_date_21.max()<cutoff
        assert (train.signal_date<cutoff).all()
        if test.empty:continue
        y=np.rint(100*train.target_rank_21.to_numpy(float)).astype(int)
        groups=train.groupby("signal_date",sort=True).size().to_numpy()
        assert groups.sum()==len(train)
        common_train=train[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)
        common_test=test[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)
        for name in names:
            features=SUBSETS[name]
            preds=[]
            for seed in SEEDS:
                model=XGBRanker(**params,random_state=seed)
                model.fit(common_train[features],y,group=groups,verbose=False)
                preds.append(model.predict(common_test[features]))
            frame=test[["signal_date","ticker","fwd_ret_21"]].copy()
            frame["pred"]=np.mean(preds,axis=0)
            for date,part in frame.groupby("signal_date",sort=True):
                result=eval_month(part,baskets)
                if result is not None:records.append({"variant":name,**result})
            audits.append({"year":year,"variant":name,"train_rows":len(train),"test_rows":len(test),
                           "train_months":train.signal_date.nunique(),"mature_last_exit":str(train.exit_date_21.max()),
                           "n_features":len(features),"params":params,"seeds":list(SEEDS)})
            print("FIT_DONE",year,name,"train",len(train),"test",len(test),flush=True)
    monthly=pd.DataFrame(records)
    if monthly.empty:raise RuntimeError("No mature OOS comparison months")
    monthly.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    summary=monthly.groupby("variant").agg(months=("universe_ic","size"),
        universe_ic=("universe_ic","mean"),universe_top1=("universe_top1","mean"),
        universe_top3=("universe_top3","mean"),universe_regret=("universe_regret","mean"),
        universe_selected_excess=("universe_selected_excess","mean"),
        basket_top1=("basket_top1","mean"),basket_top3=("basket_top3","mean"),
        basket_regret=("basket_regret","mean"),basket_selected_excess=("basket_selected_excess","mean"))
    summary["n_features"]=[len(SUBSETS[n]) for n in summary.index]
    summary.to_csv(out/"RESULTS.csv")
    # Paired calendar check: all contenders must use same test months.
    base=monthly[monthly.variant=="BASE125"].set_index("signal_date").sort_index()
    paired=[]
    for name in names:
        if name=="BASE125":continue
        contender=monthly[monthly.variant==name].set_index("signal_date").sort_index()
        assert base.index.equals(contender.index),"OOS months differ"
        for metric in ("universe_ic","universe_top1","universe_top3","universe_regret",
                       "universe_selected_excess","basket_top1","basket_top3","basket_regret",
                       "basket_selected_excess"):
            diff=(contender[metric]-base[metric]).to_numpy(float)
            rng=np.random.default_rng(20261021)
            N=len(diff);length=min(6,N)
            starts=rng.integers(0,N,size=(3000,int(np.ceil(N/length))))
            ix=((starts[:,:,None]+np.arange(length))%N).reshape(3000,-1)[:,:N]
            sims=diff[ix].mean(axis=1)
            paired.append({"variant":name,"metric":metric,"months":N,
                "mean_delta":float(diff.mean()),"ci95_low":float(np.quantile(sims,.025)),
                "ci95_high":float(np.quantile(sims,.975)),
                "bootstrap_unit":"shared months, circular 6-month blocks"})
    pd.DataFrame(paired).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    (out/"FIT_AUDIT.json").write_text(json.dumps(audits,indent=2,default=str))
    (out/"MANIFEST.json").write_text(json.dumps({"description":"October 21 2026 predeclared feature-pruning pilot",
        "raw_origin_run":39482809691,"raw_artifact_id":12292840548,
        "basket_sha256":BASKET_SHA,"prior_feature_artifact":PRIOR_ARTIFACT_ID,
        "years":years,"sets":{n:SUBSETS[n] for n in names},"all_125":k.F2D_FEATURES,
        "model":"XGBRanker rank:pairwise 127 leaves, 360 trees, seeds 101/202/303",
        "no_tail":True,"no_macro":True,"no_risk_or_allocation":True},indent=2))
    (out/"SUMMARY.md").write_text("# Frozen V2 feature-pruning pilot\n\n"
        "Full universe: 149 ETFs; same 500 canonical baskets; frozen raw snapshot from GH run 39482809691.\n"
        "Predictions: direct XGBoost only, no tail/macro/risk/portfolio overlay. Retained common eligibility.\n\n"
        "All differences are paired and exploratory; basket samples are aggregated by month.\n\n"
        +summary.round(5).to_markdown()+"\n")
    print("FINAL_RESULT\n",summary.to_string(),flush=True)

if __name__=="__main__":main()
