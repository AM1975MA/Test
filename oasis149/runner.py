#!/usr/bin/env python3
"""Run exact frozen G1/G2 science on canonical 149, no model selection/tuning."""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from oasis149.canonical import load_149,sha,SRC
from oasis.observers import prepare
from oasis_v2.g2.risk_portfolio import ARMS,simulate as g2_simulate, \
    summarize as risk_summary,paired_month_bootstraps
ROOT=Path(__file__).resolve().parents[1]

def env(inputs):
    roster,O,C,V,days,signals,quality=load_149()
    inp=Path(inputs)
    status=json.loads((inp/"MANIFEST_149.json").read_text())
    assert status["status"]=="OASIS_CANONICAL_ORIGINAL149_VERIFIED"
    assert status["member_count"]==149 and status["n_shared_days"]==2366
    assert status["roster_sha256"]==sha(SRC/"universe.csv")
    p0=pd.read_csv(inp/"P0_149_REFERENCE.csv",parse_dates=["day","signal_date"])
    p3=pd.read_csv(inp/"P3_149_SHADOW.csv",parse_dates=["day","signal_date"])
    assert len(p0)==len(p3)==len(days)==2366
    assert all(p0.day==days) and all(p3.day==days)
    assert all(p0.signal_date==signals)
    assert all(p3.signal_date==signals)
    return roster,O,C,V,p0,p3,status

