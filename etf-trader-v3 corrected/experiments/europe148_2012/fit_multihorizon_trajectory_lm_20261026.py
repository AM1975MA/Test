#!/usr/bin/env python3
"""Walk-forward annual causal 21/42/63-session ETF trajectory FORECASTS (not ranking).

LM = linear model (standardized multi-output Ridge) as a transparent reference;
GMB = LightGBM separate robust conditional median signed-return regressions.
Models predict signed price returns, not within-month percentiles.
Strictly each fit row requires the t+63 target to be MATURE BEFORE Jan 1.
No future labels in test eligibility. Same frozen 125 inputs and 101 common dates.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from lightgbm import LGBMRegressor
from etf_trader_v3.source_only import kernel as K
HORIZONS=(21,42,63)
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--market',choices=['US149','EU148'],required=True)
    p.add_argument('--year',type=int,required=True)
    p.add_argument('--panel',required=True)
    p.add_argument('--out',required=True)
    a=p.parse_args()
    assert 2018<=a.year<=2026
    assert len(K.F2D_FEATURES)==125
    z=pd.read_parquet(Path(a.panel)/a.market/'CORRECTED125_PANEL.parquet')
    z.signal_date=pd.to_datetime(z.signal_date)
    for h in HORIZONS:
        col=f'exit_date_{h}'
        assert col in z and f'fwd_ret_{h}' in z
        z[col]=pd.to_datetime(z[col])
    first=pd.Timestamp(f'{a.year}-01-01')
    tr=z[z.signal_date.lt(first)&z.signal_date.ge('2012-01-01')&
         z.exit_date_63.lt(first)&z[[f'fwd_ret_{h}' for h in HORIZONS]].notna().all(axis=1)].copy()
    te=z[z.signal_date.dt.year.eq(a.year)&z.signal_date.between('2018-01-01','2026-05-31')].copy()
    tr=tr.sort_values(['signal_date','ticker']).reset_index(drop=True)
    te=te.sort_values(['signal_date','ticker']).reset_index(drop=True)
    assert tr.signal_date.nunique()>=65 and len(tr)>2500
    assert tr.exit_date_63.max()<first
    assert te.signal_date.nunique()==(5 if a.year==2026 else 12)
    assert te.groupby('signal_date').ticker.nunique().ge(25).all()
    feature=list(K.F2D_FEATURES)
    X=tr[feature].replace([np.inf,-np.inf],np.nan)
    Xt=te[feature].replace([np.inf,-np.inf],np.nan)
    Y=tr[[f'fwd_ret_{h}' for h in HORIZONS]].to_numpy(float)
    # Train with signed TARGET returns and all complete 63-session-mature paths.
    assert np.isfinite(Y).all() and np.nanmin(Y)>-1.001
    months=tr.groupby('signal_date').size()
    # Monthly signal equal importance despite universe expansion and EU short history.
    weight=tr.signal_date.map((len(tr)/len(months)/months).to_dict()).to_numpy(float)
    out=[]
    # LM means transparent linear regression, not generative text or a LLM.
    # Centered and scaled features are fitted on past-only data.
    lm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),
        Ridge(alpha=250.))
    lm.fit(X,Y,ridge__sample_weight=weight)
    pred_lm=lm.predict(Xt)
    assert pred_lm.shape==(len(te),3)
    preds={'LM_RIDGE_PATH':pred_lm}
    lgb=[]
    for hi,h in enumerate(HORIZONS):
        mm=LGBMRegressor(objective='regression_l1',n_estimators=220,
            learning_rate=0.035,num_leaves=15,max_depth=-1,
            min_child_samples=60,reg_lambda=8.0,reg_alpha=0.15,
            colsample_bytree=0.80,subsample=0.85,subsample_freq=1,
            random_state=20261026+h,n_jobs=2,verbosity=-1)
        mm.fit(X,Y[:,hi],sample_weight=weight)
        lgb.append(mm.predict(Xt))
    preds['LGBM_MEDIAN_PATH']=np.column_stack(lgb)
    rows=[]
    truth=te[['signal_date','ticker','entry_date','fwd_ret_21','fwd_ret_42','fwd_ret_63',
        'exit_date_21','exit_date_42','exit_date_63']]
    for name,pp in preds.items():
        xx=truth.copy()
        xx['market']=a.market
        xx['model']=name
        for hi,h in enumerate(HORIZONS):
            xx[f'forecast_{h}']=pp[:,hi]
        # Fixed, not tuned with historical OOS results: slope-normalized horizon path,
        # signed predicted downside penalty along whole 3-point trajectory.
        y21,y42,y63=(pp[:,i] for i in range(3))
        xx['score_P21']=y21
        xx['score_PATH']=(.70*y21+.20*(y42/2)+.10*(y63/3)-
             .30*np.maximum(0.,-np.min(pp,axis=1)))
        rows.append(xx)
    result=pd.concat(rows,ignore_index=True)
    assert not result.duplicated(['signal_date','ticker','model']).any()
    assert result.groupby('model').signal_date.nunique().eq(te.signal_date.nunique()).all()
    folder=Path(a.out);folder.mkdir(parents=True,exist_ok=True)
    result.to_csv(folder/'ANNUAL_TRAJECTORY_FORECASTS.csv',index=False)
    diag=dict(market=a.market,year=a.year,train_months=tr.signal_date.nunique(),
       train_rows=len(tr),test_months=te.signal_date.nunique(),test_rows=len(te),
       labels='signed 21,42,63 common-trading-session open-to-open future total returns',
       training_maturity='all horizons exit before Jan1 vintage',
       train_last_63_label_exit=str(tr.exit_date_63.max().date()),
       feature_count=len(feature),trained_on_test=False,
       variants=['LM_RIDGE_PATH','LGBM_MEDIAN_PATH'],
       objective_lgb='MAE conditional median future signed return',
       lm_alpha=250.,horizon_weights_PATH=[.70,.20,.10],
       path_downside_penalty=.30,hyperparameters_selected_without_test=True,
       dev_notice='research branch, no prospective holdout, no tuning after viewing test')
    (folder/'ANNUAL_FIT_AUDIT.json').write_text(json.dumps(diag,indent=2))
    print('TRAJECTORY_FIT_PASS',a.market,a.year,diag['train_rows'],diag['test_rows'],
          'forecasts',len(result),flush=True)
if __name__=='__main__':main()
