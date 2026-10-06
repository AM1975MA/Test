"""Independent evidence validation and separate repeatability/quality gates."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from statistics import mean
import numpy as np
import pandas as pd
from compact21_semidev_v1.summarize import (sha, keys_hash, exact_frame,
    sorted_vectors, validate_maturity, prediction_audit, FIT_SOURCES, VECTOR_KEYS, OUTCOMES)
from compact21_semidev_v1.run import select_original_frames, FROZEN_TI
from compact21_predictive_v2.metrics import evaluate, paired_compare
from compact21_predictive_v2.summarize import load_variant, normalized_numeric, stability_by_date, gate
from compact21_learner_swap_v1.learners import array_hash
from ranker_stability_v1.run_ranker_benchmark_full import load, quality

RECIPE={"bags":4,"block_length_queries":3,"noncircular":True,
    "weight_rng_seed":20261005,"seed_sequence":"[20261005, year, bag_index_0_to_3]",
    "group_weights":"query occurrence bincount; no cohort row duplication",
    "quantile_sketch":"original unweighted full cohort",
    "aggregation":"canonical seed mean; four bag mean float64 then cast canonical float32",
    "seed_models":12,"baseline_seed_models":3}

LINE='COMPACT21_BLOCKBAG_V1'
VARIANT='BASE_BLOCKBAG'
YEARS=tuple(range(2017,2027))
FILES=('NATIVE_PREDICTIONS.parquet','COMMON_PREDICTIONS.parquet',
    'CONTROL_NATIVE_PREDICTIONS.parquet','CONTROL_COMMON_PREDICTIONS.parquet',
    'WEIGHTED_CONTROL_NATIVE_PREDICTIONS.parquet','WEIGHTED_CONTROL_COMMON_PREDICTIONS.parquet')


def expected_weights(query_dates, year, replicate):
    """Reconstruct the frozen noncircular three-query bootstrap independently."""
    dates=np.asarray(query_dates,dtype='datetime64[ns]')
    if len(dates)<3 or np.isnat(dates).any() or not np.all(dates[1:]>dates[:-1]):
        raise ValueError('Invalid ordered training month queries')
    months=pd.DatetimeIndex(dates).to_period('M').astype('int64').to_numpy()
    if not np.all(np.diff(months)==1):
        raise ValueError('Training queries must be consecutive calendar months')
    rng=np.random.default_rng(np.random.SeedSequence([20261005,int(year),int(replicate)]))
    starts=rng.integers(0,len(dates)-3+1,size=(len(dates)+2)//3)
    draws=np.concatenate([np.arange(start,start+3) for start in starts])[:len(dates)]
    return np.bincount(draws,minlength=len(dates)).astype(np.float64)


def decision_gates(ev,base_eval,paired,common,native,bc,bn,controls=True):
    full=gate({'eval':ev},{'eval':base_eval},paired,common,native,bc,bn,controls)
    checks=full['checks']
    pilot={key:checks[key] for key in ('all_controls_reproduced',
        'common_rank_mad_reduced_ge25pct','native_top1_disagreement_reduced_ge25pct',
        'each_common_pair_mad_not_worse','each_native_pair_top1_not_worse')}
    near=dict(all_controls_reproduced=controls,
        each_native_pair_top1_disagreement_le5pct=all(p['mean']['top1_disagreement']<=.05 for p in native['pairs'].values()),
        common_rank_mad_reduced_ge90pct=common['mean']['rank_mad']<=.1*bc['mean']['rank_mad'],
        each_common_pair_mad_reduced_ge90pct=all(common['pairs'][p]['mean']['rank_mad']<=.1*bc['pairs'][p]['mean']['rank_mad'] for p in bc['pairs']),
        each_common_pair_mad_not_worse=checks['each_common_pair_mad_not_worse'],
        each_native_pair_top1_not_worse=checks['each_native_pair_top1_not_worse'])
    primary='top1_realized_percentile';precision='top5_overlap'
    previous=base_eval['aggregate_by_date'][primary]
    vintage_checks={v:mean(r[primary] for r in ev['per_date'] if r['vintage']==v)>=
        .95*mean(r[primary] for r in base_eval['per_date'] if r['vintage']==v) for v in ('1','2','3')}
    interval=paired['bootstrap']['3']['intervals_95pct'][primary]
    conservation=dict(all_controls_reproduced=controls,
        primary_overall_ge95pct_BASE=ev['aggregate_by_date'][primary]>=.95*previous,
        primary_each_vintage_ge95pct_BASE=all(vintage_checks.values()),
        precision5_overall_ge95pct_BASE=ev['aggregate_by_date'][precision]>=.95*base_eval['aggregate_by_date'][precision],
        primary_lower95_one_sided_above_negative5pct_BASE=interval is not None and interval['lower95_one_sided']>-.05*previous)
    return dict(STABILITY_PILOT_PASS=all(pilot.values()),stability_pilot_checks=pilot,
        NEAR_REPEATABILITY_PASS=all(near.values()),near_repeatability_checks=near,
        QUALITY_CONSERVATION_PASS=all(conservation.values()),quality_conservation_checks=conservation,
        quality_conservation_vintage_checks=vintage_checks,quality_noninferiority_absolute_margin=.05*previous,
        STABLE_WITH_CONSERVED_QUALITY=all(near.values()) and all(conservation.values()),
        FULL_IMPROVEMENT=full['DEVELOPMENT_CANDIDATE'],full_improvement_gate=full,
        production_adoption=False,
        interpretation='Pilot improvement does not establish operational repeatability. Quality conservation is a development margin, not proof of equivalent forecasting or fresh holdout performance.')


def stability_diagnostics(frame,registered):
    """Mandatory year/tail/Spearman reporting; cannot substitute for gates."""
    output={}
    for pair,value in registered['pairs'].items():
        first,second=map(int,pair.split('-'))
        a=frame.loc[frame.vintage==first].sort_values(['signal_date','ticker'])
        b=frame.loc[frame.vintage==second].sort_values(['signal_date','ticker'])
        exact_frame(a,b,['signal_date','ticker'],'Detailed stability cohort')
        rows=[]
        for original in value['dates']:
            date=pd.Timestamp(original['signal_date'])
            x=a.loc[a.signal_date==date,'pred'].rank(method='average',pct=True).to_numpy()
            y=b.loc[b.signal_date==date,'pred'].rank(method='average',pct=True).to_numpy()
            difference=np.abs(x-y)
            spearman=float(np.corrcoef(x,y)[0,1]) if np.ptp(x)>0 and np.ptp(y)>0 else None
            rows.append(dict(**original,year=date.year,spearman=spearman,
                rank_abs_diff_p95=float(np.quantile(difference,.95)),
                rank_abs_diff_max=float(difference.max())))
        years={}
        for year in sorted({r['year'] for r in rows}):
            selected=[r for r in rows if r['year']==year]
            defined=[r['spearman'] for r in selected if r['spearman'] is not None]
            years[str(year)]=dict(dates=len(selected),
                **{key:mean(r[key] for r in selected) for key in ('rank_mad','top1_disagreement','top5_jaccard','rank_abs_diff_p95','rank_abs_diff_max')},
                spearman=mean(defined) if defined else None,spearman_defined_dates=len(defined))
        defined=[r['spearman'] for r in rows if r['spearman'] is not None]
        output[pair]=dict(dates=rows,by_year=years,
            spearman=mean(defined) if defined else None,spearman_defined_dates=len(defined),
            date_rank_mad_p95=float(np.quantile([r['rank_mad'] for r in rows],.95)),
            date_rank_mad_max=max(r['rank_mad'] for r in rows))
    return output


def validate_weights(path,year,trains,audit):
    """Physical frozen-source query authority; never trust manifest dates alone."""
    with np.load(path,allow_pickle=False) as retained:
        expected_fields={'query_dates','weights','group_sizes'}
        if set(retained.files)!=expected_fields:
            raise ValueError('Weights evidence schema differs')
        for v in (1,2,3):
            groups=trains[v].groupby('signal_date',sort=True).size()
            dates=groups.index.to_numpy(dtype='datetime64[ns]')
            sizes=groups.to_numpy(dtype=np.int64)
            weights=np.stack([expected_weights(dates,year,b) for b in range(4)])
            for name,value in (('query_dates',dates),('group_sizes',sizes),('weights',weights)):
                physical=retained[name]
                if physical.dtype!=value.dtype or physical.shape!=value.shape or physical.tobytes()!=value.tobytes():
                    raise ValueError('Weights/query/group evidence differs: '+name)
            a=audit
            if a['recipe']!=RECIPE or a['same_keys_all_vintages'] is not True or a['query_count']!=len(dates):
                raise ValueError('Frozen weight generator registry differs')
            if a['weights_sha256']!=array_hash(weights) or a['group_sizes_sha256']!=array_hash(sizes) or a['query_dates_sha256']!=array_hash(dates):
                raise ValueError('Declared weight evidence differs')
            identity=trains[v][['signal_date','ticker']].reset_index(drop=True)
            import hashlib
            physical_key_hash=hashlib.sha256(identity.to_csv(index=False,lineterminator='\n').encode()).hexdigest()
            if a['bag_weights_sha256']!=[array_hash(w) for w in weights] or a['train_keys_sha256_lf'][str(v)]!=physical_key_hash:
                raise ValueError('Declared bag weights/training keys differ')
            exact_frame(identity,trains[1],['signal_date','ticker'],'All vintage training cohorts')
    return True


def load_year(path,base,frames):
    path=Path(path);r=json.loads(path.read_text())
    if r.get('line')!=LINE or r.get('variant')!=VARIANT or r.get('status')!=LINE+'_COMPLETE':
        raise ValueError('Wrong blockbag registry/status')
    if len(r.get('years',[]))!=1 or r['years'][0] not in YEARS or set(r.get('per_year',{}))!={str(r['years'][0])}:
        raise ValueError('Wrong annual audit coverage')
    year=r['years'][0];br=base['result'];a=r['per_year'][str(year)];old_a=br['per_year'][str(year)]
    if any(r.get(k) is not False for k in ('negative_feedback_changed','production_adoption','portfolio_evaluation')):
        raise ValueError('Research scope changed')
    if any(r.get(k) is not True for k in ('ALL_DETERMINISM_PASS','LEGACY_PARITY_PASS','WEIGHTED_PARITY_PASS')):
        raise ValueError('Failed control or candidate refit')
    if set(r['files_sha256'])!=set(FILES)|{'WEIGHTS.npz','BAG_PREDICTIONS.npz'}:
        raise ValueError('Missing retained vectors/weights')
    for name,digest in r['files_sha256'].items():
        if sha(path.parent/name)!=digest:raise ValueError('Altered retained evidence')
    if r['input_sha256']!=br['input_sha256'] or r['baseline_input_contract']!=br['input_contract']:
        raise ValueError('Original TI/cohort/cutoff contract changed')
    if set(r['fit_sources'])!=set(FIT_SOURCES) or any(r['fit_sources'][p]!=br['sources'][p] or r['sources'].get(p)!=br['sources'][p] for p in FIT_SOURCES):
        raise ValueError('Original fit source changed')
    if normalized_numeric(r['numeric_contract'])!=normalized_numeric(br['numeric_contract']):
        raise ValueError('Original numeric contract differs')
    c=r['input_contract']
    expected=dict(line=LINE,original_ti_sha256=br['input_sha256'],signal_cutoff='2026-06-30',
        quality_exit_cutoff='2026-07-01',common_inference_repeat=2,changed_columns=[],
        train_cohorts='original_native_frozen',recipe=RECIPE,
        ref_base_result_sha256=base['sha256'],reference_prediction_sha256=br['files_sha256'])
    for key,value in expected.items():
        if c.get(key)!=value:raise ValueError('Frozen candidate input contract differs: '+key)
    vectors={name:sorted_vectors(pd.read_parquet(path.parent/name),year,name,'NATIVE' in name) for name in FILES}
    native,common=vectors[FILES[0]],vectors[FILES[1]]
    old_native=base['native'].loc[base['native'].signal_date.dt.year==year].sort_values(VECTOR_KEYS).reset_index(drop=True)
    old_common=base['common'].loc[base['common'].signal_date.dt.year==year].sort_values(VECTOR_KEYS).reset_index(drop=True)
    exact_frame(native,old_native,VECTOR_KEYS+OUTCOMES,'Original candidate keys/outcomes')
    exact_frame(common,old_common,VECTOR_KEYS,'Original candidate common keys')
    for index,old in ((2,old_native),(3,old_common),(4,old_native),(5,old_common)):
        exact_frame(vectors[FILES[index]],old,list(old.columns),'Original retained control')
    if a['evaluation_coverage']!=old_a['evaluation_coverage'] or a['determinism_PASS'] is not True:
        raise ValueError('Coverage/refit mismatch')
    trains,tests,common_input=select_original_frames(frames,year)
    validate_weights(path.parent/'WEIGHTS.npz',year,trains,a['weights_audit'])
    with np.load(path.parent/'BAG_PREDICTIONS.npz',allow_pickle=False) as bag_file:
        if set(bag_file.files)!={f'predictions_{v}' for v in (1,2,3)}:
            raise ValueError('Missing retained individual bag vectors')
        bag_vectors={v:bag_file[f'predictions_{v}'].copy() for v in (1,2,3)}
    for field in ('transforms','control_transforms','weighted_control_transforms','independent_refits','legacy_control','weighted_control'):
        if set(a[field])!={'1','2','3'}:raise ValueError('Missing vintage audit: '+field)
    for v in (1,2,3):
        key=str(v);new=a['transforms'][key];old=old_a['transforms'][key]
        validate_maturity(new,year,'Candidate '+key)
        prediction_audit(new,common,native,v,'Candidate '+key)
        if a['control_transforms'][key]!=old:raise ValueError('Original metadata differs')
        unchanged=('train_matrix_sha256','train_labels_sha256','train_groups_sha256','test_matrix_sha256',
            'train_rows','feature_names','cutoff','max_signal_date','max_exit_date_21')
        if any(new[field]!=old[field] for field in unchanged):raise ValueError('Candidate changed frozen matrix/target/cohort')
        if new['kind']!=VARIANT or new['model_params']!={'recipe':RECIPE,'canonical':old['model_params']}:
            raise ValueError('Candidate canonical/ensemble recipe differs')
        refit=a['independent_refits'][key]
        if any(refit.get(field) is not True for field in ('native_bytes_exact','common_bytes_exact','learned_audit_exact')) or refit['refit_audit']!=new or refit['prediction_sha256']!=new['prediction_sha256']:
            raise ValueError('Candidate independent refit differs')
        if any(a['legacy_control'][key].get(field) is not True for field in ('native_bytes_exact','common_bytes_exact','metadata_exact','legacy_hashes_exact')):
            raise ValueError('Original BASE control failed')
        wc=a['weighted_control'][key];wa=a['weighted_control_transforms'][key]
        if any(wc.get(field) is not True for field in ('native_bytes_exact','common_bytes_exact','learned_audit_exact','four_bag_aggregate_bytes_exact')):
            raise ValueError('Weighted ones control failed')
        stripped={k:value for k,value in wa.items() if k!='group_weights_sha256'}
        if stripped!=old:raise ValueError('Weighted ones learned metadata differs')
        query_count=len(trains[v].groupby('signal_date'))
        if wa['group_weights_sha256']!=array_hash(np.ones(query_count,dtype=np.float64)):
            raise ValueError('Weighted ones hash differs')
        dates=trains[v].groupby('signal_date',sort=True).size().index.to_numpy(dtype='datetime64[ns]')
        weights=[expected_weights(dates,year,b) for b in range(4)]
        physical=bag_vectors[v]
        nc=common.loc[common.vintage==v,'pred'].to_numpy();nn=native.loc[native.vintage==v,'pred'].to_numpy()
        if physical.dtype!=np.float32 or physical.shape!=(4,len(nc)+len(nn)) or not np.isfinite(physical).all():
            raise ValueError('Invalid retained bag score arrays')
        rebuilt=np.mean(physical,axis=0,dtype=np.float64).astype(np.float32)
        combined=np.concatenate([nc,nn])
        if rebuilt.dtype!=combined.dtype or rebuilt.tobytes()!=combined.tobytes():
            raise ValueError('Retained ensemble is not the registered bag mean')
        if set(new['bags'])!={'0','1','2','3'} or new['group_weights_sha256']!=[array_hash(w) for w in weights]:
            raise ValueError('Candidate bags/weight hashes differ')
        for b in range(4):
            bag=new['bags'][str(b)]
            validate_maturity(bag,year,'Bag '+str(b))
            if any(bag[field]!=old[field] for field in unchanged) or bag['group_weights_sha256']!=array_hash(weights[b]):
                raise ValueError('Bag changed matrix/labels/weights')
            if bag['model_params']!=old['model_params'] or bag['kind']!='BASE' or set(bag['seed_prediction_sha256'])!={'101','202','303'} or new['bag_prediction_sha256'][str(b)]!=bag['prediction_sha256']:
                raise ValueError('Bag canonical seed/model/prediction registry differs')
            if bag['prediction_sha256']!=[array_hash(physical[b,:len(nc)]),array_hash(physical[b,len(nc):])]:
                raise ValueError('Bag hashes differ from retained individual vectors')
        f=native.loc[native.vintage==v];mask=f.exit_date_21.notna()&f.target_rank_21.notna()&(f.exit_date_21<=pd.Timestamp('2026-07-01'))
        if a['quality'][key]!=quality(f.loc[mask],f.loc[mask,'pred'].to_numpy()):raise ValueError('Reported candidate quality differs')
        if keys_hash(f)!=a['evaluation_coverage']['test_keys_sha256'][key] or keys_hash(common.loc[common.vintage==v])!=a['evaluation_coverage']['common_keys_sha256']:
            raise ValueError('Retained cohort keys differ')
    return dict(result=r,native=native,common=common,path=str(path),sha256=sha(path),year=year)


def summarize(root,reference_root,out,ti_paths):
    base=load_variant(reference_root,'BASE')
    if base['result']['LEGACY_PARITY_PASS'] is not True:raise ValueError('Original BASE parity failed')
    if {str(v):sha(Path(ti_paths[v])/'TI_COMPACT.parquet') for v in (1,2,3)}!=FROZEN_TI:
        raise ValueError('Frozen TI physical authority differs')
    frames={v:load(Path(ti_paths[v])) for v in (1,2,3)}
    jobs={};invariant=None
    for path in Path(root).rglob('RESULT.json'):
        if json.loads(path.read_text()).get('line')!=LINE:continue
        job=load_year(path,base,frames);year=job['year'];r=job['result']
        if year in jobs:raise ValueError('Duplicate annual job')
        contract={key:r[key] for key in ('input_sha256','input_contract','baseline_input_contract','fit_sources','sources','preregistration_sha256')}
        contract['numeric_contract']=normalized_numeric(r['numeric_contract'])
        if invariant is None:invariant=contract
        if invariant!=contract:raise ValueError('Mixed source/numeric/protocol contracts')
        jobs[year]=job
    if set(jobs)!=set(YEARS):raise ValueError('Incomplete 10-job annual matrix')
    native=pd.concat([jobs[y]['native'] for y in YEARS],ignore_index=True).sort_values(VECTOR_KEYS).reset_index(drop=True)
    common=pd.concat([jobs[y]['common'] for y in YEARS],ignore_index=True).sort_values(VECTOR_KEYS).reset_index(drop=True)
    ev=evaluate(native,quality_exit_cutoff='2026-07-01',expected_keys=base['native'][VECTOR_KEYS])
    if ev['coverage']!=base['eval']['coverage'] or ev['coverage']['mature_dates']!=113:raise ValueError('Original quality coverage differs')
    paired=paired_compare(ev,base['eval'])
    paired['lower98_75_interpretation']='Conservative retained post-V2 development bound, no familywise control over past research.'
    sc,sn=stability_by_date(common),stability_by_date(native)
    bc,bn=stability_by_date(base['common']),stability_by_date(base['native'])
    decisions=decision_gates(ev,base['eval'],paired,sc,sn,bc,bn,True)
    result=dict(status=LINE+'_SUMMARY_COMPLETE',variant=VARIANT,years=list(YEARS),
        all_controls_reproduced=True,all_weighted_ones_controls_PASS=True,all_independent_refits_PASS=True,
        models={'BASE':dict(predictive=base['eval'],common_stability=bc,native_stability=bn),
            VARIANT:dict(predictive=ev,common_stability=sc,native_stability=sn,paired_vs_BASE=paired,gate=decisions)},
        contract=invariant,reference=dict(path=base['path'],sha256=base['sha256']),
        annual_jobs={str(y):dict(path=jobs[y]['path'],sha256=jobs[y]['sha256']) for y in YEARS},
        registry=dict(annual_jobs=10,candidate_vintage_fits=30,independent_candidate_refits=30,
            bags_per_candidate=4,seeds_per_bag=3,trees_per_seed=360,
            candidate_seed_models=360,independent_candidate_seed_models=360,
            baseline_seed_models=90,weighted_ones_seed_models=90),
        production_adoption=False,negative_feedback_changed=False,portfolio_evaluation=False,
        interpretation='Frozen development experiment on explored history. Pilot stability improvement is not operational repeatability. Increased ensemble budget is disclosed; no automatic adoption or fresh holdout generalization claim.')
    for variant,n,c,ns,cs in (('BASE',base['native'],base['common'],bn,bc),(VARIANT,native,common,sn,sc)):
        result['models'][variant]['native_stability_diagnostics']=stability_diagnostics(n,ns)
        result['models'][variant]['common_stability_diagnostics']=stability_diagnostics(c,cs)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    native.to_parquet(out/FILES[0],index=False);common.to_parquet(out/FILES[1],index=False)
    result['files_sha256']={name:sha(out/name) for name in FILES[:2]}
    (out/'SUMMARY.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--references',required=True);p.add_argument('--out',required=True)
    for v in (1,2,3):p.add_argument(f'--r{v}',required=True)
    a=p.parse_args();r=summarize(a.inputs,a.references,a.out,{v:getattr(a,f'r{v}') for v in (1,2,3)})
    print(json.dumps(r['models'][VARIANT]['gate'],indent=2))
