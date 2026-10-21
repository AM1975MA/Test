#!/usr/bin/env python3
"""V3 L03: genuinely prequential market-regime predictability test.

Question (frozen before testing): Can ONLY market state at signal date predict
which expert will have higher basket Top-3 winner capture over next 21 trading
days? Expert OOS scores are already frozen (L01 CORRECTED pairwise127 and
L02 TAIL_EVENT_LOGIT45). L03 trains ONE simple logistic gate using historical
expert-win labels with fully matured exits. No future regime labels at signal.

Compare with train-only constant prior/static expert, random/no-gate, and a
retrospective oracle (upper bound only, not traded/selected).
No CAGR, no score blending, no allocation, no risk policy change.
"""
import argparse,json,sys,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,brier_score_loss,log_loss

HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
sys.path.insert(0,str(V3/"src"))
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder,load_baskets
from etf_trader_v3.source_only import kernel

FEATURES=["spy_ret21","spy_ret63","spy_ret126","spy_vol21",
          "spy_downvol63","breadth21","dispersion21"]
START_OOS=2022
BASKET_HASH="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"

def features_known_at_signal(mats,dates):
    C=mats["Close"]
    if "SPY" not in C.columns:raise RuntimeError("SPY reference unavailable")
    mkt=C["SPY"]
    dret=C.pct_change(fill_method=None)
    r21=C.pct_change(21,fill_method=None)
    logm=np.log(mkt.where(mkt>0)).diff()
    base=pd.DataFrame(index=C.index)
    base["spy_ret21"]=mkt.pct_change(21,fill_method=None)
    base["spy_ret63"]=mkt.pct_change(63,fill_method=None)
    base["spy_ret126"]=mkt.pct_change(126,fill_method=None)
    base["spy_vol21"]=logm.rolling(21,min_periods=21).std(ddof=0)*np.sqrt(252)
    base["spy_downvol63"]=kernel.rolling_downvol(logm.to_frame("SPY"),63)["SPY"]
    base["breadth21"]=(r21>0).where(r21.notna()).mean(axis=1)
    base["dispersion21"]=r21.std(axis=1,ddof=0)
    return base.reindex(dates)

