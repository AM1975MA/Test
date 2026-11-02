"""Block-resampled descriptive OLC31 G1 differences; not a corrected alpha test."""
from pathlib import Path
import numpy as np,pandas as pd
from g0_source_parity import OUT

raw=pd.read_csv(OUT/'04_G1_MONTHLY_TOP5.csv')
result=[]
for market in ['EU','USA']:
 x=raw[raw.market==market].pivot(index='signal_date',columns='feature',values='pearson_top5').sort_index()
 assert len(x)==48
 rng=np.random.default_rng(np.random.SeedSequence([20261102,0 if market=='EU' else 1]))
 n=len(x);L=6;blocks=np.empty((4000,n),int)
 for i in range(4000):
  starts=rng.integers(0,n,size=int(np.ceil(n/L)))
  blocks[i]=np.concatenate([(np.arange(j,j+L)%n) for j in starts])[:n]
 for f in [t for t in x if t!='FUSION']:
  d=x[f].to_numpy(float)-x['FUSION'].to_numpy(float)
  observed=float(np.nanmean(d))
  sampled=np.nanmean(d[blocks],axis=1)
  lo,hi=np.nanquantile(sampled,[0.025,0.975])
  result.append({'market':market,'feature':f,'months':int(np.isfinite(d).sum()),'mean_diff_top5_pearson':observed,'block6_ci95_lower':float(lo),'block6_ci95_upper':float(hi),'descriptive_only':True})
pd.DataFrame(result).to_csv(OUT/'09_G1_BLOCK_BOOTSTRAP.csv',index=False)
print(pd.DataFrame(result).sort_values(['market','mean_diff_top5_pearson'],ascending=[True,False]).round(4).to_string(index=False))
