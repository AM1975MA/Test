#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

REF={'D1':0.15023,'D2':0.22645,'DEV':0.18617,'FULL':0.21654064}

def load(path: Path):
    spec=importlib.util.spec_from_file_location('d21_variant_runner',path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def basket_cagr(arr,dates,start,end):
    dates=pd.DatetimeIndex(dates); mask=(dates>=pd.Timestamp(start))&(dates<=pd.Timestamp(end)); z=np.asarray(arr)[:,mask]; d=dates[mask]
    if z.shape[1]<2: return np.full(z.shape[0],np.nan)
    years=(d[-1]-d[0]).days/365.25
    return np.power(z[:,-1]/z[:,0],1/years)-1

def encode_relevance(df,mode):
    p=pd.to_numeric(df['target_rank_21'],errors='coerce').clip(0,1)
    if mode=='pct100': return p
    if mode=='quintile0': return (np.ceil(p*5)-1).clip(0,4)/100.0
    if mode=='quintile1': return np.ceil(p*5).clip(1,5)/100.0
    if mode=='decile0': return (np.ceil(p*10)-1).clip(0,9)/100.0
    if mode=='top5custom':
        pos=df.groupby('signal_date')['target_rank_21'].rank(ascending=False,method='min')
        rel=np.select([pos.eq(1),pos.eq(2),pos.eq(3),pos.isin([4,5])],[5,3,2,1],default=0).astype(float)
        rel[p.isna()]=np.nan
        return pd.Series(rel,index=df.index)/100.0
    raise ValueError(mode)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--runner',required=True); ap.add_argument('--base-module',required=True); ap.add_argument('--v5-module',required=True); ap.add_argument('--data-dir',required=True); ap.add_argument('--relevance',required=True,choices=['pct100','quintile0','quintile1','decile0','top5custom']); ap.add_argument('--output',required=True); a=ap.parse_args()
    runner=load(Path(a.runner)); orig_labels=runner.add_labels; orig_fit=runner.fit_predict
    def labels21(panel,O,signal_dates):
        out=orig_labels(panel,O,signal_dates)
        out['target_rank_pct']=encode_relevance(out,a.relevance)
        out['target_top25']=(pd.to_numeric(out['target_rank_21'],errors='coerce')>=.75).astype('Int64')
        return out
    def fit21(compact,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir):
        c=compact.copy()
        if 'exit_date_21' not in c.columns: raise RuntimeError('exit_date_21 missing: cannot certify D21 maturity')
        c['exit_date']=c['exit_date_21']
        return orig_fit(c,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir)
    def forensic_package(out,*_args,**_kwargs):
        p=Path(out)/'_FORENSIC_PLACEHOLDER.zip'; p.write_bytes(b'forensic-only'); return p
    runner.add_labels=labels21; runner.fit_predict=fit21; runner.package=forensic_package
    sys.argv=[str(a.runner),'--base-module',a.base_module,'--v5-module',a.v5_module,'--data-dir',a.data_dir,'--output',a.output,'--n-estimators','360','--n-baskets','500']
    runner.main()
    out=Path(a.output); z=np.load(out/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz'); dates=z['dates']; base=z['BASE']; router=z['ROUTER']
    periods={'D1':('2017-01-01','2019-12-31'),'D2':('2020-01-01','2022-12-31'),'DEV':('2017-01-01','2022-12-31'),'FULL':('2017-01-01','2026-12-31')}
    summary={'horizon':'21d','maturity':'exit_date_21 < cutoff','relevance':a.relevance}; err=0.0
    for name,(s,e) in periods.items():
        cb=basket_cagr(base,dates,s,e); cr=basket_cagr(router,dates,s,e); bm=float(np.nanmean(cb)); rm=float(np.nanmean(cr))
        summary[name]={'base_mean_cagr':bm,'router_mean_cagr':rm,'base_median_cagr':float(np.nanmedian(cb)),'reference_base_cagr':REF[name],'base_error_pp':float((bm-REF[name])*100)}
        if name in ('D1','D2','DEV'): err+=(bm-REF[name])**2
    summary['replication_rmse_pp']=float(np.sqrt(err/3)*100)
    (out/'D21_RELEVANCE_FORENSIC_SUMMARY.json').write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
