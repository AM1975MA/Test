"""OLC16: market-balanced, context-dependent simplex weights for frozen forecasts.

The capped soft Top2 weights exist only in the training surrogate. They never
replace the actual equal-weight two-name portfolio. No target enters prediction.
"""
from __future__ import annotations
import numpy as np
from scipy.special import softmax, expit
from scipy.optimize import minimize
from scipy.stats import rankdata

PRIOR=np.array([.45,.35,.20])
FEATURES=('trend126','vol_ratio','leadership')

def capped_weights(scores, temperature=.05):
    s=np.asarray(scores,float)
    if s.ndim!=1 or len(s)<2 or not np.isfinite(s).all() or temperature<=0:
        raise ValueError('At least two finite scores and positive temperature required')
    p=softmax(s/temperature)
    j=int(np.argmax(p))
    if p[j]>.5:
        other=np.arange(len(s))!=j
        p[j]=.5;p[other]=.5*softmax(s[other]/temperature)
    return p

def _scale(groups, contextual):
    markets=np.array([g['market'] for g in groups])
    if set(markets)!={'EU','USA'}:raise ValueError('Both markets required')
    w=np.array([.5/np.count_nonzero(markets==m) for m in markets])
    if not contextual:return np.ones((len(groups),1)),{},w,markets
    X=np.array([g['x'] for g in groups],float)
    if X.shape!=(len(groups),3) or np.isinf(X).any():raise ValueError('Three finite-or-missing contexts required')
    med=np.nanmedian(X,axis=0)
    if not np.isfinite(med).all():raise ValueError('Entire context missing in training')
    X=np.where(np.isnan(X),med,X);mean=w@X;sd=np.sqrt(w@((X-mean)**2));sd=np.where(sd>1e-12,sd,1.)
    return np.column_stack([np.ones(len(X)),np.clip((X-mean)/sd,-3,3)]),dict(median=med.tolist(),mean=mean.tolist(),sd=sd.tolist()),w,markets

def setup(groups, contextual=True):
    design,scaler,qw,markets=_scale(groups,contextual)
    Ds=[];ws=[];qi=[];zs=[];us=[];nmax=max(len(g['u']) for g in groups)
    Z=np.zeros((len(groups),nmax,3));U=np.zeros((len(groups),nmax));mask=np.zeros((len(groups),nmax),bool)
    for k,g in enumerate(groups):
        z=np.asarray(g['z'],float);u=np.asarray(g['u'],float)
        if z.shape!=(len(u),3) or len(u)<2 or not np.isfinite(z).all() or not np.isfinite(u).all() or (z<0).any() or (z>1).any():
            raise ValueError('Aligned complete outcomes and scores in[0,1] required')
        i,j=np.triu_indices(len(u),1);gap=u[i]-u[j];top=rankdata(u)/len(u)>.8
        keep=(top[i]|top[j])&(gap!=0);i,j,gap=i[keep],j[keep],gap[keep]
        spread=max(float(np.subtract(*np.quantile(u,[.75,.25]))),1e-12)
        if len(gap):
            w=np.minimum(abs(gap)/spread,3.);w=w/w.sum()*qw[k]
            Ds.append(np.sign(gap)[:,None]*(z[i]-z[j]));ws.append(w);qi.append(np.full(len(w),k,int))
        Z[k,:len(u)]=z;U[k,:len(u)]=np.clip((u-np.median(u))/spread,-3,3);mask[k,:len(u)]=True
    if not Ds:raise ValueError('No informative pairs')
    cache=dict(design=design,dimension=2*design.shape[1],query_weights=qw,markets=markets,
               D=np.concatenate(Ds),w=np.concatenate(ws),query_id=np.concatenate(qi),Z=Z,U=U,mask=mask)
    return cache,scaler

def _betas(theta,design):
    A=np.asarray(theta).reshape(2,design.shape[1])
    logits=design@A.T+np.log(PRIOR[:2]/PRIOR[2])
    return softmax(np.column_stack([logits,np.zeros(len(design))]),axis=1)

