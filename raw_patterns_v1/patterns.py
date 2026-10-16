"""Historical OHLCV multiscale flattening; no target-dependent representation."""
import numpy as np
import pandas as pd

def flatten_views(values,pos):
    a=np.asarray(values,dtype=float)
    if pos<125 or pos>=len(a):raise ValueError('Insufficient historical bars')
    history=a[pos-125:pos+1]
    if not np.isfinite(history).all() or (history[:,:4]<=0).any() or (history[:,4]<0).any():
        raise ValueError('Incomplete historical window')
    views=[]
    for stride in (1,3,6):
        b=history[-21*stride:].reshape(21,stride,5)
        candles=np.column_stack([b[:,0,0],b[:,:,1].max(axis=1),b[:,:,2].min(axis=1),b[:,-1,3],b[:,:,4].sum(axis=1)])
        prices=np.log(candles[:,:4]/candles[0,3])
        mean=candles[:,4].mean()
        volumes=np.log1p(candles[:,4]/mean)-np.log(2.) if mean>0 else np.zeros(21)
        views.append(np.column_stack([prices,volumes]).ravel())
    return np.concatenate(views)

def leave_one_out(x):
    x=np.asarray(x,dtype=float)
    if len(x)<2:raise ValueError('Context requires peers')
    return (x.sum(axis=0,keepdims=True)-x)/(len(x)-1)

def split_dates(frame,year):
    cutoff=pd.Timestamp(year,1,1)
    mature=frame[(frame.signal_date<cutoff)&(frame.exit_date_21<cutoff)]
    dates=np.sort(mature.signal_date.unique())
    if len(dates)<20:raise ValueError('Insufficient pre-cutoff queries')
    start=pd.Timestamp(dates[-12])
    val=mature[mature.signal_date>=start]
    safe=mature.groupby('signal_date').exit_date_21.max()
    sub=mature[mature.signal_date.isin(safe.index[(safe.index<start)&(safe<start)])]
    test=frame[frame.signal_date.dt.year==year]
    return sub.copy(),val.copy(),test.copy()
