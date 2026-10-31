"""Baseline-anchored controller: a refusal must earn its economic justification."""
from __future__ import annotations
import bootstrap
from bootstrap import ROOT,PARENT
from assets import Assets
from state import StateTracker,action_features
from pairmath import cost_log
from calibration import fit_posterior,forecast
import numpy as np
import pandas as pd


class CalibrationBank:
    """Immutable historical OOS forecasts; only matured rows enter each estimate."""
    def __init__(self,market):
        p=pd.read_csv(PARENT/f'results/{market}_DIRECT_PREDICTIONS.csv.gz',parse_dates=['signal_date','exit21','exit42','exit63'],float_precision='round_trip')
        self.tables={f:p[(p.model==f)&p.is_full_proposal].copy() for f in ['RIDGE','HGB']}
        self.cache={};self.audit=[]
    def get(self,family,asof,horizon,scale):
        key=(family,str(asof),horizon,scale)
        if key not in self.cache:
            p=fit_posterior(self.tables[family],asof,horizon,scale)
            self.cache[key]=p
            if p:
                assert pd.Timestamp(p['last_exit'])<pd.Timestamp(asof)
                self.audit.append(dict(family=family,horizon=horizon,scale=scale,asof=str(asof),months=p['months'],rows=p['rows'],last_exit=p['last_exit'],intercept=p['mean_beta'][0]*scale,slope=p['mean_beta'][1],a=p['a'],b=p['b'],min_raw=p['min_raw'],max_raw=p['max_raw']))
        return self.cache[key]


class SelectiveController(StateTracker):
    def __init__(self,a,bank,calibration_bank,family,horizon,kind,fee,scale=.05):
        super().__init__(a)
        if kind not in ['SUPPORT','MEAN','UTILITY','NEUTRAL']:raise ValueError(kind)
        self.bank=bank;self.calibration_bank=calibration_bank;self.family=family
        self.horizon=horizon;self.kind=kind;self.fee=fee;self.scale=scale;self.action_records=[]
    def step(self,k,t1,t2,at,u1,u2,au,bu,su,free,pw,pf):
        self.force_rebalance=False
        s=self.observe(k,t1,t2,u1,u2)
        if self.want is None or self.a.ds[k].year<2021:self.want=self.base(k)
        if self.kind=='NEUTRAL':
            self.want=self.base(k)
            return self.want
        if k not in self.a.event:return self.want
        i=self.a.event[k];sd=pd.Timestamp(self.a.cal.iloc[i].signal_date)
        if sd.year<2021:
            self.want=self.base(k);return self.want
        proposed=self.a.cl01(k);oldids=s['ids'] if s is not None else []
        action='BASE_REENTRY';veto=False;info={};raw=np.nan;charge=np.nan;age_ood=False;months=0
        if s is not None and len(oldids)==2:
            if set(oldids)==set(proposed):
                action='SAME_NAMES'
            else:
                x=action_features(self.a,s,proposed)
                if x is None:action='MISSING_BASE'
                else:
                    heads=[21] if self.horizon=='21' else [21,42,63]
                    au=self.bank.audit
                    limits=au[(au.model==self.family)&(au.year==sd.year)&au.h.isin(heads)]
                    if len(limits)!=len(heads):raise ValueError('Missing annual model-support record')
                    age_ood=bool(np.log1p(s['ages'][s['weights']>0].max())>limits.age_feature_max.min()+1e-12)
                    vals,_=self.bank.values(self.family,s,[proposed],self.horizon=='PROFILE')
                    raw=float(vals[0]);w=np.zeros(self.a.N);w[list(proposed)]=.5
                    charge=cost_log(s['weights'],w,self.fee)
                    p=None
                    if self.kind in ['MEAN','UTILITY']:
                        p=self.calibration_bank.get(self.family,sd,self.horizon,self.scale)
                        if p:
                            months=p['months'];info=forecast(p,raw,charge)
                            info['calibration_last_exit']=p['last_exit']
                    if age_ood:action='AGE_BASE'
                    elif not np.isfinite(raw):action='INVALID_BASE'
                    elif raw-charge>0:action='MODEL_AGREES_BASE'
                    elif self.kind=='SUPPORT':veto=True
                    elif p is None:action='COLDSTART_BASE'
                    elif not info['inside_support']:action='FORECAST_SUPPORT_BASE'
                    else:
                        weight=1. if self.kind=='MEAN' else 2.
                        veto=bool(info['avoided_loss']>weight*info['missed_opportunity'])
                        if not veto:action='CALIBRATION_BASE'
                    if veto:
                        action='VETO_HOLD'
                        if set(oldids)!=set(self.want[:2]):
                            self.want=(*oldids,float(s['weights'][oldids[0]]),1.)
                    self.action_records.append(dict(signal_date=sd,entry_date=s['entry_date'],kind=self.kind,family=self.family,horizon=self.horizon,old_ids='|'.join(map(str,oldids)),new_ids='|'.join(map(str,proposed)),old_shares='|'.join(str(s['shares'][ii]) for ii in oldids),old_weights='|'.join(str(s['weights'][ii]) for ii in oldids),old_tickers='|'.join(self.a.names[ii] for ii in oldids),new_tickers='|'.join(self.a.names[ii] for ii in proposed),raw_gross=raw,expected_cost=charge,raw_net=raw-charge,veto=veto,age_ood=age_ood,calibration_months=months,action=action,**info))
        if not veto:self.want=self.base(k)
        self.records.append(dict(signal_date=sd,entry_date=self.a.cal.iloc[i].entry_date,kind=self.kind,family=self.family,horizon=self.horizon,action=action,veto=veto,old_tickers='|'.join(self.a.names[j] for j in oldids),proposed_tickers='|'.join(self.a.names[j] for j in proposed),target_tickers='|'.join(self.a.names[j] for j in self.want[:2]),raw_net=raw-charge,age_ood=age_ood,calibration_months=months,**info))
        assert self.want[3]==1.,'No discretionary cash/exposure change'
        return self.want
