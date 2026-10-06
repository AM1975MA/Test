#!/usr/bin/env python3
"""Frozen learner-swap gates, recomputed from every annual pair/repeat cell."""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
from statistics import mean

LINE = 'COMPACT21_LEARNER_SWAP_V1'
VARIANTS = ('BASE', 'RIDGE', 'LGBM_LAMBDARANK')
YEARS = list(range(2017, 2027))
PAIRS = ('1-2', '1-3', '2-3')
REPEATS = ('1', '2', '3')


def read_json(path):
    def reject(value):
        raise ValueError(f'Nonfinite JSON value {value} in {path}')
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f'Duplicate JSON key {key} in {path}')
            out[key] = value
        return out
    data = json.loads(Path(path).read_text(), parse_constant=reject, object_pairs_hook=unique)
    validate_finite(data)
    return data


def validate_finite(data):
    if isinstance(data, float) and not math.isfinite(data):
        raise ValueError('Nonfinite numeric evidence')
    if isinstance(data, dict):
        for value in data.values(): validate_finite(value)
    elif isinstance(data, list):
        for value in data: validate_finite(value)


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'Invalid numeric {name}')
    return value


def require_hashes(values, name):
    import re
    if not isinstance(values, dict) or not values:
        raise ValueError(f'Missing {name}')
    if not all(isinstance(v, str) and re.fullmatch('[a-f0-9]{64}', v) for v in values.values()):
        raise ValueError(f'Invalid {name}')


def aggregate_cells(row):
    if row.get('years') != YEARS or set(row.get('per_year', {})) != set(map(str, YEARS)):
        raise ValueError('Incomplete or noncanonical annual folds; require 2017–2026')
    result = {}
    expected_metrics = {
        'common_inference': {'rank_mean_abs', 'rank_p99_abs', 'mean_daily_spearman', 'top1_disagreement_fraction', 'top5_jaccard'},
        'native_inference': {'rank_mean_abs', 'rank_p99_abs', 'mean_daily_spearman', 'top1_disagreement_fraction', 'top5_jaccard'},
        'quality': {'daily_spearman_vs_target', 'ndcg5', 'ndcg10', 'pred_top1_mean_realized_pct', 'top5_realized_overlap'},
    }
    for scope, required in expected_metrics.items():
        yearly = []
        for year in YEARS:
            cell = row['per_year'][str(year)]
            values = cell.get(scope, {})
            if set(values) != set(REPEATS if scope == 'quality' else PAIRS):
                raise ValueError(f'Incomplete {scope} cells in {year}')
            metrics = set(next(iter(values.values())))
            if not required.issubset(metrics) or any(set(v) != metrics for v in values.values()):
                raise ValueError(f'Incomplete {scope} metrics in {year}')
            for member, item in values.items():
                for key, val in item.items():
                    val = number(val, f'{scope}/{year}/{member}/{key}')
                    if key in ('daily_spearman_vs_target', 'mean_daily_spearman'):
                        if not -1 <= val <= 1: raise ValueError(f'Invalid correlation {key}')
                    elif not 0 <= val <= 1:
                        raise ValueError(f'Invalid bounded metric {key}')
            yearly.append({key: mean(item[key] for item in values.values()) for key in metrics})
        if any(set(v) != set(yearly[0]) for v in yearly):
            raise ValueError(f'Metric schema changes across years: {scope}')
        result[scope] = {key: mean(v[key] for v in yearly) for key in yearly[0]}
    reported = row.get('aggregate')
    if reported is None or set(reported) != set(result):
        raise ValueError('Missing aggregate')
    for scope, values in result.items():
        if set(reported[scope]) != set(values): raise ValueError('Aggregate metric schema mismatch')
        for key, value in values.items():
            if not math.isclose(number(reported[scope][key], key), value, abs_tol=1e-14, rel_tol=1e-12):
                raise ValueError(f'Aggregate inconsistent with equally weighted annual cells: {scope}/{key}')
    return result


