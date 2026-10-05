"""Frozen training X/y interventions; no new recipe or portfolio intervention."""
from __future__ import annotations
import argparse,hashlib,json,sys,tempfile
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/etf_trader_v2/src')]
from compact21_predictive_v2.run import fit,numerical_gate
from compact21_predictive_v2.summarize import normalized_numeric
from compact21_learner_swap_v1.learners import array_hash,matrix,validate
from ranker_stability_v1.run_ranker_benchmark_full import load,train_frame,align
from etf_trader.source_only import kernel as k

MODELS=('BASE','RIDGE','LGBM_LAMBDARANK','ADDITIVE_RIDGE')
KEYS=['signal_date','ticker']
LINE='COMPACT21_FACTORIAL_V1'
PAIRS=((1,2),(1,3),(2,3))

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def keys_hash(frame):return hashlib.sha256(frame[KEYS].sort_values(KEYS).to_csv(index=False,date_format='%Y-%m-%dT%H:%M:%S',lineterminator='\n').encode()).hexdigest()

def mix_rows(feature_donor,target_donor,year):
    """Require both donors mature and exactly key matched before any transfer."""
    a=feature_donor.sort_values(KEYS).reset_index(drop=True)
    b=target_donor.sort_values(KEYS).reset_index(drop=True)
    validate(a,[a],year);validate(b,[b],year)
    if not a[KEYS].equals(b[KEYS]):raise ValueError('Training donor cohorts differ')
    z=a.copy()
    z['target_rank_21']=b.target_rank_21.to_numpy()
    z['exit_date_21']=b.exit_date_21.to_numpy()
    validate(z,[z],year)
    if array_hash(matrix(z).to_numpy())!=array_hash(matrix(a).to_numpy()):raise ValueError('Feature donor changed')
    return z

