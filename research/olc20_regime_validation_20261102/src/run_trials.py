"""Execute all fixed trials, checkpoint every annual fit; no stopping on outcomes."""
from __future__ import annotations
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ.setdefault(key,'1')
from pathlib import Path
import argparse,hashlib,json,time
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np,pandas as pd
from paths import ROOT,P16
from experiment import load_groups,dump
from nested_validation import fit_annual
from score_validation import build_scores

TRIALS={'AUTH':{},'STATIC':{'contextual':False},
        **{f'NULL{s}':{'seed':s} for s in range(20001,20051)},
        'PENALTY_HALF':{'grid_factor':.5},'PENALTY_DOUBLE':{'grid_factor':2.},
        'OMIT_TREND':{'omit':0},'OMIT_VOL':{'omit':1},'OMIT_LEADERSHIP':{'omit':2}}

def source_hash():
    paths=[ROOT/'src'/s for s in ('context_views.py','nested_validation.py','score_validation.py','run_trials.py')]
    paths+=[P16/'src'/s for s in ('context_model.py','experiment.py','revalue_memory.py','parent_chrono.py')]
    return hashlib.sha256(b''.join(p.read_bytes() for p in paths)).hexdigest()

def run_trial(name):
    if name not in TRIALS:raise ValueError('Unregistered procedure')
    t=time.time();spec=TRIALS[name];g,f,c=load_groups();models={};sighash=source_hash()
    folder=ROOT/'models'/name;folder.mkdir(parents=True,exist_ok=True)
    for year in range(2021,2027):
        path=folder/f'{year}.json'
        if path.exists():
            saved=json.loads(path.read_text())
            if saved['source_hash']!=sighash:raise ValueError('Checkpoint source hash mismatch')
            model=saved['model']
        else:
            model,audit=fit_annual(g,year,**spec)
            dump(path,dict(trial=name,source_hash=sighash,spec=spec,model=model,audit=audit))
        models[year]=model
    outputs,trace=build_scores(g,f,c,models,omit=spec.get('omit'))
    target=ROOT/'results'/'trials'/name;target.mkdir(parents=True,exist_ok=True)
    for m,df in outputs.items():df.to_csv(target/f'{m}_SCORES.csv.gz',index=False)
    trace.to_csv(target/'PARAMETERS.csv',index=False)
    info=dict(trial=name,final_models=len(models),inner_fits=sum(m['inner_fits'] for m in models.values()),
        starts=3*(len(models)+sum(m['inner_fits'] for m in models.values())),seconds=time.time()-t,source_hash=sighash)
    if name in ('AUTH','STATIC'):
        refname='TOP2_CONTEXT' if name=='AUTH' else 'TOP2_STATIC'
        maxerr=0.
        for year,m in models.items():
            old=json.loads((P16/f'models/{year}_{refname}.json').read_text())
            maxerr=max(maxerr,float(np.max(abs(np.array(old['theta'])-np.array(m['theta'])))))
            assert old['penalty']==m['penalty']
        for market,df in outputs.items():
            ref=pd.read_csv(P16/f'results/{market}_SCORES.csv.gz',float_precision='round_trip')
            for stage in ('CURRENT','SMOOTH','FUSION'):
                np.testing.assert_allclose(df[stage],ref[refname+'_REVALUE_'+stage],atol=2e-14,rtol=0,equal_nan=True)
        info['maximum_parameter_error_to_parent']=maxerr
        assert maxerr<1e-12
    dump(target/'COMPLETE.json',info)
    return info

def lag_scores():
    g,f,c=load_groups();models={y:json.loads((ROOT/f'models/AUTH/{y}.json').read_text())['model'] for y in range(2021,2027)}
    out,tr=build_scores(g,f,c,models,lag=True);folder=ROOT/'results/trials/CONTEXT_LAG';folder.mkdir(exist_ok=True)
    for m,df in out.items():df.to_csv(folder/f'{m}_SCORES.csv.gz',index=False)
    tr.to_csv(folder/'PARAMETERS.csv',index=False);dump(folder/'COMPLETE.json',dict(trial='CONTEXT_LAG',new_fits=0))

def main(names,workers):
    start=time.time();done=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        jobs={pool.submit(run_trial,n):n for n in names}
        for job in as_completed(jobs):
            result=job.result();done.append(result)
            print(json.dumps(result),flush=True)
            dump(ROOT/'results/TRAIN_PROGRESS.json',dict(completed_this_run=len(done),planned_this_run=len(names),seconds=time.time()-start))
    if set(TRIALS).issubset({p.parent.name for p in (ROOT/'results/trials').glob('*/COMPLETE.json')}):lag_scores()
    return done
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--trials',nargs='*');p.add_argument('--workers',type=int,default=3);a=p.parse_args()
    main(a.trials if a.trials else list(TRIALS),a.workers)
