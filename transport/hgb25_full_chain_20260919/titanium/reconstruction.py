#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from numba import njit, prange
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import ExtraTreesRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import adjusted_rand_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRanker

EPS = 1e-12
BACKTEST_START = pd.Timestamp('2017-01-31')
COST = 0.001
STOP = 0.055
STOP_SLIP = 0.001
N_BASKETS = 500
BASKET_SEED = 20260721
MODEL_SEEDS = [101, 202, 303]

# Exact source specification recovered from the frozen standalone engine.
OPPORTUNITY_SPECS = [
 {'target':'target_top2','model':'ET_D4_L30','features':['mom252_std_rank','mom252_std','resid_cluster_mom21_p75_rank','resid_cluster_mom21_p75','trend_slope63_std_rank','trend_slope63_std','acc_mom_5_21_std','acc_mom_5_21_std_rank','trend_slope21_std','trend_slope21_std_rank','mom63_std','mom63_std_rank','resid_cluster_mom63_std','resid_cluster_mom63_std_rank','ctx_cluster_disp63_p75_rank','ctx_cluster_disp63_mean_rank','ctx_cluster_disp63_mean','ctx_cluster_disp63_p75','ctx_cluster_disp63_max','ctx_cluster_disp63_max_rank','mom21_std','mom21_std_rank','resid_cluster_mom63_p75_rank','resid_cluster_mom63_p75','intraday_mom21_std_rank','intraday_mom21_std','resid_cluster_mom21_std','resid_cluster_mom21_std_rank','mom126_std','mom126_std_rank','downvol21_std','downvol21_std_rank','acc_mom_21_63_std','acc_mom_21_63_std_rank','max_loss21_std','max_loss21_std_rank','vol63_p75','vol63_p75_rank','max_gain63_max','max_gain63_max_rank','cluster_is_0','cluster_is_1','cluster_is_2','cluster_is_3','cluster_is_4','cluster_is_5','cluster_is_6','cluster_is_7']},
 {'target':'target_spread','model':'RIDGE_A100','features':['mom252_std_rank','mom252_std','acc_mom_5_21_std_rank','acc_mom_5_21_std','trend_slope63_std_rank','trend_slope63_std','mom126_std_rank','mom126_std','mom63_std','mom63_std_rank','ctx_cluster_disp63_max','ctx_cluster_disp63_p75','ctx_cluster_disp63_p75_rank','ctx_cluster_disp63_mean_rank','ctx_cluster_disp63_max_rank','ctx_cluster_disp63_mean','mom21_std_rank','mom21_std','resid_cluster_mom21_std_rank','resid_cluster_mom21_std','trend_slope21_std','trend_slope21_std_rank','resid_cluster_mom63_std_rank','resid_cluster_mom63_std','cvar10_63_std','cvar10_63_std_rank','vol63_std_rank','vol63_std','downvol21_std_rank','downvol21_std','vol63_max','vol63_max_rank','acc_mom_21_63_std','acc_mom_21_63_std_rank','vol21_max_rank','vol21_max','max_loss21_std_rank','max_loss21_std','resid_cluster_mom21_p75_rank','resid_cluster_mom21_p75','cluster_is_0','cluster_is_1','cluster_is_2','cluster_is_3','cluster_is_4','cluster_is_5','cluster_is_6','cluster_is_7']},
 {'target':'target_excess_max','model':'RIDGE_A100','features':['mom252_std_rank','mom252_std','acc_mom_5_21_std_rank','acc_mom_5_21_std','trend_slope63_std_rank','trend_slope63_std','mom126_std_rank','mom126_std','mom63_std','mom63_std_rank','ctx_cluster_disp63_max','ctx_cluster_disp63_p75','ctx_cluster_disp63_p75_rank','ctx_cluster_disp63_mean_rank','ctx_cluster_disp63_max_rank','ctx_cluster_disp63_mean','cvar10_63_std','cvar10_63_std_rank','vol63_std','vol63_std_rank','downvol21_std_rank','downvol21_std','mom21_std','mom21_std_rank','resid_cluster_mom21_std','resid_cluster_mom21_std_rank','max_loss21_std_rank','max_loss21_std','vol63_max_rank','vol63_max','trend_slope21_std_rank','trend_slope21_std','resid_cluster_mom63_std_rank','resid_cluster_mom63_std','gap_mom21_std','gap_mom21_std_rank','vol21_max','vol21_max_rank','downvol21_max_rank','downvol21_max','acc_mom_21_63_std','acc_mom_21_63_std_rank','max_gain63_max_rank','max_gain63_max','resid_cluster_mom21_p75','resid_cluster_mom21_p75_rank','resid_cluster_mom63_p75_rank','resid_cluster_mom63_p75','max_gain63_std_rank','max_gain63_std','vol63_p75_rank','vol63_p75','drawdown63_std','drawdown63_std_rank','vol21_std_rank','vol21_std','intraday_mom21_std','intraday_mom21_std_rank','max_gain21_std_rank','max_gain21_std','cluster_is_0','cluster_is_1','cluster_is_2','cluster_is_3','cluster_is_4','cluster_is_5','cluster_is_6','cluster_is_7']},
 {'target':'target_explosive','model':'RF_D3_L30','features':['vol63_std','vol63_std_rank','acc_mom_5_21_std','acc_mom_5_21_std_rank','mom126_std','mom126_std_rank','mom252_std_rank','mom252_std','trend_slope63_std_rank','trend_slope63_std','cvar10_63_std_rank','cvar10_63_std','mom63_std_rank','mom63_std','ctx_cluster_disp63_max','ctx_cluster_disp63_max_rank','ctx_cluster_disp63_mean_rank','ctx_cluster_disp63_p75','ctx_cluster_disp63_p75_rank','ctx_cluster_disp63_mean','downvol21_std','downvol21_std_rank','vol21_max','vol21_max_rank','resid_cluster_mom63_std','resid_cluster_mom63_std_rank','vol63_max_rank','vol63_max','resid_cluster_mom21_std_rank','resid_cluster_mom21_std','vol21_std','vol21_std_rank','mom21_std_rank','mom21_std','resid_cluster_mom21_p75_rank','resid_cluster_mom21_p75','max_loss21_std','max_loss21_std_rank','max_gain63_std_rank','max_gain63_std','trend_slope21_std','trend_slope21_std_rank','resid_cluster_mom63_p75','resid_cluster_mom63_p75_rank','downvol21_max_rank','downvol21_max','max_gain63_max','max_gain63_max_rank','max_gain21_std','max_gain21_std_rank','acc_mom_21_63_std_rank','acc_mom_21_63_std','intraday_mom21_std_rank','intraday_mom21_std','drawdown63_std','drawdown63_std_rank','max_gain21_max_rank','max_gain21_max','gap_mom21_std_rank','gap_mom21_std','cluster_is_0','cluster_is_1','cluster_is_2','cluster_is_3','cluster_is_4','cluster_is_5','cluster_is_6','cluster_is_7']},
]


