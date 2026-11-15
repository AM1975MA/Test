"""Diagnostic same-state markouts; no production imports or new strategies.

For every requested intramonth instruction, independently size just that
instruction from its exact DECISIONS.npz account snapshot. Compare the resulting
account with retaining the initial units and cash, at signal + 1, + 5 and + 21
sessions. Future instructions are ignored in both diagnostic branches. Their
due dates are used only to delimit reconciliation with the recorded real path.

The sales-first/cash-reservation algebra is adapted from the independent OLC109
account reference, not from production rebalance or simulate. These overlapping,
future-outcome intervals are not additive and are never annualized.
"""
from __future__ import annotations

import argparse
from collections import deque
import datetime as dt
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd


ARMS = ('EXIT21_MONTHLY', 'EXIT21_STAGED', 'EXIT63_STAGED',
        'EXIT21_STAGED_FRESHW', 'EXIT21_STAGED_FRESHD')
SCENARIOS = ('BASE', 'LAG2', 'NEXT_CLOSE')
CLASSES = ('PURE_EXIT', 'SAME_ASSET_REENTRY', 'PROBE_CONFIRMATION',
           'FRESH_ENTRY', 'MIXED_DEFERRED')
HORIZONS = (1, 5, 21)
TIE_BP = 1e-6


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode(value):
    if isinstance(value, str):
        return json.loads(value)
    return None if pd.isna(value) else value


def truth(value):
    if isinstance(value, str):
        assert value.lower() in ('true', 'false'), ('INVALID_BOOLEAN', value)
        return value.lower() == 'true'
    return bool(value)


def scope_mask(instruction, n):
    indices = instruction['action_indices']
    if indices is None:
        return np.ones(n, bool)
    mask = np.zeros(n, bool)
    mask[indices] = True
    return mask


def quotes_and_marks(panel, k):
    quoted = np.where(panel['valid'][k], panel['O'][k], np.nan)
    marks = np.where(np.isfinite(quoted), quoted, panel['C'][k - 1])
    return quoted, marks


def execution_inputs(panel, instruction, units, cash, k):
    quoted, marks = quotes_and_marks(panel, k)
    assert np.isfinite(marks[units > 1e-12]).all(), ('MISSING_MARK', k)
    wealth = float(cash + np.nansum(units * marks))
    target = instruction['target'].copy()
    if instruction['sell_only']:
        current = np.where(np.isfinite(marks), units * marks, 0.) / wealth
        target = np.minimum(target, current)
    scope = scope_mask(instruction, len(units))
    needed = ((units > 1e-10) | (target > 0)) & scope
    executable = np.where(scope, quoted, np.nan)
    missing = needed & ~np.isfinite(executable)
    return executable, marks, target, missing, scope, wealth


def independent_orders(units, cash, prices, marks, target, ticket, impact, force):
    """Independently value positions, sell excesses, then reserve buy tickets."""
    held = units.copy()
    values = held * np.nan_to_num(marks, nan=0.)
    wealth = float(cash + values.sum())
    budgets = wealth * target
    threshold = max(1e-8, 0. if force else .03 * wealth)
    quoted = np.isfinite(prices) & (prices > 0)
    orders, money = [], float(cash)
    for j in np.flatnonzero(quoted & (values - budgets > 1e-8)):
        excess = values[j] - budgets[j]
        if excess < threshold and target[j] != 0:
            continue
        quantity = min(held[j], excess / prices[j])
        notional = float(quantity * prices[j])
        cost = float(ticket + impact * notional)
        if notional <= cost and money + notional < cost:
            continue
        held[j] -= quantity
        money += notional - cost
        orders.append(dict(j=int(j), side='SELL', quantity=float(quantity),
                           price=float(prices[j]), notional=notional, cost=cost))
    requests = budgets - held * np.nan_to_num(marks, nan=0.)
    eligible = np.flatnonzero(quoted & (requests > 1e-8) &
                             (requests >= threshold) & (requests > ticket))
    if len(eligible) and money > ticket * len(eligible):
        fraction = min(1., (money - ticket * len(eligible)) /
                       ((1. + impact) * requests[eligible].sum()))
        for j in eligible:
            notional = float(requests[j] * fraction)
            if notional <= 1e-8:
                continue
            orders.append(dict(j=int(j), side='BUY', quantity=float(notional / prices[j]),
                               price=float(prices[j]), notional=notional,
                               cost=float(ticket + impact * notional)))
    return orders


