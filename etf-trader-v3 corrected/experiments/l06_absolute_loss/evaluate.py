#!/usr/bin/env python3
"""V3 L06.4 — absolute-loss capability of the *frozen* risk score on Tail candidates.

No modifications to risk/winner head, Compact ranker, allocation or portfolio.
One predeclared target: next 21 *trading days* ETF adjusted-open return <= -10%.
Only ETF-months actually ranked in Top3 in at least one of 500 canonical
baskets are evaluated. Duplicates from overlapping baskets are removed.
Fit ONLY monotonic probability calibration to this new risk event:
calibrated logistic(p_bad) vs expanding training-only constant prevalence.
All first-stage p_bad and Tail scores came from mature, annual OOS refits
in successful run 39662062361. Annual calibration trains on 2018..prior
year and requires true 21D next-open exit strictly before Jan1 cutoff.
Test 2022..2026 on 53 mature monthly signals. No CAGR, positions or veto.

Uncertainty from resampling **calendar months**, not ETF observations.
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
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss, log_loss

LOSS_THRESHOLD = -0.10
FIRST_TEST_YEAR = 2022
BASKET_SHA = "36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"


def load_baskets(path, tickers):
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == BASKET_SHA
    raw = pd.read_csv(path)
    assert {"ticker", "basket"} <= set(raw.columns)
    raw.ticker = raw.ticker.astype(str).str.upper()
    assert not raw.duplicated(["basket", "ticker"]).any()
    assert set(raw.ticker) <= set(tickers)
    baskets = [
        g.ticker.tolist()
        for _, g in raw.sort_values(["basket", "ticker"]).groupby("basket")
    ]
    assert len(baskets) == 500 and all(len(x) == 24 for x in baskets)
    return baskets


def mature_exit_map(spyfile, dates):
    calendar = pd.DatetimeIndex(pd.to_datetime(
        pd.read_csv(spyfile, usecols=["date"]).date
    ).sort_values().unique())
    exits = {}
    for dt in dates:
        idx = calendar.get_indexer([dt])[0]
        if idx < 0 or idx + 22 >= len(calendar):
            raise ValueError(f"No next-open+21 market date for signal {dt}")
        exits[pd.Timestamp(dt)] = calendar[idx+22]
    return exits


def selected_panel(scores, baskets):
    result = []
    for dt, frame in scores.groupby("signal_date", sort=True):
        if frame.fwd_ret_21.isna().any():
            continue
        g = frame.sort_values("ticker").reset_index(drop=True)
        assert len(g) == 149
        assert np.isfinite(g[["p_bad", "TAIL_ELITE45", "fwd_ret_21"]].to_numpy(float)).all()
        pos = {t: i for i,t in enumerate(g.ticker)}
        scores_tail = g.TAIL_ELITE45.to_numpy(float)
        union = set()
        for basket in baskets:
            ids = np.array([pos[t] for t in basket], dtype=int)
            best = np.argsort(-scores_tail[ids], kind="stable")[:3]
            union.update(ids[best].tolist())
        assert len(union) >= 20
        for i in sorted(union):
            fwd = float(g.fwd_ret_21.iloc[i])
            result.append({
                "signal_date": pd.Timestamp(dt),
                "ticker": str(g.ticker.iloc[i]),
                "p_bad": float(g.p_bad.iloc[i]),
                "tail_score": float(g.TAIL_ELITE45.iloc[i]),
                "fwd_ret_21": fwd,
                "abs_loss10": int(fwd <= LOSS_THRESHOLD)
            })
    out = pd.DataFrame(result)
    assert out.signal_date.nunique() == 101
    assert not out.duplicated(["signal_date", "ticker"]).any()
    assert np.isfinite(out[["p_bad", "fwd_ret_21"]]).all().all()
    return out


def predictive_measures(g, score, calibrated=False):
    y = g.abs_loss10.to_numpy(dtype=int)
    x = g[score].to_numpy(float)
    assert np.isfinite(x).all()
    result = {
        "n": len(y),
        "n_loss_events": int(y.sum()),
        "loss_event_fraction": float(y.mean()),
        "average_precision": float(average_precision_score(y,x)) if np.unique(y).size==2 else np.nan,
        "auc": float(roc_auc_score(y,x)) if np.unique(y).size==2 else np.nan
    }
    if calibrated:
        result["brier"] = float(brier_score_loss(y,x))
        result["log_loss"] = float(log_loss(y,np.clip(x,1e-12,1-1e-12),labels=[0,1]))
    return result


def bootstrap(pred):
    # Contiguous monthly circular 6-block resampling; evaluate pooled scores
    # per resample, avoiding independence claims for overlapping ETF histories.
    months = sorted(pred.signal_date.unique())
    assert len(months) == 53
    groups = [pred[pred.signal_date == d] for d in months]
    rng=np.random.default_rng(20261021)
    reps=1500
    block=6
    n=len(groups)
    starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
    index=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
    vals=[]
    for j in range(reps):
        selected=pd.concat([groups[i] for i in index[j]],ignore_index=True)
        y=selected.abs_loss10.to_numpy(dtype=int)
        if y.min()==y.max():continue
        x=selected.p_bad.to_numpy(float)
        cal=selected.p_abs_loss.to_numpy(float)
        prior=selected.p_train_prior.to_numpy(float)
        ap=average_precision_score(y,x)
        base=float(y.mean())
        auc=roc_auc_score(y,x)
        bs0=brier_score_loss(y,prior)
        bs1=brier_score_loss(y,cal)
        vals.append([ap,base,ap-base,ap/base,auc,auc-.5,bs1,bs0,bs1-bs0])
    a=np.array(vals,float)
    assert len(a) >= reps-5
    labels=["AP","event_rate","AP_minus_event_rate","AP_over_event_rate",
            "AUC","AUC_minus_0_5","calibrated_brier","constant_prior_brier","brier_delta"]
    return [
        {"metric":key,"point":None,
         "ci95_low":float(np.quantile(a[:,k],.025)),
         "ci95_high":float(np.quantile(a[:,k],.975)),
         "valid_replications":len(a),
         "method":"calendar month circular blocks of 6, pooled OOS candidates"}
        for k,key in enumerate(labels)
    ]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reference",default="runs/v3_l06_ref")
    ap.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    ap.add_argument("--spy",default="etf_trader_raw/SPY.csv")
    ap.add_argument("--out",default="runs/v3_l06_absolute")
    a=ap.parse_args()
    out=Path(a.out)
    out.mkdir(parents=True,exist_ok=True)
    scores=pd.read_csv(Path(a.reference)/"RISK_SCORES_OOS.csv",parse_dates=["signal_date"])
    assert len(scores)==15198 and not scores.duplicated(["signal_date","ticker"]).any()
    baskets=load_baskets(a.baskets,scores.ticker.unique())
    panel=selected_panel(scores,baskets)
    exit_map=mature_exit_map(a.spy,panel.signal_date.unique())
    panel["exit_date_21"]=panel.signal_date.map(exit_map)
    assert panel.exit_date_21.notna().all()

    fits=[];testlist=[]
    for year in range(FIRST_TEST_YEAR,2027):
        cutoff=pd.Timestamp(year,1,1)
        train=panel[(panel.signal_date<cutoff)&(panel.exit_date_21<cutoff)]
        test=panel[(panel.signal_date.dt.year==year)].copy()
        assert train.signal_date.nunique()>=36 and len(test)>0
        assert train.exit_date_21.max()<cutoff
        assert train.abs_loss10.nunique()==2,year
        pipe=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),
            LogisticRegression(C=.2,class_weight=None,solver="lbfgs",max_iter=1500))
        pipe.fit(train[["p_bad"]],train.abs_loss10.astype(int))
        test["p_abs_loss"]=pipe.predict_proba(test[["p_bad"]])[:,1]
        # Train-only smoothing prevents zero prior and preserves true time split.
        test["p_train_prior"]=(.5+float(train.abs_loss10.sum()))/(1+len(train))
        testlist.append(test)
        fits.append({
            "year":year,"train_months":int(train.signal_date.nunique()),
            "train_unique_ETF_months":len(train),
            "last_exit_date":str(train.exit_date_21.max()),
            "test_months":int(test.signal_date.nunique()),
            "test_unique_ETF_months":len(test),
            "loss_event_rate_train":float(train.abs_loss10.mean()),
            "risk_calibration":"single-feature monotone logistic C=.2",
            "risk_training":False,"ETF_membership_weights_or_PnL_changed":False
        })
        print("V3_ABSOLUTE_RISK_FIT",year,len(train),len(test),flush=True)

    pred=pd.concat(testlist,ignore_index=True)
    assert pred.signal_date.nunique()==53
    assert not pred.duplicated(["signal_date","ticker"]).any()
    pred.to_csv(out/"OOS_SELECTED_ETF_ABSOLUTE_LOSS.csv",index=False)
    byyear=[]
    for year,g in pred.groupby(pred.signal_date.dt.year,sort=True):
        s0=predictive_measures(g,"p_bad")
        s1=predictive_measures(g,"p_abs_loss",True)
        prior=predictive_measures(g,"p_train_prior",True)
        byyear.append({"year":year,**{f"frozen_{k}":v for k,v in s0.items()},
            **{f"cal_{k}":v for k,v in s1.items()},
            **{f"prior_{k}":v for k,v in prior.items()}})
    pd.DataFrame(byyear).to_csv(out/"YEARLY.csv",index=False)
    full_frozen=predictive_measures(pred,"p_bad")
    full_cal=predictive_measures(pred,"p_abs_loss",True)
    full_prior=predictive_measures(pred,"p_train_prior",True)
    # Event-screening diagnostic: top 15% p_bad among unique Tail-selected ETFs,
    # per month; alert threshold fixed before evaluating the future outcome.
    alerts=[]
    for date,g in pred.groupby("signal_date",sort=True):
        threshold=float(g.p_bad.quantile(.85))
        flag=g.p_bad.ge(threshold)
        y=g.abs_loss10.eq(1)
        alerts.append({
            "signal_date":date,
            "n":len(g),"n_flag":int(flag.sum()),"event_count":int(y.sum()),
            "flag_event_precision":float(y[flag].mean()),
            "flag_event_recall":float((y&flag).sum()/max(1,int(y.sum()))),
            "false_positive_rate":float((~y&flag).sum()/max(1,int((~y).sum()))),
        })
    alerts=pd.DataFrame(alerts)
    alerts.to_csv(out/"RISK_ALERT_DIAGNOSTIC.csv",index=False)
    summary={
        "n_months":pred.signal_date.nunique(),
        "n_unique_ETF_months":len(pred),
        "target":"next-open-to-open 21 trading-day adjusted return <= -10%",
        "frozen_pbad":full_frozen,
        "trained_calibrator":full_cal,
        "train_only_prior":full_prior,
        "brier_skill_vs_prior":float(1-full_cal["brier"]/full_prior["brier"]),
        "top15_alert_month_mean_precision":float(alerts.flag_event_precision.mean()),
        "top15_alert_month_mean_recall":float(alerts.flag_event_recall.mean()),
        "top15_alert_month_mean_fpr":float(alerts.false_positive_rate.mean()),
        "note":"This is only a prediction-quality test, not drawdown protection simulation."
    }
    (out/"RESULTS.json").write_text(json.dumps(summary,indent=2))
    ci=bootstrap(pred)
    point={
        "AP":full_frozen["average_precision"],
        "event_rate":full_frozen["loss_event_fraction"],
        "AP_minus_event_rate":full_frozen["average_precision"]-full_frozen["loss_event_fraction"],
        "AP_over_event_rate":full_frozen["average_precision"]/full_frozen["loss_event_fraction"],
        "AUC":full_frozen["auc"],
        "AUC_minus_0_5":full_frozen["auc"]-.5,
        "calibrated_brier":full_cal["brier"],
        "constant_prior_brier":full_prior["brier"],
        "brier_delta":full_cal["brier"]-full_prior["brier"]
    }
    for c in ci:c["point"]=float(point[c["metric"]])
    pd.DataFrame(ci).to_csv(out/"CALENDAR_MONTH_BOOTSTRAP.csv",index=False)
    (out/"FIT_AUDIT.json").write_text(json.dumps(fits,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
      "layer":"L06.4 absolute severe loss identification, frozen original risk",
      "risk_model":39662062361,"tail_expert":39655513813,
      "snapshots":39482809691,"same_canonical_500_baskets":True,
      "candidate_set":"unique ETF-months that are Tail Top3 in at least one canonical basket",
      "one_target":"<=-10% at next open +21 trading days",
      "predeclared_calibration":"single feature logistic C=.2",
      "train_only_prevalence_control":True,
      "evaluation_period":"2022-Jan through 2026-May",
      "no_policy_optimization_or_CAGR":True,
      "historical_exploration_not_virgin_out_of_time":True,
    },indent=2))
    print("V3_ABSOLUTE_LOSS_RISK_RESULTS",json.dumps(summary,indent=2),flush=True)


if __name__=="__main__":
    main()
