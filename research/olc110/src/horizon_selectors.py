"""Adaptive stage3: individual horizon portfolios and a single capital account."""
from __future__ import annotations
import numpy as np
from dedup_selectors import pair_corr
from cluster_selectors import CORR_LIMIT

ARMS=('HORIZON63','HORIZON126','HORIZON252','CAPITAL_3H','CAPITAL_3H_TILT',
      'HORIZON63_TOP1','HORIZON126_TOP1','HORIZON252_TOP1')
HORIZONS=(63,126,252)

def horizon_portfolio(panel,f,snapshot,k,horizon,top1=False):
    n=len(panel['names']);names=np.asarray(panel['names'])
    mask=f['liquid_eligible'][k] & (f['m252'][k]>0) & (f['m63'][k]>0) & (f['C'][k]>f['sma200'][k])
    ids=np.flatnonzero(mask)
    ranked=sorted(ids.tolist(),key=lambda j:(-float(f['m'+str(horizon)][k,j]),str(names[j])))
    selected=[];group_for={int(j):g['gid'] for g in snapshot['groups'] for j in g['members']}
    used=set();slots=1 if top1 else 3
    for j in ranked:
        if not top1:
            if group_for[j] in used:continue
            if any(pair_corr(f,k,j,old)>CORR_LIMIT+1e-12 for old in selected):continue
        selected.append(j);used.add(group_for[j])
        if len(selected)==slots:break
    w=np.zeros(n);w[selected]=1./slots
    return w,dict(horizon=horizon,slots=slots,selected_indices=selected,
                  selected_group_ids=[group_for[j] for j in selected],eligible_count=int(len(ids)))

def make_policy(panel,f,snapshots,arm):
    if arm not in ARMS:raise ValueError('ARM')
    names=np.asarray(panel['names'])
    def policy(k,current_weights):
        snap=snapshots[k]
        if arm.startswith('HORIZON'):
            horizon=int(arm.split('_')[0].replace('HORIZON',''))
            w,meta=horizon_portfolio(panel,f,snap,k,horizon,arm.endswith('_TOP1'))
            meta.update(arm=arm,selected_names=[str(names[j]) for j in meta['selected_indices']],
                        opportunity_used=False,invested_indices=np.flatnonzero(w>0).tolist())
            return w,meta
        baskets=[];sleeves=[];recent=[];acceleration=[]
        for horizon in HORIZONS:
            w,info=horizon_portfolio(panel,f,snap,k,horizon)
            baskets.append(w);sleeves.append(info)
            ids=info['selected_indices']
            b=float(np.mean(f['b21'][k,ids])) if ids else 0.
            a=float(np.mean(f['a21'][k,ids])) if ids else 0.
            recent.append(b);acceleration.append(b-a)
        alpha=np.full(3,1/3);used=False
        if arm=='CAPITAL_3H_TILT' and all(len(s['selected_indices'])==3 for s in sleeves):
            eligible=[i for i in range(3) if recent[i]>0 and acceleration[i]>0]
            if eligible:
                best=max(acceleration[i] for i in eligible)
                tied=[i for i in eligible if acceleration[i]==best]
                alpha=np.full(3,.25);alpha[tied]+=.25/len(tied)
                used=True
        target=np.asarray(baskets).T@alpha
        ids=np.flatnonzero(target>0).tolist()
        meta=dict(arm=arm,selected_indices=ids,selected_names=[str(names[j]) for j in ids],
                  invested_indices=ids,sleeve_weights=alpha.tolist(),sleeves=sleeves,
                  sleeve_recent21=recent,sleeve_acceleration21=acceleration,
                  opportunity_used=used,eligible_count=sleeves[0]['eligible_count'])
        return target,meta
    return policy
