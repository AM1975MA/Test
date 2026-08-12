#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def one(s: str, old: str, new: str, label: str) -> str:
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f"{label}: expected one site, found {n}")
    return s.replace(old,new)


def patch(path: Path, mode: str) -> None:
    s=path.read_text()
    # Exact Jul-27 LIVE training calendar: never train on signal months before 2007-09.
    s=one(s,
        "O,H,L,C,V=[mats[k] for k in ['Open','High','Low','Close','Volume']]; dates=month_end_dates(C.index)",
        "O,H,L,C,V=[mats[k] for k in ['Open','High','Low','Close','Volume']]; dates=month_end_dates(C.index); dates=dates[dates>=pd.Timestamp('2007-09-01')]",
        'training start')

    # Packaging only: normalize stacked index names, no economic change.
    s=one(s,
        "for k,x in mats.items(): longs.append(x.stack(dropna=False).rename(k.lower()).reset_index().rename(columns={'level_0':'date','level_1':'ticker'}))",
        "for k,x in mats.items():\n        q=x.stack(dropna=False).rename(k.lower()).reset_index(); q.columns=['date','ticker',k.lower()]; longs.append(q)",
        'package index names')
    s=s.replace("'compact_historical_params':False", "'compact_historical_params':True")

    if mode=='FORMULA':
        old='''def rolling_cvar10(ret,h):\n    arr=ret.to_numpy(float); out=np.full_like(arr,np.nan)\n    for i in range(h-1,len(ret)):\n        w=arr[i-h+1:i+1]; q=np.nanquantile(w,.10,axis=0); mask=w<=q[None,:]; num=np.nansum(np.where(mask,w,np.nan),axis=0); den=np.sum(mask & np.isfinite(w),axis=0); out[i]=np.where(den>0,num/den,np.nan)\n    return pd.DataFrame(out,index=ret.index,columns=ret.columns)'''
        new='''def rolling_cvar10(ret,h):\n    arr=ret.to_numpy(float); n,m=arr.shape; out=np.full((n,m),np.nan,dtype=float)\n    if n<h: return pd.DataFrame(out,index=ret.index,columns=ret.columns)\n    windows=np.lib.stride_tricks.sliding_window_view(arr,h,axis=0); chunk_size=256; max_k=int(np.floor((h-1)*0.10)+1)\n    for start in range(0,len(windows),chunk_size):\n        w=windows[start:start+chunk_size]; finite=np.isfinite(w); counts=finite.sum(axis=2); k=np.where(counts>0,np.floor((counts-1)*0.10).astype(int)+1,0); safe=np.where(finite,w,np.inf); worst=np.partition(safe,max_k-1,axis=2)[:,:,:max_k]; csum=np.cumsum(worst,axis=2); row=np.arange(w.shape[0])[:,None]; col=np.arange(m)[None,:]; picked=np.where(k>0,csum[row,col,np.maximum(k-1,0)]/np.maximum(k,1),np.nan); out[h-1+start:h-1+start+w.shape[0]]=picked\n    return pd.DataFrame(out,index=ret.index,columns=ret.columns)'''
        s=one(s,old,new,'exact CVaR')
        old2="D['intraday_mom21']=snapshot((C/O-1).rolling(21,min_periods=21).sum(),dates);D['gap_mom21']=snapshot((O/prev-1).rolling(21,min_periods=21).sum(),dates);D['max_gain21']=snapshot(ret.rolling(21,min_periods=21).max(),dates);D['max_loss21']=snapshot(ret.rolling(21,min_periods=21).min(),dates);D['cvar10_63']=snapshot(rolling_cvar10(ret,63),dates)"
        new2="intra=C/O-1; gap=O/prev-1; D['intraday_mom21']=snapshot(np.expm1(np.log1p(intra.clip(lower=-0.999999)).rolling(21,min_periods=21).sum()),dates);D['gap_mom21']=snapshot(np.expm1(np.log1p(gap.clip(lower=-0.999999)).rolling(21,min_periods=21).sum()),dates);D['max_gain21']=snapshot(ret.rolling(21,min_periods=21).max(),dates);D['max_loss21']=snapshot(ret.rolling(21,min_periods=21).min(),dates);D['cvar10_63']=snapshot(rolling_cvar10(ret,63),dates)"
        s=one(s,old2,new2,'Opportunity compounding')
    path.write_text(s)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); ap.add_argument('--mode',choices=['START_ONLY','FORMULA'],required=True); a=ap.parse_args(); patch(Path(a.source),a.mode); print('patched',a.mode,a.source)
if __name__=='__main__': main()