def objective(theta,cache,kind,penalty=.1):
    A=np.asarray(theta,float).reshape(2,cache['design'].shape[1]);b=_betas(theta,cache['design'])
    Q=len(b)
    if kind=='pair':
        D,w,qi=cache['D'],cache['w'],cache['query_id']
        v=-5*np.einsum('ij,ij->i',D,b[qi]);loss=float(w@np.logaddexp(0,v))
        gv=-5*w*expit(v)
        gb=np.column_stack([np.bincount(qi,weights=gv*D[:,j],minlength=Q) for j in range(3)])
    elif kind=='top2':
        Z,U,mask,qw=cache['Z'],cache['U'],cache['mask'],cache['query_weights']
        s=np.einsum('qij,qj->qi',Z,b);logits=np.where(mask,s/.05,-np.inf)
        p=softmax(logits,axis=1);j=p.argmax(axis=1);cap=p[np.arange(Q),j]>.5
        w=p.copy();grad_s=np.zeros_like(p)
        if (~cap).any():
            rows=~cap;mu=(p[rows]*U[rows]).sum(axis=1)
            grad_s[rows]=-p[rows]*(U[rows]-mu[:,None])/.05
        if cap.any():
            ids=np.flatnonzero(cap);v=logits[ids].copy();v[np.arange(len(ids)),j[ids]]=-np.inf
            rest=softmax(v,axis=1);w[ids]=.5*rest;w[ids,j[ids]]=.5
            mu=(rest*U[ids]).sum(axis=1)
            grad_s[ids]=-.5*rest*(U[ids]-mu[:,None])/.05
        loss=-float(qw@np.sum(w*U,axis=1));gb=np.einsum('qi,qij->qj',grad_s*qw[:,None],Z)
    else:raise ValueError('Unknown objective')
    gl=b*(gb-np.sum(gb*b,axis=1,keepdims=True))
    grad=gl[:,:2].T@cache['design']
    loss+=.05*np.sum(A[:,0]**2)+penalty*np.sum(A[:,1:]**2)
    grad[:,0]+=.1*A[:,0];grad[:,1:]+=2*penalty*A[:,1:]
    return float(loss),grad.reshape(-1)

def fit_model(groups,contextual,kind,penalty=.1):
    if penalty<=0:raise ValueError('Positive context penalty required')
    cache,scaler=setup(groups,contextual);d=cache['design'].shape[1];starts=[];results=[]
    for offset in [(0.,0.),(.5,-.5),(-.5,.5)]:
        A=np.zeros((2,d));A[:,0]=offset
        result=minimize(lambda t:objective(t,cache,kind,penalty),A.reshape(-1),jac=True,
                        method='L-BFGS-B',bounds=[(-5,5)]*(2*d),
                        options={'maxiter':250,'ftol':1e-12,'gtol':1e-7,'maxls':40})
        starts.append(dict(offset=list(offset),success=bool(result.success),loss=float(result.fun),
                           iterations=int(result.nit),message=str(result.message),grad_norm=float(np.linalg.norm(result.jac))))
        if result.success:results.append(result)
    if not results:raise RuntimeError('No converged optimization: '+str(starts))
    best=min(results,key=lambda r:r.fun)
    return dict(theta=best.x.reshape(2,d).tolist(),scaler=scaler,contextual=bool(contextual),kind=kind,
                penalty=float(penalty),converged=True,loss=float(best.fun),starts=starts,
                training_groups={m:int(np.count_nonzero(cache['markets']==m)) for m in ['EU','USA']},
                training_pairs=int(len(cache['w'])),features=list(FEATURES) if contextual else [])

def predict_weights(model,context):
    if model['contextual']:
        x=np.asarray(context,float);sc=model['scaler']
        if x.shape!=(3,) or np.isinf(x).any():raise ValueError('Three finite-or-missing context values required')
        x=np.where(np.isnan(x),sc['median'],x)
        a=np.r_[1.,np.clip((x-np.array(sc['mean']))/np.array(sc['sd']),-3,3)]
    else:a=np.ones(1)
    return _betas(np.asarray(model['theta']).reshape(-1),a.reshape(1,-1))[0]
