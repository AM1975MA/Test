from core23 import *
from core23 import signals as original_signals
RULES=['BASE','TRAIL_CASH','RAMP','TRAIL_CONFIRM','TRAIL_HALF','TRAIL_FAST','TRAIL_PROFIT','TRAIL_WIDE','RAMP_GATED','CONFIRM_RAMP','HALF_RAMP','PROFIT_RAMP']

def signals(q,m):
    old,recovery,reviews,_=original_signals(q,m)
    raw=old['BASE'];D,N=raw.shape
    c=pd.DataFrame(q['C']).where(q.get('low_observed',np.ones_like(q['C'],bool)))
    prev=c.shift(1).to_numpy();valid=np.isfinite(prev)
    r5=(c/c.shift(5)-1).shift(1).to_numpy();r21=(c/c.shift(21)-1).shift(1).to_numpy()
    ema10=c.ewm(span=10,min_periods=10,adjust=False).mean().shift(1).to_numpy()
    vol=np.log(c).diff().rolling(21,min_periods=18).std().shift(1).to_numpy()
    high10=c.shift(2).rolling(10,min_periods=10).max().to_numpy()
    fast=pd.DataFrame((prev>ema10)&(r5>0)&valid).rolling(2,min_periods=2).sum().eq(2).to_numpy()
    cash=np.array(['CASH_' in t for t in q['tickers']]);cashid=np.flatnonzero(cash)[0]
    targets={r:old[r] for r in ['BASE','TRAIL_CASH','RAMP']}
    targets['TRAIL_HALF']=.5*raw+.5*old['TRAIL_CASH']
    targetnames=['TRAIL_CONFIRM','TRAIL_FAST','TRAIL_PROFIT','TRAIL_WIDE']
    for r in targetnames:targets[r]=np.zeros_like(raw)
    blocked={r:np.zeros(N,bool) for r in targetnames};peaks={r:np.zeros(N) for r in targetnames}
    entries={r:np.zeros(N) for r in targetnames};counts=np.zeros(N,int)
    last={r:np.zeros(N) for r in targetnames};old_present=np.zeros(N,bool);gate=np.zeros(D,bool);audit=[]
    for k in range(D):
        p=raw[k];present=(p>0)&~cash;fresh=present&~old_present;active=present&valid[k]
        ids=np.flatnonzero(p>0);good_input=len(ids)>0 and np.isfinite(r5[k,ids]).all()
        gate[k]=bool(recovery[k] and good_input and p[ids]@r5[k,ids]>0)
        for name in targetnames:
            peak=peaks[name];entry=entries[name];stop=blocked[name]
            peak[~present]=0.;entry[~present]=0.;stop[~present]=False
            peak[fresh]=np.where(valid[k,fresh],prev[k,fresh],0.);entry[fresh]=peak[fresh];stop[fresh]=False
            peak[active]=np.maximum(peak[active],prev[k,active])
            band=np.clip(2*vol[k]*np.sqrt(21 if name=='TRAIL_WIDE' else 5),.08,.35 if name=='TRAIL_WIDE' else .18)
            hit=active&~stop&(prev[k]<peak*(1-band))
            rebound=active&stop&((fast[k]) if name=='TRAIL_FAST' else ((prev[k]>high10[k])&(r5[k]>0)))
            if name=='TRAIL_CONFIRM':
                breach=active&~stop&(prev[k]<peak*(1-band))&(r21[k]<0)
                counts[fresh|~present]=0;counts=np.where(breach,counts+1,0)
                hit=breach&(counts>=2)
            if name=='TRAIL_PROFIT':hit&=(entry>0)&(peak>=entry*(1+band))
            stop[hit]=True;stop[rebound]=False;peak[rebound]=prev[k,rebound];entry[rebound]=prev[k,rebound]
            if reviews[k]:
                moved=p*stop;last[name]=p-moved;last[name][cashid]+=moved.sum()
            targets[name][k]=last[name]
        old_present=present.copy()
        if reviews[k]:
            audit.append(dict(index=k,date=str(pd.Timestamp(q['dates'][k]).date()),signal_date=str(pd.Timestamp(q['dates'][k-1]).date()) if k else '',ramp_gate=bool(gate[k]),**{r+'_cash':float(targets[r][k,cash].sum()) for r in targetnames+['TRAIL_HALF']}))
    targets['RAMP_GATED']=raw;targets['CONFIRM_RAMP']=targets['TRAIL_CONFIRM'];targets['HALF_RAMP']=targets['TRAIL_HALF'];targets['PROFIT_RAMP']=targets['TRAIL_PROFIT']
    for name,t in targets.items():assert (t>=-1e-12).all() and np.allclose(t.sum(1),raw.sum(1),atol=1e-12),name
    return targets,gate,reviews,pd.DataFrame(audit)
