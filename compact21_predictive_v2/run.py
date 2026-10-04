"""Frozen predictive-only comparison. No portfolio or feedback intervention."""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, os, sys, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/etf_trader_v2/src')]
from etf_trader.source_only import kernel as k
from compact21_learner_swap_v1 import learners as legacy
from compact21_learner_swap_v1.run_benchmark import evaluation_coverage, score_gap, compare_native
from ranker_stability_v1.run_ranker_benchmark_full import load, train_frame, align, stability, quality

VARIANTS=('BASE','RIDGE','LGBM_LAMBDARANK','LGBM_TOP5','ADDITIVE_RIDGE')
KEYS=['signal_date','ticker']
PAIRS=((1,2),(1,3),(2,3))
LINE='COMPACT21_PREDICTIVE_V2'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def fit(train,tests,variant,year,tmp,tag):
    if variant=='ADDITIVE_RIDGE':
        from compact21_predictive_v2.additive import fit_additive
        return fit_additive(train,tests,year,tmp,tag)
    if variant not in VARIANTS:raise ValueError('Unknown variant')
    if variant.startswith('LGBM'):
        original=legacy.LGBM_PARAMS.copy()
        try:
            legacy.LGBM_PARAMS['lambdarank_truncation_level']=8 if variant=='LGBM_TOP5' else 30
            return legacy.fit(train,tests,'LGBM_LAMBDARANK',year,tmp,tag)
        finally:legacy.LGBM_PARAMS.clear();legacy.LGBM_PARAMS.update(original)
    return legacy.fit(train,tests,variant,year,tmp,tag)

def predictions_frame(test,pred,repeat):
    cols=KEYS+['target_rank_21','exit_date_21']
    if not set(cols).issubset(test):raise ValueError('Missing mature outcome evidence')
    if 'fwd_ret_21' in test:cols.append('fwd_ret_21')
    result=test[cols].copy().rename(columns={'fwd_ret_21':'target_ret_21'})
    result['pred']=pred;result['vintage']=repeat
    return result

