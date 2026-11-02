"""Reconstruct the frozen V6 selector, changing only its primary-holding inputs.
Algorithm transcribed from AM1975MA/Test vendor/etf_trader_v2/src/etf_trader/ma3/v6.py
blob6c5d3fd6f54fb5ef5162f4b26d3ef9af2af34701. No parameter search.
USA proxySPY; EU EXSA.DE mapping is admitted ONLY after exact parent-alt parity.
Works on the frozen Close matrices; does not certify underlying market data.
"""
import numpy as np,pandas as pd

def rank_rows(x):
 out=np.full_like(x,np.nan,dtype=float)
 for t in range(len(x)):
  ok=np.isfinite(x[t]);n=int(ok.sum())
  if n<2:continue
  o=np.argsort(x[t,ok]);r=np.empty(n);r[o]=(np.arange(n)+.5)/n;out[t,ok]=r
 return out

def rebuild(q,d1=None,d2=None,weights=None,allowed=None):
 C=np.asarray(q['C'],float);D,N=C.shape;ticks=list(q['tickers'])
 d1=q['d1'] if d1 is None else d1;d2=q['d2'] if d2 is None else d2;weights=q['weights'] if weights is None else weights
 bil=ticks.index('BIL' if 'BIL'in ticks else 'EUR_CASH_A');shv=ticks.index('SHV' if 'SHV'in ticks else 'EUR_CASH_B')
 proxy=ticks.index('SPY' if 'SPY'in ticks else 'EXSA.DE')
 ret={}
 for h in [5,21,63]:
  x=np.full_like(C,np.nan);x[h:]=C[h:]/C[:-h]-1;ret[h]=x
 dd=np.full_like(C,np.nan);vol=np.full_like(C,np.nan);above=np.zeros(D);pos5=np.zeros(D)
 for t in range(20,D):
  dd[t]=C[t]/np.nanmax(C[t-20:t+1],axis=0)-1
  rr=C[t-19:t+1]/C[t-20:t]-1;vol[t]=np.nanstd(rr,axis=0,ddof=1)
  above[t]=np.nanmean(C[t]>np.nanmean(C[t-19:t+1],axis=0));pos5[t]=np.nanmean(ret[5][t]>0)
 ma=pd.DataFrame(C).rolling(200,min_periods=200).mean().to_numpy();v200=C[:,proxy]/ma[:,proxy]-1;pos21=np.nanmean(ret[21]>0,axis=1)
 rec=np.zeros(D,bool);rec[1:]=(ret[5][:-1,proxy]>.025)&(pos5[:-1]>.58)&(above[:-1]>.48)&(v200[:-1]<-.03)&(pos21[:-1]<.75)
 stacked=np.stack([rank_rows(ret[5]),rank_rows(ret[21]),rank_rows(ret[63]),rank_rows(dd),rank_rows(-vol)])
 n=np.isfinite(stacked).sum(0);sol=np.divide(np.nansum(stacked,axis=0),n,out=np.full_like(C,np.nan),where=n>0)
 alt=np.full(d1.shape,-1,dtype=np.int16)
 for k in range(65,D-1):
  if not(rec[k] and q['gross'][k]>=.74 and q['gross'][k]<.999):continue
  t=k-1;ids=np.arange(N);ok=np.isfinite(sol[t])&np.isfinite(ret[5][t])&np.isfinite(ret[21][t])&np.isfinite(ret[63][t])&np.isfinite(dd[t])
  ids=ids[ok&(ids!=bil)&(ids!=shv)&(allowed[t] if allowed is not None else np.ones(N,bool))]
  ids=ids[(ret[5][t,ids]>.005)&(ret[21][t,ids]>0)&(ret[63][t,ids]>-.03)&(dd[t,ids]>-.07)&(sol[t,ids]>=.72)]
  if not len(ids):continue
  sc=sol[t,ids]+.20*np.clip(ret[5][t,ids]/.05,-1,1)+.10*np.clip(ret[21][t,ids]/.10,-1,1)
  ids=ids[np.argsort(-sc)]
  for b in range(d1.shape[0]):
   i1=int(d1[b,k]);i2=int(d2[b,k]);w=weights[b,k]
   if i1<0:continue
   j=i2 if i2>=0 else i1
   o5=w*ret[5][t,i1]+(1-w)*ret[5][t,j];o21=w*ret[21][t,i1]+(1-w)*ret[21][t,j]
   odd=w*dd[t,i1]+(1-w)*dd[t,j];os=w*sol[t,i1]+(1-w)*sol[t,j]
   for qi in ids:
    if qi in (i1,i2):continue
    if ret[5][t,qi]>=o5+.015 and ret[21][t,qi]>=o21+.005 and dd[t,qi]>=odd+.015 and sol[t,qi]>=os+.05:
     alt[b,k]=qi;break
 return alt
