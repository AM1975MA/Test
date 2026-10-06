"""Independent retained-state/vector checks for one frozen smooth learner."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from compact21_semidev_v1.summarize import (sha,keys_hash,exact_frame,sorted_vectors,
    validate_maturity,prediction_audit,FIT_SOURCES,VECTOR_KEYS,OUTCOMES)
from compact21_semidev_v1.run import select_original_frames,FROZEN_TI
from compact21_blockbag_v1.summarize import decision_gates,stability_diagnostics
from compact21_predictive_v2.metrics import evaluate,paired_compare
from compact21_predictive_v2.summarize import load_variant,normalized_numeric,stability_by_date
from compact21_learner_swap_v1 import learners
from ranker_stability_v1.run_ranker_benchmark_full import load,quality

LINE='COMPACT21_RBF_RIDGE_V1'
VARIANT='RBF_RIDGE'
YEARS=tuple(range(2017,2027))
SEEDS=(101,202,303)
FILES=('NATIVE_PREDICTIONS.parquet','COMMON_PREDICTIONS.parquet',
    'CONTROL_NATIVE_PREDICTIONS.parquet','CONTROL_COMMON_PREDICTIONS.parquet',
    'RIDGE_CONTROL_NATIVE_PREDICTIONS.parquet','RIDGE_CONTROL_COMMON_PREDICTIONS.parquet')
STATE_SHARED=('imputer_statistics','input_scaler_mean','input_scaler_scale',
    'input_scaler_variance','input_scaler_n_samples_seen')
STATE_SEED=('rbf_random_weights','rbf_random_offset','rbf_scaler_mean','rbf_scaler_scale',
    'rbf_scaler_variance','rbf_scaler_n_samples_seen','ridge_coef','ridge_intercept')
PARAMS={'imputer_strategy':'median','input_scaler':'StandardScaler',
    'linear_skip_features':125,'rbf_gamma':1/125,'rbf_components':512,
    'rbf_scaler':'StandardScaler','alpha':30.,'fit_intercept':True,'solver':'svd',
    'seeds':[101,202,303],'aggregation':'mean three float64 raw seed score vectors'}


def state_names():
    return set(STATE_SHARED)|{f'seed_{seed}_{field}' for seed in SEEDS for field in STATE_SEED}


def validate_state_arrays(states,vintage,audit,old_ridge):
    names=state_names();hashes=audit['learned_state_hashes']
    if set(hashes)!=names:raise ValueError('Incomplete fitted-state audit')
    values={name:states[f'v{vintage}_{name}'] for name in names}
    for name,value in values.items():
        if not np.isfinite(value).all() or learners.array_hash(value)!=hashes[name]:
            raise ValueError('Fitted-state array/hash differs: '+name)
        count=name.endswith('n_samples_seen')
        if count:
            if value.shape!=() or value.dtype!=np.float64 or float(value)!=audit['train_rows']:
                raise ValueError('Scaler training coverage differs')
        elif value.dtype!=np.float64:raise ValueError('Fitted-state precision differs')
    for name in STATE_SHARED[:-1]:
        if values[name].shape!=(125,):raise ValueError('Original linear feature state dimension differs')
    for name in ('input_scaler_scale',):
        if (values[name]<=0).any():raise ValueError('Invalid input standardization scale')
    if (values['input_scaler_variance']<0).any():raise ValueError('Invalid input variance')
    for new,old in (('imputer_statistics','imputer_statistics'),('input_scaler_mean','scaler_mean'),
            ('input_scaler_scale','scaler_scale'),('input_scaler_variance','scaler_variance')):
        if hashes[new]!=old_ridge['learned_state_hashes'][old]:
            raise ValueError('Original RIDGE imputer/input scaler state differs')
    for seed in SEEDS:
        prefix=f'seed_{seed}_';rng=np.random.RandomState(seed)
        weights=np.sqrt(2./125)*rng.normal(size=(125,512))
        offset=rng.uniform(0,2*np.pi,size=512)
        for field,expected in (('rbf_random_weights',weights),('rbf_random_offset',offset)):
            if values[prefix+field].shape!=expected.shape or values[prefix+field].tobytes()!=expected.tobytes():
                raise ValueError('Frozen random RBF projection differs')
        for field in ('rbf_scaler_mean','rbf_scaler_scale','rbf_scaler_variance'):
            if values[prefix+field].shape!=(512,):raise ValueError('RBF standardization dimension differs')
        if (values[prefix+'rbf_scaler_scale']<=0).any() or (values[prefix+'rbf_scaler_variance']<0).any():
            raise ValueError('Invalid RBF standardization state')
        if values[prefix+'ridge_coef'].shape!=(637,) or values[prefix+'ridge_intercept'].shape!=():
            raise ValueError('637-feature predictor state dimension differs')
    return True


def validate_seed_vectors(physical,common,native,vintage,audit):
    c=common.loc[common.vintage==vintage,'pred'].to_numpy()
    n=native.loc[native.vintage==vintage,'pred'].to_numpy()
    if physical.dtype!=np.float64 or physical.shape!=(3,len(c)+len(n)) or not np.isfinite(physical).all():
        raise ValueError('Invalid retained three-seed vectors')
    if set(audit['seed_prediction_sha256'])!={str(seed) for seed in SEEDS}:
        raise ValueError('Missing canonical seed audit')
    for i,seed in enumerate(SEEDS):
        if learners.array_hash(physical[i])!=audit['seed_prediction_sha256'][str(seed)]:
            raise ValueError('Retained seed vectors differ from audited hashes')
    actual=np.concatenate([c,n]);rebuilt=np.mean(physical,axis=0,dtype=np.float64)
    if actual.dtype!=rebuilt.dtype or actual.tobytes()!=rebuilt.tobytes():
        raise ValueError('Candidate scores differ from registered seed mean')


def load_year(path,base,ridge,frames):
    path=Path(path);r=json.loads(path.read_text());br=base['result'];rr=ridge['result']
    if r.get('line')!=LINE or r.get('variant')!=VARIANT or r.get('status')!=LINE+'_COMPLETE':
        raise ValueError('Wrong smooth learner registry/status')
    if len(r.get('years',[]))!=1 or r['years'][0] not in YEARS or set(r.get('per_year',{}))!={str(r['years'][0])}:
        raise ValueError('Invalid annual registry')
    year=r['years'][0];a=r['per_year'][str(year)]
    if any(r.get(key) is not False for key in ('negative_feedback_changed','production_adoption','portfolio_evaluation')):
        raise ValueError('Research scope changed')
    if any(r.get(key) is not True for key in ('ALL_DETERMINISM_PASS','LEGACY_PARITY_PASS','RIDGE_PARITY_PASS')):
        raise ValueError('Original controls or candidate refits failed')
    if set(r['files_sha256'])!=set(FILES)|{'FITTED_STATES.npz','SEED_PREDICTIONS.npz'}:
        raise ValueError('Missing retained score/state evidence')
    for name,digest in r['files_sha256'].items():
        if sha(path.parent/name)!=digest:raise ValueError('Altered retained artifact')
    if r['input_sha256']!=br['input_sha256'] or rr['input_sha256']!=br['input_sha256'] or r['baseline_input_contract']!=br['input_contract']:
        raise ValueError('Frozen input/cohort contracts differ')
    if set(r['fit_sources'])!=set(FIT_SOURCES) or any(r['fit_sources'][p]!=br['sources'][p] or r['sources'].get(p)!=br['sources'][p] or rr['sources'][p]!=br['sources'][p] for p in FIT_SOURCES):
        raise ValueError('Original fit source differs')
    if normalized_numeric(r['numeric_contract'])!=normalized_numeric(br['numeric_contract']) or normalized_numeric(rr['numeric_contract'])!=normalized_numeric(br['numeric_contract']):
        raise ValueError('Frozen numerical contracts differ')
    contract=r['input_contract']
    for key,value in dict(line=LINE,original_ti_sha256=br['input_sha256'],signal_cutoff='2026-06-30',
            quality_exit_cutoff='2026-07-01',common_inference_repeat=2,changed_columns=[],
            train_cohorts='original_native_frozen',recipe=PARAMS,
            ref_base_result_sha256=base['sha256'],reference_prediction_sha256=br['files_sha256'],
            ref_ridge_result_sha256=ridge['sha256'],ridge_reference_prediction_sha256=rr['files_sha256']).items():
        if contract.get(key)!=value:raise ValueError('Registered original input differs: '+key)
    vectors={name:sorted_vectors(pd.read_parquet(path.parent/name),year,name,'NATIVE' in name) for name in FILES}
    native,common=vectors[FILES[0]],vectors[FILES[1]]
    def annual(reference,kind):
        f=reference[kind];return f.loc[f.signal_date.dt.year==year].sort_values(VECTOR_KEYS).reset_index(drop=True)
    old_native,old_common=annual(base,'native'),annual(base,'common')
    exact_frame(native,old_native,VECTOR_KEYS+OUTCOMES,'Candidate original keys/outcomes')
    exact_frame(common,old_common,VECTOR_KEYS,'Candidate original common keys')
    for index,ref,kind in ((2,base,'native'),(3,base,'common'),(4,ridge,'native'),(5,ridge,'common')):
        old=annual(ref,kind);exact_frame(vectors[FILES[index]],old,list(old.columns),'Original retained control')
    old_a=br['per_year'][str(year)];ridge_a=rr['per_year'][str(year)]
    if a['evaluation_coverage']!=old_a['evaluation_coverage'] or a['evaluation_coverage']!=ridge_a['evaluation_coverage'] or a['determinism_PASS'] is not True:
        raise ValueError('Coverage/refit mismatch')
    for field in ('transforms','control_transforms','ridge_control_transforms','independent_refits','legacy_control','ridge_control'):
        if set(a[field])!={'1','2','3'}:raise ValueError('Missing vintage audit: '+field)
    trains,tests,common_input=select_original_frames(frames,year)
    with np.load(path.parent/'FITTED_STATES.npz',allow_pickle=False) as state_file:
        if set(state_file.files)!={f'v{v}_{name}' for v in (1,2,3) for name in state_names()}:
            raise ValueError('Fitted-state evidence schema differs')
        states={name:state_file[name].copy() for name in state_file.files}
    with np.load(path.parent/'SEED_PREDICTIONS.npz',allow_pickle=False) as seed_file:
        if set(seed_file.files)!={f'predictions_{v}' for v in (1,2,3)}:raise ValueError('Seed evidence schema differs')
        seeds={v:seed_file[f'predictions_{v}'].copy() for v in (1,2,3)}
    for v in (1,2,3):
        key=str(v);new=a['transforms'][key];old=old_a['transforms'][key];rold=ridge_a['transforms'][key]
        validate_maturity(new,year,'Smooth candidate '+key)
        prediction_audit(new,common,native,v,'Smooth candidate '+key)
        if a['control_transforms'][key]!=old or a['ridge_control_transforms'][key]!=rold:
            raise ValueError('Original learned control metadata differs')
        for controls in ('legacy_control','ridge_control'):
            if any(a[controls][key].get(field) is not True for field in ('native_bytes_exact','common_bytes_exact','metadata_exact','legacy_hashes_exact')):
                raise ValueError('Original BASE/RIDGE control failed')
        unchanged=('train_matrix_sha256','train_groups_sha256','test_matrix_sha256','train_rows',
            'feature_names','cutoff','max_signal_date','max_exit_date_21')
        if any(new[field]!=old[field] for field in unchanged) or new['train_labels_sha256']!=rold['train_labels_sha256']:
            raise ValueError('Original matrix/cohort or continuous target changed')
        if new['kind']!=VARIANT or new['design_features']!=637 or new['input_features']!=125 or new['model_params']!=PARAMS or new['feature_transform']!='mature_median_standard_linear_skip_plus_scaled_RBF' or new['target']!='continuous_percentile':
            raise ValueError('Smooth predictor design changed')
        refit=a['independent_refits'][key]
        if any(refit.get(field) is not True for field in ('native_bytes_exact','common_bytes_exact','learned_audit_exact','fitted_states_bytes_exact','seed_vectors_bytes_exact')) or refit['refit_audit']!=new or refit['prediction_sha256']!=new['prediction_sha256']:
            raise ValueError('Independent full predictor refit differs')
        validate_state_arrays(states,v,new,rold)
        validate_seed_vectors(seeds[v],common,native,v,new)
        if set(new['fit_matrix_sha256'])!={str(s) for s in SEEDS} or set(new['test_fit_matrix_sha256'])!={str(s) for s in SEEDS} or any(len(z)!=2 for z in new['test_fit_matrix_sha256'].values()):
            raise ValueError('Missing full transformed train/test matrix audit')
        # Source-backed original row identity is independent of prediction manifests.
        physical_train=trains[v]
        if keys_hash(physical_train)!=a['evaluation_coverage']['train_keys_sha256'][key]:
            raise ValueError('Physical original training keys differ')
        if learners.array_hash(learners.matrix(physical_train).to_numpy())!=new['train_matrix_sha256'] or learners.array_hash(physical_train.target_rank_21.to_numpy(float))!=new['train_labels_sha256']:
            raise ValueError('Physical original feature/target hashes differ')
        f=native.loc[native.vintage==v]
        mask=f.exit_date_21.notna()&f.target_rank_21.notna()&(f.exit_date_21<=pd.Timestamp('2026-07-01'))
        if a['quality'][key]!=quality(f.loc[mask],f.loc[mask,'pred'].to_numpy()):raise ValueError('Declared quality differs from scores')
        if keys_hash(f)!=a['evaluation_coverage']['test_keys_sha256'][key] or keys_hash(common.loc[common.vintage==v])!=a['evaluation_coverage']['common_keys_sha256']:
            raise ValueError('Retained native/common cohort hashes differ')
    return dict(result=r,native=native,common=common,path=str(path),sha256=sha(path),year=year)


def summarize(root,reference_root,out,ti_paths):
    base=load_variant(reference_root,'BASE');ridge=load_variant(reference_root,'RIDGE')
    if any(ref['result']['LEGACY_PARITY_PASS'] is not True for ref in (base,ridge)):
        raise ValueError('Original BASE/RIDGE controls failed')
    if {str(v):sha(Path(ti_paths[v])/'TI_COMPACT.parquet') for v in (1,2,3)}!=FROZEN_TI:
        raise ValueError('Original TI physical authority differs')
    frames={v:load(Path(ti_paths[v])) for v in (1,2,3)};jobs={};invariant=None
    for path in Path(root).rglob('RESULT.json'):
        if json.loads(path.read_text()).get('line')!=LINE:continue
        job=load_year(path,base,ridge,frames);year=job['year'];r=job['result']
        if year in jobs:raise ValueError('Duplicate annual job')
        contract={key:r[key] for key in ('input_sha256','input_contract','baseline_input_contract','fit_sources','sources','preregistration_sha256')}
        contract['numeric_contract']=normalized_numeric(r['numeric_contract'])
        if invariant is None:invariant=contract
        if invariant!=contract:raise ValueError('Mixed annual source/profile/registration contracts')
        jobs[year]=job
    if set(jobs)!=set(YEARS):raise ValueError('Incomplete 10-job annual matrix')
    native=pd.concat([jobs[y]['native'] for y in YEARS],ignore_index=True).sort_values(VECTOR_KEYS).reset_index(drop=True)
    common=pd.concat([jobs[y]['common'] for y in YEARS],ignore_index=True).sort_values(VECTOR_KEYS).reset_index(drop=True)
    ev=evaluate(native,quality_exit_cutoff='2026-07-01',expected_keys=base['native'][VECTOR_KEYS])
    if ev['coverage']!=base['eval']['coverage'] or ev['coverage']['mature_dates']!=113:
        raise ValueError('Original mature quality coverage differs')
    paired=paired_compare(ev,base['eval'])
    paired['lower98_75_interpretation']='Retained conservative development bound; no familywise control over prior or adaptive research.'
    sc,sn=stability_by_date(common),stability_by_date(native)
    bc,bn=stability_by_date(base['common']),stability_by_date(base['native'])
    decisions=decision_gates(ev,base['eval'],paired,sc,sn,bc,bn,True)
    models={}
    for variant,reference,n,c,ns,cs in (('BASE',base,base['native'],base['common'],bn,bc),
            ('RIDGE',ridge,ridge['native'],ridge['common'],stability_by_date(ridge['native']),stability_by_date(ridge['common'])),
            (VARIANT,None,native,common,sn,sc)):
        models[variant]=dict(predictive=ev if reference is None else reference['eval'],native_stability=ns,common_stability=cs,
            native_stability_diagnostics=stability_diagnostics(n,ns),common_stability_diagnostics=stability_diagnostics(c,cs))
    models[VARIANT].update(paired_vs_BASE=paired,gate=decisions)
    result=dict(status=LINE+'_SUMMARY_COMPLETE',variant=VARIANT,years=list(YEARS),models=models,
        all_controls_reproduced=True,all_ridge_controls_PASS=True,all_independent_refits_PASS=True,
        all_retained_fitted_state_hashes_PASS=True,all_seed_mean_vectors_exact=True,
        contract=invariant,references={name:dict(path=ref['path'],sha256=ref['sha256']) for name,ref in (('BASE',base),('RIDGE',ridge))},
        annual_jobs={str(y):dict(path=jobs[y]['path'],sha256=jobs[y]['sha256']) for y in YEARS},
        registry=dict(annual_jobs=10,candidate_vintage_fits=30,independent_candidate_refits=30,seeds_per_candidate=3,
            candidate_seed_models=90,independent_candidate_seed_models=90,baseline_seed_models=90,ridge_controls=30),
        production_adoption=False,negative_feedback_changed=False,portfolio_evaluation=False,
        interpretation='One frozen smooth learner on explored history; repeatability and predictive preservation are separate gates. No fresh holdout or automatic adoption claim.')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    native.to_parquet(out/FILES[0],index=False);common.to_parquet(out/FILES[1],index=False)
    result['files_sha256']={name:sha(out/name) for name in FILES[:2]}
    (out/'SUMMARY.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--references',required=True);p.add_argument('--out',required=True)
    for v in (1,2,3):p.add_argument(f'--r{v}',required=True)
    a=p.parse_args();result=summarize(a.inputs,a.references,a.out,{v:getattr(a,f'r{v}') for v in (1,2,3)})
    print(json.dumps(result['models'][VARIANT]['gate'],indent=2))