def numerical_gate():
    expected={'numpy':'2.3.5','pandas':'2.2.3','scikit-learn':'1.8.0','xgboost':'3.1.3','lightgbm':'4.6.0','scipy':'1.17.0','pyarrow':'23.0.1','numba':'0.65.1'}
    actual={key:importlib.metadata.version(key) for key in expected}
    if actual!=expected or sys.version_info[:2]!=(3,13):raise ValueError('Frozen Python/package environment mismatch')
    env={'PYTHONHASHSEED':'0','OPENBLAS_CORETYPE':'Haswell','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1',
         'NPY_DISABLE_CPU_FEATURES':'AVX512F,AVX512CD,AVX512_KNL,AVX512_KNM,AVX512_SKX,AVX512_CLX,AVX512_CNL,AVX512_ICL,AVX512_SPR'}
    if any(os.getenv(key)!=value for key,value in env.items()):raise ValueError('Frozen execution profile mismatch')
    from compact21_learner_swap_v1.prepare_ma3 import environment_contract
    result=environment_contract()
    from numpy._core._multiarray_umath import __cpu_features__
    result['effective_cpu_features']={key:bool(value) for key,value in __cpu_features__.items()}
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True,choices=VARIANTS)
    for i in (1,2,3):ap.add_argument(f'--r{i}',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--reference',required=True)
    ap.add_argument('--years',default=','.join(map(str,range(2017,2027))))
    a=ap.parse_args();years=list(map(int,a.years.split(',')))
    if len(set(years))!=len(years) or not years or not set(years)<=set(range(2017,2027)):raise ValueError('Invalid years')
    numeric=numerical_gate()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if (out/'RESULT.json').exists():raise ValueError('Output must be a fresh variant directory')
    inputs={i:Path(getattr(a,f'r{i}')) for i in (1,2,3)}
    hashes={str(i):sha(inputs[i]/'TI_COMPACT.parquet') for i in (1,2,3)}
    refdir=Path(a.reference)
    refs={v:json.loads(next(refdir.rglob(v+'.json')).read_text()) for v in ('BASE','RIDGE','LGBM_LAMBDARANK')}
    if any(ref['input_sha256']!=hashes for ref in refs.values()):raise ValueError('Frozen input identity mismatch')
    R={i:load(inputs[i]) for i in (1,2,3)}
    res={'status':'RUNNING','line':LINE,'variant':a.variant,'years':years,'input_sha256':hashes,
         'input_contract':refs['BASE']['input_contract'],'per_year':{},'environment':{n:importlib.metadata.version(n) for n in ('numpy','pandas','scikit-learn','xgboost','lightgbm','scipy','pyarrow')},
         'python':sys.version,'numeric_contract':numeric,
         'sources':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(list((ROOT/'compact21_predictive_v2').glob('*.py'))+list((ROOT/'compact21_learner_swap_v1').glob('*.py'))+list((ROOT/'vendor/etf_trader_v2/src/etf_trader/source_only').glob('*.py'))+[ROOT/'ranker_stability_v1/run_ranker_benchmark_full.py'])},
         'preregistration_sha256':sha(ROOT/'compact21_predictive_v2/PREREGISTRATION.md'),
         'negative_feedback_changed':False,'portfolio_evaluation':False,'production_adoption':False}
    (out/'INPUT_CONTRACT.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
    native=[];common_frames=[]
    with tempfile.TemporaryDirectory() as td:
        for year in years:
            trains={i:train_frame(R[i],year) for i in (1,2,3)}
            tests={}
            for i in (1,2,3):
                f=R[i];valid=f[k.F2D_FEATURES].notna().sum(axis=1)>=30
                tests[i]=f[(f.signal_date.dt.year==year)&(f.signal_date<='2026-06-30')&valid].sort_values(KEYS).reset_index(drop=True)
                if tests[i].duplicated(KEYS).any() or trains[i].duplicated(KEYS).any():raise ValueError('Duplicate keys')
            common=align([tests[i] for i in (1,2,3)])[1]
            if common.empty:raise ValueError('Empty common inference')
            pcs={};pns={};audits={};times={}
            for i in (1,2,3):
                p,au,_,t=fit(trains[i],[common,tests[i]],a.variant,year,Path(td),f'{year}_{i}')
                pcs[i],pns[i]=p;audits[str(i)]=au;times[str(i)]=t
                native.append(predictions_frame(tests[i],pns[i],i))
                cc=common[KEYS].copy();cc['pred']=pcs[i];cc['vintage']=i;common_frames.append(cc)
            pp,_,_,_=fit(trains[2],[common,tests[2]],a.variant,year,Path(td),f'{year}_det')
            det=all(x.tobytes()==y.tobytes() for x,y in zip(pp,[pcs[2],pns[2]]))
            if not det:raise ValueError('Independent common/native refit differs')
            qualities={}
            for i in (1,2,3):
                mask=(tests[i].target_rank_21.notna()&tests[i].exit_date_21.notna()&(tests[i].exit_date_21<=pd.Timestamp('2026-07-01'))).to_numpy()
                if not mask.any():raise ValueError('Empty mature quality')
                qualities[str(i)]=quality(tests[i].loc[mask],pns[i][mask])
            coverage=evaluation_coverage(trains,tests,common)
            if coverage!=refs['BASE']['per_year'][str(year)]['evaluation_coverage']:raise ValueError('Reference coverage differs')
            controls=None
            if a.variant in refs:
                expected=refs[a.variant]['per_year'][str(year)]
                controls={'legacy_quality_exact':qualities==expected['quality'],
                          'legacy_prediction_hashes_exact':all(audits[str(i)]['prediction_sha256']==expected['transforms'][str(i)]['prediction_sha256'] for i in (1,2,3))}
            res['per_year'][str(year)]={'common_inference':{f'{i}-{j}':stability(common[KEYS],pcs[i],pcs[j]) for i,j in PAIRS},
                'native_inference':compare_native(tests,pns),'common_score_gap':{f'{i}-{j}':score_gap(common[KEYS],pcs[i],pcs[j]) for i,j in PAIRS},
                'quality':qualities,'evaluation_coverage':coverage,'transforms':audits,'fit_seconds':times,'determinism_PASS':det,'legacy_control':controls}
            nf=pd.concat(native,ignore_index=True);cf=pd.concat(common_frames,ignore_index=True)
            nf.to_parquet(out/'NATIVE_PREDICTIONS.parquet',index=False);cf.to_parquet(out/'COMMON_PREDICTIONS.parquet',index=False)
            (out/'RESULT.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
            print(json.dumps({'variant':a.variant,'year':year,'quality':qualities,'legacy_control':controls}),flush=True)
    from compact21_predictive_v2.metrics import evaluate
    res['predictive']=evaluate(pd.concat(native,ignore_index=True),quality_exit_cutoff='2026-07-01')
    res['ALL_DETERMINISM_PASS']=all(z['determinism_PASS'] for z in res['per_year'].values())
    res['LEGACY_PARITY_PASS']=all(all(z['legacy_control'].values()) for z in res['per_year'].values()) if a.variant in refs else None
    res['files_sha256']={p.name:sha(p) for p in out.glob('*.parquet')}
    res['status']=LINE+'_COMPLETE'
    (out/'RESULT.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':main()
