#!/usr/bin/env python3
"""Post-OLC71A diagnostic of Return125 feature families. NOT independent OOS."""
import io,json
import numpy as np,pandas as pd
from zipfile import ZipFile
from pathlib import Path
from run_olc71 import INPUT,OUT,SOURCE,BASE,KEY,SEEDS,sha256,get_data,ridge_model,model_fit_predict,evaluate_row_month

GROUPS=['RAW46','PCT46','DEV33','NO_LIQ119']

def main():
 for name,sha in SOURCE.items():assert sha256(INPUT/name)==sha
 z8=ZipFile(INPUT/'OLC08F_01_FeaturePack_20261101.zip');z14=ZipFile(INPUT/'OLC14_Fitting_Risultati_20261101.zip');z19=ZipFile(INPUT/'OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
 old=pd.read_csv(OUT/'OLC71_OOF_PREDICTIONS.csv.gz',compression='gzip',parse_dates=['signal_date'])
 all_rows=[];fit_rows=[]
 for market in ('EU','USA'):
  q,feats=get_data(market,z8,z14,z19)
  group={
   'RAW46':[x for x in feats if not x.endswith(('_pct','_dev'))],
   'PCT46':[x for x in feats if x.endswith('_pct')],
   'DEV33':[x for x in feats if x.endswith('_dev')],
   'NO_LIQ119':[x for x in feats if not x.startswith(('log_adv63','volume_surprise21'))],
  }
  assert {x:len(cols) for x,cols in group.items()} == {'RAW46':46,'PCT46':46,'DEV33':33,'NO_LIQ119':119}
  for year in range(2021,2026):
   cutoff=pd.Timestamp(year,1,1)
   tr=q.loc[q.signal_date.lt(cutoff) & q.fully_mature_label & q.train_group_exit63.lt(cutoff) & q.group_valid21 & q[BASE].notna().all(axis=1)]
   te=q.loc[q.signal_date.dt.year.eq(year) & q[BASE].notna().all(axis=1)].copy()
   Xb=tr[BASE].to_numpy(float);Xt=te[BASE].to_numpy(float);y=tr.target_bp.to_numpy(float)
   test=old[(old.market==market)&old.signal_date.dt.year.eq(year)].set_index(KEY)
   native=te.set_index(KEY)
   assert len(test)==len(native) and set(test.index)==set(native.index)
   expected=test.loc[native.index,'CTRL_RIDGE'].to_numpy(float)
   new=model_fit_predict(ridge_model(),Xb,y,Xt)
   err=float(np.max(np.abs(new-expected)))
   assert err<1e-8,(market,year,err)
   for name,cols in group.items():
    p=model_fit_predict(ridge_model(),np.column_stack([Xb,tr[cols].to_numpy(float)]),y,np.column_stack([Xt,te[cols].to_numpy(float)]))
    t=te[KEY+['target_bp','fwd_ret_21','fwd_ret_42']].copy();t['score']=p
    t['market']=market;t['year']=year;t['method']=name
    all_rows.append(t)
    fit_rows.append(dict(market=market,year=year,group=name,ntrain=len(tr),npredict=len(te),features=len(cols),control_parity_absmax=err))
   print('family fit',market,year, 'base parity',err,flush=True)
 pred=pd.concat(all_rows,ignore_index=True)
 rows=[]
 for (market,date,method),x in pred.groupby(['market','signal_date','method'],sort=True):
  val=evaluate_row_month(x.rename(columns={'score':method}),market,method,date.year,date.date())
  if val:rows.append(val)
 monthly=pd.DataFrame(rows)
 sums=[]
 for (market,period,method),d in monthly.assign(period=np.where(monthly.year<=2024,'MAIN_2021_2024','LATE_2025')).groupby(['market','period','method']):
  sums.append(dict(market=market,period=period,method=method,months=len(d),rmse_bp=float(np.sqrt(d.mse_bp2.mean())),mse_bp2=float(d.mse_bp2.mean()),ic21=float(d.ic_21.mean()),top2_21=float(d.payoff_top2_21.mean()),top2_42=float(d.payoff_top2_42.mean()),top20=float(d.top2_top20.mean()),negative=float(d.top2_negative_rate.mean())))
 pd.DataFrame(fit_rows).to_csv(OUT/'OLC71B_FIT_AUDIT.csv',index=False)
 monthly.to_csv(OUT/'OLC71B_MONTHLY.csv',index=False)
 pd.DataFrame(sums).to_csv(OUT/'OLC71B_SUMMARY.csv',index=False)
 (OUT/'OLC71B_QA.json').write_text(json.dumps({'family_models':len(fit_rows),'rows':len(pred),'old_scores_ridge_parity':'max_abs <1e-8 on all 10 folds','source_sha256':SOURCE,'post_olc71a_diagnostic':True},indent=2))
 print(pd.DataFrame(sums).to_string(index=False,float_format=lambda x:f'{x:.5f}'))

if __name__=='__main__':main()