import numpy as np

def returns(e):return np.diff(np.log(np.column_stack([np.ones(len(e)),e])),axis=1)

def metrics(e,turn=None):
    l=returns(e);r=np.expm1(l);n=e.shape[1]
    cagr=np.expm1(l.sum(axis=1)*252/n)
    peaks=np.maximum.accumulate(np.column_stack([np.ones(len(e)),e]),axis=1)[:,1:]
    dd=(e/peaks-1).min(axis=1)
    sd=r.std(axis=1,ddof=1); sharpe=np.divide(r.mean(axis=1)*np.sqrt(252),sd,out=np.zeros_like(sd),where=sd>0)
    agg=e.mean(axis=0); aggr=np.diff(np.r_[1.,agg])/np.r_[1.,agg[:-1]]
    return {'mean_cagr':float(cagr.mean()),'median_cagr':float(np.median(cagr)),
        'p10_cagr':float(np.quantile(cagr,.1)),'mean_maxdd':float(dd.mean()),'worst_maxdd':float(dd.min()),
        'mean_sharpe_rf0':float(sharpe.mean()),'aggregate_cagr':float(agg[-1]**(252/n)-1),
        'aggregate_maxdd':float(np.min(agg/np.maximum.accumulate(np.r_[1.,agg])[1:]-1)),
        'mean_annualized_gross_turnover':None if turn is None else float(turn.sum(axis=1).mean()*252/n)}

def paired_bootstrap(base,other,block=21,reps=2000,seed=20260917):
    # Aggregate cross-basket log differences before resampling shared dates.
    delta=(returns(other)-returns(base)).mean(axis=0);n=len(delta)
    rng=np.random.default_rng(seed); means=np.empty(reps);mu=delta.mean()
    for i in range(reps):
        starts=rng.integers(0,n,size=int(np.ceil(n/block)))
        ix=((starts[:,None]+np.arange(block))%n).ravel()[:n]
        means[i]=delta[ix].mean()
    null=means-mu
    return {'annual_log_uplift':float(252*mu),'ci95_annual_log':list(252*np.quantile(means,[.025,.975])),
            'p_one_sided_centered':float((1+np.sum(null>=mu))/(reps+1)),'block':block,'reps':reps,
            'unit':'shared trading-date blocks; all baskets kept dependent'}

def holm(p):
    names=sorted(p,key=p.get);last=0.;out={}
    for i,n in enumerate(names):last=max(last,min(1.,p[n]*(len(names)-i)));out[n]=last
    return out

def subpath(e,mask):
    l=returns(e)[:,mask];return np.exp(np.cumsum(l,axis=1))
