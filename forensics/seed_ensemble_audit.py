#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBRanker

SEEDS=[101,202,303]
REF={'D1':0.15023,'D2':0.22645,'DEV':0.18617,'FULL':0.21654064}
PERIODS={'D1':('2017-01-01','2019-12-31'),'D2':('2020-01-01','2022-12-31'),'DEV':('2017-01-01','2022-12-31'),'FULL':('2017-01-01','2026-12-31')}

def load(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def basket_cagr(arr,dates,start,end):
    dates=pd.DatetimeIndex(dates); mask=(dates>=pd.Timestamp(start))&(dates<=pd.Timestamp(end)); z=np.asarray(arr)[:,mask]; d=dates[mask]
    if z.shape[1]<2:return np.full(z.shape[0],np.nan)
    years=(d[-1]-d[0]).days/365.25
    return np.power(z[:,-1]/z[:,0],1/years)-1

def zscore_group(s,g):
    m=s.groupby(g).transform('mean'); sd=s.groupby(g).transform(lambda x:x.std(ddof=0)).replace(0,np.nan)
    return (s-m)/sd

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--trained',required=True);ap.add_argument('--base-module',required=True);ap.add_argument('--v5-module',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    root=Path(a.trained);out=Path(a.output);out.mkdir(parents=True,exist_ok=True);base=load(Path(a.base_module),'base_seed_audit');v5=load(Path(a.v5_module),'v5_seed_audit')
    compact=pd.read_parquet(root/'COMPACT_LABELED.parquet');compact['signal_date']=pd.to_datetime(compact.signal_date)
    pred0=pd.read_parquet(root/'OOS_TICKER_SCORES.parquet');pred0['signal_date']=pd.to_datetime(pred0.signal_date)
    rawparts=[]
    for year in sorted(pred0.signal_date.dt.year.unique()):
        te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker']).copy()
        if te.empty:continue
        q=te[['signal_date','ticker']].copy()
        X=te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)
        for seed in SEEDS:
            mp=root/'MODELS'/str(int(year))/f'COMPACT_SEED_{seed}.json'
            if not mp.exists():raise FileNotFoundError(mp)
            m=XGBRanker();m.load_model(mp);q[f'raw_{seed}']=m.predict(X)
        rawparts.append(q)
    raw=pd.concat(rawparts,ignore_index=True);raw=pred0[['signal_date','ticker']].merge(raw,on=['signal_date','ticker'],how='left',validate='one_to_one')
    for seed in SEEDS: raw[f'rank_{seed}']=raw.groupby('signal_date')[f'raw_{seed}'].rank(pct=True,method='average')
    raw['rank_each_mean']=raw[[f'rank_{s}' for s in SEEDS]].mean(axis=1)
    raw['raw_mean']=raw[[f'raw_{s}' for s in SEEDS]].mean(axis=1);raw['mean_raw_then_rank']=raw.groupby('signal_date').raw_mean.rank(pct=True,method='average')
    raw['raw_median']=raw[[f'raw_{s}' for s in SEEDS]].median(axis=1);raw['median_raw_then_rank']=raw.groupby('signal_date').raw_median.rank(pct=True,method='average')
    for s in SEEDS: raw[f'z_{s}']=zscore_group(raw[f'raw_{s}'],raw.signal_date)
    raw['zmean']=raw[[f'z_{s}' for s in SEEDS]].mean(axis=1);raw['zmean_then_rank']=raw.groupby('signal_date').zmean.rank(pct=True,method='average')
    raw.to_parquet(out/'COMPACT_SEED_RAW_AND_AGGREGATES.parquet',index=False)
    if 'compact_rank' not in pred0:raise RuntimeError('compact_rank missing from trained score panel')
    chk=pred0[['signal_date','ticker','compact_rank']].merge(raw[['signal_date','ticker','rank_each_mean']],on=['signal_date','ticker'])
    maxdiff=float((chk.compact_rank-chk.rank_each_mean).abs().max())
    if maxdiff>1e-10:raise RuntimeError(f'Current seed ensemble reconstruction mismatch: {maxdiff}')
    opred=pd.read_parquet(root/'OOS_OPPORTUNITY_SCORES.parquet');opred['signal_date']=pd.to_datetime(opred.signal_date)
    clusters=pd.read_csv(root/'DYNAMIC_CLUSTER_MEMBERSHIP.csv');clusters['signal_date']=pd.to_datetime(clusters.signal_date)
    cal=pd.read_csv(root/'MONTHLY_CALENDAR.csv');
    for c in ['signal_date','entry_date','exit_date']:
        if c in cal:cal[c]=pd.to_datetime(cal[c])
    mats={k:pd.read_parquet(root/f'{k.upper()}.parquet') for k in ['Open','High','Low','Close','Volume']}
    mem=pd.read_csv(root/'BASKET_MEMBERSHIP_500.csv');baskets=[tuple(g.ticker.astype(str).tolist()) for _,g in mem.groupby('basket',sort=True)]
    oldres=pd.read_csv(root/'BASKET_RESULTS_500.csv');old_base=float(oldres[oldres.strategy=='BASE'].cagr.mean())
    variants=['rank_each_mean','mean_raw_then_rank','median_raw_then_rank','zmean_then_rank'];rows=[];detail={}
    for variant in variants:
        p=pred0.drop(columns=['compact_rank'],errors='ignore').merge(raw[['signal_date','ticker',variant]].rename(columns={variant:'compact_rank'}),on=['signal_date','ticker'],how='left',validate='one_to_one')
        p['titanium_score_pre_macro']=.70*p.compact_rank+.30*p.tail_rank
        if 'macro_bonus' not in p.columns:
            p['macro_bonus']=np.where((p.macro_category==p.top_macro)&(p.macro_gap_z>=.75)&(p.tail_rank>=.80),.15,0.0)
        p['titanium_score']=p.titanium_score_pre_macro+p.macro_bonus
        idx,EB,ED,ER,active,margin,cond,*_=v5.simulate_all(baskets,p,opred,clusters,mats,cal)
        rec={'variant':variant,'router_active_months':int(np.asarray(active).sum())}
        rmse=0.0
        for name,(s,e) in PERIODS.items():
            cb=basket_cagr(EB,idx,s,e);cr=basket_cagr(ER,idx,s,e);bm=float(np.nanmean(cb));rr=float(np.nanmean(cr));rec[f'{name}_base']=bm;rec[f'{name}_router']=rr;rec[f'{name}_base_error_pp']=(bm-REF[name])*100
            if name in ('D1','D2','DEV'):rmse+=(bm-REF[name])**2
        rec['replication_rmse_pp']=float(np.sqrt(rmse/3)*100)
        z=p[p.signal_date==pd.Timestamp('2026-06-30')].sort_values('titanium_score',ascending=False).head(2);rec['checkpoint_top1']=str(z.iloc[0].ticker) if len(z) else '';rec['checkpoint_top2']=str(z.iloc[1].ticker) if len(z)>1 else ''
        rows.append(rec);detail[variant]=rec
    df=pd.DataFrame(rows).sort_values('replication_rmse_pp');df.to_csv(out/'SEED_ENSEMBLE_SUMMARY.csv',index=False)
    verify=float(df.loc[df.variant=='rank_each_mean','FULL_base'].iloc[0]);meta={'current_artifact_base_mean_cagr':old_base,'recomputed_rank_each_mean_full_base_cagr':verify,'reproduction_abs_error':abs(old_base-verify),'compact_rank_reconstruction_max_abs_error':maxdiff,'best_variant_by_D1_D2_DEV':df.iloc[0].variant,'best_rmse_pp':float(df.iloc[0].replication_rmse_pp),'reference':REF}
    (out/'SEED_ENSEMBLE_AUDIT.json').write_text(json.dumps(meta,indent=2));print(df.to_string(index=False));print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
