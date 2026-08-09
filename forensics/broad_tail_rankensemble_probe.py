#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRanker


def load(path):
    spec=importlib.util.spec_from_file_location('broad_probe_impl',path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

m=load('forensics/broad_tail_parity_probe.py')


def fit_all_rankensemble(base, compact, tail, macro, macro_feats, years, n_estimators):
    params=dict(base.COMPACT_PARAMS); params['n_estimators']=n_estimators; params['n_jobs']=2
    preds=[]; macros=[]; audits=[]
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker'])
        te=compact[compact.signal_date.dt.year.eq(year)].sort_values(['signal_date','ticker'])
        if tr.signal_date.nunique()<60 or te.empty: continue
        groups=tr.groupby('signal_date',sort=True).size().tolist(); y=(tr.target_rank_pct*100).round().astype(int)
        raw_list=[]; rank_list=[]
        for seed in base.COMPACT_SEEDS:
            model=XGBRanker(**params,random_state=seed)
            model.fit(tr[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan),y,group=groups,verbose=False)
            raw=model.predict(te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan))
            raw_list.append(raw)
            tmp=pd.DataFrame({'signal_date':te.signal_date.to_numpy(),'raw':raw})
            rank_list.append(tmp.groupby('signal_date').raw.rank(pct=True).to_numpy())
        q=te[['signal_date','ticker']].copy()
        q['compact_raw']=np.mean(raw_list,axis=0)
        # Exact production order: rank EACH seed cross-sectionally, THEN average ranks.
        q['compact_rank']=np.mean(rank_list,axis=0)

        ttr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()]
        tte=tail[tail.signal_date.dt.year.eq(year)]
        tm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.0))
        tm.fit(ttr[base.TAIL_FEATURES],ttr.y_tailmix)
        tq=tte[['signal_date','ticker']].copy(); tq['tail_raw']=tm.predict(tte[base.TAIL_FEATURES])
        preds.append(q.merge(tq,on=['signal_date','ticker'],how='left'))

        mtr=macro[(macro.signal_date<cutoff-pd.Timedelta(days=70))&macro.target_rank.notna()]
        mte=macro[macro.signal_date.dt.year.eq(year)]
        if len(mtr)>50 and len(mte):
            mm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.0))
            mm.fit(mtr[macro_feats],mtr.target_rank)
            mq=mte[['signal_date','macro_category']].copy(); mq['macro_raw']=mm.predict(mte[macro_feats]); macros.append(mq)
        audits.append({'year':year,'compact_train_rows':len(tr),'tail_train_rows':len(ttr),'macro_train_rows':len(mtr)})
    p=pd.concat(preds,ignore_index=True)
    p['tail_rank']=p.groupby('signal_date').tail_raw.rank(pct=True)
    p['titanium_score_pre_macro']=.70*p.compact_rank+.30*p.tail_rank
    mp=pd.concat(macros,ignore_index=True)
    mp['macro_z']=mp.groupby('signal_date').macro_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12))
    tops=[]
    for dt,g in mp.groupby('signal_date'):
        g=g.sort_values('macro_z',ascending=False)
        tops.append({'signal_date':dt,'top_macro':g.iloc[0].macro_category,'macro_gap_z':float(g.iloc[0].macro_z-g.iloc[1].macro_z) if len(g)>1 else 0.0})
    p['macro_category']=p.ticker.map(base.TICKER_CATEGORY)
    p=p.merge(pd.DataFrame(tops),on='signal_date',how='left')
    p['macro_bonus']=np.where((p.macro_category==p.top_macro)&(p.macro_gap_z>=.75)&(p.tail_rank>=.80),.15,0.0)
    p['titanium_score']=p.titanium_score_pre_macro+p.macro_bonus
    return p.sort_values(['signal_date','ticker']),pd.DataFrame(audits),mp

m.fit_all=fit_all_rankensemble
m.main()
