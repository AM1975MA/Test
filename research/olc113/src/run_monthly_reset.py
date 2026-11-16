"""Monthly baseline continuation for every idle learned account; saved fits only."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

SOURCE = Path(__file__).resolve().parents[2]/'olc111'
sys.path.insert(0, str(SOURCE/'src'))
import run_olc111 as previous
from research_pipeline import HEADS, build_research_bundle, execution_panel
from replay_engine import simulate

ARMS = ('MEAN_RESET', 'PRICE_RESET', 'VIX_RESET', 'TERM_RESET')
SCENARIOS = previous.SCENARIOS
ARTIFACTS = ('DAILY.csv.gz', 'ORDERS.csv.gz', 'INSTRUCTIONS.csv.gz', 'DECISIONS.npz',
             'DECISIONS_META.json.gz', 'POLICY_TRACE.csv.gz')


class ResetOverlay(previous.AccountPolicy):
    """Use the unchanged monthly target after readiness, including from cash."""
    def __init__(self, bundle, arm, fit_cache):
        if arm not in ARMS:
            raise ValueError('RESET_ARM')
        self.output_arm = arm
        super().__init__(bundle, arm.removesuffix('_RESET'), fit_cache)

    def __call__(self, k, current, context):
        scheduled = context['scheduled'] and not context['initial']
        idle = context['pending'] is None and not context['queued']
        ready = scheduled and all(self.fit_cache.get(k)[head] is not None for head in HEADS)
        cash_reset = False
        if ready and idle:
            cash_reset = float(np.sum(current)) <= 1e-8
            row = self._record(k, current, context)
            row.update(model_ready_all=True, action='SCHEDULED', status='MONTHLY_BASELINE_RESET')
            self.trace.append(row)
            answer = dict(weights=np.array(self.bundle['targets'][k], copy=True),
                          reason='SCHEDULED', force=False,
                          meta=dict(status='MONTHLY_BASELINE_RESET'))
        else:
            answer = super().__call__(k, current, context)
        self.trace[-1].update(arm=self.output_arm, underlying_arm=self.arm,
                              monthly_cash_reset=cash_reset)
        if answer is not None:
            answer['meta'].update(arm=self.output_arm, underlying_arm=self.arm,
                                  monthly_cash_reset=cash_reset)
        return answer


class SavedOnlyFitCache(previous.MonthlyFitCache):
    """Deserialize old models; no code path can call the fitting function."""
    def get(self, k):
        cutoff = self.cutoff(k)
        if cutoff in self.cache:
            return self.cache[cutoff]
        path = None if self.folder is None else self.folder/f'FIT_{cutoff:06d}.json.gz'
        if path is None or not path.is_file():
            raise ValueError('SAVED_MODEL_MISSING_REFIT_FORBIDDEN')
        stored = previous._read_json(path)
        if (stored['provenance'] != self.provenance or stored['cutoff'] != cutoff or
                stored['fit_options'] != self.options):
            raise ValueError('FIT_CACHE_PROVENANCE_MISMATCH')
        fitted = {}
        for head in HEADS:
            record = stored['heads'][head]
            if record is None:
                fitted[head] = None
                continue
            models = {}
            for arm, values in record['models'].items():
                models[arm] = previous.AdvantageModel(values['model_name'], values['coefficients'],
                    values['bootstrap_coefficients'], values['transforms'],
                    values['feature_counts'], values['metadata'])
                digest = hashlib.sha256(previous._json_bytes(models[arm].to_dict())).hexdigest()
                if digest != record['hashes'][arm]:
                    raise ValueError('FIT_CACHE_MODEL_HASH_MISMATCH')
            fitted[head] = dict(models=models, meta=record['meta'], hashes=record['hashes'])
        self.cache[cutoff] = fitted
        return fitted


def verify_freeze(root):
    root = Path(root).resolve()
    freeze = previous._read_json(root/'docs/EXPERIMENT_FREEZE.json')
    for kind in ('code_hashes', 'input_hashes'):
        for relative, digest in freeze[kind].items():
            path = root/relative
            if not path.is_file() or previous.sha(path) != digest:
                raise ValueError('FREEZE_HASH_MISMATCH:'+relative)
    if previous.sha(root/'docs/DESIGN_AND_PROTOCOL.md') != freeze['protocol_sha256']:
        raise ValueError('FREEZE_PROTOCOL_MISMATCH')
    if (freeze['arms'] != list(ARMS) or freeze['scenarios'] != list(SCENARIOS) or
            freeze['planned_paths'] != 12):
        raise ValueError('FREEZE_MATRIX_MISMATCH')
    # OLC112 verifies OLC111 transitively; both old freezes remain authoritative.
    path = root.parent/'olc112/src/run_rotation_overlay.py'
    spec = importlib.util.spec_from_file_location('olc113_frozen_rotation', path)
    rotation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rotation)
    rotation.verify_freeze(root.parent/'olc112')
    return freeze


def monthly_reset_metrics(result):
    """Count issued resets separately from learned ENTRY and from actual orders.

    Unfilled means no executed order for the instruction, not a claim that the
    simulator discarded it. A quote-deferred reset can remain pending at end.
    """
    instructions = result['instructions']
    ids = {int(row.instruction_id) for row in instructions.itertuples()
           if isinstance(getattr(row, 'meta', None), dict) and row.meta.get('monthly_cash_reset', False)}
    orders = result['orders']
    filled = ids.intersection(int(i) for i in orders.instruction_id)
    return dict(monthly_cash_reset_instructions=len(ids),
                monthly_cash_reset_realized_instructions=len(filled),
                monthly_cash_reset_unfilled_instructions=len(ids-filled),
                monthly_cash_reset_orders=int(orders.instruction_id.isin(ids).sum()),
                monthly_cash_reset_fill_definition='at_least_one_actual_order_for_instruction')


def compare_mean_with_base(source, scenario, result, folder=None):
    """Exact all-column daily and order comparison, including calendar/identities."""
    control = Path(source)/'results'/f'BASE__{scenario}'
    original = {key:pd.read_csv(control/name, float_precision='round_trip')
                for key, name in [('daily', 'DAILY.csv.gz'), ('orders', 'ORDERS.csv.gz')]}
    discretionary = result['orders'].loc[result['orders'].reason.isin(HEADS)]
    checks = {}
    for key in ('daily', 'orders'):
        try:
            pd.testing.assert_frame_equal(original[key].reset_index(drop=True),
                result[key].reset_index(drop=True), check_dtype=False, check_exact=True)
            checks[key] = True
        except AssertionError:
            checks[key] = False
    if discretionary.empty and not all(checks.values()):
        raise AssertionError(('MEAN_RESET_BASE_PARITY', checks))
    record = dict(scenario=scenario, discretionary_orders=len(discretionary),
                  exact_baseline_parity=all(checks.values()), exact_daily_parity=checks['daily'],
                  exact_order_ledger_parity=checks['orders'],
                  comparison='all_daily_columns_and_entire_order_ledger_exact',
                  control_daily_sha256=previous.sha(control/'DAILY.csv.gz'),
                  control_orders_sha256=previous.sha(control/'ORDERS.csv.gz'))
    if folder is not None:
        previous._write_json(Path(folder)/'MEAN_BASE_REPLICATION.json', record)
    return record


def save_completed_path(folder, result, trace, metrics, source):
    """Publish the completion marker only after artifacts and parity receipts."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    # A failed/retried incomplete path cannot retain an old completion marker.
    (folder/'METRICS.json').unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='.saving-', dir=folder) as temporary:
        stage = Path(temporary)
        previous.save_path(stage, result, trace, metrics)
        for name in ARTIFACTS:
            (stage/name).replace(folder/name)
    names = list(ARTIFACTS)
    if metrics['arm'] == 'MEAN_RESET':
        compare_mean_with_base(source, metrics['scenario'], result, folder)
        names.append('MEAN_BASE_REPLICATION.json')
    receipt = dict(path_id=metrics['path_id'], artifacts={name:previous.sha(folder/name) for name in names},
                   metrics_payload_sha256=hashlib.sha256(previous._json_bytes(metrics)).hexdigest())
    previous._write_json(folder/'PATH_RECEIPT.json', receipt)
    completed = dict(metrics, path_receipt_sha256=previous.sha(folder/'PATH_RECEIPT.json'))
    previous._write_json(folder/'METRICS.json', completed)
    return completed