def load_base(path: Path):
    spec = importlib.util.spec_from_file_location('meteor_base', path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def load_mats(data_dir: Path) -> Dict[str, pd.DataFrame]:
    mats = {}
    for key in ['Open','High','Low','Close','Volume']:
        p = data_dir / f'{key.upper()}.parquet'
        if not p.exists():
            raise FileNotFoundError(p)
        x = pd.read_parquet(p)
        x.index = pd.to_datetime(x.index).tz_localize(None)
        x.columns = [str(c).upper() for c in x.columns]
        mats[key] = x.sort_index().apply(pd.to_numeric, errors='coerce')
    common = sorted(set.intersection(*[set(x.columns) for x in mats.values()]))
    return {k: v.reindex(columns=common) for k,v in mats.items()}


def enhance_feature_dictionary(base, mats, dates, D):
    O,H,L,C,V = [mats[k] for k in ['Open','High','Low','Close','Volume']]
    ret = C.pct_change(fill_method=None)
    lr = np.log(C.where(C>0)).diff()
    prev = C.shift(1)
    # Exact aliases required by BASE_FEATS and TailMix.
    D['acc_5_21'] = D['ret_5'] - (5/21)*D['ret_21']
    D['acc_21_63'] = D['ret_21'] - (21/63)*D['ret_63']
    D['vol_ratio_10_63'] = D['vol_10']/D['vol_63'].replace(0,np.nan)
    # Signed share of return energy; captures directional rather than total energy.
    for h in [21,63]:
        num = (np.sign(lr)*lr.pow(2)).rolling(h,min_periods=h).sum()
        den = lr.pow(2).rolling(h,min_periods=h).sum().replace(0,np.nan)
        D[f'directional_energy_{h}'] = base.snapshot(num/den, dates)
    D['intraday_mom21'] = base.snapshot((C/O.replace(0,np.nan)-1).rolling(21,min_periods=15).sum(), dates)
    D['gap_mom21'] = base.snapshot((O/prev.replace(0,np.nan)-1).rolling(21,min_periods=15).sum(), dates)
    D['max_loss21'] = base.snapshot(ret.rolling(21,min_periods=21).min(), dates)
    D['max_gain21'] = base.snapshot(ret.rolling(21,min_periods=21).max(), dates)
    D['max_gain63'] = base.snapshot(ret.rolling(63,min_periods=63).max(), dates)
    D['drawdown63'] = base.snapshot(C/C.rolling(63,min_periods=63).max()-1, dates)
    # Canonical source naming used by Opportunity.
    D['mom21'] = D['ret_21']; D['mom63'] = D['ret_63']; D['mom126'] = D['ret_126']; D['mom252'] = D['ret_252']
    D['trend_slope21'] = D['slope_21']; D['trend_slope63'] = D['slope_63']
    D['acc_mom_5_21'] = D['acc_5_21']; D['acc_mom_21_63'] = D['acc_21_63']
    D['downvol21'] = D['downvol_21']; D['vol21'] = D['vol_21']; D['vol63'] = D['vol_63']
    D['cvar10_63'] = base.snapshot(base.rolling_cvar10(ret,63), dates)
    # Rebuild every rank after adding the missing raw fields.
    for key, val in list(D.items()):
        if not key.endswith('_rank'):
            D[key+'_rank'] = base.cs_pct(val)
    aliases = {
        'acc_5_21_rank':'acc_5_21_rank', 'acc_21_63_rank':'acc_21_63_rank',
        'acc_mom_21_63_rank':'acc_21_63_rank', 'acc_21_63_broad_rank':'acc_21_63_rank',
        'mom126_ex21_rank':'mom_126_21_rank', 'efficiency126_rank':'eff_126_rank',
        'vol21_rank':'vol_21_rank','vol63_rank':'vol_63_rank','vol126_rank':'vol_126_rank',
        'downvol21_rank':'downvol_21_rank','downvol63_rank':'downvol_63_rank',
        'mom21_rank':'ret_21_rank','mom42_rank':'ret_42_rank','mom63_rank':'ret_63_rank','mom126_rank':'ret_126_rank',
        'kurt63_rank':'kurt_63_rank','gkvol21_rank':'gkvol21_rank',
        'energy_21_rank':'energy_21_rank','energy_63_rank':'energy_63_rank',
    }
    for dst,src in aliases.items():
        if src in D: D[dst]=D[src]
    return D


def rebuild_tail_long(base, D, dates, columns):
    for req in base.TAIL_FEATURES:
        if req not in D:
            raw = req[:-5] if req.endswith('_rank') else req
            D[req] = base.cs_pct(D[raw]) if raw in D else pd.DataFrame(np.nan,index=dates,columns=columns)
    return pd.concat([D[n].stack(dropna=False).rename(n) for n in base.TAIL_FEATURES],axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})


def balanced_kmeans_assignment(z: np.ndarray, n_clusters: int, seed: int, max_iter: int=20):
    z = np.asarray(z,float); n=z.shape[0]
    base_n=n//n_clusters; rem=n%n_clusters
    capacities=[base_n+(1 if i<rem else 0) for i in range(n_clusters)]
    km=KMeans(n_clusters=n_clusters,n_init=20,random_state=seed).fit(z)
    centers=km.cluster_centers_.copy(); labels_prev=None
    for _ in range(max_iter):
        dist=((z[:,None,:]-centers[None,:,:])**2).sum(axis=2)
        slots=np.repeat(np.arange(n_clusters,dtype=int),capacities)
        expanded=dist[:,slots] + np.arange(len(slots))[None,:]*1e-12
        ri,ci=linear_sum_assignment(expanded)
        labels=slots[ci[np.argsort(ri)]]
        new=np.vstack([z[labels==c].mean(axis=0) for c in range(n_clusters)])
        if labels_prev is not None and np.array_equal(labels,labels_prev):
            centers=new; break
        labels_prev=labels.copy(); centers=new
    return labels, centers, capacities


