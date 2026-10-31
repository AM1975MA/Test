"""Fixed annual direct portfolio-advantage regressions; no parameter search."""
from assets import ROOT,digest
from state import PAIR_FEATURES
from pairmath import mature_mask,monthly_weights
import numpy as np,pandas as pd,joblib,json,hashlib,time,sys
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor

def fit_model(tr,family,h):
    x=tr[PAIR_FEATURES].to_numpy(float);y=tr['y'+str(h)].to_numpy(float);w=monthly_weights(tr.signal_date)
    mean=float(np.average(y,weights=w))
    if family=='RIDGE':
        imp=SimpleImputer(strategy='median',keep_empty_features=True);xx=imp.fit_transform(x)
        scale=StandardScaler().fit(xx,sample_weight=w);xx=scale.transform(xx)
        reg=Ridge(alpha=20).fit(xx,y,sample_weight=w);obj=(imp,scale,reg)
    else:
        obj=HistGradientBoostingRegressor(loss='squared_error',max_iter=120,learning_rate=.05,max_leaf_nodes=15,min_samples_leaf=60,l2_regularization=10,early_stopping=False,random_state=101).fit(x,y,sample_weight=w)
    return obj,mean

def predict(obj,x):
    x=np.asarray(x,float)
    if isinstance(obj,tuple):
        imp,s,reg=obj;return reg.predict(s.transform(imp.transform(x)))
    return obj.predict(x)

def main(market):
    p=pd.read_csv(ROOT/f'results/{market}_PAIRS.csv.gz',parse_dates=['signal_date','entry_date','exit21','exit42','exit63'],float_precision='round_trip')
    out=[];audit=[];t=time.time()
    for year in range(2021,2027):
        cutoff=pd.Timestamp(year,1,1);te=p[p.signal_date.dt.year==year]
        for family in ['RIDGE','HGB']:
            result=te[['key','market','trace','signal_date','entry_date','old_tickers','new_tickers','is_full_proposal','y21','y42','y63','exit21','exit42','exit63']].copy();result['model']=family;result['year']=year
            for h in [21,42,63]:
                tr=p[mature_mask(p.signal_date,p['exit'+str(h)],p['y'+str(h)],cutoff)]
                assert tr.signal_date.nunique()>=18,(market,year,h,tr.signal_date.nunique())
                obj,mu=fit_model(tr,family,h);pr=predict(obj,te[PAIR_FEATURES].to_numpy(float))
                assert np.isfinite(pr).all()
                dest=ROOT/f'models/{market}_{family}_{year}_H{h}.joblib';joblib.dump(obj,dest,compress=3)
                result['pred'+str(h)]=pr;result['mean'+str(h)]=mu
                keys=tr[['key','exit'+str(h)]].to_csv(index=False).encode()
                audit.append(dict(market=market,model=family,year=year,h=h,n=len(tr),months=tr.signal_date.nunique(),last_exit=str(tr['exit'+str(h)].max()),cutoff=str(cutoff),train_keys_sha256=hashlib.sha256(keys).hexdigest(),model_sha256=digest(dest),mean=mu,age_feature_max=float(tr.old_age_max.max()),pred_rows=len(te)))
            out.append(result)
            print('FIT',market,year,family,'training_months',audit[-1]['months'],'elapsed',round(time.time()-t,1),flush=True)
        pd.concat(out).to_csv(ROOT/f'results/{market}_DIRECT_PREDICTIONS.csv.gz',index=False,compression='gzip')
        pd.DataFrame(audit).to_csv(ROOT/f'results/{market}_FIT_AUDIT.csv',index=False)
    print('DONE',market,len(audit),'models',round(time.time()-t,1),flush=True)

if __name__=='__main__':
    for m in sys.argv[1:] or ['EU','USA']:main(m)
