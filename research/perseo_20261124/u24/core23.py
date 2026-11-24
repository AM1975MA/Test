from pathlib import Path
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import sys,json,hashlib
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent;INPUT=ROOT/'inputs';OUT=ROOT/'results'
RULES=['BASE','CORE25','CORE_WEAK','LEG_BENCH','TREND_CASH','TRAIL_CASH','RECOVERY','RAMP','TREND_RECOVERY','LEG_RECOVERY']
MARKETS=['EU','USA','TR']
BM={'EU':'SXR8.DE','USA':'SPY','TR':'IE00B5BMR087'}

def load(path):
    with np.load(path) as z:return {k:z[k].copy() for k in z.files}

def state(m):return load(INPUT/f'{m}_STATE.npz')

def source_targets(q):
    D,N=q['O'].shape;p=np.zeros((D,N))
    for k in range(D):
        i,j=int(q['d1'][0,k]),int(q['d2'][0,k]);w=float(q['weights'][0,k]);w=1. if i==j else w
        if i>=0:p[k,i]+=w
        if j>=0:p[k,j]+=1-w
    return p

def signals(q,m):
    obs=q.get('low_observed',np.ones_like(q['C'],bool));c=pd.DataFrame(q['C']).where(obs)
    prev=c.shift(1).to_numpy();r={h:(c/c.shift(h)-1).shift(1).to_numpy() for h in [5,21,63]}
    ema21=c.ewm(span=21,min_periods=21,adjust=False).mean().shift(1).to_numpy()
    ema63=c.ewm(span=63,min_periods=63,adjust=False).mean().shift(1).to_numpy()
    vol=np.log(c).diff().rolling(21,min_periods=18).std().shift(1).to_numpy()
    high10=c.shift(2).rolling(10,min_periods=10).max().to_numpy()
    valid=np.isfinite(prev);weak=(prev<ema63)&(r[21]<0)&valid;good=(prev>ema21)&(r[5]>0)&valid
    weak3=pd.DataFrame(weak).rolling(3,min_periods=3).sum().eq(3).to_numpy()
    good2=pd.DataFrame(good).rolling(2,min_periods=2).sum().eq(2).to_numpy()
    b=list(q['tickers']).index(BM[m]);recovery=good2[:,b]
    D,N=prev.shape;raw=source_targets(q);cash=np.array(['CASH_' in t for t in q['tickers']]);cashid=np.flatnonzero(cash)[0]
    names=['CORE25','CORE_WEAK','LEG_BENCH','TREND_CASH','TRAIL_CASH']
    targets={name:np.zeros_like(raw) for name in names};targets['BASE']=raw
    trend=np.zeros(N,bool);trailing=np.zeros(N,bool);peak=np.zeros(N);old_present=np.zeros(N,bool)
    reviews=np.zeros(D,bool);guardlog=[];last={name:np.zeros(N) for name in names}
    for k in range(D):
        p=raw[k];present=(p>0)&~cash
        trend[weak3[k]]=True;trend[good2[k]]=False;trend[cash]=False
        fresh=present&~old_present;peak[~present]=0.;trailing[~present]=False
        peak[fresh]=np.where(valid[k,fresh],prev[k,fresh],0.);trailing[fresh]=False
        active=present&valid[k];peak[active]=np.maximum(peak[active],prev[k,active])
        band=np.clip(2*vol[k]*np.sqrt(5),.08,.18)
        stopped=trailing.copy();hit=active&~stopped&(prev[k]<peak*(1-band))
        rebound=active&stopped&(prev[k]>high10[k])&(r[5][k]>0)
        trailing[hit]=True;trailing[rebound]=False;peak[rebound]=prev[k,rebound]
        old_present=present.copy()
        review=k==0 or k%5==0 or np.max(abs(raw[k]-raw[k-1]))>1e-12
        reviews[k]=review
        if review:
            for name in names:last[name]=p.copy()
            if p.sum()>0:
                last['CORE25']=.75*p;last['CORE25'][b]+=.25
                ids=np.flatnonzero(p>0)
                weak_port=np.isfinite(r[21][k,ids]).all() and np.isfinite(r[63][k,ids]).all() and p[ids]@r[21][k,ids]<0 and p[ids]@r[63][k,ids]<0
                refuge=b if np.isfinite(r[63][k,b]) and r[63][k,b]>0 else cashid
                if weak_port:last['CORE_WEAK']=.75*p;last['CORE_WEAK'][refuge]+=.25
                bad=(r[21][k]<0)&(r[63][k]<0)&present
                moved=.5*p*bad;last['LEG_BENCH']-=moved;last['LEG_BENCH'][refuge]+=moved.sum()
                for name,blocked in [('TREND_CASH',trend),('TRAIL_CASH',trailing)]:
                    moved=p*blocked;last[name]-=moved;last[name][cashid]+=moved.sum()
            guardlog.append(dict(index=k,date=str(pd.Timestamp(q['dates'][k]).date()),signal_date=str(pd.Timestamp(q['dates'][k-1]).date()) if k else '',trend_cash=float(last['TREND_CASH'][cash].sum()),trail_cash=float(last['TRAIL_CASH'][cash].sum()),leg_benchmark=float(last['LEG_BENCH'][b]),core_weak_benchmark=float(last['CORE_WEAK'][b])))
        for name in names:targets[name][k]=last[name]
    targets['RECOVERY']=raw;targets['RAMP']=raw;targets['TREND_RECOVERY']=targets['TREND_CASH'];targets['LEG_RECOVERY']=targets['LEG_BENCH']
    for name,t in targets.items():
        assert (t>=-1e-12).all() and np.allclose(t.sum(1),raw.sum(1),atol=1e-12)
    return targets,recovery,np.array(reviews),pd.DataFrame(guardlog)

def metrics(ds,nav):
    years=(pd.Timestamp(ds[-1])-pd.Timestamp(ds[0])).days/365.2425
    return dict(cagr=float((nav[-1]/nav[0])**(1/years)-1),maxdd=float(min(nav/np.maximum.accumulate(nav)-1)),final_capital=float(10000*nav[-1]/nav[0]))

def months(ds,nav):
    r=pd.Series(nav[1:]/nav[:-1]-1,index=pd.DatetimeIndex(ds[:-1]));return (1+r).groupby(r.index.to_period('M')).prod()-1

def tag(m,rule,bps,lag=0):return f'{m}_{rule}_{bps}_L{lag}'
