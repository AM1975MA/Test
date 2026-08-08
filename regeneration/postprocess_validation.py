#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PERIODS = {
    'D1_2017_2019': ('2017-02-01', '2019-12-31'),
    'D2_2020_2022': ('2020-01-01', '2022-12-31'),
    'DEVELOPMENT_2017_2022': ('2017-02-01', '2022-12-31'),
    'HOLDOUT_2023_2026': ('2023-01-01', '2099-12-31'),
    'FULL': ('1900-01-01', '2099-12-31'),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def path_metrics(eq: np.ndarray, dates: pd.DatetimeIndex, start: str, end: str) -> dict:
    mask = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
    if mask.sum() < 2:
        return {'cagr': np.nan, 'maxdd': np.nan, 'sharpe': np.nan, 'final_equity': np.nan, 'n_days': int(mask.sum())}
    x = np.asarray(eq[mask], float)
    d = dates[mask]
    valid = np.isfinite(x) & (x > 0)
    if valid.sum() < 2:
        return {'cagr': np.nan, 'maxdd': np.nan, 'sharpe': np.nan, 'final_equity': np.nan, 'n_days': int(mask.sum())}
    first = int(np.flatnonzero(valid)[0]); last = int(np.flatnonzero(valid)[-1])
    x = x[first:last+1]; d = d[first:last+1]
    x = x / x[0]
    years = max((d[-1] - d[0]).days / 365.25, 1 / 365.25)
    cagr = x[-1] ** (1 / years) - 1
    dd = x / np.maximum.accumulate(x) - 1
    r = x[1:] / x[:-1] - 1
    sd = np.nanstd(r)
    sharpe = np.sqrt(252) * np.nanmean(r) / sd if sd > 0 else np.nan
    return {'cagr': float(cagr), 'maxdd': float(np.nanmin(dd)), 'sharpe': float(sharpe), 'final_equity': float(x[-1]), 'n_days': int(len(x))}


