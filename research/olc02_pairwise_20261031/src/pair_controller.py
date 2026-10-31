"""Narrow direct-action controller. CL01 proposals and legacy protection are fixed."""
from assets import ROOT,PARENT
from state import StateTracker,action_features,PAIR_FEATURES
from pairmath import candidate_pairs,cost_log,best_action
from train_pairs import predict
from lifecycle_math import expected_growth
import numpy as np,pandas as pd,joblib

class ForecastBank:
    def __init__(self,a):
        self.a=a;self.saved={}
        self.audit=pd.read_csv(ROOT/f'results/{a.market}_FIT_AUDIT.csv')
        p=pd.read_csv(PARENT/f'results/{a.market}_PREDICTIONS.csv.gz',parse_dates=['signal_date'],float_precision='round_trip')
        self.absolute={}
        for model in ['RIDGE','HGB']:
            f=p[p.model==model]
            self.absolute[model]=np.stack([f.pivot(index='signal_date',columns='ticker',values='mu'+str(h)).reindex(index=a.score.index,columns=a.score.columns).to_numpy(float) for h in [1,2,3]],axis=1)
    def model(self,family,year,h):
        key=(family,year,h)
        if key not in self.saved:self.saved[key]=joblib.load(ROOT/f'models/{self.a.market}_{family}_{year}_H{h}.joblib')
        return self.saved[key]
    def values(self,family,s,actions,profile):
        xx=np.array([action_features(self.a,s,pair) for pair in actions],dtype=float)
        year=int(s['signal_date'].year);heads=[21,42,63] if profile else [21]
        v=[]
        for h in heads:
            if family=='MEAN':
                row=self.audit[(self.audit.model=='RIDGE')&(self.audit.year==year)&(self.audit.h==h)]
                v.append(np.full(len(actions),row['mean'].iloc[0]))
            else:v.append(predict(self.model(family,year,h),xx))
        return np.mean(v,axis=0),np.stack(v,axis=1)
    def absolute_values(self,family,s,actions,profile):
        m=self.absolute[family][s['i']];cov=self.a.covs[s['i']]
        old=expected_growth(s['weights'],m,cov,profile)
        result=[]
        for pair in actions:
            nw=np.zeros(self.a.N);nw[list(pair)]=.5
            result.append(expected_growth(nw,m,cov,profile)-old)
        return np.asarray(result),None

