#!/usr/bin/env python3
"""Freeze-controlled risk-layer integration, without model or risk retuning.

This is an exact source-only V3 execution replay with existing risk=True,
using validated time-causal 101-month nested meta-tree choices.
Independent control: risk=False must numerically match the earlier NEXT-OPEN
same-calendar NAV for original ranker and decision-tree correction.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
sys.path.insert(0,str(V3/"src"))
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder,load_baskets
from etf_trader_v3.source_only.execution import replay as original_replay
from etf_trader_v3.source_only.statistics import metrics
SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
WINDOWS={"FULL101":("2018-02-01","2026-06-30"),
         "MATCHED_2022":("2022-02-01","2026-06-30")}
def paired_alpha(a,b,rep=2500):
    assert np.array_equal(a[0],b[0])
    assert a[1].shape==b[1].shape and a[1].shape[0]==500
    aa=np.diff(np.log(np.column_stack((np.ones(500),a[1]))),axis=1)
    bb=np.diff(np.log(np.column_stack((np.ones(500),b[1]))),axis=1)
    x=(bb-aa).mean(axis=0)
    n=len(x);rng=np.random.default_rng(20261024)
    starts=rng.integers(0,n,size=(rep,(n+20)//21))
    ix=((starts[:,:,None]+np.arange(21))%n).reshape(rep,-1)[:,:n]
    ci=np.quantile(x[ix].mean(axis=1)*252,[.025,.975])
    return dict(annual_log_alpha=float(252*x.mean()),
                ci025=float(ci[0]),ci975=float(ci[1]),
                block_trading_days=21,replicates=rep,n_days=n)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--membership",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--decisions",required=True)
    p.add_argument("--score",required=True)
    p.add_argument("--prior-economic",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path(a.membership).read_bytes()).hexdigest()==SHA
    mats,cats,_=load_ticker_csv_folder(a.raw)
    mats={k:v.loc[v.index>=pd.Timestamp("2011-01-01")] for k,v in mats.items()}
    assert len(cats)==149 and set(["BIL","SHV"])<=set(cats)
    baskets=load_baskets(a.membership,cats)
    assert len(baskets)==500
    original=pd.read_csv(a.decisions,parse_dates=["signal_date"])
    assert len(original)==50500 and original.signal_date.nunique()==101
    assert original.groupby("signal_date").basket.nunique().eq(500).all()
    assert original.top1_changed.sum()==2209
    predictions=pd.concat([pd.read_csv(x,parse_dates=["signal_date"]) for x in sorted(Path(a.score).glob("regression/s*/OOS_SCORES.csv"))],ignore_index=True) if Path(a.score).is_dir() else pd.read_csv(a.score,parse_dates=["signal_date"])
    predictions=predictions[predictions.variant.eq("CORRECTED")]
    assert predictions.signal_date.nunique()==102 and predictions.ticker.nunique()==149
    assert not predictions.duplicated(["signal_date","ticker"]).any()
    sc=predictions.pivot(index="signal_date",columns="ticker",values="pred")
    pct=sc.rank(axis=1,pct=True,method="average")
    days=mats["Open"].index
    dates=original.signal_date.drop_duplicates().sort_values()
    tables={"BASE":[],"TREE":[]}
    entry_mapping={}
    for date in dates:
        i=days.searchsorted(date,side="right")
        assert i<len(days) and days[i]>date
        entry_mapping[date]=days[i]
    for row in original.itertuples(index=False):
        date=row.signal_date
        candidates=sorted(set([row.tree_top1,row.top2,row.top3]))
        assert len(candidates)==3
        prices=sc.loc[date]
        orig=sorted(candidates,key=lambda t:(-float(prices[t]),t))
        assert orig[0]==row.base_top1,(date,row.basket,orig,row.base_top1)
        t1,t2=orig[0],orig[1]
        gap=float(pct.loc[date,t1]-pct.loc[date,t2])
        w1=1. if gap>=.12 else .75
        # Regardless of meta corrections, the original Top2 gap and weight
        # policy are unchanged, isolating *ranking corrections* from risk.
        for arm,chosen in (("BASE",(t1,t2)),("TREE",(row.tree_top1,row.top2))):
            tables[arm].append(dict(entry_date=entry_mapping[date],
                basket=int(row.basket),top1=chosen[0],top2=chosen[1],
                w1=w1,w2=1.-w1))
    reference=pd.read_csv(a.prior-economic,parse_dates=["date"])
    results=[]; curves=[];annual=[];contrasts=[]
    for period,(start,end) in WINDOWS.items():
        paths={}
        for arm in ("BASE","TREE"):
            df=pd.DataFrame(tables[arm])
            assert not df.duplicated(["entry_date","basket"]).any()
            assert df.groupby("entry_date").basket.nunique().eq(500).all()
            for risk in (False,True):
                dates_,equity,turnover=original_replay(pd.DataFrame(),mats,baskets,
                    start=start,end=end,cost=.001,risk=risk,allocation_override=df)
                name=arm+("__RISK" if risk else "__NO_RISK")
                if not risk:
                    expected=reference[(reference.window==period)&
                         (reference.arm==arm+"__TOP2")].sort_values("date")
                    assert np.array_equal(dates_,expected.date.to_numpy()),(period,name)
                    np.testing.assert_allclose(equity.mean(axis=0),expected.aggregate_nav.to_numpy(float),
                        rtol=0,atol=1e-10,err_msg="Risk integration MUST reproduce certified 500-basket previous 10bps replay")
                metric=metrics(equity,turnover)
                results.append(dict(window=period,arm=name,risk_active=risk,
                    n_trading_days=len(dates_),fee_bps=10,**metric))
                paths[name]=(dates_,equity,turnover)
                v=pd.Series(equity.mean(axis=0),index=dates_)
                curves.extend(dict(window=period,arm=name,date=d,ensemble_nav=float(e))
                              for d,e in v.items())
                prev=1.
                for year,g in v.groupby(v.index.year):
                    annual.append(dict(window=period,arm=name,year=int(year),
                        ensemble_year_return=float(g.iloc[-1]/prev-1)))
                    prev=float(g.iloc[-1])
                print("RISK_REPLAY",period,name,metric["aggregate_cagr"],metric["aggregate_maxdd"],flush=True)
        for status in ("RISK","NO_RISK"):
            a1=paths["BASE__"+status];a2=paths["TREE__"+status]
            contrasts.append(dict(window=period,comparison="TREE versus BASE",risk=status,
                **paired_alpha(a1,a2)))
        for arm in ("BASE","TREE"):
            x=paths[arm+"__NO_RISK"];y=paths[arm+"__RISK"]
            contrasts.append(dict(window=period,comparison=arm+" risk gate versus no risk",
                risk="RISK_GATE",**paired_alpha(x,y)))
    pd.DataFrame(results).to_csv(out/"RISK_SCORECARD.csv",index=False)
    pd.DataFrame(curves).to_csv(out/"DAILY_RISK_ENSEMBLE.csv",index=False)
    pd.DataFrame(annual).to_csv(out/"YEARLY_RISK_ENSEMBLE.csv",index=False)
    pd.DataFrame(contrasts).to_csv(out/"PAIRED_RISK_ALPHA.csv",index=False)
    (out/"RISK_MANIFEST.json").write_text(json.dumps(dict(
        original_frozen_input_run=40016809498,tree_config_run=40032282233,
        meta_economic_parity_run=40032693599,frozen_raw_run=39482809691,
        source_replay="etf_trader_v3.source_only.execution.replay",
        risk_params_unmodified=True,distress_close_rolling63=True,
        breadth_threshold=.55,z5_threshold=-2,cooldown_days=3,
        risk_exposure_factor=.25,risk_defensives=["BIL","SHV"],
        risk_off_behavior="same source-only risk engine, no parameter search",
        allocation_policy="original percentile gap 0.12, 75/25 else 100/0",
        true_next_open_execution=True,fees_oneway_bps=10,
        baseline_without_risk_parity_1e_10=True,
        production_unchanged=True,historical_calendar_reused=True),indent=2))
    print("RISK_INTEGRATION_PASS",pd.DataFrame(results).to_string(index=False),flush=True)
    print("RISK_ALPHA",pd.DataFrame(contrasts).to_string(index=False),flush=True)
if __name__=="__main__":main()
