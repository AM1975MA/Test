#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRanker


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def exact_rolling_downvol(lr: pd.DataFrame, h: int) -> pd.DataFrame:
    neg = lr.where(lr < 0, 0.0)
    return np.sqrt(neg.pow(2).rolling(h, min_periods=h).mean() * 252)


def exact_rolling_gkvol(O, H, L, C, h):
    rs = 0.5 * np.log(H / L).pow(2) - (2 * np.log(2) - 1) * np.log(C / O).pow(2)
    rs = rs.clip(lower=0)
    return np.sqrt(rs.rolling(h, min_periods=h).mean() * 252)


def exact_compact(base, mats, dates):
    O, H, L, C, V = [mats[k] for k in ['Open', 'High', 'Low', 'Close', 'Volume']]
    logc = np.log(C.where(C > 0))
    lr = logc.diff()
    ret = C.pct_change(fill_method=None)
    market = ret.mean(axis=1, skipna=True)
    out = {}
    for h in [5, 10, 21, 42, 63, 126, 252]:
        out[f'mom{h}'] = base.snapshot(C.pct_change(h, fill_method=None), dates)
    for h in [21, 63, 126]:
        # Exact July-27 source: pandas std default ddof=1.
        out[f'vol{h}'] = base.snapshot(lr.rolling(h, min_periods=h).std() * np.sqrt(252), dates)
        out[f'downvol{h}'] = base.snapshot(exact_rolling_downvol(lr, h), dates)
        out[f'drawdown{h}'] = base.snapshot(C / C.rolling(h, min_periods=h).max() - 1, dates)
        out[f'efficiency{h}'] = base.snapshot(base.rolling_efficiency(logc, h), dates)
    out['mom126_ex21'] = base.snapshot(C.shift(21) / C.shift(126) - 1, dates)
    out['mom252_ex21'] = base.snapshot(C.shift(21) / C.shift(252) - 1, dates)
    out['acc_mom_5_21'] = out['mom5'] - (5 / 21) * out['mom21']
    out['acc_mom_21_63'] = out['mom21'] - (21 / 63) * out['mom63']
    out['vol_ratio_21_126'] = out['vol21'] / out['vol126']
    out['skew63'] = base.snapshot(lr.rolling(63, min_periods=63).skew(), dates)
    out['kurt63'] = base.snapshot(lr.rolling(63, min_periods=63).kurt(), dates)
    out['gkvol21'] = base.snapshot(exact_rolling_gkvol(O, H, L, C, 21), dates)
    dollar = V * C
    out['log_adv63'] = base.snapshot(np.log1p(dollar.rolling(63, min_periods=63).mean()), dates)
    lv = np.log1p(V)
    out['volume_surprise21'] = base.snapshot(
        (lv - lv.rolling(21, min_periods=21).mean()) /
        lv.rolling(21, min_periods=21).std().replace(0, np.nan), dates
    )
    for h in [63, 126]:
        cov = ret.rolling(h, min_periods=h).cov(market)
        var = market.rolling(h, min_periods=h).var()
        out[f'beta_mkt{h}'] = base.snapshot(cov.div(var, axis=0), dates)
        out[f'corr_mkt{h}'] = base.snapshot(ret.rolling(h, min_periods=h).corr(market), dates)

    # Exact Compact extras from July-27 source.
    out['ma_gap50'] = base.snapshot(C / C.rolling(50, min_periods=50).mean() - 1, dates)
    out['ma_gap200'] = base.snapshot(C / C.rolling(200, min_periods=200).mean() - 1, dates)
    out['ema_gap20'] = base.snapshot(C / C.ewm(span=20, adjust=False, min_periods=20).mean() - 1, dates)
    out['ema_gap50'] = base.snapshot(C / C.ewm(span=50, adjust=False, min_periods=50).mean() - 1, dates)
    for h in [126, 252]:
        lo = C.rolling(h, min_periods=h).min()
        hi = C.rolling(h, min_periods=h).max()
        out[f'breakout_pos{h}'] = base.snapshot((C - lo) / (hi - lo).replace(0, np.nan), dates)
    out['rsi14'] = base.snapshot(base.rolling_rsi(C, 14), dates)
    out['positive_frac63'] = base.snapshot((ret > 0).rolling(63, min_periods=63).mean(), dates)
    out['max_loss63'] = base.snapshot(ret.rolling(63, min_periods=63).min(), dates)
    out['max_gain63'] = base.snapshot(ret.rolling(63, min_periods=63).max(), dates)
    out['cvar10_63'] = base.snapshot(base.rolling_cvar10(ret, 63), dates)
    out['sign_entropy63'] = base.snapshot(base.rolling_sign_entropy(ret, 63), dates)
    out['autocorr1_63'] = base.snapshot(base.rolling_autocorr(ret, 63), dates)

    for name in list(out):
        if name + '_pct' in base.F2D_FEATURES:
            out[name + '_pct'] = base.cs_pct(out[name])
        if name + '_dev' in base.F2D_FEATURES:
            out[name + '_dev'] = base.cs_robust_dev(out[name])
    for n in base.F2D_FEATURES:
        if n not in out:
            out[n] = pd.DataFrame(np.nan, index=dates, columns=C.columns)
    long = pd.concat(
        [out[n].stack(dropna=False).rename(n) for n in base.F2D_FEATURES], axis=1
    ).reset_index().rename(columns={'level_0': 'signal_date', 'level_1': 'ticker'})
    return long, out


