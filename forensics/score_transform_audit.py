#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

REF={'D1':0.15023,'D2':0.22645,'DEV':0.18617,'FULL':0.21654064}
PERIODS={'D1':('2017-01-01','2019-12-31'),'D2':('2020-01-01','2022-12-31'),'DEV':('2017-01-01','2022-12-31'),'FULL':('2017-01-01','2026-12-31')}

def load(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def bcagr(arr,dates,s,e):
    dates=pd.DatetimeIndex(dates);m=(dates>=pd.Timestamp(s))&(dates<=pd.Timestamp(e));z=np.asarray(arr)[:,m];d=dates[m]
    if z.shape[1]<2:return np.full(z.shape[0],np.nan)
    y=(d[-1]-d[0]).days/365.25;return np.power(z[:,-1]/z[:,0],1/y)-1

def rankx(df,col): return df.groupby('signal_date')[col].rank(pct=True,method='average')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--trained',required=True);ap.add_argument('--v5-module',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    root=Path(a.trained);out=Path(a.output);out.mkdir(parents=True,exist_ok=True);v5=load(Path(a.v5_module),'v5_score_audit')
    pred0=pd.read_parquet(root/'OOS_TICKER_SCORES.parquet');pred0.signal_date=pd.to_datetime(pred0.signal_date)
    opred=pd.read_parquet(root/'OOS_OPPORTUNITY_SCORES.parquet');opred.signal_date=pd.to_datetime(opred.signal_date)
    clusters=pd.read_csv(root/'DYNAMIC_CLUSTER_MEMBERSHIP.csv');clusters.signal_date=pd.to_datetime(clusters.signal_date)
    cal=pd.read_csv(root/'MONTHLY_CALENDAR.csv');
    for c in ['signal_date','entry_date','exit_date']:
        if c in cal:cal[c]=pd.to_datetime(cal[c])
    mats={k:pd.read_parquet(root/f'{k.upper()}.parquet') for k in ['Open','High','Low','Close','Volume']}
    mem=pd.read_csv(root/'BASKET_MEMBERSHIP_500.csv');baskets=[tuple(g.ticker.astype(str).tolist()) for _,g in mem.groupby('basket',sort=True)]
    old=pd.read_csv(root/'BASKET_RESULTS_500.csv');oldbase=float(old[old.strategy=='BASE'].cagr.mean())
    p=pred0.copy();
    if 'titanium_score_pre_macro' not in p:p['titanium_score_pre_macro']=.70*p.compact_rank+.30*p.tail_rank
    if 'macro_bonus' not in p.columns:p['macro_bonus']=0.0
    p['blend_rank']=rankx(p,'titanium_score_pre_macro')
    p['current_final']=p.titanium_score_pre_macro+p.macro_bonus
    p['current_final_rank']=rankx(p,'current_final')
    # macro applied to ranked blend; optionally re-rank after bonus
    p['rankblend_plus_macro']=p.blend_rank+p.macro_bonus
    p['rankblend_plus_macro_rank']=rankx(p,'rankblend_plus_macro')
    variants={
      'current':'current_final',
      'rank_blend_then_macro':'rankblend_plus_macro',
      'rank_final_current':'current_final_rank',
      'rank_blend_macro_then_rerank':'rankblend_plus_macro_rank',
      'rank_blend_no_macro':'blend_rank',
    }
    rows=[]
    for name,col in variants.items():
        q=pred0.copy();q['titanium_score']=p[col].to_numpy();q['titanium_score_pre_macro']=q['titanium_score']
        idx,EB,ED,ER,active,margin,cond,*_=v5.simulate_all(baskets,q,opred,clusters,mats,cal)
        rec={'variant':name,'router_active_months':int(np.asarray(active).sum()),'mean_margin':float(np.nanmean(margin)),'frac_margin_ge_012':float(np.nanmean(np.asarray(margin)>=.12))};rm=0.0
        for per,(s,e) in PERIODS.items():
            cb=bcagr(EB,idx,s,e);cr=bcagr(ER,idx,s,e);bm=float(np.nanmean(cb));rr=float(np.nanmean(cr));rec[f'{per}_base']=bm;rec[f'{per}_router']=rr;rec[f'{per}_err_pp']=(bm-REF[per])*100
            if per in ('D1','D2','DEV'):rm+=(bm-REF[per])**2
        rec['rmse_pp']=float(np.sqrt(rm/3)*100)
        z=q[q.signal_date==pd.Timestamp('2026-06-30')].sort_values('titanium_score',ascending=False).head(2);rec['top1']=str(z.iloc[0].ticker) if len(z) else '';rec['top2']=str(z.iloc[1].ticker) if len(z)>1 else ''
        rows.append(rec)
    df=pd.DataFrame(rows).sort_values('rmse_pp');df.to_csv(out/'SCORE_TRANSFORM_SUMMARY.csv',index=False)
    cur=float(df.loc[df.variant=='current','FULL_base'].iloc[0]);meta={'saved_base_full_cagr':oldbase,'recomputed_current_base_full_cagr':cur,'reproduction_abs_error':abs(oldbase-cur),'best_variant':str(df.iloc[0].variant),'best_rmse_pp':float(df.iloc[0].rmse_pp),'reference':REF};(out/'SCORE_TRANSFORM_AUDIT.json').write_text(json.dumps(meta,indent=2));print(df.to_string(index=False));print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
