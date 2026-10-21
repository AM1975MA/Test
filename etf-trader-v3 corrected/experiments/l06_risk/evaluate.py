#!/usr/bin/env python3
"""V3 L06: isolate loss-risk policy at frozen Tail45 + Top3 50/30/20.

Refit ONLY the same independently established 45-field logistic bottom-decile
head from L02 at annual expanding cutoffs, with labels mature >=63 trading
days before fit. Its purpose here is to identify future bottom-10%-universe
ETFs. Exclude an ETF from proposed basket holdings if its same-month
cross-universe bad-risk percentile is >=85th, substitute next safest ETF in
frozen Tail rank order, KEEP exactly 3 holdings & weights [0.5,0.3,0.2].
Predeclared threshold 0.85, not tuned to OOS. Compare with no-risk Top3
policy on identical 149 ETF-months and 500 baskets. No CAGR.
"""
from __future__ import annotations
import argparse,json,sys,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import average_precision_score,roc_auc_score

HERE=Path(__file__).resolve().parent
V3=HERE.parents[1];sys.path.insert(0,str(V3/"experiments"/"l02_tail"))
from evaluate import read_original,UNIQUE45

BASE="TOP3_DECAY"
GATE="TOP3_DECAY_RISK85"
RISK_THRESHOLD=0.85
WEIGHTS=np.array([.5,.3,.2])
BASKET_SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"

