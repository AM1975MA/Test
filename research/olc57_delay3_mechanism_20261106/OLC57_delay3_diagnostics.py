#!/usr/bin/env python3
"""OLC57: forensic diagnostics for frozen OLC56 DELAY3 vs IMMEDIATE.

Input: original ZIP OLC56_TESTS_20261106_VERIFICATI.zip from ChatGPT Library.
This DOES NOT retrain models, choose parameters or replay prices.
Usage: python OLC57_delay3_diagnostics.py /path/to/OLC56_TESTS_20261106_VERIFICATI.zip
"""
import io
import sys
import zipfile
from pathlib import Path
import pandas as pd

PREFIX = 'OLC56_ROBUST_20261106/results/'
MAIN_YEARS = range(2021, 2025)

def load(z, name):
    return pd.read_csv(io.BytesIO(z.read(PREFIX + name)))

def analyze(z, market):
    daily = load(z, f'{market}_TIMING_DAILY.csv')
    daily['day'] = pd.to_datetime(daily['day'])
    wide = daily.pivot(index='day', columns='policy', values='logR').sort_index()
    assert {'DELAY3', 'IMMEDIATE'} <= set(wide.columns)
    assert wide.notna().all().all() and wide.index.is_unique
    wide['delta'] = wide['DELAY3'] - wide['IMMEDIATE']
    wide['month'] = wide.index.to_period('M')
    wide['session_index'] = wide.groupby('month').cumcount()
    wide['phase'] = wide['session_index'].map(lambda k: 'FIRST_2' if k < 2 else 'REST')
    wide['window'] = wide.index.year.map(lambda y: 'MAIN' if y in MAIN_YEARS else ('LATE' if y >= 2025 else 'EARLY'))

    archived = load(z, f'{market}_TIMING_MONTHLY_DELTA.csv')
    calc = (wide.groupby('month')['delta'].sum() * 10000).rename('calc_log_bp')
    calc.index = calc.index.astype(str)
    merged = archived.merge(calc, left_on='month', right_index=True, validate='one_to_one')
    assert len(merged) == len(archived) == len(calc) == 90
    max_error_bp = (merged['delay_minus_immediate_log_bp'] - merged['calc_log_bp']).abs().max()
    assert max_error_bp < 1e-7, f'monthly parity mismatch: {max_error_bp}'

    # Post-hoc diagnostic sums are log-return DIFFERENCES, not CAGR deltas.
    phase = (wide.groupby(['window', 'phase'])['delta'].sum() * 10000).rename('paired_log_bp')
    phase = phase.reset_index().assign(market=market)
    main = wide[wide.index.year.isin(MAIN_YEARS)]
    assert main['month'].nunique() == 48
    loo = []
    for dropped_year in MAIN_YEARS:
        retained = main[main.index.year != dropped_year]
        nmonths = retained['month'].nunique()
        loo.append(dict(market=market, excluded_year=dropped_year, nmonths=nmonths,
                        annualized_paired_log_pp=retained['delta'].sum() * 100 * 12 / nmonths))
    return phase, pd.DataFrame(loo), max_error_bp

def main(zip_path):
    phase, loo = [], []
    with zipfile.ZipFile(zip_path) as z:
        for market in ('EU', 'USA'):
            p, l, err = analyze(z, market)
            phase.append(p)
            loo.append(l)
            print(f'{market}: monthly parity max |error| = {err:.9g} log-bp')
    phase = pd.concat(phase, ignore_index=True)
    loo = pd.concat(loo, ignore_index=True)
    print('Contributions in paired LOG basis points:')
    print(phase.to_string(index=False, float_format=lambda x: f'{x:.3f}'))
    print('Leave-one-calendar-year-out MAIN annualized paired LOG pp:')
    print(loo.to_string(index=False, float_format=lambda x: f'{x:.3f}'))
    dst = Path.cwd()
    phase.to_csv(dst / 'OLC57_PHASE_CONTRIBUTIONS.csv', index=False)
    loo.to_csv(dst / 'OLC57_LEAVE_ONE_YEAR_OUT.csv', index=False)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python OLC57_delay3_diagnostics.py OLC56_TESTS_20261106_VERIFICATI.zip')
    main(sys.argv[1])
