"""Strict annual-fitted factor + idiosyncratic predictions at 21,42,63 trading days.
Predefined 2 alpha estimators and factor-only control; train label fully matured.
NOT portfolio optimization. Raw rankers are features, not weighted votes.
"""
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
from lightgbm import LGBMRegressor
ROOT=Path(__file__).resolve().parent
H=[21,42,63]
source=pd.read_pickle(ROOT/'PIT_MONTHLY_ETF_FEATURES.pkl')
fac=pd.read_pickle(ROOT/'PIT_MONTHLY_FACTOR_FEATURES.pkl')
macro=pd.get_dummies(source['macro'],prefix='macro',dtype=float)
source=pd.concat([source.reset_index(drop=True),macro.reset_index(drop=True)],axis=1)
BETA=['beta_EU','beta_US','beta_BANK','beta_BOND'];MACRO=list(macro.columns)
BASIC=['m21','m63','m126','m252','resid_m21','resid_m63','vol63','market_gap200']+BETA + MACRO
# Train-once source rankers: their raw signals contain complementary opportunities.
EXPERTS=['V3_PAIR127_PCT','V3_PAIR25_HYBRID_PCT','V2_FULL_HYBRID_PCT','V3_TAIL_RIDGE45_PCT','MOM252_PCT']
WITH=BASIC+EXPERTS

def clean(D,fields):
 a=D[fields].astype(float).to_numpy();a[~np.isfinite(a)]=np.nan
 return a

def standard_ridge(X,y,Xtest,alpha=100.0):
 model=make_pipeline(SimpleImputer(strategy='median',add_indicator=False),StandardScaler(),Ridge(alpha=alpha))
 model.fit(X,y)
 return model.predict(Xtest),model

def lgbm(X,y,Xtest):
 imputer=SimpleImputer(strategy='median');a=imputer.fit_transform(X);b=imputer.transform(Xtest)
 model=LGBMRegressor(n_estimators=110,learning_rate=.025,num_leaves=7,max_depth=3,min_child_samples=130,
    reg_lambda=15.0,reg_alpha=1.0,colsample_bytree=.9,subsample=1.0,n_jobs=2,verbosity=-1,random_state=20261031)
 model.fit(a,y)
 return model.predict(b),model

pred=[];audit=[]
for year in range(2021,2027):
 cutoff=pd.Timestamp(year,1,1)
 test=source[source.signal_date.dt.year==year].copy()
 if test.empty:continue
 ftest=fac[fac.signal_date.dt.year==year].copy()
 if ftest.empty:continue
 fd={}
 for h in H:
  fmu=np.zeros((len(ftest),4))
  for k in range(4):
   fields=[f'f{k}_mom21',f'f{k}_mom63',f'f{k}_mom252',f'f{k}_vol63','market_gap200']
   yy=f'f{k}_y{h}';m=fac[(fac['exit_'+str(h)]<cutoff)&fac[yy].notna()&(fac.signal_date<cutoff)]
   if len(m)>=18:
    fp,_=standard_ridge(clean(m,fields),m[yy].to_numpy(float),clean(ftest,fields),alpha=20)
   else:fp=np.zeros(len(ftest))
   fmu[:,k]=fp
   audit.append({'year':year,'horizon':h,'model':f'factor_{k}','train_rows':len(m),
             'last_label_exit':m['exit_'+str(h)].max() if len(m) else pd.NaT,'pred_rows':len(ftest)})
  fd[h]={d:arr for d,arr in zip(ftest.signal_date,fmu)}
 for h in H:
  target='alpha'+str(h);exitcol='exit_'+str(h)
  train=source[(source[exitcol]<cutoff)&(source.signal_date<cutoff)&source[target].notna()].copy()
  # A true source-fitted ETF score must be present for direct specialist model.
  train=train[train[EXPERTS].notna().all(axis=1)]
  audit.append({'year':year,'horizon':h,'model':'ETF_annual_train','train_rows':len(train),
       'last_label_exit':train[exitcol].max() if len(train) else pd.NaT,'pred_rows':len(test)})
  if len(train)<450:continue
  trX=clean(train,BASIC);teX=clean(test,BASIC)
  nobase,nobmod=standard_ridge(trX,train[target].to_numpy(float),teX)
  basic_boosted,basic_gbm=lgbm(trX,train[target].to_numpy(float),teX)
  fullX=clean(train,WITH);testX=clean(test,WITH)
  rid,model=standard_ridge(fullX,train[target].to_numpy(float),testX)
  boosted,gbm=lgbm(fullX,train[target].to_numpy(float),testX)
  # TRAIN-only idiosyncratic-error spread (not conformal, no claim of calibrated interval).
  in_pred=model.predict(SimpleImputer(strategy='median').fit_transform(fullX)) if False else None
  # compute raw dispersion of label and preserve the risk proxy for evaluation.
  resid_sigma=float(np.std(train[target].to_numpy(float),ddof=1))
  assert train[exitcol].max()<cutoff
  for k,(_,r) in enumerate(test.iterrows()):
   factors=fd[h].get(r.signal_date,np.zeros(4))
   fm=float(np.dot(r[BETA].to_numpy(float),factors))
   for modelname,pval in [('FACTOR_ONLY',0.0),('FACTOR_PLUS_BASIC_RIDGE',nobase[k]),('FACTOR_PLUS_BASIC_GBM',basic_boosted[k]),
       ('V5_FACTOR_PLUS_EXPERT_RIDGE',rid[k]),('V5_FACTOR_PLUS_EXPERT_GBM',boosted[k])]:
    pred.append({'signal_date':r.signal_date,'ticker':r.ticker,'year':year,'horizon':h,'model':modelname,
      'mu_factor':fm,'mu_alpha':float(pval),'mu':fm+float(pval),
      'true_log':r['y'+str(h)],'true_alpha':r[target],'sigma_train':resid_sigma,
      'last_exit':r[exitcol]})
  print('FIT',year,h,'train',len(train),'test',len(test),'factor labels',len(fac[(fac['exit_'+str(h)]<cutoff)&fac['f0_y'+str(h)].notna()]),flush=True)
p=pd.DataFrame(pred)
p.to_csv(ROOT/'PREQUENTIAL_MULTIHORIZON_PREDICTIONS.csv.gz',index=False,compression='gzip')
au=pd.DataFrame(audit);au.to_csv(ROOT/'ANNUAL_LABEL_MATURITY_AUDIT.csv',index=False)
assert (au.dropna(subset=['last_label_exit']).last_label_exit<pd.to_datetime(au.dropna(subset=['last_label_exit']).year.astype(str)+'-01-01')).all()
print('SAVED predictions',len(p),'dates',p.signal_date.nunique(),'models',p.model.unique().tolist(),flush=True)
