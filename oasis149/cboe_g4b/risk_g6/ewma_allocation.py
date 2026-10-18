#!/usr/bin/env python3
"""OASIS149 G6: only monthly full-investment weights change to as-of EWMA126.

Monthly ETF *names* taken from frozen R3. No alpha forecast and no cash
timing; compare matched re-executed historical R3 for strict parity.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from oasis149.canonical import load_149,sha,SRC
from oasis.observers import prepare
from oasis_v2.g2.risk_portfolio import (
    simulate as g2_simulate,execute_targets,limited_weights,
    summarize as economic_summary,paired_month_bootstraps)
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"oasis149/results"
LAMBDA=.97;WMAX=.25;FEE=.001

def ewma_weights(opens,signal,names):
    if len(names)!=6 or len(set(names))!=6:
        raise AssertionError("Frozen R3 must have six unique assets")
    log=np.log(opens.loc[:signal,names].where(opens.loc[:signal,names]>0))
    ret=log.diff().tail(126)
    if len(ret)!=126 or ret.isna().any().any():
        raise AssertionError("Missing 126-day as-of open-to-open history")
    weights=LAMBDA**np.arange(125,-1,-1)
    vals=(ret.to_numpy(float)**2*weights[:,None]).sum(axis=0)/weights.sum()
    if (vals<=0).any() or not np.isfinite(vals).all():
        raise AssertionError("EWMA portfolio risk not calculable")
    return limited_weights({t:1/math.sqrt(float(v)) for t,v in zip(names,vals)},cap=WMAX)

def make_new(reference,opens,roster):
    shares={};cash=1.
    current_month=None
    ledger=[]
    count=0
    for x in reference.itertuples(index=False):
        d=pd.Timestamp(x.day);s=pd.Timestamp(x.signal_date)
        if not s<d:raise AssertionError("Open-before-available-signal leak")
        month=(d.year,d.month)
        trade=month!=current_month
        current_month=month
        quotes=opens.loc[d]
        change=0.;fee=0.;orders=0
        if trade:
            names=str(x.names).split(";")
            if set(roster.set_index("ticker").loc[names].macro_category)!=set(roster.macro_category):
                raise AssertionError("Frozen six category universe drift")
            w=ewma_weights(opens,s,names)
            shares,cash,change,fee,orders=execute_targets(shares,cash,w,quotes)
            count+=1
        wealth=cash+sum(q*float(quotes[t]) for t,q in shares.items())
        if not math.isfinite(wealth) or wealth<=0:
            raise AssertionError("G6 invalid wealth accounting")
        ledger.append(dict(day=str(d.date()),signal_date=str(s.date()),
           arm="R7_EWMA126_INV_VOL",wealth=wealth,
           exposure=float((wealth-cash)/wealth),actual_cash=float(cash/wealth),
           n_orders=orders,rebalanced=int(change>1e-10),
           risk_intervention=0,turnover=change,fee=fee,
           estimated_full_ES=0.,positions=len(shares),
           names=";".join(shares)))
    if count!=114:raise AssertionError("Original 114 month selection sequence drift")
    return pd.DataFrame(ledger)

def periods(df):
    v=df.wealth.to_numpy(float)
    lg=np.diff(np.log(v),prepend=np.log(v[0]))
    year=pd.to_datetime(df.day).dt.year
    x={}
    for title,mask in (("2017_2020",year<=2020),
                      ("2021_2023",year.between(2021,2023)),
                      ("2024_2026",year>=2024)):
        ix=np.flatnonzero(mask.to_numpy())
        z=v[ix]
        x[title]={"n_days":len(ix),
            "annualized_compound_return":float(np.exp(252*np.mean(lg[ix]))-1),
            "drawdown_rebased":float(np.min(z/np.maximum.accumulate(z)-1))}
    return x

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    roster,opens,close,vol,days,signals,quality=load_149()
    prior=pd.read_csv(BASE/"R3_GROUP_INV_VOL.csv")
    p0=pd.read_csv(BASE/"P0_149_REFERENCE.csv",parse_dates=["day","signal_date"])
    if len(prior)!=2366 or len(p0)!=2366:
        raise AssertionError("wrong original149 historical universe")
    if not (pd.to_datetime(prior.day)==days).all():
        raise AssertionError("Frozen G2 reference date drift")
    assert (p0.day==days).all()
    # Must reproduce R3 with independent original engine; no "better engine"
    # is allowed to get free economic advantage from a silent fee convention.
    old=g2_simulate("R3_GROUP_INV_VOL",roster,opens,close,p0,prepare(close))
    parity=float(np.max(np.abs(old.wealth.to_numpy(float)-
                 prior.wealth.to_numpy(float))))
    if parity>1e-8:
        raise AssertionError("ECONOMIC PARITY FAIL "+str(parity))
    new=make_new(prior,opens,roster)
    if len(new)!=2366 or not (new.day==old.day).all():
        raise AssertionError("Not matched portfolio event timeline")
    metrics={"R3_63DAY_INV_VOL":economic_summary(old),
             "R7_EWMA126_INV_VOL":economic_summary(new)}
    ci=paired_month_bootstraps({"R3_63DAY_INV_VOL":old,
          "R7_EWMA126_INV_VOL":new},baseline="R3_63DAY_INV_VOL")
    r3=metrics["R3_63DAY_INV_VOL"];r7=metrics["R7_EWMA126_INV_VOL"]
    uplift=ci["R7_EWMA126_INV_VOL"]
    gate=(r7["daily_maxdd"]>r3["daily_maxdd"] and
        r7["daily_es5"]>r3["daily_es5"] and
        r7["cagr"]>.99*r3["cagr"] and uplift["ci95"][0]>0)
    outcomes={"R3_63DAY_INV_VOL":periods(old),
              "R7_EWMA126_INV_VOL":periods(new)}
    result=dict(status="ORIGINAL149_EWMA_G6_MATCHED_PORTFOLIO_COMPLETED",
      original149_exact=149,source_roster_sha=sha(SRC/"universe.csv"),
      original_R3_replay_parity_error=parity,
      n_study_days=2366,
      no_new_ETF_selection=True,
      no_G1_or_G4_failed_alpha_used=True,
      only_weights_changed_at_same_114_monthly_opens=True,
      fixed_weight_cap_25pct=True,ewma_decay_predeclared=LAMBDA,
      under_volatility_forecast_G5_accepted_as_risk_observer_only=True,
      metrics=metrics,by_era=outcomes,bootstrap_12month_monthly_log=ci,
      preregistered_economic_gate=bool(gate),
      source_already_hindsight_biased=True,
      no_broker_spread_or_EUR_implementation=True,
      historical_repeatedly_mined=True,
      conclusion="RISK_WEIGHTING_DIAGNOSTIC_NOT_NEW_ALPHA")
    new.to_csv(out/"R7_EWMA126_INV_VOL.csv",index=False)
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("OASIS149_G6_EWMA_ECONOMIC_RESULT "+json.dumps(result,allow_nan=False),flush=True)
if __name__=="__main__":main()
