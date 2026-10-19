#!/usr/bin/env python3
"""Use frozen K1 as relative risk over frozen F3/H1 holdings, never as Top5 selector."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from oasis149.canonical import sha,SRC
from research_reset.predict149.complementarity.run import (
    from_archive,monthly_weights,trade_policy,metrics,bootstrap,K)
ROOT=Path(__file__).resolve().parents[3]
STOCK=ROOT/"research_reset/predict149/walkforward_stacking/results"
PREV=ROOT/"research_reset/predict149/complementarity/results"
METHODS=("STATIC_F3_H1_50","L1_K1_WITHIN","L2_K1_BETWEEN",
         "L3_K1_TWO_LEVELS","L4_VOL63_WITHIN","H3_FROZEN")
SEED=20261019

def allocate(f,h,dat,kind):
    """Exactly F3/H1 names, no replacement; share weights sum 1."""
    def scale(names,col,damp):
        x=dat.loc[names,col].to_numpy(float)
        if not np.isfinite(x).all() or (x<=0).any():
            raise AssertionError("Invalid as-of risk forecast")
        s=np.clip((damp+x.mean())/(damp+x),.5,1.5)
        return s/s.sum()
    if kind=="STATIC_F3_H1_50":
        return monthly_weights([("F3",.5,f),("H1",.5,h)])
    if kind=="H3_FROZEN":raise AssertionError("H3 handled separately")
    if kind=="L4_VOL63_WITHIN":
        sf=scale(f,"v63",.005);sh=scale(h,"v63",.005)
        fmass=.5
    else:
        sf=scale(f,"P_DOWN5",.05) if kind in ("L1_K1_WITHIN","L3_K1_TWO_LEVELS") else np.full(5,.2)
        sh=scale(h,"P_DOWN5",.05) if kind in ("L1_K1_WITHIN","L3_K1_TWO_LEVELS") else np.full(5,.2)
        if kind in ("L2_K1_BETWEEN","L3_K1_TWO_LEVELS"):
            pf=float(dat.loc[f,"P_DOWN5"].mean())
            ph=float(dat.loc[h,"P_DOWN5"].mean())
            fmass=.6 if pf+.03<ph else (.4 if ph+.03<pf else .5)
        else:fmass=.5
    weights={}
    for tick,x in zip(f,sf):weights[tick]=weights.get(tick,0)+fmass*float(x)
    for tick,x in zip(h,sh):weights[tick]=weights.get(tick,0)+(1-fmass)*float(x)
    assert abs(sum(weights.values())-1)<1e-12
    assert set(weights)==set(f+h)
    return weights

def interval(v,seed):
    a=np.asarray(v,float)
    assert len(a)==64
    rng=np.random.default_rng(seed)
    x=[]
    for _ in range(2200):
        indices=[]
        while len(indices)<64:
            k=int(rng.integers(64))
            indices.extend((k+j)%64 for j in range(3))
        x.append(float(np.mean(a[np.array(indices[:64])])))
    return {"mean":float(a.mean()),"ci95":np.quantile(x,[.025,.975]).tolist()}

def evaluate(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    p,old,roster,opens,closes,days,signals,ids,selected=from_archive()
    k1=pd.read_csv(STOCK/"ALL_9536_PREQUENTIAL_STACKING_FORECASTS.csv")
    assert len(k1)==9536 and k1.groupby("block").size().eq(149).all()
    assert set(k1.block)==set(ids)
    for x in ("P_DOWN5","P_UP3","NULL_DOWN5","event_down","is_model_warmup"):
        assert x in k1.columns
    weights={m:[] for m in METHODS}
    log=[]
    for k,b in enumerate(ids):
        f=selected["F3"][k];h=selected["H1"][k]
        raw=k1[k1.block==b].copy()
        previous=p[p.block==b][["ticker","v63","signal"]]
        raw=raw.merge(previous,on="ticker",suffixes=("","_base"),validate="one_to_one")
        assert raw.signal.iloc[0]==str(pd.Timestamp(signals[b*K]).date())
        assert len(raw)==149
        indexed=raw.set_index("ticker")
        warm=bool(raw.is_model_warmup.iloc[0])
        if raw.is_model_warmup.nunique()!=1:raise AssertionError("inconsistent warmup")
        if not warm and (not np.isfinite(raw.P_DOWN5.to_numpy(float)).all()):
            raise AssertionError("K1 current probability missing")
        baseline=allocate(f,h,indexed,"STATIC_F3_H1_50")
        for m in METHODS:
            if m=="H3_FROZEN":
                chosen=monthly_weights([("H3",1.,selected["H3"][k])])
            elif warm:
                chosen=baseline
            else:
                chosen=allocate(f,h,indexed,m)
            if m!="H3_FROZEN" and set(chosen)!=set(f+h):
                raise AssertionError("K1 replaced a ticker selector")
            if warm and m!="H3_FROZEN" and chosen!=baseline:
                raise AssertionError("Risk model active before fitted forecasts")
            weights[m].append(chosen)
        for t in sorted(set(f+h)):
            q=indexed.loc[t]
            log.append(dict(block=int(b),signal=str(pd.Timestamp(signals[b*K]).date()),
                ticker=t,in_f3=t in f,in_h1=t in h,warmup=warm,
                P_DOWN5=None if warm else float(q.P_DOWN5),
                NULL_DOWN5=None if warm else float(q.NULL_DOWN5),
                actual_relative_down5=int(q.event_down),
                historical_vol63=float(q.v63),
                **{"weight_"+m:weights[m][-1].get(t,0.) for m in METHODS if m!="H3_FROZEN"}))
    path={};stats={}
    window=days[ids[0]*K:(ids[-1]+1)*K+1]
    oldbase=pd.read_csv(PREV/"EXPERTS_AND_REAL_COSTED_MIXTURES_DAILY.csv")
    for m in METHODS:
        capital,trade=trade_policy(weights[m],opens,days,ids,list(roster.ticker))
        if m in ("STATIC_F3_H1_50","H3_FROZEN"):
            key="STATIC_F3_H1_50" if m=="STATIC_F3_H1_50" else "H3"
            err=float(np.max(abs(capital-oldbase[key].to_numpy(float))))
            if err>1e-9:raise AssertionError("Original share curve parity failed "+m+" "+str(err))
        path[m]=capital
        stats[m]=metrics(capital,window,trade)
        print("T149L_OVERLAY_ECON",m,json.dumps(stats[m]),flush=True)
    selected_rows=pd.DataFrame(log)
    active=selected_rows.loc[~selected_rows.warmup]
    bydate=[]
    for b,d in active.groupby("block"):
        prob=d.P_DOWN5.to_numpy(float)
        true=d.actual_relative_down5.to_numpy(float)
        prior=d.NULL_DOWN5.to_numpy(float)
        bydate.append(dict(block=int(b),n_holding_slots=len(d),
            predicted_risk_mean=float(prob.mean()),
            actual_event_frequency=float(true.mean()),
            brier_gain_vs_historical_prior=float(np.mean(
                (prior-true)**2-(prob-true)**2)),
            risk_probability_std=float(prob.std())))
    proper=pd.DataFrame(bydate)
    assert len(proper)==51
    # These are distinct held tickers 8..10, not statistically independent slots.
    chance=interval(np.pad(proper.brier_gain_vs_historical_prior.to_numpy(float),
                (13,0),constant_values=0),SEED+10)
    # Extra bootstrap on 51 truly model-predicted dates, group month not ETFs.
    rng=np.random.default_rng(SEED+11)
    gains=proper.brier_gain_vs_historical_prior.to_numpy(float)
    ss=[]
    for _ in range(2000):
        selected_blocks=[]
        while len(selected_blocks)<51:
            i=int(rng.integers(51))
            selected_blocks.extend((i+j)%51 for j in range(3))
        ss.append(float(gains[np.array(selected_blocks[:51])].mean()))
    proprecord=dict(test_months=51,
        selected_8_to_10_held_etfs_per_month=len(active),
        mean_predicted_minus_prior_brier_gain=float(gains.mean()))
    proprecord["3anchor_bootstrap_CI95"]=np.quantile(ss,[.025,.975]).tolist()
    proprecord["mean_predicted_down_probability"]=float(active.P_DOWN5.mean())
    proprecord["realized_event_rate"]=float(active.actual_relative_down5.mean())
    score={}
    years=np.array([pd.Timestamp(signals[b*K]).year for b in ids])
    month={m:np.diff(np.log(v[::K])) for m,v in path.items()}
    for m in METHODS[1:5]:
        d=month[m]-month["STATIC_F3_H1_50"]
        score[m]=dict(gain=interval(d,SEED+20),
           early_2021_2023=float(np.mean(d[years<=2023])),
           late_2024_2026=float(np.mean(d[years>=2024])),
           months_better=int(np.sum(d>0)),
           preregistered_joint_GO=bool(
               proprecord["3anchor_bootstrap_CI95"][0]>0
               and interval(d,SEED+20)["ci95"][0]>0
               and stats[m]["cagr"]>stats["STATIC_F3_H1_50"]["cagr"]
               and stats[m]["maxdd_daily_open"]>=stats["STATIC_F3_H1_50"]["maxdd_daily_open"]
               and stats[m]["es5_daily"]>=stats["STATIC_F3_H1_50"]["es5_daily"]
               and np.mean(d[years<=2023])>0 and np.mean(d[years>=2024])>0))
    selected_rows.to_csv(out/"ASOF_SELECTED_F3_H1_K1_RISK_AND_WEIGHTS.csv",index=False)
    proper.to_csv(out/"K1_HELD_ETF_EVENT_PROPER_SCORING_BY_MONTH.csv",index=False)
    series=pd.DataFrame({"day":window})
    for m,w in path.items():series[m]=w
    series.to_csv(out/"FULLY_COSTED_RISK_OVERLAY_DAILY_NAV.csv",index=False)
    report=dict(status="ORIGINAL149_K1_AS_RISK_OVERLAY_NOT_SELECTOR_TEST_COMPLETE",
      original149_source_sha=sha(SRC/"universe.csv"),
      n_149=149,n_evaluation_21session_blocks=64,
      n_model_ready_blocks=51,
      original_F3_H1_top5_tickers_unchanged=True,
      legacy_5050_and_H3_share_level_equity_parity=True,
      models_frozen_no_refit=True,
      only_asof_K1_P_DOWN5_risk_forecasts_used=True,
      model_probabilities_on_existing_held_ETFs=proprecord,
      policies=stats,paired_vs_original_5050=score,
      scientific_GO=any(x["preregistered_joint_GO"] for x in score.values()),
      no_independent_PIT_or_future_holdout=True,
      no_production_deployment=True,
      limitations=["Repeatedly mined 2021-2026 cohort of original149 US ETF survivors",
        "K1 negative 5% is relative to 60/40 benchmark, not absolute downside probability",
        "No covariance model for simultaneous extreme declines, 8-10 held tickers correlated",
        "No broker spreads, FX, tax or original fund PIT availability"])
    (out/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("T149L_FINAL_OVERLAY",json.dumps(report,allow_nan=False),flush=True)
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--out",required=True)
    evaluate(a.parse_args().out)