def build_s3b_clusters(mats, dates, category_map, seed=26072026):
    C=mats['Close']; lr=np.log(C.where(C>0)).diff()
    defensive=[t for t in C.columns if category_map.get(t)=='C05_BONDS_CASH_CREDIT']
    dynamic=[t for t in C.columns if t not in defensive]
    rows=[]; prev_by_id=None; ari=[]; balance=[]
    for di,dt in enumerate(dates):
        win=lr.loc[:dt,dynamic].tail(252)
        elig=[t for t in dynamic if win[t].notna().sum()>=168 and pd.notna(C.at[dt,t])]
        if len(elig)<14: continue
        x=win[elig].copy()
        x=x.apply(lambda s:s.fillna(s.mean()),axis=0).fillna(0.0)
        # Standardise each ticker history; PCA embeds tickers by common-factor loadings.
        arr=x.to_numpy(float)
        mu=np.nanmean(arr,axis=0); sd=np.nanstd(arr,axis=0); sd[sd<EPS]=1.0
        arr=(arr-mu)/sd
        nc=min(5,arr.shape[0]-1,arr.shape[1]-1)
        pca=PCA(n_components=max(1,nc),random_state=seed).fit(arr)
        emb=pca.components_.T*np.sqrt(np.maximum(pca.explained_variance_,EPS))[None,:]
        labels,centers,caps=balanced_kmeans_assignment(emb,7,seed+di)
        local={c:set(np.array(elig)[labels==c]) for c in range(7)}
        if prev_by_id is None:
            order=np.argsort(centers[:,0])
            mapping={int(local_id):int(rank+1) for rank,local_id in enumerate(order)}
        else:
            ids=list(range(1,8)); overlap=np.zeros((7,7))
            for a in range(7):
                for j,pid in enumerate(ids):
                    overlap[a,j]=len(local[a] & prev_by_id.get(pid,set()))
            rr,cc=linear_sum_assignment(-overlap)
            mapping={int(a):int(ids[j]) for a,j in zip(rr,cc)}
        cur_by_id={pid:set() for pid in range(1,8)}
        for t,l in zip(elig,labels):
            pid=mapping[int(l)]; cur_by_id[pid].add(t)
            rows.append({'signal_date':dt,'ticker':t,'cluster_id':pid,'cluster_source':'S3B_DYNAMIC'})
        for t in defensive:
            if pd.notna(C.at[dt,t]): rows.append({'signal_date':dt,'ticker':t,'cluster_id':0,'cluster_source':'S3B_DEFENSIVE_FIXED'})
        counts=[len(cur_by_id[i]) for i in range(1,8)]
        balance.append({'signal_date':dt,'min_dynamic_size':min(counts),'max_dynamic_size':max(counts),'n_dynamic':len(elig),'n_defensive':sum(pd.notna(C.loc[dt,defensive]))})
        if prev_by_id is not None:
            common=sorted(set().union(*prev_by_id.values()) & set(elig))
            if len(common)>10:
                old={t:i for i,s in prev_by_id.items() for t in s}; new={t:i for i,s in cur_by_id.items() for t in s}
                ari.append({'signal_date':dt,'ari':adjusted_rand_score([old[t] for t in common],[new[t] for t in common]),'n_common':len(common)})
        prev_by_id=cur_by_id
    return pd.DataFrame(rows),pd.DataFrame(balance),pd.DataFrame(ari)


def build_macro_panel(base, D, labels, category_map):
    missing=[f for f in base.BASE_FEATS if f not in D]
    if missing: raise RuntimeError(f'Missing BASE_FEATS: {missing}')
    long=pd.concat([D[f].stack(dropna=False).rename(f) for f in base.BASE_FEATS],axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})
    lab=labels[['signal_date','ticker','fwd_ret_21','fwd_ret_42','fwd_ret_63','exit_date_63']].drop_duplicates(['signal_date','ticker'])
    p=long.merge(lab,on=['signal_date','ticker'],how='left')
    p['macro_category']=p.ticker.map(category_map)
    p['fwd_multi']=.45*p.fwd_ret_21+.35*p.fwd_ret_42+.20*p.fwd_ret_63
    rows=[]
    for (dt,cat),g in p.dropna(subset=['macro_category']).groupby(['signal_date','macro_category']):
        rec={'signal_date':dt,'macro_category':cat,'label_exit_date_63':g.exit_date_63.max()}
        for f in base.BASE_FEATS:
            rec[f+'_mean']=g[f].mean(); rec[f+'_max']=g[f].max()
        vals=g.fwd_multi.dropna().sort_values(ascending=False)
        rec['target']=vals.iloc[:2].mean() if len(vals)>=2 else np.nan
        rows.append(rec)
    out=pd.DataFrame(rows)
    out['target_rank']=out.groupby('signal_date').target.rank(pct=True)
    feats=[f'{f}_{a}' for f in base.BASE_FEATS for a in ['mean','max']]
    return out,feats