def evaluate_one_month(frame,baskets,prev):
    if frame.fwd_ret_21.isna().any():return [],None
    one=frame.sort_values("ticker").reset_index(drop=True)
    assert len(one)==149
    lookup={t:i for i,t in enumerate(one.ticker)}
    future=one.fwd_ret_21.to_numpy(float)
    signal=one.TAIL_ELITE45.to_numpy(float)
    risk=one.risk_percentile.to_numpy(float)
    target=one.target_rank_21.to_numpy(float)
    if not (np.isfinite(signal).all() and np.isfinite(risk).all()):raise RuntimeError("Not point-in-time scored")
    bad=target<=.10
    risky=risk>=RISK_THRESHOLD
    if len(np.unique(bad))!=2:raise RuntimeError("No both classes in monthly bottom-decile labels")
    riskresult={
        "signal_date":one.signal_date.iloc[0],
        "bottom_ap":float(average_precision_score(bad.astype(int),risk)),
        "bottom_auc":float(roc_auc_score(bad.astype(int),risk)),
        "risk_flag_rate":float(risky.mean()),
        "risk_flag_precision":float(np.mean(bad[risky])),
        "risk_flag_recall":float(np.sum(bad&risky)/max(1,np.sum(bad))),
        "risk_false_positive_rate":float(np.sum(~bad&risky)/max(1,np.sum(~bad)))}
    groups={BASE:[],GATE:[]}
    skips=[]
    for j,basket in enumerate(baskets):
        ix=np.array([lookup[t] for t in basket],int)
        y=future[ix];ss=signal[ix];rr=risk[ix]
        order=np.argsort(-ss,kind="stable")
        normal=order[:3]
        eligible=[i for i in order if rr[i]<RISK_THRESHOLD]
        assert len(eligible)>=3,(j,len(eligible))
        gated=np.array(eligible[:3],int)
        true=np.argsort(-y,kind="stable")
        best=int(true[0]);bottom=set(true[-3:].tolist())
        # Distinguish an exclusion of an actually good ETF from a
        # negative-tail detection; these OOS labels are evaluation ONLY.
        excluded=set(normal.tolist())-set(gated.tolist())
        for z in excluded:
            skips.append((float(z not in bottom),float(z==best)))
        rel=np.empty(len(ix),float);rel[true]=np.linspace(1.,0.,len(ix))
        for name,chosen in [(BASE,normal),(GATE,gated)]:
            w=WEIGHTS
            holdings={basket[int(chosen[i])]:float(w[i]) for i in range(3)}
            old=prev[name][j]
            churn=np.nan if old is None else float(sum(abs(
                holdings.get(k,0.)-old.get(k,0.)) for k in set(holdings)|set(old))/2)
            prev[name][j]=holdings
            capture=float(best in chosen)
            winner_weight=float(w[list(chosen).index(best)]) if best in chosen else 0.
            bad_weight=float(sum(w[i] for i,z in enumerate(chosen) if int(z) in bottom))
            groups[name].append((capture,winner_weight,bad_weight,
                float(np.dot(w,rel[chosen])),
                float(y.max()-np.dot(w,y[chosen])),
                churn,float(len(excluded)) if name==GATE else 0.))
    monthly=[]
    for name,v in groups.items():
        arr=np.asarray(v,float)
        monthly.append({"variant":name,"signal_date":one.signal_date.iloc[0],
            "year":int(one.signal_date.iloc[0].year),
            "n_baskets":len(baskets),
            "winner_in_selected3":float(arr[:,0].mean()),
            "winner_weight":float(arr[:,1].mean()),
            "future_bottom3_weight":float(arr[:,2].mean()),
            "selected_rank_quality":float(arr[:,3].mean()),
            "selected_oracle_regret21":float(arr[:,4].mean()),
            "target_weight_churn":float(np.nanmean(arr[:,5])) if np.isfinite(arr[:,5]).any() else np.nan,
            "excluded_etfs_per_basket":float(arr[:,6].mean()),
            "false_exclusion_fraction":float(np.mean([q[0] for q in skips])) if (name==GATE and skips) else np.nan,
            "mistaken_exclusion_of_best_fraction":float(np.mean([q[1] for q in skips])) if (name==GATE and skips) else np.nan})
    return monthly,riskresult

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--predictions",default="runs/v3_l04_static/OOS_SCORES_ALL_FIXED_BLENDS.csv")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",default="runs/v3_l06_risk")
    a=p.parse_args()
    assert hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()==BASKET_SHA
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    table,baskets,valid,_=read_original(a.raw,a.baskets)
    oracle=pd.read_csv(a.predictions,parse_dates=["signal_date"])
    oracle=oracle[["signal_date","ticker","TAIL_ELITE45","fwd_ret_21"]]
    assert len(oracle)==15198
    assert not oracle.duplicated(["signal_date","ticker"]).any()
    risks=[];audits=[]
    for year in range(2018,2027):
        cutoff=pd.Timestamp(year,1,1)
        train=(table.signal_date.ge(pd.Timestamp("2012-01-01"))&
               table.signal_date.lt(cutoff)&table.exit_date_63.lt(cutoff)&
               table.y_tailmix.notna()&table.target_rank_21.notna()&valid)
        test=(table.signal_date.dt.year.eq(year)&valid)
        tr=table.loc[train].sort_values(["signal_date","ticker"])
        te=table.loc[test].sort_values(["signal_date","ticker"])
        assert tr.signal_date.nunique()>=50
        assert tr.exit_date_63.max()<cutoff
        model=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),
            LogisticRegression(C=.2,solver="lbfgs",class_weight=None,max_iter=1500))
        y=tr.target_rank_21.le(.10).astype(int)
        model.fit(tr[UNIQUE45],y)
        result=te[["signal_date","ticker","target_rank_21","fwd_ret_21"]].copy()
        result["p_bad"]=model.predict_proba(te[UNIQUE45])[:,1]
        risks.append(result)
        audits.append({"year":year,"train_rows":len(tr),"test_rows":len(te),
          "last_mature_63d_exit":str(tr.exit_date_63.max()),
          "risk_training_event_rate":float(y.mean()),
          "input_features":UNIQUE45,
          "model":"Logistic C=.2 no balance, median/standardized",
          "gate_threshold":RISK_THRESHOLD,"other_layers_retrained":False})
        print("V3_L06_RISK_OOS_FITTED",year,len(tr),len(te),flush=True)
    risk=pd.concat(risks,ignore_index=True)
    scores=oracle.merge(risk[["signal_date","ticker","p_bad","target_rank_21"]],
         on=["signal_date","ticker"],validate="one_to_one")
    assert len(scores)==len(oracle)
    assert not scores.duplicated(["signal_date","ticker"]).any()
    scores["risk_percentile"]=scores.groupby("signal_date").p_bad.rank(pct=True,method="average")
    prev={p:[None]*500 for p in [BASE,GATE]}
    records=[];riskquality=[]
    for dt,g in scores.groupby("signal_date",sort=True):
        x,r=evaluate_one_month(g,baskets,prev)
        if x:records.extend(x)
        if r:riskquality.append(r)
    monthly=pd.DataFrame(records)
    riskout=pd.DataFrame(riskquality)
    assert len(monthly)==101*2 and len(riskout)==101
    assert not monthly.duplicated(["variant","signal_date"]).any()
    monthly.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    riskout.to_csv(out/"RISK_MODEL_MONTHLY.csv",index=False)
    scores.to_csv(out/"RISK_SCORES_OOS.csv",index=False)
    cols=["winner_in_selected3","winner_weight","future_bottom3_weight",
          "selected_rank_quality","selected_oracle_regret21","target_weight_churn",
          "excluded_etfs_per_basket","false_exclusion_fraction",
          "mistaken_exclusion_of_best_fraction"]
    summary=monthly.groupby("variant")[cols].mean()
    summary.insert(0,"months",monthly.groupby("variant").size())
    summary.to_csv(out/"RESULTS.csv")
    monthly.groupby(["year","variant"],as_index=False)[cols].mean().to_csv(out/"YEARLY.csv",index=False)
    rs={x:float(riskout[x].mean()) for x in riskout if x!="signal_date"}
    (out/"RISK_MODEL_SKILL.json").write_text(json.dumps(rs,indent=2))
    baseline=monthly[monthly.variant==BASE].sort_values("signal_date").reset_index(drop=True)
    trial=monthly[monthly.variant==GATE].sort_values("signal_date").reset_index(drop=True)
    pd.testing.assert_series_equal(baseline.signal_date,trial.signal_date)
    stats=[]
    for col in cols[:6]:
        dif=(trial[col]-baseline[col]).to_numpy(float)
        if col=="target_weight_churn":dif=dif[1:]
        assert np.isfinite(dif).all()
        n=len(dif);rng=np.random.default_rng(20261021);b=6;reps=6000
        starts=rng.integers(0,n,size=(reps,int(np.ceil(n/b))))
        idx=((starts[:,:,None]+np.arange(b))%n).reshape(reps,-1)[:,:n]
        sim=dif[idx].mean(axis=1)
        stats.append({"arm":GATE,"ref":BASE,"metric":col,
            "mean_delta":float(dif.mean()),
            "ci95_low":float(np.quantile(sim,.025)),
            "ci95_high":float(np.quantile(sim,.975)),
            "method":"paired 6-month calendar-block bootstrap"})
    pd.DataFrame(stats).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    (out/"FIT_AUDIT.json").write_text(json.dumps(audits,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
       "layer":"L06 independent bottom-decile risk rejection",
       "fixed_tail_expert":"TAIL_ELITE45 from 39655513813",
       "fixed_allocation":"TOP3_DECAY [.5,.3,.2] from V3 L05",
       "risk":"annual fitted 45-feature logistic head, 63D label maturity",
       "risk_filter":"remove top-ranked candidates if monthly p_bad percentile>=0.85; replace with next available safe Tail rank",
       "fixed_threshold_no_oos_search":True,
       "raw_source_run":39482809691,"l04_frozen_scores_run":39659903643,
       "regime_tuning":False,"cagr":False,"execution_PnL":False,
       "historical_explored_no_virgin_holdout":True},indent=2))
    print("V3_L06_RISK_FUNCTIONAL_RESULT\n",summary.to_string(),flush=True)
    print("V3_L06_P_BAD_SKILL\n",json.dumps(rs,indent=2),flush=True)

if __name__=="__main__":main()
