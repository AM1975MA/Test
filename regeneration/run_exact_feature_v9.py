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


def exact_compact_wrapper(base):
    old_build=base.build_features
    def build_features(mats):
        dates,compact_long,tail_long,D=old_build(mats)
        O,H,L,C,V=[mats[k] for k in ['Open','High','Low','Close','Volume']]
        logp=np.log(C.where(C>0)); logret=logp.diff(); prev=C.shift(1)
        exact={}
        for w in [5,10,21,42,63,126,252]:
            exact[f'mom{w}']=base.snapshot(logp-logp.shift(w),dates)
        for w in [21,63,126]:
            minp=max(10,int(w*.75))
            exact[f'vol{w}']=base.snapshot(logret.rolling(w,min_periods=minp).std(ddof=0)*math.sqrt(252.0),dates)
            neg=logret.where(logret<0,0.0)
            exact[f'downvol{w}']=base.snapshot(neg.rolling(w,min_periods=minp).std(ddof=0)*math.sqrt(252.0),dates)
            rollmax=C.rolling(w,min_periods=minp).max()
            exact[f'drawdown{w}']=base.snapshot(C/rollmax-1.0,dates)
            path=logp.diff().abs().rolling(w,min_periods=minp).sum()
            exact[f'efficiency{w}']=base.snapshot((logp-logp.shift(w)).abs()/path.replace(0,np.nan),dates)
        exact['mom126_ex21']=base.snapshot(logp.shift(21)-logp.shift(126),dates)
        exact['mom252_ex21']=base.snapshot(logp.shift(21)-logp.shift(252),dates)
        exact['acc_mom_5_21']=exact['mom5']-(5.0/16.0)*base.snapshot(logp.shift(5)-logp.shift(21),dates)
        exact['acc_mom_21_63']=exact['mom21']-.5*base.snapshot(logp.shift(21)-logp.shift(63),dates)
        exact['vol_ratio_21_126']=np.log(exact['vol21']/exact['vol126'].replace(0,np.nan))
        exact['skew63']=base.snapshot(logret.rolling(63,min_periods=45).skew(),dates)
        exact['kurt63']=base.snapshot(logret.rolling(63,min_periods=45).kurt(),dates)
        hl=np.log(H.where(H>0)/L.where(L>0)); co=np.log(C.where(C>0)/O.where(O>0))
        gk=(.5*hl.pow(2)-(2.0*np.log(2.0)-1.0)*co.pow(2)).clip(lower=0)
        exact['gkvol21']=base.snapshot(np.sqrt(gk.rolling(21,min_periods=15).mean()*252.0),dates)
        dollar=C*V
        exact['log_adv63']=base.snapshot(np.log(dollar.rolling(63,min_periods=42).median().where(lambda x:x>0)),dates)
        exact['volume_surprise21']=base.snapshot(np.log(V.rolling(21,min_periods=15).mean()/V.rolling(63,min_periods=42).median().replace(0,np.nan)),dates)
        market='SPY' if 'SPY' in logret.columns else logret.columns[0]; mret=logret[market]
        for w in [63,126]:
            minp=int(w*.75); cov=logret.rolling(w,min_periods=minp).cov(mret); var=mret.rolling(w,min_periods=minp).var(ddof=0)
            exact[f'beta_mkt{w}']=base.snapshot(cov.div(var.replace(0,np.nan),axis=0),dates)
            exact[f'corr_mkt{w}']=base.snapshot(logret.rolling(w,min_periods=minp).corr(mret),dates)
        # Frozen panel transform: percentile rank + raw deviation from same-date median.
        x=compact_long.set_index(['signal_date','ticker']).copy()
        for name,frame in exact.items():
            s=frame.stack(dropna=False); s.index.names=['signal_date','ticker']
            if name in x.columns: x[name]=s.reindex(x.index).to_numpy()
            pn=name+'_pct'; dn=name+'_dev'
            if pn in x.columns:
                r=frame.rank(axis=1,pct=True,method='average').stack(dropna=False); r.index.names=['signal_date','ticker']; x[pn]=r.reindex(x.index).to_numpy()
            if dn in x.columns:
                dev=frame.sub(frame.median(axis=1),axis=0).stack(dropna=False); dev.index.names=['signal_date','ticker']; x[dn]=dev.reindex(x.index).to_numpy()
        compact_long=x.reset_index()
        # Keep TailMix dictionary internally consistent for shared exact features/ranks.
        aliases={
            'beta_mkt63':'beta_mkt63','beta_mkt126':'beta_mkt126','corr_mkt63':'corr_mkt63','corr_mkt126':'corr_mkt126',
            'gkvol21':'gkvol21','max_gain63':'max_gain63','positive_frac63':'positive_frac63'
        }
        for k,v in exact.items():
            if k in D: D[k]=v
        for key in list(D):
            if key.endswith('_rank'):
                raw=key[:-5]
                if raw in D: D[key]=D[raw].rank(axis=1,pct=True,method='average')
        return dates,compact_long,tail_long,D
    base.build_features=build_features
    return base


