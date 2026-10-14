"""Diagnosi senza fit delle differenze raw→Compact; nessuna tolleranza adottata."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import importlib.metadata
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from paper_ltr_v2.replay import rebuild_compact,verify_cache,sha,KEYS,FEATURES


def numeric_difference(left,right):
    a=np.asarray(left,dtype=np.float64);b=np.asarray(right,dtype=np.float64)
    if a.shape!=b.shape:raise ValueError('Supporti numerici diversi')
    fa=np.isfinite(a);fb=np.isfinite(b);both=fa&fb;different=both&(a!=b)
    x=a[different];y=b[different]
    if len(x):
        absolute=np.abs(x-y);denom=np.maximum(np.abs(x),np.abs(y))
        relative=np.divide(absolute,denom,out=np.zeros_like(absolute),where=denom>0)
        # Rappresentazione monotona IEEE754, inclusi numeri negativi.
        sign=np.uint64(1<<63)
        ax=x.view(np.uint64);by=y.view(np.uint64)
        ao=np.where((ax&sign)!=0,~ax,ax|sign);bo=np.where((by&sign)!=0,~by,by|sign)
        ulp=np.maximum(ao,bo)-np.minimum(ao,bo)
        quantiles=lambda v:[float(np.quantile(v,q)) for q in (.5,.9,.99)]
        maxima=dict(max_absolute_difference=float(absolute.max()),max_relative_difference=float(relative.max()),
                    max_ulp_difference=int(ulp.max()),absolute_difference_p50_p90_p99=quantiles(absolute),
                    relative_difference_p50_p90_p99=quantiles(relative),ulp_difference_p50_p90_p99=quantiles(ulp),
                    differences_gt1ulp=int((ulp>1).sum()),differences_gt16ulp=int((ulp>16).sum()))
    else:
        maxima=dict(max_absolute_difference=0.,max_relative_difference=0.,max_ulp_difference=0,
                    absolute_difference_p50_p90_p99=[0.]*3,relative_difference_p50_p90_p99=[0.]*3,
                    ulp_difference_p50_p90_p99=[0.]*3,differences_gt1ulp=0,differences_gt16ulp=0)
    return dict(rows=int(a.size),finite_mask_differences=int((fa!=fb).sum()),
                nonfinite_differences=int(((~fa)&(~fb)&~((np.isnan(a)&np.isnan(b))|(a==b))).sum()),
                finite_value_differences=int(different.sum()),**maxima)


def compare_panels(original,rebuilt,out):
    a=original.sort_values(KEYS).reset_index(drop=True);b=rebuilt.sort_values(KEYS).reset_index(drop=True)
    if any(f[KEYS].isna().any().any() or f.duplicated(KEYS).any() for f in (a,b)):
        raise ValueError('Chiavi ambigue')
    keys_equal=a[KEYS].equals(b[KEYS])
    report=dict(keys_exact=keys_equal,original_rows=len(a),rebuilt_rows=len(b),
                original_tickers=int(a.ticker.nunique()),rebuilt_tickers=int(b.ticker.nunique()),features=[])
    if not keys_equal:
        a[KEYS].merge(b[KEYS],how='outer',indicator=True).to_csv(out/'KEY_DIFFERENCES.csv',index=False)
        return report
    rows=[];samples=[]
    for feature in [*FEATURES,'target_rank_21','fwd_ret_21']:
        if feature not in a or feature not in b:raise ValueError(f'Colonna mancante: {feature}')
        x=a[feature].to_numpy(float);y=b[feature].to_numpy(float)
        row=dict(feature=feature,**numeric_difference(x,y))
        ar=a.groupby('signal_date')[feature].rank(method='average',pct=True)
        br=b.groupby('signal_date')[feature].rank(method='average',pct=True)
        ranks=numeric_difference(ar.to_numpy(),br.to_numpy())
        row['cross_section_rank_differences']=ranks['finite_value_differences']
        row['cross_section_rank_mask_differences']=ranks['finite_mask_differences']
        changed=(np.isfinite(x)!=np.isfinite(y))|(np.isfinite(x)&np.isfinite(y)&(x!=y))
        for ix in np.flatnonzero(changed)[:10]:
            samples.append(dict(feature=feature,signal_date=str(a.signal_date.iloc[ix]),ticker=str(a.ticker.iloc[ix]),
                original=None if not np.isfinite(x[ix]) else float(x[ix]),rebuilt=None if not np.isfinite(y[ix]) else float(y[ix]),
                original_hex=float(x[ix]).hex(),rebuilt_hex=float(y[ix]).hex()))
        rows.append(row)
    report['features']=rows
    report['date_column_differences']={}
    for column in ('entry_date','exit_date_21'):
        x=pd.to_datetime(a[column]);y=pd.to_datetime(b[column])
        report['date_column_differences'][column]=int((~((x==y)|(x.isna()&y.isna()))).sum())
    pd.DataFrame(rows).to_csv(out/'FEATURE_DIFFERENCES.csv',index=False)
    pd.DataFrame(samples).to_csv(out/'FIRST_DIFFERENCE_SAMPLES.csv',index=False)
    report['all_numeric_and_dates_exact']=all(r['finite_value_differences']==r['finite_mask_differences']==r['nonfinite_differences']==0 for r in rows) and not any(report['date_column_differences'].values())
    return report


def worker(raw,out):
    out.mkdir(parents=True,exist_ok=False)
    rebuilt=rebuild_compact(raw);rebuilt.to_parquet(out/'REBUILT_COMPACT.parquet',index=False)
    from numpy._core._multiarray_umath import __cpu_features__
    env=dict(versions={p:importlib.metadata.version(p) for p in ('numpy','pandas','scipy','numba')},
             cpu_features={k:bool(v) for k,v in __cpu_features__.items()},
             environment={k:os.getenv(k) for k in ('OPENBLAS_CORETYPE','NPY_DISABLE_CPU_FEATURES','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')},
             pandas_use_bottleneck=pd.get_option('compute.use_bottleneck'),pandas_use_numexpr=pd.get_option('compute.use_numexpr'))
    (out/'ENVIRONMENT.json').write_text(json.dumps(env,indent=2)+'\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--baseline');ap.add_argument('--ti-panel');ap.add_argument('--repeat',type=int,choices=(1,2,3));ap.add_argument('--worker',action='store_true')
    a=ap.parse_args();raw=Path(a.raw).resolve();out=Path(a.out).resolve()
    if a.worker:worker(raw,out);return
    if not a.ti_panel:ap.error('Diagnosi richiede --ti-panel')
    out.mkdir(parents=True,exist_ok=False)
    if a.baseline:
        _,_,_,audit=verify_cache(Path(a.baseline),raw)
        raw_hashes=audit['raw_files_sha256']
    else:raw_hashes={p.name:sha(p) for p in sorted(raw.glob('*.csv'))}
    if not raw_hashes:raise ValueError('Nessun raw CSV')
    panel=pd.read_parquet(a.ti_panel)
    result=dict(status='PAPER_LTR_V2_LINKAGE_NUMERIC_DIAGNOSTIC_COMPLETE',repeat=a.repeat,new_fits_executed=0,
        original_ti_sha256=sha(a.ti_panel),raw_files_sha256=raw_hashes,baseline_cache_verified=bool(a.baseline),profiles={},
        source_sha256={p:sha(ROOT/p) for p in ('paper_ltr_v2/diagnose_linkage.py','paper_ltr_v2/replay.py',
            'vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py','vendor/etf_trader_v2/src/etf_trader/source_only/raw_io.py')},
        certification_PASS=False,tolerance_changed=False,source_changed=False)
    for profile in ('current_frozen','historical_dispatch'):
        env=os.environ.copy()
        if profile=='historical_dispatch':
            env.pop('OPENBLAS_CORETYPE',None);env.pop('NPY_DISABLE_CPU_FEATURES',None)
            for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[name]='2'
        folder=out/profile
        subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker','--raw',str(raw),'--out',str(folder)],env=env,check=True)
        rebuilt=pd.read_parquet(folder/'REBUILT_COMPACT.parquet')
        report=compare_panels(panel,rebuilt,folder)
        report['rebuilt_parquet_sha256']=sha(folder/'REBUILT_COMPACT.parquet')
        report['environment']=json.loads((folder/'ENVIRONMENT.json').read_text())
        result['profiles'][profile]=report
        (out/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(json.dumps(dict(profile=profile,keys_exact=report['keys_exact'],all_exact=report.get('all_numeric_and_dates_exact'),
            differing_features=[dict(feature=r['feature'],count=r['finite_value_differences'],max_abs=r['max_absolute_difference'],max_ulp=r['max_ulp_difference'],rank_diffs=r['cross_section_rank_differences']) for r in report['features'] if r['finite_value_differences'] or r['finite_mask_differences']]),indent=2))


if __name__=='__main__':main()
