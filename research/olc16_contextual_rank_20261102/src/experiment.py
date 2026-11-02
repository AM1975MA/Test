"""Chronological orchestration. Every model is fitted on mature query groups."""
from __future__ import annotations
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from context_model import FEATURES,PRIOR,fit_model,predict_weights
from ranking_core import utility
from layer_metrics import topk_weights

ROOT=Path(__file__).resolve().parents[1]
MARKETS=('EU','USA')
LEARNED=('PAIR_STATIC','PAIR_CONTEXT','TOP2_STATIC','TOP2_CONTEXT')
CONTROLS=('ORIGINAL','CUM_FIXED','CUM_FIT')
LAGGED=('PAIR_LAG','TOP2_LAG')
NULLS=tuple(f'{kind}_NULL{s}' for kind in ['PAIR','TOP2'] for s in [1601,1602])
REVALUED=tuple(v+'_REVALUE' for v in LEARNED)
VARIANTS=CONTROLS+LEARNED+LAGGED+REVALUED
BASE_NATIVE=CONTROLS+LEARNED+LAGGED+NULLS
NULL_REVALUED=tuple(v+'_REVALUE' for v in NULLS)
NATIVE_VARIANTS=VARIANTS+NULLS+NULL_REVALUED

def dump(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2,default=str,allow_nan=False));tmp.replace(path)

def readcsv(path):
    f=pd.read_csv(path,float_precision='round_trip')
    for c in f:
        if c in ('date','signal_date','entry_date','available','context_source_date') or c.startswith('exit_date'):
            f[c]=pd.to_datetime(f[c])
    return f

def load_groups():
    ctx=readcsv(ROOT/'inputs/GATE_PANEL.csv').set_index(['market','date'])
    groups=[];frames={};controls={}
    for m in MARKETS:
        f=readcsv(ROOT/f'inputs/{m}_FITTING_FRAME.csv.gz').sort_values(['signal_date','ticker']).reset_index(drop=True)
        c=readcsv(ROOT/f'inputs/{m}_MEAN3_SCORES.csv.gz').sort_values(['signal_date','ticker']).reset_index(drop=True)
        pd.testing.assert_frame_equal(f[['signal_date','ticker']],c[['signal_date','ticker']])
        frames[m]=f;controls[m]=c;prev=np.full(3,np.nan)
        for date,g0 in f.groupby('signal_date',sort=True):
            g=g0[np.isfinite(g0.ORIGINAL_P15)];pos=g.index.to_numpy()
            if len(g)<2:raise ValueError('Insufficient candidates')
            z=g[['C21','C42','C63']].to_numpy(float)
            if not np.isfinite(z).all():raise ValueError('Mismatched forecast support')
            x=ctx.loc[(m,date),list(FEATURES)].to_numpy(float)
            source=ctx.loc[(m,date),'context_source_date']
            if pd.notna(source) and source>date:raise ValueError('Future context')
            r=g[['fwd_ret_21','fwd_ret_42','fwd_ret_63']].to_numpy(float)
            complete=np.isfinite(r).all() and (r>-1).all() and g.exit_date_63.notna().all()
            groups.append(dict(market=m,date=date,positions=pos,tickers=g.ticker.to_numpy(),z=z,x=x,xlag=prev.copy(),
                         available=g.exit_date_63.max() if complete else pd.NaT,
                         full=bool(complete),u=utility(r) if complete else np.full(len(g),np.nan),
                         returns=r,target=g.TARGET.to_numpy(),anchor=c.loc[pos,'CUM_FIXED_MAPPED'].to_numpy()))
            prev=x.copy()
    return sorted(groups,key=lambda g:(g['date'],g['market'])),frames,controls

def eligible(groups,cutoff):
    cutoff=pd.Timestamp(cutoff)
    return [g for g in groups if g['date']<cutoff and g['full'] and pd.notna(g['available']) and g['available']<cutoff]

def counts(groups):return {m:sum(g['market']==m for g in groups) for m in MARKETS}

def folds(groups,cutoff):
    past=eligible(groups,cutoff);out=[]
    for year in sorted({g['date'].year for g in past}):
        tr=eligible(past,pd.Timestamp(year,1,1));va=[g for g in past if g['date'].year==year]
        if min(counts(tr).values())>=8 and min(counts(va).values())>=4:out.append((year,tr,va))
    return out[-2:]

def value(groups,model):
    vals={m:[] for m in MARKETS}
    for g in groups:
        b=predict_weights(model,g['x']);s=g['z']@b
        vals[g['market']].append(float(topk_weights(s)@g['u']-g['u'].mean()))
    if any(not v for v in vals.values()):raise ValueError('Both validation markets required')
    means={m:float(np.mean(vals[m])) for m in MARKETS}
    return dict(**means,criterion=.5*(means['EU']+means['USA'])-.25*abs(means['EU']-means['USA']))

def fit_year(groups,year,kind,contextual):
    cutoff=pd.Timestamp(year,1,1);past=eligible(groups,cutoff);n=counts(past)
    if min(n.values())<18:
        return dict(theta=[[0.],[0.]],contextual=False,scaler={},kind=kind,fallback=True,
                    training_groups=n,cutoff=str(cutoff),cv=[],inner_fits=0)
    trace=[];best=None;cv=folds(past,cutoff) if contextual else []
    for penalty in [.01,.1,1.] if contextual else []:
        valgroups=[];predscores=[];fold_rows=[]
        for y,tr,va in cv:
            model=fit_model(tr,True,kind,penalty)
            valgroups.extend(va)
            predscores.extend(g['z']@predict_weights(model,g['x']) for g in va)
            fold_rows.append(dict(year=y,train=counts(tr),valid=counts(va),
                                 max_training_exit=str(max(g['available'] for g in tr)),loss=model['loss']))
        if valgroups:
            vals={m:[] for m in MARKETS}
            for g,s in zip(valgroups,predscores):vals[g['market']].append(float(topk_weights(s)@g['u']-g['u'].mean()))
            v={m:float(np.mean(vals[m])) for m in MARKETS};v['criterion']=.5*(v['EU']+v['USA'])-.25*abs(v['EU']-v['USA'])
            trace.append(dict(penalty=penalty,**v,folds=fold_rows))
            key=(v['criterion'],penalty)
            if best is None or key>best[0]:best=(key,penalty)
    penalty=best[1] if best else .1
    model=fit_model(past,contextual,kind,penalty)
    model.update(cutoff=str(cutoff),year=year,fallback=False,cv=trace,inner_fits=len(trace)*len(cv),
                 max_training_exit=str(max(g['available'] for g in past)),training_dates=[(g['market'],str(g['date']),str(g['available'])) for g in past])
    return model

def shuffled_context_groups(groups,seed):
    rng=np.random.default_rng(seed);out=[dict(g,x=g['x'].copy()) for g in groups]
    for m in MARKETS:
        idx=[i for i,g in enumerate(out) if g['market']==m];p=rng.permutation(idx)
        for i,j in zip(idx,p):out[i]['x']=groups[j]['x'].copy()
    return out
