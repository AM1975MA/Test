from pathlib import Path
import sys,hashlib
import numpy as np,pandas as pd
B=Path(__file__).resolve().parents[1]
SRC=B/'source/research/tail-only-and-allocation-ablation-20261017'
sys.path[:0]=[str(SRC),str(SRC/'vendor/etf_trader_v2/src')]
def training_mask(f,year):
 cutoff=pd.Timestamp(year,1,1)
 return (pd.to_datetime(f.signal_date)<cutoff)&(pd.to_datetime(f.exit_date_21)<cutoff)&np.isfinite(f.fwd_ret_21)
def asof_external(s,dates):
 dates=pd.DatetimeIndex(dates);idx=s.dropna().index;pos=idx.searchsorted(dates,side='left')-1
 a=np.full(len(dates),np.nan);ok=pos>=0;a[ok]=s.dropna().to_numpy()[pos[ok]]
 return pd.Series(a,index=dates)
def score_blend(b,et,x):
 t=.6*et+.4*x;l1=np.vstack([t[:1],t[:-1]]);l2=np.vstack([t[:1],t[:1],t[:-2]])
 return .475*b+.525*np.power(np.clip(.4*t+.3*l1+.3*l2,0,1),1.1)
def select_pair(a):
 ok=np.flatnonzero(np.isfinite(a));return ok[np.argsort(-a[ok],kind='stable')[:2]].tolist()
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
