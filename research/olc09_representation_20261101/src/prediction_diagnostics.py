"""Matched out-of-time target error; no outcome-based feature or seed selection."""
from bridge import *
from replay_models import source
import numpy as np,pandas as pd,joblib
OUT=ROOT/'results'
rows=[]
variants=list(pd.read_csv(OUT/'SCORECARD.csv').variant.unique())
for m in ['EU','USA']:
    panel=pd.read_pickle(parent_bootstrap.CAL/f'{m}_HYBRID.pkl')
    panel['TARGET']=parent_bootstrap.corrected_target(panel)
    labels=panel.loc[(panel.signal_date>='2021-01-01')&(panel.exit_date_63<'2025-01-01'),['signal_date','ticker','TARGET']]
    means={year:float(joblib.load(ROOT/'cache'/f'{m}_{year}.joblib')['y'].mean()) for year in range(2021,2025)}
    ref_support=None
    for v in variants:
        p=pd.read_csv(source(m,v),parse_dates=['signal_date'],float_precision='round_trip')
        p=p.merge(labels,on=['signal_date','ticker'],validate='one_to_one')
        p=p.dropna(subset=['ET_RAW','XGB_RAW','TARGET'])
        keys=key_hash(p.sort_values(['signal_date','ticker']))
        if ref_support is None:ref_support=keys
        else:assert keys==ref_support
        p['predicted_target']=.6*p.ET_RAW+.4*p.XGB_RAW
        for date,g in p.groupby('signal_date'):
            mean=means[date.year]
            rows.append(dict(market=m,variant=v,date=str(date.date()),n=len(g),mse=float(((g.predicted_target-g.TARGET)**2).mean()),mean_baseline_mse=float(((mean-g.TARGET)**2).mean())))
d=pd.DataFrame(rows);d.to_csv(OUT/'TARGET_ERROR_MONTHS.csv',index=False)
a=d.groupby(['market','variant']).agg(months=('date','nunique'),mse=('mse','mean'),mean_baseline_mse=('mean_baseline_mse','mean')).reset_index()
a['relative_mse_vs_train_mean']=a.mse/a.mean_baseline_mse-1
a.to_csv(OUT/'TARGET_ERROR_SUMMARY.csv',index=False)
print(a[a.variant.isin(['REF_RSI','ENSEMBLE_REF42','FIXED_CORE_S101','FIXED_PATH_S101'])].to_string(index=False))
