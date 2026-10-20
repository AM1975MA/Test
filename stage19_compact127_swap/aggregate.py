#!/usr/bin/env python3
"""Aggregate authentic same-vintage Stage19 V2 vs isolated Compact21 XGB127 replay."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',default='_results')
    p.add_argument('--out',default='_final')
    a=p.parse_args()
    root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    rows=[];ret=[]
    for i in (1,2,3):
        path=root/f'r{i}'
        doc=json.loads((path/'RESULT.json').read_text())
        if doc['status']!='TRUE_BASE_PARITY_PASS_AND_ISOLATED_COMPACT127_DONE':
            raise RuntimeError('Failed baseline gate')
        if doc['reference_vintage']!=i:raise RuntimeError('Vintage mismatch')
        if doc['baseline_parity_gate'].get('PASS') is not True:
            raise RuntimeError('Baseline not certified')
        if len(doc['xgb127_fit_audit'])!=10:raise RuntimeError('127 year fit missing')
        df=pd.read_csv(path/'PAIRED_DAILY_NAV.csv',parse_dates=['date'])
        b=df.baseline.to_numpy(float);c=df.challenger_compact127.to_numpy(float)
        dates=df.date
        if len(b)!=2366 or not(np.isfinite(b).all() and np.isfinite(c).all()):
            raise RuntimeError('Bad 2366-session original calendars')
        d=np.diff(np.log(np.r_[1.,c]))-np.diff(np.log(np.r_[1.,b]))
        ret.append(pd.DataFrame({'date':dates,'vintage':i,'paired_log_return_delta':d}))
        rows.append({'vintage':i,
            'BASE_cagr':doc['original_base']['cagr'],
            'Compact127_cagr':doc['challenger']['cagr'],
            'delta_cagr_pp':doc['delta_cagr_pp'],
            'BASE_maxdd':doc['original_base']['maxdd'],
            'Compact127_maxdd':doc['challenger']['maxdd'],
            'delta_maxdd_pp':doc['delta_maxdd_pp'],
            'top1_changed':doc['fraction_daily_top1_changed']})
    df=pd.DataFrame(rows)
    changes=pd.concat(ret,ignore_index=True).pivot(index='date',columns='vintage',values='paired_log_return_delta')
    if changes.isna().any().any():raise RuntimeError('Dates differ among original vintages')
    daily=changes.mean(axis=1).to_numpy(float)
    rng=np.random.default_rng(20261021)
    n=len(daily);block=21;reps=6000
    starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
    ix=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
    samples=daily[ix].mean(axis=1)*252
    aggregate={
        'status':'THREE_ORIGINAL_VINTAGE_EXACT_BASE_PARITY_AND_STAGE19_127_SWAP_COMPLETE',
        'provenance': 'Three preserved original data-vintages; correlation precludes independent samples',
        'mean_BASE_cagr':float(df.BASE_cagr.mean()),
        'mean_Compact127_cagr':float(df.Compact127_cagr.mean()),
        'mean_paired_cagr_delta_pp':float(df.delta_cagr_pp.mean()),
        'mean_BASE_maxdd':float(df.BASE_maxdd.mean()),
        'mean_Compact127_maxdd':float(df.Compact127_maxdd.mean()),
        'mean_delta_maxdd_pp':float(df.delta_maxdd_pp.mean()),
        'paired_annual_log_return_delta':float(daily.mean()*252),
        'paired_daily_21_session_block_bootstrap_ci95':list(map(float,np.quantile(samples,[.025,.975]))),
        'block_bootstrap_vintages_collapsed_by_date':True,
        'individual_vintages':rows,
        'no_unchanged_producer_family_claim':True,
        'only_modified_prediction_column':'compact21',
        'original_Stage19_V6_DDfirst_HighCAGR24_executable_source_untouched':True,
        'historically_inspected_not_prospective_holdout':True,
    }
    (out/'RESULT.json').write_text(json.dumps(aggregate,indent=2))
    df.to_csv(out/'PAIRED_VINTAGES.csv',index=False)
    changes.to_csv(out/'PAIRED_DAILY_LOG_RETURNS.csv',index_label='date')
    print('TRUE_STAGE19_THREE_VINTAGE_VERDICT',json.dumps(aggregate),flush=True)

if __name__=='__main__':main()
