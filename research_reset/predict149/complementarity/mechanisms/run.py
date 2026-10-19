#!/usr/bin/env python3
"""T149-Ib: only two precommitted causal factor-vs-growth and basket-risk tests."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from oasis149.canonical import sha,SRC
from research_reset.predict149.complementarity.run import (
    from_archive,monthly_weights,trade_policy,metrics,bootstrap,K)
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/"research_reset/predict149/complementarity/results"
POLICIES=("F3","H1","H3","STATIC_F3_H1_50",
          "OIL_VS_GROWTH_63","INVERSE_BASKET_VOL63")

def dynamic_weights(closes,asof,f3,h1):
    """No post-signal price is accessed here."""
    prices=np.log(closes.loc[:asof,list(dict.fromkeys(["USO","QQQ"]+f3+h1))].where(
        closes.loc[:asof,list(dict.fromkeys(["USO","QQQ"]+f3+h1))]>0))
    if len(prices)<70:raise AssertionError("Insufficient as-of factor history")
    prioroil=float(prices.USO.iloc[-1]-prices.USO.iloc[-64])
    priorqqq=float(prices.QQQ.iloc[-1]-prices.QQQ.iloc[-64])
    decision="H1" if prioroil>priorqqq else "F3"
    x=prices.diff().tail(63)
    rvF=float(x[f3].mean(axis=1).std(ddof=1))
    rvH=float(x[h1].mean(axis=1).std(ddof=1))
    if not np.isfinite([prioroil,priorqqq,rvF,rvH]).all() or min(rvF,rvH)<=0:
        raise AssertionError("Invalid as-of oil/growth/risk distribution")
    frac=float(np.clip(rvH/(rvF+rvH),.2,.8))
    oilw=monthly_weights([(decision,1.,f3 if decision=="F3" else h1)])
    riskw=monthly_weights([("F3",frac,f3),("H1",1-frac,h1)])
    return oilw,riskw,dict(oil63=prioroil,growth63=priorqqq,
          factor_oil_minus_growth=prioroil-priorqqq,
          preferred_expert=decision,
          asof_f3_dailyvol=rvF,asof_h1_dailyvol=rvH,
          allocated_weight_f3_inverse_risk=frac)

def run(dest):
    out=Path(dest);out.mkdir(parents=True,exist_ok=False)
    pred,old,roster,O,C,days,signals,ids,selection=from_archive()
    path=BASE/"RESULT.json"
    assert path.exists(), "Run T149-I scientific discovery with prereg first"
    previous=json.loads(path.read_text())
    assert previous["replay_max_abs_error"]["F3"]<1e-9
    assert previous["replay_max_abs_error"]["H1"]<1e-9
    weights={name:[] for name in POLICIES}
    rows=[]
    for k,b in enumerate(ids):
        F=selection["F3"][k];H=selection["H1"][k]
        wOil,wRisk,detail=dynamic_weights(C,pd.Timestamp(signals[b*K]),F,H)
        rows.append(dict(eval_month=k,prior_signal=str(pd.Timestamp(signals[b*K]).date()),
            entry_open=str(pd.Timestamp(days[b*K]).date()),**detail))
        weights["F3"].append(monthly_weights([("F3",1.,F)]))
        weights["H1"].append(monthly_weights([("H1",1.,H)]))
        weights["H3"].append(monthly_weights([("H3",1.,selection["H3"][k])]))
        weights["STATIC_F3_H1_50"].append(monthly_weights([("F3",.5,F),("H1",.5,H)]))
        weights["OIL_VS_GROWTH_63"].append(wOil)
        weights["INVERSE_BASKET_VOL63"].append(wRisk)
    window=days[ids[0]*K:(ids[-1]+1)*K+1]
    stats={};wealth={}
    previous_sources={x:x for x in ("F3","H1","H3","STATIC_F3_H1_50")}
    priorcsv=pd.read_csv(BASE/"EXPERTS_AND_REAL_COSTED_MIXTURES_DAILY.csv")
    for key in POLICIES:
        path,turn=trade_policy(weights[key],O,days,ids,list(roster.ticker))
        if key in previous_sources:
            oldseries=priorcsv[previous_sources[key]].to_numpy(float)
            err=float(np.max(abs(path-oldseries)))
            if err>1e-9:raise AssertionError("Exact original strategy replay mismatch "+key+"="+str(err))
        wealth[key]=path
        stats[key]=metrics(path,window,turn)
        print("T149IB_MECHANISM_POLICY",key,json.dumps(stats[key]),flush=True)
    paired={};eras={}
    for key in ("OIL_VS_GROWTH_63","INVERSE_BASKET_VOL63"):
        a=np.diff(np.log(wealth[key][::K]))
        d=np.diff(np.log(wealth["STATIC_F3_H1_50"][::K]))
        ci=bootstrap(a-d,20261019+40)
        ciF=bootstrap(a-np.diff(np.log(wealth["F3"][::K])),20261019+41)
        ciH=bootstrap(a-np.diff(np.log(wealth["H1"][::K])),20261019+42)
        paired[key]=dict(growth_vs_50_50=ci,growth_vs_F3=ciF,growth_vs_H1=ciH,
            positive_50_50_months=int(np.sum(a>d)),
            regime_time_asof_only=True)
        masks=np.asarray([pd.Timestamp(signals[b*K]).year<=2023 for b in ids],bool)
        eras[key]=dict(
            year_2021_2023_mean_monthly_log_excess_over_static=float(np.mean((a-d)[masks])),
            year_2024_2026_mean_monthly_log_excess_over_static=float(np.mean((a-d)[~masks])))
    static=stats["STATIC_F3_H1_50"]
    gate={}
    for key in ("OIL_VS_GROWTH_63","INVERSE_BASKET_VOL63"):
        v=stats[key]
        gate[key]=bool(paired[key]["growth_vs_50_50"]["ci95"][0]>0
                       and v["cagr"]>static["cagr"]
                       and v["maxdd_daily_open"]>=static["maxdd_daily_open"]
                       and v["es5_daily"]>=static["es5_daily"]
                       and eras[key]["year_2021_2023_mean_monthly_log_excess_over_static"]>0
                       and eras[key]["year_2024_2026_mean_monthly_log_excess_over_static"]>0)
    q=pd.DataFrame(rows)
    for p in POLICIES:
        q["net_month_log_"+p]=np.diff(np.log(wealth[p][::K]))
    q.to_csv(out/"EXANTE_64_MONTH_MECHANISM_WEIGHTS_AND_RETURNS.csv",index=False)
    d=pd.DataFrame({"day":window})
    for key in POLICIES:d[key]=wealth[key]
    d.to_csv(out/"MECHANISM_TRUE_SHARES_NEXT_OPEN_CASH_PATHS.csv",index=False)
    report=dict(status="EXACT149_COMPLEMENTARITY_POSTHOC_MECHANISTIC_TEST_DONE",
        source_sha=sha(SRC/"universe.csv"),
        n_149=149,n_anchor_months=64,n_daily_open_points=len(window),
        fixed_after_original_I_results=True,
        no_new_forecaster_training=True,
        asof_63day_lookback_frozen=True,
        capital_self_financed_and_10bp_per_side=True,
        same_F3_H1_H3_static_curves_replayed=True,
        policies=stats,
        paired_month_results=paired,
        chronology_era_diagnostics=eras,
        original_dynamic_benchmark=previous["portfolio_results"],
        primary_preregistered_mechanism_gates=gate,
        market_state_comparison_EXPLORATORY=True,
        conclusions_limited_by_repeatedly_mined_2021_2026=True,
        no_trading_production_approval=True,
        notes=["USO oil futures roll ETF vs QQQ Nasdaq relative strength is a coarse proxy",
               "Original 149 are survivor-selected and U.S. listed, no EUR broker spread",
               "Posthoc original result exposure discovery contaminates new hypothesis",
               "Even lower paired bootstrap CI positive cannot certify independent alpha",
               "Same underlying fee accounting and original next-Open fills"])
    (out/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("T149IB_POSTHOC_TWO_MECHANISMS "+json.dumps(report,allow_nan=False),flush=True)
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True)
    run(ap.parse_args().out)
