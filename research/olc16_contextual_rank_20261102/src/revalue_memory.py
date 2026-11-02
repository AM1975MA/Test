"""Revalue known historical forecasts under CURRENT coefficients, at current decision.

No past order is rewritten. All arrays are predictor outputs, never future labels.
"""
import numpy as np
from parent_chrono import anchor_scale

def revalue(groups,betas):
    if len(groups)!=len(betas):raise ValueError('One current beta for each dated forecast required')
    out=[];dates=[g['date'] for g in groups]
    if any(a>=b for a,b in zip(dates,dates[1:])):raise ValueError('Strict chronological order required')
    for k,(g,beta) in enumerate(zip(groups,betas)):
        beta=np.asarray(beta,float)
        if beta.shape!=(3,) or not np.isfinite(beta).all() or (beta<0).any() or not np.isclose(beta.sum(),1):raise ValueError('Simplex required')
        mapped=[]
        for lag in range(3):
            old=groups[max(k-lag,0)]
            values=anchor_scale(old['z']@beta,old['anchor'])
            table=dict(zip(old['tickers'],values))
            mapped.append(np.array([table.get(t,np.nan) for t in g['tickers']]))
        a=np.stack(mapped);weights=np.array([.4,.3,.3])[:,None];ok=np.isfinite(a)
        den=(weights*ok).sum(0);mean=(weights*np.where(ok,a,0)).sum(0)/den
        mean=np.where(ok.all(0),.4*a[0]+.3*a[1]+.3*a[2],mean)
        out.append(np.clip(mean,0,1)**1.1)
    return out
