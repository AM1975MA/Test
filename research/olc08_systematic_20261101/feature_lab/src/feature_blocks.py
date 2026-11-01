"""Causal normalized price-path/session measurements and training-only compression.
No labels, future eligibility, quote interpolation, or learned thresholds are used here.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
PATH=['path_high_age63','path_underwater63','path_upside_concentration63','path_downside_energy63','path_acceleration63','path_sign_persistence63']
SESSION=['session_overnight_mean21','session_intraday_mean21','session_overnight_share63','session_gap_reversal21','session_intraday_efficiency63','session_gap_tail63']
LEADERSHIP=['lead_rank21_change1','lead_rank21_change3','lead_top21_persistence3','lead_top63_persistence6','lead_rank21_turnover3','lead_rank21_minus63']

def ratio(num,den,neutral=0.):
    num,den=np.asarray(num,float),np.asarray(den,float)
    out=np.full(np.broadcast_shapes(num.shape,den.shape),np.nan)
    finite=np.isfinite(num)&np.isfinite(den)
    np.divide(num,den,out=out,where=finite&(den!=0))
    return np.where(finite&(den==0),neutral,out)

def native_blocks(frame:pd.DataFrame)->pd.DataFrame:
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:raise ValueError('Sorted unique observed dates required')
    if not {'Open','Close'}<=set(frame):raise ValueError('Open and Close required')
    if ((frame[['Open','Close']]<=0)&frame[['Open','Close']].notna()).any().any():raise ValueError('Positive observed prices required')
    n=len(frame);c=frame.Close.astype(float);o=frame.Open.astype(float)
    r=np.log(c/c.shift(1));gap=np.log(o/c.shift(1));day=np.log(c/o)
    out=pd.DataFrame(np.nan,index=frame.index,columns=PATH+SESSION)
    v=r.rolling(63,min_periods=63).std(ddof=1)
    if n>=63:
        wc=sliding_window_view(c.to_numpy(),63)
        good=np.isfinite(wc).all(axis=1)
        high=np.max(wc,axis=1)
        last=np.max(np.where(wc==high[:,None],np.arange(63),-1),axis=1)
        out.loc[out.index[62:],'path_high_age63']=np.where(good,(62-last)/62,np.nan)
        underwater=np.mean(wc<np.maximum.accumulate(wc,axis=1),axis=1)
        out.loc[out.index[62:],'path_underwater63']=np.where(good,underwater,np.nan)
        wr=sliding_window_view(r.to_numpy(),63);good=np.isfinite(wr).all(axis=1)
        pos=np.maximum(wr,0);gain=ratio(np.partition(pos,-3,axis=1)[:,-3:].sum(1),pos.sum(1))
        down=ratio(np.minimum(wr,0).astype(float).__pow__(2).sum(1),np.square(wr).sum(1),.5)
        acc=ratio(wr[:,-21:].mean(1)-wr[:,:42].mean(1),v.to_numpy()[62:])
        sign=(np.sign(wr[:,1:])*np.sign(wr[:,:-1])).mean(1)
        for name,val in zip(PATH[2:],[gain,down,acc,sign]):out.loc[out.index[62:],name]=np.where(good,val,np.nan)
    out[SESSION[0]]=ratio(gap.rolling(21,min_periods=21).mean(),v)
    out[SESSION[1]]=ratio(day.rolling(21,min_periods=21).mean(),v)
    g2=gap.pow(2).rolling(63,min_periods=63).mean();d2=day.pow(2).rolling(63,min_periods=63).mean()
    out[SESSION[2]]=ratio(g2,g2+d2,.5)
    corr=-gap.rolling(21,min_periods=21).corr(day)
    gs=gap.rolling(21,min_periods=21).std();ds=day.rolling(21,min_periods=21).std()
    out[SESSION[3]]=corr.mask(gs.notna()&ds.notna()&((gs==0)|(ds==0)),0).clip(-1,1)
    out[SESSION[4]]=ratio(day.rolling(63,min_periods=63).sum(),day.abs().rolling(63,min_periods=63).sum())
    tail=(gap< -2*v.shift(1)).astype(float).where(gap.notna()&v.shift(1).notna())
    out[SESSION[5]]=tail.rolling(63,min_periods=63).mean()
    return out.replace([np.inf,-np.inf],np.nan)

def sample_native(features:pd.DataFrame,source_dates:pd.Series)->pd.DataFrame:
    # Every source date was fixed by the restored baseline, so missing/stale is preserved.
    return features.reindex(pd.DatetimeIndex(source_dates)).reset_index(drop=True)

def leadership_block(panel:pd.DataFrame)->pd.DataFrame:
    keys=['signal_date','ticker']
    if panel.duplicated(keys).any():raise ValueError('Duplicate panel keys')
    dates=pd.DatetimeIndex(sorted(panel.signal_date.unique()));tickers=sorted(panel.ticker.unique())
    ranks={}
    for base in ['mom21','mom63']:
        v=panel[base].where(panel.eligible)
        q=v.groupby(panel.signal_date).rank(pct=True)
        ranks[base]=pd.DataFrame({'signal_date':panel.signal_date,'ticker':panel.ticker,'value':q}).pivot(index='signal_date',columns='ticker',values='value').reindex(index=dates,columns=tickers)
    a,b=ranks['mom21'],ranks['mom63']
    values=[a-a.shift(1),a-a.shift(3),(a>=.8).astype(float).where(a.notna()).rolling(3,min_periods=3).mean(),(b>=.8).astype(float).where(b.notna()).rolling(6,min_periods=6).mean(),a.diff().abs().rolling(3,min_periods=3).mean(),a-b]
    joined=None
    for col,value in zip(LEADERSHIP,values):
        long=value.rename_axis(index='signal_date',columns='ticker').stack(future_stack=True).rename(col).reset_index()
        joined=long if joined is None else joined.merge(long,on=keys,validate='one_to_one')
    return panel[keys].merge(joined,on=keys,how='left',sort=False,validate='one_to_one')[LEADERSHIP].set_axis(panel.index)

def prune_training(frame:pd.DataFrame,columns:list[str],threshold:float=.985,minimum:int=300):
    if not 0<threshold<=1:raise ValueError('Threshold outside (0,1]')
    if len(columns)!=len(set(columns)):raise ValueError('Duplicate feature names')
    if not set(columns)<=set(frame):raise ValueError('Missing inputs')
    priority=sorted(columns,key=lambda c:(0 if c.endswith('_pct') else 2 if c.endswith('_dev') else 1,columns.index(c)))
    data=frame[priority].replace([np.inf,-np.inf],np.nan)
    corr=data.corr(method='spearman',min_periods=minimum)
    keep=[];log=[]
    for c in priority:
        if data[c].nunique(dropna=False)<=1:
            log.append({'dropped':c,'retained':None,'reason':'constant_in_training_including_missingness','abs_spearman':None});continue
        partner=None
        for k in keep:
            value=corr.at[c,k]
            if np.isfinite(value) and abs(value)>=threshold and data[c].isna().equals(data[k].isna()):partner=k;break
        if partner is None:keep.append(c)
        else:log.append({'dropped':c,'retained':partner,'reason':'train_only_near_collinearity_same_missingness','abs_spearman':float(abs(corr.at[c,partner]))})
    return [c for c in columns if c in keep],log
