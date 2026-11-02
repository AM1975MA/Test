"""Descriptive, post-outcome OLC27 horizon comparison; no refit, no new portfolio simulation."""
from pathlib import Path
import sys
import numpy as np,pandas as pd
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,'/mnt/data/olc20_work/stage1/src')
from portfolio_validation import P16,readcsv
rows=[]
for m in ('EU','USA'):
    q=np.load(P16/f'inputs/{m}_STATE_HALF.npz');cal=readcsv(P16/f'inputs/{m}_CALENDAR.csv')
    dates=pd.DatetimeIndex(q['dates']);ticker={str(t):i for i,t in enumerate(q['tickers'])}
    f=pd.read_csv(ROOT/f'results/AUTH/{m}_SCORES.csv.gz',parse_dates=['signal_date'])
    fr=pd.read_csv('/mnt/data/olc26_work/results/'+m+'_FRAME.csv.gz')
    f['future126']=fr.future126
    f['p_tail_pool']=pd.read_csv(ROOT/f'results/LONG_POOL/{m}_PREDICTIONS.csv.gz').p_tail
    f['p_tail_strat']=pd.read_csv(ROOT/f'results/LONG_STRAT/{m}_PREDICTIONS.csv.gz').p_tail
    for _,r in cal.iterrows():
        sig=pd.Timestamp(r.signal_date)
        if not 2022<=sig.year<=2024:continue
        top=f.loc[f.signal_date==sig].dropna(subset=['FUSION']).sort_values(['FUSION','ticker'],ascending=[False,True]).head(5).copy()
        if len(top)!=5:continue
        j,k=dates.get_indexer([pd.Timestamp(r.entry_date),pd.Timestamp(r.exit_date)])
        if j<0 or k<0:continue
        ret=[]
        for t in top.ticker:
            n=ticker[t]
            ok=np.isfinite(q['O'][j,n]) and np.isfinite(q['O'][k,n]) and q['O'][j,n]>0 and q['O'][k,n]>0
            if m=='EU':ok=ok and bool(q['observed'][j,n]) and bool(q['observed'][k,n])
            ret.append(float(q['O'][k,n]/q['O'][j,n]-1) if ok else np.nan)
        top['o2o']=ret
        for name,column in [('AUTH','FUSION'),('POOL_TAIL','p_tail_pool'),('STRAT_TAIL','p_tail_strat'),('FUTURE126_ORACLE','future126')]:
            g=top.dropna(subset=[column,'o2o'])
            if len(g)<3:continue
            rho=float(spearmanr(g[column],g.o2o).statistic)
            if not np.isfinite(rho):continue
            rows.append(dict(market=m,signal_date=str(sig.date()),metric=name,rho=rho,n=len(g)))
df=pd.DataFrame(rows);df.to_csv(ROOT/'results/TOP5_126VSO2O_MONTHLY.csv',index=False)
print(df.groupby(['market','metric']).rho.agg(['size','mean','median']).round(3).to_string())
