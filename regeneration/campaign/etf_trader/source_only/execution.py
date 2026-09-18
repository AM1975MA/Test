"""Conservative close-signal -> next-open self-financing replay.
No intraday stop fills, no opening-breadth decision filled at that same open.
Missing held prices fail closed; unlisted names cannot enter from future fills.
"""
import numpy as np
import pandas as pd

def allocations(scores, baskets, dates, cols, threshold=.12, top_weight=.75):
    lookup={t:i for i,t in enumerate(cols)}
    members=np.array([[lookup[t] for t in sorted(b)] for b in baskets])
    arr=scores.pivot(index='signal_date',columns='ticker',values='score').reindex(columns=cols)
    sched={}
    for dt,row in arr.iterrows():
        pos=dates.searchsorted(dt,side='right')
        if pos>=len(dates): continue
        # A close-derived signal may only trade strictly after its signal date.
        if not pd.Timestamp(dates[pos]) > pd.Timestamp(dt):
            raise RuntimeError(f'look-ahead/same-bar execution at {dt}')
        values=row.to_numpy()[members]
        safe=np.where(np.isfinite(values),values,-np.inf)
        order=np.argsort(-safe,axis=1,kind='stable')[:,:2]
        picks=np.take_along_axis(members,order,axis=1)
        ranks=np.take_along_axis(safe,order,axis=1)
        if not np.isfinite(ranks).all(): raise ValueError('Fewer than two eligible names')
        w=np.where(ranks[:,0]-ranks[:,1]>=threshold,1.,top_weight)
        W=np.zeros((len(baskets),len(cols)))
        W[np.arange(len(baskets)),picks[:,0]]=w
        W[np.arange(len(baskets)),picks[:,1]]=1-w
        sched[int(pos)]=W
    return sched

def allocation_table(scores, baskets, dates, cols, threshold=.12, top_weight=.75):
    """Materialize the same monthly decisions for independent replay engines."""
    lookup={t:i for i,t in enumerate(cols)}
    arr=scores.pivot(index='signal_date',columns='ticker',values='score').reindex(columns=cols)
    rows=[]
    signal_dates=list(arr.index)
    for signal_no,(dt,row) in enumerate(arr.iterrows()):
        pos=dates.searchsorted(dt,side='right')
        if signal_no+1>=len(signal_dates) or pos>=len(dates)-1: continue
        if not pd.Timestamp(dates[pos]) > pd.Timestamp(dt):
            raise RuntimeError(f'look-ahead/same-bar allocation at {dt}')
        next_signal=pd.Timestamp(signal_dates[signal_no+1])
        next_pos=dates.searchsorted(next_signal,side='right')
        if next_pos<=pos or next_pos>=len(dates): continue
        if not pd.Timestamp(dates[next_pos]) > next_signal:
            raise RuntimeError(f'look-ahead/same-bar exit allocation at {next_signal}')
        for bid,basket in enumerate(baskets):
            local=[(t,float(row[t])) for t in sorted(basket) if t in lookup and np.isfinite(row[t])]
            if len(local)<2: raise ValueError(f'Fewer than two eligible names: {dt} basket {bid}')
            local.sort(key=lambda x:(-x[1],x[0])); (t1,s1),(t2,s2)=local[:2]
            w1=1. if s1-s2>=threshold else top_weight
            rows.append({'signal_date':dt,'entry_date':dates[pos],'exit_date':dates[next_pos],
                         'basket':str(bid),'top1':t1,'top2':t2,'w1':w1,'w2':1-w1})
    return pd.DataFrame(rows)

def schedule_from_table(table,dates,cols,baskets):
    ti={t:i for i,t in enumerate(cols)};sched={}
    for entry,g in table.groupby('entry_date',sort=True):
        pos=int(dates.searchsorted(pd.Timestamp(entry),side='left'))
        W=np.zeros((len(baskets),len(cols)))
        for r in g.itertuples(index=False):
            b=int(r.basket);W[b,ti[r.top1]]=float(r.w1);W[b,ti[r.top2]]=float(r.w2)
        sched[pos]=W
    return sched

def replay(scores,mats,baskets,start='2017-02-01',end='2026-07-01',cost=.001,risk=False,threshold=.12,top_weight=.75,allocation_override=None):
    dates=mats['Open'].index; cols=list(mats['Open'].columns)
    sched=(allocations(scores,baskets,dates,cols,threshold,top_weight) if allocation_override is None
           else schedule_from_table(allocation_override,dates,cols,baskets))
    start_i=dates.searchsorted(pd.Timestamp(start)); end_i=dates.searchsorted(pd.Timestamp(end),side='right')-1
    O=mats['Open'].to_numpy(float); C=mats['Close']
    # Distress is available at the previous close. Constants fixed ex ante.
    m5=C.pct_change(5,fill_method=None); m21=C.pct_change(21,fill_method=None)
    vol=np.log(C).diff().rolling(63,min_periods=42).std()
    z5=m5/(vol*np.sqrt(5)).replace(0,np.nan)
    distress=((C<C.rolling(63).mean())&(m21<0)&(z5<-2.0)).shift(1).fillna(False).to_numpy(bool)
    breadth=((C<C.rolling(63).mean())&(m21<0)).mean(axis=1).shift(1).fillna(0).to_numpy()
    B=len(baskets); N=len(cols); units=np.zeros((B,N)); cash=np.ones(B)
    target=np.zeros((B,N)); active=np.zeros(B,dtype=bool)
    equity=[]; turnovers=[]; index=[]; lastdesired=np.zeros((B,N)); cooldown=np.zeros(B,dtype=int)
    for i in range(start_i,end_i):
        prices=O[i]; bad=~np.isfinite(prices)|(prices<=0)
        if ((units>0)&bad[None,:]).any(): raise ValueError(f'Missing held open {dates[i]}')
        p=np.where(bad,0,prices); value=cash+units@p
        if i in sched: target=sched[i].copy(); active[:]=True
        desired=target.copy()
        if risk:
            alarm=((target*distress[i]).sum(axis=1)>.5)&(breadth[i]>.55)
            cooldown=np.maximum(cooldown-1,0); cooldown[alarm]=3
            factor=np.where(cooldown>0,.25,1.)
            desired*=factor[:,None]
            for t in ['BIL','SHV']: desired[:,cols.index(t)]+=(1-factor)*.5*active
        change=np.max(np.abs(desired-lastdesired),axis=1)>1e-12
        if (desired[:,bad]>0).any(): raise ValueError(f'Missing selected open {dates[i]}')
        current=units*p[None,:]/value[:,None]
        # Exact fixed point: fees on actual traded dollars after costs.
        after=value.copy()
        for _ in range(10):
            traded=np.abs(desired*after[:,None]-units*p[None,:]).sum(axis=1)
            after=np.where(change,value-cost*traded,value)
        turnover=np.where(change,traded/value,0.)
        safe=np.where(bad,1,prices)
        units=np.where(change[:,None],desired*after[:,None]/safe[None,:],units)
        cash=np.where(change,after*(1-desired.sum(axis=1)),cash)
        nextp=O[i+1]; badnext=~np.isfinite(nextp)|(nextp<=0)
        if ((units>0)&badnext[None,:]).any(): raise ValueError(f'Missing valuation {dates[i+1]}')
        e=cash+units@np.where(badnext,0,nextp)
        if (e<=0).any(): raise ValueError('Nonpositive wealth')
        equity.append(e); turnovers.append(turnover); index.append(dates[i+1])
        lastdesired=desired
    return pd.DatetimeIndex(index),np.array(equity).T,np.array(turnovers).T
