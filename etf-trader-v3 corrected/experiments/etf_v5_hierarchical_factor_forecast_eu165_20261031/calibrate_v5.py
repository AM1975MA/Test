"""Strictly prior-matured prequential calibration of V5 ETF forecasts, 2023-24 only.
Tests intervals and probability of beating passive EXSA by round-trip 20 bps.
No portfolio deployment or selection from this diagnostic.
"""
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import norm
from sklearn.metrics import brier_score_loss, roc_auc_score
ROOT=Path(__file__).resolve().parent
p=pd.read_csv(ROOT/'PREQUENTIAL_MULTIHORIZON_PREDICTIONS.csv.gz',parse_dates=['signal_date','last_exit'])
p=p[p.model.isin(['FACTOR_ONLY','FACTOR_PLUS_BASIC_GBM','V5_FACTOR_PLUS_EXPERT_GBM'])].copy()
p['err']=p.true_log-p.mu
r=[];detail=[]
for (model,h),g in p.groupby(['model','horizon']):
 g=g.sort_values('signal_date').copy()
 bench=g[g.ticker=='EXSA.DE'][['signal_date','mu','true_log','err']].rename(columns={'mu':'mu_bench','true_log':'true_bench','err':'err_bench'})
 # Each forecast date is priced ex ante, and later used for calib only after exit.
 bench=bench.set_index('signal_date')
 for sd,month in g.groupby('signal_date'):
  if sd.year not in (2023,2024):continue
  start=sd-pd.DateOffset(months=24)
  prior=g[(g.signal_date>=start)&(g.signal_date<sd)&(g.last_exit<sd)&g.err.notna()].copy()
  if prior.signal_date.nunique()<12 or len(prior)<300:continue
  q=float(np.quantile(abs(prior.err),.8))
  test=month[month.true_log.notna()].copy();test['lower']=test.mu-q;test['upper']=test.mu+q
  coverage=float(((test.true_log>=test.lower)&(test.true_log<=test.upper)).mean())
  bi=bench.loc[sd] if sd in bench.index else None
  if bi is not None and pd.notna(bi.err_bench) and pd.notna(bi.true_bench):
   priorB=prior.join(bench[['err_bench','true_bench']],on='signal_date',how='left')
   priorB=priorB.dropna(subset=['err_bench','true_bench'])
   residualdiff=priorB.err-priorB.err_bench
   s=float(np.std(residualdiff)) if len(residualdiff)>200 else np.nan
   if np.isfinite(s) and s>0.001:
    expected_excess=test.mu-bi.mu_bench-0.002
    prob=norm.cdf(expected_excess/s)
    actual=((test.true_log-bi.true_bench-0.002)>0).astype(float)
    base=float(((priorB.true_log-priorB.true_bench-0.002)>0).mean())
    brier=float(np.mean((prob-actual)**2));brierbase=float(np.mean((base-actual)**2))
    predicted_win=float(np.mean(prob));actual_win=float(actual.mean())
    auc=float(roc_auc_score(actual,prob)) if actual.nunique()>1 else np.nan
   else:brier=brierbase=predicted_win=actual_win=auc=np.nan
  else:brier=brierbase=predicted_win=actual_win=auc=np.nan
  r.append({'model':model,'h':h,'date':sd,'n_priormonths':prior.signal_date.nunique(),'n_prior_etfs':len(prior),
    'n_test':len(test),'pred_half_width_80':q,'coverage80':coverage,'brier_vs_exsa':brier,
    'brier_base_rate':brierbase,'predicted_win_exsa':predicted_win,'actual_win_exsa':actual_win,'auc':auc})
  for _,z in test.iterrows():
   detail.append({'model':model,'h':h,'date':sd,'ticker':z.ticker,'mu':z.mu,'y':z.true_log,'q80':q,
    'hit80':int(z.lower<=z.true_log<=z.upper)})
D=pd.DataFrame(r);D.to_csv(ROOT/'MONTHLY_PREQUENTIAL_CALIBRATION.csv',index=False)
S=D.groupby(['model','h']).agg(months=('date','nunique'),ticker_months=('n_test','sum'),nominal_80_coverage=('coverage80','mean'),
  interval_half_width=('pred_half_width_80','mean'),brier_vs_exsa=('brier_vs_exsa','mean'),brier_base_rate=('brier_base_rate','mean'),
  predicted_win_exsa=('predicted_win_exsa','mean'),observed_win_exsa=('actual_win_exsa','mean'),auc=('auc','mean')).reset_index()
S.to_csv(ROOT/'PREQUENTIAL_CALIBRATION_SCORECARD.csv',index=False)
print(S.to_string(index=False,float_format=lambda x:f'{x:.4f}'))
