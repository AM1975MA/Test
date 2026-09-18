"""Annual prequential models; explicit label maturity and training-only transforms."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
from xgboost import XGBRanker
from .features import GROUPS

def fit_predict(k,compact,tail,macro,mfeatures,extra,out,years=range(2017,2027)):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    frame=compact.merge(extra,on=['signal_date','ticker'],validate='one_to_one')
    predictions=[]; audit=[]; eligibility=[]
    for year in years:
        cached=out/f'scores_{year}.csv'
        if cached.exists():
            # Cached predictions are derived acceleration only.  They are accepted
            # only when the corresponding causal fit audit exists; otherwise fail closed.
            audit_file=out/f'fit_audit_{year}.json'
            if not audit_file.exists():
                raise RuntimeError(f'cached scores without causal fit audit: {cached}')
            predictions.append(pd.read_csv(cached,parse_dates=['signal_date','entry_date','exit_date']))
            continue
        cutoff=pd.Timestamp(year,1,1)
        valid=frame[k.F2D_FEATURES].notna().sum(axis=1)>=30
        tr=frame[(frame.signal_date<cutoff)&(frame.exit_date_21<cutoff)&frame.target_rank_pct.notna()&valid].sort_values(['signal_date','ticker'])
        te=frame[(frame.signal_date.dt.year==year)&valid].sort_values(['signal_date','ticker'])
        if te.empty:
            eligibility.append({'year':year,'status':'SKIP_NO_TEST_ROWS','train_signal_dates':int(tr.signal_date.nunique())})
            continue
        n_train_dates=int(tr.signal_date.nunique())
        if n_train_dates<60:
            # A short raw vintage cannot support the recovered ranker minimum.
            # Skip the year rather than weakening the model or backfilling scores.
            eligibility.append({'year':year,'status':'SKIP_INSUFFICIENT_MATURE_HISTORY','train_signal_dates':n_train_dates,'required':60})
            continue
        eligibility.append({'year':year,'status':'FIT','train_signal_dates':n_train_dates})
        assert (tr.exit_date_21<cutoff).all()
        if not (tr.signal_date < cutoff).all():
            raise RuntimeError(f'look-ahead: compact signal_date reaches fit cutoff {year}')
        o=te[['signal_date','ticker','entry_date','exit_date']].copy()
        for horizon in [21,63]:
            train=tr if horizon==21 else frame[(frame.signal_date<cutoff)&(frame.exit_date_63<cutoff)&frame.target_rank_63.notna()&valid].sort_values(['signal_date','ticker'])
            if not (train.signal_date < cutoff).all() or not (train[f'exit_date_{horizon}'] < cutoff).all():
                raise RuntimeError(f'look-ahead: immature compact{horizon} label in fit year {year}')
            y=(train[f'target_rank_{horizon}']*100).round().astype(int)
            groups=train.groupby('signal_date',sort=True).size().to_numpy()
            pp=[]
            for seed in k.COMPACT_SEEDS:
                model=XGBRanker(**k.COMPACT_PARAMS,random_state=seed)
                model.fit(train[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan),y,group=groups,verbose=False)
                pp.append(model.predict(te[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)))
            o[f'compact{horizon}']=np.mean(pp,axis=0)
            audit.append({'year':year,'model':f'compact{horizon}','train_rows':len(train),'max_exit':str(train[f'exit_date_{horizon}'].max()),'fit_date':str(cutoff)})
        # Independently regularized predictors test incremental information.
        for group,features in {**GROUPS,'all':sum(GROUPS.values(),[])}.items():
            model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=100.))
            model.fit(tr[features],tr.target_rank_pct)
            o[group]=model.predict(te[features])
        tv=tail[k.TAIL_FEATURES].notna().sum(axis=1)>=12
        ttr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()&tv]
        tte=tail[(tail.signal_date.dt.year==year)&tv]
        if not (ttr.signal_date < cutoff).all() or not (ttr.exit_date_63 < cutoff).all():
            raise RuntimeError(f'look-ahead: immature tail label in fit year {year}')
        model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.))
        model.fit(ttr[k.TAIL_FEATURES],ttr.y_tailmix)
        t=tte[['signal_date','ticker']].copy(); t['tail']=model.predict(tte[k.TAIL_FEATURES])
        o=o.merge(t,on=['signal_date','ticker'],validate='one_to_one')
        mtr=macro[(macro.signal_date<cutoff)&(macro.label_exit_date_63<cutoff)&macro.target_rank.notna()]
        mte=macro[macro.signal_date.dt.year==year]
        if not (mtr.signal_date < cutoff).all() or not (mtr.label_exit_date_63 < cutoff).all():
            raise RuntimeError(f'look-ahead: immature macro label in fit year {year}')
        model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.))
        model.fit(mtr[mfeatures],mtr.target_rank)
        q=mte[['signal_date','macro_category']].copy();q['raw']=model.predict(mte[mfeatures])
        q['z']=q.groupby('signal_date').raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12))
        records=[]
        for dt,g in q.groupby('signal_date'):
            g=g.sort_values(['z','macro_category'],ascending=[False,True]);records.append({'signal_date':dt,'top_macro':g.iloc[0].macro_category,'macro_gap':g.iloc[0].z-g.iloc[1].z})
        o=o.merge(pd.DataFrame(records),on='signal_date');o['macro_category']=o.ticker.map(k.TICKER_CATEGORY)
        audit.extend([{'year':year,'model':'tail','max_exit':str(ttr.exit_date_63.max()),'fit_date':str(cutoff)},
                      {'year':year,'model':'macro','max_exit':str(mtr.label_exit_date_63.max()),'fit_date':str(cutoff)}])
        o.to_csv(cached,index=False);predictions.append(o)
        (out/f'fit_audit_{year}.json').write_text(json.dumps([a for a in audit if a['year']==year],indent=2))
        print('FIT_YEAR_COMPLETE',year,len(o),flush=True)
    (out/'eligibility_audit.json').write_text(json.dumps(eligibility,indent=2))
    if not predictions:
        raise RuntimeError('no annual model has at least 60 mature monthly training signals')
    return pd.concat(predictions,ignore_index=True)

def variants(pred):
    p=pred.copy()
    for col in ['compact21','compact63','tail',*GROUPS,'all']:
        p[col]=p.groupby('signal_date')[col].rank(method='average',pct=True)
    mix=.7*p.compact21+.3*p['tail']
    condition=(p.macro_category==p.top_macro)&(p.macro_gap>=.75)
    historical=mix+.15*(condition&(p['tail']>=.8))
    out={'baseline':historical,'macro_rule':mix+.15*(condition&(mix>=.8)),
         'compact_only':p.compact21,'blend85':.85*p.compact21+.15*p['tail'],
         'horizon63':.7*p.compact63+.3*p['tail']+.15*(condition&(p['tail']>=.8))}
    for group in [*GROUPS,'all']:
        out[group]=.8*historical+.2*p[group]
    panels={}
    for name,values in out.items():
        q=p[['signal_date','ticker']].copy();q['score']=values.groupby(p.signal_date).rank(method='average',pct=True);panels[name]=q
    return panels
