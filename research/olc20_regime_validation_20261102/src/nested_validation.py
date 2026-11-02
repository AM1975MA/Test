"""Annual nested fit of the frozen OLC16 procedure, including all null re-selection.

Training views are built independently inside each inner/outer cutoff. Validation
contexts are unpermuted. No outcome selects a seed or which trials to retain.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from paths import P16
from context_model import fit_model,predict_weights
from experiment import eligible,counts,folds,MARKETS
from layer_metrics import topk_weights
from context_views import transformed

def fit_annual(groups,year,seed=None,omit=None,grid_factor=1.,contextual=True):
    if grid_factor not in (.5,1.,2.):raise ValueError('Unregistered penalty grid')
    cutoff=pd.Timestamp(year,1,1);past=eligible(groups,cutoff);n=counts(past)
    audits=[]
    def training_view(gs,at):
        view,a=transformed(gs,seed=seed,omit=omit)
        a.update(cutoff=str(at),max_training_exit=str(max(g['available'] for g in gs)))
        assert pd.Timestamp(a['max_training_exit'])<pd.Timestamp(at)
        assert all(pd.Timestamp(x['donor_date'])<pd.Timestamp(at) for x in a['mapping'])
        audits.append(a);return view
    if min(n.values())<18:
        return dict(theta=[[0.],[0.]],contextual=False,scaler={},kind='top2',fallback=True,
           training_groups=n,cutoff=str(cutoff),cv=[],inner_fits=0),dict(views=[],inner_validation_context='AUTHENTIC')
    trace=[];best=None;cv=folds(past,cutoff) if contextual else []
    prepared=[]
    for y,tr,va in cv:
        trv=training_view(tr,pd.Timestamp(y,1,1))
        if omit is None:vav=va
        else:vav=transformed(va,omit=omit)[0]
        prepared.append((y,trv,vav))
    for penalty in [x*grid_factor for x in (.01,.1,1.)] if contextual else []:
        valgroups=[];predscores=[];fold_rows=[]
        for y,tr,va in prepared:
            model=fit_model(tr,True,'top2',penalty)
            valgroups.extend(va)
            predscores.extend(g['z']@predict_weights(model,g['x']) for g in va)
            fold_rows.append(dict(year=y,train=counts(tr),valid=counts(va),
              max_training_exit=str(max(g['available'] for g in tr)),loss=model['loss'],
              optimization_starts=model['starts']))
        if valgroups:
            vals={m:[] for m in MARKETS}
            for g,s in zip(valgroups,predscores):
                vals[g['market']].append(float(topk_weights(s)@g['u']-g['u'].mean()))
            v={m:float(np.mean(vals[m])) for m in MARKETS}
            v['criterion']=.5*(v['EU']+v['USA'])-.25*abs(v['EU']-v['USA'])
            trace.append(dict(penalty=penalty,**v,folds=fold_rows))
            key=(v['criterion'],penalty)
            if best is None or key>best[0]:best=(key,penalty)
    penalty=best[1] if best else .1*grid_factor
    tr=training_view(past,cutoff)
    model=fit_model(tr,contextual,'top2',penalty)
    model.update(cutoff=str(cutoff),year=year,fallback=False,cv=trace,inner_fits=len(trace)*len(cv),
      max_training_exit=str(max(g['available'] for g in past)),
      training_dates=[(g['market'],str(g['date']),str(g['available'])) for g in past])
    return model,dict(views=audits,inner_validation_context='AUTHENTIC',seed=seed,omit=omit,grid_factor=grid_factor)
