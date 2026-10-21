#!/usr/bin/env python3
"""V3 L06.3: Is the loss classifier skilled *conditional on Tail Top-3 selection*?

This is a prediction-only experiment: NO position selection, weight changes,
risk exclusion, or CAGR. Uses immutable, matured 2018-2026 OOS score streams
from successful V3 L06 run 39662062361. Training 2018..prior year, annual
cutoff with actual 21-trading-day target maturation; test 2022..2026.

Label for each selected ETF in each canonical 24-name basket:
  true if its next-21D return ranks among THAT BASKET's worst 3 of 24.
This is deliberately not the old whole-149-ETF bottom-decile label.

Compare frozen global risk score (ranking reference) vs:
  BASE_CALIBRATED: logistic calibration of ONLY frozen p_bad.
  CONDITIONED3: same logistic model with p_bad, frozen Tail score
                and pre-trade rank slot (0, .5, 1).
No parameter sweep; both C=0.2, identical matured OOS training rows.
Each unique (month, ETF) has total training weight 1 across all overlapping
basket-selection duplicates, avoiding treating 500 baskets as independent.
Evaluation averages by independent calendar month and block bootstraps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss, log_loss

BASKET_SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
REFERENCE="FROZEN_P_BAD"
CONTROL="BASE_CALIBRATED"
CHALLENGER="CONDITIONED3"
FEATURES=("p_bad","TAIL_ELITE45","rank_slot")
START=2022


def load_baskets(path, tickers):
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==BASKET_SHA
    data=pd.read_csv(path)
    assert {"basket","ticker"} <= set(data.columns)
    data["ticker"]=data.ticker.astype(str).str.upper()
    assert not data.duplicated(["basket","ticker"]).any()
    assert set(data.ticker)<=set(tickers)
    groups=[(str(k),grp.ticker.tolist()) for k,grp in
            data.sort_values(["basket","ticker"]).groupby("basket",sort=True)]
    assert len(groups)==500 and all(len(names)==24 for _,names in groups)
    return groups


def build_candidate_panel(scores,baskets):
    scorecols=["signal_date","ticker","TAIL_ELITE45","p_bad","risk_percentile","fwd_ret_21"]
    assert len(scores)==15198 and not scores.duplicated(["signal_date","ticker"]).any()
    assert set(scorecols)<=set(scores.columns)
    rows=[]
    for date,group in scores.groupby("signal_date",sort=True):
        if group.fwd_ret_21.isna().any():continue  # unfinished next-21D labels
        g=group.sort_values("ticker").reset_index(drop=True)
        assert len(g)==149 and np.isfinite(g[["p_bad","TAIL_ELITE45","fwd_ret_21"]].to_numpy(float)).all()
        where={t:i for i,t in enumerate(g.ticker)}
        y=g.fwd_ret_21.to_numpy(float)
        tail=g.TAIL_ELITE45.to_numpy(float)
        bad=g.p_bad.to_numpy(float)
        pct=g.risk_percentile.to_numpy(float)
        for basket,basket_names in baskets:
            ix=np.array([where[t] for t in basket_names],int)
            y24=y[ix];r24=tail[ix]
            order=np.argsort(-r24,kind="stable")
            selected=order[:3]
            future_worst3=set(np.argsort(y24,kind="stable")[:3].tolist())
            for slot,pos in enumerate(selected):
                idx=int(ix[pos])
                rows.append((date,basket,str(g.ticker.iloc[idx]),slot,
                             float(slot/2),float(bad[idx]),float(tail[idx]),
                             float(pct[idx]),int(int(pos) in future_worst3)))
    cols=["signal_date","basket","ticker","slot","rank_slot",
          "p_bad","TAIL_ELITE45","risk_percentile","bottom3_in_basket"]
    df=pd.DataFrame(rows,columns=cols)
    assert len(df)==101*500*3
    assert df.signal_date.nunique()==101
    assert not df.duplicated(["signal_date","basket","ticker"]).any()
    assert df.bottom3_in_basket.mean()>.08
    return df


def exit_dates(frame,spyfile):
    market=pd.read_csv(spyfile,usecols=["date"])
    calendar=pd.DatetimeIndex(pd.to_datetime(market.date).sort_values().unique())
    # Match original source-only 21 trading-day next-open label maturation:
    # next-open index i+1 and 21 sessions later index i+1+21.
    dates=pd.DatetimeIndex(frame.signal_date.unique())
    index=calendar.get_indexer(dates)
    assert (index>=0).all(),dates[index<0]
    exitvalues={}
    for dt,i in zip(dates,index):
        assert i+22<len(calendar),(dt,i)
        exitvalues[pd.Timestamp(dt)]=calendar[i+22]
    frame["exit_date_21"]=frame.signal_date.map(exitvalues)
    assert frame.exit_date_21.notna().all()


def model(cols):
    return make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(C=.2,class_weight=None,solver="lbfgs",max_iter=1500)
    )


def measure(monthly,scorecol,variant):
    y=monthly.bottom3_in_basket.to_numpy(dtype=int)
    x=monthly[scorecol].to_numpy(float)
    assert np.isfinite(x).all()
    assert np.unique(y).size==2
    # Declared precision/recall at the top risk decile of currently selected names.
    cutoff=float(np.quantile(x,.85))
    flag=(x>=cutoff)
    return {
      "signal_date":monthly.signal_date.iloc[0],
      "year":int(monthly.signal_date.iloc[0].year),
      "variant":variant,
      "n_selected_instances":int(len(y)),
      "bottom3_event_rate":float(y.mean()),
      "average_precision":float(average_precision_score(y,x)),
      "roc_auc":float(roc_auc_score(y,x)),
      "top15_risk_precision":float(y[flag].mean()),
      "top15_risk_recall":float(y[flag].sum()/max(1,y.sum())),
      "brier":float(brier_score_loss(y,x)) if variant!=REFERENCE else np.nan,
      "log_loss":float(log_loss(y,np.clip(x,1e-12,1-1e-12))) if variant!=REFERENCE else np.nan
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reference",default="runs/v3_l06_ref")
    ap.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    ap.add_argument("--spy",default="etf_trader_raw/SPY.csv")
    ap.add_argument("--out",default="runs/v3_l06_conditional")
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    scores=pd.read_csv(Path(a.reference)/"RISK_SCORES_OOS.csv",parse_dates=["signal_date"])
    baskets=load_baskets(a.baskets,scores.ticker.unique())
    panel=build_candidate_panel(scores,baskets)
    exit_dates(panel,a.spy)
    audit=[];results=[];predicted=[]
    for year in range(START,2027):
        cutoff=pd.Timestamp(year,1,1)
        train=panel[(panel.signal_date<cutoff)&(panel.exit_date_21<cutoff)]
        test=panel[panel.signal_date.dt.year==year].copy()
        assert len(train)>50000 and len(test)>0,(year,len(train),len(test))
        assert train.signal_date.nunique()>=36
        assert train.exit_date_21.max()<cutoff
        # Discount repeated use of one ETF in many overlapping canonical baskets.
        # Each (month, ETF) contributes total weight exactly one.
        count=train.groupby(["signal_date","ticker"]).basket.transform("size")
        sample_weight=1/count.to_numpy(float)
        assert np.isfinite(sample_weight).all() and (sample_weight>0).all()
        # Neither model receives the future outcome of any held-out month.
        control=model(["p_bad"])
        conditioned=model(list(FEATURES))
        target=train.bottom3_in_basket.to_numpy(dtype=int)
        control.fit(train[["p_bad"]],target,
                    logisticregression__sample_weight=sample_weight)
        conditioned.fit(train[list(FEATURES)],target,
                    logisticregression__sample_weight=sample_weight)
        test[CONTROL]=control.predict_proba(test[["p_bad"]])[:,1]
        test[CHALLENGER]=conditioned.predict_proba(test[list(FEATURES)])[:,1]
        test[REFERENCE]=test["risk_percentile"]
        predicted.append(test)
        for date,g in test.groupby("signal_date",sort=True):
            for score,arm in [(REFERENCE,REFERENCE),(CONTROL,CONTROL),
                              (CHALLENGER,CHALLENGER)]:
                results.append(measure(g,score,arm))
        audit.append({
          "year":year,"train_rows":len(train),
          "train_unique_month_ETFs":int(train[["signal_date","ticker"]].drop_duplicates().shape[0]),
          "train_months":int(train.signal_date.nunique()),
          "last_fully_mature_21D_exit":str(train.exit_date_21.max()),
          "test_months":int(test.signal_date.nunique()),"test_rows":len(test),
          "training_bottom3_basket_frequency":float(target.mean()),
          "C":.2,"control_features":["p_bad"],"challenger_features":list(FEATURES),
          "ETF_month_duplicate_inverse_weight":True,
          "source_scores_frozen":True,"no_allocation_change":True
        })
        print("V3_L06_CONDITIONAL_YEAR",year,len(train),len(test),flush=True)
    d=pd.DataFrame(results)
    assert not d.duplicated(["variant","signal_date"]).any()
    ref=d[d.variant==REFERENCE].sort_values("signal_date").reset_index(drop=True)
    base=d[d.variant==CONTROL].sort_values("signal_date").reset_index(drop=True)
    treatment=d[d.variant==CHALLENGER].sort_values("signal_date").reset_index(drop=True)
    assert len(ref)==len(base)==len(treatment)==53
    for x in (base,treatment):
        pd.testing.assert_series_equal(ref.signal_date,x.signal_date)
        pd.testing.assert_series_equal(ref.bottom3_event_rate,x.bottom3_event_rate)
        pd.testing.assert_series_equal(ref.n_selected_instances,x.n_selected_instances)
    metrics=["average_precision","roc_auc","top15_risk_precision",
             "top15_risk_recall","brier","log_loss"]
    d.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    pred=pd.concat(predicted,ignore_index=True)
    assert not pred.duplicated(["signal_date","basket","ticker"]).any()
    pred.to_csv(out/"OOS_SELECTED_ETF_SCORES.csv",index=False)
    summary=d.groupby("variant")[metrics].mean()
    summary.insert(0,"months",d.groupby("variant").size())
    summary.to_csv(out/"RESULTS.csv")
    d.groupby(["year","variant"],as_index=False)[metrics].mean().to_csv(out/"YEARLY.csv",index=False)
    boot=[]
    for comparison in [REFERENCE,CONTROL]:
        left=d[d.variant==comparison].sort_values("signal_date").reset_index(drop=True)
        for col in metrics:
            if comparison==REFERENCE and col in ("brier","log_loss"):continue
            delta=(treatment[col]-left[col]).to_numpy(float)
            assert np.isfinite(delta).all(),(comparison,col)
            n=len(delta);block=6;reps=6000
            rng=np.random.default_rng(20261021)
            starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
            ix=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
            sims=delta[ix].mean(axis=1)
            boot.append({
                "arm":CHALLENGER,"reference":comparison,"metric":col,
                "delta":float(delta.mean()),
                "ci95_low":float(np.quantile(sims,.025)),
                "ci95_high":float(np.quantile(sims,.975)),
                "resampling":"paired calendar months, circular 6-month blocks, 6000 replicates"
            })
    pd.DataFrame(boot).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    (out/"FIT_AUDIT.json").write_text(json.dumps(audit,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
        "experiment":"V3 L06.3 selection-conditional loss prediction only",
        "old_global_risk_scores_from_actions_run":39662062361,
        "raw_149_ETF_snapshot_run":39482809691,
        "selection":"frozen Tail top3 each canonical 24-name basket",
        "target":"worst-3 ETF in each basket by mature future21D return",
        "outcome_known_at_signal":False,
        "temporal_outcomes_after_fit_cutoff_allowed":False,
        "train_start":2018,"test_start":2022,"test_end":"2026-05",
        "training_weight_each_month_ticker_sum_one":True,
        "baseline":"calibrated one-feature logistic(p_bad) on identical selected samples",
        "challenger":"logistic(C=.2) on p_bad, Tail score, slot within selection",
        "no_allocation_or_portfolio_change":True,
        "no_CAGR":True,"historical_calendar_reexamined_not_virgin":True
    },indent=2))
    print("V3_L06_3_CONDITIONAL_RESULTS\n"+summary.to_string(),flush=True)


if __name__=="__main__":
    main()
