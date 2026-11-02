"""Training-only block permutations, jointly aligned across the two markets.

No target participates in the map. Validation/test contexts are never passed
here by the experiment runner. Temporal dependence is only partially preserved;
this is a negative-control diagnostic, not an exact exchangeability claim.
"""
from __future__ import annotations
import hashlib
import numpy as np
import pandas as pd

def transformed(groups,seed=None,omit=None):
    if omit is not None and omit not in (0,1,2):raise ValueError('Unknown context channel')
    out=[dict(g,x=np.asarray(g['x'],float).copy()) for g in groups]
    if any(g['x'].shape!=(3,) for g in out):raise ValueError('Expected three context values')
    index={}
    for i,g in enumerate(out):
        key=(g['market'],str(pd.Timestamp(g['date']).to_period('M')))
        if key in index:raise ValueError('Duplicate market month')
        index[key]=i
    if set(m for m,_ in index)!={'EU','USA'}:raise ValueError('Both markets required')
    common=sorted(set(k for m,k in index if m=='EU')&set(k for m,k in index if m=='USA'))
    signature='|'.join(f'{m}:{d}' for m,d in sorted(index))
    digest=hashlib.sha256(signature.encode()).hexdigest()
    donor=dict(zip(common,common));order=list(range((len(common)+5)//6))
    if seed is not None and common:
        rng=np.random.default_rng(np.random.SeedSequence([int(seed),int(digest[:8],16)]))
        blocks=[common[i:i+6] for i in range(0,len(common),6)]
        order=rng.permutation(len(blocks)).tolist()
        flattened=[d for j in order for d in blocks[j]]
        donor=dict(zip(common,flattened))
    mapping=[]
    for (market,month),i in index.items():
        dmonth=donor.get(month,month);j=index[market,dmonth]
        out[i]['x']=np.asarray(groups[j]['x'],float).copy()
        if omit is not None:out[i]['x'][omit]=0.
        mapping.append({'market':market,'date':str(groups[i]['date']),
                        'donor_date':str(groups[j]['date']),'changed':i!=j})
    audit={'seed':seed,'omitted_channel':omit,'training_key_sha256':digest,
           'rows':len(groups),'common_months':len(common),'unshared':len(groups)-2*len(common),
           'changed':sum(r['changed'] for r in mapping),'block_order':order,
           'latest_donor':str(max(g['date'] for g in groups)),'mapping':mapping}
    return out,audit
