#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

REF = {'D1':0.15023,'D2':0.22645,'DEV':0.18617,'FULL':0.21654064}

def load(path: Path):
    spec=importlib.util.spec_from_file_location('target_variant_runner', path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def basket_cagr(arr, dates, start, end):
    dates=pd.DatetimeIndex(dates)
    mask=(dates>=pd.Timestamp(start))&(dates<=pd.Timestamp(end))
    z=np.asarray(arr)[:,mask]
    d=dates[mask]
    if z.shape[1]<2: return np.full(z.shape[0],np.nan)
    years=(d[-1]-d[0]).days/365.25
    return np.power(z[:,-1]/z[:,0],1/years)-1

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--runner',required=True); ap.add_argument('--base-module',required=True); ap.add_argument('--v5-module',required=True); ap.add_argument('--data-dir',required=True); ap.add_argument('--target',required=True,choices=['monthly','d21','d42','d63','multi']); ap.add_argument('--output',required=True)
    a=ap.parse_args(); runner=load(Path(a.runner)); original=runner.add_labels
    def patched(panel,O,signal_dates):
        out=original(panel,O,signal_dates)
        if a.target=='d21': out['target_rank_pct']=out['target_rank_21']
        elif a.target=='d42': out['target_rank_pct']=out['target_rank_42']
        elif a.target=='d63': out['target_rank_pct']=out['target_rank_63']
        elif a.target=='multi': out['target_rank_pct']=out['target_multi_rank']
        out['target_top25']=(out['target_rank_pct']>=.75).astype('Int64')
        return out
    runner.add_labels=patched
    sys.argv=[str(a.runner),'--base-module',a.base_module,'--v5-module',a.v5_module,'--data-dir',a.data_dir,'--output',a.output,'--n-estimators','360','--n-baskets','500']
    runner.main()
    out=Path(a.output); z=np.load(out/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz'); dates=z['dates']; base=z['BASE']; router=z['ROUTER']
    periods={'D1':('2017-01-01','2019-12-31'),'D2':('2020-01-01','2022-12-31'),'DEV':('2017-01-01','2022-12-31'),'FULL':('2017-01-01','2026-12-31')}
    summary={'target':a.target}
    err=0.0
    for name,(s,e) in periods.items():
        cb=basket_cagr(base,dates,s,e); cr=basket_cagr(router,dates,s,e)
        summary[name]={'base_mean_cagr':float(np.nanmean(cb)),'router_mean_cagr':float(np.nanmean(cr)),'base_median_cagr':float(np.nanmedian(cb)),'reference_base_cagr':REF[name],'base_error_pp':float((np.nanmean(cb)-REF[name])*100)}
        if name in ('D1','D2','DEV'): err += (np.nanmean(cb)-REF[name])**2
    summary['replication_rmse_pp']=float(np.sqrt(err/3)*100)
    (out/'TARGET_FORENSIC_SUMMARY.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
