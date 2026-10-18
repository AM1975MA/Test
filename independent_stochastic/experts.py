"""Price-only stochastic / ergodic ETF experts, fixed parameters from PROTOCOL.md."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from research_bayes_europe.experiment import robust_kalman_score
from scientific_lab.models import daily_asof,market
SEED=20261018
BASE=("D0_BROAD_LOWVOL","D1_ROBUST_STATE","D2_LOG_GROWTH",
      "D3_CONTRARIAN","D4_ENTROPIC_CORRELATION")
ARMS=BASE+("D5_STUDENT_T_SCENARIO","D6_HEDGE_GAME","D7_HEDGE_REGIME","D8_UNIFORM_EXPERTS")

def bounds(weight_map,cap=.2):
    keys=list(weight_map)
    w=np.maximum(np.array([weight_map[t] for t in keys],float),0.)
    if len(w)<math.ceil(1/cap-1e-10):raise ValueError("too few names for bound")
    if not np.isfinite(w).all() or w.sum()<=0:w[:]=1.
    w=w/w.sum()
    for _ in range(60):
        over=w>cap+1e-13
        if not over.any():break
        free=~over
        if not free.any():raise ValueError("too many cap violations")
        w[over]=cap
        left=1.-w[over].sum()
        v=np.maximum(w[free],1e-12)
        w[free]=left*v/v.sum()
    if abs(w.sum()-1)>1e-9 or max(w)>cap+1e-9:
        raise AssertionError("constraint solver")
    return {t:float(x) for t,x in zip(keys,w) if x>1e-9}

def rank_score(items, k, reverse=True):
    finite={t:v for t,v in items.items() if np.isfinite(v)}
    if len(finite)<k:raise ValueError("not enough finite scores")
    return sorted(finite,key=lambda t:(-finite[t] if reverse else finite[t],t))[:k]

def features(close,sd):
    history=close.loc[:sd]
    returns=daily_asof(close,sd)
    out={};readys=[]
    for t in close.columns:
        h=history[t].dropna()
        if len(h)<253 or h.iloc[-1]<=0:continue
        if history.index.get_loc(h.index[-1]) < len(history)-4:continue
        recent=h.iloc[-253:].to_numpy(float)
        if not np.isfinite(recent).all() or min(recent)<=0:continue
        r=np.diff(np.log(recent))
        if np.max(np.abs(r))>.65:continue  # corrupted, unadjusted split risk
        rv=np.std(r[-126:],ddof=1)*math.sqrt(21.)
        if not np.isfinite(rv) or rv<.002:continue
        clipped=np.clip(r,-.08,.08)
        mu_daily=.5*np.mean(clipped[-126:])+.5*np.mean(clipped)
        # Conservative estimation-error penalty: confidence from 126-day effective observations.
        uncertainty=1.5*np.std(clipped[-126:],ddof=1)*math.sqrt(21/126.)
        g=21.*mu_daily-.5*21*np.var(clipped[-126:],ddof=1)-uncertainty
        rev=-(np.log(recent[-1]/recent[-22]))/(rv+1e-8)
        rev+=.25*np.log(recent[-1]/recent[-127])/(rv+1e-8)
        state_mu,pv,ov=robust_kalman_score(history[t],sd)
        state_score=state_mu/math.sqrt(max(pv+ov,1e-8)) if np.isfinite(state_mu+pv+ov) else float(mu_daily*21./max(rv,.002))
        out[t]={"vol":float(rv),"growth":float(g),"reverse":float(rev),
                "kalman":float(state_score),"daily_mu":float(mu_daily),
                "ret":returns[t].dropna().tail(252)}
        readys.append(t)
    return out,returns,readys

def expert_allocations(feat,daily):
    if len(feat)<12:raise ValueError(f"Too few history-ready ETFs: {len(feat)}")
    vol={t:x["vol"] for t,x in feat.items()}
    grow={t:x["growth"] for t,x in feat.items()}
    kal={t:x["kalman"] for t,x in feat.items()}
    rev={t:x["reverse"] for t,x in feat.items()}
    low=rank_score(vol,10,reverse=False)
    state=rank_score(kal,5)
    Kelly=rank_score(grow,8)
    anti=rank_score(rev,8)
    d0=bounds({t:1/max(vol[t],.02) for t in low},cap=.20)
    d1=bounds({t:1/max(vol[t],.02) for t in state},cap=.25)
    d2=bounds({t:1/max(vol[t],.02) for t in Kelly},cap=.20)
    d3=bounds({t:1/max(vol[t],.02) for t in anti},cap=.20)
    # Greedy residual-correlation selection on 20 leading conservative log growers.
    leader=rank_score(grow,20)
    corr=daily[leader].tail(126).corr(min_periods=90).fillna(0)
    ranks={t:(20-i)/20 for i,t in enumerate(leader)}
    chosen=[]
    for i in range(8):
        candidates=[t for t in leader if t not in chosen]
        def value(t):
            worst=max([max(float(corr.loc[t,u]),0) for u in chosen],default=0.)
            return .5*ranks[t]-.8*worst
        selected=max(candidates,key=lambda t:(value(t),t))
        chosen.append(selected)
    d4=bounds({t:1/max(vol[t],.02) for t in chosen},cap=.20)
    return dict(zip(BASE,(d0,d1,d2,d3,d4)))

def correlated_student_scenarios(feat,daily,month_index,n=384):
    # Common realized covariance innovations retain correlation and fat tails
    names=sorted(feat)
    a=daily[names].tail(252).to_numpy(float)
    mean=np.nanmean(a,axis=0)
    for j in range(a.shape[1]):a[~np.isfinite(a[:,j]),j]=mean[j]
    a=np.clip(a,-.08,.08)
    cov=np.cov(a,rowvar=False)
    shrink=.65*cov+.35*np.diag(np.diag(cov))
    L=np.linalg.cholesky(shrink+np.eye(len(names))*1e-8)
    mu=np.array([feat[t]["daily_mu"] for t in names])
    rng=np.random.default_rng(SEED+month_index)
    z=rng.normal(size=(n,len(names)))
    chisq=rng.chisquare(df=5,size=n)
    shocks=z*np.sqrt(3./np.maximum(chisq[:,None],1e-10))
    x=21*mu[None,:]+math.sqrt(21.)*shocks@L.T
    return names,np.exp(np.clip(x,-1.,1.))

def stochastic_scenario_choose(experts,feat,daily,month_index,prior):
    names,gross=correlated_student_scenarios(feat,daily,month_index)
    scenario={}
    for policy,w in experts.items():
        ww=np.array([w.get(t,0.) for t in names],float)
        cash=1-ww.sum()
        if abs(cash)>1e-9:raise AssertionError("all shadow experts fully allocated")
        factors=np.maximum(gross@ww,1e-8)
        logs=np.log(factors)
        penalty_tail=-np.mean(np.sort(logs)[:max(1,int(.10*len(logs)))])
        # Anti-concentration measure and penalty against useless trading.
        turn=.5*sum(abs(w.get(t,0.)-prior.get(t,0.)) for t in set(w)|set(prior))
        utility=float(np.mean(logs)-.25*penalty_tail-.001*turn)
        scenario[policy]=utility
    # Prespecified tie order; this action is selected on SIMULATED as-of data.
    best=max(BASE,key=lambda name:(scenario[name],-BASE.index(name)))
    return best,scenario

def weighted_mix(experts,coeff):
    all_names=set().union(*(set(v) for v in experts.values()))
    mixed={t:sum(float(coeff[k])*experts[k].get(t,0.) for k in BASE)
             for t in all_names}
    return bounds(mixed,cap=.20)

def softmax_experts(state):
    z=np.array([state[p] for p in BASE],float)
    z=5*(z-np.max(z))
    w=np.exp(z);w/=w.sum()
    for _ in range(50):
        over=w>.45+1e-12
        if not over.any():break
        free=~over
        a=1-.45*int(over.sum())
        if a<0:raise AssertionError("more than two weights above cap")
        w[over]=.45
        w[free]=a*w[free]/w[free].sum()
    return dict(zip(BASE,w))

def synthetic_no_future_test():
    dates=pd.bdate_range("2013-01-02",periods=1500)
    m=np.arange(len(dates))
    x=pd.DataFrame({f"x{i}":np.exp(np.cumsum(.0001+.004*np.sin(m/(13+i))))
                    for i in range(24)},index=dates)
    sd=dates[1200];f,ret,e=features(x,sd)
    af=expert_allocations(f,ret)
    y=x.copy();y.loc[y.index>sd]*=12.35
    f2,ret2,e2=features(y,sd)
    bf=expert_allocations(f2,ret2)
    assert e==e2 and set(af)==set(bf)
    for k in af:
        assert all(abs(af[k].get(t,0)-bf[k].get(t,0))<1e-12
                   for t in set(af[k])|set(bf[k]))
    a,sc=stochastic_scenario_choose(af,f,ret,1,{})
    b,sb=stochastic_scenario_choose(bf,f2,ret2,1,{})
    assert a==b and sc==sb
    print("INDEPENDENT_PRICE_ONLY_NO_LOOKAHEAD_PASS",flush=True)