def post_orders(units, cash, orders):
    units = units.copy()
    for order in orders:
        j = int(order['j'])
        if order['side'] == 'SELL':
            units[j] -= float(order['quantity'])
            cash += float(order['notional']) - float(order['cost'])
        else:
            assert order['side'] == 'BUY'
            units[j] += float(order['quantity'])
            cash -= float(order['notional']) + float(order['cost'])
    assert np.min(units) >= -1e-10 and cash >= -1e-7, ('SELF_FINANCING', cash, units.min())
    return np.maximum(units, 0.), max(0., float(cash))


def isolated_markouts(panel, instruction, initial_units, initial_cash, *,
                      horizons=HORIZONS, validation_end=None):
    """Execute one instruction with retries, without any later decisions."""
    signal = int(instruction['signal_idx'])
    due = int(instruction['due_idx'])
    cutoff = len(panel['dates']) - 1
    assert 0 <= signal < cutoff and due > signal
    initial_units = np.asarray(initial_units, float).copy()
    initial_cash = float(initial_cash)
    initial_nav = float(initial_cash + np.nansum(initial_units * panel['C'][signal]))
    assert initial_nav > 0
    end = min(cutoff, max(signal + max(horizons), signal if validation_end is None else validation_end))
    units, cash, fees = initial_units.copy(), initial_cash, 0.
    states = [(signal, units.copy(), cash, fees)]
    trades, missing_attempts = [], []
    completed_idx = None
    max_conservation_error = 0.
    for k in range(due, end + 1):
        executable, marks, target, missing, scope, wealth = execution_inputs(
            panel, instruction, units, cash, k)
        before = units.copy()
        orders = independent_orders(units, cash, executable, marks, target,
                                    instruction['ticket'], instruction['impact'],
                                    instruction['force'])
        if instruction['sell_only']:
            assert all(order['side'] == 'SELL' for order in orders), 'SELL_ONLY_BOUGHT'
        units, cash = post_orders(units, cash, orders)
        assert np.array_equal(units[~scope], before[~scope]), 'UNTOUCHED_UNITS_CHANGED'
        day_fees = sum(order['cost'] for order in orders)
        error = abs(cash + np.nansum(units * marks) + day_fees - wealth)
        max_conservation_error = max(max_conservation_error, error)
        assert error < max(1e-7, wealth * 1e-10), ('CONSERVATION', k, error)
        fees += day_fees
        trades.extend(dict(order, execution_idx=k) for order in orders)
        states.append((k, units.copy(), cash, fees))
        if missing.any():
            missing_attempts.append(k)
        else:
            completed_idx = k
            break
    intervals = []
    for horizon in horizons:
        endpoint = min(signal + horizon, cutoff)
        state = next(item for item in reversed(states) if item[0] <= endpoint)
        _, held, money, cost = state
        closing = panel['C'][endpoint]
        hold_nav = float(initial_cash + np.nansum(initial_units * closing))
        action_nav = float(money + np.nansum(held * closing))
        difference = action_nav - hold_nav
        filled = [order for order in trades if order['execution_idx'] <= endpoint]
        market_pnl = sum((1. if order['side'] == 'BUY' else -1.) * order['quantity'] *
                         (closing[order['j']] - order['price']) for order in filled)
        assert abs(market_pnl - (difference + cost)) < max(1e-7, initial_nav * 1e-10), 'DECOMPOSITION'
        net_bp, cost_bp = difference / initial_nav * 10000., cost / initial_nav * 10000.
        market_bp = market_pnl / initial_nav * 10000.
        outcome = 'WIN' if net_bp > TIE_BP else 'LOSS' if net_bp < -TIE_BP else 'TIE'
        intervals.append(dict(horizon_sessions=horizon, endpoint_idx=endpoint,
            actual_horizon_sessions=endpoint - signal, truncated=endpoint < signal + horizon,
            initial_nav=initial_nav, nav_hold=hold_nav, nav_action=action_nav,
            increment_eur=difference, increment_bp=net_bp,
            direct_cost_eur=cost, direct_cost_bp=cost_bp, market_markout_bp=market_bp,
            outcome=outcome, cost_flipped_win_to_loss=(market_bp > TIE_BP and net_bp < -TIE_BP),
            adverse_market_markout=market_bp < -TIE_BP, execution_count=len(filled),
            first_execution_idx=None if not filled else filled[0]['execution_idx'],
            status_at_horizon=('QUEUED' if endpoint < due else 'PENDING'
                               if completed_idx is None or endpoint < completed_idx else 'COMPLETE'),
            missing_quote_attempts=sum(k <= endpoint for k in missing_attempts)))
    return dict(intervals=intervals, trades=trades, end_units=units, end_cash=cash,
                completed_idx=completed_idx, missing_attempts=missing_attempts,
                max_conservation_error=max_conservation_error)


