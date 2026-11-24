from pathlib import Path
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import json,sys,hashlib
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'inputs';OUT=ROOT/'results'
INPUT.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
MARKETS=['EU','USA','TR'];HORIZONS=[5,21,63]
RULES=['BASE','NET21','LCB21','LCB_MULTI']
XNAMES=['delta_log5','delta_log21','delta_log63','delta_vol21','delta_drawdown63','replaced_weight']

def load(path):
    with np.load(path) as z:return {k:z[k].copy() for k in z.files}

def state(m):return load(INPUT/f'{m}_STATE.npz')

def target(q,k):
    p=np.zeros(len(q['tickers']))
    i,j=int(q['d1'][0,k]),int(q['d2'][0,k]);w=float(q['weights'][0,k])
    if i==j:w=1.
    if i>=0:p[i]+=w
    if j>=0:p[j]+=1-w
    return p

def features(q):
    obs=q.get('low_observed',np.ones_like(q['C'],bool))
    c=pd.DataFrame(q['C']).where(obs)
    log=np.log(c)
    cols=[(log-log.shift(h)).shift(1).to_numpy() for h in [5,21,63]]
    cols.append(log.diff().rolling(21,min_periods=18).std().shift(1).to_numpy())
    cols.append((c/c.rolling(63,min_periods=55).max()-1).shift(1).to_numpy())
    return np.stack(cols,axis=2)

def pair_x(f,k,p,h):
    ids=np.flatnonzero((p>1e-10)|(h>1e-10))
    if not len(ids) or not np.isfinite(f[k,ids]).all():return None
    return np.r_[(p[ids]-h[ids])@f[k,ids],1-np.minimum(p,h).sum()]

def forward(q,k,p,h,hor):
    end=k+hor
    if end>=len(q['dates']):return None
    ids=np.flatnonzero((p>1e-10)|(h>1e-10))
    obs=q.get('observed',np.ones_like(q['O'],bool))
    if not obs[k,ids].all() or not obs[end,ids].all():return None
    y=float((p[ids]-h[ids])@(q['O'][end,ids]/q['O'][k,ids]-1))
    return y,str(pd.Timestamp(q['dates'][end]).date())

def metrics(ds,nav):
    years=(pd.Timestamp(ds[-1])-pd.Timestamp(ds[0])).days/365.2425
    return dict(cagr=float((nav[-1]/nav[0])**(1/years)-1),maxdd=float(min(nav/np.maximum.accumulate(nav)-1)),final_capital=float(10000*nav[-1]/nav[0]))

def month_returns(ds,nav):
    s=pd.Series(nav[1:]/nav[:-1]-1,index=pd.DatetimeIndex(ds[:-1]))
    return (1+s).groupby(s.index.to_period('M')).prod()-1

def ridge(X,y,w):
    design=np.column_stack([np.ones(len(X)),X])
    penalty=np.diag([0.]+[10.]*X.shape[1])
    return np.linalg.solve(design.T@(w[:,None]*design)+penalty,design.T@(w*y))

def fit_models(rows,save=True):
    models={};audit=[]
    for year in range(2020,2027):
        models[str(year)]={}
        for hor in HORIZONS:
            a=rows[(rows.horizon==hor)&(rows.exit_date<f'{year}-01-01')].copy()
            counts=a.groupby('market').month.nunique().to_dict()
            meta=dict(year=year,horizon=hor,rows=len(a),counts=counts,cutoff=f'{year}-01-01',last_exit=a.exit_date.max() if len(a) else None)
            if min([counts.get(m,0) for m in MARKETS])<18:
                models[str(year)][str(hor)]=None;audit.append(dict(**meta,available=False));continue
            assert (a.signal_date<a.exit_date).all() and a.exit_date.max()<f'{year}-01-01'
            months=sorted(a.month.unique());n=len(months)
            # Equal total mass per universe, then month, then counterfactual.
            nq=a.groupby('market').month.transform('nunique').to_numpy()
            ng=a.groupby(['market','month']).month.transform('size').to_numpy()
            w=n/(3*nq*ng)
            X=a[XNAMES].to_numpy();y=a.y.to_numpy()
            mean=np.average(X,axis=0,weights=w);sd=np.sqrt(np.average((X-mean)**2,axis=0,weights=w));sd=np.maximum(sd,1e-6)
            X=np.clip((X-mean)/sd,-3,3);y=np.clip(y,-.5,.5)
            beta=ridge(X,y,w)
            mi=np.array([months.index(m) for m in a.month]);rng=np.random.default_rng(2200+year*100+hor)
            boots=[]
            for b in range(200):
                picks=((rng.integers(0,n,size=(int(np.ceil(n/3)),1))+np.arange(3))%n).ravel()[:n]
                multiplicity=np.bincount(picks,minlength=n)
                ww=w*multiplicity[mi]
                ww*=n/ww.sum()
                boots.append(ridge(X,y,ww))
            models[str(year)][str(hor)]=dict(**meta,mean=mean.tolist(),sd=sd.tolist(),beta=beta.tolist(),bootstrap=np.array(boots).tolist())
            audit.append(dict(**meta,available=True))
    if save:
        (OUT/'MODELS.json').write_text(json.dumps(models,indent=2))
        pd.DataFrame(audit).to_csv(OUT/'FIT_AUDIT.csv',index=False)
    return models