def source_faithful_fit(v6, base, compact, tail, macro, macro_feats, years, n_estimators=360):
    params = dict(base.COMPACT_PARAMS)
    params['n_estimators'] = n_estimators
    params['n_jobs'] = 2
    pred_rows, macro_rows, audit = [], [], []
    for year in years:
        cutoff = pd.Timestamp(year, 1, 1)
        # Exact source: maturity is exit_date < cutoff and NO cvalid filter.
        tr = compact[
            (compact.signal_date < cutoff)
            & (compact.exit_date < cutoff)
            & compact.target_rank_pct.notna()
        ].sort_values(['signal_date', 'ticker'])
        te = compact[compact.signal_date.dt.year == year].sort_values(['signal_date', 'ticker'])
        if tr.signal_date.nunique() < 60 or te.empty:
            continue
        groups = tr.groupby('signal_date', sort=True).size().tolist()
        y = (tr.target_rank_pct * 100).round().astype(int)
        cps = []
        for seed in [101, 202, 303]:
            model = XGBRanker(**params, random_state=seed)
            model.fit(
                tr[base.F2D_FEATURES].replace([np.inf, -np.inf], np.nan),
                y, group=groups, verbose=False,
            )
            cps.append(model.predict(te[base.F2D_FEATURES].replace([np.inf, -np.inf], np.nan)))
        out = te[['signal_date', 'ticker']].copy()
        out['compact_raw'] = np.mean(cps, axis=0)

        # Exact source: no tvalid filter.
        ttr = tail[
            (tail.signal_date < cutoff)
            & (tail.exit_date_63 < cutoff)
            & tail.y_tailmix.notna()
        ]
        tte = tail[tail.signal_date.dt.year == year]
        tm = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), Ridge(alpha=30.0))
        tm.fit(ttr[base.TAIL_FEATURES], ttr.y_tailmix)
        tp = tte[['signal_date', 'ticker']].copy()
        tp['tail_raw'] = tm.predict(tte[base.TAIL_FEATURES])
        pred_rows.append(out.merge(tp, on=['signal_date', 'ticker'], how='left'))

        # July-27 embedded/source engine: macro maturity uses cutoff - 70 days.
        mtr = macro[(macro.signal_date < cutoff - pd.Timedelta(days=70)) & macro.target_rank.notna()]
        mte = macro[macro.signal_date.dt.year == year]
        if len(mtr) > 50 and len(mte):
            mm = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), Ridge(alpha=50.0))
            mm.fit(mtr[macro_feats], mtr.target_rank)
            q = mte[['signal_date', 'macro_category']].copy()
            q['macro_raw'] = mm.predict(mte[macro_feats])
            macro_rows.append(q)
        audit.append({
            'year': year,
            'compact_train_dates': int(tr.signal_date.nunique()),
            'compact_train_rows': int(len(tr)),
            'compact_test_rows': int(len(te)),
            'tail_train_rows': int(len(ttr)),
            'tail_test_rows': int(len(tte)),
            'macro_train_rows': int(len(mtr)),
        })

    p = pd.concat(pred_rows, ignore_index=True)
    p['compact_rank'] = p.groupby('signal_date').compact_raw.rank(pct=True)
    p['tail_rank'] = p.groupby('signal_date').tail_raw.rank(pct=True)
    p['titanium_score_pre_macro'] = .70 * p.compact_rank + .30 * p.tail_rank
    mp = pd.concat(macro_rows, ignore_index=True)
    mp['macro_z'] = mp.groupby('signal_date').macro_raw.transform(
        lambda x: (x - x.mean()) / (x.std(ddof=0) + 1e-12)
    )
    tops = []
    for dt, g in mp.groupby('signal_date'):
        g = g.sort_values('macro_z', ascending=False)
        tops.append({
            'signal_date': dt,
            'top_macro': g.iloc[0].macro_category,
            'macro_gap_z': float(g.iloc[0].macro_z - g.iloc[1].macro_z) if len(g) > 1 else 0.0,
        })
    p['macro_category'] = p.ticker.map(base.TICKER_CATEGORY)
    p = p.merge(pd.DataFrame(tops), on='signal_date', how='left')
    p['macro_bonus'] = np.where(
        (p.macro_category == p.top_macro) & (p.macro_gap_z >= .75) & (p.tail_rank >= .80),
        .15, 0.0,
    )
    p['titanium_score'] = p.titanium_score_pre_macro + p.macro_bonus
    return p.sort_values(['signal_date', 'ticker']), pd.DataFrame(audit), mp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', required=True)
    ap.add_argument('--output', default='BASE_PARITY_PROBE')
    ap.add_argument('--trees', type=int, default=360)
    args = ap.parse_args()
    pkg = Path(args.package).resolve()
    outdir = Path(args.output).resolve()
    shutil.rmtree(outdir, ignore_errors=True)
    outdir.mkdir(parents=True)
    t0 = time.time()

    base = load_module('meteor_base_probe', pkg / 'source' / 'titanium_retrained_current_data_audit.py')
    v6 = load_module('meteor_v6_probe', pkg / 'source' / 'titanium_reconstruction_v6.py')
    mats = v6.load_mats(pkg / 'data')

    # Reuse broad/Tail dictionaries only for this staged probe; Compact is rebuilt exactly.
    dates, _oldcompact, _tail0, D = base.build_features(mats)
    compact, compact_frames = exact_compact(base, mats, dates)
    compact = base.add_labels(compact, mats['Open'], dates)
    D = v6.enhance_feature_dictionary(base, mats, dates, D)
    tail = v6.rebuild_tail_long(base, D, dates, mats['Close'].columns)
    tail = base.add_labels(tail, mats['Open'], dates)
    macro, macro_feats = v6.build_macro_panel(base, D, compact, base.TICKER_CATEGORY)

    pred, fit_audit, macro_pred = source_faithful_fit(
        v6, base, compact, tail, macro, macro_feats, range(2017, 2027), args.trees
    )
    pred = pred[pred.signal_date >= v6.BACKTEST_START].copy()

    cal = pd.read_csv(pkg / 'panels' / 'MONTHLY_CALENDAR.csv', parse_dates=['signal_date','entry_date','exit_date'])
    cal = cal[cal.signal_date.isin(pred.signal_date.unique()) & cal.exit_date.notna()].reset_index(drop=True)
    clusters = pd.read_csv(pkg / 'panels' / 'DYNAMIC_CLUSTERS_MONTHLY.csv', parse_dates=['signal_date'])
    opp_pred = pd.read_csv(pkg / 'panels' / 'TITANIUM_V3_OPPORTUNITY_OOS_CLUSTER_PANEL.csv', parse_dates=['signal_date'])
    mem = pd.read_csv(pkg / 'panels' / 'BASKET_MEMBERSHIP_500.csv')
    baskets = [tuple(sorted(g.ticker.astype(str))) for _, g in mem.groupby('basket', sort=True)]

    idx, EB, ED, ER, active, margin, cond, *_ = v6.simulate_all(
        baskets, pred, opp_pred, clusters, mats, cal
    )
    rows = []
    for b in range(500):
        cagr, maxdd, sharpe, final_equity = v6.metrics(EB[b], idx)
        rows.append({'basket': b, 'cagr': cagr, 'maxdd': maxdd, 'sharpe': sharpe, 'final_equity': final_equity})
    res = pd.DataFrame(rows)
    res.to_csv(outdir / 'BASE_BASKET_RESULTS.csv', index=False)
    pred.to_parquet(outdir / 'OOS_TICKER_SCORES.parquet', index=False)
    fit_audit.to_csv(outdir / 'FIT_AUDIT.csv', index=False)

    checkpoint = pd.Timestamp('2026-06-30')
    chk = pred[pred.signal_date.eq(checkpoint)].sort_values('titanium_score', ascending=False).head(10)
    chk.to_csv(outdir / 'CHECKPOINT_20260630.csv', index=False)
    summary = {
        'stage': 'exact_compact_and_training_protocol__existing_broad_tail_macro',
        'trees': args.trees,
        'n_scored_tickers': int(pred.ticker.nunique()),
        'n_oos_months': int(pred.signal_date.nunique()),
        'base_mean_cagr': float(res.cagr.mean()),
        'base_median_cagr': float(res.cagr.median()),
        'base_median_maxdd': float(res.maxdd.median()),
        'frozen_base_mean_cagr': 0.21654064,
        'gap_pp': float((res.cagr.mean() - 0.21654064) * 100),
        'checkpoint_top1': str(chk.iloc[0].ticker) if len(chk) else None,
        'checkpoint_top2': str(chk.iloc[1].ticker) if len(chk) > 1 else None,
        'checkpoint_matches_USO_PALL': bool(len(chk) > 1 and chk.iloc[0].ticker == 'USO' and chk.iloc[1].ticker == 'PALL'),
        'macro_bonus_months': int(pred.groupby('signal_date').macro_bonus.max().gt(0).sum()),
        'elapsed_seconds': time.time() - t0,
    }
    (outdir / 'SUMMARY.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