def frozen_fit_predict(v5,base,compact,tail,macro,macro_feats,opp,years,n_estimators=360):
    params=dict(base.COMPACT_PARAMS); params.update(n_estimators=n_estimators,n_jobs=2)
    pred_rows=[]; macro_rows=[]; opp_rows=[]; audit=[]
    for year in years:
        cut=pd.Timestamp(year,1,1)
        tr=compact[(compact.signal_date<cut)&(compact.exit_date_21<cut)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']).copy()
        te=compact[(compact.signal_date.dt.year==year)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']).copy()
        if tr.signal_date.nunique()<60 or te.empty: continue
        groups=tr.groupby('signal_date',sort=False).size().to_numpy(np.int32)
        rel=np.minimum(9,np.floor(tr.target_rank_pct.to_numpy(float)*10.0-1e-12)).astype(np.int32)
        z=None
        for seed in [101,202,303]:
            m=XGBRanker(**params,random_state=seed); m.fit(tr[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan),rel,group=groups,verbose=False)
            q=te[['signal_date','ticker']].copy(); q[f'seed_{seed}']=m.predict(te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)); q[f'pct_{seed}']=q.groupby('signal_date')[f'seed_{seed}'].rank(pct=True,method='average')
            q=q[['signal_date','ticker',f'pct_{seed}']]; z=q if z is None else z.merge(q,on=['signal_date','ticker'],how='inner')
        z['compact_rank']=z[[f'pct_{s}' for s in [101,202,303]]].mean(axis=1); z['compact_raw']=z.compact_rank
        ttr=tail[(tail.signal_date<cut)&(tail.exit_date_63<cut)&tail.y_tailmix.notna()].copy(); tte=tail[(tail.signal_date.dt.year==year)&tail.y_tailmix.notna()].copy()
        if len(ttr):
            tm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.0)).fit(ttr[base.TAIL_FEATURES],ttr.y_tailmix)
            tq=tte[['signal_date','ticker']].copy(); tq['tail_raw']=tm.predict(tte[base.TAIL_FEATURES]); tq['tail_rank']=tq.groupby('signal_date').tail_raw.rank(pct=True,method='average'); z=z.merge(tq,on=['signal_date','ticker'],how='left')
        else: z['tail_raw']=np.nan; z['tail_rank']=np.nan
        z['titanium_score_pre_macro']=.70*z.compact_rank+.30*z.tail_rank; pred_rows.append(z)
        mtr=macro[(macro.signal_date<cut-pd.Timedelta(days=70))&macro.target_rank.notna()].copy(); mte=macro[macro.signal_date.dt.year==year].copy()
        if len(mtr)>50 and len(mte):
            mm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.0)).fit(mtr[macro_feats],mtr.target_rank)
            q=mte[['signal_date','macro_category']].copy(); q['macro_raw']=mm.predict(mte[macro_feats]); macro_rows.append(q)
        oo=opp[opp.signal_date.dt.year==year][['signal_date','cluster_id']].copy()
        for spec in v5.OPPORTUNITY_SPECS:
            feats,target=spec['features'],spec['target']; otr=opp[(opp.signal_date<cut)&(opp.label_exit_date_21<cut)&opp[target].notna()]; ote=opp[opp.signal_date.dt.year==year]
            if len(otr)<100 or ote.empty: oo[target+'_pred']=np.nan; continue
            if spec['model'].startswith('ET'): model=make_pipeline(SimpleImputer(strategy='median'),ExtraTreesRegressor(n_estimators=300,max_depth=4,min_samples_leaf=30,n_jobs=2,random_state=year+11))
            elif spec['model'].startswith('RF'): model=make_pipeline(SimpleImputer(strategy='median'),RandomForestClassifier(n_estimators=300,max_depth=3,min_samples_leaf=30,n_jobs=2,class_weight='balanced',random_state=year+17))
            else: model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=100.0))
            yy=otr[target].astype(int) if target=='target_explosive' else otr[target]; model.fit(otr[feats],yy)
            if target=='target_explosive':
                clf=model[-1]; pp=model.predict_proba(ote[feats]); val=pp[:,list(clf.classes_).index(1)] if 1 in clf.classes_ else np.zeros(len(ote))
            else: val=model.predict(ote[feats])
            oo[target+'_pred']=val
        opp_rows.append(oo); audit.append({'year':year,'compact_train_dates':tr.signal_date.nunique(),'compact_train_rows':len(tr),'protocol':'EXACT_PLATINUM_FEATURES_21D_DECILES_SEED_RANKMEAN'})
    p=pd.concat(pred_rows,ignore_index=True); mp=pd.concat(macro_rows,ignore_index=True) if macro_rows else pd.DataFrame(columns=['signal_date','macro_category','macro_raw'])
    if len(mp):
        mp['macro_z']=mp.groupby('signal_date').macro_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+v5.EPS)); tops=[]
        for dt,g in mp.groupby('signal_date'):
            g=g.sort_values('macro_z',ascending=False); tops.append({'signal_date':dt,'top_macro':g.iloc[0].macro_category,'macro_gap_z':float(g.iloc[0].macro_z-g.iloc[1].macro_z) if len(g)>1 else 0.0})
        p['macro_category']=p.ticker.map(base.TICKER_CATEGORY); p=p.merge(pd.DataFrame(tops),on='signal_date',how='left'); p['macro_bonus']=np.where((p.macro_category==p.top_macro)&(p.macro_gap_z>=.75)&(p.tail_rank>=.80),.15,0.0)
    else: p['macro_category']=p.ticker.map(base.TICKER_CATEGORY); p['top_macro']=None; p['macro_gap_z']=np.nan; p['macro_bonus']=0.0
    p['titanium_score']=p.titanium_score_pre_macro+p.macro_bonus
    op=pd.concat(opp_rows,ignore_index=True); weights={'target_top2_pred':.35,'target_spread_pred':.15,'target_excess_max_pred':.35,'target_explosive_pred':.15}
    for c in weights: op[c+'_rank']=op.groupby('signal_date')[c].rank(pct=True,method='average')
    op['opp_raw']=sum(w*op[c+'_rank'] for c,w in weights.items()); op['opp_z']=op.groupby('signal_date').opp_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+v5.EPS))
    return p.sort_values(['signal_date','ticker']),op.sort_values(['signal_date','cluster_id']),pd.DataFrame(audit),mp


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--v5',required=True); ap.add_argument('--base',required=True); ap.add_argument('--data-dir',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
    v5=load(Path(a.v5),'v5_exact_feature'); base=exact_compact_wrapper(load(Path(a.base),'base_exact_feature')); v5.load_base=lambda _:base
    v5.fit_predict=lambda base_,compact,tail,macro,macro_feats,opp,years,n_estimators=360:frozen_fit_predict(v5,base_,compact,tail,macro,macro_feats,opp,years,n_estimators)
    sys.argv=[Path(a.v5).name,'--base-module',a.base,'--data-dir',a.data_dir,'--output',a.output]; v5.main()

if __name__=='__main__': main()
