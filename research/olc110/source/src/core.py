"""OLC106: fixed, causal, long-only research screen; no live orders.
Fractional economic units on frozen adjusted O/C proxies, NOT physical shares.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

ARMS=("PASSIVE","MOM252_TOP2","DIVERSE_TREND","DIVERSE_RISK15","DIVERSE_GUARD")

def capped_inverse_vol(vol, cap=.25):
    vol=np.asarray(vol,float)
    if np.any(~np.isfinite(vol)) or np.any(vol<=0):raise ValueError("VOL")
    n=len(vol);w=np.zeros(n)
    if n==0:return w
    remaining=min(1.,cap*n);active=np.ones(n,bool)
    for _ in range(n+1):
        if not active.any():break
        idx=np.flatnonzero(active);proposed=remaining*(1/vol[idx])/(1/vol[idx]).sum()
        saturated=proposed>cap+1e-14
        if not saturated.any():w[idx]=proposed;break
        fixed=idx[saturated];w[fixed]=cap;remaining-=cap*len(fixed);active[fixed]=False
    assert w.max()<=cap+1e-10 and w.sum()<=1.+1e-10
    return w

def rebalance(units,cash,prices,weights,ticket,impact,band=.03,force=False,mark=None):
    """Sell first, then self-finance purchases. Missing Open never receives a fill."""
    u=np.asarray(units,float).copy();p=np.asarray(prices,float);w=np.asarray(weights,float)
    if len(u)!=len(p) or len(w)!=len(p) or (w<0).any() or w.sum()>1+1e-9:raise ValueError("WEIGHTS")
    if ticket<0 or not 0<=impact<1 or (u<0).any() or cash< -1e-8:raise ValueError("ACCOUNT")
    mark=np.asarray(mark if mark is not None else p,float)
    valid=np.isfinite(p)&(p>0)
    if np.any((u>1e-12)&(~np.isfinite(mark)|(mark<=0))):raise ValueError("MISSING_MARK")
    value=u*np.where(np.isfinite(mark),mark,0.)
    wealth=float(cash+value.sum())
    desired=wealth*w;diff=desired-value;orders=[]
    threshold=max(1e-8,(0. if force else band)*wealth)
    for j in np.flatnonzero(valid&(diff< -1e-8)&((np.abs(diff)>=threshold)|(w==0))):
        qty=min(u[j],-diff[j]/p[j])
        notional=qty*p[j];cost=ticket+impact*notional
        if notional<=cost and cash+notional<cost:continue
        u[j]-=qty;cash+=notional-cost
        orders.append(dict(j=int(j),side="SELL",quantity=float(qty),price=float(p[j]),notional=float(notional),cost=float(cost)))
    # Freeze the original requested target; do not invest proceeds beyond that target.
    value_now=u*np.where(np.isfinite(mark),mark,0.)
    requests=np.maximum(0.,desired-value_now)
    ids=np.flatnonzero(valid&(requests>1e-8)&(requests>=threshold))
    if len(ids):
        ids=ids[requests[ids]>ticket]
        if len(ids) and cash>ticket*len(ids):
            scale=min(1.,(cash-ticket*len(ids))/((1+impact)*requests[ids].sum()))
            for j in ids:
                notional=float(requests[j]*scale);cost=ticket+impact*notional
                if notional<=1e-8:continue
                qty=notional/p[j];u[j]+=qty;cash-=notional+cost
                orders.append(dict(j=int(j),side="BUY",quantity=float(qty),price=float(p[j]),notional=notional,cost=float(cost)))
    after=float(cash+np.sum(u*np.where(np.isfinite(mark),mark,0.)))
    err=abs(after+sum(x["cost"] for x in orders)-wealth)
    if cash< -1e-7 or (u< -1e-10).any() or err>max(1e-7,wealth*1e-10):raise AssertionError(("SELF_FINANCING",cash,err))
    return np.maximum(u,0.),max(0.,float(cash)),orders

def features(p):
    C=np.asarray(p["C"],float);obs=np.asarray(p["observed"],bool)
    f=pd.DataFrame(np.where(obs&(C>0)&np.isfinite(C),C,np.nan)).ffill()
    lr=np.log(f/f.shift(1))
    vol=(lr.rolling(63,min_periods=50).std(ddof=1)*np.sqrt(252)).clip(lower=.01)
    m63=np.log(f/f.shift(63));m126=np.log(f/f.shift(126));m252=np.log(f/f.shift(252))
    count=pd.DataFrame(obs).rolling(253,min_periods=253).sum()
    total=np.cumsum(obs,axis=0)
    score=(4*m63+2*m126+m252)/3/vol
    mean200=f.rolling(200,min_periods=200).mean()
    last=np.maximum.accumulate(np.where(obs,np.arange(len(f))[:,None],-1),axis=0)
    dates=pd.DatetimeIndex(p["dates"]).values.astype("datetime64[D]").astype(int)
    age=dates[:,None]-dates[np.maximum(last,0)]
    eligible=(count.to_numpy()>=math.ceil(.95*253))&(total>=253)&(age<=5)&np.isfinite(score.to_numpy())
    trend=(f.to_numpy()>mean200.to_numpy())&(m252.to_numpy()>0)&eligible
    return dict(C=f.to_numpy(),returns=lr.to_numpy(),vol=vol.to_numpy(),score=score.to_numpy(),
                m252=m252.to_numpy(),m21=np.log(f/f.shift(21)).to_numpy(),
                eligible=eligible,trend=trend,above200=(f>mean200).to_numpy())

def covariance_at(f,k,ids,n=63):
    x=f["returns"][max(0,k-n+1):k+1,ids]
    if x.ndim==1:x=x[:,None]
    x=x[np.isfinite(x).all(axis=1)]
    if len(x)<min(50,n):return np.diag(np.maximum(f["vol"][k,ids],.01)**2)
    return np.atleast_2d(np.cov(x,rowvar=False,ddof=1))*252

def chosen_weights(p,f,k,arm):
    w=np.zeros(len(p["names"]))
    if arm=="PASSIVE":w[int(p["benchmark"])]=1.;return w,1.
    ids=np.flatnonzero(f["eligible"][k])
    if arm=="MOM252_TOP2":
        ranked=sorted(ids,key=lambda j:(-f["m252"][k,j],str(p["names"][j])))[:2]
        if len(ranked):w[ranked]=1/len(ranked)
        return w,float(len(ranked))
    ids=np.flatnonzero(f["trend"][k])
    ranked=sorted(ids,key=lambda j:(-f["score"][k,j],str(p["names"][j])))
    selected=[]
    for j in ranked:
        if selected:
            xx=f["returns"][max(0,k-125):k+1,[j]+selected]
            xx=xx[np.isfinite(xx).all(axis=1)]
            if len(xx)<100:continue
            centered=xx-xx.mean(axis=0)
            norm=np.sqrt((centered*centered).sum(axis=0))
            denom=norm[0]*norm[1:]
            cor=np.divide(centered[:,0]@centered[:,1:],denom,out=np.zeros(len(selected)),where=denom>1e-12)
            if np.any(cor>.90):continue
        selected.append(j)
        if len(selected)==6:break
    if selected:
        v=f["vol"][k,selected];w[selected]=capped_inverse_vol(v)
        if arm in ("DIVERSE_RISK15","DIVERSE_GUARD"):
            sig=float(np.sqrt(max(0.,w[selected]@covariance_at(f,k,selected)@w[selected])))
            w*=min(1.,.15/max(sig,1e-12))
    return w,float(len(selected))

def portfolio_metrics(nav,dates,initial=10000.,open_nav=None):
    a=np.asarray(nav,float);d=pd.DatetimeIndex(dates)
    if len(a)<1 or len(a)!=len(d) or np.any(a<=0) or initial<=0:raise ValueError("NAV")
    chain=np.r_[initial,a];dd=chain/np.maximum.accumulate(chain)-1
    days=max(1,(d[-1]-d[0]).days+1);cagr=(a[-1]/initial)**(365.2425/days)-1
    maxdd=float(dd.min())
    both=chain
    if open_nav is not None:
        both=np.r_[initial,np.column_stack([open_nav,a]).ravel()]
    sampled=float(np.min(both/np.maximum.accumulate(both)-1))
    lr=np.diff(np.log(chain));n=min(21,len(a))
    worst21=float(np.expm1(pd.Series(lr).rolling(n).sum().min()))
    return dict(cagr=float(cagr),cumulative=float(a[-1]/initial-1),maxdd_close=maxdd,
                maxdd_sampled=sampled,calmar=float(cagr/abs(sampled)) if sampled<0 else np.nan,
                volatility=float(lr.std(ddof=1)*np.sqrt(252)) if len(lr)>1 else 0.,
                worst_21_sessions=worst21,end_equity=float(a[-1]),days=days)

def simulate(p,arm,ticket=1.,impact=.0015,lag=0,start="2020-03-02",end="2026-10-30",initial=10000.,f=None):
    if arm not in ARMS or lag<0:raise ValueError("CONFIG")
    dates=pd.DatetimeIndex(p["dates"]);names=np.array(p["names"])
    O=np.asarray(p["O"],float);C=np.asarray(p["C"],float);obs=np.asarray(p["observed"],bool)
    f=features(p) if f is None else f
    begin=int(dates.searchsorted(start));finish=int(dates.searchsorted(end,side="right"))
    if begin<253 or finish-begin<2:raise ValueError("WARMUP_OR_WINDOW")
    N=len(names);u=np.zeros(N);cash=float(initial)
    logs=[];orders=[];alerts=[];daily=[];deferred=0;maxerr=0.
    peak=float(initial);phase="NORMAL";cash_since=-10000;reentry_at=-10000
    active=np.zeros(N);pending=None
    def issue(k,w,reason,force=False):
        nonlocal pending
        due=k+1+lag
        # A queued instruction is superseded only by a newer eligible decision.
        pending=dict(due=due,weights=w.copy(),reason=reason,force=force,signal=k)
        alerts.append(dict(signal_date=str(dates[k].date()),execution_not_before=str(dates[min(due,len(dates)-1)].date()),
                           reason=reason,gross_target=float(w.sum()),positions=int((w>0).sum())))
    w,_=chosen_weights(p,f,begin-1,arm);issue(begin-1,w,"INITIAL",True)
    for k in range(begin,finish):
        prev=f["C"][k-1]
        op=O[k].copy();op[~obs[k]|(op<=0)]=np.nan
        mark=np.where(np.isfinite(op),op,prev)
        if np.any((u>1e-12)&(~np.isfinite(mark))):raise AssertionError("NO_MARK_FOR_HOLDING")
        nav_open=float(cash+np.nansum(u*mark))
        if pending is not None and k>=pending["due"]:
            target=pending["weights"]
            need=(u>1e-10)|(target>0)
            missing=need&(~np.isfinite(op))
            before=float(cash+np.nansum(u*mark))
            u,cash,trades=rebalance(u,cash,op,target,ticket,impact,.03,pending["force"],mark=mark)
            fees=sum(t["cost"] for t in trades)
            maxerr=max(maxerr,abs(cash+np.nansum(u*mark)+fees-before))
            for t in trades:
                t.update(date=str(dates[k].date()),signal_date=str(dates[pending["signal"]].date()),
                         ticker=str(names[t["j"]]),reason=pending["reason"])
                orders.append(t)
            active=target.copy()
            if missing.any():
                deferred+=1
            else:
                pending=None
        close=f["C"][k]
        nav=float(cash+np.nansum(u*close))
        exposure=float(np.nansum(u*close)/nav)
        peak=max(peak,nav);dd=nav/peak-1
        daily.append(dict(date=str(dates[k].date()),nav_open=nav_open,nav_close=nav,cash=cash,gross=exposure,
                          positions=int((u>1e-10).sum()),controller_dd=dd,phase=phase))
        if k+1>=finish:continue
        monthly=dates[k].month!=dates[k+1].month
        if arm=="PASSIVE":continue
        reason=None;target=None;force=False
        if arm=="DIVERSE_GUARD":
            if phase=="CASH":
                if monthly and k-cash_since>=20:
                    base,count=chosen_weights(p,f,k,arm);b=int(p["benchmark"])
                    if count>=4 and f["above200"][k,b] and f["m21"][k,b]>0:
                        target=.5*base;reason="REENTRY";phase="RECOVERY";reentry_at=k;peak=nav
                if target is None:continue
            elif dd<=-.18:
                target=np.zeros(N);reason="DD_EXIT";force=True;phase="CASH";cash_since=k
            elif dd<=-.12 and exposure>.50+.005:
                # Reduce proportional existing economic exposures; do not buy alternatives.
                holdings=np.where(np.isfinite(close),u*close,0.)/nav
                target=holdings*(.5/max(exposure,1e-12));reason="DD_REDUCE";force=True
        if target is None and monthly:
            target,count=chosen_weights(p,f,k,arm);reason="MONTHLY"
            if arm=="DIVERSE_GUARD":
                if phase=="RECOVERY" and k-reentry_at<20:target*=.5
                else:phase="NORMAL"
                if dd<=-.12:target*=min(1.,.5/max(target.sum(),1e-12))
        if target is None and arm in ("DIVERSE_RISK15","DIVERSE_GUARD") and exposure>0:
            ids=np.flatnonzero(u>1e-10);holdings=np.where(np.isfinite(close),u*close,0.)/nav
            sig=np.sqrt(max(0.,holdings[ids]@covariance_at(f,k,ids)@holdings[ids]))
            if sig>.1875 and (pending is None or pending["reason"] not in ("DD_EXIT","DD_REDUCE")):
                target=holdings*(.15/sig);reason="VOL_REDUCE";force=True
        if target is not None:
            # Do not postpone an unfilled risk exit because of another signal.
            if pending is not None and pending["reason"]=="DD_EXIT" and reason!="REENTRY":continue
            # A daily repeated reduction must not continuously postpone delayed execution.
            if pending is not None and force and pending["force"]:
                pending["weights"]=np.minimum(pending["weights"],target)
            else:
                issue(k,target,reason,force)
        if monthly:
            logs.append(dict(signal_date=str(dates[k].date()),phase=phase,controller_dd=float(dd)))
    return dict(daily=pd.DataFrame(daily),orders=pd.DataFrame(orders),alerts=pd.DataFrame(alerts),
                review=pd.DataFrame(logs),deferred_sessions=deferred,max_self_financing_error=maxerr)
