#!/usr/bin/env python3
"""OLC71: frozen-score conditional residual information of Return125.

Protocol: research/olc71_return125_residual_20261107/PROTOCOL_PRE_RESULTS.md
Dependencies: Python >=3.10, numpy, pandas, scikit-learn, scipy (for corr).
No portfolio accounting, no new historical quote acquisition, no live trading.
"""
from __future__ import annotations
import os
for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[k]='2'
from pathlib import Path
from zipfile import ZipFile
import hashlib,io,json,time
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from scipy.stats import spearmanr

HERE=Path(__file__).resolve().parent
INPUT=Path(os.environ.get('OLC71_SOURCE_DIR','/mnt/data/etf_source'))
OUT=HERE/'results'; OUT.mkdir(exist_ok=True)
SOURCE={
 'OLC08F_01_FeaturePack_20261101.zip':'420faa56547721fd58db9f75ceef1370483047073d91c1b675587bd2d2e9db6c',
 'OLC14_Fitting_Risultati_20261101.zip':'4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1',
 'OLC19_Rischio_Rientro_Checkpoint_20261102.zip':'3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540',
}
KEY=['signal_date','ticker']
META={'signal_date','ticker','source_date','eligible','entry_date','exit_date_21','fwd_ret_21','exit_date_42','fwd_ret_42','exit_date_63','fwd_ret_63','target_rank_21','target_rank_42','target_rank_63','target_rank_pct'}
BASE=['RETURN','ORIGINAL_CURRENT','ORIGINAL_SMOOTH']
SEEDS=[71001,71002,71003]


def sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(1<<22),b''): h.update(chunk)
 return h.hexdigest()


def get_data(m,z8,z14,z19):
 cp=pd.read_pickle(io.BytesIO(z8.read(f'inputs/{m}_RSI_COMPACT.pkl')))
 fcols=[c for c in cp.columns if c not in META]
 assert len(fcols)==125, (m,len(fcols))
 assert len(fcols)==len(set(fcols))
 cp=cp.loc[cp.eligible & cp.signal_date.between('2019-01-01','2025-12-31')].copy()
 assert not cp.duplicated(KEY).any()
 assert int((cp.source_date>cp.signal_date).sum())==0
 sc_prefix='olc19_combined_risk_20261102/restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/inputs/'
 sc=pd.read_csv(io.BytesIO(z19.read(sc_prefix+f'{m}_MEAN3_SCORES.csv.gz')),compression='gzip',parse_dates=['signal_date'],float_precision='round_trip')
 fit=pd.read_csv(io.BytesIO(z14.read(f'olc14_fitted_ranking_20261101/inputs/{m}_FITTING_FRAME.csv.gz')),compression='gzip',parse_dates=['signal_date','exit_date_21','exit_date_42'],float_precision='round_trip')
 for d in (sc,fit):assert not d.duplicated(KEY).any()
 q=cp.merge(sc[KEY+BASE+['ORIGINAL_FUSION']],on=KEY,how='left',validate='one_to_one')
 q=q.merge(fit[KEY+['fwd_ret_21','fwd_ret_42']],on=KEY,how='left',validate='one_to_one',suffixes=('','_olc14'))
 for target in ['fwd_ret_21','fwd_ret_42']:
  valid=q[target].notna() & q[target+'_olc14'].notna()
  a=q.loc[valid,target].to_numpy(); b=q.loc[valid,target+'_olc14'].to_numpy()
  assert np.allclose(a,b,atol=1e-10,rtol=0),(target,np.nanmax(np.abs(a-b)))
 assert ((q['ORIGINAL_FUSION']-(.475*q.RETURN+.525*q.ORIGINAL_SMOOTH)).abs().dropna().max()<1e-12)
 # The outcome is centered on the market-wide currently eligible universe, not on selected tickers.
 # Use only fully available 21d forward labels to form a realized cross-sectional relative target.
 g=q.groupby('signal_date')['fwd_ret_21']
 available=g.transform('count'); total=g.transform('size')
 q['group_valid21']=available.eq(total)
 q['retlog21']=np.log1p(q.fwd_ret_21)
 q['retlog42']=np.log1p(q.fwd_ret_42)
 q['target_bp']=1e4*(q.retlog21-q.groupby('signal_date').retlog21.transform('median'))
 # Strict group maturity for all the 63d peer outcomes, conservative relative to 21d target.
 q['train_group_exit63']=q.groupby('signal_date').exit_date_63.transform('max')
 q['fully_mature_label']=q.groupby('signal_date').exit_date_63.transform('count').eq(total)
 # Predictors are original model outputs and Return125 features. No knowledge of future values.
 return q,fcols


