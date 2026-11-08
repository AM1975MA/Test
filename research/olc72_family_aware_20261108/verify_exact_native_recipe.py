#!/usr/bin/env python3
"""Re-fits seed101 native unweighted XGB of 2024, compares with archive for BOTH markets."""
from pathlib import Path
import io,json
import numpy as np,pandas as pd,xgboost as xgb
import run_olc72 as c
R=Path(__file__).parent;O=R/'results';z=c.init();out=[]
for market in ['EU','USA']:
 cp=pd.read_pickle(io.BytesIO(z['OLC08F_01_FeaturePack_20261101.zip'].read(f'inputs/{market}_RSI_COMPACT.pkl')))
 tr,te,y,groups=c.train_test(cp,2024);f=c.audit(z,market,2024)['return_features']
 X=tr[f].to_numpy(float);XP=te[f].to_numpy(float);X[~np.isfinite(X)]=np.nan;XP[~np.isfinite(XP)]=np.nan
 dm=xgb.QuantileDMatrix(X,label=y,nthread=1);dm.set_group(groups)
 dp=xgb.QuantileDMatrix(XP,ref=dm,nthread=1)
 refit=xgb.train({**c.PARAMS,'seed':101},dm,num_boost_round=360,verbose_eval=False)
 native=c.orig_model(z,market,2024,101)
 a=refit.predict(dp);b=native.predict(dp)
 diff=float(np.max(abs(a-b)))
 print('EXACT_NAT',market,'model native-refit max prediction diff',diff,'n_train',len(tr),'n_pred',len(te),flush=True)
 assert diff==0.0,(market,'TRAIN_RECIPE_PARITY_FAILURE',diff)
 out.append({'market':market,'fit_year':2024,'seed':101,'native_retrain_prediction_exact':True,'max_abs_diff':diff,'n_train':len(tr),'n_test':len(te)})
(O/'OLC72_NATIVE_REFIT_PARITY.json').write_text(json.dumps({'checks':out,'status':'PASS'},indent=2))