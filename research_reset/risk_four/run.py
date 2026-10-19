#!/usr/bin/env python3
"""Four standalone risk/turnover interventions on frozen original F3/H1 ETF signals.

Yahoo factor proxies are ONLY read up to previous completed Close. Historical
period is heavily mined and cannot independently certify a trading edge.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
from oasis149.canonical import sha, SRC
from research_reset.predict149.complementarity.run import (
    from_archive, monthly_weights, metrics, bootstrap, K,
)

ROOT=Path(__file__).resolve().parents[2]
ARCHIVE=ROOT/"research_reset/predict149/complementarity/results"
ARMS=("B0_STATIC_F3_H1","R1_FACTOR_BALANCE","R2_VOL20",
      "R3_TREND126","R4_BUFFER_RANK")
FACTOR_PROXIES=("SPY","TLT","GLD","USO","HYG","UUP","VNQ","XLE")
FEE=.001

def rebalance_cash(shares, cash, target, quotes):
    """Exact unlevered ETF-only fee model; residual cash neither yields nor pays fee."""
    union=set(shares)|set(target)
    assert all(math.isfinite(float(q)) and q>0 for q in quotes.values())
    mass=sum(target.values())
    assert 0 <= mass <= 1+1e-12 and all(v>=0 for v in target.values())
    pre=float(cash+sum(shares[k]*quotes[k] for k in shares))
    assert pre>0
    mark={t:shares.get(t,0)*quotes[t] for t in union}
    post=pre
    for _ in range(100):
        turnover=sum(abs(post*target.get(t,0.)-mark[t]) for t in union)
        nxt=pre-FEE*turnover
        if abs(nxt-post)<1e-14:
            post=nxt
            break
        post=nxt
    assert post>0
    new_shares={t:post*weight/quotes[t] for t,weight in target.items()
                if weight>1e-14}
    sell=sum(max(mark[t]-post*target.get(t,0.),0.) for t in union)
    buy=sum(max(post*target.get(t,0.)-mark[t],0.) for t in union)
    cash_after=cash+(1-FEE)*sell-(1+FEE)*buy
    intended=post*(1-mass)
    assert abs(cash_after-intended)<1e-9*max(1,post), (cash_after,intended)
    return new_shares, max(0.,cash_after), sell+buy, pre-post


def trade(weightseq, prices, days, ids):
    """1345 daily Opening-price valuation including true idle zero-return cash."""
    assert len(ids)==len(weightseq)==64
    cash=1.;shares={};curve=np.empty(64*K+1)
    fee_total=0.;gross_turnover=0.;rebalances=0
    for k,b in enumerate(ids):
        date=days[b*K]
        tgt=weightseq[k]
        quotes={t:float(prices.loc[date,t]) for t in set(shares)|set(tgt)}
        shares,cash,gross,cost=rebalance_cash(shares,cash,tgt,quotes)
        fee_total+=cost;gross_turnover+=gross
        rebalances+=int(gross>1e-11)
        curve[k*K]=cash+sum(q*quotes[t] for t,q in shares.items())
        for h in range(1,K+1):
            d=days[b*K+h]
            curve[k*K+h]=cash+sum(q*float(prices.loc[d,t]) for t,q in shares.items())
    assert np.isfinite(curve).all() and (curve>0).all()
    cost=dict(fee_notional=fee_total,
              absolute_gross_traded_initial_dollars=gross_turnover,
              trade_dates=rebalances,
              avg_underlying_positions=float(np.mean([len(x) for x in weightseq])),
              mean_invested_fraction=float(np.mean([sum(x.values()) for x in weightseq])),
              minimum_invested_fraction=float(min(sum(x.values()) for x in weightseq)))
    return curve,cost


def last_log_returns(closes, chosen, signal, windows):
    """As-of source; all dates are strictly <= completed previous Close."""
    assert pd.Timestamp(signal) in closes.index
    sample=closes.loc[:signal,chosen].dropna().tail(windows+1)
    assert len(sample)==windows+1
    assert sample.index[-1]==pd.Timestamp(signal)
    x=np.log(sample.to_numpy(float))
    r=np.diff(x,axis=0)
    assert np.isfinite(r).all()
    return sample.index,r,x[-1]-x[0]


def factor_weights(weights, closes, factor_close, signal):
    """Prior126 absolute correlations choose ONE proxy label; balance cluster mass."""
    chosen=sorted(weights)
    index, etf_ret, momentum=last_log_returns(closes,chosen,signal,126)
    proxy_past=factor_close.loc[:pd.Timestamp(signal)].reindex(index).ffill()
    assert proxy_past.index[-1]==pd.Timestamp(signal)
    assert proxy_past.shape==(127,len(FACTOR_PROXIES))
    assert np.isfinite(proxy_past.to_numpy(float)).all()
    prox=np.diff(np.log(proxy_past[list(FACTOR_PROXIES)].to_numpy(float)),axis=0)
    assert np.isfinite(prox).all()
    scores={}
    groups={}
    for j,t in enumerate(chosen):
        corr=[float(np.corrcoef(etf_ret[:,j],prox[:,k])[0,1])
              for k in range(len(FACTOR_PROXIES))]
        if not np.isfinite(corr).all():
            raise AssertionError("invalid asof factor correlation "+t)
        ix=int(np.argmax(np.abs(corr)))
        label=FACTOR_PROXIES[ix] if abs(corr[ix])>=.25 else "OTHER"
        groups[t]=label
        scores[t]=float(corr[ix])
    names=set(groups.values())
    group_w={g:sum(v for t,v in weights.items() if groups[t]==g)
             for g in names}
    # Partially equalize factors, but retain each selected ETF and 100% capital.
    out={t:weights[t]*(.5*group_w[groups[t]]+.5/len(names))/
            group_w[groups[t]] for t in chosen}
    assert abs(sum(out.values())-1)<1e-12
    assert set(out)==set(weights)
    return out,dict(distinct_factors=len(names),assigned=groups,
                    correlations=scores,max_original_factor_weight=max(group_w.values()),
                    max_new_factor_weight=max(sum(v for t,v in out.items()
                                                  if groups[t]==g) for g in names))


def vol20_weights(weights, closes, signal):
    chosen=sorted(weights)
    _,r,_=last_log_returns(closes,chosen,signal,63)
    cov=np.cov(r,rowvar=False)
    cov=.5*cov+.5*np.diag(np.diag(cov))
    w=np.array([weights[t] for t in chosen])
    v=float(np.sqrt(max(1e-14, w@cov@w)*252.))
    exposure=float(np.clip(.20/v,.40,1.))
    return {t:exposure*weights[t] for t in chosen}, dict(
        asof_annualized_portfolio_vol=v,invested=exposure)


def trend126_weights(weights, closes, signal):
    chosen=sorted(weights)
    _,_,momentum=last_log_returns(closes,chosen,signal,126)
    mom=float(np.dot(np.array([weights[t] for t in chosen]),momentum))
    exposure=0.5 if mom<0 else 1.
    return {t:exposure*weights[t] for t in chosen}, dict(
        asof_selected_126d_log_momentum=mom,invested=exposure)


def buffer_expert(scores, expert, old, orig):
    """Original pre-signal ranking only. Retain top10 previous members close to rank5."""
    assert scores.index.is_unique and len(scores)==149
    ordered=scores.sort_values(ascending=False,kind="mergesort")
    assert set(orig)==set(ordered.head(5).index)
    if not old:
        return list(orig)
    std=float(scores.std(ddof=1))
    fifth=float(ordered.iloc[4])
    top10=set(ordered.index[:10])
    retained=[t for t in old if t in top10 and float(scores[t])>=fifth-.15*std]
    retained=sorted(retained,key=lambda t:(-float(scores[t]),t))[:5]
    chosen=list(retained)
    for t in ordered.index:
        if len(chosen)==5:break
        if t not in chosen:chosen.append(t)
    assert len(set(chosen))==5
    return chosen


def read_factors(path):
    frame=pd.read_csv(path,parse_dates=["date"]).set_index("date").sort_index()
    assert list(frame.columns)==list(FACTOR_PROXIES)
    assert frame.index.is_unique
    assert (frame.index.max()<=pd.Timestamp("2026-07-02"))
    assert np.isfinite(frame.to_numpy(float)[np.isfinite(frame.to_numpy(float))]).all()
    return frame


def run(factors_path, folder):
    out=Path(folder)
    out.mkdir(parents=True,exist_ok=False)
    p,old,roster,opens,closes,days,signals,ids,selected=from_archive()
    factors=read_factors(factors_path)
    assert len(ids)==64 and len(set(roster.ticker))==149
    oldcurve=pd.read_csv(ARCHIVE/"EXPERTS_AND_REAL_COSTED_MIXTURES_DAILY.csv")
    weights={name:[] for name in ARMS}
    state_rows=[];ticker_rows=[]
    old_f=[];old_h=[]
    for i,b in enumerate(ids):
        sig=pd.Timestamp(signals[b*K])
        assert sig<pd.Timestamp(days[b*K])
        f=selected["F3"][i];h=selected["H1"][i]
        original=monthly_weights([("F3",.5,f),("H1",.5,h)])
        wfac,diagfac=factor_weights(original,closes,factors,sig)
        wvol,diagvol=vol20_weights(original,closes,sig)
        wtrend,diagtrend=trend126_weights(original,closes,sig)
        here=p.loc[p.block==b].set_index("ticker")
        new_f=buffer_expert(here["B0_F3_FROZEN"],"F3",old_f,f)
        new_h=buffer_expert(here["H1_FACTOR_ONLY"],"H1",old_h,h)
        wbuffer=monthly_weights([("F3",.5,new_f),("H1",.5,new_h)])
        old_f,old_h=new_f,new_h
        for name,w in zip(ARMS,(original,wfac,wvol,wtrend,wbuffer)):
            assert abs(sum(w.values())-(1 if name not in ("R2_VOL20","R3_TREND126")
                                         else sum(w.values())))<1e-12
            assert all(np.isfinite(list(w.values()))) and all(v>=0 for v in w.values())
            if name not in ("R2_VOL20","R3_TREND126"):
                assert abs(sum(w.values())-1.)<1e-12
            if name!="R4_BUFFER_RANK":
                assert set(w)==set(original)
            weights[name].append(w)
            ticker_rows.extend(dict(block=int(b),signal=str(sig.date()),ticker=t,
                       policy=name,weight=float(x)) for t,x in w.items())
        state_rows.append(dict(block=int(b),signal=str(sig.date()),
                   base_names=";".join(sorted(original)),
                   base_factor_count=diagfac["distinct_factors"],
                   max_base_factor_weight=diagfac["max_original_factor_weight"],
                   max_balanced_factor_weight=diagfac["max_new_factor_weight"],
                   asof_vol=diagvol["asof_annualized_portfolio_vol"],
                   vol_invested=diagvol["invested"],
                   trend_momentum=diagtrend["asof_selected_126d_log_momentum"],
                   trend_invested=diagtrend["invested"],
                   buffer_f3_changed=len(set(new_f)^set(f))//2,
                   buffer_h1_changed=len(set(new_h)^set(h))//2,
                   current_expert_overlap=len(set(f)&set(h))))
    window=days[ids[0]*K:(ids[-1]+1)*K+1]
    curves={};stats={}
    for name in ARMS:
        equity,trading=trade(weights[name],opens,days,ids)
        curves[name]=equity
        stats[name]=metrics(equity,window,trading)
        peak=np.maximum.accumulate(equity)
        underwater=equity<peak-1e-12
        longest=0;count=0
        for x in underwater:
            count=count+1 if x else 0
            longest=max(longest,count)
        stats[name]["max_underwater_sessions"]=longest
    parity=float(np.max(np.abs(curves["B0_STATIC_F3_H1"]-
                               oldcurve.STATIC_F3_H1_50.to_numpy(float))))
    if parity>1e-9:
        raise AssertionError("Original F3/H1 financial path changed: "+str(parity))
    paired={}
    years=np.array([pd.Timestamp(signals[b*K]).year for b in ids])
    base=np.diff(np.log(curves["B0_STATIC_F3_H1"][::K]))
    benchmark=stats["B0_STATIC_F3_H1"]
    for j,name in enumerate(ARMS[1:]):
        monthly=np.diff(np.log(curves[name][::K]))
        excess=monthly-base
        ci=bootstrap(excess,seed=20261019+4+j,nrep=3000)
        early=float(excess[years<=2023].mean())
        late=float(excess[years>=2024].mean())
        maxdd_improve=float(stats[name]["maxdd_daily_open"]-
                            benchmark["maxdd_daily_open"])
        gate=bool(ci["ci95"][0]>0 and maxdd_improve>=.03
                  and stats[name]["es5_daily"]>=benchmark["es5_daily"]
                  and early>0 and late>0)
        paired[name]=dict(net_21session_log_gain=ci,
              earlier_2021_2023_mean=early,later_2024_2026_mean=late,
              maxdd_improvement_percentage_points=maxdd_improve*100,
              es5_improvement_percentage_points=
                  (stats[name]["es5_daily"]-benchmark["es5_daily"])*100,
              preregistered_joint_GO=gate)
    path=pd.DataFrame({"day":window})
    for name in ARMS:path[name]=curves[name]
    path.to_csv(out/"FULL_DAILY_NEXT_OPEN_EQUITIES.csv",index=False)
    pd.DataFrame(state_rows).to_csv(out/"ASOF_64_MONTH_RISK_STATES.csv",index=False)
    pd.DataFrame(ticker_rows).to_csv(out/"ASOF_SELECTED_WEIGHTS_ALL_FOUR_ARMS.csv",index=False)
    comparison=dict(
        status="FOUR_INDEPENDENT_F3H1_RISK_ABLATIONS_COMPLETE",
        original149_sha256=sha(SRC/"universe.csv"),
        yahoo_factor_proxy_sha256=hashlib.sha256(Path(factors_path).read_bytes()).hexdigest(),
        original_149=149,investable_periods=64,
        daily_open_wealth_points=1345,
        frozen_original_F3_H1_exact_parity=parity,
        historical_US_survivor_universe_reused=True,
        third_party_factors_not_true_point_in_time=True,
        policies=stats,paired_tests=paired,
        all_strict_gates_passed=[k for k,v in paired.items()
                                 if v["preregistered_joint_GO"]],
        no_deployment=True,
        limitations=["Original 149 US ETF survivor cohort, not EUR trading roster",
                     "Yahoo historical Close updated and not vendor-vintage PIT",
                     "No broker spreads, dividend cash management, live FX or taxes",
                     "Historical dates 2021-2026 extensively mined across prior models",
                     "Zero-interest idle cash; turnover charged on actual ETF trades only"])
    (out/"RESULT.json").write_text(json.dumps(comparison,indent=2)+"\n")
    print("R149_R_FOUR_ABLATIONS "+json.dumps(comparison),flush=True)
    return comparison


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--factors",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    run(args.factors,args.out)