def read_path(root, arm, scenario):
    folder = root / 'results' / f'{arm}__{scenario}'
    files = ('DECISIONS.csv', 'DECISIONS.npz', 'INSTRUCTIONS.csv.gz',
             'ORDERS.csv.gz', 'POLICY_TRACE.csv.gz', 'METRICS.json')
    hashes = {str((folder / file).relative_to(root)): sha(folder / file) for file in files}
    decisions = pd.read_csv(folder / 'DECISIONS.csv', float_precision='round_trip')
    instruction_frame = pd.read_csv(folder / 'INSTRUCTIONS.csv.gz', float_precision='round_trip')
    orders = pd.read_csv(folder / 'ORDERS.csv.gz', float_precision='round_trip')
    trace = pd.read_csv(folder / 'POLICY_TRACE.csv.gz', float_precision='round_trip')
    metrics = json.loads((folder / 'METRICS.json').read_text())
    with np.load(folder / 'DECISIONS.npz', allow_pickle=False) as z:
        arrays = {key: z[key] for key in z.files}
    assert len(decisions) == len(instruction_frame) == len(arrays['k'])
    instructions = []
    for row in instruction_frame.to_dict('records'):
        item = dict(row, target=np.array(decode(row['target_weights']), float),
                    action_indices=decode(row['action_indices']), meta=decode(row['meta']),
                    sell_only=truth(row['sell_only']), force=truth(row['force']),
                    ticket=float(metrics['ticket']), impact=float(metrics['impact_bps']) / 10000.)
        instructions.append(item)
    assert [int(item['instruction_id']) for item in instructions] == list(range(len(instructions)))
    assert np.array_equal(decisions.instruction_id, np.arange(len(instructions)))
    assert np.array_equal(decisions.signal_idx, arrays['k'])
    return decisions, instructions, orders, trace, arrays, metrics, hashes


def verify_empty_book(panel, decisions, instructions, orders, trace, arrays, lag):
    """Replay saved fills and chronological instruction eligibility only.

    This reconstructs the archived book; it does not evaluate a selector or
    create any decision. Exact serialized quantities preserve numerical dust.
    """
    by_signal = {int(item['signal_idx']): item for item in instructions}
    by_k = {int(k): group.to_dict('records') for k, group in orders.groupby('execution_idx', sort=False)}
    trace_by_k = {int(k): group for k, group in trace.groupby('k', sort=False)}
    units, cash = np.zeros(len(panel['names'])), 10000.
    queue, pending = deque(), None
    checked, max_units_error, max_cash_error = [], 0., 0.
    begin = int(instructions[0]['signal_idx'])
    for k in range(begin, len(panel['dates'])):
        if k > begin:
            while queue and int(queue[0]['due_idx']) <= k:
                pending = queue.popleft()
            actual = by_k.get(k, [])
            if pending is not None:
                _, _, _, missing, _, _ = execution_inputs(panel, pending, units, cash, k)
                assert all(int(order['instruction_id']) == int(pending['instruction_id']) for order in actual), ('WRONG_ACTIVE_INSTRUCTION', k)
            else:
                assert not actual, ('ORDERS_WITHOUT_PENDING', k)
            units, cash = post_orders(units, cash, actual)
            if pending is not None and not missing.any():
                pending = None
        if k not in by_signal:
            continue
        item = by_signal[k]
        iid = int(item['instruction_id'])
        assert int(item['due_idx']) == k + 1 + lag, ('DUE_DATE', k)
        max_units_error = max(max_units_error, float(np.max(np.abs(units - arrays['units'][iid]))))
        max_cash_error = max(max_cash_error, abs(cash - float(arrays['cash'][iid])))
        assert np.allclose(units, arrays['units'][iid], rtol=1e-10, atol=1e-7), ('SNAPSHOT_UNITS', k)
        assert np.isclose(cash, arrays['cash'][iid], rtol=1e-10, atol=1e-7), ('SNAPSHOT_CASH', k)
        assert np.array_equal(item['target'], arrays['weights'][iid]), ('TARGET_SNAPSHOT', k)
        record = decisions.iloc[iid]
        if not truth(record['initial']) and not truth(record['scheduled']):
            empty = pending is None and len(queue) == 0
            metadata_empty = not truth(item['meta']['book_busy'])
            trace_empty = not trace_by_k[k].busy.map(truth).any()
            assert empty and metadata_empty and trace_empty, ('INTRAMONTH_BUSY_BOOK', k, iid)
            assert trace_by_k[k].action_emitted.map(truth).all(), ('TRACE_ACTION', k)
            checked.append(dict(instruction_id=iid, signal_idx=k, reconstructed_empty=True,
                                metadata_empty=True, trace_empty=True))
        queue.append(item)
    return checked, dict(max_snapshot_units_error=max_units_error, max_snapshot_cash_error=max_cash_error)