def ridge_model():
 return Pipeline([('imputer',SimpleImputer(strategy='median',keep_empty_features=True)),('scale',StandardScaler()),('ridge',Ridge(alpha=100,fit_intercept=True))])


def tree_model():
 return HistGradientBoostingRegressor(max_iter=75,max_leaf_nodes=7,min_samples_leaf=100,l2_regularization=100,
    learning_rate=.04,max_bins=127,random_state=71071,early_stopping=False)


def month_shuffle(features,dates,seed,tag):
 """Shuffle all Return125 features as a single multivariate block within each date.
       Tag used to independently shuffle train and test without shared random state.
 """
 out=np.asarray(features).copy()
 # stable per-group seed derived from exact date, tag and seed, independent of input row order.
 date_str=pd.to_datetime(dates).dt.strftime('%Y%m%d').to_numpy()
 for date in np.unique(date_str):
  ix=np.flatnonzero(date_str==date)
  if len(ix)<2:continue
  msg=f'{seed}|{tag}|{date}'.encode()
  rng=np.random.default_rng(int(hashlib.sha256(msg).hexdigest()[:16],16))
  out[ix]=out[ix][rng.permutation(len(ix))]
 return out


def model_fit_predict(model,xtrain,train_y,xtest):
 model.fit(xtrain,train_y)
 p=model.predict(xtest)
 if not np.isfinite(p).all():raise ValueError('nonfinite prediction')
 return p


def run_market(m,z8,z14,z19):
 q,feats=get_data(m,z8,z14,z19)
 meta=[];outs=[]
 for year in range(2021,2026):
  cutoff=pd.Timestamp(year,1,1)
  tr=q.loc[q.signal_date.lt(cutoff) & q.fully_mature_label & q.train_group_exit63.lt(cutoff) & q.group_valid21 & q[BASE].notna().all(axis=1)].copy()
  te=q.loc[q.signal_date.dt.year.eq(year) & q[BASE].notna().all(axis=1)].copy()
  if not len(tr) or not len(te):raise ValueError((m,year,'missing samples'))
  assert tr.train_group_exit63.max()<cutoff
  assert tr.source_date.le(tr.signal_date).all() and te.source_date.le(te.signal_date).all()
  assert tr.groupby('signal_date')['target_bp'].count().min()>0
  # Exclude present-day unknown future label only for evaluation, not for score calculation.
  qlabels=tr.target_bp.to_numpy(dtype='float64')
  Xb=tr[BASE].to_numpy(dtype='float64')
  Xt=te[BASE].to_numpy(dtype='float64')
  Ftr=tr[feats].to_numpy(dtype='float64');Fte=te[feats].to_numpy(dtype='float64')
  # Prepared B0 and B125 use the exact same dated rows and no predictions after label filtering.
  te['CTRL_RIDGE']=model_fit_predict(ridge_model(),Xb,qlabels,Xt)
  te['125_RIDGE']=model_fit_predict(ridge_model(),np.hstack([Xb,Ftr]),qlabels,np.hstack([Xt,Fte]))
  for seed in SEEDS:
   ftr=month_shuffle(Ftr,tr.signal_date,seed,'train')
   fte=month_shuffle(Fte,te.signal_date,seed,'test')
   te[f'NULL_{seed}']=model_fit_predict(ridge_model(),np.hstack([Xb,ftr]),qlabels,np.hstack([Xt,fte]))
  te['CTRL_TREE']=model_fit_predict(tree_model(),Xb,qlabels,Xt)
  te['125_TREE']=model_fit_predict(tree_model(),np.hstack([Xb,Ftr]),qlabels,np.hstack([Xt,Fte]))
  te['ORIG_FUSION']=te['ORIGINAL_FUSION']
  outs.append(te[KEY+['source_date','exit_date_21','exit_date_42','fwd_ret_21','fwd_ret_42','target_bp','ORIG_FUSION','CTRL_RIDGE','125_RIDGE','CTRL_TREE','125_TREE']+[f'NULL_{seed}' for seed in SEEDS]].copy())
  meta.append(dict(market=m,fit_year=year,cutoff=str(cutoff.date()),ntrain=len(tr),n_test=len(te),train_months=tr.signal_date.nunique(),test_months=te.signal_date.nunique(),last_training_exit63=str(tr.train_group_exit63.max().date()),n_features=125,score_features=BASE.copy(),min_source_lag_days=int((te.signal_date-te.source_date).dt.days.min()),nan_fractions_in_test=float(np.isnan(Fte).mean())))
  print('FIT',m,year,'train',len(tr),'test',len(te),'train_months',tr.signal_date.nunique(),flush=True)
 return pd.concat(outs,ignore_index=True),q,feats,meta


