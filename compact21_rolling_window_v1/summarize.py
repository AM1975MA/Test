"""Independent validation of frozen Compact21 rolling training windows."""
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
from etf_trader.source_only.kernel import F2D_FEATURES
from compact21_rolling_window_v1.windows import WINDOWS, manifest, manifest_sha256
from compact21_rolling_window_v1.run import rolling_train

LINE = 'COMPACT21_ROLLING_WINDOW_V1'
YEARS = tuple(range(2017, 2027))
FILES = (
    'NATIVE_PREDICTIONS.parquet', 'COMMON_PREDICTIONS.parquet',
    'CONTROL_NATIVE_PREDICTIONS.parquet', 'CONTROL_COMMON_PREDICTIONS.parquet',
)


def check_complete_matrix(jobs):
    expected = {(variant, year) for variant in WINDOWS for year in YEARS}
    if set(jobs) != expected:
        missing = sorted(expected - set(jobs))
        extra = sorted(set(jobs) - expected)
        raise ValueError(f'Incomplete rolling matrix: missing={missing}, extra={extra}')


def _annual(reference, kind, year):
    return reference[kind].loc[reference[kind].signal_date.dt.year == year].sort_values(VECTOR_KEYS).reset_index(drop=True)


def physical_coverage(trains, tests, common):
    """Rebuild the legacy key contract with explicit LF on every OS."""
    result = dict(train_keys_sha256={str(v): keys_hash(trains[v]) for v in (1, 2, 3)},
        test_keys_sha256={str(v): keys_hash(tests[v]) for v in (1, 2, 3)},
        common_keys_sha256=keys_hash(common), common_rows=len(common),
        common_queries=common.signal_date.nunique(), quality_keys_sha256={},
        quality_rows={}, quality_queries={})
    for v in (1, 2, 3):
        frame = tests[v]
        mature = (frame.target_rank_21.notna() & frame.exit_date_21.notna() &
                  frame.exit_date_21.le(pd.Timestamp('2026-07-01')))
        q = frame.loc[mature]
        result['quality_keys_sha256'][str(v)] = keys_hash(q)
        result['quality_rows'][str(v)] = len(q)
        result['quality_queries'][str(v)] = q.signal_date.nunique()
    return result