def contract_checks(row):
    contract = row.get('input_contract', {})
    required = {'protocol': LINE, 'years': YEARS, 'train_cohorts': 'native_no_intersection',
                'common_inference_repeat': 2, 'signal_cutoff': '2026-06-30', 'quality_exit_cutoff': '2026-07-01'}
    if any(contract.get(k) != v for k, v in required.items()):
        raise ValueError('Missing or noncanonical benchmark input contract')
    require_hashes(contract.get('canonical_source_sha256'), 'canonical source hashes')
    require_hashes(contract.get('learner_source_sha256'), 'learner source hashes')
    require_hashes(row.get('input_sha256'), 'input hashes')
    if set(row['input_sha256']) != set(REPEATS): raise ValueError('Incomplete snapshot input hashes')
    if not isinstance(row.get('environment'), dict) or not row['environment'] or any(not isinstance(v, str) or not v for v in row['environment'].values()):
        raise ValueError('Missing environment versions')
    for year in YEARS:
        c = row['per_year'][str(year)]
        if set(c.get('train_rows', {})) != set(REPEATS) or set(c.get('test_rows', {})) != set(REPEATS):
            raise ValueError('Missing native training/inference counts')
        for key in ('train_rows', 'test_rows'):
            if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in c[key].values()): raise ValueError('Invalid native cohort counts')
        if isinstance(c.get('common_test_rows'), bool) or not isinstance(c.get('common_test_rows'), int) or c['common_test_rows'] <= 0:
            raise ValueError('Missing common test rows')
        coverage = c.get('evaluation_coverage', {})
        for key in ('train_keys_sha256', 'test_keys_sha256', 'quality_keys_sha256'):
            require_hashes(coverage.get(key), key)
            if set(coverage[key]) != set(REPEATS): raise ValueError('Incomplete cohort signature repeats')
        require_hashes({'common_keys_sha256': coverage.get('common_keys_sha256')}, 'common cohort signature')
        for key in ('quality_rows', 'quality_queries'):
            if set(coverage.get(key, {})) != set(REPEATS) or any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in coverage[key].values()):
                raise ValueError('Invalid quality cohort counts')
        if coverage.get('common_rows') != c['common_test_rows'] or isinstance(coverage.get('common_queries'), bool) or not isinstance(coverage.get('common_queries'), int) or coverage['common_queries'] <= 0:
            raise ValueError('Invalid common cohort counts')
        if any(coverage['quality_rows'][r] > c['test_rows'][r] or coverage['quality_queries'][r] > coverage['quality_rows'][r] for r in REPEATS):
            raise ValueError('Impossible quality coverage')
    return contract


def summarize(root):
    rows = {}
    for p in Path(root).rglob('*.json'):
        q = read_json(p)
        if q.get('status') == LINE + '_BENCHMARK_COMPLETE':
            if q.get('variant') in rows: raise ValueError('Duplicate variant result')
            rows[q['variant']] = q
    if set(rows) != set(VARIANTS): raise ValueError(f'Incomplete variants: {set(rows)}')
    aggregates = {}
    for variant, row in rows.items():
        aggregates[variant] = aggregate_cells(row)
        contract_checks(row)
    baseline = rows['BASE']
    for q in rows.values():
        if any(q[key] != baseline[key] for key in ('years', 'input_sha256', 'environment', 'input_contract')):
            raise ValueError('Mismatched benchmark provenance')
        for y in map(str, YEARS):
            if any(q['per_year'][y][key] != baseline['per_year'][y][key]
                   for key in ('train_rows', 'test_rows', 'common_test_rows', 'evaluation_coverage')):
                raise ValueError('Benchmark cohorts/coverage differ across learners')
    b = aggregates['BASE']; table = []; eligible = []
    for variant in VARIANTS:
        q = rows[variant]; a = aggregates[variant]; s = a['common_inference']; bs = b['common_inference']
        improve = 1 - s['rank_mean_abs'] / bs['rank_mean_abs'] if bs['rank_mean_abs'] else 0
        maturity = all(c.get('maturity_PASS') is True for c in q['per_year'].values()) and q.get('ALL_MATURITY_PASS') is True
        determinism = all(c.get('determinism', {}).get('PASS') is True and not isinstance(c['determinism'].get('max_abs'), bool) and c['determinism'].get('max_abs') == 0.0 and c['determinism'].get('common_and_native_bytes_exact') is True for c in q['per_year'].values()) and q.get('ALL_DETERMINISM_PASS') is True
        checks = {'rank_mad_reduction_ge25pct': improve >= .25,
                  'common_top1_not_worse': s['top1_disagreement_fraction'] <= bs['top1_disagreement_fraction'],
                  'spearman_not_worse': s['mean_daily_spearman'] >= bs['mean_daily_spearman'],
                  'native_top1_not_worse': a['native_inference']['top1_disagreement_fraction'] <= b['native_inference']['top1_disagreement_fraction'],
                  'quality_ndcg5_ge95pct': a['quality']['ndcg5'] >= .95 * b['quality']['ndcg5'],
                  'quality_top1_realized_pct_ge95pct': a['quality']['pred_top1_mean_realized_pct'] >= .95 * b['quality']['pred_top1_mean_realized_pct'],
                  'maturity': maturity, 'determinism': determinism}
        ok = variant != 'BASE' and all(checks.values())
        if ok: eligible.append(variant)
        table.append({'variant': variant, 'rank_mad_reduction_pct': 100 * improve, 'aggregate': a, 'checks': checks, 'ADVANCE_FULL_REPLAY': ok})
    full = list(VARIANTS)
    return {'status': LINE + '_BENCHMARK_SUMMARY', 'ranking': table, 'eligible': eligible,
            'full_matrix': {'include': [{'variant': v, 'repeat': i} for v in full for i in (1, 2, 3)]},
            'full_matrix_purpose': 'All nine preregistered diagnostic transplants; failed benchmark gates cannot be rescued by CAGR.',
            'models': rows, 'weighting': 'Equal annual folds; each fold equally averages all three pairs or all three native quality repeats.',
            'production_adoption': False}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--inputs', required=True); ap.add_argument('--out', required=True); a = ap.parse_args()
    q = summarize(a.inputs); p = Path(a.out); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(q, indent=2, allow_nan=False) + '\n')
    print(json.dumps(q['ranking'], indent=2, allow_nan=False))
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f: f.write('matrix=' + json.dumps(q['full_matrix'], separators=(',', ':')) + '\n')
if __name__ == '__main__': main()