def evaluate_row_month(d,market,method,year,month):
 good=d[d[method].notna() & d['target_bp'].notna() & d['fwd_ret_21'].notna() & d['fwd_ret_42'].notna()].copy()
 if len(good)<50:return None
 pred=good[method].to_numpy()
 true=good.target_bp.to_numpy()
 corr=spearmanr(pred,true).statistic
 order=np.lexsort((good.ticker.astype(str).to_numpy(),-pred))
 chosen=good.iloc[order[:2]]
 # Top quintile of y evaluated on identical eligible rows, not selected on future values.
 threshold=np.nanpercentile(true,80)
 return dict(market=market,year=year,month=str(month),method=method,n_etf=len(good),
    mse_bp2=float(np.mean((pred-true)**2)) if method!='ORIG_FUSION' else np.nan,mae_bp=float(np.mean(np.abs(pred-true))) if method!='ORIG_FUSION' else np.nan,ic_21=float(corr),
    payoff_top2_21=float(chosen.fwd_ret_21.mean()),payoff_top2_42=float(chosen.fwd_ret_42.mean()),
    top2_top20=float((chosen.target_bp>=threshold).mean()),
    payoff_top2_21_log=float(np.log1p(chosen.fwd_ret_21).mean()),
    top2_tickers=';'.join(chosen.ticker.astype(str)),
    top2_negative_rate=float((chosen.fwd_ret_21<0).mean()))


def summarize_monthly(preds):
 methods=['ORIG_FUSION','CTRL_RIDGE','125_RIDGE','CTRL_TREE','125_TREE']+[f'NULL_{i}' for i in SEEDS]
 rows=[]
 for (market,signal_date),d in preds.groupby(['market','signal_date'],sort=True):
  for name in methods:
   r=evaluate_row_month(d,market,name,signal_date.year,signal_date.date())
   if r:rows.append(r)
 mo=pd.DataFrame(rows)
 rows=[]
 for (market,period,method),d in mo.assign(period=np.where(mo.year<=2024,'MAIN_2021_2024','LATE_2025')).groupby(['market','period','method']):
  rows.append(dict(market=market,period=period,method=method,months=len(d),
                   mse_bp2=d.mse_bp2.mean(),rmse_bp=np.sqrt(d.mse_bp2.mean()),mae_bp=d.mae_bp.mean(),ic_21=d.ic_21.mean(),
                   payoff_top2_21=d.payoff_top2_21.mean(),payoff_top2_42=d.payoff_top2_42.mean(),
                   top2_top20=d.top2_top20.mean(),top2_negative_rate=d.top2_negative_rate.mean()))
 return mo,pd.DataFrame(rows)


def block_bootstrap(mo):
 rng=np.random.default_rng(71071); res=[]
 for market in ['EU','USA']:
  sub=mo[(mo.market==market)&(mo.year.between(2021,2024))]
  w=sub.pivot(index='month',columns='method',values=['mse_bp2','payoff_top2_21'])
  # align complete date range (48 months), all fixed data; no estimator tuning.
  assert w.shape[0]==48
  for method,ctrl in [('125_RIDGE','CTRL_RIDGE'),('125_TREE','CTRL_TREE'),('NULL_71001','CTRL_RIDGE'),('NULL_71002','CTRL_RIDGE'),('NULL_71003','CTRL_RIDGE')]:
   dd_mse=w[('mse_bp2',ctrl)].to_numpy()-w[('mse_bp2',method)].to_numpy()
   dd_ret=w[('payoff_top2_21',method)].to_numpy()-w[('payoff_top2_21',ctrl)].to_numpy()
   assert np.isfinite(dd_mse).all() and np.isfinite(dd_ret).all()
   for metric,delta in [('mse_gain_bp2',dd_mse),('payoff_gain_pp',dd_ret*100)]:
    draws=[];length=len(delta);block=6;number=(length+block-1)//block
    for _ in range(4000):
     starts=rng.integers(0,length,number)
     ids=(starts[:,None]+np.arange(block))%length
     draws.append(float(delta[ids.ravel()[:length]].mean()))
    res.append(dict(market=market,compare=f'{method}_minus_{ctrl}',metric=metric,estimate=float(delta.mean()),ci_lower=float(np.percentile(draws,2.5)),ci_upper=float(np.percentile(draws,97.5)),months=length,bootstrap='circular_blocks_6_B4000_seed71071'))
 return pd.DataFrame(res)


