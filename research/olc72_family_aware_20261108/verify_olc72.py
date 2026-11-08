#!/usr/bin/env python3
"""Independent OLC72 checks: model reload, exact original support, top2 recomputation."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
import io,json
import pandas as pd,numpy as np,xgboost as xgb
from zipfile import ZipFile
import run_olc72 as c
R=Path(__file__).parent;O=R/'results'
def verify():
 z=c.init()
 p=pd.read_csv(O/'OLC72_PREDICTIONS.csv.gz',parse_dates=['signal_date'],float_precision='round_trip')
 mo=pd.read_csv(O/'OLC72_MONTHLY.csv',float_precision='round_trip')
 assert len(p)>17000 and len(mo)==240
 assert not p.duplicated(['market','signal_date','ticker']).any()
 assert np.allclose(p.RETURN_REBUILT,p.RETURN,atol=1e-13,rtol=0)
 assert np.nanmax(abs(.475*p.RETURN+.525*p.ORIGINAL_SMOOTH-p.ORIGINAL_FUSION))<1e-12
 assert np.nanmax(abs(.475*p.FAMILY_RETURN+.525*p.ORIGINAL_SMOOTH-p.FAMILY_FUSION))<1e-12
 checks=[];maxpred=0;maxpay=0
 for m in ('EU','USA'):
  cp=pd.read_pickle(io.BytesIO(z['OLC08F_01_FeaturePack_20261101.zip'].read(f'inputs/{m}_RSI_COMPACT.pkl')))
  for year in (2021,2024,2025):
   sub=p.loc[p.market.eq(m)&p.signal_date.dt.year.eq(year)].copy()
   obs=cp.loc[cp.eligible&cp.signal_date.dt.year.eq(year)].sort_values(['signal_date','ticker']).copy()
   f=c.audit(z,m,year)['return_features'];x=obs[f].to_numpy(float);x[~np.isfinite(x)]=np.nan
   models=[xgb.Booster(model_file=str(R/'models'/m/str(year)/f'FAMILY_{seed}.ubj')) for seed in c.SEEDS]
   pred=np.mean([model.predict(xgb.DMatrix(x,nthread=1)) for model in models],axis=0)
   chk=obs[['signal_date','ticker']].copy();chk['recomputed_raw']=pred
   chk=chk.merge(sub[['signal_date','ticker','FAMILY_RAW']],on=['signal_date','ticker'],validate='one_to_one')
   diff=float(np.max(abs(chk.recomputed_raw-chk.FAMILY_RAW)));maxpred=max(maxpred,diff)
   assert diff<1e-6,(m,year,diff)
   checks.append({'market':m,'year':year,'n_records':len(chk),'max_model_prediction_diff':diff})
 for (market,dt),group in p.groupby(['market','signal_date']):
  for method in ('ORIGINAL_FUSION','FAMILY_FUSION'):
   top=group.sort_values([method,'ticker'],ascending=[False,True],kind='stable').iloc[:2]
   mm=mo[(mo.market==market)&(mo.month==dt.strftime('%Y-%m'))&(mo.method==method)]
   assert len(mm)==1
   assert ';'.join(top.ticker.astype(str))==mm.top2.iloc[0]
   for metric,col in [('p21','fwd_ret_21'),('p42','fwd_ret_42')]:
    v=float(top[col].mean());o=float(mm[metric].iloc[0])
    if np.isfinite(v) and np.isfinite(o): maxpay=max(maxpay,abs(v-o));assert abs(v-o)<1e-12
 out={'n_predictions':len(p),'n_monthly_decisions':len(mo),'original_return_fusion_parity':True,
 'family_fusion_parity':True,'model_reload_sample_n':len(checks),'independently_recomputed_months':len(mo),
 'max_model_raw_prediction_error':maxpred,'max_top2_payoff_error':maxpay,'model_verification':checks,
 'status':'QA_PASS_RESEARCH_ONLY'}
 (O/'OLC72_INDEPENDENT_QA.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':verify()