def read_equity(path: Path) -> tuple[pd.DatetimeIndex, np.ndarray]:
    x = pd.read_csv(path)
    date_col = x.columns[0]
    value_col = 'equity' if 'equity' in x.columns else x.columns[-1]
    return pd.DatetimeIndex(pd.to_datetime(x[date_col])), pd.to_numeric(x[value_col], errors='coerce').to_numpy(float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--package-dir', required=True)
    ap.add_argument('--mode', required=True)
    ap.add_argument('--zip-parent', default='.')
    args = ap.parse_args()
    root = Path(args.package_dir).resolve()
    back = root / 'backtest'
    panels = root / 'panels'

    paths = np.load(panels / 'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz', allow_pickle=False)
    dates = pd.DatetimeIndex(pd.to_datetime(paths['dates']))
    arrays = {s: np.asarray(paths[s], float) for s in ['BASE', 'DIRECT', 'ROUTER']}

    rows = []
    for period, (start, end) in PERIODS.items():
        for strategy, matrix in arrays.items():
            for basket in range(matrix.shape[0]):
                row = {'period': period, 'strategy': strategy, 'basket': basket}
                row.update(path_metrics(matrix[basket], dates, start, end))
                rows.append(row)
    period_metrics = pd.DataFrame(rows)
    period_metrics.to_csv(back / 'BASKET_PERIOD_METRICS.csv', index=False)

    summary_rows = []
    for (period, strategy), g in period_metrics.groupby(['period', 'strategy']):
        c = g.cagr.dropna()
        summary_rows.append({
            'period': period, 'strategy': strategy, 'n_baskets': int(len(c)),
            'mean_cagr': float(c.mean()), 'median_cagr': float(c.median()),
            'std_cagr': float(c.std(ddof=0)), 'min_cagr': float(c.min()),
            'p01_cagr': float(c.quantile(.01)), 'p05_cagr': float(c.quantile(.05)),
            'p10_cagr': float(c.quantile(.10)), 'p25_cagr': float(c.quantile(.25)),
            'p75_cagr': float(c.quantile(.75)), 'p90_cagr': float(c.quantile(.90)),
            'p95_cagr': float(c.quantile(.95)), 'p99_cagr': float(c.quantile(.99)),
            'max_cagr': float(c.max()), 'mean_maxdd': float(g.maxdd.mean()),
            'median_maxdd': float(g.maxdd.median()), 'mean_sharpe': float(g.sharpe.mean()),
            'median_sharpe': float(g.sharpe.median()), 'positive_cagr_rate': float((c > 0).mean()),
        })
    distribution = pd.DataFrame(summary_rows)
    distribution.to_csv(back / 'BASKET_PERIOD_DISTRIBUTION.csv', index=False)

    paired_rows = []
    for period in PERIODS:
        q = period_metrics[period_metrics.period == period].pivot(index='basket', columns='strategy', values=['cagr','maxdd','sharpe'])
        for candidate in ['DIRECT', 'ROUTER']:
            dc = q[('cagr', candidate)] - q[('cagr', 'BASE')]
            ds = q[('sharpe', candidate)] - q[('sharpe', 'BASE')]
            dd = q[('maxdd', candidate)] - q[('maxdd', 'BASE')]
            paired_rows.append({
                'period': period, 'candidate': candidate,
                'mean_cagr_delta': float(dc.mean()), 'median_cagr_delta': float(dc.median()),
                'cagr_win_rate': float((dc > 0).mean()),
                'mean_sharpe_delta': float(ds.mean()), 'sharpe_win_rate': float((ds > 0).mean()),
                'mean_maxdd_delta': float(dd.mean()), 'maxdd_improvement_rate': float((dd > 0).mean()),
            })
    paired = pd.DataFrame(paired_rows)
    paired.to_csv(back / 'PAIRED_PERIOD_DELTAS.csv', index=False)

    global_rows = []
    for strategy in ['BASE', 'DIRECT', 'ROUTER']:
        gd, geq = read_equity(back / f'GLOBAL_{strategy}_EQUITY.csv')
        for period, (start, end) in PERIODS.items():
            row = {'period': period, 'strategy': strategy}
            row.update(path_metrics(geq, gd, start, end))
            global_rows.append(row)
    global_period = pd.DataFrame(global_rows)
    global_period.to_csv(back / 'GLOBAL_PERIOD_METRICS.csv', index=False)

    full_router = period_metrics.query("period == 'FULL' and strategy == 'ROUTER'").cagr.dropna() * 100
    plt.figure(figsize=(10, 6))
    plt.hist(full_router, bins=30, edgecolor='black')
    plt.axvline(full_router.mean(), label=f'Media {full_router.mean():.2f}%')
    plt.axvline(full_router.median(), label=f'Mediana {full_router.median():.2f}%')
    plt.xlabel('CAGR (%)')
    plt.ylabel('Numero di panieri')
    plt.title(f'Titanium Router — distribuzione CAGR 500 panieri ({args.mode})')
    plt.legend()
    plt.tight_layout()
    plt.savefig(back / 'CAGR_500_BASKETS_VALIDATED.png', dpi=180)
    plt.close()

    exact = args.mode == 'zero_std'
    dev = distribution.query("period == 'DEVELOPMENT_2017_2022'").set_index('strategy')
    hold = distribution.query("period == 'HOLDOUT_2023_2026'").set_index('strategy')
    full = distribution.query("period == 'FULL'").set_index('strategy')
    validation = {
        'downvol_mode': args.mode,
        'source_faithful_downvol': exact,
        'selection_policy': 'Exact zero_std is the source-faithful package. Challenger variants require improvement in both Development and Holdout before promotion.',
        'router_mean_cagr': {
            'development': float(dev.loc['ROUTER','mean_cagr']),
            'holdout': float(hold.loc['ROUTER','mean_cagr']),
            'full': float(full.loc['ROUTER','mean_cagr']),
        },
        'base_mean_cagr': {
            'development': float(dev.loc['BASE','mean_cagr']),
            'holdout': float(hold.loc['BASE','mean_cagr']),
            'full': float(full.loc['BASE','mean_cagr']),
        },
        'global_router': global_period.query("strategy == 'ROUTER'").set_index('period')[['cagr','maxdd','sharpe']].to_dict('index'),
    }
    (back / 'VALIDATION_SUMMARY.json').write_text(json.dumps(validation, indent=2))

    req = '\n'.join([
        'numpy==2.3.5','pandas==2.2.3','scipy==1.17.0','scikit-learn==1.8.0',
        'xgboost==3.1.3','joblib==1.5.3','pyarrow>=18','matplotlib>=3.8','numba>=0.60',''
    ])
    (root / 'requirements.txt').write_text(req)

    report = f"""# Validation report — {args.mode}

- Source-faithful downside volatility: **{exact}**
- OOS dates: {dates[0].date()} — {dates[-1].date()}
- Baskets: {arrays['ROUTER'].shape[0]}

## Mean CAGR over 500 baskets

| Period | Base | Direct | Router |
|---|---:|---:|---:|
"""
    for period in PERIODS:
        z = distribution[distribution.period == period].set_index('strategy')
        report += f"| {period} | {z.loc['BASE','mean_cagr']:.3%} | {z.loc['DIRECT','mean_cagr']:.3%} | {z.loc['ROUTER','mean_cagr']:.3%} |\n"
    report += "\n## Unrestricted universe\n\n| Period | Base CAGR | Direct CAGR | Router CAGR | Router MaxDD | Router Sharpe |\n|---|---:|---:|---:|---:|---:|\n"
    for period in PERIODS:
        z = global_period[global_period.period == period].set_index('strategy')
        report += f"| {period} | {z.loc['BASE','cagr']:.3%} | {z.loc['DIRECT','cagr']:.3%} | {z.loc['ROUTER','cagr']:.3%} | {z.loc['ROUTER','maxdd']:.3%} | {z.loc['ROUTER','sharpe']:.3f} |\n"
    (back / 'VALIDATION_REPORT.md').write_text(report)
    with (root / 'README.md').open('a') as f:
        f.write('\n\n' + report)

    excluded = {'manifest/SHA256SUMS_POSTPROCESSED.txt', 'manifest/PACKAGE_MANIFEST_POSTPROCESSED.json'}
    files = []
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and rel not in excluded:
            files.append({'path': rel, 'size': p.stat().st_size, 'sha256': sha256(p)})
    manifest = {'package': root.name, 'downvol_mode': args.mode, 'postprocessed': True, 'validation': validation, 'files': files}
    manifest_path = root / 'manifest' / 'PACKAGE_MANIFEST_POSTPROCESSED.json'
    manifest_path.write_text(json.dumps(manifest, indent=2))
    sums = root / 'manifest' / 'SHA256SUMS_POSTPROCESSED.txt'
    with sums.open('w') as f:
        for row in files:
            f.write(f"{row['sha256']}  {row['path']}\n")
        f.write(f"{sha256(manifest_path)}  manifest/PACKAGE_MANIFEST_POSTPROCESSED.json\n")

    zip_parent = Path(args.zip_parent).resolve()
    zip_path = zip_parent / f'{root.name}.zip'
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix('')), 'zip', root.parent, root.name)
    (zip_parent / f'{root.name}.sha256').write_text(f'{sha256(zip_path)}  {zip_path.name}\n')
    print(report)
    print(json.dumps({'zip': str(zip_path), 'sha256': sha256(zip_path), 'validation': validation}, indent=2))


if __name__ == '__main__':
    main()