def build_opportunity_panel(base, D, clusters, labels):
    raw_names=['mom252','mom126','mom63','mom21','trend_slope63','trend_slope21','acc_mom_5_21','acc_mom_21_63','intraday_mom21','downvol21','max_loss21','vol63','vol21','max_gain63','max_gain21','cvar10_63','gap_mom21','drawdown63']
    missing=[x for x in raw_names if x not in D]
    if missing: raise RuntimeError(f'Missing Opportunity raw features: {missing}')
    t=pd.concat([D[n].stack(dropna=False).rename(n) for n in raw_names],axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})
    lab=labels[['signal_date','ticker','fwd_ret_21','exit_date_21']].drop_duplicates(['signal_date','ticker'])
    t=t.merge(clusters[['signal_date','ticker','cluster_id']],on=['signal_date','ticker'],how='inner').merge(lab,on=['signal_date','ticker'],how='left')
    grp=t.groupby(['signal_date','cluster_id'])
    t['resid_cluster_mom21']=t.mom21-grp.mom21.transform('mean')
    t['resid_cluster_mom63']=t.mom63-grp.mom63.transform('mean')
    t['ctx_cluster_disp63']=grp.mom63.transform('std')
    features=raw_names+['resid_cluster_mom21','resid_cluster_mom63','ctx_cluster_disp63']
    rows=[]
    for (dt,cid),g in t.groupby(['signal_date','cluster_id']):
        rec={'signal_date':dt,'cluster_id':int(cid),'label_exit_date_21':g.exit_date_21.max()}
        for f in features:
            rec[f+'_mean']=g[f].mean(); rec[f+'_p75']=g[f].quantile(.75); rec[f+'_max']=g[f].max(); rec[f+'_std']=g[f].std(ddof=0)
        vals=g.fwd_ret_21.dropna().sort_values(ascending=False)
        allv=t.loc[t.signal_date.eq(dt),'fwd_ret_21'].dropna()
        if len(vals):
            rec['target_top2']=vals.iloc[:2].mean()
            rec['target_spread']=vals.iloc[0]-(vals.iloc[1] if len(vals)>1 else vals.iloc[0])
            rec['target_excess_max']=vals.iloc[0]-(allv.median() if len(allv) else np.nan)
            rec['target_explosive']=float(len(allv)>0 and vals.iloc[0]>allv.quantile(.90))
        rows.append(rec)
    out=pd.DataFrame(rows)
    numeric=[c for c in out.columns if c.endswith(('_mean','_p75','_max','_std'))]
    for c in numeric: out[c+'_rank']=out.groupby('signal_date')[c].rank(pct=True)
    for cid in range(8): out[f'cluster_is_{cid}']=(out.cluster_id==cid).astype(float)
    requested=sorted(set(f for s in OPPORTUNITY_SPECS for f in s['features']))
    for f in requested:
        if f not in out: out[f]=np.nan
    return out


def fit_predict(base, compact, tail, macro, macro_feats, opp, years, n_estimators=360):
    params=dict(base.COMPACT_PARAMS);params['n_estimators']=n_estimators;params['n_jobs']=2
    pred_rows=[]; macro_rows=[]; opp_rows=[]; audit=[]
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        cvalid=compact[base.F2D_FEATURES].notna().sum(axis=1)>=30
        tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_pct.notna()&cvalid].sort_values(['signal_date','ticker'])
        te=compact[(compact.signal_date.dt.year==year)&cvalid].sort_values(['signal_date','ticker'])
        if tr.signal_date.nunique()<60 or te.empty: continue
        groups=tr.groupby('signal_date',sort=True).size().tolist(); y=(tr.target_rank_pct*100).round().astype(int)
        cps=[]
        for seed in MODEL_SEEDS:
            model=XGBRanker(**params,random_state=seed)
            model.fit(tr[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan),y,group=groups,verbose=False)
            cps.append(model.predict(te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)))
        out=te[['signal_date','ticker']].copy();out['compact_raw']=np.mean(cps,axis=0)
        tvalid=tail[base.TAIL_FEATURES].notna().sum(axis=1)>=12
        ttr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()&tvalid]
        tte=tail[(tail.signal_date.dt.year==year)&tvalid]
        tm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.0)).fit(ttr[base.TAIL_FEATURES],ttr.y_tailmix)
        tp=tte[['signal_date','ticker']].copy();tp['tail_raw']=tm.predict(tte[base.TAIL_FEATURES])
        pred_rows.append(out.merge(tp,on=['signal_date','ticker'],how='left'))
        mtr=macro[(macro.signal_date<cutoff)&(macro.label_exit_date_63<cutoff)&macro.target_rank.notna()]
        mte=macro[macro.signal_date.dt.year==year]
        if len(mtr)>50 and len(mte):
            mm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.0)).fit(mtr[macro_feats],mtr.target_rank)
            q=mte[['signal_date','macro_category']].copy();q['macro_raw']=mm.predict(mte[macro_feats]);macro_rows.append(q)
        out_opp=opp[opp.signal_date.dt.year==year][['signal_date','cluster_id']].copy()
        for spec in OPPORTUNITY_SPECS:
            feats=spec['features']; target=spec['target']
            otr=opp[(opp.signal_date<cutoff)&(opp.label_exit_date_21<cutoff)&opp[target].notna()]
            ote=opp[opp.signal_date.dt.year==year]
            if len(otr)<100 or ote.empty:
                out_opp[target+'_pred']=np.nan; continue
            if spec['model'].startswith('ET'):
                model=make_pipeline(SimpleImputer(strategy='median'),ExtraTreesRegressor(n_estimators=300,max_depth=4,min_samples_leaf=30,n_jobs=2,random_state=year+11))
            elif spec['model'].startswith('RF'):
                model=make_pipeline(SimpleImputer(strategy='median'),RandomForestClassifier(n_estimators=300,max_depth=3,min_samples_leaf=30,n_jobs=2,class_weight='balanced',random_state=year+17))
            else:
                model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=100.0))
            model.fit(otr[feats],otr[target].astype(int) if target=='target_explosive' else otr[target])
            if target=='target_explosive':
                clf=model[-1]
                pp=model.predict_proba(ote[feats])
                val=pp[:,list(clf.classes_).index(1)] if 1 in clf.classes_ else np.zeros(len(ote))
            else: val=model.predict(ote[feats])
            out_opp[target+'_pred']=val
        opp_rows.append(out_opp)
        audit.append({'year':year,'compact_train_dates':tr.signal_date.nunique(),'compact_train_rows':len(tr),'tail_train_rows':len(ttr),'macro_train_rows':len(mtr),'opp_train_rows':len(opp[opp.signal_date<cutoff])})
    p=pd.concat(pred_rows,ignore_index=True)
    p['compact_rank']=p.groupby('signal_date').compact_raw.rank(pct=True)
    p['tail_rank']=p.groupby('signal_date').tail_raw.rank(pct=True)
    p['titanium_score_pre_macro']=.70*p.compact_rank+.30*p.tail_rank
    mp=pd.concat(macro_rows,ignore_index=True)
    mp['macro_z']=mp.groupby('signal_date').macro_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+EPS))
    tops=[]
    for dt,g in mp.groupby('signal_date'):
        g=g.sort_values('macro_z',ascending=False)
        tops.append({'signal_date':dt,'top_macro':g.iloc[0].macro_category,'macro_gap_z':float(g.iloc[0].macro_z-g.iloc[1].macro_z) if len(g)>1 else 0.0})
    p['macro_category']=p.ticker.map(base.TICKER_CATEGORY)
    p=p.merge(pd.DataFrame(tops),on='signal_date',how='left')
    p['macro_bonus']=np.where((p.macro_category==p.top_macro)&(p.macro_gap_z>=.75)&(p.tail_rank>=.80),.15,0.0)
    p['titanium_score']=p.titanium_score_pre_macro+p.macro_bonus
    op=pd.concat(opp_rows,ignore_index=True)
    weights={'target_top2_pred':.35,'target_spread_pred':.15,'target_excess_max_pred':.35,'target_explosive_pred':.15}
    for c in weights: op[c+'_rank']=op.groupby('signal_date')[c].rank(pct=True)
    op['opp_raw']=sum(w*op[c+'_rank'] for c,w in weights.items())
    op['opp_z']=op.groupby('signal_date').opp_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+EPS))
    return p.sort_values(['signal_date','ticker']),op.sort_values(['signal_date','cluster_id']),pd.DataFrame(audit),mp


