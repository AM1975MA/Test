"""Exact cash-PnL to log-return attribution, independently derived from stored units.
Components are accounting contributions conditional on each realized stateful path.
They are not a unique causal decomposition of the market mechanism.
"""
import numpy as np

NAMES=['old_only','new_only','shared','other_primary','defensive','stop_effect','rebalance_fees','stop_fees','stop_slippage']

def proposal_categories(q):
    D,N=q['O'].shape;cats=np.full((D-1,N),3,dtype=np.int8)
    last=None;old=np.zeros(N,bool)
    for k in range(D-1):
        p=np.zeros(N);i,j=int(q['d1'][0,k]),int(q['d2'][0,k]);w=float(q['weights'][0,k]);w=1 if i==j else w
        if i>=0:p[i]+=w
        if j>=0:p[j]+=1-w
        if last is None or np.max(abs(p-last))>1e-12:
            old=np.zeros(N,bool) if last is None else last>0
            last=p.copy()
        now=p>0
        cats[k,old&~now]=0;cats[k,now&~old]=1;cats[k,now&old]=2
    return cats

def decompose(q,res):
    O=np.asarray(q['O'],float);U=res['primary_units'];DU=res['defensive_units'];L=res['ledger'];K=len(O)-1
    before=np.zeros_like(U[:-1]);before[1:]=U[:-2]
    reb=L[:-1,3].astype(bool)
    before[reb]=res['targets'][:-1][reb]*L[:-1,1][reb,None]*(L[:-1,0]-L[:-1,5])[reb,None]/O[:-1][reb]
    primary=before*(O[1:]-O[:-1]);cat=proposal_categories(q)
    cash=np.zeros((K,len(NAMES)))
    for j in range(4):cash[:,j]=np.where(cat==j,primary,0).sum(1)
    cash[:,4]=(DU[:-1]*(O[1:]-O[:-1])).sum(1)
    stop=(before>0)&(U[:-1]==0)
    if not np.array_equal(stop.sum(1),L[:-1,8].astype(int)):
        raise AssertionError('Pre/post units disagree with recorded stop count')
    sp=q['PC'][:-1]*(1-.055)
    rawfill=np.where(O[:-1]<=sp,O[:-1],sp)
    cash[:,5]=np.where(stop,before*(rawfill-O[1:]),0.).sum(1)
    cash[:,6:9]=-L[:-1,5:8]
    pnl=res['nav'][:-1]-L[:-1,0]
    if np.max(abs(cash.sum(1)-pnl))>1e-10:raise AssertionError('Cash contribution identity failed')
    r=pnl/L[:-1,0];log=np.log1p(r)
    factor=np.divide(log,r,out=np.ones_like(r),where=np.abs(r)>1e-14)
    logs=cash/L[:-1,0,None]*factor[:,None]
    if not np.allclose(logs.sum(1),log,atol=1e-12,rtol=0):raise AssertionError('Log contribution identity failed')
    return dict(names=NAMES.copy(),log_components=logs,log_return=log,cash_components=cash,
                before_units=before,categories=cat,primary_cash_pnl=primary,
                primary_log_contribution=primary/L[:-1,0,None]*factor[:,None],stop_mask=stop)
