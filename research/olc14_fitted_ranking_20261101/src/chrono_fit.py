"""Chronological nested fitting; all coefficients are shared by both universes."""
from __future__ import annotations
import numpy as np,pandas as pd
from ranking_core import PRIOR,score,fit_beta
from layer_metrics import topk_weights
from scipy.stats import rankdata
ALPHAS=(1.,1.5,2.)
LAMBDAS=(.01,.1,1.)

def anchor_scale(raw,anchor):
 x=np.asarray(raw,float);a=np.asarray(anchor,float)
 if x.ndim!=1 or x.shape!=a.shape or not len(x) or not np.isfinite(x).all() or not np.isfinite(a).all():raise ValueError('Aligned finite score vectors required')
 order=np.argsort(x,kind='stable');v=np.sort(a);out=np.empty_like(x);s=0
 while s<len(x):
  e=s+1
  while e<len(x) and x[order[e]]==x[order[s]]:e+=1
  out[order[s:e]]=v[s:e].mean();s=e
 # Duplicate anchor quantiles may collapse distinct raw ranks. Use only raw ordinal
 # information to preserve strict ordering, perturbing scale by at most1e-12.
 if len(np.unique(out))<len(np.unique(x)):
  out=(1-1e-12)*out+1e-12*rankdata(x,method="average")/len(x)
 if not np.array_equal(rankdata(out),rankdata(x)):
  raise RuntimeError("Score-scale mapping altered ranks")
 return out

def eligible(groups,cutoff):
 c=pd.Timestamp(cutoff)
 return [g for g in groups if g['date']<c and pd.notna(g['available']) and g['available']<c]

def counts(groups):return {m:sum(g['market']==m for g in groups) for m in ('EU','USA')}

def inner_folds(groups,outer):
 outer=pd.Timestamp(outer);past=eligible(groups,outer);folds=[]
 for year in sorted(set(g['date'].year for g in past)):
  c=pd.Timestamp(year,1,1);tr=eligible(past,c);va=[g for g in past if g['date'].year==year]
  if min(counts(tr).values())>=8 and min(counts(va).values())>=4:
   folds.append(dict(year=year,cutoff=c,train=tr,valid=va))
 return folds[-2:]

def balanced_value(groups,scores):
 if len(groups)!=len(scores):raise ValueError('Aligned query predictions required')
 vals={m:[] for m in ('EU','USA')}
 for g,s in zip(groups,scores):
  u=np.asarray(g['u'],float);vals[g['market']].append(float(topk_weights(s)@u-u.mean()))
 if any(not v for v in vals.values()):raise ValueError('Both markets required')
 means={m:float(np.mean(v)) for m,v in vals.items()}
 return dict(**means,criterion=.5*(means['EU']+means['USA'])-.25*abs(means['EU']-means['USA']))

def _learning_groups(groups,representation):
 return [dict(market=g['market'],date=g['date'],z=g[representation],u=g['u']) for g in groups]

def fit_year(groups,outer,representation):
 if representation not in ('CUM','INC'):raise ValueError('Unknown representation')
 outer=pd.Timestamp(outer);past=eligible(groups,outer);folds=inner_folds(groups,outer);trace=[]
 if min(counts(past).values())<8:
  return dict(beta=PRIOR.tolist(),alpha=1.,**{'lambda':1.},fallback=True,cutoff=str(outer),cv=[],inner_fits=0,training_groups=counts(past))
 best=None
 for alpha in ALPHAS:
  for lam in LAMBDAS:
   vs=[];gs=[];fitted=[]
   for fold in folds:
    p=fit_beta(_learning_groups(fold['train'],representation),alpha,lam)
    vs.extend(score(g[representation],p['beta'],alpha) for g in fold['valid']);gs.extend(fold['valid'])
    fitted.append(dict(year=fold['year'],beta=p['beta'],train_groups=counts(fold['train']),validation_groups=counts(fold['valid']),max_training_exit=str(max(g['available'] for g in fold['train'])),max_validation_exit=str(max(g['available'] for g in fold['valid']))))
   if gs:
    value=balanced_value(gs,vs);trace.append(dict(alpha=alpha,**{'lambda':lam},**value,folds=fitted))
    key=(value['criterion'],lam,-abs(alpha-1))
    if best is None or key>best[0]:best=(key,alpha,lam)
 alpha,lam=(best[1],best[2]) if best else (1.,1.)
 out=fit_beta(_learning_groups(past,representation),alpha,lam)
 out.update(cutoff=str(outer),representation=representation,cv=trace,inner_fits=len(trace)*len(folds),fallback=False,training_groups=counts(past),max_training_exit=str(max(g['available'] for g in past)))
 out['in_sample_value']=balanced_value(past,[score(g[representation],out['beta'],alpha) for g in past])
 return out

def choose_target(groups,outer,names):
 folds=inner_folds(groups,outer);past=eligible(groups,outer);valid=[g for f in folds for g in f['valid']]
 rows=[]
 for name in names:
  value=balanced_value(valid,[g['targets'][name] for g in valid]) if valid else dict(EU=0.,USA=0.,criterion=0.)
  rows.append(dict(target=name,**value))
 best=max(rows,key=lambda x:(x['criterion'],-names.index(x['target'])))
 return dict(target=best['target'],cutoff=str(pd.Timestamp(outer)),validation=rows,validation_groups=counts(valid),max_validation_exit=str(max(g['available'] for g in valid)) if valid else None,fallback=not bool(valid))
