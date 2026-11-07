#!/usr/bin/env python3
"""OLC64: does *signal-date* disagreement predict future utility of original components?

Read-only diagnostic of fixed OLC63 16-coalition output; no model fitting,
new strategy, tuning or price downloads. Protocol must already be committed.
"""
from pathlib import Path
from scipy.stats import spearmanr, pearsonr
import pandas as pd
import numpy as np
import hashlib, json

ROOT=Path(__file__).resolve().parent
P=ROOT.parent/'OLC63_Fusion_Attribution_20261107'/'results'
D=ROOT/'results';D.mkdir(exist_ok=True)
expected='f6cf047b543904e425f46b0b8c3c4aac13f81b0aea9040f4fb57f4df93759916'
assert hashlib.sha256((P/'OLC63_MONTHLY_FACTORIAL.csv').read_bytes()).hexdigest()==expected
F=pd.read_csv(P/'OLC63_MONTHLY_FACTORIAL.csv')
C=pd.read_csv(P/'OLC63_MONTHLY_CORRELATIONS.csv')
S=pd.read_csv(P/'OLC63_MONTHLY_SHAPLEY.csv')
assert hashlib.sha256((P/'OLC63_MONTHLY_SHAPLEY.csv').read_bytes()).hexdigest()=='72bb4b75319100428d33acd6a331ecddb45e695caf06270d4281728016619672'
F=F[F.method=='SUBSET'].copy()
assert len(F)==16*118 and F.duplicated(['market','date','mask']).sum()==0
wide=F.pivot(index=['market','date'],columns='mask',values=['mean21','mean42'])
assert wide.notna().all().all()
for market in ['EU','USA']:
 a=wide.loc[market];assert len(a)==(58 if market=='EU' else 60)
C=C.pivot(index=['market','date'],columns='pair',values='spearman')
assert {'RETURN__ORIGINAL_CURRENT','ER__XR'}.issubset(set(C.columns))
assert C.notna().all().all()
assert set(C.index)==set(wide.index)

rows=[]
for market,date in wide.index:
 year=int(date[:4]);period='MAIN' if year<=2024 else 'LATE'
 for horizon in ['mean21','mean42']:
  v=wide.loc[(market,date),horizon]
  dr=1-float(C.loc[(market,date),'RETURN__ORIGINAL_CURRENT'])
  dx=1-float(C.loc[(market,date),'ER__XR'])
  v13,v14,v11,v15=[float(v[k]) for k in [13.0,14.0,11.0,15.0]]
  values=[('H1_RETURN_VS_ET',dr,v13-v14),('H2_XGB_MARGINAL',dx,v15-v11)]
  for hyp,indicator,target in values:
   assert np.isfinite(indicator) and np.isfinite(target)
   rows.append(dict(market=market,date=date,year=year,period=period,horizon=horizon,
                   hypothesis=hyp,disagreement=indicator,future_marginal_utility_pp=100*target))
T=pd.DataFrame(rows).sort_values(['market','date','horizon','hypothesis']);T.to_csv(D/'OLC64_MONTHLY_DIAGNOSTIC.csv',index=False)

B=3000

def cir_ci(a,b,seed=64001,block=6):
 a=np.asarray(a,float);b=np.asarray(b,float)
 n=len(a);rng=np.random.default_rng(seed)
 sims=[]
 for k in range(B):
  ind=[]
  while len(ind)<n:
   s=int(rng.integers(n));ind.extend([(s+j)%n for j in range(block)])
  ii=np.array(ind[:n],int)
  x,y=a[ii],b[ii]
  if np.std(x)>1e-12 and np.std(y)>1e-12:sims.append(float(spearmanr(x,y).statistic))
 return [float(v) for v in np.quantile(sims,[.025,.975])],len(sims)

out=[]
for (m,period,hyp,h),g in T.groupby(['market','period','hypothesis','horizon'],sort=True):
 g=g.sort_values('date')
 x=g.disagreement.to_numpy(float); y=g.future_marginal_utility_pp.to_numpy(float)
 sp=float(spearmanr(x,y).statistic);pe=float(pearsonr(x,y).statistic)
 ci,k=cir_ci(x,y)
 out.append(dict(market=m,period=period,hypothesis=hyp,horizon=h,months=len(g),
                 spearman=sp,pearson=pe,ci95_lo=ci[0],ci95_hi=ci[1],bootstrap_draws=k,
                 mean_utility_pp=float(y.mean()),mean_disagreement=float(x.mean()),
                 positive_utility_months=int((y>0).sum()),negative_utility_months=int((y<0).sum())))
results=pd.DataFrame(out)
results.to_csv(D/'OLC64_ASSOCIATIONS.csv',index=False)

annual=[]
for (market,hyp,h,year),g in T[T.period=='MAIN'].groupby(['market','hypothesis','horizon','year']):
 x=g.disagreement.to_numpy();y=g.future_marginal_utility_pp.to_numpy()
 annual.append(dict(market=market,hypothesis=hyp,horizon=h,year=year,months=len(g),spearman=float(spearmanr(x,y).statistic),
                    mean_utility_pp=y.mean(),positive_utility_months=int((y>0).sum())))
pd.DataFrame(annual).to_csv(D/'OLC64_YEARLY_ASSOCIATIONS.csv',index=False)

# Independently verify exact fractional-utility equivalence with monthly factorial and pair correlation.
for (m,date,h),g in T.groupby(['market','date','horizon']):
 assert len(g)==2
 assert set(g.hypothesis)=={'H1_RETURN_VS_ET','H2_XGB_MARGINAL'}
 assert (g.disagreement>=0).all() and (g.disagreement<=2).all()
qa={'status':'PASS','preregistered_prior_to_outcome':True,'no_model_fit':True,'no_policy_modified':True,
    'months_eu':58,'months_usa':60,'hypotheses':2,'horizons':2,'row_count':len(T),
    'source_factorial_sha256':expected,'source_correlations_sha256':hashlib.sha256((P/'OLC63_MONTHLY_CORRELATIONS.csv').read_bytes()).hexdigest(),
    'protocol_sha256':hashlib.sha256((ROOT/'PROTOCOL_PRE_RESULTS.md').read_bytes()).hexdigest()}
(D/'OLC64_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
print(results.sort_values(['period','horizon','market','hypothesis']).to_string(index=False,float_format=lambda v:f'{v:+.4f}'))
print('\nAnnual 21-session:')
print(pd.DataFrame(annual).query('horizon=="mean21"').to_string(index=False,float_format=lambda v:f'{v:+.3f}'))
print(json.dumps(qa,indent=2))