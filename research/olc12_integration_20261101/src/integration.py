"""Pure causal score contracts. No labels, costs or fitted weights enter this module."""
from __future__ import annotations
import numpy as np
import pandas as pd

VARIANTS = ['MATCHED_REG','NAIVE_CLASS','MIX_CLASS_CURRENT','SOLO_CLASS_CURRENT',
            'SOLO_CLASS_MEMORY','SOLO_REG_CURRENT','SOLO_REG_MEMORY','CLASS_NATIVE',
            'PROB_MEMORY','SPECIALIST20_CURRENT','SPECIALIST20_MEMORY','RERANK5','ARCHIVE_S101']

def memory(values):
    a=np.asarray(values,float)
    if a.ndim!=2 or len(a)==0:raise ValueError('Nonempty time by asset matrix required')
    l1=a[np.maximum(np.arange(len(a))-1,0)];l2=a[np.maximum(np.arange(len(a))-2,0)]
    stack=np.stack([a,l1,l2]);w=np.array([.4,.3,.3])[:,None,None];ok=np.isfinite(stack)
    den=(w*ok).sum(0)
    out=np.divide((np.where(ok,stack,0)*w).sum(0),den,out=np.full_like(a,np.nan),where=den>0)
    # Exact legacy arithmetic where there are no missing observations.
    out=np.where(ok.all(0),.4*a+.3*l1+.3*l2,out)
    return np.where(np.isfinite(a),out,np.nan)

def rerank_shortlist(parent,specialist,k=5):
    a=np.asarray(parent,float);b=np.asarray(specialist,float)
    if a.ndim!=1 or a.shape!=b.shape or k<2:raise ValueError('Aligned scores and k>=2 required')
    valid=np.isfinite(a)&np.isfinite(b);out=np.full_like(a,np.nan)
    if valid.sum()<2:return out
    cutoff=np.sort(a[valid])[-min(k,valid.sum())];eligible=valid&(a>=cutoff)
    # All boundary ties enter; below-shortlist ranks cannot displace a shortlisted name.
    out[valid]=pd.Series(a[valid]).rank(pct=True,method='average').to_numpy()
    out[eligible]=2.+b[eligible]
    return out

def _rank_matrix(a):
    return pd.DataFrame(a).rank(axis=1,pct=True,method='average').to_numpy()

def build_scores(frame):
    required=['signal_date','ticker','RETURN','ET_REG','XGB_REG','XGB_CLASS','ARCH_ET','ARCH_XGB']
    if not set(required)<=set(frame):raise ValueError('Required forecast fields absent')
    f=frame[required].copy().sort_values(['signal_date','ticker']).reset_index(drop=True)
    f['signal_date']=pd.to_datetime(f.signal_date)
    if f.duplicated(['signal_date','ticker']).any():raise ValueError('Duplicate forecast key')
    prob=f.XGB_CLASS.dropna()
    if ((prob<0)|(prob>1)).any():raise ValueError('Probability outside [0,1]')
    dates=pd.DatetimeIndex(sorted(f.signal_date.unique()));tickers=sorted(f.ticker.unique())
    def mat(col):return f.pivot(index='signal_date',columns='ticker',values=col).reindex(index=dates,columns=tickers).to_numpy(float)
    r=mat('RETURN');e=_rank_matrix(mat('ET_REG'));x=_rank_matrix(mat('XGB_REG'));p=mat('XGB_CLASS');c=_rank_matrix(p)
    pe=lambda a:np.clip(a,0,1)**1.1
    valid=np.isfinite(r)&np.isfinite(e)&np.isfinite(x)&np.isfinite(c)
    current=.6*e+.4*x;mix=.6*e+.4*c
    base=.475*r+.525*pe(memory(current))
    d={'MATCHED_REG':base,'NAIVE_CLASS':.475*r+.525*pe(memory(mix)),
       'MIX_CLASS_CURRENT':.475*r+.525*pe(mix),
       'SOLO_CLASS_CURRENT':.475*r+.525*pe(c),'SOLO_CLASS_MEMORY':.475*r+.525*pe(memory(c)),
       'SOLO_REG_CURRENT':.475*r+.525*pe(x),'SOLO_REG_MEMORY':.475*r+.525*pe(memory(x)),
       'CLASS_NATIVE':p,'PROB_MEMORY':.475*r+.525*pe(_rank_matrix(memory(p))),
       'SPECIALIST20_CURRENT':.8*base+.2*c,'SPECIALIST20_MEMORY':.8*base+.2*pe(memory(c)),
       'RERANK5':np.vstack([rerank_shortlist(a,b) for a,b in zip(base,p)]),
       'ARCHIVE_S101':.475*r+.525*pe(memory(.6*_rank_matrix(mat('ARCH_ET'))+.4*_rank_matrix(mat('ARCH_XGB'))))}
    out=f[['signal_date','ticker']].copy();di=dates.get_indexer(out.signal_date);ti=pd.Index(tickers).get_indexer(out.ticker)
    for name in VARIANTS:out[name]=np.where(valid,d[name],np.nan)[di,ti]
    return out
