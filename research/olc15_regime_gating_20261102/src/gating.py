"""Nested chronological model selection: only mature differential outcomes."""
import numpy as np,pandas as pd
from core import CONTEXT,mature_rows,market_weights,fit_gate,predict_gate

FEATURE_SETS={'CONSTANT':[],'RECENT':['recent'],'CONTEXT':CONTEXT,'CONTEXT_RECENT':CONTEXT+['recent']}

def trainable(frame,cutoff):
    z=mature_rows(frame,cutoff)
    return z[(pd.to_datetime(z.date)>=pd.Timestamp('2021-01-01'))&z[CONTEXT].notna().all(axis=1)].copy()

def enough(frame):
    n=frame.groupby('market').date.nunique()
    return set(n.index)=={'EU','USA'} and n.min()>=12

def fit_year(panel,year,features):
    cutoff=pd.Timestamp(year,1,1);tr=trainable(panel,cutoff)
    record={'year':year,'features':list(features),'active':False,'cutoff':str(cutoff.date()),'counts':tr.groupby('market').size().to_dict(),'fallback_g':1.}
    if not enough(tr):return record
    folds=[];years=sorted(tr.date.dt.year.unique())[-2:]
    for y in years:
        a=trainable(panel,pd.Timestamp(y,1,1));v=tr[tr.date.dt.year.eq(y)]
        if enough(a) and set(v.market)=={'EU','USA'} and v.groupby('market').date.nunique().min()>=3:
            folds.append((int(y),a,v))
    tests=[];los={lam:[] for lam in [1.,10.,100.]}
    for lam in los:
        for vy,a,v in folds:
            model=fit_gate(a,features,lam);pred=predict_gate(model,v)['delta'];w=market_weights(v.market)
            mse=float(w@((pred-v.delta.to_numpy())**2));los[lam].append(mse)
            tests.append(dict(penalty=lam,validation_year=vy,mse=mse,train_max_available=str(a.available.max().date()),training_counts=a.groupby('market').size().to_dict(),validation_counts=v.groupby('market').size().to_dict()))
    penalty=min(los,key=lambda lam:(np.mean(los[lam]),-lam)) if folds else 10.
    model=fit_gate(tr,features,penalty)
    record.update(active=True,model=model,inner=tests,default_penalty_no_valid_fold=not bool(folds),max_train_available=str(tr.available.max().date()),train_keys=[f'{x.market}:{x.date.date()}' for x in tr.itertuples()],validation_means={str(k):float(np.mean(v)) if v else None for k,v in los.items()})
    return record
