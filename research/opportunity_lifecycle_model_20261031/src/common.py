from pathlib import Path
import os,sys,hashlib,json
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1]
DIAG=Path(os.environ.get('OLC_SOURCE_ROOT','/mnt/data/lifecycle_restore/opportunity_lifecycle_20261031'))
F=DIAG/'inputs/frontier'
sys.path.insert(0,str(F/'src'))
from native_screen import load,state_with_score,simulate,metrics,SOURCE
from calendar_replay import crop
import numpy as np,pandas as pd

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def sources(market):
    q,_,C,*_=load(market);q=crop(q,'2019-02-01');T=list(C.columns)
    base=F/'results/rebuilt'
    def matrix(name):return pd.read_csv(base/f'{market}_{name}_SCORES.csv',index_col=0,parse_dates=True,float_precision='round_trip').reindex(columns=T)
    score=matrix('LEGACY');rr=matrix('R_ONLY');hy=matrix('H_ONLY')
    pred=pd.read_csv(F/f'results/calendar/{market}_FORECASTS.csv.gz',parse_dates=['signal_date','source_date'])
    assert (pred.source_date<=pred.signal_date).all()
    et=pred.pivot(index='signal_date',columns='ticker',values='ET').reindex_like(score)
    xx=pred.pivot(index='signal_date',columns='ticker',values='XGB').reindex_like(score)
    cal=pd.read_csv(F/f'results/calendar/{market}_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date'])
    cal=cal[cal.signal_date.isin(score.index)].sort_values('signal_date').reset_index(drop=True)
    if market=='EU':
        raw={k:pd.read_pickle(SOURCE/'inputs'/f'EU_{k}.pkl').reindex(columns=T).loc[:'2026-07-01'] for k in ['Open','High','Low','Close','Volume']}
    else:
        frames={t:pd.read_csv(SOURCE/'raw/_repeat1'/f'{t}.csv',index_col=0,parse_dates=True,float_precision='round_trip').loc[:'2026-07-01'] for t in T}
        raw={k:pd.DataFrame({t:f[k] for t,f in frames.items()}).reindex(columns=T) for k in ['Open','High','Low','Close','Volume']}
    return q,C,score,rr,hy,et,xx,cal,pred,raw