def classify(instruction, units, current):
    scope = scope_mask(instruction, len(units))
    delta = instruction['target'] - current
    plus = np.flatnonzero(scope & (delta > 1e-10))
    minus = np.flatnonzero(scope & (delta < -1e-10))
    changes = instruction['meta'].get('changes', [])
    tokens = {change.split(':')[0] for change in changes}
    changed_assets = {int(change.split(':')[-1]) for change in changes}
    category, subtype = 'MIXED_DEFERRED', 'MIXED_METADATA_OR_DIRECTION'
    if instruction['reason'] == 'DEFERRED_STATE' or not changes:
        subtype = 'DEFERRED_STATE' if instruction['reason'] == 'DEFERRED_STATE' else 'NO_CHANGE_METADATA'
    elif tokens <= {'EXIT', 'REBOUND_EXIT'} and len(minus) and not len(plus):
        category = 'PURE_EXIT'
        subtype = 'REBOUND_FAILURE' if tokens == {'REBOUND_EXIT'} else 'NORMAL_EXIT' if tokens == {'EXIT'} else 'BOTH_EXIT_TYPES'
    elif tokens <= {'REENTER_SLOW', 'REENTER_FAST'} and len(plus) and not len(minus):
        original_assets = {int(slot['asset']) for slot in instruction['meta']['slots']
                           if slot['asset'] is not None and slot['asset'] == slot['primary']}
        if set(plus) <= original_assets & changed_assets and np.all(units[plus] <= 1e-10):
            category = 'SAME_ASSET_REENTRY'
            subtype = 'FAST' if tokens == {'REENTER_FAST'} else 'SLOW' if tokens == {'REENTER_SLOW'} else 'FAST_AND_SLOW'
    elif tokens == {'CONFIRM'} and len(plus) and not len(minus) and np.all(units[plus] > 1e-10):
        category, subtype = 'PROBE_CONFIRMATION', 'CONFIRM'
    elif tokens == {'FRESH'} and len(plus) and not len(minus) and np.all(units[plus] <= 1e-10):
        substitutes = {int(slot['asset']) for slot in instruction['meta']['slots']
                       if slot['asset'] is not None and slot['asset'] != slot['primary']}
        if set(plus) <= substitutes & changed_assets:
            category, subtype = 'FRESH_ENTRY', 'FRESH'
    if not len(plus) and not len(minus):
        category, subtype = 'MIXED_DEFERRED', 'NO_MATERIAL_TARGET_CHANGE'
    return category, subtype, plus.tolist(), minus.tolist()


