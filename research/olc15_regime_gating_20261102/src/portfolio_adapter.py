"""Label-blind monthly targets; actual execution availability remains engine-owned."""
from __future__ import annotations
import numpy as np,pandas as pd

def adapt_state(q,calendar,scores,variant):
    st={k:v.copy() for k,v in q.items()};ds=pd.DatetimeIndex(q['dates']);tickers=list(q['tickers']);D=len(ds)
    st['d1']=np.full((1,D),-1,dtype=np.int64);st['d2']=np.full((1,D),-1,dtype=np.int64);st['weights']=np.full((1,D),.5)
    events=np.zeros(D,bool);decisions=[]
    cal=calendar.sort_values('entry_date')
    if (cal.signal_date>=cal.entry_date).any():raise ValueError('Signal must precede fill')
    groups={pd.Timestamp(d):g for d,g in scores.groupby('signal_date')}
    for row in cal.itertuples(index=False):
        signal=pd.Timestamp(row.signal_date);entry=pd.Timestamp(row.entry_date)
        if entry>ds[-1]:continue
        if entry not in ds and entry>=ds[0]:raise ValueError('Entry missing from declared execution calendar')
        k=ds.searchsorted(entry);g=groups.get(signal)
        if g is None:raise ValueError(f'Forecast date unavailable: {signal}')
        good=g[np.isfinite(g[variant])&g.ticker.isin(tickers)].copy()
        if len(good)<2:
            decisions.append({'signal_date':signal,'entry_date':entry,'count':len(good),'ticker1':'','ticker2':'','status':'carry_insufficient_forecasts'});continue
        top=good.sort_values([variant,'ticker'],ascending=[False,True]).head(2)
        i,j=[tickers.index(t) for t in top.ticker]
        st['d1'][0,k:]=i;st['d2'][0,k:]=j;events[k]=True
        decisions.append({'signal_date':signal,'entry_date':entry,'count':len(good),'ticker1':top.ticker.iloc[0],'ticker2':top.ticker.iloc[1], 'score1':float(top[variant].iloc[0]),'score2':float(top[variant].iloc[1]),'status':'proposed'})
    return st,events,pd.DataFrame(decisions)
