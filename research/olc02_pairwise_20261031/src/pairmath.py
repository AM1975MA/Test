"""Pure direct-action arithmetic; no market data or future-dependent selection."""
import numpy as np
import pandas as pd

def log_advantage(shares, new_weights, entry, exit):
    q=np.asarray(shares,float); w=np.asarray(new_weights,float)
    p=np.asarray(entry,float); f=np.asarray(exit,float)
    if not (q.shape==w.shape==p.shape==f.shape): raise ValueError('Shape mismatch')
    if (q<0).any() or (w<0).any() or not np.isclose(w.sum(),1): raise ValueError('Invalid allocation')
    active=(q>0)|(w>0)
    if not np.isfinite(p[active]).all() or not np.isfinite(f[active]).all() or (p[active]<=0).any() or (f[active]<=0).any():return np.nan
    old=q>0; new=w>0
    start=np.dot(q[old],p[old])
    if start<=0:return np.nan
    hold=np.dot(q[old],f[old])/start
    proposed=np.dot(w[new],f[new]/p[new])
    return float(np.log(proposed)-np.log(hold))

def mature_mask(signal_dates, exits, targets, cutoff):
    return np.asarray((pd.DatetimeIndex(signal_dates)<pd.Timestamp(cutoff))&(pd.DatetimeIndex(exits)<pd.Timestamp(cutoff))&np.isfinite(np.asarray(targets,float)))

def monthly_weights(dates):
    s=pd.Series(pd.DatetimeIndex(dates))
    return (1/s.groupby(s).transform('size')).to_numpy(float)

def cost_log(old,new,fee):
    if fee<0:raise ValueError('Negative fee')
    tv=.5*np.abs(np.asarray(new,float)-np.asarray(old,float)).sum()
    charge=fee*tv
    if charge>=1:raise ValueError('Invalid fee burden')
    return float(-np.log1p(-charge))

def candidate_pairs(old_ids,cl01,ranked,single=False,training=False):
    old=list(dict.fromkeys(int(i) for i in old_ids)); base=list(dict.fromkeys(int(i) for i in cl01))
    if len(old)!=2 or len(base)!=2:return []
    result=[]; seen={tuple(sorted(old))}
    def add(p):
        p=tuple(map(int,p));key=tuple(sorted(p))
        if len(set(p))==2 and key not in seen:
            result.append(p);seen.add(key)
    add(base)
    if single or training:
        new=list(ranked)[:5] if training else base
        for slot in range(2):
            for j in new:
                p=old.copy();p[slot]=int(j);add(p)
    return result

def best_action(predicted,costs):
    a=np.asarray(predicted,float)-np.asarray(costs,float)
    a=np.where(np.isfinite(a),a,-np.inf)
    if not len(a) or a.max()<=0:return -1
    return int(np.argmax(a))
