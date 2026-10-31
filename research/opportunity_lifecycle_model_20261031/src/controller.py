"""Monthly receding-horizon decisions from actual prior-close holdings.
No Open, gap, Low, or future label is read when choosing a discretionary action.
"""
import itertools
import numpy as np
import pandas as pd
from lifecycle_math import expected_growth,trade_cost,choose_best

def top2(x):
    ids=np.flatnonzero(np.isfinite(x))
    return ids[np.argsort(-x[ids],kind='stable')[:2]].tolist()

class Controller:
    def __init__(self,q,cal,score,mu,covs,fee,policy,profile=True):
        self.q=q;self.cal=cal;self.score=score;self.mu=mu;self.covs=covs;self.fee=fee;self.policy=policy;self.profile=profile
        self.ds=pd.DatetimeIndex(q['dates']);self.N=score.shape[1];self.names=q['tickers'].tolist()
        self.events={int(self.ds.get_indexer([r.entry_date])[0]):i for i,r in enumerate(cal.itertuples(index=False)) if r.entry_date in self.ds}
        self.want=None;self.records=[];self.active_month=0;self.ages={}
    def step(self,k,t1,t2,at,u1,u2,au,bu,su,free,pw,pf):
        self.force_rebalance=False
        i=self.events.get(k)
        # Frozen baseline prior to first fitted forecast year.
        if self.ds[k].year<2021 or self.want is None:
            self.want=(int(self.q['d1'][0,k]),int(self.q['d2'][0,k]),float(self.q['weights'][0,k]),1.)
        if i is None:return self.want
        sd=self.cal.iloc[i].signal_date
        if sd.year<2021:
            self.want=(int(self.q['d1'][0,k]),int(self.q['d2'][0,k]),float(self.q['weights'][0,k]),1.)
            return self.want
        sigpos=int(self.ds.searchsorted(sd,side='right')-1)
        assert sigpos<k
        prices=self.q['C'][max(sigpos,0)]
        bil=self.names.index('BIL' if 'EUR_CASH_A' not in self.names else 'EUR_CASH_A')
        shv=self.names.index('SHV' if 'EUR_CASH_B' not in self.names else 'EUR_CASH_B')
        values=np.zeros(self.N)
        oldids=[]
        for j,u in [(t1,u1),(t2,u2)]:
            if j>=0 and u>1e-14 and j<self.N:values[j]+=u*prices[j];oldids.append(int(j))
        av=au*prices[at] if at>=0 else 0.
        total=values.sum()+av+bu*prices[bil]+su*prices[shv]+free
        if total<=0:total=1.
        current=values/total
        altctx=np.zeros(self.N)
        if at>=0 and at<self.N:altctx[at]+=av/total
        old=current+altctx
        sc=self.score[i];mu=self.mu[i];cov=self.covs[i];g=float(self.q['g'][k])
        prev=self.want;policy=self.policy;action='HOLD';delta=0.;options=0
        proposal=top2(sc);ranking=np.mean(np.cumsum(mu,axis=0),axis=0) if self.profile else mu[0]
        if not np.isfinite(mu).any():ranking=np.full(self.N,np.nan)
        predpair=top2(ranking)
        selected=None
        if policy=='BUFFER4':
            order=np.flatnonzero(np.isfinite(sc));order=order[np.argsort(-sc[order],kind='stable')]
            keep=[j for j in oldids if j in order[:4]]
            selected=(keep+[int(j) for j in order if j not in keep])[:2]
        elif policy.startswith('FIXED'):
            _,every,phase=policy.split('_');every=int(every);phase=int(phase)
            if self.active_month%every==phase or not oldids:selected=proposal
        elif policy=='RANK':selected=predpair
        if selected is not None and len(selected)==2:
            self.want=(int(selected[0]),int(selected[1]),.5,1.);action='RESELECT'
        elif policy in ['GATE','PARTIAL','BASE_GATE']:
            if len(predpair)==2 and np.isfinite(mu[:,old>1e-12]).all():
                specs=[];vectors=[]
                def add(pair,w=.5,rho=1.):
                    vec=altctx*min(rho,rho*max(0.,1-g)/(altctx.sum()+1e-30))
                    for j,share in zip(pair,[w,1-w]):vec[j]+=rho*g*share
                    specs.append((int(pair[0]),int(pair[1]),float(w),float(rho)))
                    vectors.append(vec)
                if policy in ['GATE','BASE_GATE']:
                    add(proposal if policy=='BASE_GATE' else predpair)
                else:
                    pool=sorted(set(proposal+predpair+top2(mu[0])+oldids))
                    pool=[j for j in pool if np.isfinite(mu[:,j]).all()]
                    for pair in itertools.combinations(pool,2):
                        # Slot order stable for actual incumbent when possible.
                        if t1 in pair:pair=(t1,pair[0] if pair[1]==t1 else pair[1])
                        for w in [.25,.5,.75]:
                            for rho in [.5,1.]:add(pair,w,rho)
                specs.append((-1,-1,1.,0.));vectors.append(np.zeros(self.N))
                options=len(specs)
                pick,delta=choose_best(old,vectors,mu,cov,self.fee,self.profile)
                if pick>=0:
                    self.force_rebalance=True
                    self.want=specs[pick]
                    names=set(self.want[:2])-{ -1 }
                    if not names:action='CASH'
                    elif names==set(oldids):action='RESIZE'
                    elif names.intersection(oldids):action='REPLACE_ONE'
                    else:action='REPLACE_PAIR'
                else:
                    # Preserve current desired plan when actual two primary positions remain intact.
                    # For stopped/missing positions HOLD must not resurrect an empty slot.
                    if set(oldids)!=set(j for j in self.want[:2] if j>=0):
                        if len(oldids)==0:self.want=(-1,-1,1.,0.)
                        elif len(oldids)==1:
                            j=oldids[0];rho=min(1.,current.sum()/max(g,1e-12));self.want=(j,j,1.,rho)
                        else:
                            a,b=oldids[:2];rho=min(1.,current.sum()/max(g,1e-12));w=current[a]/max(current.sum(),1e-12);self.want=(a,b,float(w),float(rho))
            else:action='MISSING_FORECAST_HOLD'
        self.active_month+=1
        rec=dict(old_weights='|'.join(f'{j}:{old[j]:.17g}' for j in np.flatnonzero(old>1e-12)),signal_date=str(sd.date()),execution_date=str(self.ds[k].date()),policy=policy,action=action,old_tickers='|'.join(self.names[j] for j in oldids),target_tickers='|'.join(self.names[j] for j in self.want[:2] if j>=0),target_weight1=self.want[2],target_primary_fraction=self.want[3],current_primary_fraction=float(current.sum()),candidate_count=options,expected_log_advantage=float(delta),hold_surrogate=float(expected_growth(old,mu,cov,self.profile)) if np.isfinite(mu[:,old>0]).all() else None,signal_index=sigpos,execution_index=k)
        for pos,j in enumerate(oldids[:2],1):
            for h in range(3):rec[f'old{pos}_remaining_segment{h+1}']=float(mu[h,j]) if np.isfinite(mu[h,j]) else None
        self.records.append(rec)
        return self.want