class PairController(StateTracker):
    def __init__(self,a,bank,policy,fee):
        super().__init__(a);self.bank=bank;self.policy=policy;self.fee=fee;self.action_records=[]
    def step(self,k,t1,t2,at,u1,u2,au,bu,su,free,pw,pf):
        self.force_rebalance=False
        s=self.observe(k,t1,t2,u1,u2)
        if self.want is None or self.a.ds[k].year<2021:self.want=self.base(k)
        if k not in self.a.event:return self.want
        i=self.a.event[k];sd=self.a.cal.iloc[i].signal_date;before=self.want;action='HOLD';accepted=False
        if sd.year<2021:
            self.want=self.base(k);return self.want
        clpair=self.a.cl01(k);oldids=s['ids'] if s is not None else []
        options=[];vals=np.empty(0);costs=np.empty(0);best=-1;age_ood=False
        if s is None or len(oldids)!=2:
            self.want=self.base(k);action='BASE_REENTRY'
        elif self.policy=='BUFFER4':
            ranked=self.a.ranked(i);keep=[j for j in oldids if j in ranked[:4]]
            new=(keep+[j for j in ranked if j not in keep])[:2]
            self.want=(*new,.5,1.);action='BUFFER4'
        elif self.policy=='FOLLOW_CL01':
            if set(oldids)!=set(clpair):self.want=self.base(k);action='ACCEPT_FULL';accepted=True
            else:action='SAME_NAMES'
        elif self.policy=='HOLD_NAMES':
            if set(oldids)!=set(self.want[:2]):self.want=(*oldids,float(s['weights'][oldids[0]]),1.)
        else:
            pieces=self.policy.split('_');absolute=pieces[0]=='ABS'
            family=pieces[1] if absolute else pieces[0]
            profile='PROFILE' in pieces;single='SLOT' in pieces
            options=candidate_pairs(oldids,clpair,self.a.ranked(i),single=single)
            guard='AGE' in pieces and not absolute and family!='MEAN'
            if guard:
                aa=self.bank.audit;hh=[21,42,63] if profile else [21]
                support=aa[(aa.model==family)&(aa.year==sd.year)&aa.h.isin(hh)].age_feature_max.min()
                age_ood=bool(np.log1p(s['ages'][s['weights']>0].max())>support+1e-12)
            if guard and age_ood and len(options):
                self.want=self.base(k);action='AGE_SUPPORT_BASE';accepted=True
                self.action_records.append(dict(signal_date=sd,entry_date=self.a.cal.iloc[i].entry_date,old_ids='|'.join(map(str,oldids)),old_shares='|'.join(str(s['shares'][ii]) for ii in oldids),old_weights='|'.join(str(s['weights'][ii]) for ii in oldids),new_ids='|'.join(map(str,clpair)),old_tickers='|'.join(self.a.names[ii] for ii in oldids),new_tickers='|'.join(self.a.names[ii] for ii in clpair),is_full_proposal=True,predicted_gross=np.nan,expected_cost=np.nan,predicted_net=np.nan,selected=True,age_ood=True))
            elif len(options):
                features=[action_features(self.a,s,pair) for pair in options]
                if any(x is None for x in features):
                    self.want=self.base(k);action='MISSING_CURRENT_BASE'
                else:
                    vals,heads=(self.bank.absolute_values(family,s,options,profile) if absolute else self.bank.values(family,s,options,profile))
                    costs=[]
                    for pair in options:
                        nw=np.zeros(self.a.N);nw[list(pair)]=.5;costs.append(cost_log(s['weights'],nw,self.fee))
                    costs=np.array(costs);best=best_action(vals,costs)
                    audit=self.bank.audit;year=sd.year
                    if family!='MEAN':
                        limit=audit[(audit.model==family)&(audit.year==year)].age_feature_max.min()
                        age_ood=np.log1p(s['ages'][s['weights']>0].max())>limit+1e-12
                    if best>=0:
                        pair=options[best];self.want=(*pair,.5,1.);self.force_rebalance=True
                        action='ACCEPT_FULL' if set(pair)==set(clpair) else 'ACCEPT_ONE';accepted=True
                    elif set(oldids)!=set(self.want[:2]):
                        self.want=(*oldids,float(s['weights'][oldids[0]]),1.)
                    for j,pair in enumerate(options):
                        self.action_records.append(dict(signal_date=sd,entry_date=self.a.cal.iloc[i].entry_date,old_ids='|'.join(map(str,oldids)),old_shares='|'.join(str(s['shares'][ii]) for ii in oldids),old_weights='|'.join(str(s['weights'][ii]) for ii in oldids),new_ids='|'.join(map(str,pair)),old_tickers='|'.join(self.a.names[ii] for ii in oldids),new_tickers='|'.join(self.a.names[ii] for ii in pair),is_full_proposal=set(pair)==set(clpair),predicted_gross=float(vals[j]),expected_cost=float(costs[j]),predicted_net=float(vals[j]-costs[j]),selected=j==best,age_ood=age_ood))
            else:action='SAME_NAMES'
        self.records.append(dict(signal_date=sd,entry_date=self.a.cal.iloc[i].entry_date,policy=self.policy,action=action,old_ids='|'.join(map(str,oldids)),old_tickers='|'.join(self.a.names[j] for j in oldids),proposed_tickers='|'.join(self.a.names[j] for j in clpair),target_tickers='|'.join(self.a.names[j] for j in self.want[:2]),accepted=accepted,option_count=len(options),best_net_advantage=float(np.max(vals-costs)) if len(vals) else np.nan,old_age_max=float(s['ages'].max()) if s else 0.,age_ood=age_ood,target_weight=self.want[2]))
        assert self.want[3]==1.,'No discretionary cash or exposure cut allowed'
        return self.want
