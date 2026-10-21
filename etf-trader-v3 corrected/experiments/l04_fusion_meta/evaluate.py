#!/usr/bin/env python3
"""V3 L04/02: train-only OOS meta-ranker, frozen prior expert predictions.

Input is ONLY previous layer's fully OOS pair127 & Tail45 score percentiles,
their predeclared product and disagreement. Target: future 21-trading-day
cross-sectional top-decile status, matured before fit cutoff. Train expanding
annual 2022–2026 and compare identical later test months vs frozen Tail and
2 already-published fixed blends. No rewrites to first-stage experts. No CAGR.
"""
from __future__ import annotations
import argparse,json,hashlib,sys
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import average_precision_score,roc_auc_score,brier_score_loss

HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
sys.path.insert(0,str(V3/"src"))
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder

FROZEN=["RANKER127","TAIL_ELITE45","BLEND50","BLEND25PAIR_75TAIL"]
CHALLENGER="L04_META_LOGIT"
FEATURES=["RANKER127","TAIL_ELITE45","product_rank","disagreement"]
HASH="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"

def basket_list(file,tickers):
    assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==HASH
    b=pd.read_csv(file)
    b.ticker=b.ticker.astype(str).str.upper()
    assert len(b)==12000 and b.basket.nunique()==500
    assert set(b.ticker)<=set(tickers)
    bs=[x.ticker.tolist() for _,x in b.sort_values(["basket","ticker"]).groupby("basket")]
    assert len(bs)==500 and all(len(a)==24 for a in bs)
    return bs