def make_baskets(base, p, n=500):
    # Match the original 500-basket construction: four fully observed names per category.
    coverage=p[p.signal_date>=BACKTEST_START].groupby('ticker').signal_date.nunique()
    total=p[p.signal_date>=BACKTEST_START].signal_date.nunique()
    eligible=set(coverage[coverage>=max(1,int(.95*total))].index)
    cats={c:sorted([t for t in xs if t in eligible]) for c,xs in base.CATEGORY_TICKERS.items()}
    if any(len(v)<4 for v in cats.values()):
        raise RuntimeError({k:len(v) for k,v in cats.items()})
    rng=random.Random(BASKET_SEED); seen=set(); baskets=[]
    while len(baskets)<n:
        selected=[]
        for c in sorted(cats): selected.extend(rng.sample(cats[c],4))
        b=tuple(sorted(selected))
        if b not in seen: seen.add(b);baskets.append(b)
    return baskets,cats


def build_target_arrays(universes, pred, opp, clusters, cal_dates, tick_index, Odf, entry_dates):
    B=len(universes);K=len(cal_dates);P=2
    base_sel=np.full((B,K,P),-1,np.int16);base_bw=np.zeros((B,K,P));direct_sel=base_sel.copy();direct_bw=base_bw.copy()
    margin=np.full((B,K),np.nan);conditions=np.zeros((B,K),bool)
    cluster_map=clusters.set_index(['signal_date','ticker']).cluster_id.to_dict()
    opp_by={pd.Timestamp(d):g.sort_values('opp_z',ascending=False) for d,g in opp.groupby('signal_date')}
    pred_by={pd.Timestamp(d):g.sort_values('titanium_score',ascending=False) for d,g in pred.groupby('signal_date')}
    for k,dt in enumerate(cal_dates):
        g0=pred_by.get(pd.Timestamp(dt)); entry=entry_dates[k]
        if g0 is None: continue
        og=opp_by.get(pd.Timestamp(dt)); topc=None;gap=-np.inf
        if og is not None and len(og)>=2:
            topc=int(og.iloc[0].cluster_id);gap=float(og.iloc[0].opp_z-og.iloc[1].opp_z)
        for b,u in enumerate(universes):
            allowed=set(u)
            g=g0[g0.ticker.isin(allowed)]
            g=g[g.ticker.map(lambda t:t in Odf.columns and pd.notna(Odf.at[entry,t]) and Odf.at[entry,t]>0)]
            if len(g)<2: continue
            r1,r2=g.iloc[0],g.iloc[1];t1=str(r1.ticker);t2=str(r2.ticker)
            m=float(r1.titanium_score-r2.titanium_score);margin[b,k]=m
            w1=1.0 if m>=.12 else .75
            base_sel[b,k]=[tick_index[t1],tick_index[t2]];base_bw[b,k]=[w1,1-w1]
            direct_sel[b,k]=base_sel[b,k];direct_bw[b,k]=base_bw[b,k]
            cid=cluster_map.get((pd.Timestamp(dt),t1),-1)
            cond=bool(w1<1 and cid==topc and np.isfinite(gap) and gap>=.50)
            conditions[b,k]=cond
            if cond: direct_bw[b,k]=[1.0,0.0]
    return base_sel,base_bw,direct_sel,direct_bw,margin,conditions


@njit(cache=False)
def _value(a,u,free,bu,su,p,bil,shv):
    v=free+bu*p[bil]+su*p[shv]
    for j in range(len(a)):
        if a[j]>=0 and u[j]!=0: v+=u[j]*p[a[j]]
    return v


@njit(parallel=True,cache=False)
def exact_sim(SEL,BW,mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,bil,shv,cost=.001,slip=.001):
    N,B,K,P=SEL.shape;D=len(mi);E=np.ones((N,B,D))
    for n in prange(N):
      for b in range(B):
        a=np.full(P,-1,np.int16);u=np.zeros(P);bu=0.;su=0.;free=1.;pf=-1.;pw=np.full(P,-9.);cd=0
        for d in range(D):
          # Value at current open, before any rebalance.
          val=_value(a,u,free,bu,su,O[d],bil,shv)
          if not np.isfinite(val) or val<=0: val=E[n,b,d-1] if d>0 else 1.0
          if d==D-1:
            E[n,b,d]=val
            break
          k=int(mi[d]);da=np.full(P,-1,np.int16);bw=np.zeros(P)
          if k>=0: da[:]=SEL[n,b,k];bw[:]=BW[n,b,k]
          sys_event=False;f=0.
          if da[0]>=0:
            pg=0.
            for j in range(P):
              if da[j]>=0 and bw[j]>0: pg+=bw[j]*gap[d,da[j]]
            sys_event=((pg<=-0.032 and UD1[d]>=.70) or (pg<=-0.044 and UNEG[d]>=.75))
            if sys_event: f=.25;cd=3
            elif cd>0: f=.25;cd-=1
            else: f=1.
          tw=bw*f;cw=1.-f
          reb=(d==0 or free>1e-14 or abs(pf-f)>1e-12)
          if not reb:
            for j in range(P):
              if a[j]!=da[j] or abs(pw[j]-bw[j])>1e-12: reb=True;break
          if reb:
            cb=bu*O[d,bil]/val if bu else 0.;cs=su*O[d,shv]/val if su else 0.;cf=free/val if val>0 else 0.
            tv=.5*(abs(cf)+abs(cb-cw*.5)+abs(cs-cw*.5))
            # Turnover must be matched by ticker, not by rank slot.  If the
            # previous top-1 becomes top-2 (or vice versa), only the weight
            # difference is traded; treating slots independently double-counts
            # a full sale and repurchase.
            for j in range(P):
              if a[j] < 0: continue
              cur=u[j]*O[d,a[j]]/val if u[j]!=0 else 0.
              target=0.
              for q in range(P):
                if da[q] == a[j]:
                  target += tw[q]
              tv += .5*abs(cur-target)
            for q in range(P):
              if da[q] < 0: continue
              found=False
              for j in range(P):
                if a[j] == da[q]:
                  found=True
              if not found:
                tv += .5*tw[q]
            val*=1.-cost*tv
            a[:]=da;u[:]=0.
            for j in range(P):
              if a[j]>=0 and tw[j]>0: u[j]=tw[j]*val/O[d,a[j]]
            bu=cw*.5*val/O[d,bil];su=cw*.5*val/O[d,shv];free=0.;pf=f;pw[:]=bw
          # Intraday protective stops, exactly gated by UH/SA and systemic breadth.
          for j in range(P):
            x=a[j]
            if x>=0 and u[j]>0 and (UH[d,x] or SA[d,x]) and (sys_event or UD1[d]>=.55):
              sp=PC[d,x]*(1.-.055)
              if O[d,x]<=sp:
                fill=O[d,x]
                free += u[j]*fill*(1.-cost);u[j]=0.
              elif L[d,x]<=sp:
                fill=sp*(1.-slip)
                free += u[j]*fill*(1.-cost);u[j]=0.
          close_val=_value(a,u,free,bu,su,C[d],bil,shv)
          E[n,b,d]=close_val if np.isfinite(close_val) and close_val>0 else (E[n,b,d-1] if d>0 else 1.)
    return E


