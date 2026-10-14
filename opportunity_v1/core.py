"""Causal helpers for the research-only Opportunity experiment."""
import numpy as np
import pandas as pd

def causal_features(names):
    return [c for c in names if not c.startswith(('target_','fwd_','label_','exit_'))]

def mature_training(panel, cutoff):
    return panel[(panel.signal_date < cutoff) & (panel.label_exit_date_21 < cutoff)
                 & panel.target_excess_max.notna()].copy()

def router_decisions(signals, exits, shadow):
    exits=pd.DatetimeIndex(exits); shadow=np.asarray(shadow,float)
    if not exits.is_monotonic_increasing or len(exits)!=len(shadow):
        raise ValueError('Invalid shadow calendar')
    active=[];counts=[];sums=[]
    for signal in pd.DatetimeIndex(signals):
        mature=shadow[exits <= signal]
        if not np.isfinite(mature).all():raise ValueError('Nonfinite mature shadow')
        value=float(mature[-12:].sum())
        active.append(len(mature)>=12 and value>0)
        counts.append(len(mature));sums.append(value)
    return np.asarray(active,bool),np.asarray(counts,int),np.asarray(sums,float)

def period_shadow(dates, calendar, base_equity, direct_equity):
    dates=pd.DatetimeIndex(dates)
    a=dates.get_indexer(pd.DatetimeIndex(calendar.entry_date))
    e=dates.get_indexer(pd.DatetimeIndex(calendar.exit_date))
    if np.any(a<0) or np.any(e<0) or np.any(e<=a):raise ValueError('Missing shadow dates')
    delta=np.diff(np.r_[0.,np.log(direct_equity)])-np.diff(np.r_[0.,np.log(base_equity)])
    return np.array([delta[start:end].sum() for start,end in zip(a,e)])

def fit_opportunity(panel, features, years):
    from sklearn.impute import SimpleImputer
    from sklearn.ensemble import ExtraTreesRegressor, RandomForestClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    allowed=causal_features(features)
    if len(allowed)!=120 or len(features)-len(allowed)!=2:
        raise ValueError(f'Unexpected original Opportunity predictor contract: {len(allowed)}/{len(features)}')
    predictions=[];audit={}
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        train=mature_training(panel,cutoff)
        test=panel[panel.signal_date.dt.year==year].copy()
        if len(train)<=100 or test.empty:raise ValueError('Missing Opportunity fold')
        im=SimpleImputer(strategy='median')
        X=im.fit_transform(train[allowed]); Xt=im.transform(test[allowed])
        et=ExtraTreesRegressor(n_estimators=300,max_depth=4,min_samples_leaf=30,n_jobs=2,random_state=year).fit(X,train.target_top2)
        rs=make_pipeline(StandardScaler(),Ridge(alpha=100.)).fit(X,train.target_spread)
        re=make_pipeline(StandardScaler(),Ridge(alpha=100.)).fit(X,train.target_excess_max)
        rf=RandomForestClassifier(n_estimators=300,max_depth=3,min_samples_leaf=30,n_jobs=2,class_weight='balanced',random_state=year+1).fit(X,train.target_explosive.astype(int))
        z=test[['signal_date','cluster_id']].copy()
        z['p_top2']=et.predict(Xt);z['p_spread']=rs.predict(Xt);z['p_excess']=re.predict(Xt)
        z['p_explosive']=rf.predict_proba(Xt)[:,1] if len(rf.classes_)>1 else rf.classes_[0]
        for c in ('p_top2','p_spread','p_excess','p_explosive'):
            z[c+'_rank']=z.groupby('signal_date')[c].rank(pct=True)
        z['opp_raw']=.35*z.p_top2_rank+.15*z.p_spread_rank+.35*z.p_excess_rank+.15*z.p_explosive_rank
        z['opp_z']=z.groupby('signal_date').opp_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12))
        predictions.append(z)
        audit[str(year)]={'cutoff':str(cutoff),'rows':len(train),'max_signal':str(train.signal_date.max()),
                          'max_exit':str(train.label_exit_date_21.max()),'test_rows':len(test)}
    return pd.concat(predictions,ignore_index=True),dict(features=allowed,excluded=[c for c in features if c not in allowed],folds=audit)
