#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, sys, math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import ExtraTreesRegressor, RandomForestClassifier
from xgboost import XGBRanker


def load(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); assert spec.loader is not None
    spec.loader.exec_module(mod); return mod


def patch_base(base):
    # Frozen research feature definitions recovered from the 21-Jul/24-Jul sources.
    def cs_robust_dev(df: pd.DataFrame) -> pd.DataFrame:
        med=df.median(axis=1)
        q75=df.quantile(.75,axis=1); q25=df.quantile(.25,axis=1)
        scale=(q75-q25).replace(0,np.nan)
        return df.sub(med,axis=0).div(scale,axis=0).clip(-8,8)
    def rolling_downvol(ret: pd.DataFrame,h:int) -> pd.DataFrame:
        neg=ret.where(ret<0,0.0)
        return np.sqrt(neg.pow(2).rolling(h,min_periods=h).mean()*252.0)
    base.cs_robust_dev=cs_robust_dev
    base.rolling_downvol=rolling_downvol
    return base


def frozen_fit_predict(v5, base, compact, tail, macro, macro_feats, opp, years, n_estimators=360):
    params=dict(base.COMPACT_PARAMS); params['n_estimators']=n_estimators; params['n_jobs']=2
    pred_rows=[]; macro_rows=[]; opp_rows=[]; audit=[]
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        # Original SuperGold protocol: 21-session D+1 open->open target and maturity.
        tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']).copy()
        te=compact[(compact.signal_date.dt.year==year)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']).copy()
        if tr.signal_date.nunique()<60 or te.empty: continue
        groups=tr.groupby('signal_date',sort=False).size().to_numpy(np.int32)
        # Original ranking relevance: deciles 0..9, not rounded percentile*100.
        relevance=np.minimum(9,np.floor(tr.target_rank_pct.to_numpy(float)*10.0-1e-12)).astype(np.int32)
        per_seed=[]
        for seed in [101,202,303]:
            model=XGBRanker(**params,random_state=seed)
            model.fit(tr[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan),relevance,group=groups,verbose=False)
            raw=model.predict(te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan))
            tmp=te[['signal_date','ticker']].copy(); tmp['raw']=raw
            # Frozen seed aggregation: percentile-rank each seed cross-sectionally, then average.
            tmp['pct']=tmp.groupby('signal_date')['raw'].rank(pct=True,method='average')
            per_seed.append(tmp[['signal_date','ticker','pct']].rename(columns={'pct':f'seed_{seed}_pct'}))
        out=per_seed[0]
        for q in per_seed[1:]: out=out.merge(q,on=['signal_date','ticker'],how='inner',validate='one_to_one')
        seed_cols=[f'seed_{s}_pct' for s in [101,202,303]]
        out['compact_rank']=out[seed_cols].mean(axis=1)
        out['compact_raw']=out['compact_rank']

        # TailMix frozen source: 63-session maturity, median imputation, standardization, Ridge alpha 30.
        ttr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()].copy()
        tte=tail[(tail.signal_date.dt.year==year)&tail.y_tailmix.notna()].copy()
        if len(ttr):
            tm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.0)).fit(ttr[base.TAIL_FEATURES],ttr.y_tailmix)
            tp=tte[['signal_date','ticker']].copy(); tp['tail_raw']=tm.predict(tte[base.TAIL_FEATURES])
            tp['tail_rank']=tp.groupby('signal_date').tail_raw.rank(pct=True,method='average')
            out=out.merge(tp,on=['signal_date','ticker'],how='left')
        else:
            out['tail_raw']=np.nan; out['tail_rank']=np.nan
        out['titanium_score_pre_macro']=.70*out.compact_rank+.30*out.tail_rank
        pred_rows.append(out)

        # Macro destination source protocol.
        mtr=macro[(macro.signal_date<cutoff-pd.Timedelta(days=70))&macro.target_rank.notna()].copy()
        mte=macro[macro.signal_date.dt.year==year].copy()
        if len(mtr)>50 and len(mte):
            mm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.0)).fit(mtr[macro_feats],mtr.target_rank)
            q=mte[['signal_date','macro_category']].copy(); q['macro_raw']=mm.predict(mte[macro_feats]); macro_rows.append(q)

        # Opportunity: exact selected feature lists/models already recovered in V5.
        out_opp=opp[opp.signal_date.dt.year==year][['signal_date','cluster_id']].copy()
        for spec in v5.OPPORTUNITY_SPECS:
            feats=spec['features']; target=spec['target']
            otr=opp[(opp.signal_date<cutoff)&(opp.label_exit_date_21<cutoff)&opp[target].notna()].copy()
            ote=opp[opp.signal_date.dt.year==year].copy()
            if len(otr)<100 or ote.empty:
                out_opp[target+'_pred']=np.nan; continue
            if spec['model'].startswith('ET'):
                model=make_pipeline(SimpleImputer(strategy='median'),ExtraTreesRegressor(n_estimators=300,max_depth=4,min_samples_leaf=30,n_jobs=2,random_state=year+11))
            elif spec['model'].startswith('RF'):
                model=make_pipeline(SimpleImputer(strategy='median'),RandomForestClassifier(n_estimators=300,max_depth=3,min_samples_leaf=30,n_jobs=2,class_weight='balanced',random_state=year+17))
            else:
                model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=100.0))
            yy=otr[target].astype(int) if target=='target_explosive' else otr[target]
            model.fit(otr[feats],yy)
            if target=='target_explosive':
                clf=model[-1]; pp=model.predict_proba(ote[feats]); val=pp[:,list(clf.classes_).index(1)] if 1 in clf.classes_ else np.zeros(len(ote))
            else: val=model.predict(ote[feats])
            out_opp[target+'_pred']=val
        opp_rows.append(out_opp)
        audit.append({'year':year,'compact_train_dates':int(tr.signal_date.nunique()),'compact_train_rows':len(tr),'tail_train_rows':len(ttr),'macro_train_rows':len(mtr),'opp_train_rows':len(opp[opp.signal_date<cutoff]),'protocol':'SUPERGOLD_FROZEN_21D_DECILE_SEED_RANKMEAN'})

    p=pd.concat(pred_rows,ignore_index=True)
    # compact_rank/tail_rank already rank-normalized exactly as frozen.
    if 'titanium_score_pre_macro' not in p: p['titanium_score_pre_macro']=.70*p.compact_rank+.30*p.tail_rank
    mp=pd.concat(macro_rows,ignore_index=True) if macro_rows else pd.DataFrame(columns=['signal_date','macro_category','macro_raw'])
    if len(mp):
        mp['macro_z']=mp.groupby('signal_date').macro_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+v5.EPS))
        tops=[]
        for dt,g in mp.groupby('signal_date'):
            g=g.sort_values('macro_z',ascending=False)
            tops.append({'signal_date':dt,'top_macro':g.iloc[0].macro_category,'macro_gap_z':float(g.iloc[0].macro_z-g.iloc[1].macro_z) if len(g)>1 else 0.0})
        p['macro_category']=p.ticker.map(base.TICKER_CATEGORY)
        p=p.merge(pd.DataFrame(tops),on='signal_date',how='left')
        p['macro_bonus']=np.where((p.macro_category==p.top_macro)&(p.macro_gap_z>=.75)&(p.tail_rank>=.80),.15,0.0)
    else:
        p['macro_category']=p.ticker.map(base.TICKER_CATEGORY); p['top_macro']=None; p['macro_gap_z']=np.nan; p['macro_bonus']=0.0
    p['titanium_score']=p.titanium_score_pre_macro+p.macro_bonus

    op=pd.concat(opp_rows,ignore_index=True)
    weights={'target_top2_pred':.35,'target_spread_pred':.15,'target_excess_max_pred':.35,'target_explosive_pred':.15}
    for c in weights: op[c+'_rank']=op.groupby('signal_date')[c].rank(pct=True,method='average')
    op['opp_raw']=sum(w*op[c+'_rank'] for c,w in weights.items())
    op['opp_z']=op.groupby('signal_date').opp_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+v5.EPS))
    return p.sort_values(['signal_date','ticker']),op.sort_values(['signal_date','cluster_id']),pd.DataFrame(audit),mp


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--v5',required=True); ap.add_argument('--base',required=True); ap.add_argument('--data-dir',required=True); ap.add_argument('--output',required=True); ap.add_argument('--fast',action='store_true'); a=ap.parse_args()
    v5=load(Path(a.v5),'v5_frozen_protocol'); base=patch_base(load(Path(a.base),'base_frozen_protocol'))
    v5.load_base=lambda _p: base
    v5.fit_predict=lambda base_,compact,tail,macro,macro_feats,opp,years,n_estimators=360: frozen_fit_predict(v5,base_,compact,tail,macro,macro_feats,opp,years,n_estimators)
    sys.argv=[Path(a.v5).name,'--base-module',a.base,'--data-dir',a.data_dir,'--output',a.output]+(['--fast'] if a.fast else [])
    v5.main()

if __name__=='__main__': main()
