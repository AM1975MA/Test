"""Declared adaptive stage2: preserve individual rank, constrain correlation."""
from __future__ import annotations
import numpy as np
from scipy.stats import rankdata
from cluster_selectors import make_policy as group_policy,guard_condition,CORR_LIMIT

ARMS=('DEDUP_LEADERS','DEDUP_DUAL21','DEDUP_DUAL_PEERS2','DEDUP_DUAL_TREND_OPP',
      'DEDUP_DUAL_RISK15','DEDUP_DUAL_RISK20','DEDUP_DUAL_EXIT63','DEDUP_DUAL_TRAIL15',
      'CLUSTER_PEERS2_RISK15','CLUSTER_PEERS2_RISK20')

def pair_corr(f,k,a,b):
    x=f['returns'][k-125:k+1,[a,b]]
    if x.shape[0]!=126 or not np.isfinite(x).all():raise ValueError('CORRELATION_WINDOW')
    x=x-x.mean(axis=0);den=np.sqrt(np.sum(x*x,axis=0)).prod()
    return float(x[:,0]@x[:,1]/den) if den>1e-14 else 0.

def make_policy(panel,f,snapshots,arm):
    if arm not in ARMS:raise ValueError('ARM')
    names=np.asarray(panel['names']);n=len(names)
    if arm.startswith('CLUSTER_PEERS2_'):
        base=group_policy(panel,f,snapshots,'CLUSTER_DUAL_PEERS2')
        def delegate(k,current):
            w,m=base(k,current);m['arm']=arm;return w,m
        return delegate
    def policy(k,current):
        mask=f['liquid_eligible'][k].copy()
        if arm=='DEDUP_DUAL_PEERS2':
            peers=np.zeros(n,bool)
            for g in snapshots[k]['groups']:
                if g['size']>=2:peers[g['members']]=True
            mask &= peers
        ids=np.flatnonzero(mask)
        ranked=sorted(ids.tolist(),key=lambda j:(-float(f['m252'][k,j]),str(names[j])))
        leaders=[]
        for j in ranked:
            if not leaders or pair_corr(f,k,j,leaders[0])<=CORR_LIMIT+1e-12:leaders.append(j)
            if len(leaders)==2:break
        selected=leaders.copy();used=False;challenger=None;emerging=[]
        if len(ids) and arm!='DEDUP_LEADERS':
            rb=rankdata(f['b21'][k,ids],method='average')/len(ids)
            ra=rankdata(f['a21'][k,ids],method='average')/len(ids)
            for pos,j in enumerate(ids):
                if j in leaders:continue
                if not(f['b21'][k,j]>0 and rb[pos]>=2/3 and ra[pos]<2/3
                       and f['acceleration21'][k,j]>0 and f['C'][k,j]>f['sma63'][k,j]):continue
                if arm=='DEDUP_DUAL_TREND_OPP' and not(f['m252'][k,j]>0 and f['m63'][k,j]>0
                                                       and f['C'][k,j]>f['sma200'][k,j]):continue
                emerging.append(int(j))
            emerging.sort(key=lambda j:(-float(f['acceleration21'][k,j]),str(names[j])))
            if len(leaders)==2:
                compatible=[j for j in emerging if pair_corr(f,k,j,leaders[0])<=CORR_LIMIT+1e-12]
                if compatible:
                    challenger=compatible[0]
                    if f['b21'][k,challenger]>f['b21'][k,leaders[1]]:
                        selected[1]=challenger;used=True
        w=np.zeros(n);w[selected]=.5
        if arm.endswith('EXIT63'):w[guard_condition(f,k,'EXIT63')]=0.
        elif arm.endswith('TRAIL15'):w[guard_condition(f,k,'TRAIL15')]=0.
        meta=dict(arm=arm,leader_indices=leaders,selected_indices=selected,
                  selected_names=[str(names[j]) for j in selected],
                  invested_indices=np.flatnonzero(w>0).tolist(),
                  opportunity_used=used,challenger_available=bool(emerging),
                  challenger=challenger,eligible_count=int(len(ids)),
                  selected_pair_correlation=pair_corr(f,k,*selected) if len(selected)==2 else None)
        return w,meta
    return policy
