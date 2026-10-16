"""Fixed90-fit raw context neural walk-forward; no economic retuning."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from raw_patterns_v1.full import panel,expected_keys,cohort_meta,forward_saved,verify_full_fingerprints,VARIANT
from raw_patterns_v1.model import learner as v1
from raw_patterns_v1.patterns import split_dates
from raw_patterns_v1.run import sha,write
from compact21_predictive_v2.metrics import evaluate

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw',required=True);ap.add_argument('--bases',required=True);ap.add_argument('--ti',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out)
    if out.exists() and any(out.iterdir()):raise ValueError('Output must be new')
    out.mkdir(parents=True,exist_ok=True);(out/'models').mkdir()
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in Path(__file__).parent.glob('*.py')}
    sources['paper_ltr_v1/learner.py']=sha(ROOT/'paper_ltr_v1/learner.py')
    r=dict(status='RAW_NEURAL_RUNNING',variant=VARIANT,out_dir=str(out),per_year={str(y):dict(transforms={}) for y in range(2017,2027)},
        source_sha256=sources,recipe=v1.RECIPE,protocol_sha256=sha(Path(__file__).with_name('FULL_PROTOCOL.md')),
        raw_files_sha256={},input_sha256={},input_role='TI hashes reference replay coverage only; never neural fit inputs',new_fits_executed=0,production_adoption=False)
    predictions=[];seed_frames={s:[] for s in (101,202,303)};started=time.perf_counter()
    all_panels={}
    for i in (1,2,3):
        cache=Path(a.bases)/f'r{i}';contracts=list(cache.rglob('INPUT_CONTRACT.json'))
        if len(contracts)!=1:raise ValueError('Ambiguous baseline raw contract')
        contract=json.loads(contracts[0].read_text());r['raw_files_sha256'][str(i)]=contract['raw_files_sha256']
        f,x,coverage=panel(Path(a.raw)/f'_repeat{i}',r['raw_files_sha256'][str(i)])
        write(out/f'RAW_COVERAGE_r{i}.json',coverage)
        path=Path(a.ti)/f'r{i}'/'TI_COMPACT.parquet';ti=pd.read_parquet(path);r['input_sha256'][str(i)]=sha(path)
        for c in ('signal_date','exit_date_21'):ti[c]=pd.to_datetime(ti[c])
        all_panels[i]=ti
        for year in range(2017,2027):
            sub,val,test=split_dates(f,year)
            pd.testing.assert_frame_equal(test[v1.KEYS].reset_index(drop=True),expected_keys(ti,year),check_exact=True)
            if not (sub.exit_date_21<val.signal_date.min()).all() or not (val.exit_date_21<pd.Timestamp(year,1,1)).all():raise ValueError('Maturity/purge failed')
            state=v1.fit_transform_state(x[sub.index]);sx=v1.transform(x[sub.index],state);vx=v1.transform(x[val.index],state);tx=v1.transform(x[test.index],state)
            meta=cohort_meta(sub,val,test,x,state);scores=[];meta.update(saved_models=[],seeds=[])
            for seed in (101,202,303):
                p,audit=v1.train_network(sx,v1.decile_labels(sub),v1.query_indices(sub),vx,v1.decile_labels(val),v1.query_indices(val),seed)
                score=v1.forward(tx,p)[0];np.testing.assert_allclose(score,forward_saved(tx,p),rtol=0,atol=1e-12)
                if not np.isfinite(score).all():raise ValueError('Nonfinite predictions')
                path=out/'models'/f'{year}_r{i}_{seed}.npz';np.savez(path,**p,**state)
                audit['prediction_sha256']=v1.array_hash(score);meta['seeds'].append(audit);meta['saved_models'].append(str(path));scores.append(score)
                z=test.copy();z['pred']=score;z['vintage']=i;seed_frames[seed].append(z)
                r['new_fits_executed']+=1
            z=test.copy();z['pred']=np.mean(scores,axis=0);z['vintage']=i;predictions.append(z)
            r['per_year'][str(year)]['transforms'][str(i)]=meta
            print(json.dumps(dict(year=year,download=i,new_fits=r['new_fits_executed'],seconds=time.perf_counter()-started)),flush=True)
            write(out/'RESULT.json',r)
    z=pd.concat(predictions,ignore_index=True);z.to_parquet(out/'NATIVE_PREDICTIONS.parquet',index=False)
    seed_quality={};leaders=[]
    for seed,parts in seed_frames.items():
        sf=pd.concat(parts,ignore_index=True);sf.to_parquet(out/f'SEED_{seed}.parquet',index=False)
        seed_quality[str(seed)]=evaluate(sf,quality_exit_cutoff='2026-07-01')['aggregate_by_date']
        sf=sf[sf.exit_date_21<='2026-07-01']
        top=sf.sort_values(['vintage','signal_date','pred','ticker'],ascending=[True,True,False,True]).groupby(['vintage','signal_date']).first().ticker
        leaders.append(top.rename(str(seed)))
    seed_disagreement=pd.concat(leaders,axis=1).nunique(axis=1)>1
    r.update(seed_quality=seed_quality,seed_top1_any_disagreement=float(seed_disagreement.mean()),seed_top1_any_disagreement_by_download={str(i):float(seed_disagreement.loc[i].mean()) for i in (1,2,3)})
    r.update(status='PAPER_LTR_V2_COMPLETE',ALL_MATURITY_PASS=True,predictive=evaluate(z,quality_exit_cutoff='2026-07-01'),
        model_files_sha256={p.relative_to(out).as_posix():sha(p) for p in (out/'models').glob('*.npz')},
        files_sha256={p.name:sha(p) for p in out.glob('*.parquet')},elapsed_seconds=time.perf_counter()-started)
    if r['new_fits_executed']!=90:raise ValueError('Unexpected neural budget')
    write(out/'RESULT.json',r)
    checks={str(i):verify_full_fingerprints(r,all_panels[i],i,Path(a.raw)/f'_repeat{i}') for i in (1,2,3)}
    write(out/'RAW_AUDIT.json',dict(all_PASS=True,records=checks,candidate_result_sha256=sha(out/'RESULT.json')))
    print(json.dumps(dict(status=r['status'],new_fits=r['new_fits_executed'],quality=r['predictive']['aggregate_by_date']),indent=2))

if __name__=='__main__':main()