def prepare_sim_inputs(mats, cal):
    # The tradable path begins at the first D+1 entry and ends at the last
    # open-to-open exit. Never expose the portfolio to pre-OOS placeholder data.
    full_idx=mats['Close'].index
    first_entry=pd.Timestamp(cal.entry_date.min())
    last_exit=pd.Timestamp(cal.exit_date.max())
    idx=full_idx[(full_idx>=first_entry)&(full_idx<=last_exit)]
    if len(idx)<2:
        raise RuntimeError(f'Invalid OOS simulation calendar: {first_entry} -> {last_exit}')
    ticks=list(mats['Close'].columns);ti={t:i for i,t in enumerate(ticks)}

    Odf=mats['Open'].reindex(idx,columns=ticks).ffill()
    Ldf=mats['Low'].reindex(idx,columns=ticks).ffill()
    Cdf=mats['Close'].reindex(idx,columns=ticks).ffill()

    # Breadth and overnight gaps are computed before any neutral placeholders.
    prev_close=Cdf.shift(1)
    valid_gap=Odf.notna() & prev_close.notna() & (prev_close>0)
    gap_df=(Odf/prev_close-1.0).where(valid_gap)
    denom=valid_gap.sum(axis=1).replace(0,np.nan)
    UD1=((gap_df<-.01)&valid_gap).sum(axis=1).div(denom).fillna(0.0).to_numpy(float)
    UNEG=((gap_df<0)&valid_gap).sum(axis=1).div(denom).fillna(0.0).to_numpy(float)

    # BIL and SHV must be genuine observations throughout the OOS path.
    for defensive in ('BIL','SHV'):
        if defensive not in ticks:
            raise RuntimeError(f'Missing defensive asset {defensive}')
        bad=Odf[defensive].isna()|Ldf[defensive].isna()|Cdf[defensive].isna()
        if bad.any():
            raise RuntimeError(f'{defensive} has {int(bad.sum())} missing OOS price rows')

    # Neutral placeholders are allowed only for assets that are not yet listed;
    # point-in-time eligibility prevents them from being selected.
    O=Odf.fillna(1.0).to_numpy(float)
    L=Ldf.fillna(Odf).fillna(1.0).to_numpy(float)
    C=Cdf.fillna(1.0).to_numpy(float)
    gap=np.nan_to_num(gap_df.to_numpy(float),nan=0.0,posinf=0.0,neginf=0.0)

    hist=Cdf
    m3=hist/hist.shift(3)-1;m5=hist/hist.shift(5)-1
    sma10=hist.rolling(10,min_periods=10).mean();sma20=hist.rolling(20,min_periods=20).mean()
    UH=((((hist<sma10)&(m3<0))|((hist<sma20)&(m5<-.015))).shift(1).fillna(False)).to_numpy(bool)
    SA=(((m5<-.04)|((hist<sma20)&(m3<-.025))).shift(1).fillna(False)).to_numpy(bool)
    PC=np.empty_like(C);PC[0]=O[0];PC[1:]=C[:-1]

    ei=np.array([idx.get_loc(pd.Timestamp(d)) for d in cal.entry_date],np.int32)
    xi=np.array([idx.get_loc(pd.Timestamp(d)) for d in cal.exit_date],np.int32)
    mi=np.full(len(idx),-1,np.int16)
    for k,(a,e) in enumerate(zip(ei,xi)):
        mi[a:e]=k
    if mi[0] != 0:
        raise RuntimeError(f'First OOS day is not assigned to month 0: mi0={mi[0]}')
    return idx,ticks,ti,O,L,C,PC,gap,UD1,UNEG,UH,SA,ei,xi,mi


def month_log_excess(eq_direct,eq_base,idx,cal_dates):
    # Official Router state: average shadow log excess across the 500
    # robustness baskets, then aggregate daily excess by calendar month.
    # This yields one common causal schedule, not one schedule per basket.
    rd=np.zeros_like(eq_direct);rb=np.zeros_like(eq_base)
    rd[:,1:]=eq_direct[:,1:]/np.maximum(eq_direct[:,:-1],EPS)-1.0
    rb[:,1:]=eq_base[:,1:]/np.maximum(eq_base[:,:-1],EPS)-1.0
    x=(np.log1p(np.clip(rd,-.999999,None))-np.log1p(np.clip(rb,-.999999,None))).mean(axis=0)
    monthly=pd.Series(x,index=idx).groupby(idx.to_period('M')).sum()
    return np.array([float(monthly.get(pd.Timestamp(d).to_period('M'),0.0)) for d in cal_dates],float)


