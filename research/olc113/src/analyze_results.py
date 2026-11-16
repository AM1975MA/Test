"""Independent OLC113 results-only audit: zero fits and zero policy replays.

Reads twelve RESET accounts, six frozen OLC111 controls and twelve OLC112
predecessors. Reuses tested date/Close-ledger helpers and independently checks
execution prices, fees, pre-fee NAV and scheduled cash-reset completion.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARMS = ('MEAN_RESET', 'PRICE_RESET', 'VIX_RESET', 'TERM_RESET')
CONTROLS = ('BASE', 'STATIC_75')
SCENARIOS = ('NEXT_CLOSE', 'DOUBLE_COST', 'NEXT_OPEN')
TERMS = {'NEXT_CLOSE': (1., .0015, 'C'), 'DOUBLE_COST': (2., .003, 'C'),
         'NEXT_OPEN': (1., .0015, 'O')}
ARTIFACTS = ('DAILY.csv.gz', 'ORDERS.csv.gz', 'INSTRUCTIONS.csv.gz', 'DECISIONS.npz',
             'DECISIONS_META.json.gz', 'POLICY_TRACE.csv.gz')


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = _module('olc113_legacy_independent_audit', ROOT.parent/'olc111/src/analyze_results.py')
comparison = _module('olc113_rotation_comparisons', ROOT.parent/'olc112/src/analyze_results.py')


def _json(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def _bool(value):
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    raise ValueError('INVALID_BOOLEAN_LEDGER_VALUE')


def material_criterion(candidate, base):
    """Predeclared +3pp CAGR and nonworse signed MaxDD in both windows."""
    result = {}
    for window in ('whole', 'post'):
        left, right = candidate[window], base[window]
        gain = float(left['cagr'] - right['cagr'])
        dd_change = float(left['maxdd_sampled'] - right['maxdd_sampled'])
        growth_pass, dd_pass = gain >= .03 - 1e-12, dd_change >= -1e-12
        result[window] = dict(cagr_gain=gain, sampled_maxdd_change=dd_change,
            cagr_gain_at_least_3pp=bool(growth_pass), drawdown_nonworse=bool(dd_pass),
            material=bool(growth_pass and dd_pass))
    result.update(material_both_windows=all(result[w]['material'] for w in ('whole', 'post')),
                  target30_whole=bool(candidate['whole']['cagr'] >= .30),
                  target30_post=bool(candidate['post']['cagr'] >= .30))
    return result


def audit_execution_ledger(daily, orders, instructions, panel, scenario):
    """Reconstruct recorded fills and pending quote state; choose no new orders."""
    ticket, impact, price_key = TERMS[scenario]
    n = len(panel['names'])
    dates = np.asarray(panel['dates'], dtype='datetime64[D]')
    execution_raw = np.asarray(panel[price_key], float)
    execution_observed = np.asarray(panel.get('open_observed', panel['observed'])
                                   if price_key == 'O' else panel['observed'], bool)
    execution_valid = execution_observed & np.isfinite(execution_raw) & (execution_raw > 0)
    raw_close = np.asarray(panel['C'], float)
    close_valid = np.asarray(panel['observed'], bool) & np.isfinite(raw_close) & (raw_close > 0)
    marks = pd.DataFrame(np.where(close_valid, raw_close, np.nan)).ffill().to_numpy()
    last_seen = np.maximum.accumulate(np.where(close_valid, np.arange(len(dates))[:, None], -1), axis=0)
    by_signal, by_iid = {}, {}
    for row in instructions.itertuples():
        iid, signal, due = int(row.instruction_id), int(row.signal_idx), int(row.due_idx)
        target = np.asarray(_json(row.target_weights), float)
        if (iid in by_iid or target.shape != (n,) or not np.isfinite(target).all()
                or np.any(target < 0) or target.sum() > 1 + 1e-9 or due != signal + 1):
            raise ValueError('INSTRUCTION_LEDGER_CONTRACT')
        record = dict(iid=iid, signal=signal, due=due, target=target, reason=row.reason)
        by_iid[iid] = record
        by_signal.setdefault(signal, []).append(record)
    grouped = {int(k): group for k, group in orders.groupby('execution_idx')} if len(orders) else {}
    if not set(grouped).issubset(set(daily.k.astype(int))):
        raise ValueError('ORDER_OUTSIDE_DAILY_CALENDAR')
    units = np.zeros(n)
    cash, pending, queue = 10000., None, []
    errors = {key: 0. for key in ('fee_formula', 'notional_quantity', 'execution_price',
        'pre_fee_nav', 'close_nav', 'cash', 'gross', 'self_financing')}
    negative_cash = negative_units = execution_support_violations = pre_mark_violations = 0
    max_pre_mark_age = 0
    attempts, busy_by_k = [], {}
    start, end = int(daily.k.iloc[0]), int(daily.k.iloc[-1])
    queue.extend(by_signal.get(start-1, []))
    busy_by_k[start-1] = False
    for day in daily.itertuples():
        k = int(day.k)
        accepted = np.where(execution_valid[k], execution_raw[k], np.nan)
        mark = np.where(np.isfinite(accepted), accepted, marks[k-1])
        held_before = units > 1e-12
        for j in np.flatnonzero(held_before):
            seen = k if execution_valid[k, j] else int(last_seen[k-1, j])
            if seen < 0 or not np.isfinite(mark[j]) or mark[j] <= 0:
                pre_mark_violations += 1
                continue
            age = int((dates[k]-dates[seen]).astype(int))
            max_pre_mark_age = max(max_pre_mark_age, age)
            pre_mark_violations += int(age > 5)
        pre_nav = cash + float(np.nansum(units*mark))
        errors['pre_fee_nav'] = max(errors['pre_fee_nav'], abs(pre_nav-float(day.nav_open)))
        eligible = [item for item in queue if item['due'] <= k]
        queue = [item for item in queue if item['due'] > k]
        for item in eligible:
            pending = item
        missing = np.zeros(n, bool)
        if pending is not None:
            need = (units > 1e-10) | (pending['target'] > 0)
            missing = need & ~execution_valid[k]
            attempts.append(dict(k=k, date=str(dates[k]), instruction_id=pending['iid'],
                signal_idx=pending['signal'], due_idx=pending['due'], missing_count=int(missing.sum()),
                missing_tickers='|'.join(str(x) for x in np.asarray(panel['names'])[missing]),
                deferred=bool(missing.any())))
        fees = 0.
        if k in grouped:
            for row in grouped[k].itertuples():
                iid, j = int(row.instruction_id), int(row.j)
                if pending is None or iid != pending['iid'] or iid not in by_iid:
                    raise ValueError('ORDER_WITHOUT_ACTIVE_INSTRUCTION')
                if (int(row.signal_idx) != pending['signal'] or int(row.due_idx) != pending['due']
                        or k < pending['due'] or k <= pending['signal'] or row.reason != pending['reason']):
                    raise ValueError('ORDER_INSTRUCTION_OR_TIMING')
                if j < 0 or j >= n or (hasattr(row, 'ticker') and str(row.ticker) != str(panel['names'][j])):
                    raise ValueError('ORDER_INSTRUMENT')
                if str(row.date) != str(dates[k]) or (hasattr(row, 'execution_date') and str(row.execution_date) != str(dates[k])):
                    raise ValueError('ORDER_EXECUTION_DATE')
                quantity, price, notional, cost = map(float, (row.quantity, row.price, row.notional, row.cost))
                if not np.isfinite([quantity, price, notional, cost]).all() or min(quantity, price, notional) <= 0 or cost < 0:
                    raise ValueError('INVALID_EXECUTED_AMOUNTS')
                errors['fee_formula'] = max(errors['fee_formula'], abs(cost-(ticket+impact*notional)))
                errors['notional_quantity'] = max(errors['notional_quantity'], abs(quantity*price-notional))
                execution_support_violations += int(not execution_valid[k, j])
                if execution_valid[k, j]:
                    errors['execution_price'] = max(errors['execution_price'], abs(price-execution_raw[k, j]))
                if row.side == 'BUY':
                    units[j] += quantity
                    cash -= notional+cost
                elif row.side == 'SELL':
                    units[j] -= quantity
                    cash += notional-cost
                else:
                    raise ValueError('INVALID_EXECUTED_SIDE')
                fees += cost
        after_at_same_mark = cash+float(np.nansum(units*mark))
        errors['self_financing'] = max(errors['self_financing'], abs(after_at_same_mark+fees-pre_nav))
        if pending is not None and not missing.any():
            pending = None
        busy_by_k[k] = pending is not None or bool(queue)
        close_value = float(np.nansum(units*marks[k]))
        errors['close_nav'] = max(errors['close_nav'], abs(cash+close_value-float(day.nav_close)))
        errors['cash'] = max(errors['cash'], abs(cash-float(day.cash)))
        errors['gross'] = max(errors['gross'], abs(close_value/(cash+close_value)-float(day.gross)))
        negative_cash += int(cash < -1e-8)
        negative_units += int(np.any(units < -1e-8))
        queue.extend(by_signal.get(k, []))
    tolerance = max(1e-6, float(daily.nav_close.max())*1e-10)
    monetary_pass = all(value <= tolerance for key, value in errors.items() if key != 'gross')
    summary = dict(**{f'maximum_{key}_error': value for key, value in errors.items()},
        reconciliation_tolerance=tolerance, negative_cash_closes=negative_cash,
        negative_unit_closes=negative_units, execution_quote_support_violations=execution_support_violations,
        pre_fee_held_mark_violations=pre_mark_violations, max_pre_fee_held_mark_age_calendar_days=max_pre_mark_age,
        deferred_attempt_sessions=sum(int(row['deferred']) for row in attempts),
        ending_pending_instruction_id=None if pending is None else pending['iid'],
        fee_and_execution_pass=bool(monetary_pass and errors['gross'] <= 1e-10 and
            not negative_cash and not negative_units and not execution_support_violations and not pre_mark_violations),
        new_financial_policy_replay=False)
    columns = ['k','date','instruction_id','signal_idx','due_idx','missing_count','missing_tickers','deferred']
    return summary, pd.DataFrame(attempts, columns=columns), busy_by_k


def audit_monthly_resets(trace, instructions, orders, daily, targets, monthly, busy_by_k, attempts, ready_idx):
    """Reconcile scheduled cash decisions with immutable instructions and buys."""
    instructions_by_signal = {int(k): frame for k, frame in instructions.groupby('signal_idx')}
    trace_flags = trace.monthly_cash_reset.map(_bool)
    expected_flags = pd.Series(False, index=trace.index)
    recorded_gross = daily.set_index('k').gross
    records, scheduled_rows, scheduled_cash_busy = [], 0, 0
    for row in trace.itertuples():
        k = int(row.k)
        if bool(row.scheduled) != bool(monthly[k]) and not bool(row.initial):
            raise ValueError('TRACE_MONTHLY_CALENDAR')
        ready = k >= ready_idx and not row.initial
        if not row.initial:
            if k not in recorded_gross or not np.isfinite(row.gross) or abs(float(row.gross)-float(recorded_gross.loc[k])) > 1e-10:
                raise ValueError('TRACE_ACCOUNT_STATE_MISMATCH')
            if _bool(row.model_ready_all) != ready:
                raise ValueError('MODEL_READINESS_TRACE_MISMATCH')
        if k >= ready_idx and not row.initial and ready and bool(busy_by_k.get(k, False)):
            if row.status != 'BUSY' or len(instructions_by_signal.get(k, [])):
                raise ValueError('BUSY_STATE_INSTRUCTION_REPLACED')
        if row.initial or not row.scheduled or not ready:
            continue
        scheduled_rows += 1
        is_cash = float(row.gross) <= 1e-8
        if bool(busy_by_k.get(k, False)):
            scheduled_cash_busy += int(is_cash)
            continue
        emitted = instructions_by_signal.get(k, pd.DataFrame())
        if (row.status != 'MONTHLY_BASELINE_RESET' or row.action != 'SCHEDULED' or len(emitted) != 1):
            raise ValueError('MONTHLY_RESET_CONTRACT: idle scheduled account did not reset')
        inst = emitted.iloc[0]
        target, raw = np.asarray(_json(inst.target_weights),float), np.asarray(_json(inst.raw_weights),float)
        meta = _json(inst.meta)
        if (_bool(inst.force) or inst.reason != 'SCHEDULED' or int(inst.due_idx) != k+1
                or not np.array_equal(target, targets[k]) or not np.array_equal(raw, targets[k])
                or _bool(meta.get('monthly_cash_reset',False)) != is_cash
                or meta.get('status') != 'MONTHLY_BASELINE_RESET'):
            raise ValueError('MONTHLY_RESET_CONTRACT: target, force, timing or metadata')
        expected_flags.loc[row.Index] = is_cash
        if not is_cash:
            continue
        iid = int(inst.instruction_id)
        fills = orders.loc[orders.instruction_id == iid]
        buys = fills.loc[(fills.side == 'BUY') & (fills.notional > 0)]
        if len(fills) and (int(fills.execution_idx.min()) <= k or int(fills.execution_idx.min()) < int(inst.due_idx)):
            raise ValueError('RESET_EXECUTION_TIMING')
        trials = attempts.loc[attempts.instruction_id == iid]
        first_buy = None if buys.empty else int(buys.execution_idx.min())
        last_attempt = None if trials.empty else int(trials.k.max())
        still_pending = bool(last_attempt is not None and
                             trials.loc[trials.k == last_attempt, 'missing_count'].iloc[-1] > 0)
        future_due = int(inst.due_idx) > int(daily.k.iloc[-1])
        actionable = bool(np.max(target, initial=0.) >= .03)
        if first_buy is None and actionable and not still_pending and not future_due:
            raise ValueError('MONTHLY_RESET_CONTRACT: actionable cash reset had no buy or unresolved quote deferral')
        records.append(dict(signal_idx=k, signal_date=str(row.date), instruction_id=iid,
            due_idx=int(inst.due_idx), target_gross=float(target.sum()), target_positions=int((target>0).sum()),
            actual_orders=len(fills), actual_buy_orders=len(buys),
            first_buy_idx=first_buy, first_buy_delay_sessions=None if first_buy is None else first_buy-k,
            first_buy_date=None if first_buy is None else str(daily.loc[daily.k == first_buy,'date'].iloc[0]),
            last_execution_idx=None if fills.empty else int(fills.execution_idx.max()),
            deferred_attempt_sessions=int((trials.missing_count>0).sum()),
            still_pending_at_end=still_pending, future_due_at_end=future_due,
            no_buy_target_below_band=first_buy is None and not actionable,
            target_and_trace_valid=True))
    if not trace_flags.equals(expected_flags):
        raise ValueError('MONTHLY_CASH_RESET_TRACE_FLAG_MISMATCH')
    flagged_instructions = {int(row.instruction_id) for row in instructions.itertuples()
                            if _bool(_json(row.meta).get('monthly_cash_reset',False))}
    if flagged_instructions != {row['instruction_id'] for row in records}:
        raise ValueError('MONTHLY_CASH_RESET_INSTRUCTION_FLAG_MISMATCH')
    spells = []
    for spell in audit.cash_spells(daily):
        row = dict(spell)
        ending_buy_idx = None if spell['right_censored'] else int(spell['end_idx'])+1
        ending = orders.loc[(orders.execution_idx == ending_buy_idx) & (orders.side == 'BUY') & (orders.notional > 0)]
        if not spell['right_censored'] and ending.empty:
            raise ValueError('CASH_SPELL_ENDED_WITHOUT_RECORDED_BUY')
        ids = sorted(set(ending.instruction_id.astype(int))) if len(ending) else []
        row.update(ending_instruction_ids='|'.join(map(str,ids)),
            ending_instruction_reason='|'.join(sorted(set(ending.reason))) if len(ending) else None,
            ended_by_monthly_cash_reset=bool(set(ids) & flagged_instructions),
            reset_signals_within_spell=sum(spell['start_idx'] <= r['signal_idx'] <= spell['end_idx'] for r in records),
            return_to_invested_verified=not ending.empty if not spell['right_censored'] else None)
        spells.append(row)
    summary = dict(mechanical_contract_pass=True, scheduled_ready_rows=scheduled_rows,
        scheduled_cash_busy_rows=scheduled_cash_busy, cash_reset_instructions=len(records),
        cash_reset_instructions_with_any_order=sum(r['actual_orders']>0 for r in records),
        cash_reset_instructions_with_buys=sum(r['actual_buy_orders']>0 for r in records),
        cash_reset_buy_orders=sum(r['actual_buy_orders'] for r in records),
        cash_reset_orders=sum(r['actual_orders'] for r in records),
        cash_reset_deferred_attempt_sessions=sum(r['deferred_attempt_sessions'] for r in records),
        cash_reset_unfilled_instructions=sum(r['actual_orders']==0 for r in records),
        cash_reset_pending_at_end=sum(r['still_pending_at_end'] for r in records),
        cash_spells_ended_by_reset=sum(r['ended_by_monthly_cash_reset'] for r in spells),
        universal21_session_cap_asserted=False)
    columns = ['signal_idx','signal_date','instruction_id','due_idx','target_gross','target_positions',
        'actual_orders','actual_buy_orders','first_buy_idx','first_buy_delay_sessions','first_buy_date',
        'last_execution_idx','deferred_attempt_sessions','still_pending_at_end','future_due_at_end',
        'no_buy_target_below_band','target_and_trace_valid']
    return summary, pd.DataFrame(records,columns=columns), pd.DataFrame(spells)


def _source_freezes(root, hashes):
    freezes = {}
    for study, filename in [('olc113','EXPERIMENT_FREEZE.json'),('olc112','EXPERIMENT_FREEZE.json'),
                            ('olc111','EXPERIMENT_FREEZE.json'),('olc111','BANK_FREEZE.json')]:
        directory = root.parent/study
        path = directory/'docs'/filename
        record = json.loads(path.read_text())
        hashes[str(path.relative_to(root.parent))] = audit._sha256(path)
        for section in ('code_hashes','input_hashes'):
            for relative, expected in record[section].items():
                source = (directory/relative).resolve()
                if not source.is_file() or audit._sha256(source) != expected:
                    raise ValueError('FROZEN_SOURCE_HASH_MISMATCH:'+str(source))
                hashes[str(source.relative_to(root.parent))] = expected
        protocol = directory/'docs/DESIGN_AND_PROTOCOL.md'
        if audit._sha256(protocol) != record['protocol_sha256']:
            raise ValueError('FROZEN_PROTOCOL_MISMATCH:'+study)
        hashes[str(protocol.relative_to(root.parent))] = record['protocol_sha256']
        freezes[f'{study}/{filename}'] = record
    current = freezes['olc113/EXPERIMENT_FREEZE.json']
    if (current['arms'] != list(ARMS) or current['scenarios'] != list(SCENARIOS)
            or current['planned_paths'] != 12):
        raise ValueError('FREEZE_MATRIX_MISMATCH')
    return current


def _verify_receipt(folder, native, hashes, workspace):
    expected_arm, expected_scenario = folder.name.split('__')
    if (native.get('path_id') != folder.name or native.get('arm') != expected_arm
            or native.get('scenario') != expected_scenario):
        raise ValueError('PATH_RECEIPT_EXPECTED_PATH')
    receipt_path = folder/'PATH_RECEIPT.json'
    receipt = json.loads(receipt_path.read_text())
    digest = audit._sha256(receipt_path)
    if native.get('path_receipt_sha256') != digest or receipt['path_id'] != native['path_id']:
        raise ValueError('PATH_RECEIPT_IDENTITY')
    payload = {key:value for key,value in native.items() if key != 'path_receipt_sha256'}
    canonical = json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if hashlib.sha256(canonical).hexdigest() != receipt['metrics_payload_sha256']:
        raise ValueError('PATH_RECEIPT_METRICS_HASH')
    required = set(ARTIFACTS)
    if native['arm'] == 'MEAN_RESET':
        required.add('MEAN_BASE_REPLICATION.json')
    if set(receipt['artifacts']) != required:
        raise ValueError('PATH_RECEIPT_ARTIFACT_SET')
    for name, expected in receipt['artifacts'].items():
        path = folder/name
        if audit._sha256(path) != expected:
            raise ValueError('PATH_RECEIPT_ARTIFACT_HASH:'+name)
        hashes[str(path.relative_to(workspace))] = expected
    hashes[str(receipt_path.relative_to(workspace))] = digest


def _forecast_hashes(trace, saved_fits, *, expected_arm, expected_cutoffs, cboe):
    count = 0
    for row in trace.itertuples():
        if int(row.fit_cutoff_idx) != int(expected_cutoffs[int(row.k)]):
            raise ValueError('TRACE_MODEL_MONTHLY_CUTOFF')
        if row.arm != expected_arm or row.underlying_arm != expected_arm.removesuffix('_RESET'):
            raise ValueError('TRACE_MODEL_UNDERLYING_ARM')
        stored = saved_fits[int(row.fit_cutoff_idx)]
        expected_ready = not row.initial and all(stored['heads'][head] is not None for head in audit.ACTIONS)
        if _bool(row.model_ready_all) != expected_ready:
            raise ValueError('MODEL_READINESS_TRACE_MISMATCH')
        source_available = bool(cboe['available'][int(row.k)])
        if _bool(row.source_available) != source_available:
            raise ValueError('TRACE_MODEL_SOURCE_AVAILABILITY')
        source_ok = bool(source_available and np.isfinite(cboe['legacy'][int(row.k)]).all()
                         and np.isfinite(cboe['term'][int(row.k)]).all())
        intended = expected_arm.removesuffix('_RESET')
        intended_model = 'PRICE' if intended in ('VIX','TERM') and not source_ok else intended
        observed_fallback = False
        for head in audit.ACTIONS:
            prefix = head.lower()
            digest = getattr(row, prefix+'_model_sha256')
            if pd.isna(digest):
                continue
            arm = getattr(row, prefix+'_model_arm')
            if arm != intended_model:
                raise ValueError('TRACE_MODEL_ARM_OR_FALLBACK')
            observed_fallback |= arm != intended
            record = stored['heads'][head]
            if record is None or record['hashes'][arm] != digest:
                raise ValueError('TRACE_SAVED_MODEL_HASH_MISMATCH')
            if record['meta']['max_terminal_idx'] >= stored['cutoff'] or stored['cutoff'] > row.k:
                raise ValueError('TRACE_MODEL_MATURITY')
            count += 1
        if _bool(row.fallback_price) != observed_fallback:
            raise ValueError('TRACE_MODEL_FALLBACK_FLAG')
    return dict(model_predictions_with_verified_hash=count, pass_all=True)


def _trace_account_states(trace, daily):
    indexed = daily.set_index('k')
    errors = {key:0. for key in ('nav','cash','gross','positions')}
    first_idx = int(daily.k.iloc[0])-1
    initial_count = 0
    for row in trace.itertuples():
        if _bool(row.initial):
            initial_count += 1
            if int(row.k) != first_idx:
                raise ValueError('INITIAL_TRACE_DATE')
            expected = dict(nav=10000.,cash=10000.,gross=0.,positions=0.)
        else:
            if int(row.k) not in indexed.index:
                raise ValueError('TRACE_ACCOUNT_STATE_CALENDAR')
            day = indexed.loc[int(row.k)]
            expected = dict(nav=day.nav_close,cash=day.cash,gross=day.gross,positions=day.positions)
        for key,value in expected.items():
            actual = float(getattr(row,key))
            if not np.isfinite(actual):
                raise ValueError('NONFINITE_TRACE_ACCOUNT_STATE')
            errors[key] = max(errors[key],abs(actual-float(value)))
    tolerance = max(1e-6,float(daily.nav_close.max())*1e-10)
    passed = (initial_count == 1 and errors['nav'] <= tolerance and errors['cash'] <= tolerance
              and errors['gross'] <= 1e-10 and errors['positions'] == 0)
    if not passed:
        raise ValueError('TRACE_ACCOUNT_STATE_MISMATCH')
    return dict(pass_all=True,maximum_absolute_errors=errors,initial_rows=initial_count)


def _annual_rows(path_id, daily):
    years = pd.to_datetime(daily.date).dt.year
    rows = []
    for year in sorted(years.unique()):
        indices = daily.loc[years == year,'k']
        metrics = audit.performance_window(daily,start_idx=int(indices.min()),end_idx=int(indices.max()))
        rows.append(dict(path_id=path_id,year=int(year),annual_return=metrics['cumulative'],
            log_growth=metrics['log_growth'],sampled_maxdd_in_year=metrics['maxdd_sampled'],
            initial_nav=metrics['initial_nav'],end_equity=metrics['end_equity'],
            start_date=metrics['start_date'],end_date=metrics['end_date']))
    return rows


def run_audit(root=ROOT):
    root = Path(root).resolve()
    results, prior, rotation = root/'results', root.parent/'olc111/results', root.parent/'olc112/results'
    hashes = {}
    freeze = _source_freezes(root, hashes)
    def read_json(path):
        hashes[str(path.resolve().relative_to(root.parent))] = audit._sha256(path)
        raw = path.read_bytes()
        return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)
    def read_csv(path):
        hashes[str(path.resolve().relative_to(root.parent))] = audit._sha256(path)
        return audit._read_csv(path)
    readiness = read_json(results/'FIT_READINESS.json')
    if readiness != read_json(prior/'FIT_READINESS.json'):
        raise ValueError('READINESS_CHANGED_FROM_OLC111')
    manifest = read_json(results/'RUN_MANIFEST.json')
    scores, prior_scores = read_csv(results/'SCORES.csv'), read_csv(prior/'SCORES.csv')
    expected = [f'{arm}__{scenario}' for arm in ARMS for scenario in SCENARIOS]
    control_ids = [f'{arm}__{scenario}' for arm in CONTROLS for scenario in SCENARIOS]
    if (manifest['completed_paths'] != 12 or manifest['planned_paths'] != 12
            or set(manifest['completed_path_ids']) != set(expected) or len(scores) != 12
            or set(scores.path_id) != set(expected) or manifest['new_model_fits'] != 0
            or manifest['primary_arm'] != 'PRICE_RESET'):
        raise ValueError('INCOMPLETE_OR_REFITTED_RESET_MATRIX')
    if manifest['freeze_sha256'] != audit._sha256(root/'docs/EXPERIMENT_FREEZE.json'):
        raise ValueError('MANIFEST_FREEZE_HASH')
    if manifest['code_hashes'] != freeze['code_hashes'] or manifest['input_hashes'] != freeze['input_hashes']:
        raise ValueError('MANIFEST_FROZEN_INPUTS_CHANGED')
    if pd.Timestamp(manifest['start_utc']) < pd.Timestamp(freeze['created_utc']):
        raise ValueError('FINANCIAL_RUN_PRECEDES_FREEZE')
    panel_path = root.parent/'olc110/source/data/XETRA_EUR_ETF.npz'
    hashes[str(panel_path.relative_to(root.parent))] = audit._sha256(panel_path)
    with np.load(panel_path,allow_pickle=False) as source:
        panel = {key:source[key] for key in ('dates','names','C','O','observed','open_observed') if key in source.files}
    dates = np.asarray(panel['dates'],dtype='datetime64[D]')
    monthly = np.r_[pd.DatetimeIndex(dates[:-1]).to_period('M') != pd.DatetimeIndex(dates[1:]).to_period('M'),False]
    selection_path = root.parent/'olc111/data/CAUSAL_SELECTIONS.npz'
    hashes[str(selection_path.relative_to(root.parent))] = audit._sha256(selection_path)
    with np.load(selection_path,allow_pickle=False) as source:
        targets = source['targets']
    cboe_path = root.parent/'olc111/data/CBOE_ALIGNED.npz'
    hashes[str(cboe_path.relative_to(root.parent))] = audit._sha256(cboe_path)
    with np.load(cboe_path,allow_pickle=False) as source:
        cboe = {key:source[key] for key in ('available','legacy','term')}
    ready, post_idx = int(readiness['all_heads_first_ready_idx']),int(readiness['postwarmup_start_idx'])
    if (post_idx != ready+1 or str(dates[ready]) != readiness['all_heads_first_ready_date']
            or str(dates[post_idx]) != readiness['postwarmup_start_date']):
        raise ValueError('READINESS_CALENDAR_MISMATCH')
    begin, end = int(scores.start_idx.iloc[0]),int(scores.end_idx.iloc[0])
    if (scores.start_idx.nunique()!=1 or scores.end_idx.nunique()!=1 or end!=len(dates)-1
            or str(dates[begin])!='2020-03-02' or str(dates[end])!='2026-10-30'):
        raise ValueError('STUDY_WINDOW_CHANGED')
    month_keys = pd.DatetimeIndex(dates).to_period('M')
    first_in_month = np.r_[True,month_keys[1:] != month_keys[:-1]]
    expected_cutoffs = np.maximum(np.maximum.accumulate(np.where(first_in_month,np.arange(len(dates)),0)),begin-1)
    saved_fits = {}
    for cutoff in readiness['fitted_calendar_cutoffs']:
        path = prior/'FITS'/f'FIT_{int(cutoff):06d}.json.gz'
        saved_fits[int(cutoff)] = read_json(path)
        if saved_fits[int(cutoff)]['cutoff'] != int(cutoff):
            raise ValueError('SAVED_FIT_CUTOFF')
        if str(path.relative_to(root.parent)) not in hashes:
            raise ValueError('FIT_SOURCE_HASH_MISSING')
    if len(saved_fits) != 81:
        raise ValueError('SAVED_FIT_MATRIX_COUNT')
    paths = {}
    for path_id in expected+control_ids:
        folder = (results if path_id in expected else prior)/path_id
        loaded = {key:read_csv(folder/name) for key,name in (
            ('daily','DAILY.csv.gz'),('orders','ORDERS.csv.gz'),('trace','POLICY_TRACE.csv.gz'),
            ('instructions','INSTRUCTIONS.csv.gz'))}
        loaded['native'] = read_json(folder/'METRICS.json')
        if path_id in expected:
            _verify_receipt(folder,loaded['native'],hashes,root.parent)
        audit.validate_result_calendar(loaded['daily'],dates,start_idx=begin,end_idx=end)
        trace = loaded['trace']
        if not np.array_equal(trace.k.to_numpy(int),np.arange(begin-1,end)) or not np.array_equal(
                pd.to_datetime(trace.date).to_numpy(dtype='datetime64[D]'),dates[begin-1:end]):
            raise ValueError('INCOMPLETE_TRACE_CALENDAR')
        paths[path_id] = loaded
    predecessors = {}
    for path_id in expected:
        predecessor = path_id.replace('_RESET__','_ROTATION__')
        daily = read_csv(rotation/predecessor/'DAILY.csv.gz')
        audit.validate_result_calendar(daily,dates,start_idx=begin,end_idx=end)
        predecessors[path_id] = dict(path_id=predecessor,daily=daily,native=read_json(rotation/predecessor/'METRICS.json'))
    diagnostics, compact, cash_rows, action_rows, violations, annual_rows = {},[],[],[],[],[]
    reset_rows, execution_attempt_rows, reset_summaries, mean_parity = [],[],{},{}
    comparison_rows = []
    for path_id in expected+control_ids:
        arm, scenario = path_id.split('__')
        is_control, loaded = arm in CONTROLS,paths[path_id]
        daily,orders,trace,instructions = (loaded[key] for key in ('daily','orders','trace','instructions'))
        whole,post = audit.performance_window(daily),audit.performance_window(daily,start_idx=post_idx)
        years = whole['days']/audit.YEAR_DAYS
        nav_at = daily.set_index('date').nav_open.loc[orders.date].to_numpy()
        whole.update(orders=len(orders),costs=float(orders.cost.sum()),instructions=len(instructions),
            trading_days=int(orders.date.nunique()),trading_days_per_year=float(orders.date.nunique()/years),
            two_sided_turnover_per_year=float((orders.notional.to_numpy()/nav_at).sum()/years))
        selected_scores = prior_scores if is_control else scores
        recorded = selected_scores.loc[selected_scores.path_id == path_id].iloc[0].to_dict()
        parity = dict(metrics_whole=audit.metric_parity(whole,loaded['native']),
            metrics_post=audit.metric_parity(post,loaded['native'],prefix='post_'),
            scores_whole=audit.metric_parity(whole,recorded),scores_post=audit.metric_parity(post,recorded,prefix='post_'))
        base = paths[f'BASE__{scenario}']['daily']
        warmup = None if is_control else audit.warmup_replication(base,daily,ready_idx=ready)
        actions,event_frame = audit.intervention_summary(trace,orders,last_idx=end)
        held,issue_frame = audit.held_mark_audit(daily,orders,panel)
        execution,attempts,busy = audit_execution_ledger(daily,orders,instructions,panel,scenario)
        if execution['deferred_attempt_sessions'] != int(loaded['native']['deferred_sessions']):
            raise ValueError('NATIVE_DEFERRED_SESSION_COUNT:'+path_id)
        spells = comparison.cash_spell_context(audit.cash_spells(daily),daily,base)
        comparisons = {}
        reset = None
        if not is_control:
            reset,reset_frame,reset_spells = audit_monthly_resets(trace,instructions,orders,daily,
                targets,monthly,busy,attempts,ready)
            reset_summaries[path_id] = reset
            for key,native_key in [('cash_reset_instructions','monthly_cash_reset_instructions'),
                ('cash_reset_instructions_with_any_order','monthly_cash_reset_realized_instructions'),
                ('cash_reset_unfilled_instructions','monthly_cash_reset_unfilled_instructions'),
                ('cash_reset_orders','monthly_cash_reset_orders')]:
                if reset[key] != int(loaded['native'][native_key]):
                    raise ValueError('NATIVE_RESET_TELEMETRY:'+path_id+':'+key)
            reset_frame.insert(0,'path_id',path_id)
            reset_rows.append(reset_frame)
            extra = {int(row['start_idx']):row for row in reset_spells.to_dict('records')}
            spells = [dict(spell,**{k:v for k,v in extra[int(spell['start_idx'])].items() if k not in spell}) for spell in spells]
            for reference in CONTROLS:
                comparisons[f'OLC111_{reference}'] = dict(
                    whole=comparison.compare_accounts(daily,paths[f'{reference}__{scenario}']['daily']),
                    post=comparison.compare_accounts(daily,paths[f'{reference}__{scenario}']['daily'],start_idx=post_idx))
            predecessor = predecessors[path_id]
            comparisons['OLC112_'+arm.replace('_RESET','_ROTATION')] = dict(
                whole=comparison.compare_accounts(daily,predecessor['daily']),
                post=comparison.compare_accounts(daily,predecessor['daily'],start_idx=post_idx))
            for reference,windows in comparisons.items():
                comparison_rows.extend(dict(path_id=path_id,reference=reference,window=window,**value)
                                       for window,value in windows.items())
        if arm == 'MEAN_RESET':
            base_loaded = paths[f'BASE__{scenario}']
            mean_parity[scenario] = dict(
                daily_all_columns_exact=daily.equals(base_loaded['daily']),
                entire_order_ledger_exact=orders.equals(base_loaded['orders']),
                discretionary_orders=int(orders.reason.isin(audit.ACTIONS).sum()),
                daily_rows=len(daily),order_rows=len(orders))
        trace_account = _trace_account_states(trace,daily)
        forecast_provenance = None if is_control else _forecast_hashes(trace,saved_fits,
            expected_arm=arm,expected_cutoffs=expected_cutoffs,cboe=cboe)
        diagnostics[path_id] = dict(arm=arm,scenario=scenario,source_study='OLC111' if is_control else 'OLC113',
            whole=whole,post=post,metric_parity=parity,warmup_against_same_scenario_base=warmup,
            interventions=actions,held_marks=held,execution_ledger=execution,cash_spells=spells,
            longest_cash_spell_sessions=max((row['cash_sessions'] for row in spells),default=0),
            monthly_resets=reset,forecast_provenance=forecast_provenance,trace_account_reconciliation=trace_account,
            trace=audit.trace_diagnostics(trace,ready_idx=ready),comparisons=comparisons)
        compact.append(dict(path_id=path_id,arm=arm,scenario=scenario,source_study='OLC111' if is_control else 'OLC113',
            cagr=whole['cagr'],sampled_maxdd=whole['maxdd_sampled'],post_cagr=post['cagr'],
            post_sampled_maxdd=post['maxdd_sampled'],end_equity=whole['end_equity'],
            post_anchor_nav=post['initial_nav'],post_anchor_date=post['anchor_date'],
            mean_exposure=whole['mean_exposure'],post_mean_exposure=post['mean_exposure'],
            full_cash_days=whole['full_cash_days'],longest_cash_spell_sessions=diagnostics[path_id]['longest_cash_spell_sessions'],
            orders=len(orders),costs=whole['costs'],two_sided_turnover_per_year=whole['two_sided_turnover_per_year'],
            monthly_cash_reset_instructions=0 if reset is None else reset['cash_reset_instructions'],
            monthly_cash_reset_instructions_with_buys=0 if reset is None else reset['cash_reset_instructions_with_buys'],
            **{f'{head.lower()}_filled_instructions':actions[head]['realized_instructions'] for head in audit.ACTIONS},
            **{f'{head.lower()}_separated_completed21':actions[head]['separated_completed21_episodes'] for head in audit.ACTIONS},
            max_source_age_calendar_days=held['max_source_age_calendar_days'],
            max_nav_reconstruction_error=held['max_nav_reconstruction_error'],
            max_pre_fee_nav_reconstruction_error=execution['maximum_pre_fee_nav_error'],
            max_cash_reconstruction_error=held['max_cash_reconstruction_error'],
            valuation_support_pass=held['valuation_support_pass'],ledger_reconciliation_pass=held['ledger_reconciliation_pass'],
            fee_and_execution_pass=execution['fee_and_execution_pass'],
            whole_post_metric_parity=all(row['pass_all'] for row in parity.values()),
            exact_learned_warmup=None if warmup is None else warmup['exact_match']))
        for frame,destination in ((event_frame,action_rows),(issue_frame,violations),(attempts,execution_attempt_rows)):
            frame.insert(0,'path_id',path_id)
            destination.append(frame)
        cash_rows.extend(dict(path_id=path_id,**spell) for spell in spells)
        annual_rows.extend(_annual_rows(path_id,daily))
    criteria = {}
    for path_id in expected:
        arm,scenario = path_id.split('__')
        criteria[path_id] = material_criterion(diagnostics[path_id],diagnostics[f'BASE__{scenario}'])
    stress = {}
    for arm in ARMS:
        primary, doubled = criteria[f'{arm}__NEXT_CLOSE'],criteria[f'{arm}__DOUBLE_COST']
        stress[arm] = dict(material_next_close=primary['material_both_windows'],
            material_double_cost=doubled['material_both_windows'],
            positive_cagr_gain_both_windows_next_close=all(primary[w]['cagr_gain']>0 for w in ('whole','post')),
            positive_cagr_gain_both_windows_double_cost=all(doubled[w]['cagr_gain']>0 for w in ('whole','post')),
            gain_reverses_with_double_cost=any(primary[w]['cagr_gain']>0 and doubled[w]['cagr_gain']<=0 for w in ('whole','post')),
            next_close=primary,double_cost=doubled)
    primary_criterion = criteria['PRICE_RESET__NEXT_CLOSE']
    material_arms = [arm for arm in ARMS if criteria[f'{arm}__NEXT_CLOSE']['material_both_windows']]
    target30_arms = [arm for arm in ARMS if criteria[f'{arm}__NEXT_CLOSE']['target30_whole']]
    checks = dict(complete12_new_paths_and6_existing_controls=True,all12_rotation_predecessors_compared=True,
        unchanged_protocol_code_data_and81_saved_fit_files=True,all12_path_receipts_valid=True,
        identical_complete_daily_and_trace_calendars=True,
        whole_post_metric_parity=all(row['pass_all'] for path in diagnostics.values() for row in path['metric_parity'].values()),
        exact_warmup_all12_paths=all(diagnostics[path]['warmup_against_same_scenario_base']['exact_match'] for path in expected),
        mean_exact_base_daily_and_orders_all_scenarios=all(row['daily_all_columns_exact'] and row['entire_order_ledger_exact']
            and row['discretionary_orders']==0 for row in mean_parity.values()),
        account_reconstruction_all18_paths=all(path['held_marks']['ledger_reconciliation_pass'] for path in diagnostics.values()),
        held_quote_support_all18_paths=all(path['held_marks']['valuation_support_pass'] for path in diagnostics.values()),
        trace_account_state_reconciliation_all18_paths=all(path['trace_account_reconciliation']['pass_all'] for path in diagnostics.values()),
        fees_execution_prices_and_prefee_nav_all18_paths=all(path['execution_ledger']['fee_and_execution_pass'] for path in diagnostics.values()),
        monthly_cash_reset_contract_all12_paths=all(row['mechanical_contract_pass'] for row in reset_summaries.values()),
        saved_forecast_hashes_all12_paths=all(diagnostics[path]['forecast_provenance']['pass_all'] for path in expected))
    for path in (Path(__file__),root/'src/audit_plot.py',root/'tests/test_result_audit.py',
                 root.parent/'olc111/src/analyze_results.py',root.parent/'olc112/src/analyze_results.py'):
        hashes[str(path.relative_to(root.parent))] = audit._sha256(path)
    report = dict(study='OLC113',audit='independent_results_only_v1',readiness=readiness,checks=checks,
        primary_arm='PRICE_RESET',primary_material_criterion=primary_criterion,
        material_arms_primary_execution=material_arms,target30_arms_primary_execution=target30_arms,
        criteria=criteria,stress=stress,paths=diagnostics,mean_base_replication=mean_parity,
        monthly_reset_summaries=reset_summaries,source_sha256=hashes,
        audit_new_model_fits=0,audit_new_financial_policies=0,audit_new_financial_paths=0,
        performance_modified=False,adaptive_after_olc111=True,adaptive_after_olc112=True,pristine_holdout=False,
        discovered_predictive_alpha=False,validated_promotion=False,
        conclusion=dict(primary_meets_predeclared_material_criterion=primary_criterion['material_both_windows'],
            any_primary_execution_arm_meets_criterion=bool(material_arms),any_primary_execution_arm_reaches30=bool(target30_arms),
            economic_result_is_derived_from_audited_ledgers=True),
        limitations=['Adaptive mechanism ablation on repeatedly inspected history; no untouched holdout.',
            'Scheduled reentry repair does not change the failed OLC111 incremental-information forecast evidence.',
            'Concurrent BASE and predecessor comparisons describe recorded accounts, not prospective or isolated causal alpha.',
            'Repeated policy continuation still differs from a one-intervention21-session bank.',
            'Calendar months and quote deferrals prohibit a universal21-session cash-spell cap.',
            'Separated completed intervention counts establish temporal support only.',
            'Current catalog, survivorship, adjustment vintage and next-Open availability limitations remain.'])
    results.mkdir(exist_ok=True)
    (results/'INDEPENDENT_DIAGNOSTICS.json').write_text(json.dumps(audit._jsonable(report),indent=2,allow_nan=False)+'\n')
    pd.DataFrame(compact).to_csv(results/'INDEPENDENT_SCORES.csv',index=False)
    pd.DataFrame(cash_rows).to_csv(results/'INDEPENDENT_CASH_SPELLS.csv',index=False)
    pd.DataFrame(annual_rows).to_csv(results/'INDEPENDENT_ANNUAL_RETURNS.csv',index=False)
    pd.DataFrame(comparison_rows).to_csv(results/'INDEPENDENT_COMPARISONS.csv',index=False)
    pd.DataFrame([dict(path_id=path_id,window=window,**record[window],
        material_both_windows=record['material_both_windows'],target30_whole=record['target30_whole'],target30_post=record['target30_post'])
        for path_id,record in criteria.items() for window in ('whole','post')]).to_csv(results/'INDEPENDENT_CRITERIA.csv',index=False)
    for frames,name in [(action_rows,'INDEPENDENT_INTERVENTIONS.csv'),(reset_rows,'INDEPENDENT_MONTHLY_CASH_RESETS.csv'),
                         (execution_attempt_rows,'INDEPENDENT_EXECUTION_ATTEMPTS.csv')]:
        nonempty = [frame for frame in frames if len(frame)]
        combined = pd.concat(nonempty,ignore_index=True) if nonempty else frames[0]
        combined.to_csv(results/name,index=False)
    pd.concat(violations,ignore_index=True).to_csv(results/'INDEPENDENT_HELD_MARK_VIOLATIONS.csv.gz',index=False,
        compression={'method':'gzip','mtime':0})
    annual_comparisons = []
    for path_id in expected:
        arm,scenario=path_id.split('__')
        own=pd.DataFrame(_annual_rows(path_id,paths[path_id]['daily'])).set_index('year')
        references={'BASE':paths[f'BASE__{scenario}']['daily'],
                    'STATIC_75':paths[f'STATIC_75__{scenario}']['daily'],
                    arm.replace('_RESET','_ROTATION'):predecessors[path_id]['daily']}
        for reference,ref_daily in references.items():
            ref=pd.DataFrame(_annual_rows(reference,ref_daily)).set_index('year')
            annual_comparisons.extend(dict(path_id=path_id,reference=reference,year=int(year),
                candidate_annual_return=float(own.loc[year,'annual_return']),reference_annual_return=float(ref.loc[year,'annual_return']),
                simple_return_difference=float(own.loc[year,'annual_return']-ref.loc[year,'annual_return']),
                log_growth_difference=float(own.loc[year,'log_growth']-ref.loc[year,'log_growth'])) for year in own.index)
    pd.DataFrame(annual_comparisons).to_csv(results/'INDEPENDENT_ANNUAL_COMPARISONS.csv',index=False)
    plotting=_module('olc113_audit_plot',root/'src/audit_plot.py')
    plotting.plot_primary(paths,readiness,results/'INDEPENDENT_PRIMARY_POSTWARMUP.png',postwarmup=True)
    plotting.plot_primary(paths,readiness,results/'INDEPENDENT_PRIMARY_FULL.png',postwarmup=False)
    _write_notes(root,report,pd.DataFrame(annual_comparisons))
    (results/'INDEPENDENT_SOURCE_MANIFEST.json').write_text(json.dumps(dict(
        audit='OLC113_results_only',source_files=len(hashes),source_sha256=hashes,
        audit_new_model_fits=0,audit_new_financial_policies=0,audit_new_financial_paths=0),indent=2)+'\n')
    return report


def _write_notes(root,report,annual):
    paths=report['paths']
    p=paths['PRICE_RESET__NEXT_CLOSE'];b=paths['BASE__NEXT_CLOSE']
    primary=report['primary_material_criterion']
    verdict='soddisfa' if primary['material_both_windows'] else 'non soddisfa'
    lines=['# OLC113 — lettura indipendente dei risultati','',
        f"**PRICE_RESET {verdict} il criterio prefissato di miglioramento materiale.** "
        f"Il CAGR completo è {p['whole']['cagr']:.2%} contro {b['whole']['cagr']:.2%} di BASE "
        f"({100*primary['whole']['cagr_gain']:+.2f} punti percentuali); il MaxDD campionato è "
        f"{p['whole']['maxdd_sampled']:.2%} contro {b['whole']['maxdd_sampled']:.2%}. "
        f"Nel periodo comune il differenziale di CAGR è {100*primary['post']['cagr_gain']:+.2f} punti. "
        'La soglia economica richiede almeno +3 punti di CAGR e MaxDD non peggiore in entrambe le finestre; il 30% resta un obiettivo separato.','',
        '## Conti nella convenzione principale','',
        '| Conto | CAGR completo | MaxDD completo | CAGR comune | MaxDD comune | Giorni cash | Reset cash con acquisti | Costi EUR |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for arm in CONTROLS+ARMS:
        r=paths[f'{arm}__NEXT_CLOSE'];reset=r['monthly_resets']
        lines.append(f"| {arm} | {r['whole']['cagr']:.2%} | {r['whole']['maxdd_sampled']:.2%} | {r['post']['cagr']:.2%} | "
            f"{r['post']['maxdd_sampled']:.2%} | {r['whole']['full_cash_days']} | {0 if reset is None else reset['cash_reset_instructions_with_buys']} | {r['whole']['costs']:.2f} |")
    lines += ['',f"Periodo completo: {p['whole']['start_date']}–{p['whole']['end_date']}; capitale iniziale EUR10.000. "
        f"Periodo comune: {p['post']['start_date']}–{p['post']['end_date']}, ancorato per ciascun conto alla sua chiusura effettiva del {p['post']['anchor_date']}.",'',
        '## Confronti e criterio materiale','',
        '| Conto principale | Delta CAGR vs BASE, completo | Delta CAGR vs BASE, comune | Delta MaxDD completo | Delta MaxDD comune | Criterio in entrambe | CAGR completo >=30% |',
        '|---|---:|---:|---:|---:|---|---|']
    for arm in ARMS:
        c=report['criteria'][f'{arm}__NEXT_CLOSE']
        lines.append(f"| {arm} | {100*c['whole']['cagr_gain']:+.3f} pp | {100*c['post']['cagr_gain']:+.3f} pp | "
            f"{100*c['whole']['sampled_maxdd_change']:+.4f} pp | {100*c['post']['sampled_maxdd_change']:+.4f} pp | "
            f"{'Sì' if c['material_both_windows'] else 'No'} | {'Sì' if c['target30_whole'] else 'No'} |")
    lines += ['', 'Un delta MaxDD positivo indica una perdita massima meno profonda. Il nome primario resta PRICE_RESET; VIX_RESET e TERM_RESET sono secondari.', '',
        '## Riparazione del rientro','',
        '| Conto | Reset cash emessi | Reset con acquisti | Tentativi differiti per quote | Spell cash massimo | Spell chiusi dal reset |',
        '|---|---:|---:|---:|---:|---:|']
    for arm in ARMS:
        path=paths[f'{arm}__NEXT_CLOSE'];r=path['monthly_resets']
        lines.append(f"| {arm} | {r['cash_reset_instructions']} | {r['cash_reset_instructions_with_buys']} | "
            f"{r['cash_reset_deferred_attempt_sessions']} | {path['longest_cash_spell_sessions']} | {r['cash_spells_ended_by_reset']} |")
    lines += ['', 'Il controllo verifica i flag del trace, il target originale, force=False, il segnale mensile, la successiva eleggibilità di esecuzione, gli acquisti effettivi e la fine dello spell cash. '
        'Uno spell non è respinto perché supera 21 sedute: contano il calendario mensile effettivo e le eventuali istruzioni in attesa/quote mancanti. '
        'Il cambio ripristina la continuazione mensile anche dal cash; non rende tutta la policy ripetuta uguale alla banca di interventi singoli.','',
        '## Effetto rispetto a OLC112','',
        '| Conto | Delta CAGR completo | Delta CAGR comune | Delta MaxDD completo | Cash completo, nuovo / precedente |',
        '|---|---:|---:|---:|---:|']
    for arm in ARMS:
        path=paths[f'{arm}__NEXT_CLOSE'];ref='OLC112_'+arm.replace('_RESET','_ROTATION');r=path['comparisons'][ref]
        old_cash=path['whole']['full_cash_days']-r['whole']['full_cash_days_difference']
        lines.append(f"| {arm} | {100*r['whole']['cagr_difference']:+.2f} pp | {100*r['post']['cagr_difference']:+.2f} pp | "
            f"{100*r['whole']['sampled_maxdd_difference']:+.3f} pp | {path['whole']['full_cash_days']} / {old_cash} |")
    lines += ['', '## Sensibilità ai costi ed esecuzione','',
        '| Conto | Scenario | CAGR | MaxDD | CAGR comune | MaxDD comune | Criterio entrambe |',
        '|---|---|---:|---:|---:|---:|---|']
    for arm in ARMS:
        for scenario in SCENARIOS:
            r=paths[f'{arm}__{scenario}'];c=report['criteria'][f'{arm}__{scenario}']
            lines.append(f"| {arm} | {scenario} | {r['whole']['cagr']:.2%} | {r['whole']['maxdd_sampled']:.2%} | "
                f"{r['post']['cagr']:.2%} | {r['post']['maxdd_sampled']:.2%} | {'Sì' if c['material_both_windows'] else 'No'} |")
    lines += ['', 'Il ritorno alla convenzione Open è una sensibilità con il limite noto di disponibilità derivata dal volume giornaliero completato. '
        'Non dimostra eseguibilità reale all’apertura. Le tabelle JSON includono esplicitamente eventuali inversioni del guadagno con costi doppi.','',
        '## Anni e interventi','',
        '| Anno | PRICE_RESET | BASE | Differenza semplice | Incremento log |',
        '|---|---:|---:|---:|---:|']
    selected=annual.loc[(annual.path_id=='PRICE_RESET__NEXT_CLOSE')&(annual.reference=='BASE')]
    for row in selected.itertuples():
        lines.append(f'| {row.year} | {row.candidate_annual_return:.2%} | {row.reference_annual_return:.2%} | {100*row.simple_return_difference:+.2f} pp | {row.log_growth_difference:+.6f} |')
    lines += ['', 'I differenziali annuali semplici non sono sommabili. Gli incrementi log descrivono i conti osservati; non identificano un profitto causale isolato del singolo reset.','',
        '| Conto | CASH: eseguiti / separati completi | FRESH: eseguiti / separati completi | ENTRY: eseguiti / separati completi |',
        '|---|---:|---:|---:|']
    for arm in ARMS:
        r=paths[f'{arm}__NEXT_CLOSE']['interventions']
        cells=[f"{r[h]['realized_instructions']} / {r[h]['separated_completed21_episodes']}" for h in audit.ACTIONS]
        lines.append('| '+arm+' | '+' | '.join(cells)+' |')
    lines += ['', 'I reset mensili sono conteggiati separatamente da ENTRY. Il numero di episodi con 21 sedute complete e separazione temporale è un controllo di supporto, non una garanzia di indipendenza.','',
        '## Verifiche e limiti','']
    lines += [f"- {key}: {'PASS' if value else 'FAIL'}." for key,value in report['checks'].items()]
    lines += ['', 'L’audit ricostruisce quantità, cash, costi, prezzi eseguiti e NAV prima dei costi e a chiusura; applica il limite di cinque giorni di calendario alle fonti dei prezzi detenuti. '
        'MEAN_RESET è confrontato esattamente con tutti i campi giornalieri e l’intero registro ordini BASE, in ciascuno scenario. '
        'Sono verificati protocollo, codice finanziario, dati, 81 file di modelli e ricevute complete dei 12 percorsi.','',
        '**L’audit non ha addestrato modelli, scelto nuove policy o rieseguito strategie finanziarie.** '
        'Tutti i risultati provengono dai registri congelati. Gli hash di ogni fonte e del codice di audit sono in `INDEPENDENT_SOURCE_MANIFEST.json`.','']
    lines += ['- '+item for item in report['limitations']]
    lines += ['', 'Fonti: `INDEPENDENT_DIAGNOSTICS.json`, `INDEPENDENT_SCORES.csv`, `INDEPENDENT_CRITERIA.csv`, '
        '`INDEPENDENT_MONTHLY_CASH_RESETS.csv`, `INDEPENDENT_CASH_SPELLS.csv`, `INDEPENDENT_ANNUAL_COMPARISONS.csv` '
        'e i registri originali identificati nel manifesto.','']
    destination=root/'research/design/RESULT_ANALYSIS_NOTES.md'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text('\n'.join(lines))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args()
    report=run_audit(args.root)
    print(json.dumps(dict(checks=report['checks'],primary_material_criterion=report['primary_material_criterion'],
        material_arms_primary_execution=report['material_arms_primary_execution'],
        target30_arms_primary_execution=report['target30_arms_primary_execution'],
        audit_new_model_fits=0,audit_new_financial_policies=0),indent=2))
    if not all(report['checks'].values()):
        raise SystemExit(1)