def intrinsic_month(group,baskets,score_name):
    one=group.sort_values("ticker")
    if len(one)!=149 or one.fwd_ret_21.isna().any():return None
    if not np.isfinite(one[score_name]).all():raise ValueError("Nonfinite forecast")
    y=one.fwd_ret_21.to_numpy(float);p=one[score_name].to_numpy(float)
    lookup={name:i for i,name in enumerate(one.ticker)}
    acc=[]
    for basket in baskets:
        ix=np.array([lookup[t] for t in basket],int)
        future=y[ix];forecast=p[ix]
        order=np.argsort(-forecast,kind="stable")
        true=np.argsort(-future,kind="stable")
        rank=int(np.where(true==order[0])[0][0])+1
        relevance=np.empty(len(ix),float);relevance[true]=np.linspace(1,0,len(ix))
        discount=1/np.log2(np.arange(2,5))
        ndcg=float(np.dot(relevance[order[:3]],discount)/
                   np.dot(np.sort(relevance)[::-1][:3],discount))
        acc.append((float(true[0] in set(order[:3])),
                    float(true[0]==order[0]),
                    float(future.max()-future[order[0]]),
                    ndcg,float(1/rank)))
    v=np.asarray(acc,float)
    actual_elite=one.elite21.to_numpy(dtype=int)
    return {"signal_date":one.signal_date.iloc[0],
        "year":int(one.signal_date.iloc[0].year),"variant":score_name,
        "basket_top3":float(v[:,0].mean()),"basket_top1":float(v[:,1].mean()),
        "basket_regret":float(v[:,2].mean()),"basket_ndcg3":float(v[:,3].mean()),
        "basket_mrr":float(v[:,4].mean()),
        "universe_ic":float(spearmanr(p,y).statistic),
        "elite21_ap":float(average_precision_score(actual_elite,p)),
        "elite21_auc":float(roc_auc_score(actual_elite,p)),
        "n_baskets":len(baskets),"n_etfs":len(one)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--prior",default="runs/v3_l04_static")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",default="runs/v3_l04_meta")
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    mat,cats,_=load_ticker_csv_folder(a.raw)
    assert len(cats)==149
    O=mat["Open"].loc[mat["Open"].index>=pd.Timestamp("2011-01-01")]
    frame=pd.read_csv(Path(a.prior)/"OOS_SCORES_ALL_FIXED_BLENDS.csv",parse_dates=["signal_date"])
    assert len(frame)==15198 and not frame.duplicated(["signal_date","ticker"]).any()
    assert set(FROZEN)<=set(frame.columns)
    bs=basket_list(a.baskets,cats)
    frame["product_rank"]=frame.RANKER127*frame.TAIL_ELITE45
    frame["disagreement"]=(frame.RANKER127-frame.TAIL_ELITE45).abs()
    frame["elite21"]=(frame.groupby("signal_date").fwd_ret_21.rank(pct=True)>=.9).astype(float)
    frame.loc[frame.fwd_ret_21.isna(),"elite21"]=np.nan
    assert np.isfinite(frame[FEATURES].to_numpy(float)).all()
    # Label maturity must be computed from actual next-open and 21 trading days.
    exits={}
    for date in frame.signal_date.unique():
        idx=O.index.get_indexer([date])[0]
        exits[date]=O.index[idx+1+21] if idx>=0 and idx+1+21<len(O.index) else pd.NaT
    frame["exit_date_21"]=frame.signal_date.map(exits)
    audit=[];testpred=[]
    for year in range(2022,2027):
        cutoff=pd.Timestamp(year,1,1)
        train=frame[(frame.signal_date<cutoff)&
                    (frame.exit_date_21<cutoff)&frame.elite21.notna()]
        test=frame[(frame.signal_date.dt.year.eq(year))&frame.elite21.notna()]
        if len(test)==0:continue
        assert train.signal_date.nunique()>=36,(year,train.signal_date.nunique())
        assert train.exit_date_21.max()<cutoff
        learner=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),
            LogisticRegression(C=.2,max_iter=1500,solver="lbfgs",class_weight=None))
        learner.fit(train[FEATURES],train.elite21.astype(int))
        preds=learner.predict_proba(test[FEATURES])[:,1]
        x=test.copy();x[CHALLENGER]=preds
        testpred.append(x)
        audit.append({"year":year,"train_months":int(train.signal_date.nunique()),
            "train_rows":len(train),"test_rows":len(test),
            "last_mature_exit":str(train.exit_date_21.max()),
            "feature_list":FEATURES,
            "model":"logistic C=.2, train-only standardization, classification of next21D top-decile",
            "oos_inputs_from":[39652989033,39655513813],
            "tail_macro_risk_retrained":False})
        print("V3_L04_META_TRAINED",year,len(train),len(test),flush=True)
    oos=pd.concat(testpred,ignore_index=True)
    assert not oos.duplicated(["signal_date","ticker"]).any()
    months=sorted(oos.signal_date.unique())
    assert len(months)==53 and str(pd.Timestamp(months[0]).date())=="2022-01-31"
    records=[]
    for _,one in oos.groupby("signal_date",sort=True):
        for expert in [*FROZEN,CHALLENGER]:
            r=intrinsic_month(one,bs,expert)
            if r:records.append(r)
    outmonth=pd.DataFrame(records)
    assert len(outmonth)==53*(len(FROZEN)+1)
    outmonth.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    vals=["basket_top3","basket_top1","basket_regret","basket_ndcg3","basket_mrr","universe_ic","elite21_ap","elite21_auc"]
    summ=outmonth.groupby("variant")[vals].mean()
    summ.insert(0,"months",outmonth.groupby("variant").size())
    summ.to_csv(out/"RESULTS.csv")
    outmonth.groupby(["year","variant"],as_index=False)[vals].mean().to_csv(out/"YEARLY.csv",index=False)
    boot=[]
    for base in ["TAIL_ELITE45","BLEND50","BLEND25PAIR_75TAIL"]:
        comp=outmonth[outmonth.variant==CHALLENGER].sort_values("signal_date").reset_index(drop=True)
        ref=outmonth[outmonth.variant==base].sort_values("signal_date").reset_index(drop=True)
        pd.testing.assert_series_equal(comp.signal_date,ref.signal_date)
        for col in vals:
            delta=(comp[col]-ref[col]).to_numpy(float)
            n=len(delta);rng=np.random.default_rng(20261021);block=6;reps=6000
            starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
            ix=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
            sim=delta[ix].mean(axis=1)
            boot.append({"arm":CHALLENGER,"reference":base,"metric":col,
                "mean_delta":float(delta.mean()),
                "ci95_low":float(np.quantile(sim,.025)),
                "ci95_high":float(np.quantile(sim,.975)),
                "method":"paired signal month circular 6-month blocks, 6000 repetitions"})
    pd.DataFrame(boot).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    oos[["signal_date","ticker","fwd_ret_21","elite21",*FROZEN,CHALLENGER]].to_csv(out/"OOS_SCORES.csv",index=False)
    (out/"FIT_AUDIT.json").write_text(json.dumps(audit,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
       "experiment":"L04 supervised meta rank on frozen first-stage expert OOS",
       "features":FEATURES,"target":"within-month top10pct of matured next21D returns",
       "first_fit":2022,"calendar_months":53,"source_raw":39482809691,
       "prior_blends_from":39659903643,
       "fully_mature_label_before_each_annual_fit":True,
       "first_stage_scores_preq_annual_oos":True,
       "cagr":False,"risk_macro_allocation_changed":False,
       "exploratory_not_virgin_holdout":True},indent=2))
    print("V3_L04_SUPERVISED_META_RESULT\n",summ.to_string(),flush=True)

if __name__=="__main__":main()