def g1(inp,out):
    from oasis_v2.g1.pairwise import (
        make_dataset,run_predictions,summarize as proper_score,
        bootstrap_anchor_brier,shadow_accepts,VARIANTS)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    roster,O,C,V,p0,p3,status=env(inp)
    ds=make_dataset(roster,C,O,p3)
    predictions=run_predictions(ds)
    assert predictions.anchor.nunique()>=40
    analysis={};era={}
    for task in ("challenge","probe"):
        x=predictions[predictions.pair_type==task]
        analysis[task]={m:proper_score(x.y,x[m]) for m in VARIANTS}
        era[task]={}
        for title,mask in (("2021_2023",pd.to_datetime(x.signal).dt.year<=2023),
                           ("2024_2026",pd.to_datetime(x.signal).dt.year>=2024)):
            frame=x[mask]
            era[task][title]={m:proper_score(frame.y,frame[m]) for m in VARIANTS}
    ci=bootstrap_anchor_brier(predictions)
    overall=analysis["challenge"];p2=overall["H2_GROUP_RESIDUAL"]
    gain=bool(all(p2[k]<overall[other][k] for k in ("brier","log_loss")
                  for other in ("H0_PRIOR","H1_RAW_TREND"))
              and ci["H2_GROUP_RESIDUAL"]["ci95"][0]>0
              and all(era["challenge"][period]["H2_GROUP_RESIDUAL"]["brier"]
                     <era["challenge"][period]["H0_PRIOR"]["brier"]
                     for period in ("2021_2023","2024_2026")))
    shadows=shadow_accepts(predictions)
    wins=[x["realized_net_relative_log"] for x in shadows]
    result=dict(status="CANONICAL149_G1_PREQUENTIAL_COMPLETED",
       G1_PREDICTIVE_GATE="PASS_EXPLORATORY" if gain else "FAIL",
       true_independent_holdout=False,source_roster_is_exact_original149=True,
       n_funds=149,n_anchor_dates=int(predictions.anchor.nunique()),
       n_pair_predictions=len(predictions),
       predicted_event="new_21session_return > incumbent_21session_return + 30bps_log",
       no_legacy_LM_or_future_returns_as_features=True,
       conditional_held_uses_original149_P3_shadow=True,
       asof_label_maturity_verified=bool((
         pd.to_datetime(predictions.latest_training_label_maturity) <
         pd.to_datetime(predictions.signal)).all()),
       by_task=analysis,by_era=era,
       block_anchor_ci=ci,
       H2_shadow_actions=dict(n=len(shadows),
           mean_net_relative_log=float(np.mean(wins)) if wins else None,
           share_win=float(np.mean(np.asarray(wins)>0)) if wins else None,
           decisions=shadows),
       original149_sha256=sha(SRC/"universe.csv"),
       notes=["Previously mined original149! No prospective superiority claims",
           "Pair outcome labels within anchor correlated",
           "Score proxy not a validated EUR risk adjusted investment"],
       research_decision="BLOCK_PORTFOLIO_FROM_G1_UNLESS_PROPER_SCORE_GATE_PASSES")
    predictions.to_csv(out/"PREDICTIONS_149.csv",index=False)
    (out/"RESULT_149_G1.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("OASIS149_G1_RESULT "+json.dumps(result,allow_nan=False),flush=True)

def passive(quotes,dates,weights):
    p={name:quotes.loc[dates,name].to_numpy(float) for name in weights}
    if any(not np.isfinite(x).all() or np.min(x)<=0 for x in p.values()):
        raise AssertionError("passive missing open")
    wealth=sum(weight*p[name]/p[name][0] for name,weight in weights.items())
    years=(dates[-1]-dates[0]).days/365.25
    return {"cagr":float(wealth[-1]**(1/years)-1),
         "maxdd":float(np.min(wealth/np.maximum.accumulate(wealth)-1)),
         "terminal_multiple":float(wealth[-1]),
         "cost_match":"passive buy-hold gross context, NOT cost matched"}

def g2(inp,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    roster,O,C,V,p0,p3,status=env(inp)
    f=prepare(C)
    tables={};metrics={}
    for arm in ARMS:
        ledger=g2_simulate(arm,roster,O,C,p0,f)
        if len(ledger)!=len(p0) or not (ledger.day==p0.day.dt.strftime("%Y-%m-%d")).all():
            raise AssertionError("Not common daily timeline "+arm)
        metrics[arm]=risk_summary(ledger)
        tables[arm]=ledger
        ledger.to_csv(out/(arm+".csv"),index=False)
        print("OASIS149_G2_ARM "+arm+" "+json.dumps(metrics[arm]),flush=True)
    # Independent simulator agreement on the exact original 149 lineup,
    # signals, next-open fees and daily holdings.
    match=np.max(np.abs(tables["R0_TWO_REFERENCE"].wealth.to_numpy(float)
             -p0.wealth.to_numpy(float)))
    if match>1e-8:raise AssertionError("P0 no economic parity "+str(match))
    r2=metrics["R2_ONE_PER_GROUP_EQUAL"]
    r3=metrics["R3_GROUP_INV_VOL"]
    r0=metrics["R0_TWO_REFERENCE"]
    r1=metrics["R1_TOP6_EQUAL"]
    naive_passive={label:passive(O,p0.day,weights) for label,weights in (
        ("SPY",{"SPY":1.}),
        ("AGG",{"AGG":1.}),
        ("SPY60_AGG40",{"SPY":.6,"AGG":.4}))}
    chronology={}
    for arm,d in tables.items():
        g=d.copy()
        y=pd.to_datetime(g.day).dt.year
        wealth=np.log(g.wealth.to_numpy(float))
        lr=np.diff(wealth,prepend=wealth[0])
        slices={}
        for label,mask in (
          ("2017_2020",y<=2020),
          ("2021_2023",y.between(2021,2023)),
          ("2024_2026",y>=2024)):
            inds=np.flatnonzero(mask.to_numpy())
            a=lr[inds];v=g.wealth.iloc[inds].to_numpy(float)
            slices[label]={"n_days":len(inds),
                "annualized_log_return":float(np.mean(a)*252),
                "annualized_compound_return":float(np.exp(np.mean(a)*252)-1),
                "drawdown_rebased":float(np.min(v/np.maximum.accumulate(v)-1))}
        chronology[arm]=slices
    sample_development_gate={
       arm:bool(metrics[arm]["daily_maxdd"]>r0["daily_maxdd"]
         and metrics[arm]["daily_es5"]>r0["daily_es5"]
         and metrics[arm]["cagr"]>=r0["cagr"]-.03)
       for arm in ("R1_TOP6_EQUAL","R2_ONE_PER_GROUP_EQUAL","R3_GROUP_INV_VOL")}
    report=dict(status="CANONICAL149_G2_RISK_EVALUATION_COMPLETED",
       n_funds=149,n_days=len(p0),asof_source=SRC.as_posix(),
       source_roster_sha256=sha(SRC/"universe.csv"),
       source_verified_149=True,
       two_independent_simulators_P0_parity_error=float(match),
       failed_G1_forecaster_not_used=True,
       same_OASIS_price_score_no_rank_retraining=True,
       no_parameter_tuning=True,
       risks=metrics,
       by_era=chronology,
       paired_12month_bootstrap=paired_month_bootstraps(tables),
       passive_context_not_fee_matched=naive_passive,
       historical_exploratory_risk_gate=sample_development_gate,
       no_unseen_future_holdout=True,
       warnings=["Original149 repeatedly studied and subject to survivorship",
          "Dividend-adjusted historical open not actual broker trade quote",
          "SPY/AGG passive context not cost matched, all in USD not EUR",
          "No actual bid ask, liquidity, tax or spread verification"])
    (out/"RESULT_149_G2.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("OASIS149_G2_RESULT "+json.dumps(report,allow_nan=False),flush=True)

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--input",required=True)
    a.add_argument("--out",required=True)
    a.add_argument("--stage",required=True,choices=("g1","g2"))
    args=a.parse_args()
    {"g1":g1,"g2":g2}[args.stage](args.input,args.out)