class Gate:
    def __init__(self,q,f,models,rule,bps):
        self.q=q;self.f=f;self.models=models;self.rule=rule;self.impact=bps/10000
        self.accepted=None;self.previous_proposal=None;self.next_review=0;self.log=[]

    def __call__(self,k,p,units,pc,lock_until,cooldown,forced):
        changed=self.previous_proposal is None or np.max(abs(p-self.previous_proposal))>1e-12
        self.previous_proposal=p.copy()
        value=units*pc;capital=float(value.sum())
        cash=np.array(['CASH_' in s for s in self.q['tickers']])
        # Admission affects discretionary composition only. Risk and cash reentry keep priority.
        bypass=self.accepted is None or capital<1e-12 or forced or cooldown>0 or np.any(lock_until>=k) or p[cash].sum()>0 or p.sum()<1e-12
        if bypass:
            self.accepted=p.copy();self.next_review=k;return p
        if np.max(abs(p-self.accepted))<1e-12:return p
        if not changed and k<self.next_review:return self.accepted.copy()
        h=value/capital;x=pair_x(self.f,k,p,h)
        year=str(pd.Timestamp(self.q['dates'][k]).year)
        needed=HORIZONS if self.rule=='LCB_MULTI' else [21]
        available=x is not None and all(self.models[year][str(z)] is not None for z in needed)
        if not available:
            self.accepted=p.copy();return p
        diff=capital*p-value;mask=abs(diff)>max(1e-12,capital*1e-10)
        cost=(mask.sum()/10000+self.impact*abs(diff[mask]).sum())/capital
        preds=[]
        for hor in needed:
            model=self.models[year][str(hor)]
            xx=np.r_[1.,np.clip((x-np.array(model['mean']))/np.array(model['sd']),-3,3)]
            mean=float(xx@model['beta']);draws=np.array(model['bootstrap'])@xx
            lower=float(np.quantile(draws,.2/3 if self.rule=='LCB_MULTI' else .2))
            score=((mean if self.rule=='NET21' else lower)-cost)/hor
            preds.append(dict(horizon=hor,mean=mean,lower=lower,score=score,last_exit=model['last_exit']))
        best=max(preds,key=lambda z:z['score']);allow=best['score']>0
        row=dict(index=k,date=str(pd.Timestamp(self.q['dates'][k]).date()),last_input=str(pd.Timestamp(self.q['dates'][k-1]).date()),rule=self.rule,allow=bool(allow),estimated_cost=cost,primary_capital=10000*capital,**best)
        row.update({name:float(v) for name,v in zip(XNAMES,x)})
        row['proposal']=json.dumps({str(i):float(p[i]) for i in np.flatnonzero(p)})
        row['held']=json.dumps({str(i):float(h[i]) for i in np.flatnonzero(h)})
        self.log.append(row)
        retry=max(2,min(10,round(best['horizon']/4))) if self.rule=='LCB_MULTI' else 5
        self.next_review=k+retry
        if allow:self.accepted=p.copy()
        return self.accepted.copy()
