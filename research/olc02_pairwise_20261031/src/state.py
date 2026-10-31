"""As-of actual holdings and features. Outcomes are computed by labels.py only."""
import numpy as np
from assets import FEATURES
DIFF=[f for f in FEATURES if f not in ['market_mom63','breadth','price_age_days']]
LEVEL=['r_pct','h_pct','mom21','mom63','ma200_gap','vol63']
PAIR_FEATURES=['d_'+f for f in DIFF]+['old_'+f for f in LEVEL]+['market_mom63','breadth','old_age_mean','old_age_max','overlap','old_vol','new_vol','difference_vol','correlation','same_risk_fraction','old_max_weight','signal_gap']

class StateTracker:
    def __init__(self,a):
        self.a=a;self.ages={};self.want=None;self.records=[];self.force_rebalance=False
    def observe(self,k,t1,t2,u1,u2):
        actual={}
        for j,u in [(t1,u1),(t2,u2)]:
            if 0<=j<self.a.N and u>1e-14:actual[int(j)]=actual.get(int(j),0.)+float(u)
        self.ages={j:self.ages.get(j,max(0,k-1)) for j in actual}
        if k not in self.a.event:return None
        i=self.a.event[k];sd=self.a.cal.iloc[i].signal_date
        sp=int(self.a.ds.searchsorted(sd,side='right')-1)
        if sp<0 or sp>=k:return None
        q=np.zeros(self.a.N)
        for j,u in actual.items():q[j]=u
        pv=q*self.a.q['C'][sp,:self.a.N]; total=pv.sum()
        if not np.isfinite(total) or total<=0:return None
        weights=pv/total;shares=q/total
        ages=np.zeros(self.a.N)
        for j in actual:ages[j]=max(0,sp-self.ages[j]+1)
        return dict(i=i,k=k,signal_date=sd,entry_date=self.a.cal.iloc[i].entry_date,ids=list(actual),weights=weights,shares=shares,ages=ages)
    def base(self,k):
        return (*self.a.cl01(k),float(self.a.q['weights'][0,k]),1.)

def action_features(a,s,pair):
    i=s['i'];ow=s['weights'];nw=np.zeros(a.N);nw[list(pair)]=.5
    active=(ow>1e-14)|(nw>0)
    z=a.X[i]
    # Current expert scores are mandatory, additional technical NaNs are imputed in training only.
    if not np.isfinite(z[active,:2]).all():return None
    def weighted(w):
        ids=w>1e-14;return np.sum(z[ids]*w[ids,None],axis=0)
    old=weighted(ow);new=weighted(nw);idx={f:j for j,f in enumerate(FEATURES)}
    co=a.covs[i];vo=float(ow@co@ow);vn=float(nw@co@nw);cross=float(ow@co@nw)
    dv=max(0.,float((nw-ow)@co@(nw-ow)))
    age=s['ages'];maxage=float(age[ow>0].max());meanage=float(age@ow)
    sc=a.score.iloc[i].to_numpy()
    v=[new[idx[f]]-old[idx[f]] for f in DIFF]+[old[idx[f]] for f in LEVEL]
    v += [float(np.nanmedian(z[:,idx['market_mom63']])),float(np.nanmedian(z[:,idx['breadth']])),np.log1p(meanage),np.log1p(maxage),float(np.minimum(ow,nw).sum()),np.sqrt(max(vo,0)*252),np.sqrt(max(vn,0)*252),np.sqrt(dv*252),cross/np.sqrt(max(vo*vn,1e-20)),1.-dv/max(vo+vn,1e-20),float(ow.max()),float(sc[nw>0]@nw[nw>0]-sc[ow>0]@ow[ow>0])]
    out=np.asarray(v,float);out[~np.isfinite(out)]=np.nan
    assert len(out)==len(PAIR_FEATURES)
    return out

class TraceController(StateTracker):
    def __init__(self,a,rule='BASE'):
        super().__init__(a);self.rule=rule;self.states=[]
    def step(self,k,t1,t2,at,u1,u2,au,bu,su,free,pw,pf):
        self.force_rebalance=False
        s=self.observe(k,t1,t2,u1,u2)
        if self.want is None:self.want=self.base(k)
        if k not in self.a.event:return self.base(k) if self.rule=='BASE' else self.want
        i=self.a.event[k]
        if s is not None and len(s['ids'])==2:self.states.append(s)
        if self.rule=='BASE':self.want=self.base(k)
        elif self.rule=='BUFFER4':
            ranks=self.a.ranked(i);old=s['ids'] if s is not None else []
            keep=[j for j in old if j in ranks[:4]]
            pair=(keep+[j for j in ranks if j not in keep])[:2]
            if len(pair)==2:self.want=(*pair,.5,1.)
        elif self.rule.startswith('FIXED2'):
            phase=int(self.rule[-1])
            if i%2==phase or s is None or len(s['ids'])<2:self.want=self.base(k)
        else:raise ValueError(self.rule)
        return self.want