def validate_recorded_fills(result, actual, until):
    expected = [order for order in result['trades'] if order['execution_idx'] <= until]
    observed = actual[actual.execution_idx <= until].to_dict('records')
    assert len(expected) == len(observed), ('FILL_COUNT', len(expected), len(observed), until)
    errors = dict(quantity=0., price=0., notional=0., cost=0.)
    for wanted, saved in zip(expected, observed):
        assert (wanted['execution_idx'], wanted['j'], wanted['side']) == (
            int(saved['execution_idx']), int(saved['j']), saved['side']), ('FILL_IDENTITY', wanted, saved)
        for field in errors:
            error = abs(float(saved[field]) - wanted[field])
            errors[field] = max(errors[field], error)
            assert np.isclose(float(saved[field]), wanted[field], rtol=1e-10, atol=1e-7), ('FILL_SIZING', field, saved, wanted)
    return dict(fills_checked=len(expected), **{'max_' + key + '_error': value for key, value in errors.items()})


def summary_record(frame):
    full = frame.loc[~frame.truncated]
    count = len(full)
    result = dict(intervals_all=len(frame), complete_intervals=count,
                  truncated_intervals=int(frame.truncated.sum()))
    for outcome in ('WIN', 'LOSS', 'TIE'):
        amount = int((full.outcome == outcome).sum())
        result[outcome.lower() + '_count'] = amount
        result[outcome.lower() + '_pct'] = 100. * amount / count if count else np.nan
    for field in ('increment_bp', 'market_markout_bp', 'direct_cost_bp'):
        result['mean_' + field] = float(full[field].mean()) if count else np.nan
        result['median_' + field] = float(full[field].median()) if count else np.nan
    result.update(p10_increment_bp=float(full.increment_bp.quantile(.1)) if count else np.nan,
                  p90_increment_bp=float(full.increment_bp.quantile(.9)) if count else np.nan,
                  cost_flip_count=int(full.cost_flipped_win_to_loss.sum()),
                  adverse_market_count=int(full.adverse_market_markout.sum()),
                  no_execution_count=int((full.execution_count == 0).sum()),
                  cost_flip_pct=100. * float(full.cost_flipped_win_to_loss.mean()) if count else np.nan,
                  adverse_market_pct=100. * float(full.adverse_market_markout.mean()) if count else np.nan)
    return result


def grouped_summary(frame, columns, *, grid=None):
    groups = {key if isinstance(key, tuple) else (key,): group
              for key, group in frame.groupby(columns, sort=False, dropna=False)}
    keys = groups if grid is None else itertools.product(*grid)
    empty = frame.iloc[:0]
    return pd.DataFrame([dict(zip(columns, key), **summary_record(groups.get(key, empty))) for key in keys])


