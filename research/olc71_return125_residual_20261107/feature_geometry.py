#!/usr/bin/env python3
"""Structural geometry, rank equivalence, missingness, effective covariance dimension."""
from run_olc71 import *
from scipy.stats import rankdata,spearmanr
from numpy.linalg import eigvalsh

fdir=OUT;za=ZipFile(INPUT/'OLC08F_01_FeaturePack_20261101.zip')
rows=[];dimensions=[]
for market in ('EU','USA'):
 cp=pd.read_pickle(io.BytesIO(za.read(f'inputs/{market}_RSI_COMPACT.pkl')))
 cp=cp.loc[cp.eligible & cp.signal_date.dt.year.between(2021,2024)].copy()
 cols=[c for c in cp.columns if c not in META]
 raw=[c for c in cols if not c.endswith(('_pct','_dev'))]
 # Cross-sectional rank agreement per (month, family)
 for date,d in cp.groupby('signal_date'):
  for col in raw:
   for suffix in ('_pct','_dev'):
    target=col+suffix
    if target not in cp.columns:continue
    x=d[col].to_numpy(float);y=d[target].to_numpy(float)
    good=np.isfinite(x)&np.isfinite(y)
    if good.sum()<15 or np.std(x[good])==0 or np.std(y[good])==0:continue
    ic=spearmanr(x[good],y[good]).statistic
    rows.append(dict(market=market,date=date.strftime('%Y-%m-%d'),feature=col,suffix=suffix,coverage=float(good.mean()),rank_ic=float(ic)))
 # Covariance dimension. Drop features all-missing; fill within-date median as neutral, standardize each date separately.
 mat=[]
 for date,d in cp.groupby('signal_date'):
  x=d[cols].to_numpy(float)
  for j in range(x.shape[1]):
   v=x[:,j];ok=np.isfinite(v)
   if ok.sum()<15 or np.nanstd(v)==0:x[:,j]=0
   else:
    median=np.nanmedian(v);v[~ok]=median
    sd=np.std(v)
    x[:,j]=(v-np.mean(v))/(sd if sd else 1)
  mat.append(x)
 x=np.vstack(mat)
 cov=np.corrcoef(x,rowvar=False)
 eig=eigvalsh(cov)
 eig=np.maximum(eig,0)
 participation=(eig.sum()**2)/np.sum(eig**2)
 entropy=np.exp(-np.sum((eig/eig.sum())[eig>0]*np.log((eig/eig.sum())[eig>0])))
 for cutoff in (0.50,0.8,0.9,0.95):
  k=int(np.searchsorted(np.cumsum(eig[::-1])/eig.sum(),cutoff)+1)
  dimensions.append(dict(market=market,measure='components_to_reach_'+str(cutoff),value=k))
 dimensions += [dict(market=market,measure='participation_ratio',value=participation),dict(market=market,measure='spectral_entropy_effective_rank',value=entropy)]
 print(market,'raw',len(raw),'all',len(cols),'effective_rank',participation,'entropy',entropy)
df=pd.DataFrame(rows);df.to_csv(OUT/'OLC71_RANK_REDUNDANCY.csv',index=False)
pd.DataFrame(dimensions).to_csv(OUT/'OLC71_EFFECTIVE_DIMENSION.csv',index=False)
print(df.groupby(['market','suffix']).rank_ic.agg(['count','mean','median','min','max']).to_string())
print('fraction rank equivalence abs(r-1)<1e-8:',df.groupby(['market','suffix']).rank_ic.apply(lambda x:np.mean(abs(x-1)<1e-8)).to_dict())
print(pd.DataFrame(dimensions).to_string(index=False))