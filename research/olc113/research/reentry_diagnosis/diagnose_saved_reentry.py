"""Read-only OLC111/112 frozen-model diagnostics; never fit or replay policies.

Only output files under this script's directory are written. Training-bank
outcomes are descriptive overlapping one-intervention comparisons, not policy
returns. Synthetic fresh-held predictions compare existing heads, not labels.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'olc111/src'))
from advantage_model import AdvantageModel
from research_pipeline import basket_stats, feature_monthly_schedule, fresh_is_action, state_features


def read_npz(path):
    with np.load(path, allow_pickle=False) as source:
        return {key: source[key] for key in source.files}


def native(value):
    if isinstance(value, dict):
        return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    if isinstance(value, np.ndarray):
        return native(value.tolist())
    if isinstance(value, np.generic):
        return native(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def describe(values):
    x = np.asarray(values, float)
    x = x[np.isfinite(x)]
    return dict(n=len(x), mean=float(np.mean(x)), min=float(np.min(x)),
                q10=float(np.quantile(x, .1)), median=float(np.median(x)),
                q90=float(np.quantile(x, .9)), max=float(np.max(x))) if len(x) else dict(n=0)


def load_model(values):
    return AdvantageModel(values['model_name'], values['coefficients'],
                          values['bootstrap_coefficients'], values['transforms'],
                          values['feature_counts'], values['metadata'])


def run():
    used_paths = {ROOT / relative for relative in (
        'olc111/src/advantage_model.py', 'olc111/src/research_pipeline.py',
        'olc111/src/run_olc111.py', 'olc111/src/replay_engine.py',
        'olc112/src/run_rotation_overlay.py', 'olc110/source/src/core.py',
        'olc110/src/signals.py')}
    def npz(relative):
        used_paths.add(ROOT / relative)
        return read_npz(ROOT / relative)
    def csv(relative):
        used_paths.add(ROOT / relative)
        return pd.read_csv(ROOT / relative, float_precision='round_trip')

    panel = npz('olc110/source/data/XETRA_EUR_ETF.npz')
    dates = pd.DatetimeIndex(panel['dates'])
    n = len(dates)
    # This is exactly the source core.features definition for these two fields.
    marked = pd.DataFrame(np.where(panel['observed'] & (panel['C'] > 0) &
                                  np.isfinite(panel['C']), panel['C'], np.nan)).ffill()
    features = dict(C=marked.to_numpy(), returns=np.log(marked / marked.shift(1)).to_numpy())
    months = dates.to_period('M')
    monthly = np.r_[months[:-1] != months[1:], False]
    feature_monthly = feature_monthly_schedule(dates, monthly)
    selections = npz('olc111/data/CAUSAL_SELECTIONS.npz')
    targets, breadth = selections['targets'], selections['breadth']
    cboe = npz('olc111/data/CBOE_ALIGNED.npz')
    banks = {head: npz(f'olc111/data/BANK_{head}.npz') for head in ['CASH', 'FRESH', 'ENTRY']}
    baseline = npz('olc111/data/BASELINE_STATES.npz')
    base_by_k = {int(k): i for i, k in enumerate(baseline['k'])}
    event_path = ROOT / 'olc111/data/BANK_EVENTS.jsonl'
    used_paths.add(event_path)
    events = {int(row['k']): row for line in event_path.read_text().splitlines()
              if line for row in [json.loads(line)]}
    empty = np.zeros(len(panel['names']))
    feature_rows = {}
    for k in range(270, n - 1):
        feature_rows[k] = state_features(features, k, targets[k], targets[k],
                                         breadth[k], feature_monthly)

    model_cache = {}
    def fitted(cutoff):
        if cutoff not in model_cache:
            path = ROOT / f'olc111/results/FITS/FIT_{cutoff:06d}.json.gz'
            used_paths.add(path)
            raw = json.loads(gzip.decompress(path.read_bytes()))
            model_cache[cutoff] = {head: None if record is None else
                dict(meta=record['meta'], models={arm: load_model(model)
                     for arm, model in record['models'].items()})
                for head, record in raw['heads'].items()}
        return model_cache[cutoff]

    feature_names = ['fresh_nm21', 'fresh_nm63', 'fresh_log_vol21_over_vol63',
                     'breadth63', 'sessions_to_next_month_div21']
    all_cash_rows, spell_summaries, path_summaries = [], [], []
    max_prediction_error = 0.
    max_feature_error = 0.
    feature_reconciled = 0
    for study, arms in [('olc111', ['MEAN', 'PRICE', 'VIX', 'TERM']),
                        ('olc112', ['MEAN_ROTATION', 'PRICE_ROTATION', 'VIX_ROTATION', 'TERM_ROTATION'])]:
        for arm in arms:
            for scenario in ['NEXT_CLOSE', 'DOUBLE_COST', 'NEXT_OPEN']:
                path_id = f'{arm}__{scenario}'
                trace = csv(f'{study}/results/{path_id}/POLICY_TRACE.csv.gz')
                daily = csv(f'{study}/results/{path_id}/DAILY.csv.gz')
                cash = trace.loc[(trace.gross <= 1e-8) & trace.model_ready_all].copy()
                path_summaries.append(dict(study=study, path_id=path_id,
                    cash_rows=len(cash), predictions=int(cash.entry_mean.notna().sum()),
                    ready=int(cash.model_ready_all.sum()), source_available=int(cash.source_available.sum()),
                    fallback=int(cash.fallback_price.sum()), busy=int((cash.status == 'BUSY').sum()),
                    unsupported=int((cash.status == 'HOLD_UNSUPPORTED').sum()),
                    mean_positive=int((cash.entry_mean > 0).sum()),
                    both_positive=int(((cash.entry_mean > 0) & (cash.entry_lower > 0)).sum()),
                    mean_positive_lower_nonpositive=int(((cash.entry_mean > 0) & (cash.entry_lower <= 0)).sum()),
                    mean_nonpositive=int((cash.entry_mean <= 0).sum())))
                if scenario != 'NEXT_CLOSE':
                    continue
                ready_cash = daily.loc[(daily.gross <= 1e-8) & (daily.k >= 865)]
                intervals = []
                if len(ready_cash):
                    grouped = (ready_cash.k.diff().fillna(1) != 1).cumsum()
                    intervals = [(int(block.k.iloc[0]), int(block.k.iloc[-1]))
                                 for _, block in ready_cash.groupby(grouped)]
                detailed = []
                for row in cash.itertuples():
                    k, cutoff = int(row.k), int(row.fit_cutoff_idx)
                    fp = feature_rows[k]['ENTRY']
                    valid = fp is not None and np.isfinite(fp).all()
                    record = dict(study=study, path_id=path_id, k=k, date=row.date,
                        scheduled=bool(row.scheduled), status=row.status, action=row.action,
                        gross=row.gross, nav=row.nav, cutoff=cutoff,
                        model_ready_all=bool(row.model_ready_all), source_available=bool(row.source_available),
                        fallback_price=bool(row.fallback_price), mean=row.entry_mean, lower=row.entry_lower,
                        candidate_gross=float(targets[k].sum()),
                        candidate_positions=int((targets[k] > 1e-12).sum()),
                        candidate_legal=fresh_is_action(empty, targets[k]),
                        feature_valid=valid, max_abs_z=row.entry_max_abs_standardized_price,
                        has_bank_comparison=k in events and 'cash' in events[k])
                    if valid:
                        model_arm = row.entry_model_arm
                        m = fitted(cutoff)['ENTRY']['models'][model_arm]
                        prediction = m.predict(fp, cboe['legacy'][k], cboe['term'][k])
                        max_prediction_error = max(max_prediction_error, abs(prediction['mean'] - row.entry_mean),
                                                   abs(prediction['lower'] - row.entry_lower))
                        vector = m._prediction_vector(fp, cboe['legacy'][k], cboe['term'][k])
                        contribution = vector * m.coefficients
                        if model_arm != 'MEAN':
                            for j, name in enumerate(feature_names):
                                record[name] = fp[j]
                                record[f'z_{name}'] = vector[j + 1]
                                record[f'contribution_{name}'] = contribution[j + 1]
                            record['contribution_intercept'] = contribution[0]
                            record['contribution_options'] = float(contribution[6:].sum())
                            mask = banks['ENTRY']['terminal_idx'] < cutoff
                            train_x = banks['ENTRY']['Xprice'][mask]
                            outside = (fp < train_x.min(axis=0)) | (fp > train_x.max(axis=0))
                            record['outside_training_range_any'] = bool(outside.any())
                            record['outside_training_range_features'] = '|'.join(np.array(feature_names)[outside])
                            record['train_dates'] = fitted(cutoff)['ENTRY']['meta']['n_dates']
                            record['train_mean_target'] = float(banks['ENTRY']['y'][mask].mean())
                            record['train_positive_target_fraction'] = float((banks['ENTRY']['y'][mask] > 0).mean())
                            record['entry_nm63_slope_per_training_sd'] = m.coefficients[2]
                        record['next_month_sessions'] = float(fp[-1] * 21)
                        record['next_month_signal_date'] = str(dates[k + int(round(fp[-1] * 21))].date())
                    e = events.get(k, {})
                    if 'cash' in e and e['cash']['status'] == 'OK':
                        entry = e['cash']
                        record['bank_entry_advantage'] = entry['net']['FRESH']
                        record['bank_entry_vs_initial_cash_log'] = float(np.log(entry['nav']['FRESH'] / entry['initial_nav']))
                        record['bank_hold_then_monthly_vs_initial_cash_log'] = float(np.log(entry['nav']['HOLD'] / entry['initial_nav']))
                        record['bank_hold_branch_orders'] = entry['orders']['HOLD']
                        record['bank_initial_nav'] = entry['initial_nav']
                        record['actual_nav_over_bank_nav'] = row.nav / entry['initial_nav']
                        bank_features = next(x['Xprice'] for x in e['rows'] if x['head'] == 'ENTRY')
                        max_feature_error = max(max_feature_error, float(np.max(np.abs(fp - bank_features))))
                        feature_reconciled += 1
                    detailed.append(record)
                details = pd.DataFrame(detailed)
                all_cash_rows.extend(detailed)
                for first, last in intervals:
                    block = details.loc[(details.k >= first) & (details.k <= last)]
                    pred = block.loc[block['mean'].notna()]
                    held = pred.loc[pred.action == 'HOLD']
                    labeled = block.loc[block.get('bank_entry_advantage', pd.Series(index=block.index, dtype=float)).notna()]
                    exitrows = trace.loc[(trace.k < first) & (trace.action == 'CASH')]
                    entryrows = block.loc[block.action == 'ENTRY']
                    summary = dict(study=study, path_id=path_id, start_idx=first, end_idx=last,
                        start_date=str(dates[first].date()), last_cash_date=str(dates[last].date()),
                        cash_sessions=last-first+1, trace_rows=len(block), predictions=len(pred),
                        scheduled_cash_days=int(block.scheduled.sum()),
                        candidate_legal=int(block.candidate_legal.sum()), feature_valid=int(block.feature_valid.sum()),
                        model_ready=int(block.model_ready_all.sum()), source_unavailable=int((~block.source_available).sum()),
                        fallback_days=int(block.fallback_price.sum()), status_counts=block.status.value_counts().to_dict(),
                        mean_positive=int((pred['mean'] > 0).sum()),
                        both_positive=int(((pred['mean'] > 0) & (pred.lower > 0)).sum()),
                        mean_positive_lower_nonpositive=int(((pred['mean'] > 0) & (pred.lower <= 0)).sum()),
                        mean_nonpositive=int((pred['mean'] <= 0).sum()),
                        first_positive_mean_date=None if not (pred['mean'] > 0).any() else pred.loc[pred['mean'] > 0, 'date'].iloc[0],
                        mean_stats=describe(pred['mean']), lower_stats=describe(pred.lower),
                        mean_minus_lower_stats=describe(pred['mean'] - pred.lower),
                        hold_max_lower=float(held.lower.max()) if len(held) else None,
                        hold_max_lower_date=None if not len(held) else held.loc[held.lower.idxmax(), 'date'],
                        entry_signal_date=None if entryrows.empty else entryrows.date.iloc[-1],
                        next_invested_close_date=None if last + 1 >= n else str(dates[last + 1].date()),
                        exit_signal_date=None if exitrows.empty else exitrows.date.iloc[-1],
                        max_abs_z_stats=describe(block.max_abs_z),
                        max_abs_z_above3=int((block.max_abs_z > 3).sum()),
                        max_abs_z_above5=int((block.max_abs_z > 5).sum()),
                        outside_training_range_days=int(block.get('outside_training_range_any',pd.Series(dtype=bool)).sum()),
                        label_rows=len(labeled), label_positive=int((labeled.bank_entry_advantage > 0).sum()) if len(labeled) else 0,
                        label_mean=float(labeled.bank_entry_advantage.mean()) if len(labeled) else None,
                        entry_absolute_positive=int((labeled.bank_entry_vs_initial_cash_log > 0).sum()) if len(labeled) else 0,
                        entry_absolute_mean_log=float(labeled.bank_entry_vs_initial_cash_log.mean()) if len(labeled) else None,
                        delayed_monthly_absolute_mean_log=float(labeled.bank_hold_then_monthly_vs_initial_cash_log.mean()) if len(labeled) else None,
                        label_negative_but_entry_absolute_positive=int(((labeled.bank_entry_advantage <= 0) &
                            (labeled.bank_entry_vs_initial_cash_log > 0)).sum()) if len(labeled) else 0,
                        labeled_hold_branch_with_orders=int((labeled.bank_hold_branch_orders > 0).sum()) if len(labeled) else 0,
                        actual_nav_over_bank_nav_stats=describe(labeled.actual_nav_over_bank_nav) if len(labeled) else {},
                        mean_contributions={c.removeprefix('contribution_'):float(block[c].mean())
                            for c in block.columns if c.startswith('contribution_')},
                        feature_summary={c:describe(block[c]) for c in feature_names if c in block})
                    spell_summaries.append(summary)

    # Existing CASH/ENTRY predictions on the same calendar features, with
    # CASH evaluated as if today's fresh basket were already held at gross 1.
    reference_trace = csv('olc112/results/PRICE_ROTATION__NEXT_CLOSE/POLICY_TRACE.csv.gz')
    matched_rows = []
    for row in reference_trace.loc[reference_trace.model_ready_all].itertuples():
        k, cutoff = int(row.k), int(row.fit_cutoff_idx)
        fp, cp = feature_rows[k]['ENTRY'], feature_rows[k]['CASH']
        if fp is None or cp is None or not np.isfinite(fp).all() or not np.isfinite(cp).all():
            continue
        for arm in ['MEAN', 'PRICE', 'VIX', 'TERM']:
            source_ok = bool(cboe['available'][k] and np.isfinite(cboe['legacy'][k]).all()
                             and np.isfinite(cboe['term'][k]).all())
            model_arm = 'PRICE' if arm in ('VIX','TERM') and not source_ok else arm
            models = fitted(cutoff)
            exit_pred = models['CASH']['models'][model_arm].predict(cp, cboe['legacy'][k], cboe['term'][k])
            entry_pred = models['ENTRY']['models'][model_arm].predict(fp, cboe['legacy'][k], cboe['term'][k])
            matched_rows.append(dict(k=k, date=row.date, arm=arm, model_arm=model_arm,
                cash_mean=exit_pred['mean'], cash_lower=exit_pred['lower'],
                entry_mean=entry_pred['mean'], entry_lower=entry_pred['lower'],
                mean_sum=exit_pred['mean']+entry_pred['mean'],
                cash_pass=exit_pred['mean']>0 and exit_pred['lower']>0,
                entry_pass=entry_pred['mean']>0 and entry_pred['lower']>0))
    matched = pd.DataFrame(matched_rows)
    matched_summaries = []
    for scope, mask in [('all_postwarmup', np.ones(len(matched), bool)),
                        ('price_long_cash', (matched.k >= 1606) & (matched.k <= 1820)),
                        ('term_long_cash', (matched.k >= 1627) & (matched.k <= 1820))]:
        for arm, block in matched.loc[mask].groupby('arm'):
            matched_summaries.append(dict(scope=scope, arm=arm, rows=len(block),
                mean_correlation=float(block.cash_mean.corr(block.entry_mean)),
                cash_mean_positive=int((block.cash_mean>0).sum()),
                entry_mean_positive=int((block.entry_mean>0).sum()),
                both_mean_positive=int(((block.cash_mean>0)&(block.entry_mean>0)).sum()),
                both_mean_nonpositive=int(((block.cash_mean<=0)&(block.entry_mean<=0)).sum()),
                both_lower_positive=int((block.cash_pass&block.entry_pass).sum()),
                neither_lower_positive=int((~block.cash_pass&~block.entry_pass).sum()),
                exit_pass_entry_nonpositive=int((block.cash_pass & (block.entry_mean<=0)).sum()),
                mean_sum=describe(block.mean_sum)))

    # Exact dates with both saved label heads; closeness of actual baseline book
    # to fresh basket is recorded, rather than claiming exact reciprocity.
    label_pair_rows = []
    for k, event in events.items():
        if not ('cash' in event and 'invested' in event and
                event['cash']['status']=='OK' and event['invested']['status']=='OK'):
            continue
        seq = base_by_k[k]
        current = baseline['units'][seq] * np.where(np.isfinite(features['C'][k]), features['C'][k], 0.) / baseline['nav'][seq]
        near = float(np.abs(current-targets[k]).sum())
        label_pair_rows.append(dict(k=k,date=str(dates[k].date()),
            baseline_fresh_l1=near, baseline_gross=float(current.sum()),
            cash_label=event['invested']['net']['CASH'], entry_label=event['cash']['net']['FRESH'],
            label_sum=event['invested']['net']['CASH']+event['cash']['net']['FRESH'],
            entry_hold_orders=event['cash']['orders']['HOLD']))
    pairs = pd.DataFrame(label_pair_rows)
    pair_summaries = []
    for name, block in [('all', pairs), ('fresh_within_noop_band', pairs.loc[pairs.baseline_fresh_l1 < .03])]:
        pair_summaries.append(dict(scope=name,rows=len(block),
            mean_label_sum=float(block.label_sum.mean()),
            positive_sum=int((block.label_sum>0).sum()),
            both_positive_labels=int(((block.cash_label>0)&(block.entry_label>0)).sum()),
            correlation=float(block.cash_label.corr(block.entry_label)),
            label_sum_stats=describe(block.label_sum),
            entry_hold_branch_orders=int((block.entry_hold_orders>0).sum())))

    diagnostics = dict(description=__doc__, frozen_model_fits_used=len(model_cache), new_fits=0,
        new_policy_replays=0, path_summaries=path_summaries, spell_summaries=spell_summaries,
        matched_summaries=matched_summaries, label_pair_summaries=pair_summaries,
        reconciliation=dict(max_saved_entry_prediction_abs_error=max_prediction_error,
                            max_reconstructed_entry_feature_abs_error=max_feature_error,
                            reconciled_bank_entry_feature_rows=feature_reconciled),
        entry_training_definition='FRESH now minus HOLD cash followed by automatic monthly baseline continuation',
        entry_deployed_hold='Cash stays cash at monthly dates until current ENTRY mean and lower are both positive',
        entry_features=feature_names,
        files_read_sha256={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sorted(used_paths)})
    (OUT/'DIAGNOSTICS.json').write_text(json.dumps(native(diagnostics),indent=2,allow_nan=False)+'\n')
    pd.DataFrame(all_cash_rows).to_csv(OUT/'CASH_DECISION_DETAILS.csv',index=False)
    pd.DataFrame(path_summaries).to_csv(OUT/'ALL_PATH_CASH_GATE_SUMMARY.csv',index=False)
    matched.to_csv(OUT/'MATCHED_FRESH_HELD_PREDICTIONS.csv',index=False)
    pairs.to_csv(OUT/'MATCHED_BANK_LABELS.csv',index=False)
    print(json.dumps(native(dict(reconciliation=diagnostics['reconciliation'],
        long_cash_spells=[r for r in spell_summaries if r['study']=='olc112' and r['cash_sessions']>=190],
        matched_summaries=[r for r in matched_summaries if r['scope']=='all_postwarmup'],
        label_pair_summaries=pair_summaries)),indent=2))


if __name__ == '__main__':
    run()