def load_completed_path(folder, source, arm, scenario):
    folder = Path(folder)
    required = list(ARTIFACTS)+['PATH_RECEIPT.json', 'METRICS.json']
    if arm == 'MEAN_RESET':
        required.append('MEAN_BASE_REPLICATION.json')
    if any(not (folder/name).is_file() for name in required):
        raise ValueError('INCOMPLETE_SAVED_PATH_RECEIPT')
    metrics = previous._read_json(folder/'METRICS.json')
    receipt = previous._read_json(folder/'PATH_RECEIPT.json')
    path_id = f'{arm}__{scenario}'
    if (metrics.get('path_id') != path_id or metrics.get('arm') != arm or metrics.get('scenario') != scenario or
            receipt.get('path_id') != path_id or
            metrics.get('path_receipt_sha256') != previous.sha(folder/'PATH_RECEIPT.json')):
        raise ValueError('PATH_RECEIPT_MISMATCH')
    payload = {key:value for key,value in metrics.items() if key != 'path_receipt_sha256'}
    if hashlib.sha256(previous._json_bytes(payload)).hexdigest() != receipt.get('metrics_payload_sha256'):
        raise ValueError('METRICS_RECEIPT_MISMATCH')
    artifacts = set(required)-{'PATH_RECEIPT.json', 'METRICS.json'}
    if set(receipt['artifacts']) != artifacts:
        raise ValueError('PATH_RECEIPT_ARTIFACTS_MISMATCH')
    for name, digest in receipt['artifacts'].items():
        if previous.sha(folder/name) != digest:
            raise ValueError('PATH_RECEIPT_HASH_MISMATCH:'+name)
    result = dict(daily=pd.read_csv(folder/'DAILY.csv.gz', float_precision='round_trip'),
                  orders=pd.read_csv(folder/'ORDERS.csv.gz', float_precision='round_trip'))
    if arm == 'MEAN_RESET':
        observed = compare_mean_with_base(source, scenario, result)
        if previous._read_json(folder/'MEAN_BASE_REPLICATION.json') != observed:
            raise ValueError('BASELINE_RECEIPT_MISMATCH')
    return metrics, result['daily']


