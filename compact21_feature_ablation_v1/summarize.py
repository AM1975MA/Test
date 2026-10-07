"""Independent validation of the frozen Compact21 feature-family ablations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from compact21_blockbag_v1.summarize import decision_gates, stability_diagnostics
from compact21_predictive_v2.metrics import evaluate, paired_compare
from compact21_predictive_v2.summarize import load_variant, normalized_numeric, stability_by_date
from compact21_semidev_v1.summarize import (
    FIT_SOURCES, OUTCOMES, VECTOR_KEYS, exact_frame, keys_hash,
    prediction_audit, sha, sorted_vectors, validate_maturity,
)
from compact21_semidev_v1.run import FROZEN_TI, select_original_frames
from compact21_learner_swap_v1 import learners
from ranker_stability_v1.run_ranker_benchmark_full import load, quality
from compact21_feature_ablation_v1.variants import FEATURES, MASKS, mask_manifest
from compact21_feature_ablation_v1.run import masked

LINE = 'COMPACT21_FEATURE_ABLATION_V1'
YEARS = tuple(range(2017, 2027))
FILES = (
    'NATIVE_PREDICTIONS.parquet', 'COMMON_PREDICTIONS.parquet',
    'CONTROL_NATIVE_PREDICTIONS.parquet', 'CONTROL_COMMON_PREDICTIONS.parquet',
)


def check_complete_matrix(jobs):
    expected = {(variant, year) for variant in MASKS for year in YEARS}
    if set(jobs) != expected:
        missing = sorted(expected - set(jobs))
        extra = sorted(set(jobs) - expected)
        raise ValueError(f'Incomplete ablation matrix: missing={missing}, extra={extra}')


def _annual(reference, kind, year):
    return reference[kind].loc[reference[kind].signal_date.dt.year == year].sort_values(VECTOR_KEYS).reset_index(drop=True)


def load_year(path, base, frames):
    path = Path(path)
    r = json.loads(path.read_text())
    variant = r.get('variant')
    if r.get('line') != LINE or variant not in MASKS or r.get('status') != LINE + '_COMPLETE':
        raise ValueError('Wrong ablation identity/status')
    if len(r.get('years', [])) != 1 or r['years'][0] not in YEARS:
        raise ValueError('Wrong annual fold')
    year = r['years'][0]
    if set(r.get('per_year', {})) != {str(year)}:
        raise ValueError('Incomplete annual audit')
    if any(r.get(k) is not False for k in ('negative_feedback_changed', 'production_adoption', 'portfolio_evaluation')):
        raise ValueError('Research scope changed')
    if any(r.get(k) is not True for k in ('ALL_DETERMINISM_PASS', 'LEGACY_PARITY_PASS')):
        raise ValueError('Controls/refits failed')
    if set(r.get('files_sha256', {})) != set(FILES):
        raise ValueError('Missing retained vectors')
    for name, digest in r['files_sha256'].items():
        if sha(path.parent / name) != digest:
            raise ValueError('Altered retained vector: ' + name)
    br = base['result']
    if r['input_sha256'] != br['input_sha256'] or r['baseline_input_contract'] != br['input_contract']:
        raise ValueError('Original input contract differs')
    if set(r['fit_sources']) != set(FIT_SOURCES) or any(
        r['fit_sources'][key] != br['sources'][key] or r['sources'].get(key) != br['sources'][key]
        for key in FIT_SOURCES
    ):
        raise ValueError('Canonical fit source differs')
    if normalized_numeric(r['numeric_contract']) != normalized_numeric(br['numeric_contract']):
        raise ValueError('Numerical profile differs')
    manifest = mask_manifest()[variant]
    if r.get('mask_feature_names') != manifest['masked_columns'] or r.get('mask_feature_names_sha256') != manifest['masked_columns_sha256']:
        raise ValueError('Ablation mask differs from registered feature family')
    if r.get('mask_manifest_sha256') != sha(path.parent.parent / 'MASK_MANIFEST.json') or \
       json.loads((path.parent.parent / 'MASK_MANIFEST.json').read_text()) != mask_manifest():
        raise ValueError('Original four-mask manifest differs')
    contract = r['input_contract']
    for key, value in dict(
        line=LINE, original_ti_sha256=br['input_sha256'],
        signal_cutoff='2026-06-30', quality_exit_cutoff='2026-07-01',
        common_inference_repeat=2, train_cohorts='original_native_frozen_before_mask',
        changed_columns=list(MASKS[variant]),
        ref_base_result_sha256=base['sha256'], reference_prediction_sha256=br['files_sha256'],
    ).items():
        if contract.get(key) != value:
            raise ValueError('Frozen contract differs: ' + key)
    vectors = {name: sorted_vectors(pd.read_parquet(path.parent / name), year, name, 'NATIVE' in name)
               for name in FILES}
    native, common = vectors[FILES[0]], vectors[FILES[1]]
    old_native, old_common = _annual(base, 'native', year), _annual(base, 'common', year)
    exact_frame(native, old_native, VECTOR_KEYS + OUTCOMES, 'Candidate native cohort/outcomes')
    exact_frame(common, old_common, VECTOR_KEYS, 'Candidate common cohort')
    exact_frame(vectors[FILES[2]], old_native, list(old_native.columns), 'Exact original BASE native control')
    exact_frame(vectors[FILES[3]], old_common, list(old_common.columns), 'Exact original BASE common control')
    a, old_a = r['per_year'][str(year)], br['per_year'][str(year)]
    if a['evaluation_coverage'] != old_a['evaluation_coverage'] or a['determinism_PASS'] is not True:
        raise ValueError('Coverage/refit differs')
    for field in ('transforms', 'control_transforms', 'independent_refits', 'legacy_control'):
        if set(a[field]) != {'1', '2', '3'}:
            raise ValueError('Missing vintage audit: ' + field)
    trains, tests, common_input = select_original_frames(frames, year)
    for v in (1, 2, 3):
        key = str(v)
        new, old = a['transforms'][key], old_a['transforms'][key]
        validate_maturity(new, year, f'Ablation {variant}/{year}/{v}')
        prediction_audit(new, common, native, v, f'Ablation {variant}/{year}/{v}')
        if a['control_transforms'][key] != old:
            raise ValueError('Original BASE fit metadata differs')
        for field in ('train_labels_sha256', 'train_groups_sha256', 'train_rows',
                      'feature_names', 'cutoff', 'max_signal_date', 'max_exit_date_21'):
            if new[field] != old[field]:
                raise ValueError('Original cohort/target/feature schema differs: ' + field)
        if new['feature_names'] != list(FEATURES):
            raise ValueError('Canonical 125-column feature order differs')
        refit = a['independent_refits'][key]
        if any(refit.get(field) is not True for field in
               ('native_bytes_exact', 'common_bytes_exact', 'learned_audit_exact')):
            raise ValueError('Independent candidate refit failed')
        if refit['refit_audit'] != new or refit['prediction_sha256'] != new['prediction_sha256']:
            raise ValueError('Independent candidate refit hashes differ')
        if any(a['legacy_control'][key].get(field) is not True for field in
               ('native_bytes_exact', 'common_bytes_exact', 'metadata_exact', 'legacy_hashes_exact')):
            raise ValueError('Original BASE control failed')
        # Independently tie the registry to the physical frozen training panels.
        train = trains[v]
        if keys_hash(train) != a['evaluation_coverage']['train_keys_sha256'][key]:
            raise ValueError('Physical training cohort differs')
        physical_labels = (train.target_rank_21.clip(0, 1) * 100).round().astype(int).to_numpy()
        if learners.array_hash(physical_labels) != new['train_labels_sha256']:
            raise ValueError('Physical target labels differ')
        expected_train = learners.matrix(masked(train, MASKS[variant])).to_numpy()
        expected_common = learners.matrix(masked(common_input, MASKS[variant])).to_numpy()
        expected_native = learners.matrix(masked(tests[v], MASKS[variant])).to_numpy()
        if new['train_matrix_sha256'] != learners.array_hash(expected_train) or \
           new['test_matrix_sha256'] != [learners.array_hash(expected_common), learners.array_hash(expected_native)]:
            raise ValueError('Candidate matrices differ from physical frozen TI with declared mask')
        if new['model_params'] != old['model_params'] or new['target'] != old['target'] or \
           new['feature_transform'] != old['feature_transform'] or new['kind'] != old['kind']:
            raise ValueError('Canonical XGB model/target changed')
        f = native.loc[native.vintage == v]
        mature = f.exit_date_21.notna() & f.target_rank_21.notna() & (f.exit_date_21 <= pd.Timestamp('2026-07-01'))
        if a['quality'][key] != quality(f.loc[mature], f.loc[mature, 'pred'].to_numpy()):
            raise ValueError('Declared candidate quality differs')
        if keys_hash(f) != a['evaluation_coverage']['test_keys_sha256'][key] or \
           keys_hash(common.loc[common.vintage == v]) != a['evaluation_coverage']['common_keys_sha256']:
            raise ValueError('Retained original inference cohort differs')
    return dict(result=r, variant=variant, year=year, native=native, common=common,
                path=str(path), sha256=sha(path))


def summarize(root, reference_root, out, ti_paths):
    base = load_variant(reference_root, 'BASE')
    if base['result']['LEGACY_PARITY_PASS'] is not True:
        raise ValueError('Original BASE controls failed')
    if {str(v): sha(Path(ti_paths[v]) / 'TI_COMPACT.parquet') for v in (1, 2, 3)} != FROZEN_TI:
        raise ValueError('Original TI physical authority differs')
    frames = {v: load(Path(ti_paths[v])) for v in (1, 2, 3)}
    jobs = {}
    contracts = {}
    for path in Path(root).rglob('RESULT.json'):
        r = json.loads(path.read_text())
        if r.get('line') != LINE:
            continue
        job = load_year(path, base, frames)
        identity = (job['variant'], job['year'])
        if identity in jobs:
            raise ValueError('Duplicate ablation annual job')
        jobs[identity] = job
        c = {key: r[key] for key in ('input_sha256', 'baseline_input_contract',
             'fit_sources', 'sources', 'preregistration_sha256')}
        c['numeric_contract'] = normalized_numeric(r['numeric_contract'])
        c['input_contract'] = r['input_contract']
        if job['variant'] in contracts and contracts[job['variant']] != c:
            raise ValueError('Mixed annual source/profile/registration contracts')
        contracts[job['variant']] = c
    check_complete_matrix(jobs)
    shared = None
    for variant in MASKS:
        c = contracts[variant]
        comparable = {key: c[key] for key in ('input_sha256', 'baseline_input_contract',
            'fit_sources', 'sources', 'preregistration_sha256', 'numeric_contract')}
        comparable['sources'] = {key: value for key, value in comparable['sources'].items()
            if not key.startswith('compact21_feature_ablation_v1/')}
        if shared is None:
            shared = comparable
        elif shared != comparable:
            raise ValueError('Mixed source/numeric/preregistration contracts across feature masks')
    bc, bn = stability_by_date(base['common']), stability_by_date(base['native'])
    if any(any(len(pair['dates']) != 114 for pair in x['pairs'].values()) for x in (bc, bn)):
        raise ValueError('Original 114-date stability coverage differs')
    models = {'BASE': dict(predictive=base['eval'], common_stability=bc, native_stability=bn)}
    models['BASE']['native_stability_diagnostics'] = stability_diagnostics(base['native'], bn)
    models['BASE']['common_stability_diagnostics'] = stability_diagnostics(base['common'], bc)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for variant in MASKS:
        native = pd.concat([jobs[(variant, y)]['native'] for y in YEARS], ignore_index=True).sort_values(VECTOR_KEYS).reset_index(drop=True)
        common = pd.concat([jobs[(variant, y)]['common'] for y in YEARS], ignore_index=True).sort_values(VECTOR_KEYS).reset_index(drop=True)
        exact_frame(native, base['native'].sort_values(VECTOR_KEYS), VECTOR_KEYS + OUTCOMES,
                    'Combined original native outcomes')
        exact_frame(common, base['common'].sort_values(VECTOR_KEYS), VECTOR_KEYS,
                    'Combined original common cohort')
        ev = evaluate(native, quality_exit_cutoff='2026-07-01', expected_keys=base['native'][VECTOR_KEYS])
        if ev['coverage'] != base['eval']['coverage'] or ev['coverage']['mature_dates'] != 113:
            raise ValueError('Original 113-date mature quality coverage differs')
        paired = paired_compare(ev, base['eval'])
        paired['lower98_75_interpretation'] = ('Descriptive retained bound on repeatedly explored development history; '
            'four current masks and prior trials preclude a fresh or global familywise claim.')
        sc, sn = stability_by_date(common), stability_by_date(native)
        if any(any(len(pair['dates']) != 114 for pair in x['pairs'].values()) for x in (sc, sn)):
            raise ValueError('Candidate 114-date stability coverage differs')
        gates = decision_gates(ev, base['eval'], paired, sc, sn, bc, bn, True)
        models[variant] = dict(predictive=ev, paired_vs_BASE=paired,
            common_stability=sc, native_stability=sn, gate=gates,
            native_stability_diagnostics=stability_diagnostics(native, sn),
            common_stability_diagnostics=stability_diagnostics(common, sc),
            mask=mask_manifest()[variant])
        directory = out / variant
        directory.mkdir(exist_ok=True)
        native.to_parquet(directory / FILES[0], index=False)
        common.to_parquet(directory / FILES[1], index=False)
    result = dict(status=LINE+'_SUMMARY_COMPLETE', years=list(YEARS), variants=list(MASKS),
        models=models, contracts=contracts,
        annual_jobs={f'{variant}/{year}': dict(path=jobs[(variant, year)]['path'],
            sha256=jobs[(variant, year)]['sha256']) for variant in MASKS for year in YEARS},
        registry=dict(annual_jobs=len(jobs), candidate_vintage_fits=len(jobs)*3,
            independent_candidate_refits=len(jobs)*3, candidate_variants=len(MASKS)),
        all_controls_reproduced=True, all_independent_refits_PASS=True,
        production_adoption=False, negative_feedback_changed=False,
        portfolio_evaluation=False,
        interpretation=('Preregistered family ablations on already explored snapshots. '
            'Feature perturbations and label perturbations both contribute to instability; '
            'no automatic adoption or fresh holdout claim.'))
    result['files_sha256'] = {f'{variant}/{name}': sha(out/variant/name)
        for variant in MASKS for name in FILES[:2]}
    (out/'SUMMARY.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', required=True)
    parser.add_argument('--references', required=True)
    parser.add_argument('--out', required=True)
    for v in (1, 2, 3):
        parser.add_argument(f'--r{v}', required=True)
    args = parser.parse_args()
    result = summarize(args.inputs, args.references, args.out,
        {v: getattr(args, f'r{v}') for v in (1, 2, 3)})
    print(json.dumps({v: result['models'][v]['gate'] for v in MASKS}, indent=2))
