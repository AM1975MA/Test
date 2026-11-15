"""OLC109 fixed, causal exposure-group selectors; no fit or optimization.

Group statistics and liquidity use only completed observations <= signal index.
Current catalogue and vendor adjustments still have the documented source limits.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from scipy.stats import rankdata
from signals import compute_features, pick

ARMS=("PASSIVE","LEADERS","DUAL21","LIQ_LEADERS","LIQ_DUAL21",
      "CLUSTER_LEADERS","CLUSTER_DUAL21","CLUSTER_TREND","CLUSTER_SLOW",
      "CLUSTER_SLOW_RVOL","CLUSTER_SLOW_DUAL21","CLUSTER_DUAL_RESID",
      "CLUSTER_DUAL_REVERT","CLUSTER_LEADERS4","CLUSTER_DUAL4",
      "CLUSTER_DUAL_CASH","CLUSTER_DUAL_RISK15","CLUSTER_DUAL_RISK20",
      "CLUSTER_DUAL_EXIT63","CLUSTER_SLOW_EXIT63","CLUSTER_DUAL_PEERS2",
      "CLUSTER_DUAL_TRAIL15")
CORR_LIMIT=.85
MIN_MEDIAN_TURNOVER=100000.


def prepare_features(panel, legacy, turnover):
    f=compute_features(panel,legacy)
    c=pd.DataFrame(f['C'])
    t=np.asarray(turnover,float)
    if t.shape!=c.shape or not np.isfinite(t).all() or (t<0).any():
        raise ValueError('TURNOVER')
    # Include zero/missing sessions in the median. A liquid present-day fund
    # cannot retroactively be liquid before its own observed history.
    t=np.where(np.asarray(panel['observed'],bool),t,0.)
    adv=pd.DataFrame(t).rolling(63,min_periods=63).median().to_numpy()
    m63=np.log(c/c.shift(63)).to_numpy()
    m126=np.log(c/c.shift(126)).to_numpy()
    slow=.5*((m126-f['m21'])*252/105+(f['m252']-f['m21'])*252/231)
    liquid=f['eligible'] & np.asarray(panel['observed'],bool) & (adv>=MIN_MEDIAN_TURNOVER)
    f.update(adv63=adv,m63=m63,m126=m126,slow=slow,
             sma200=c.rolling(200,min_periods=200).mean().to_numpy(),
             peak63=c.rolling(63,min_periods=63).max().to_numpy(),liquid_eligible=liquid)
    lf=f.copy()
    rb=pd.DataFrame(np.where(liquid,f['b21'],np.nan)).rank(axis=1,pct=True,method='average').to_numpy()
    ra=pd.DataFrame(np.where(liquid,f['a21'],np.nan)).rank(axis=1,pct=True,method='average').to_numpy()
    fast=liquid & (f['b21']>0) & (rb>=2/3) & (f['C']>f['sma63'])
    lf.update(eligible=liquid,rank_b21=rb,rank_a21=ra,fast_eligible21=fast,
              emerging_eligible21=fast & (ra<2/3) & (f['acceleration21']>0))
    f['liquid_features']=lf
    return f


def _correlation(x):
    x=np.asarray(x,float)
    if x.ndim!=2 or not np.isfinite(x).all():raise ValueError('CORRELATION_INPUT')
    z=x-x.mean(axis=0)
    norm=np.sqrt(np.sum(z*z,axis=0))
    z=np.divide(z,norm[None,:],out=np.zeros_like(z),where=norm[None,:]>1e-14)
    out=np.clip(z.T@z,-1.,1.)
    # A constant-return instrument is not assumed correlated with every asset.
    np.fill_diagonal(out,1.)
    return out


def build_snapshot(panel,f,k):
    names=np.asarray(panel['names'])
    ids=np.flatnonzero(f['liquid_eligible'][k])
    if len(ids)==0:
        return dict(k=int(k),groups=[],rep_corr=np.zeros((0,0)),eligible_count=0)
    rr=f['returns'][k-125:k+1,ids]
    if rr.shape[0]!=126:raise ValueError('CLUSTER_WARMUP')
    corr=_correlation(rr)
    if len(ids)==1:labels=np.ones(1,dtype=int)
    else:
        distance=np.maximum(0.,1-corr)
        distance=(distance+distance.T)/2
        np.fill_diagonal(distance,0.)
        tree=linkage(squareform(distance,checks=False),method='complete',optimal_ordering=False)
        labels=fcluster(tree,t=1-CORR_LIMIT,criterion='distance')
    groups=[]
    for label in np.unique(labels):
        members=ids[labels==label]
        rep=sorted(members.tolist(),key=lambda j:(-float(f['adv63'][k,j]),str(names[j])))[0]
        med=lambda key:float(np.median(f[key][k,members]))
        g=dict(gid=min(str(names[j]) for j in members),members=list(map(int,members)),
               representative=int(rep),size=int(len(members)),annual=med('m252'),
               m63=med('m63'),slow=med('slow'),b21=med('b21'),a21=med('a21'),
               accel21=med('acceleration21'),vol63=med('vol'),
               above63=bool(f['C'][k,rep]>f['sma63'][k,rep]),
               above200=bool(f['C'][k,rep]>f['sma200'][k,rep]),
               median_turnover=float(f['adv63'][k,rep]))
        g['trend']=bool(g['annual']>0 and g['m63']>0 and g['above200'])
        g['slow_rvol']=g['slow']/max(g['vol63'],.05)
        groups.append(g)
    groups.sort(key=lambda g:g['gid'])
    loc={int(j):i for i,j in enumerate(ids)}
    rid=[loc[g['representative']] for g in groups]
    return dict(k=int(k),groups=groups,rep_corr=corr[np.ix_(rid,rid)].copy(),eligible_count=int(len(ids)))


def _choose(snapshot,arm):
    groups=snapshot['groups']; corr=snapshot['rep_corr']; n=len(groups)
    count=4 if arm in ('CLUSTER_LEADERS4','CLUSTER_DUAL4') else 2
    pool=list(range(n))
    if arm=='CLUSTER_DUAL_PEERS2':pool=[i for i in pool if groups[i]['size']>=2]
    is_slow='SLOW' in arm
    if is_slow or arm=='CLUSTER_TREND':pool=[i for i in pool if groups[i]['trend']]
    score='slow_rvol' if arm=='CLUSTER_SLOW_RVOL' else ('slow' if is_slow else 'annual')
    ranked=sorted(pool,key=lambda i:(-groups[i][score],groups[i]['gid']))
    compatible=lambda i,chosen:all(corr[i,j]<=CORR_LIMIT+1e-12 for j in chosen)
    leaders=[]
    for i in ranked:
        if compatible(i,leaders):leaders.append(i)
        if len(leaders)==count:break
    selected=leaders.copy();challenger=None;used=False;emerging=[]
    is_dual='DUAL' in arm
    if is_dual and pool:
        rb=rankdata([groups[i]['b21'] for i in pool],method='average')/len(pool)
        ra=rankdata([groups[i]['a21'] for i in pool],method='average')/len(pool)
        emerging=[i for pos,i in enumerate(pool) if i not in leaders and groups[i]['b21']>0
                  and rb[pos]>=2/3 and ra[pos]<2/3 and groups[i]['accel21']>0 and groups[i]['above63']]
        emerging.sort(key=lambda i:(-groups[i]['accel21'],groups[i]['gid']))
        if len(leaders)==count:
            candidates=[i for i in emerging if compatible(i,leaders[:-1])]
            if candidates:
                challenger=candidates[0]
                if groups[challenger]['b21']>groups[leaders[-1]]['b21']:
                    selected[-1]=challenger;used=True
    return selected,dict(leader_group_ids=[groups[i]['gid'] for i in leaders],
                         selected_group_ids=[groups[i]['gid'] for i in selected],
                         opportunity_used=used,challenger_available=bool(emerging),
                         challenger_group_id=(groups[challenger]['gid'] if challenger is not None else None),
                         eligible_groups=len(pool),all_groups=n,slots=count)


def _residual_vol(panel,f,k,ids):
    b=int(panel['benchmark']); rr=f['returns'][max(0,k-125):k+1]
    out=[]
    for j in ids:
        mask=np.isfinite(rr[:,b])&np.isfinite(rr[:,j])
        x,y=rr[mask,b],rr[mask,j]
        if len(x)<100:
            out.append(max(float(f['vol'][k,j]),.05));continue
        x=x-x.mean(); y=y-y.mean()
        beta=float(x@y/(x@x)) if x@x>1e-16 else 0.
        residual=y-beta*x
        out.append(max(float(residual.std(ddof=1)*np.sqrt(252)),.05))
    return np.array(out)


def guard_condition(f,k,kind):
    if kind=='EXIT63':return (f['C'][k]<f['sma63'][k])&(f['m21'][k]<0)
    if kind=='TRAIL15':return f['C'][k]/f['peak63'][k]-1<=-.15
    raise ValueError('GUARD_KIND')


def make_guard(f,kind):
    def guard(k,current_weights):
        active=(np.asarray(current_weights)>1e-10)&guard_condition(f,k,kind)
        if not active.any():return None
        w=np.array(current_weights,copy=True);w[active]=0.
        return w,dict(guard=kind,exited_indices=np.flatnonzero(active).tolist())
    return guard


def make_policy(panel,f,snapshots,arm):
    if arm not in ARMS:raise ValueError('UNKNOWN_ARM')
    names=np.asarray(panel['names']);n=len(names)
    if arm in ('PASSIVE','LEADERS','DUAL21','LIQ_LEADERS','LIQ_DUAL21'):
        source=f['liquid_features'] if arm.startswith('LIQ_') else f
        mapped='DUAL_SELECTIVE_21' if 'DUAL21' in arm else arm.replace('LIQ_','')
        def legacy_policy(k,current_weights):
            w,m=pick(panel,source,k,mapped,current_weights);m['arm']=arm
            return w,m
        return legacy_policy
    def policy(k,current_weights):
        snap=snapshots[k]
        selected,meta=_choose(snap,arm)
        groups=snap['groups'];ids=[groups[i]['representative'] for i in selected]
        w=np.zeros(n);w[ids]=1./meta['slots']
        if len(ids)==2 and arm=='CLUSTER_DUAL_RESID':
            rv=_residual_vol(panel,f,k,ids);inv=1/rv
            first=float(np.clip(inv[0]/inv.sum(),.25,.75))
            w[ids]=[first,1-first];meta['residual_vol']=rv.tolist()
        elif len(ids)==2 and arm=='CLUSTER_DUAL_REVERT':
            a,b=f['m21'][k,ids]
            w[ids]=[.65,.35] if a<b else ([.35,.65] if a>b else [.5,.5])
        if arm=='CLUSTER_DUAL_CASH':
            w[(f['C'][k]<=f['sma200'][k])|(f['m63'][k]<=0)]=0.
        elif arm.endswith('EXIT63'):w[guard_condition(f,k,'EXIT63')]=0.
        elif arm.endswith('TRAIL15'):w[guard_condition(f,k,'TRAIL15')]=0.
        meta.update(arm=arm,eligible_count=int(snap['eligible_count']),
                    selected_indices=ids,selected_names=[str(names[j]) for j in ids],
                    invested_indices=np.flatnonzero(w>0).tolist(),
                    selected_group_sizes=[groups[i]['size'] for i in selected],
                    selected_median_turnover=[groups[i]['median_turnover'] for i in selected])
        return w,meta
    return policy
