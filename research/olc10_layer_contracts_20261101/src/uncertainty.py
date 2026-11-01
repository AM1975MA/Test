"""Paired monthly block inference on layer metrics, not CAGR; common month alignment."""
from pathlib import Path
import pandas as pd,numpy as np
from layer_metrics import paired_month_matrix
ROOT=Path(__file__).resolve().parents[1];O=ROOT/'results';df=pd.read_csv(O/'TARGET_MONTHS.csv')
comparisons=[('AFFINE_target_loss','CAL_AFFINE','REF_RSI','mse',-1),('STACK_target_loss','CAL_STACK2','REF_RSI','mse',-1),('SHRINK_target_loss','SHRINK50','REF_RSI','mse',-1),('PATH_target_loss','FIXED_PATH_S101','FIXED_CORE_S101','mse',-1),('PATH_target_Top2','FIXED_PATH_S101','FIXED_CORE_S101','ndcg2',1),('STACK_target_Top2','CAL_STACK2','REF_RSI','ndcg2',1)]
rows=[]
for block in [3,6]:
    series={}
    for name,c,b,metric,sgn in comparisons:
        for m in ['EU','USA']:
            a=df[(df.market==m)&(df.period=='PRE2025')&df.variant.isin([c,b])].pivot(index='date',columns='variant',values=metric).dropna()
            series[(name,m)]=sgn*(a[c]-a[b])
    z=paired_month_matrix(series);x=z.to_numpy();n=len(x);rng=np.random.default_rng(20261101)
    starts=rng.integers(0,n,size=(6000,(n+block-1)//block))
    idx=((starts[:,:,None]+np.arange(block))%n).reshape(6000,-1)[:,:n]
    draws=x[idx].mean(axis=1);point=x.mean(axis=0);sd=draws.std(axis=0,ddof=1)
    active=sd>1e-15;crit=np.quantile(np.max(abs((draws[:,active]-point[active])/sd[active]),axis=1),.95)
    for j,col in enumerate(z.columns):
        lo,hi=np.quantile(draws[:,j],[.025,.975]);rows.append({'contrast':col[0],'market':col[1],'block_months':block,'paired_common_months':n,'higher_is_better':True,'mean_difference':point[j],'ci95_low':lo,'ci95_high':hi,'family_simultaneous95_low':point[j]-crit*sd[j],'family_simultaneous95_high':point[j]+crit*sd[j],'bootstrap_positive_fraction_not_posterior':float(np.mean(draws[:,j]>0))})
pd.DataFrame(rows).to_csv(O/'LAYER_PAIRED_UNCERTAINTY.csv',index=False)
print(pd.DataFrame(rows).query('block_months==6').to_string(index=False))
