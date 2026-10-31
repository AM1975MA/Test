"""Annual separately matured segment models. Fixed hyperparameters, no tuning."""
from common import ROOT,digest
from prepare import FEATURES
from lifecycle_math import mature_mask
import numpy as np,pandas as pd,json,time,sys,joblib
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor

def fit_one(train, test, family, head):
    x=train[FEATURES].to_numpy();xt=test[FEATURES].to_numpy();y=train[f'y{head}'].to_numpy()
    w=1/train.groupby('signal_date').signal_date.transform('count').to_numpy()
    if family=='RIDGE':
        imp=SimpleImputer(strategy='median',keep_empty_features=True);a=imp.fit_transform(x);b=imp.transform(xt)
        scaler=StandardScaler().fit(a,sample_weight=w);a=scaler.transform(a);b=scaler.transform(b)
        model=Ridge(alpha=20).fit(a,y,sample_weight=w)
        pr=model.predict(b);obj=(imp,scaler,model)
    else:
        model=HistGradientBoostingRegressor(loss='squared_error',max_iter=120,learning_rate=.05,max_leaf_nodes=15,min_samples_leaf=60,l2_regularization=10,early_stopping=False,random_state=101)
        model.fit(x,y,sample_weight=w);pr=model.predict(xt);obj=model
    return pr,obj,float(np.average(y,weights=w)),float(np.average((y-np.average(y,weights=w))**2,weights=w))

def main(market):
    started=time.time();p=pd.read_pickle(ROOT/f'inputs/{market}_PANEL.pkl')
    out=ROOT/'results';md=out/'models';md.mkdir(exist_ok=True);rows=[];aud=[]
    for year in range(2021,2027):
        cutoff=pd.Timestamp(year,1,1);te=p[p.signal_date.dt.year==year].copy()
        for family in ['RIDGE','HGB']:
            res=te[['market','signal_date','entry_date','source_date','ticker','ticker_idx','y1','y2','y3','exit1','exit2','exit3']].copy()
            res['model']=family;res['fit_year']=year
            for head in [1,2,3]:
                tr=p[mature_mask(p.signal_date,p[f'exit{head}'],p[f'y{head}'],cutoff)].copy()
                assert tr.signal_date.nunique()>=18
                pr,obj,mean,var=fit_one(tr,te,family,head)
                assert np.isfinite(pr).all()
                dest=md/f'{market}_{family}_{year}_S{head}.joblib';joblib.dump(obj,dest,compress=3)
                res[f'mu{head}']=pr;res[f'control_mean{head}']=mean
                keys=tr[['signal_date','ticker',f'exit{head}']].to_csv(index=False)
                import hashlib
                aud.append(dict(market=market,model=family,year=year,head=head,n=len(tr),months=tr.signal_date.nunique(),max_label_exit=str(tr[f'exit{head}'].max()),cutoff=str(cutoff),keys_hash=hashlib.sha256(keys.encode()).hexdigest(),prediction_rows=len(te),train_mean=mean,train_variance=var,model_sha256=digest(dest)))
            rows.append(res)
            print('FIT',market,year,family,'predict',len(te),'sec',round(time.time()-started,1),flush=True)
        pd.concat(rows).to_csv(out/f'{market}_PREDICTIONS.csv.gz',index=False,compression='gzip')
        pd.DataFrame(aud).to_csv(out/f'{market}_FIT_AUDIT.csv',index=False)
    print('COMPLETE',market,len(aud),flush=True)
if __name__=='__main__':
    for m in sys.argv[1:] or ['EU','USA']:main(m)