def load_year(path, base, frames):
    path = Path(path)
    r = json.loads(path.read_text())
    variant = r.get('variant')
    if r.get('line') != LINE or variant not in WINDOWS or r.get('status') != LINE + '_COMPLETE':
        raise ValueError('Wrong rolling identity/status')
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
    years = WINDOWS[variant]
    if r.get('lookback_years') != years or r.get('window_rule_sha256') != manifest_sha256():
        raise ValueError('Rolling rule differs from registry')
    if r.get('window_manifest_sha256') != sha(path.parent.parent / 'WINDOW_MANIFEST.json') or \
       json.loads((path.parent.parent / 'WINDOW_MANIFEST.json').read_text()) != manifest():
        raise ValueError('Original rolling manifest differs')
    trains, tests, common_input = select_original_frames(frames, year)
    physical_trains = {v: rolling_train(trains[v], year, years) for v in (1, 2, 3)}
    contract = r['input_contract']
    for key, value in dict(
        line=LINE, original_ti_sha256=br['input_sha256'],
        signal_cutoff='2026-06-30', quality_exit_cutoff='2026-07-01',
        common_inference_repeat=2,
        train_cohorts='original_native_eligible_mature_then_strict_rolling_start',
        rolling_start=f'{year-years}-01-01',
        retained_training_rows={str(v): len(physical_trains[v]) for v in (1, 2, 3)},
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
    if a['evaluation_coverage'] != physical_coverage(physical_trains, tests, common_input) or \
       a['determinism_PASS'] is not True:
        raise ValueError('Physical rolling coverage/refit differs')
    for field in ('test_keys_sha256', 'common_keys_sha256', 'common_rows',
                  'common_queries', 'quality_keys_sha256', 'quality_rows', 'quality_queries'):
        if a['evaluation_coverage'][field] != old_a['evaluation_coverage'][field]:
            raise ValueError('Original inference/quality cohort differs')
    for field in ('transforms', 'control_transforms', 'independent_refits', 'legacy_control'):
        if set(a[field]) != {'1', '2', '3'}:
            raise ValueError('Missing vintage audit: ' + field)
    for v in (1, 2, 3):
        key = str(v)
        new, old = a['transforms'][key], old_a['transforms'][key]
        validate_maturity(new, year, f'Rolling {variant}/{year}/{v}')
        prediction_audit(new, common, native, v, f'Rolling {variant}/{year}/{v}')
        if a['control_transforms'][key] != old:
            raise ValueError('Original BASE fit metadata differs')
        for field in ('feature_names', 'cutoff'):
            if new[field] != old[field]:
                raise ValueError('Original feature schema/cutoff differs: ' + field)
        if new['feature_names'] != list(F2D_FEATURES):
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
        # Independently tie the declared rolling cohort to physical frozen panels.
        train = physical_trains[v]
        if keys_hash(train) != a['evaluation_coverage']['train_keys_sha256'][key]:
            raise ValueError('Physical training cohort differs')
        physical_labels = (train.target_rank_21.clip(0, 1) * 100).round().astype(int).to_numpy()
        physical_groups = train.groupby('signal_date', sort=True).size().to_numpy()
        if learners.array_hash(physical_labels) != new['train_labels_sha256'] or \
           learners.array_hash(physical_groups) != new['train_groups_sha256'] or \
           new['train_rows'] != len(train):
            raise ValueError('Physical target labels differ')
        expected_train = learners.matrix(train).to_numpy()
        expected_common = learners.matrix(common_input).to_numpy()
        expected_native = learners.matrix(tests[v]).to_numpy()
        if new['train_matrix_sha256'] != learners.array_hash(expected_train) or \
           new['test_matrix_sha256'] != [learners.array_hash(expected_common), learners.array_hash(expected_native)]:
            raise ValueError('Candidate matrices differ from physical frozen TI with rolling start')
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
            raise ValueError('Duplicate rolling annual job')
        jobs[identity] = job
        c = {key: r[key] for key in ('input_sha256', 'baseline_input_contract',
             'fit_sources', 'sources', 'preregistration_sha256')}
        c['numeric_contract'] = normalized_numeric(r['numeric_contract'])
        c['input_contract'] = {key: value for key, value in r['input_contract'].items()
            if key not in ('rolling_start', 'retained_training_rows')}
        if job['variant'] in contracts and contracts[job['variant']] != c:
            raise ValueError('Mixed annual source/profile/registration contracts')
        contracts[job['variant']] = c
    check_complete_matrix(jobs)
    shared = None
    for variant in WINDOWS:
        c = contracts[variant]
        comparable = {key: c[key] for key in ('input_sha256', 'baseline_input_contract',
            'fit_sources', 'sources', 'preregistration_sha256', 'numeric_contract')}
        if shared is None:
            shared = comparable
        elif shared != comparable:
            raise ValueError('Mixed source/numeric/preregistration contracts across windows')
    bc, bn = stability_by_date(base['common']), stability_by_date(base['native'])
    if any(any(len(pair['dates']) != 114 for pair in x['pairs'].values()) for x in (bc, bn)):
        raise ValueError('Original 114-date stability coverage differs')
    models = {'BASE': dict(predictive=base['eval'], common_stability=bc, native_stability=bn)}
    models['BASE']['native_stability_diagnostics'] = stability_diagnostics(base['native'], bn)
    models['BASE']['common_stability_diagnostics'] = stability_diagnostics(base['common'], bc)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for variant in WINDOWS:
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
            'three rolling windows and prior trials preclude a fresh or global familywise claim.')
        sc, sn = stability_by_date(common), stability_by_date(native)
        if any(any(len(pair['dates']) != 114 for pair in x['pairs'].values()) for x in (sc, sn)):
            raise ValueError('Candidate 114-date stability coverage differs')
        gates = decision_gates(ev, base['eval'], paired, sc, sn, bc, bn, True)
        models[variant] = dict(predictive=ev, paired_vs_BASE=paired,
            common_stability=sc, native_stability=sn, gate=gates,
            native_stability_diagnostics=stability_diagnostics(native, sn),
            common_stability_diagnostics=stability_diagnostics(common, sc),
            window=manifest()[variant])
        directory = out / variant
        directory.mkdir(exist_ok=True)
        native.to_parquet(directory / FILES[0], index=False)
        common.to_parquet(directory / FILES[1], index=False)
    result = dict(status=LINE+'_SUMMARY_COMPLETE', years=list(YEARS), variants=list(WINDOWS),
        models=models, contracts=contracts,
        annual_jobs={f'{variant}/{year}': dict(path=jobs[(variant, year)]['path'],
            sha256=jobs[(variant, year)]['sha256']) for variant in WINDOWS for year in YEARS},
        registry=dict(annual_jobs=len(jobs), candidate_vintage_fits=len(jobs)*3,
            independent_candidate_refits=len(jobs)*3, candidate_variants=len(WINDOWS)),
        all_controls_reproduced=True, all_independent_refits_PASS=True,
        production_adoption=False, negative_feedback_changed=False,
        portfolio_evaluation=False,
        interpretation=('Preregistered rolling training windows on already explored snapshots. '
            'Feature and label perturbations remain potential instability sources; '
            'no automatic adoption or fresh holdout claim.'))
    result['files_sha256'] = {f'{variant}/{name}': sha(out/variant/name)
        for variant in WINDOWS for name in FILES[:2]}
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
    print(json.dumps({v: result['models'][v]['gate'] for v in WINDOWS}, indent=2))