def router_active(logex,window=12):
    K=len(logex);active=np.zeros(K,bool)
    for k in range(K):
        hist=logex[max(0,k-window):k]
        if len(hist)>=max(6,window//2): active[k]=float(np.mean(hist))>0
    return active


def metrics(eq,idx):
    years=(idx[-1]-idx[0]).days/365.25
    cagr=eq[-1]**(1/years)-1
    dd=eq/np.maximum.accumulate(eq)-1
    r=eq[1:]/eq[:-1]-1
    sh=np.sqrt(252)*np.nanmean(r)/np.nanstd(r) if np.nanstd(r)>0 else np.nan
    return float(cagr),float(np.nanmin(dd)),float(sh),float(eq[-1])


def simulate_all(universes,pred,opp,clusters,mats,cal,forced_active=None):
    idx,ticks,ti,O,L,C,PC,gap,UD1,UNEG,UH,SA,ei,xi,mi=prepare_sim_inputs(mats,cal)
    base_s,base_w,dir_s,dir_w,margin,cond=build_target_arrays(universes,pred,opp,clusters,pd.DatetimeIndex(cal.signal_date),ti,mats['Open'],pd.DatetimeIndex(cal.entry_date))
    SEL=np.stack([base_s,dir_s]);BW=np.stack([base_w,dir_w])
    E=exact_sim(SEL,BW,mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,ti['BIL'],ti['SHV'],COST,STOP_SLIP)
    if forced_active is None:
        active=router_active(month_log_excess(E[1],E[0],idx,pd.DatetimeIndex(cal.signal_date)))
    else:
        active=np.asarray(forced_active,bool).copy()
        if len(active)!=len(cal): raise RuntimeError('Forced Router schedule length mismatch')
    router_s=base_s.copy();router_w=base_w.copy()
    for b in range(len(universes)):
      for k in range(len(cal)):
        if active[k]:router_s[b,k]=dir_s[b,k];router_w[b,k]=dir_w[b,k]
    ER=exact_sim(router_s[None,:,:,:],router_w[None,:,:,:],mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,ti['BIL'],ti['SHV'],COST,STOP_SLIP)[0]
    return idx,E[0],E[1],ER,active,margin,cond,base_s,base_w,dir_s,dir_w


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base-module',required=True)
    ap.add_argument('--data-dir',required=True)
    ap.add_argument('--output',default='TITANIUM_RECONSTRUCTION_V2')
    ap.add_argument('--fast',action='store_true')
    args=ap.parse_args();out=Path(args.output);shutil.rmtree(out,ignore_errors=True);out.mkdir(parents=True)
    base=load_base(Path(args.base_module));mats=load_mats(Path(args.data_dir))
    t0=time.time();dates,compact,tail0,D=base.build_features(mats);D=enhance_feature_dictionary(base,mats,dates,D);tail=rebuild_tail_long(base,D,dates,mats['Close'].columns)
    compact=base.add_labels(compact,mats['Open'],dates);tail=base.add_labels(tail,mats['Open'],dates)
    clusters,balance,ari=build_s3b_clusters(mats,dates,base.TICKER_CATEGORY)
    macro,macro_feats=build_macro_panel(base,D,compact,base.TICKER_CATEGORY)
    opp=build_opportunity_panel(base,D,clusters,compact)
    years=range(2017,2027);nt=60 if args.fast else 360
    pred,opp_pred,fit_audit,macro_pred=fit_predict(base,compact,tail,macro,macro_feats,opp,years,nt)
    pred=pred[pred.signal_date>=BACKTEST_START].copy();opp_pred=opp_pred[opp_pred.signal_date>=BACKTEST_START].copy()
    # Calendar is derived from fully matured D+1 open labels.
    cal=compact[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date')
    cal=cal[(cal.signal_date>=BACKTEST_START)&cal.signal_date.isin(pred.signal_date.unique())&cal.exit_date.notna()].reset_index(drop=True)
    baskets,cats=make_baskets(base,pred,20 if args.fast else 500)
    idx,EB,ED,ER,active,margin,cond,bs,bw,ds,dw=simulate_all(baskets,pred,opp_pred,clusters,mats,cal)
    rows=[]
    for b in range(len(baskets)):
      for name,arr in [('BASE',EB[b]),('DIRECT',ED[b]),('ROUTER',ER[b])]:
        c,dd,sh,fe=metrics(arr,idx);rows.append({'basket':b,'strategy':name,'cagr':c,'maxdd':dd,'sharpe':sh,'final_equity':fe,'router_active_months':int(active.sum()),'direct_condition_months':int(cond[b].sum())})
    res=pd.DataFrame(rows);res.to_csv(out/'BASKET_RESULTS.csv',index=False)
    pd.DataFrame([{'basket':b,'ticker':t} for b,u in enumerate(baskets) for t in u]).to_csv(out/'BASKET_MEMBERSHIP.csv',index=False)
    # Unrestricted universe uses every ticker scored in >=50% of OOS months; eligibility remains point-in-time in target builder.
    global_universe=[sorted(pred.ticker.unique())]
    idxg,Ebg,Edg,Erg,activeg,marging,condg,*_=simulate_all(global_universe,pred,opp_pred,clusters,mats,cal,forced_active=active)
    grows=[]
    for name,arr in [('BASE',Ebg[0]),('DIRECT',Edg[0]),('ROUTER',Erg[0])]:
        c,dd,sh,fe=metrics(arr,idxg);grows.append({'strategy':name,'cagr':c,'maxdd':dd,'sharpe':sh,'final_equity':fe,'router_active_months':int(activeg.sum()),'direct_condition_months':int(condg[0].sum())});pd.Series(arr,index=idxg,name='equity').to_csv(out/f'GLOBAL_{name}_EQUITY.csv')
    global_score=pd.DataFrame(grows)
    global_score.to_csv(out/'GLOBAL_SCORECARD.csv',index=False)
    health=[]
    for name,arr in [('BASE',Ebg[0]),('DIRECT',Edg[0]),('ROUTER',Erg[0])]:
        dr=arr[1:]/arr[:-1]-1.0
        j=int(np.nanargmax(np.abs(dr))) if len(dr) else -1
        health.append({'strategy':name,'start_date':str(idxg[0].date()),'end_date':str(idxg[-1].date()),
                       'max_abs_daily_return':float(abs(dr[j])) if j>=0 else np.nan,
                       'max_abs_daily_return_date':str(idxg[j+1].date()) if j>=0 else None,
                       'min_equity':float(np.nanmin(arr)),'max_equity':float(np.nanmax(arr))})
    path_health=pd.DataFrame(health);path_health.to_csv(out/'PATH_HEALTH_AUDIT.csv',index=False)
    pred.to_parquet(out/'OOS_TICKER_SCORES.parquet',index=False);opp_pred.to_csv(out/'OOS_OPPORTUNITY_SCORES.csv',index=False);clusters.to_csv(out/'S3B_CLUSTERS.csv',index=False);balance.to_csv(out/'S3B_BALANCE.csv',index=False);ari.to_csv(out/'S3B_ARI.csv',index=False);fit_audit.to_csv(out/'FIT_AUDIT.csv',index=False)
    # Parity and health gates.
    feature_rows=[]
    for family,cols,frame in [('COMPACT',base.F2D_FEATURES,compact),('TAIL',base.TAIL_FEATURES,tail),('MACRO',macro_feats,macro)]:
      for c in cols:feature_rows.append({'family':family,'feature':c,'exists':c in frame,'missing_rate':float(frame[c].isna().mean()) if c in frame else 1.0})
    feature_audit=pd.DataFrame(feature_rows);feature_audit.to_csv(out/'FEATURE_PARITY_AUDIT.csv',index=False)
    macro_gate=pred.groupby('signal_date').agg(any_bonus=('macro_bonus',lambda x:bool((x>0).any())),macro_gap=('macro_gap_z','max')).reset_index();macro_gate.to_csv(out/'MACRO_GATE_AUDIT.csv',index=False)
    # Frozen deterministic diagnostic: the registered checkpoint is 2026-06-30.
    checkpoint=pd.Timestamp('2026-06-30')
    chk=pred[pred.signal_date==checkpoint].sort_values('titanium_score',ascending=False).head(5)
    known={'signal_date':str(checkpoint.date()),'checkpoint_available':bool(len(chk)),
           'top1':str(chk.iloc[0].ticker) if len(chk) else None,
           'top2':str(chk.iloc[1].ticker) if len(chk)>1 else None,
           'frozen_expected_top1':'USO','frozen_expected_top2':'PALL',
           'matches_frozen_checkpoint':bool(len(chk)>1 and chk.iloc[0].ticker=='USO' and chk.iloc[1].ticker=='PALL')}
    (out/'KNOWN_SIGNAL_CHECK.json').write_text(json.dumps(known,indent=2))
    gates={
      'all_compact_features_present':bool(feature_audit.query("family=='COMPACT'").exists.all()),
      'all_tail_features_present':bool(feature_audit.query("family=='TAIL'").exists.all()),
      'all_54_macro_aggregates_present':bool(feature_audit.query("family=='MACRO'").exists.all() and len(macro_feats)==54),
      'all_opportunity_features_present':bool(all(f in opp.columns for s in OPPORTUNITY_SPECS for f in s['features'])),
      's3b_dynamic_sizes_balanced':bool(len(balance)>0 and (balance.max_dynamic_size-balance.min_dynamic_size).max()<=1),
      'macro_gate_non_degenerate':bool(macro_gate.any_bonus.sum()>=5),
      'known_signal_matches_frozen':known['matches_frozen_checkpoint'],
      'daily_path_no_impossible_jumps':bool(path_health.max_abs_daily_return.max()<0.50),
      'oos_path_starts_at_first_entry':bool(pd.Timestamp(idxg[0])==pd.Timestamp(cal.entry_date.min())),
      'n_baskets':len(baskets),'n_oos_months':len(cal),'n_scored_tickers':int(pred.ticker.nunique()),'median_s3b_ari':float(ari.ari.median()) if len(ari) else np.nan,'macro_bonus_months':int(macro_gate.any_bonus.sum()),'elapsed_seconds':time.time()-t0,
    }
    (out/'PARITY_GATES.json').write_text(json.dumps(gates,indent=2))
    # Plots and report.
    router=res[res.strategy=='ROUTER'];base_res=res[res.strategy=='BASE'];direct=res[res.strategy=='DIRECT']
    plt.figure(figsize=(10,6));plt.hist(router.cagr*100,bins=30,edgecolor='black');plt.axvline(router.cagr.mean()*100,ls='--',label=f'Media {router.cagr.mean()*100:.2f}%');plt.axvline(router.cagr.median()*100,ls=':',label=f'Mediana {router.cagr.median()*100:.2f}%');plt.xlabel('CAGR (%)');plt.ylabel('Panieri');plt.legend();plt.grid(alpha=.2);plt.tight_layout();plt.savefig(out/'CAGR_DISTRIBUTION.png',dpi=180);plt.close()
    glob=pd.DataFrame(grows).set_index('strategy');q=router.cagr.quantile([.01,.05,.1,.25,.5,.75,.9,.95,.99])
    report=f'''# Titanium current-data reconstruction v2\n\nThis run reconstructs the frozen architecture from source specifications on the downloaded current Yahoo matrices. It is not accepted as a frozen replication unless all parity gates pass.\n\n## Parity gates\n\n```json\n{json.dumps(gates,indent=2)}\n```\n\n## 500-basket Router distribution\n\n- Mean CAGR: {router.cagr.mean():.4%}\n- Median CAGR: {router.cagr.median():.4%}\n- P05/P95: {q.loc[.05]:.4%} / {q.loc[.95]:.4%}\n- Min/Max: {router.cagr.min():.4%} / {router.cagr.max():.4%}\n- Median MaxDD: {router.maxdd.median():.4%}\n\n## Mean basket strategies\n\n- Base CAGR: {base_res.cagr.mean():.4%}\n- Direct CAGR: {direct.cagr.mean():.4%}\n- Router CAGR: {router.cagr.mean():.4%}\n\n## Unrestricted universe\n\n| Strategy | CAGR | MaxDD | Sharpe |\n|---|---:|---:|---:|\n| BASE | {glob.loc['BASE','cagr']:.4%} | {glob.loc['BASE','maxdd']:.4%} | {glob.loc['BASE','sharpe']:.3f} |\n| DIRECT | {glob.loc['DIRECT','cagr']:.4%} | {glob.loc['DIRECT','maxdd']:.4%} | {glob.loc['DIRECT','sharpe']:.3f} |\n| ROUTER | {glob.loc['ROUTER','cagr']:.4%} | {glob.loc['ROUTER','maxdd']:.4%} | {glob.loc['ROUTER','sharpe']:.3f} |\n'''
    (out/'REPORT.md').write_text(report);print(report,flush=True)
    shutil.make_archive(str(out),'zip',out)

if __name__=='__main__': main()