def run(root, resume=False):
    root = Path(root).resolve()
    source = root.parent/'olc111'
    freeze = verify_freeze(root)
    freeze_sha = previous.sha(root/'docs/EXPERIMENT_FREEZE.json')
    source_freeze_sha = previous.sha(source/'docs/EXPERIMENT_FREEZE.json')
    results = root/'results'
    results.mkdir(exist_ok=True)
    manifest_path = results/'RUN_MANIFEST.json'
    if manifest_path.exists():
        if not resume:
            raise FileExistsError('Use resume under unchanged freeze')
        manifest = previous._read_json(manifest_path)
        if manifest['freeze_sha256'] != freeze_sha:
            raise ValueError('RUN_FREEZE_MISMATCH')
    else:
        manifest = dict(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            freeze_sha256=freeze_sha, source_study_freeze_sha256=source_freeze_sha,
            code_hashes=freeze['code_hashes'], input_hashes=freeze['input_hashes'],
            arms=list(ARMS), scenarios=list(SCENARIOS), planned_paths=12,
            completed_paths=0, completed_path_ids=[], adaptive_after_olc111=True,
            adaptive_after_olc112=True, pristine_holdout=False, new_model_fits=0,
            primary_arm='PRICE_RESET', single_change='monthly_baseline_reset_including_cash')
    previous._write_json(manifest_path, manifest)
    scores, annual, common, drawdowns, replications = [], [], [], [], []
    with threadpool_limits(limits=1):
        bundle = build_research_bundle(source, resume=True)
        cache = SavedOnlyFitCache(bundle['bank'], bundle['panel']['dates'], bundle['begin'],
                                  folder=source/'results/FITS', provenance=source_freeze_sha)
        readiness = cache.prepare()
        if readiness != previous._read_json(source/'results/FIT_READINESS.json'):
            raise AssertionError('READINESS_CHANGED')
        previous._write_json(results/'FIT_READINESS.json', readiness)
        print('Using saved OLC111 fits; no model is retrained', flush=True)
        for arm in ARMS:
            for scenario, (ticket, impact, fill) in SCENARIOS.items():
                folder = results/f'{arm}__{scenario}'
                if resume and (folder/'METRICS.json').exists():
                    metrics, daily = load_completed_path(folder, source, arm, scenario)
                else:
                    callback = ResetOverlay(bundle, arm, cache)
                    panel = execution_panel(bundle['panel'], fill)
                    result = simulate(panel, bundle['f'], lambda k,w:bundle['targets'][k], bundle['monthly'],
                        legacy=bundle['core'], account_policy=callback, allow_scheduled_hold=True,
                        ticket=ticket, impact=impact, start=str(panel['dates'][bundle['begin']].date()),
                        end=str(panel['dates'][-1].date()))
                    metrics = previous.summarize_path(bundle, arm, scenario, result, readiness)
                    metrics.update(source_model_arm=arm.removesuffix('_RESET'), new_model_fits=0,
                                   adaptive_after_olc111=True, adaptive_after_olc112=True,
                                   **monthly_reset_metrics(result))
                    metrics = save_completed_path(folder, result, callback.trace, metrics, source)
                    daily = result['daily']
                if arm == 'MEAN_RESET':
                    replications.append(previous._read_json(folder/'MEAN_BASE_REPLICATION.json'))
                scores.append(metrics)
                annual.extend(previous.annual_rows(bundle, daily, arm, scenario))
                drawdowns.extend(previous.drawdown_rows(daily, arm, scenario))
                segment = previous.performance_window(bundle['core'], daily,
                    start_idx=readiness['postwarmup_start_idx'])
                common.append(dict(path_id=f'{arm}__{scenario}', arm=arm, scenario=scenario, **segment))
                previous._csv(pd.DataFrame(scores), results/'SCORES.csv')
                manifest.update(completed_paths=len(scores), completed_path_ids=[r['path_id'] for r in scores])
                previous._write_json(manifest_path, manifest)
                print(f'{len(scores)}/12 {arm}__{scenario}: CAGR {metrics["cagr"]:.6f}, DD {metrics["maxdd_sampled"]:.6f}', flush=True)
        previous._csv(pd.DataFrame(annual), results/'ANNUAL_RETURNS.csv')
        previous._csv(pd.DataFrame(common), results/'COMMON_POST_WARMUP.csv')
        previous._csv(pd.DataFrame(drawdowns), results/'DRAWDOWN_EPISODES.csv')
        previous._write_json(results/'MEAN_BASE_REPLICATION.json', replications)
    verify_freeze(root)
    manifest.update(end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), completed_paths=12)
    previous._write_json(manifest_path, manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    run(args.root, args.resume)