def run(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    assert output == root / 'analysis/action_diagnostics', 'OUTPUT_SCOPE'
    output.mkdir(exist_ok=True, parents=True)
    manifest = json.loads((root / 'results/RUN_MANIFEST.json').read_text())
    for name, digest in manifest['code_hashes'].items():
        assert sha(root / name) == digest, ('FROZEN_CODE_CHANGED', name)
    panel_path = root / 'source/data/XETRA_EUR_ETF.npz'
    assert sha(panel_path) == manifest['input_hashes']['source/data/XETRA_EUR_ETF.npz']
    with np.load(panel_path, allow_pickle=False) as z:
        raw = {key: z[key] for key in z.files}
    valid_close = raw['observed'] & np.isfinite(raw['C']) & (raw['C'] > 0)
    closes = pd.DataFrame(np.where(valid_close, raw['C'], np.nan)).ffill().to_numpy()
    dates, names = pd.DatetimeIndex(raw['dates']), raw['names']
    input_hashes = {'source/data/XETRA_EUR_ETF.npz': sha(panel_path),
                    'results/RUN_MANIFEST.json': sha(root / 'results/RUN_MANIFEST.json')}
    intervals, event_rows, fill_checks, book_checks, isolated_trades = [], [], [], [], []
    reconstruction_maxima = dict(max_snapshot_units_error=0., max_snapshot_cash_error=0., max_conservation_error=0.)
    for arm, scenario in itertools.product(ARMS, SCENARIOS):
        decisions, instructions, orders, trace, arrays, metrics, hashes = read_path(root, arm, scenario)
        input_hashes.update(hashes)
        is_close = scenario == 'NEXT_CLOSE'
        quotes = raw['C'] if is_close else raw['O']
        valid = valid_close if is_close else raw['open_observed'] & np.isfinite(quotes) & (quotes > 0)
        panel = dict(C=closes, O=quotes, valid=valid, dates=dates, names=names)
        checked, snapshot_errors = verify_empty_book(panel, decisions, instructions, orders, trace,
                                                   arrays, int(metrics['lag_extra']))
        for key, value in snapshot_errors.items():
            reconstruction_maxima[key] = max(reconstruction_maxima[key], value)
        book_checks.extend(dict(arm=arm, scenario=scenario, **row) for row in checked)
        count = 0
        for record in decisions.to_dict('records'):
            if truth(record['initial']) or truth(record['scheduled']):
                continue
            iid, signal = int(record['instruction_id']), int(record['signal_idx'])
            instruction = instructions[iid]
            assert instruction['action_indices'] is not None, ('EXPECTED_TARGETED_EVENT', arm, scenario, iid)
            units, cash = arrays['units'][iid].copy(), float(arrays['cash'][iid])
            starting_nav = float(cash + np.nansum(units * closes[signal]))
            current = np.where(np.isfinite(closes[signal]), units * closes[signal], 0.) / starting_nav
            assert np.allclose(current, arrays['current_weights'][iid], rtol=1e-12, atol=1e-12), 'START_WEIGHTS'
            category, subtype, increase, decrease = classify(instruction, units, current)
            next_due = int(instructions[iid + 1]['due_idx']) if iid + 1 < len(instructions) else len(dates)
            validation_end = min(next_due - 1, len(dates) - 1)
            result = isolated_markouts(panel, instruction, units, cash, validation_end=validation_end)
            reconstruction_maxima['max_conservation_error'] = max(
                reconstruction_maxima['max_conservation_error'], result['max_conservation_error'])
            actual = orders[orders.instruction_id == iid]
            check = validate_recorded_fills(result, actual, validation_end)
            identity = dict(arm=arm, scenario=scenario, instruction_id=iid,
                            signal_idx=signal, signal_date=str(dates[signal].date()),
                            signal_year=int(dates[signal].year), category=category, subtype=subtype)
            fill_checks.append(dict(identity, validation_end_idx=validation_end,
                                    first_later_instruction_due_idx=next_due,
                                    status='PASS', **check))
            event_rows.append(dict(identity, reason=instruction['reason'], due_idx=int(instruction['due_idx']),
                action_indices=json.dumps(instruction['action_indices']),
                increase_indices=json.dumps(increase), decrease_indices=json.dumps(decrease),
                increase_isins=json.dumps([str(names[j]) for j in increase]),
                decrease_isins=json.dumps([str(names[j]) for j in decrease]),
                changes_json=json.dumps(instruction['meta'].get('changes', [])),
                starting_nav=starting_nav, starting_cash=cash,
                sell_only=instruction['sell_only'], force=instruction['force'],
                empty_book_verified=True, diagnostic_completion_idx=result['completed_idx'],
                diagnostic_missing_attempts=len(result['missing_attempts']),
                isolated_fills=len(result['trades']), recorded_fills_before_supersession=check['fills_checked']))
            for row in result['intervals']:
                intervals.append(dict(identity, **row,
                    endpoint_date=str(dates[row['endpoint_idx']].date()),
                    future_outcome_label=True, overlapping_intervals=True))
            isolated_trades.extend(dict(identity, ticker=str(names[order['j']]),
                                         execution_date=str(dates[order['execution_idx']].date()),
                                         recorded_path_comparable=order['execution_idx'] <= validation_end,
                                         **order) for order in result['trades'])
            count += 1
        print(f'{arm} {scenario}: {count} isolated events; empty books and initial fills reconciled', flush=True)
    frame, events = pd.DataFrame(intervals), pd.DataFrame(event_rows)
    frame.to_csv(output / 'INTERVAL_MARKOUTS.csv', index=False)
    events.to_csv(output / 'EVENT_CATALOGUE.csv', index=False)
    pd.DataFrame(fill_checks).to_csv(output / 'FILL_VALIDATION.csv', index=False)
    pd.DataFrame(book_checks).to_csv(output / 'EMPTY_BOOK_VALIDATION.csv', index=False)
    pd.DataFrame(isolated_trades).to_csv(output / 'ISOLATED_FILLS.csv', index=False)
    grouped_summary(frame, ['arm', 'scenario', 'category', 'horizon_sessions'],
                    grid=[ARMS, SCENARIOS, CLASSES, HORIZONS]).to_csv(output / 'SUMMARY_BY_CLASS.csv', index=False)
    grouped_summary(frame, ['arm', 'scenario', 'category', 'subtype', 'horizon_sessions']).to_csv(
                    output / 'SUMMARY_BY_SUBTYPE.csv', index=False)
    grouped_summary(frame, ['arm', 'scenario', 'signal_year', 'category', 'horizon_sessions'],
                    grid=[ARMS, SCENARIOS, tuple(range(2020, 2027)), CLASSES, HORIZONS]).to_csv(
                    output / 'SUMMARY_BY_YEAR.csv', index=False)
    grouped_summary(frame, ['arm', 'scenario', 'horizon_sessions'],
                    grid=[ARMS, SCENARIOS, HORIZONS]).to_csv(output / 'SUMMARY_ALL_EVENTS.csv', index=False)
    frame.loc[frame.truncated].to_csv(output / 'TRUNCATED_INTERVALS.csv', index=False)
    counts = events.groupby(['arm', 'scenario', 'category', 'subtype'], dropna=False).size().rename('events').reset_index()
    counts.to_csv(output / 'CLASSIFICATION_COUNTS.csv', index=False)
    for name, digest in manifest['code_hashes'].items():
        assert sha(root / name) == digest, ('FROZEN_CODE_CHANGED_AFTER_ANALYSIS', name)
    assert all(sha(root / name) == digest for name, digest in input_hashes.items()), 'SOURCE_MUTATION'
    qa = dict(status='PASS_ISOLATED_EVENT_DIAGNOSTICS', completed_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        paths=15, events=len(events), intervals=len(frame), horizons=list(HORIZONS),
        empty_books_verified=len(book_checks), fill_comparisons=len(fill_checks),
        individual_fills_checked=int(pd.DataFrame(fill_checks).fills_checked.sum()),
        truncated_intervals=int(frame.truncated.sum()),
        truncated_events=int(frame.loc[frame.truncated, ['arm', 'scenario', 'instruction_id']].drop_duplicates().shape[0]),
        no_execution_complete_intervals=int(((frame.execution_count == 0) & ~frame.truncated).sum()),
        maximum_errors={**reconstruction_maxima, **{
            key: float(pd.DataFrame(fill_checks)[key].max())
            for key in ('max_quantity_error', 'max_price_error', 'max_notional_error', 'max_cost_error')}},
        denominator='Identical signal-Close NAV from exact DECISIONS.npz units and cash',
        direct_cost='Actual diagnostic order fees; no terminal liquidation fee',
        gross_market_markout='Net NAV difference plus direct costs on actual fee-constrained quantities',
        horizon_anchor='Signal session; T+1 can precede the first LAG2 execution',
        tie_tolerance_bp=TIE_BP, production_imports=False, new_strategy_runs=0,
        future_outcomes_used_only_for_diagnostics=True, overlapping_not_additive=True,
        annualized_or_compounded=False, full_horizon_summaries_exclude_truncation=True,
        limitations=['Conditional same-state diagnostics, not prospective or randomized evidence.',
                    'Overlap and repeated assets make intervals dependent; frequencies are descriptive.',
                    'Different arms and scenarios have different event states and dates.',
                    'Cash counterfactual earns zero; fees at the horizon are not assumed liquidation fees.',
                    'Market markout does not remove equity risk premium or evaluate alternative candidate choices.',
                    'NEXT_CLOSE uses accepted future closes for execution; its T+1 market component is zero when filled once.',
                    'No certification of point-in-time universe, adjusted-price vintage, provenance or capacity.'])
    (output / 'VALIDATION.json').write_text(json.dumps(qa, indent=2) + '\n')
    outputs = {file.name: sha(file) for file in sorted(output.glob('*.csv'))}
    provenance = dict(script_sha256=sha(Path(__file__)), input_hashes=input_hashes,
                      financial_code_hashes_unchanged=manifest['code_hashes'], output_csv_hashes=outputs,
                      run_command='python analysis/action_diagnostics/action_markouts.py . analysis/action_diagnostics')
    (output / 'PROVENANCE.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(qa, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.root, args.output)
