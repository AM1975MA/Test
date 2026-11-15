"""Re-derive and audit all 78 frozen OLC110 paths without production imports."""
from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
from pathlib import Path
import sys
import traceback

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from signal_reference import ARMS, SCENARIOS, prepare_panel, prepare_features, SelectorReference
from account_reference import AccountAudit, read_path

REFERENCE_FILES = ('signal_reference.py','policy_reference.py','account_reference.py','run_independent_audit.py')
FORBIDDEN_IMPORTS = {'engine','protection','dedup_selectors','cluster_selectors','signals','core'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def independent_import_check(folder):
    details = {}
    for name in REFERENCE_FILES:
        imports = []
        for node in ast.walk(ast.parse((folder/name).read_text())):
            if isinstance(node,ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node,ast.ImportFrom):
                imports.append(node.module or '')
        assert not {value.split('.')[0] for value in imports} & FORBIDDEN_IMPORTS, ('PRODUCTION_IMPORT',name)
        details[name] = dict(sha256=digest(folder/name),imports=sorted(set(imports)))
    return details


def load_reference(root):
    with np.load(root/'source/data/XETRA_EUR_ETF.npz',allow_pickle=False) as source:
        raw = {key:source[key] for key in source.files}
    with np.load(root/'data/LIQUIDITY.npz',allow_pickle=False) as source:
        assert np.array_equal(source['names'],raw['names']) and np.array_equal(source['dates'],raw['dates'])
        turnover = source['turnover']
    prepared = prepare_panel(raw)
    features = prepare_features(prepared,turnover)
    return SelectorReference(prepared,features)


def verify_olc109_selection(root, selector):
    folder = root.parent/'olc109/results_stage2/DEDUP_DUAL_TREND_OPP__BASE'
    with np.load(folder/'DECISIONS.npz',allow_pickle=False) as saved:
        count = 0
        for k,wanted in zip(saved['k'],saved['raw_weights']):
            actual,_ = selector.selection(int(k))
            assert np.array_equal(actual,wanted), ('ORIGINAL_SELECTOR_REPLICATION',int(k))
            count += 1
    return dict(status='PASS_ORIGINAL_OLC109_SELECTOR',monthly_targets_reconstructed=count,
                source=str(folder/'DECISIONS.npz'))


def verify_baseline(root, saved, scenario):
    previous = root.parent/'olc109/results_stage2'/f'DEDUP_DUAL_TREND_OPP__{scenario}'
    maximum, tables = 0., 0
    for key,filename in [('daily','DAILY.csv.gz'),('orders','ORDERS.csv.gz')]:
        before = pd.read_csv(previous/filename,float_precision='round_trip')
        after = saved[key]
        assert before.shape == after.shape and list(before.columns) == list(after.columns), ('BASELINE_SHAPE',scenario,key)
        for col in before:
            if pd.api.types.is_numeric_dtype(before[col]):
                error = float(np.max(np.abs(before[col].to_numpy(float)-after[col].to_numpy(float)))) if len(before) else 0.
                assert error < 1e-8, ('BASELINE_NUMERIC',scenario,key,col,error)
                maximum = max(maximum,error)
            else:
                assert before[col].astype(str).tolist() == after[col].astype(str).tolist(), ('BASELINE_TEXT',scenario,key,col)
        tables += 1
    with np.load(previous/'DECISIONS.npz',allow_pickle=False) as before:
        after = saved['decision_arrays']
        for key in before.files:
            assert before[key].shape == after[key].shape
            error = float(np.max(np.abs(before[key]-after[key]))) if before[key].size else 0.
            assert error < 1e-8, ('BASELINE_DECISIONS',scenario,key,error)
            maximum = max(maximum,error)
    return dict(scenario=scenario,status='PASS',maximum_difference=maximum,tables=tables+1)


def audit(root, *, only=None):
    root = Path(root).resolve()
    output = root/'validation'
    code = independent_import_check(output)
    (output/'VALIDATION_CODE_HASHES.json').write_text(json.dumps(code,indent=2)+'\n')
    selector = load_reference(root)
    historical_selector = verify_olc109_selection(root,selector)
    if only == 'ORIGINAL_SELECTOR':
        (output/'ORIGINAL_SELECTOR_REPLICATION.json').write_text(json.dumps(historical_selector,indent=2)+'\n')
        print(json.dumps(historical_selector),flush=True)
        return
    freeze = json.loads((root/'docs/EXPERIMENT_FREEZE.json').read_text())
    manifest = json.loads((root/'results/RUN_MANIFEST.json').read_text())
    assert freeze['planned_paths'] == 78 and freeze['arms'] == list(ARMS) and freeze['scenarios'] == list(SCENARIOS)
    for filename,expected in freeze['code_hashes'].items():
        assert digest(root/filename) == expected, ('FINANCIAL_CODE_CHANGED',filename)
    for filename,expected in freeze['input_hashes'].items():
        assert digest(root/filename) == expected, ('INPUT_CHANGED',filename)
    assert digest(root/'docs/DESIGN_AND_PROTOCOL.md') == freeze['protocol_sha256']
    assert manifest['code_hashes'] == freeze['code_hashes'] and manifest['input_hashes'] == freeze['input_hashes']
    all_paths = [f'{arm}__{scenario}' for arm in ARMS for scenario in SCENARIOS]
    selected_paths = all_paths if only is None else [only]
    if only is None:
        assert manifest['completed_paths'] == 78 and 'end_utc' in manifest, 'RUN_INCOMPLETE'
        actual_paths = sorted(path.parent.name for path in (root/'results').glob('*/METRICS.json'))
        assert actual_paths == sorted(all_paths), ('MISSING_OR_EXTRA_PATHS',actual_paths)
    rows,contributions,annual,replications,failures = [],[],[],[],[]
    for index,path_id in enumerate(selected_paths,1):
        folder = root/'results'/path_id
        try:
            saved = read_path(folder)
            reference = AccountAudit(selector,saved)
            independent,attribution,years = reference.run()
            rows.append(independent);contributions.extend(attribution);annual.extend(years)
            if independent['arm'] == 'BASE' and independent['scenario'] != 'NEXT_CLOSE':
                replications.append(verify_baseline(root,saved,independent['scenario']))
            print(f'{index}/{len(selected_paths)} PASS {path_id}: {independent["orders_independently_sized"]} orders, {independent["instructions_independently_rederived"]} targets, NAV error {independent["max_nav_cash_error"]:.3g}',flush=True)
        except Exception as error:
            failure = dict(path_id=path_id,error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc())
            failures.append(failure)
            print(f'{index}/{len(selected_paths)} FAIL {path_id}: {type(error).__name__} {error}',flush=True)
        # Save concrete audit progress, including failures, for resumability.
        suffix = '' if only is None else '_SINGLE'
        pd.DataFrame(rows).to_csv(output/f'INDEPENDENT_RECONSTRUCTIONS{suffix}.csv',index=False)
        (output/f'AUDIT_FAILURES{suffix}.json').write_text(json.dumps(failures,indent=2)+'\n')
    if only is None and not failures:
        observed_annual = pd.read_csv(root/'results/ANNUAL_RETURNS.csv',float_precision='round_trip').set_index(['path_id','year'])
        for row in annual:
            actual = observed_annual.loc[(row['path_id'],row['year'])]
            for field in ('annual_return','maxdd_in_year'):
                assert np.isclose(row[field],actual[field],rtol=1e-10,atol=1e-10), ('ANNUAL',row['path_id'],row['year'],field)
        assert len(annual) == 78*7 and all(set(item['year'] for item in annual if item['path_id']==path_id)==set(range(2020,2027)) for path_id in all_paths)
    suffix = '' if only is None else '_SINGLE'
    pd.DataFrame(contributions).to_csv(output/f'HOLDINGS_PNL_ATTRIBUTION{suffix}.csv',index=False)
    pd.DataFrame(annual).to_csv(output/f'INDEPENDENT_ANNUAL_RETURNS{suffix}.csv',index=False)
    pd.DataFrame(replications).to_csv(output/f'BASELINE_REPLICATION{suffix}.csv',index=False)
    counters = {key:int(sum(row.get(key,0) for row in rows)) for key in
                ('orders_independently_sized','instructions_independently_rederived','slot_trace_rows_checked',
                 'targeted_masks_rederived','targeted_execution_attempts_checked','untouched_quantities_checked',
                 'scheduled_selections_rederived','order_timestamps_checked')}
    maxima = {key:max((row.get(key,0.) for row in rows),default=0.) for key in
              ('max_nav_cash_error','max_order_quantity_error','max_order_cost_error','max_self_financing_error','max_daily_pnl_attribution_error')}
    result = dict(status='PASS_COMPLETE_INDEPENDENT_RECONSTRUCTION' if not failures and len(rows)==78 else 'PASS_SINGLE_PATH' if not failures else 'FAIL',
                  timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned_paths=len(selected_paths),passed_paths=len(rows),failed_paths=len(failures),
                  source_input_hashes=freeze['input_hashes'],financial_code_hashes=freeze['code_hashes'],protocol_sha256=freeze['protocol_sha256'],
                  original_selector_replication=historical_selector,baseline_replications=len(replications),
                  production_imports_in_reference=False,reference_dependencies='Python standard library, numpy, pandas, threadpoolctl; locally adapted OLC109 independent numerical conventions',
                  reconstructions=counters,maxima=maxima,failures=failures,
                  limits=['Does not certify point-in-time universe, vendor adjustment vintage, quote provenance, or market capacity.',
                          'NEXT_CLOSE quotes are accepted closes and its sampled drawdown is pre/post-close-fee, not intraday.',
                          'Reference and production implement the same declared protocol; agreement cannot establish economic profitability or prospective validity.'])
    (output/f'INDEPENDENT_QA{suffix}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('status','planned_paths','passed_paths','failed_paths','reconstructions','maxima')},indent=2),flush=True)
    assert not failures, f'{len(failures)} independent audits failed; see AUDIT_FAILURES{suffix}.json'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root',nargs='?',default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--only')
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        audit(args.root,only=args.only)
