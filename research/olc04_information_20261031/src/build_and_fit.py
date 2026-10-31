"""Matched feature ablation: fixed rows/targets/models, additional past information only."""
import setup_paths
from setup_paths import ROOT,OLC2
from assets import Assets,PARENT
from state import PAIR_FEATURES
from pairmath import mature_mask,monthly_weights
from relative_information import Information,EXTRA_NAMES,REL_NAMES
from train_pairs import predict
import numpy as np,pandas as pd,joblib,json,hashlib,time,sys
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
SETS={'OLD':PAIR_FEATURES,'REL':PAIR_FEATURES+REL_NAMES,'PEER':PAIR_FEATURES+EXTRA_NAMES}
def fit(tr,fam,h,features):
 x=tr[features].to_numpy(float);y=tr[f'y{h}'].to_numpy(float);w=monthly_weights(tr.signal_date)
 if fam=='RIDGE':
  im=SimpleImputer(strategy='median',keep_empty_features=True);xx=im.fit_transform(x)
  sc=StandardScaler().fit(xx,sample_weight=w);xx=sc.transform(xx)
  obj=(im,sc,Ridge(alpha=20).fit(xx,y,sample_weight=w))
 else:
  obj=HistGradientBoostingRegressor(loss='squared_error',max_iter=120,learning_rate=.05,max_leaf_nodes=15,min_samples_leaf=60,l2_regularization=10,early_stopping=False,random_state=101).fit(x,y,sample_weight=w)
 return obj,float(np.average(y,weights=w))
def run(market):
 start=time.time()
 for m in json.loads((OLC2/'PARENT_INPUTS.json').read_text())['files']:
  path=PARENT/m['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==m['sha256'],str(path)
 a=Assets(market);close=pd.read_pickle(PARENT/f'inputs/{market}_Close.pkl').reindex(columns=a.score.columns);info=Information(close)
 p=pd.read_csv(OLC2/f'results/{market}_PAIRS.csv.gz',parse_dates=['signal_date','entry_date','exit21','exit42','exit63'],float_precision='round_trip')
 extras=[]
 for row in p.itertuples(index=False):
  old=np.zeros(a.N);new=np.zeros(a.N);ids=list(map(int,row.old_ids.split('|')))
  old[ids]=list(map(float,row.old_weights.split('|')));new[list(map(int,row.new_ids.split('|')))]=.5
  extras.append(info.values(row.signal_date,old,new))
 p=pd.concat([p,pd.DataFrame(extras,columns=EXTRA_NAMES)],axis=1)
 p.to_csv(ROOT/f'results/{market}_AUGMENTED_PAIRS.csv.gz',index=False,compression='gzip')
 pd.DataFrame({'feature':EXTRA_NAMES,'finite_fraction':np.isfinite(extras).mean(axis=0)}).to_csv(ROOT/f'results/{market}_FEATURE_COVERAGE.csv',index=False)
 peerrows=[]
 for d,(_,pc,peers) in info.cache.items():
  for j,ids in enumerate(peers):peerrows.append(dict(signal_date=d,ticker=a.names[j],peers='|'.join(a.names[k] for k in ids),n_peers=len(ids),finite_features=int(np.isfinite(pc[j]).sum())))
 pd.DataFrame(peerrows).to_csv(ROOT/f'results/{market}_PEERS.csv.gz',index=False,compression='gzip')
 oldpred=pd.read_csv(OLC2/f'results/{market}_DIRECT_PREDICTIONS.csv.gz',parse_dates=['signal_date'],float_precision='round_trip')
 audits=[];preds=[];par=[];(ROOT/'models').mkdir(exist_ok=True)
 for year in range(2021,2027):
  cutoff=pd.Timestamp(year,1,1);te=p[p.signal_date.dt.year==year]
  for name in ['OLD','REL','PEER']:
   for fam in ['RIDGE','HGB']:
    r=te[['key','market','trace','signal_date','entry_date','old_tickers','new_tickers','is_full_proposal','y21','y42','y63','exit21','exit42','exit63']].copy();r['feature_set']=name;r['model']=fam;r['year']=year
    for h in [21,42,63]:
     tr=p[mature_mask(p.signal_date,p[f'exit{h}'],p[f'y{h}'],cutoff)];assert tr[f'exit{h}'].max()<cutoff
     if name=='OLD':
      obj=joblib.load(OLC2/f'models/{market}_{fam}_{year}_H{h}.joblib');mu=float(np.average(tr[f'y{h}'],weights=monthly_weights(tr.signal_date)))
     else:
      obj,mu=fit(tr,fam,h,SETS[name]);joblib.dump(obj,ROOT/f'models/{market}_{name}_{fam}_{year}_H{h}.joblib',compress=3)
     pr=predict(obj,te[SETS[name]].to_numpy(float));assert np.isfinite(pr).all();r[f'pred{h}']=pr;r[f'mean{h}']=mu
     if name=='OLD':
      ref=oldpred[(oldpred.year==year)&(oldpred.model==fam)].set_index('key').loc[te.key,f'pred{h}'].to_numpy();err=float(np.max(abs(pr-ref)));assert err<1e-12;par.append(dict(year=year,model=fam,h=h,prediction_error=err))
     audits.append(dict(market=market,feature_set=name,model=fam,year=year,h=h,rows=len(tr),months=tr.signal_date.nunique(),last_exit=str(tr[f'exit{h}'].max()),cutoff=str(cutoff),train_keys_sha256=hashlib.sha256(tr[['key',f'exit{h}']].to_csv(index=False).encode()).hexdigest(),age_feature_max=float(tr.old_age_max.max()),n_features=len(SETS[name]),mean=mu,new_fit=name!='OLD'))
    preds.append(r)
   print('FIT',market,year,name,'elapsed',round(time.time()-start,1),flush=True)
  pd.DataFrame(audits).to_csv(ROOT/f'results/{market}_FIT_AUDIT.csv',index=False);pd.concat(preds).to_csv(ROOT/f'results/{market}_PREDICTIONS.csv.gz',index=False,compression='gzip')
 pd.DataFrame(par).to_csv(ROOT/f'results/{market}_OLD_PREDICTION_PARITY.csv',index=False)
 print('COMPLETE',market,len(audits),'head records',round(time.time()-start,1),flush=True)
if __name__=='__main__':
 for market in sys.argv[1:] or ['EU','USA']:run(market)