def quality_stats(q,features,market):
 # Non-forecast quality analysis on 125 feature definitions and observed support.
 rows=[]
 for yr,d in q[q.signal_date.dt.year.between(2021,2025)].groupby(q.signal_date.dt.year):
  for col in features:
   x=d[col].to_numpy(float);valid=np.isfinite(x)
   rows.append(dict(market=market,year=int(yr),feature=col,kind='PCT' if col.endswith('_pct') else 'DEV' if col.endswith('_dev') else 'RAW',missing=float(1-valid.mean()),nonmissing=int(valid.sum()),std=float(np.std(x[valid])) if valid.any() else np.nan))
 return pd.DataFrame(rows)


def main():
 files={name:INPUT/name for name in SOURCE}
 for name,p in files.items():
  assert p.is_file(),p
  assert sha256(p)==SOURCE[name],(name,sha256(p))
 z8=ZipFile(files['OLC08F_01_FeaturePack_20261101.zip'])
 z14=ZipFile(files['OLC14_Fitting_Risultati_20261101.zip'])
 z19=ZipFile(files['OLC19_Rischio_Rientro_Checkpoint_20261102.zip'])
 preds=[];allmeta=[];qualities=[];names=None
 for market in ('EU','USA'):
  p,q,f,meta=run_market(market,z8,z14,z19)
  p.insert(0,'market',market)
  preds.append(p);allmeta.extend(meta);qualities.append(quality_stats(q,f,market));names=f
 pred=pd.concat(preds,ignore_index=True)
 assert not pred.duplicated(['market']+KEY).any()
 mo,su=summarize_monthly(pred)
 bs=block_bootstrap(mo)
 quality=pd.concat(qualities,ignore_index=True)
 pred.to_csv(OUT/'OLC71_OOF_PREDICTIONS.csv.gz',index=False,compression='gzip')
 mo.to_csv(OUT/'OLC71_MONTHLY_METRICS.csv',index=False)
 su.to_csv(OUT/'OLC71_SUMMARY.csv',index=False)
 bs.to_csv(OUT/'OLC71_BOOTSTRAP.csv',index=False)
 quality.to_csv(OUT/'OLC71_FEATURE_QUALITY.csv',index=False)
 pd.DataFrame(allmeta).to_csv(OUT/'OLC71_FIT_AUDIT.csv',index=False)
 (OUT/'OLC71_125_COLUMNS.json').write_text(json.dumps(names,indent=2))
 prior=pd.read_csv(INPUT/'PRIOR_FEATURES_125.csv')
 assert set(prior.feature)==set(names), 'prior feature table differs from original 125 columns'
 (OUT/'OLC71_AUDIT.json').write_text(json.dumps({
  'status':'reproducible research only','source_sha256':SOURCE,'features':len(names),'types':{'RAW':sum(not x.endswith(('_pct','_dev')) for x in names),'PCT':sum(x.endswith('_pct') for x in names),'DEV':sum(x.endswith('_dev') for x in names)},
  'n_prior_FDR_below_005':int((prior.FDR_q<.05).sum()),'min_prior_fdr_q':float(prior.FDR_q.min()),'n_oof_rows':len(pred),'monthly_events_by_market':mo.groupby('market')['month'].nunique().to_dict(),
  'training':allmeta,'source_reconciliation':'21/42 matching OLC14 <=1e-10, source_date <=signal_date, exact original FUSION formula',
  'selection_warning':'Top2 direct rank only, no OLC19 context/V6/risk, no CAGR',
  'no_new_holdout':True},indent=2,default=str))
 print('\n---SUMMARY---\n',su.to_string(index=False,float_format=lambda x:f'{x:.5f}'))
 print('\n---BOOTSTRAP---\n',bs.to_string(index=False,float_format=lambda x:f'{x:.5f}'))
 print('DONE',len(pred),'OOF rows',flush=True)

if __name__=='__main__':main()