def evaluate_experts(scores_a,scores_b,baskets):
    a=scores_a[["signal_date","ticker","fwd_ret_21","pred"]].rename(
        columns={"pred":"pair_score","fwd_ret_21":"pair_y"})
    b=scores_b[["signal_date","ticker","fwd_ret_21","pred"]].rename(
        columns={"pred":"tail_score","fwd_ret_21":"tail_y"})
    df=a.merge(b,on=["signal_date","ticker"],how="inner",validate="one_to_one")
    df.signal_date=pd.to_datetime(df.signal_date,format="mixed")
    if not len(df):raise RuntimeError("No common expert observations")
    dates=sorted(df.signal_date.unique())
    if len(dates)<98:raise RuntimeError("Too few common months")
    rows=[]
    for date,g in df.groupby("signal_date",sort=True):
        if g.pair_y.isna().any() or g.tail_y.isna().any():
            # Do not infer future returns for months without a matured target.
            continue
        g=g.sort_values("ticker")
        if len(g)<100:raise RuntimeError("Expert overlap unexpectedly small")
        np.testing.assert_allclose(g.pair_y,g.tail_y,rtol=0,atol=1e-14)
        lookup={t:i for i,t in enumerate(g.ticker)}
        y=g.pair_y.to_numpy(float)
        sa=g.pair_score.to_numpy(float);sb=g.tail_score.to_numpy(float)
        ma=[];mb=[]
        for basket in baskets:
            ix=np.array([lookup[t] for t in basket if t in lookup],dtype=int)
            if len(ix)<2:continue
            best=int(np.argmax(y[ix]))
            topp=set(np.argsort(-sa[ix],kind="stable")[:3])
            topt=set(np.argsort(-sb[ix],kind="stable")[:3])
            ma.append(int(best in topp));mb.append(int(best in topt))
        if len(ma)!=500:raise RuntimeError(f"Not exactly 500 fixed comparable baskets on {date}")
        pair_top3=float(np.mean(ma));tail_top3=float(np.mean(mb))
        rows.append({"signal_date":pd.Timestamp(date),"pair_top3":pair_top3,
            "tail_top3":tail_top3,"tail_advantage":tail_top3-pair_top3,
            "tail_wins":int(tail_top3>pair_top3),"n_tickers":len(g)})
    z=pd.DataFrame(rows).sort_values("signal_date")
    assert len(z)==101,("Unexpected matured months",len(z))
    return z

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--ranker",default="runs/v3_l01_reference")
    p.add_argument("--tail",default="runs/v3_l02_reference")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",default="runs/v3_l03_regime")
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path(args.baskets).read_bytes()).hexdigest()==BASKET_HASH
    mats,cats,_=load_ticker_csv_folder(args.raw)
    assert len(cats)==149
    mats={f:x.loc[x.index>=pd.Timestamp("2011-01-01")] for f,x in mats.items()}
    baskets=load_baskets(args.baskets,cats)
    assert len(baskets)==500
    sc_a=pd.read_csv(Path(args.ranker)/"OOS_SCORES.csv",parse_dates=["signal_date"])
    sc_b=pd.read_csv(Path(args.tail)/"OOS_SCORES.csv",parse_dates=["signal_date"])
    a=sc_a.loc[sc_a.variant=="CORRECTED"]
    b=sc_b.loc[sc_b.variant=="TAIL_EVENT_LOGIT45"]
    assert not a[["signal_date","ticker"]].duplicated().any()
    assert not b[["signal_date","ticker"]].duplicated().any()
    z=evaluate_experts(a,b,baskets)
    state=features_known_at_signal(mats,z.signal_date)
    for feature in FEATURES:
        z[feature]=state[feature].to_numpy(float)
    # If the snapshot spans 2018-May2026, all states are available after warm-up.
    if not np.isfinite(z[FEATURES].to_numpy(float)).all():
        raise RuntimeError("Market information missing in mature signal window")
    Open=mats["Open"];cal=Open.index
    exits=[]
    for d in z.signal_date:
        i=cal.get_indexer([d])[0]
        if i<0 or i+1+21>=len(cal):raise RuntimeError(f"Exit date unavailable for {d}")
        exits.append(cal[i+1+21])
    z["exit_date_21"]=pd.to_datetime(exits)
    z.to_csv(out/"EXPERT_MONTHLY_INTRINSIC.csv",index=False)
    # Fit a *new* regime gate at each January 1, training exclusively on
    # previously matured monthly expert-success comparisons.
    rows=[];fitaudit=[]
    for year in range(START_OOS,2027):
        cutoff=pd.Timestamp(year,1,1)
        train=z[(z.signal_date<cutoff)&(z.exit_date_21<cutoff)]
        test=z[z.signal_date.dt.year.eq(year)]
        assert len(train)>=36 and len(test)>0,(year,len(train),len(test))
        assert train.exit_date_21.max()<cutoff
        prior=(1.0+train.tail_wins.sum())/(2.0+len(train))
        if train.tail_wins.nunique()==1:
            p_tail=np.full(len(test),prior)
            status="CONST_FALLBACK"
        else:
            clf=make_pipeline(SimpleImputer(strategy="median"),
              StandardScaler(),
              LogisticRegression(C=.1,solver="lbfgs",class_weight=None,max_iter=1000))
            clf.fit(train[FEATURES],train.tail_wins)
            p_tail=clf.predict_proba(test[FEATURES])[:,1]
            status="TRAINED_LOGISTIC"
        t=test.copy()
        t["p_tail"]=p_tail
        t["p_train_prior"]=prior
        t["choose_tail"]=p_tail>0.5
        t["choose_tail_static"]=prior>0.5
        t["chosen_top3"]=np.where(t.choose_tail,t.tail_top3,t.pair_top3)
        t["static_top3"]=np.where(t.choose_tail_static,t.tail_top3,t.pair_top3)
        t["oracle_top3"]=np.maximum(t.tail_top3,t.pair_top3)
        t["model_brier"]=(t.p_tail-t.tail_wins)**2
        t["prior_brier"]=(t.p_train_prior-t.tail_wins)**2
        rows.append(t)
        fitaudit.append({"train_cutoff":str(cutoff.date()),
            "year":year,"train_months":len(train),"last_mature_exit_date":str(train.exit_date_21.max().date()),
            "test_months":len(test),"positive_label_prevalence":float(train.tail_wins.mean()),
            "laplace_prior":prior,"features":FEATURES,"model":"L2 logistic(C=.1) or constant fallback",
            "status":status,"expert_scores_frozen":True,"no_profit_used":True})
        print("V3_L03_OOS",year,len(train),len(test),status,flush=True)
    pred=pd.concat(rows,ignore_index=True)
    assert not pred.signal_date.duplicated().any()
    pred.to_csv(out/"GATE_OOS_MONTHLY.csv",index=False)
    observed=pred.tail_wins.to_numpy(int)
    p_hat=pred.p_tail.to_numpy(float)
    p_prior=pred.p_train_prior.to_numpy(float)
    eps=1e-12
    result={
      "n_test_months":len(pred),"test_first":str(pred.signal_date.min().date()),
      "test_last":str(pred.signal_date.max().date()),
      "tail_wins_event_prevalence":float(observed.mean()),
      "gate_brier":float(brier_score_loss(observed,p_hat)),
      "prior_brier":float(brier_score_loss(observed,p_prior)),
      "brier_skill_vs_prior":float(1-brier_score_loss(observed,p_hat)/brier_score_loss(observed,p_prior)),
      "gate_log_loss":float(log_loss(observed,np.clip(p_hat,eps,1-eps))),
      "prior_log_loss":float(log_loss(observed,np.clip(p_prior,eps,1-eps))),
      "gate_auc":float(roc_auc_score(observed,p_hat)) if len(set(observed))==2 else None,
      "expert_choice_accuracy":float(np.mean((p_hat>.5)==observed)),
      "static_choice_accuracy":float(np.mean((p_prior>.5)==observed)),
      "gate_top3":float(pred.chosen_top3.mean()),
      "static_train_prior_top3":float(pred.static_top3.mean()),
      "always_pair_top3":float(pred.pair_top3.mean()),
      "always_tail_top3":float(pred.tail_top3.mean()),
      "oracle_future_best_top3":float(pred.oracle_top3.mean()),
      "relative_gain_vs_static":float((pred.chosen_top3-pred.static_top3).mean()),
      "relative_gain_vs_best_fixed":float(pred.chosen_top3.mean()-max(pred.pair_top3.mean(),pred.tail_top3.mean())),
      "feature_list":FEATURES,
      "note":"The oracle is retrospective and cannot be used for live model choice."}
    (out/"RESULTS.json").write_text(json.dumps(result,indent=2))
    (out/"FIT_AUDIT.json").write_text(json.dumps(fitaudit,indent=2))
    # Paired month block intervals for actual practical choice uplift.
    d=(pred.chosen_top3-pred.static_top3).to_numpy(float)
    ds=(pred.model_brier-pred.prior_brier).to_numpy(float)
    N=len(d);reps=6000;block=6;rng=np.random.default_rng(20261021)
    starts=rng.integers(0,N,size=(reps,int(np.ceil(N/block))))
    ix=((starts[:,:,None]+np.arange(block))%N).reshape(reps,-1)[:,:N]
    stats=[]
    for title,delta in [("gate_minus_static_monthly_top3",d),("gate_minus_prior_brier",ds)]:
        samples=delta[ix].mean(axis=1)
        stats.append({"metric":title,"mean_delta":float(delta.mean()),
           "ci95_lower":float(np.quantile(samples,.025)),
           "ci95_upper":float(np.quantile(samples,.975)),
           "unit":"month; paired 6-month circular block bootstrap 6000 reps"})
    pd.DataFrame(stats).to_csv(out/"PAIRED_MONTH_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps({
      "layer":"L03 market-regime classifier",
      "question":"Predict which frozen expert captures more next-21D basket winners",
      "ranker_run":39652989033,"tail_run":39655513813,
      "raw_run":39482809691,"frozen_baskets":500,
      "train":"annually refit, prior fully mature 21D expert outcomes only",
      "test":"2022 through 2026 with fully mature forward labels",
      "no_tail_or_compact_retraining":True,"allocation_or_risk_change":False,
      "no_CAGR":True,"not_virgin_holdout":True},indent=2))
    print("V3_L03_REGIME_RESULTS",json.dumps(result,sort_keys=True),flush=True)

if __name__=="__main__":main()