def verify_prepared(trains,common,prepared,year,hashes):
    if hashes!=prepared['input_sha256']:raise ValueError('Prepared source mismatch')
    if not prepared['all_pair_cohorts_equal']:raise ValueError('Prepared design requires cohort equality')
    for i,t in trains.items():
        a=prepared['training'][f'{year}_r{i}']
        y=t.target_rank_21.to_numpy(float)
        checks=(keys_hash(t)==a['keys_sha256_lf'],len(t)==a['rows'],t.signal_date.nunique()==a['queries'],array_hash(matrix(t).to_numpy())==a['matrix_sha256'],
          array_hash(y)==a['continuous_labels_sha256'],array_hash(np.rint(y*100).astype(np.int64))==a['integer_labels_sha256'])
        if not all(checks):raise ValueError('Reconstructed mature training differs')
    for i,j in PAIRS:
        a=prepared['pairs'][f'{year}_{i}-{j}']
        if keys_hash(trains[i])!=keys_hash(trains[j]) or len(trains[i])!=a['common_rows']:raise ValueError('Unexplained cohort change')
        if keys_hash(common)!=a['inference_keys_sha256_lf'] or len(common)!=a['inference_rows'] or array_hash(matrix(common).to_numpy())!=a['inference_matrix_sha256']:raise ValueError('Frozen common inference differs')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model',required=True,choices=MODELS);ap.add_argument('--year',required=True,type=int)
    for i in (1,2,3):ap.add_argument(f'--r{i}',required=True)
    ap.add_argument('--reference',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    if a.year not in range(2017,2027):raise ValueError('Unregistered year')
    numeric=numerical_gate();normalized_numeric(numeric)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise ValueError('Fresh output required')
    paths={i:Path(getattr(a,f'r{i}')) for i in (1,2,3)}
    hashes={str(i):sha(paths[i]/'TI_COMPACT.parquet') for i in (1,2,3)}
    refpath=next(Path(a.reference).rglob('RESULT.json'));reference=json.loads(refpath.read_text())
    if reference['variant']!=a.model or reference['status']!='COMPACT21_PREDICTIVE_V2_COMPLETE' or hashes!=reference['input_sha256']:
        raise ValueError('Wrong original control reference')
    for name,digest in reference['files_sha256'].items():
        if sha(refpath.parent/name)!=digest:raise ValueError('Altered old reference vectors')
    if normalized_numeric(numeric)!=normalized_numeric(reference['numeric_contract']):raise ValueError('Old control numerical profile differs')
    prepared=json.loads((ROOT/'compact21_factorial_v1/PREPARED_CONTRACT.json').read_text())
    frames={i:load(paths[i]) for i in paths};trains={i:train_frame(frames[i],a.year) for i in paths}
    tests={}
    for i,f in frames.items():
        eligible=f[k.F2D_FEATURES].notna().sum(axis=1)>=30
        tests[i]=f[(f.signal_date.dt.year==a.year)&(f.signal_date<='2026-06-30')&eligible].sort_values(KEYS).reset_index(drop=True)
    common=align([tests[i] for i in (1,2,3)])[1]
    verify_prepared(trains,common,prepared,a.year,hashes)
    control_vectors=pd.read_parquet(refpath.parent/'COMMON_PREDICTIONS.parquet')
    cov=reference['per_year'][str(a.year)]['evaluation_coverage']
    if keys_hash(common)!=cov['common_keys_sha256']:raise ValueError('Original inference key mismatch')
    source_paths=[ROOT/'compact21_learner_swap_v1/learners.py',ROOT/'compact21_predictive_v2/additive.py',ROOT/'compact21_predictive_v2/run.py',
      ROOT/'ranker_stability_v1/run_ranker_benchmark_full.py']+list((ROOT/'vendor/etf_trader_v2/src/etf_trader/source_only').glob('*.py'))
    inherited={p.relative_to(ROOT).as_posix():sha(p) for p in source_paths}
    if any(reference['sources'].get(path)!=digest for path,digest in inherited.items()):raise ValueError('Frozen fit source changed')
    result={'status':'RUNNING','line':LINE,'model':a.model,'year':a.year,'input_sha256':hashes,'numeric_contract':numeric,
      'fit_sources':inherited,'factorial_sources':{p.name:sha(p) for p in (ROOT/'compact21_factorial_v1').glob('*.py')},
      'protocol_sha256':sha(ROOT/'compact21_factorial_v1/PROTOCOL.md'),'prepared_contract_sha256':sha(ROOT/'compact21_factorial_v1/PREPARED_CONTRACT.json'),
      'old_run':37229180477,'reference_sha256':sha(refpath),'inference_keys_sha256':keys_hash(common),
      'train_keys_sha256':{str(i):keys_hash(t) for i,t in trains.items()},'cells':{},'negative_feedback_changed':False,'production_adoption':False}
    (out/'INPUT_CONTRACT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    cols=KEYS+['target_rank_21','exit_date_21']+(['fwd_ret_21'] if 'fwd_ret_21' in common else [])
    predictions=common[cols].copy().rename(columns={'fwd_ret_21':'target_ret_21'})
    with tempfile.TemporaryDirectory() as td:
        for x in (1,2,3):
            for y in (1,2,3):
                cell=f'X{x}Y{y}';train=mix_rows(trains[x],trains[y],a.year)
                inference=[common[KEYS+list(k.F2D_FEATURES)],tests[x][KEYS+list(k.F2D_FEATURES)]]
                pp,audit,_,seconds=fit(train,inference,a.model,a.year,Path(td),cell)
                qq,refit_audit,_,refit_seconds=fit(train,inference,a.model,a.year,Path(td),cell+'_refit')
                if any(p.tobytes()!=q.tobytes() for p,q in zip(pp,qq)):raise ValueError('Independent refit not exact')
                parity=None
                if x==y:
                    old=control_vectors[(control_vectors.vintage==x)&(control_vectors.signal_date.dt.year==a.year)].sort_values(KEYS).reset_index(drop=True)
                    if not old[KEYS].equals(common[KEYS].reset_index(drop=True)):raise ValueError('Diagonal control keys differ')
                    parity=pp[0].tobytes()==old.pred.to_numpy().tobytes()
                    if not parity:raise ValueError('Diagonal original prediction mismatch')
                predictions[cell]=pp[0]
                result['cells'][cell]={'feature_repeat':x,'target_repeat':y,'audit':audit,'refit_audit':refit_audit,'determinism_PASS':True,
                  'diagonal_control_PASS':parity,'prediction_sha256':array_hash(pp[0]),'fit_seconds':seconds,'refit_seconds':refit_seconds}
                predictions.to_parquet(out/'PREDICTIONS.parquet',index=False)
                (out/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
                print(json.dumps({'model':a.model,'year':a.year,'cell':cell,'determinism_PASS':True,'diagonal_control_PASS':parity}),flush=True)
    result.update(status=LINE+'_COMPLETE',prediction_file_sha256=sha(out/'PREDICTIONS.parquet'))
    (out/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':main()
