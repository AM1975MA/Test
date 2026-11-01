"""Explicit economic outcomes and constrained, market-balanced ranking fit."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.optimize import minimize
from scipy.stats import rankdata
PRIOR=np.array([.45,.35,.20])

def utility(r):
 a=np.asarray(r,float)
 if a.ndim!=2 or a.shape[1]!=3 or not np.isfinite(a).all() or (a<=-1).any():
  raise ValueError('Three finite cumulative returns, gross positive, required')
 logs=np.log1p(a);inc=np.column_stack([logs[:,0],logs[:,1]-logs[:,0],logs[:,2]-logs[:,1]])
 w=np.exp2(-np.arange(3)/2);return inc@w/w.sum()

def horizon_labels(frame):
 ks=['signal_date','ticker'];cols=[f'target_rank_{h}' for h in (21,42,63)]
 if frame.duplicated(ks).any():raise ValueError('Duplicate label keys')
 a=frame[cols].to_numpy(float);r=frame[[f'fwd_ret_{h}' for h in (21,42,63)]].to_numpy(float)
 if not np.isfinite(a).all() or (a<0).any() or (a>1).any():raise ValueError('Invalid ranks')
 utility(r)
 z={f'C{h}':a[:,j]**1.5 for j,h in enumerate((21,42,63))}
 for j,h in [(1,42),(2,63)]:
  v=pd.Series((1+r[:,j])/(1+r[:,j-1])-1,index=frame.index)
  z[f'I{h}']=v.groupby(frame.signal_date).rank(pct=True,method='average').to_numpy()**1.5
 return z

def mature_groups(frame,cutoff):
 cutoff=pd.Timestamp(cutoff);out=[]
 for (market,date),g in frame.groupby(['market','signal_date'],sort=True):
  if date>=cutoff:continue
  valid=np.isfinite(g[['fwd_ret_21','fwd_ret_42','fwd_ret_63']].to_numpy(float)).all()
  if valid and g.exit_date_63.notna().all() and g.exit_date_63.max()<cutoff:
   out.append((market,pd.Timestamp(date)))
 return out

def score(z,beta,alpha=1):
 a=np.asarray(z,float);b=np.asarray(beta,float)
 if a.ndim!=2 or a.shape[1]!=3 or b.shape!=(3,) or not np.isfinite(a).all() or (a<0).any() or (a>1).any():raise ValueError('Finite n-by-three scores in [0,1] required')
 if not np.isfinite(b).all() or (b<0).any() or not np.isclose(b.sum(),1,atol=1e-10) or not np.isfinite(alpha) or alpha<=0:raise ValueError('Simplex weights and positive alpha required')
 return a**alpha@b

def pairs(groups,alpha):
 chunks=[];meta=[]
 for g in groups:
  z=np.asarray(g['z'],float);u=np.asarray(g['u'],float)
  score(z,PRIOR,alpha)
  if len(u)!=len(z) or not np.isfinite(u).all():raise ValueError('Aligned finite outcomes required')
  i,j=np.triu_indices(len(u),1);gap=u[i]-u[j];top=rankdata(u)/len(u)>.8
  keep=((top[i])|(top[j]))&(gap!=0);i=i[keep];j=j[keep];gap=gap[keep]
  if not len(gap):continue
  scale=float(np.subtract(*np.quantile(u,[.75,.25])))
  if scale<=0:scale=float(np.ptp(u))
  if scale<=0:continue
  w=np.minimum(abs(gap)/scale,3.);w=w/w.sum()
  D=np.sign(gap)[:,None]*(z[i]**alpha-z[j]**alpha)
  chunks.append((g['market'],D,w));meta.append({'market':g['market'],'date':str(g['date']),'pairs':len(w)})
 if set(x[0] for x in chunks)!={'EU','USA'}:raise ValueError('Both markets require informative completed groups')
 counts={m:sum(x[0]==m for x in chunks) for m in ['EU','USA']};Ds=[];ws=[]
 for (m,D,w),a in zip(chunks,meta):
  fac=.5/counts[m];Ds.append(D);ws.append(w*fac);a['total_weight']=fac
 return np.concatenate(Ds),np.concatenate(ws),meta

def objective(beta,D,w,lam):
 b=np.asarray(beta,float);a=-5*(D@b)
 loss=float(w@np.logaddexp(0,a)+lam*np.square(b-PRIOR).sum())
 grad=-5*(D.T@(w*expit(a)))+2*lam*(b-PRIOR)
 return loss,grad

def fit_beta(groups,alpha=1,lam=1):
 if lam<0:raise ValueError('Negative shrinkage')
 D,w,meta=pairs(groups,alpha)
 res=minimize(lambda b:objective(b,D,w,lam),PRIOR.copy(),jac=True,method='SLSQP',bounds=[(0,1)]*3,
  constraints=[{'type':'eq','fun':lambda b:b.sum()-1,'jac':lambda b:np.ones(3)}],options={'maxiter':200,'ftol':1e-11})
 if not res.success:raise RuntimeError('Constrained fit failed: '+res.message)
 beta=np.clip(res.x,0,1);beta/=beta.sum()
 return {'beta':beta.tolist(),'alpha':float(alpha),'lambda':float(lam),'loss':float(objective(beta,D,w,lam)[0]),'success':bool(res.success),'iterations':int(res.nit),'pairs':len(w),'groups':meta}
