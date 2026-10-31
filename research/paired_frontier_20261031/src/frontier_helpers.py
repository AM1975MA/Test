"""Causal research helpers; frozen choices, not a live trading implementation."""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

def asof_snapshot(frame, dates, max_age_days=5):
    """Last observed value no later than cutoff, with an explicit age bound."""
    frame=frame.sort_index();dates=pd.DatetimeIndex(dates)
    if frame.index.has_duplicates or not dates.is_monotonic_increasing:raise ValueError('Unique ordered dates required')
    values=pd.DataFrame(np.nan,index=dates,columns=frame.columns)
    sources=pd.DataFrame(pd.NaT,index=dates,columns=frame.columns,dtype='datetime64[ns]')
    for col in frame:
        s=frame[col].dropna();ix=s.index.searchsorted(dates,side='right')-1;good=ix>=0
        ii=np.maximum(ix,0)
        if len(s)==0:continue
        age=(dates-s.index[ii]).days;good&=(age<=max_age_days)
        values.loc[good,col]=s.to_numpy()[ix[good]];sources.loc[good,col]=s.index[ix[good]].values
    return values,sources

def diversify_pair(scores,corr,buffer=False,previous=(),correlation_limit=.90):
    scores=np.asarray(scores,float);valid=np.flatnonzero(np.isfinite(scores));order=valid[np.argsort(-scores[valid],kind='stable')]
    if len(order)<2:return []
    chosen=[]
    if buffer:
        chosen=[int(j) for j in order[:4] if int(j) in previous][:2]
    chosen+= [int(j) for j in order if int(j) not in chosen][:2-len(chosen)]
    chosen=sorted(chosen,key=lambda j:-scores[j]);first,second=chosen
    if correlation_limit is not None and np.isfinite(corr[first,second]) and corr[first,second]>=correlation_limit:
        alternatives=[int(j) for j in order[:10] if j!=first and np.isfinite(corr[first,j]) and corr[first,j]<correlation_limit]
        if alternatives:second=alternatives[0]
    return sorted([first,second],key=lambda j:-scores[j])

def systematic_cap(market_r5,negative_share,ma20_ratio,slow,ma200_ratio,market_r63):
    """Inputs already lagged to previous closes. Recovery is not a fixed timer."""
    arrays=[np.asarray(x,float) for x in [market_r5,negative_share,ma20_ratio,ma200_ratio,market_r63]]
    if len({len(x) for x in arrays})!=1:raise ValueError('Aligned risk arrays required')
    out=np.ones(len(arrays[0]));active=False
    for i,(r,b,m,m200,r63) in enumerate(zip(*arrays)):
        if np.isfinite(r) and np.isfinite(b) and r<=-.05 and b>=.60:active=True
        if active and np.isfinite(r) and r>0 and np.isfinite(m) and m>=1:active=False
        cap=1. if not active else (.75 if np.isfinite(r) and r>0 else .5)
        if slow and np.isfinite(m200) and m200<1 and np.isfinite(r63) and r63<0:cap=min(cap,.5)
        out[i]=cap
    return out

def monthly_calibration(dates,exitdates,features,targets,window=None,minimum=24,alpha=10.):
    """Fit equal-month-weighted Ridge on completed outcomes only; score unseen rows."""
    dates=pd.DatetimeIndex(dates);exitdates=pd.DatetimeIndex(exitdates);features=np.asarray(features,float);targets=np.asarray(targets,float)
    if features.shape[:2]!=targets.shape or len(dates)!=len(features):raise ValueError('Bad calibration shapes')
    out=np.full_like(targets,np.nan);audit=[]
    for i,sd in enumerate(dates):
        past=np.flatnonzero((exitdates<sd)&(dates<sd))
        if window is not None:past=past[-window:]
        current=np.isfinite(features[i]).all(axis=1)
        complete=[]
        for j in past:
            ok=np.isfinite(features[j]).all(axis=1)&np.isfinite(targets[j])
            if ok.sum()>=2:complete.append((j,ok))
        trained=len(complete)>=minimum
        row={'signal_date':str(sd.date()),'trained':trained,'train_months':len(complete),'weight_sum':0.,'max_exit':None}
        if not trained:out[i,current]=features[i,current,:2].mean(axis=1)
        else:
            X=np.concatenate([features[j,ok] for j,ok in complete]);y=np.concatenate([targets[j,ok] for j,ok in complete]);w=np.concatenate([np.full(ok.sum(),1./ok.sum()) for j,ok in complete])
            model=Ridge(alpha=alpha,fit_intercept=True);model.fit(X,y,sample_weight=w)
            out[i,current]=model.predict(features[i,current]);row.update(weight_sum=float(w.sum()),max_exit=str(exitdates[[j for j,ok in complete]].max().date()),coefficients=model.coef_.tolist(),intercept=float(model.intercept_))
        audit.append(row)
    return out,audit
