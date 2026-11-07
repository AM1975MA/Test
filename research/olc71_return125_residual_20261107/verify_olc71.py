#!/usr/bin/env python3
"""Independent output and source-labelling QA for OLC71A/B/C, no refitting models."""
import io,json,os
from pathlib import Path
from zipfile import ZipFile
import pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';INPUT=Path(os.environ.get('OLC71_SOURCE_DIR','/mnt/data/etf_source'))
source={
 'OLC08F_01_FeaturePack_20261101.zip':'420faa56547721fd58db9f75ceef1370483047073d91c1b675587bd2d2e9db6c',
 'OLC14_Fitting_Risultati_20261101.zip':'4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1',
 'OLC19_Rischio_Rientro_Checkpoint_20261102.zip':'3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540',}

a=pd.read_csv(OUT/'OLC71_OOF_PREDICTIONS.csv.gz',parse_dates=['signal_date'])
b=pd.read_csv(OUT/'OLC71C_TOP10_OOF.csv.gz',parse_dates=['signal_date'])
sumry=pd.read_csv(OUT/'OLC71_SUMMARY.csv');sumb=pd.read_csv(OUT/'OLC71B_SUMMARY.csv');sumc=pd.read_csv(OUT/'OLC71C_TOP10_SUMMARY.csv')
fit=pd.read_csv(OUT/'OLC71_FIT_AUDIT.csv')
assert len(a)==18099 and len(b)==1200
assert a[['market','signal_date','ticker']].duplicated().sum()==0
assert b[['market','signal_date','ticker']].duplicated().sum()==0
assert ((pd.to_datetime(fit.last_training_exit63)<pd.to_datetime(fit.cutoff))).all()
assert (fit.min_source_lag_days>=0).all()
assert a.ORIG_FUSION.notna().all()
checks=[]
# Recalculate original selected returns DIRECTLY on stored rows, independent of stored monthly metrics.
for market in ('EU','USA'):
 for period,yr in [('MAIN_2021_2024',range(2021,2025)),('LATE_2025',[2025])]:
  q=a[(a.market==market)&(a.signal_date.dt.year.isin(yr)) & a.fwd_ret_21.notna() & a.fwd_ret_42.notna()].copy()
  results=[]
  for date,g in q.groupby('signal_date'):
   g=g.loc[g.ORIG_FUSION.notna()].sort_values(['ORIG_FUSION','ticker'],ascending=[False,True])
   top=g.head(2)
   results.append((top.fwd_ret_21.mean(),top.fwd_ret_42.mean()))
  m=np.mean(results,axis=0)
  target=sumry[(sumry.market==market)&(sumry.period==period)&(sumry.method=='ORIG_FUSION')].iloc[0]
  err=max(abs(m[0]-target.payoff_top2_21),abs(m[1]-target.payoff_top2_42))
  assert err<1e-12,(market,period,err)
  # Re-evaluate OOF Ridge forecasts without using saved monthly table or module routines.
  for model in ['CTRL_RIDGE','125_RIDGE','CTRL_TREE','125_TREE']:
   row=sumry[(sumry.market==market)&(sumry.period==period)&(sumry.method==model)].iloc[0]
   diff=q[model]-q.target_bp
   mse=(diff**2).mean() # all months have different counts EU; reconcile with weighted monthly mean
   monthly=(diff**2).groupby(q.signal_date).mean().mean()
   assert abs(monthly-row.mse_bp2)<1e-6,(market,period,model,row.mse_bp2,monthly)
  checks.append(dict(market=market,period=period,months=len(results),original_payoff21=m[0],original_payoff42=m[1],max_static_parity_abs=err))
# Original FUSION top10 and original top2 must pick the same Top2 on identical months.
for market in ('EU','USA'):
 aa=a[(a.market==market)]
 bb=b[(b.market==market)]
 for date,g in bb.groupby('signal_date'):
  top_a=aa[aa.signal_date.eq(date)].sort_values(['ORIG_FUSION','ticker'],ascending=[False,True]).head(2).ticker.tolist()
  top_b=g.sort_values(['ORIG_FUSION_TOP2','ticker'],ascending=[False,True]).head(2).ticker.tolist()
  assert top_a==top_b,(market,date,top_a,top_b)
# No calibrated FUSION MSE may appear; original score is dimensionless, not log-bp.
assert sumry.loc[sumry.method=='ORIG_FUSION','mse_bp2'].isna().all()
# 125 columns exactly the set from prior table and three derived blocks.
names=json.loads((OUT/'OLC71_125_COLUMNS.json').read_text())
assert len(names)==125
assert len([x for x in names if x.endswith('_pct')])==46
assert len([x for x in names if x.endswith('_dev')])==33
assert len([x for x in names if not x.endswith(('_pct','_dev'))])==46
prior=pd.read_csv(INPUT/'PRIOR_FEATURES_125.csv')
assert set(prior.feature)==set(names)
checks.sort(key=lambda x:(x['market'],x['period']))
res={'passed':True,'rows_oof':int(len(a)),'top10_oof_rows':int(len(b)), 'score_parity_checks':checks,
 'train_label_maturity_cutoffs_pass':True,'original_score_in_bp_mse_excluded':True,
 'feature_family_counts':{'RAW':46,'PCT':46,'DEV':33},'prior_feature_set_identical':True,
 'source_sha256':source,'limitation':'Internal independent output recomputation only; no new external prices/OOS and no full NAV accounting'}
(OUT/'OLC71_INDEPENDENT_QA.json').write_text(json.dumps(res,indent=2,ensure_ascii=False))
print(json.dumps(res,indent=2,ensure_ascii=False))