#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def assert_source_contract(runner_path: Path, exec_path: Path) -> None:
    r = runner_path.read_text()
    e = exec_path.read_text()
    required_runner = [
        "compact.exit_date<cutoff",
        "compact.target_rank_pct.notna()",
        "(tr.target_rank_pct*100).round().astype(int)",
        "pd.to_datetime(macro.macro_label_exit_date_63)<cutoff",
        "pred['TIT_R']=pred.groupby('signal_date').titanium_score.rank(pct=True,method='average')",
        "op['opp_raw']=op['target_excess_max_pred']",
        "load_fixture_baskets",
        "PERIOD_SCORECARD_500.csv",
    ]
    required_exec = [
        "sort_values(['TIT_R','titanium_score'],ascending=False)",
        "m=float(r1.TIT_R-r2.TIT_R)",
        "label_exit_date_21<cutoff",
    ]
    missing = [x for x in required_runner if x not in r] + [x for x in required_exec if x not in e]
    if missing:
        raise AssertionError(f"Source contract missing: {missing}")
    forbidden = [
        "np.minimum(4,np.floor(tr.target_rank_21.to_numpy(float)*5.0))",
        "m=float(r1.titanium_score-r2.titanium_score)",
    ]
    bad = [x for x in forbidden if x in r or x in e]
    if bad:
        raise AssertionError(f"Forbidden forensic logic remains: {bad}")


def test_monthly_label(runner) -> None:
    dates = pd.bdate_range('2020-01-01', '2020-04-10')
    tickers = ['A', 'B']
    O = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    O['A'] = np.arange(len(dates), dtype=float) + 100.0
    O['B'] = np.arange(len(dates), dtype=float) * 2.0 + 100.0
    sig = pd.DatetimeIndex([
        dates[dates.to_period('M') == pd.Period('2020-01')][-1],
        dates[dates.to_period('M') == pd.Period('2020-02')][-1],
        dates[dates.to_period('M') == pd.Period('2020-03')][-1],
    ])
    panel = pd.MultiIndex.from_product([sig, tickers], names=['signal_date','ticker']).to_frame(index=False)
    out = runner.add_labels(panel, O, sig)
    jan = out[out.signal_date.eq(sig[0])].set_index('ticker')
    entry = dates[dates.get_loc(sig[0]) + 1]
    feb_entry = dates[dates.get_loc(sig[1]) + 1]
    for t in tickers:
        expected = O.at[feb_entry, t] / O.at[entry, t] - 1.0
        assert abs(float(jan.at[t, 'fwd_ret_monthly']) - expected) < 1e-12
    assert jan.loc['B','target_rank_pct'] > jan.loc['A','target_rank_pct']


def test_rank_each_seed_semantics() -> None:
    # Raw-scale differences make mean-raw and rank-each-then-mean non-equivalent.
    raw = pd.DataFrame({
        's1':[1000.0, 900.0, 1.0],
        's2':[0.0, 100.0, 99.0],
        's3':[0.0, 100.0, 99.0],
    }, index=['A','B','C'])
    rank_each = raw.rank(pct=True).mean(axis=1)
    mean_raw_rank = raw.mean(axis=1).rank(pct=True)
    assert not np.allclose(rank_each.to_numpy(), mean_raw_rank.to_numpy())


def test_tit_r_margin(execmod) -> None:
    dt = pd.Timestamp('2020-01-31'); entry = pd.Timestamp('2020-02-03')
    pred = pd.DataFrame({
        'signal_date':[dt,dt,dt], 'ticker':['A','B','C'],
        'titanium_score':[1.00,0.91,0.10],
        # A-B raw gap=.09 (<.12), but TIT_R gap=.20 (>=.12): must concentrate 100/0.
        'TIT_R':[1.00,0.80,0.20],
    })
    opp = pd.DataFrame({'signal_date':[dt,dt],'cluster_id':[0,1],'opp_z':[1.0,0.0]})
    clusters = pd.DataFrame({'signal_date':[dt,dt,dt],'ticker':['A','B','C'],'cluster_id':[0,1,1]})
    O = pd.DataFrame([[10.0,10.0,10.0]], index=[entry], columns=['A','B','C'])
    ti = {'A':0,'B':1,'C':2}
    sel,bw,*rest = execmod.build_target_arrays([['A','B','C']], pred, opp, clusters, pd.DatetimeIndex([dt]), ti, O, pd.DatetimeIndex([entry]))
    assert abs(float(bw[0,0,0]) - 1.0) < 1e-12
    assert abs(float(bw[0,0,1])) < 1e-12


def validate_fit_audit(path: Path) -> None:
    a = pd.read_csv(path)
    for row in a.itertuples():
        cutoff = pd.Timestamp(row.cutoff)
        for col in ['compact_max_exit','tail_max_exit63','macro_max_exit63','opp_max_exit21']:
            val = getattr(row, col)
            if pd.notna(val):
                assert pd.Timestamp(val) < cutoff, (row.year, col, val, cutoff)


def validate_results(result_dir: Path) -> None:
    validate_fit_audit(result_dir/'FIT_AUDIT.csv')
    p = pd.read_csv(result_dir/'PERIOD_SCORECARD_500.csv')
    expected_periods = {'D1','D2','DEV','HOLD','FULL'}
    assert expected_periods.issubset(set(p.period)), set(p.period)
    assert {'BASE','DIRECT','ROUTER'}.issubset(set(p.strategy))
    m = pd.read_csv(result_dir/'BASKET_MEMBERSHIP_500.csv')
    assert m.basket.nunique() == 500
    assert m.groupby('basket').size().eq(24).all()
    chk = __import__('json').loads((result_dir/'KNOWN_SIGNAL_CHECK.json').read_text())
    print('checkpoint', chk)
    print(p.to_string(index=False))


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument('--runner',required=True)
    ap.add_argument('--execution',required=True)
    ap.add_argument('--results')
    args=ap.parse_args()
    rp=Path(args.runner); ep=Path(args.execution)
    assert_source_contract(rp,ep)
    runner=load(rp,'tn_runner'); execmod=load(ep,'tn_exec')
    test_monthly_label(runner)
    test_rank_each_seed_semantics()
    test_tit_r_margin(execmod)
    if args.results:
        validate_results(Path(args.results))
    print('ALL_TITANIUM_TRAINING_NATIVE_CONTRACT_TESTS_PASS')


if __name__=='__main__':
    main()
