"""Read-only attribution of archived annual LINEAR vs BASE; no fitting."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '_evidence/listnet-linear-relative-repair/_replays'
OUT = ROOT / 'paper_ltr_monthly_v1/results/annual_diagnosis'

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    hashes = {}
    daily = []
    for repeat in (1, 2, 3):
        folder = SOURCE / f'v2replay-LINEAR_NUMERICAL_REPAIR-r{repeat}'
        frames = {}
        for side in ('candidate', 'baseline_control'):
            p = folder / side / 'FULL_UNIVERSE_PATH.npz'
            leaders_path = folder / side / 'DAILY_LEADERS.csv'
            for file in (p, leaders_path):
                hashes[str(file.relative_to(ROOT))] = hashlib.sha256(file.read_bytes()).hexdigest()
            with np.load(p, allow_pickle=False) as z:
                dates = pd.DatetimeIndex(z['dates'])
                equity = z['equity'][0]
                assert dates.is_monotonic_increasing and not dates.has_duplicates
                assert np.isfinite(equity).all() and (equity > 0).all()
                f = pd.DataFrame({'date': dates, 'log_return': np.diff(np.r_[0., np.log(equity)])})
                for field in ('weight1', 'turnover', 'margin', 'alt_idx'):
                    f[field] = z[field][0]
                assert abs(f.log_return.sum() - np.log(equity[-1])) < 1e-12
            leaders = pd.read_csv(leaders_path, parse_dates=['date'])
            f = f.merge(leaders, on='date', validate='one_to_one')
            assert len(f) == len(dates)
            frames[side] = f.set_index('date')
        a, b = frames['candidate'], frames['baseline_control']
        assert a.index.equals(b.index)
        f = pd.DataFrame({'date': a.index, 'download': repeat,
                          'linear_log': a.log_return.to_numpy(),
                          'base_log': b.log_return.to_numpy(),
                          'same_top1': (a.top1 == b.top1).to_numpy(),
                          'same_ordered_pair': ((a.top1 == b.top1) & (a.top2 == b.top2)).to_numpy()})
        f['gap_log'] = f.linear_log - f.base_log
        for prefix, source in (('linear', a), ('base', b)):
            for field in ('top1', 'top2', 'weight1', 'turnover', 'margin', 'alt_idx'):
                f[f'{prefix}_{field}'] = source[field].to_numpy()
        daily.append(f)
    d = pd.concat(daily, ignore_index=True)
    d['year'] = d.date.dt.year
    d['month'] = d.date.dt.strftime('%Y-%m')
    monthly = []
    annual = []
    buckets = []
    selections = []
    for (repeat, year), g in d.groupby(['download', 'year']):
        lin, base = np.expm1(g.linear_log.sum()), np.expm1(g.base_log.sum())
        annual.append(dict(download=int(repeat), year=int(year), linear_return=float(lin), base_return=float(base),
                           gap_return_pp=float(100 * (lin-base)), gap_log=float(g.gap_log.sum()),
                           same_ordered_pair_share=float(g.same_ordered_pair.mean()),
                           linear_mean_weight1=float(g.linear_weight1.mean()), base_mean_weight1=float(g.base_weight1.mean()),
                           linear_turnover_sum=float(g.linear_turnover.sum()), base_turnover_sum=float(g.base_turnover.sum())))
        subtotal = 0.
        for same, bucket in g.groupby('same_ordered_pair'):
            value = float(bucket.gap_log.sum()); subtotal += value
            buckets.append(dict(download=int(repeat), year=int(year), same_ordered_pair=bool(same), days=len(bucket), gap_log=value))
        assert abs(subtotal - g.gap_log.sum()) < 1e-12
        for model in ('linear', 'base'):
            for (top1, top2), bucket in g.groupby([f'{model}_top1', f'{model}_top2']):
                selections.append(dict(download=int(repeat), year=int(year), model=model, top1=top1, top2=top2,
                                       days=len(bucket), portfolio_log_return_sum=float(bucket[f'{model}_log'].sum())))
    for (repeat, month), g in d.groupby(['download', 'month']):
        monthly.append(dict(download=int(repeat), month=month,
                            linear_return=float(np.expm1(g.linear_log.sum())), base_return=float(np.expm1(g.base_log.sum())),
                            gap_log=float(g.gap_log.sum()), same_pair_share=float(g.same_ordered_pair.mean()),
                            linear_pairs=';'.join(sorted(set(g.linear_top1 + '/' + g.linear_top2))),
                            base_pairs=';'.join(sorted(set(g.base_top1 + '/' + g.base_top2)))))
    annual = pd.DataFrame(annual)
    chart = pd.read_csv(ROOT / 'paper_ltr_monthly_v1/results/charts/ANNUAL_RETURNS_3_DOWNLOADS.csv')
    errors = []
    for row in annual.itertuples():
        for strategy, value in [('BASE', row.base_return), ('LINEAR annuale', row.linear_return)]:
            expected = chart[(chart.strategy == strategy) & (chart.download == row.download) & (chart.year == row.year)].net_return
            assert len(expected) == 1
            errors.append(abs(value - expected.iloc[0]))
    assert max(errors) < 1e-12
    for name, table in [('ANNUAL', annual), ('MONTHLY', pd.DataFrame(monthly)), ('AGREEMENT_ATTRIBUTION', pd.DataFrame(buckets)), ('SELECTION_DAYS', pd.DataFrame(selections))]:
        table.to_csv(OUT / (name + '.csv'), index=False)
    evidence = dict(source_sha256=hashes, source='Verified annual frozen replay; no new fits or replays',
                    max_error_against_published_annual_returns=float(max(errors)),
                    gap_decomposition='Additive log wealth difference, not causal attribution or percentage-point contribution',
                    limitations=['Top1/Top2 are allocation signals, not complete executed daily holdings',
                                 'weight1 is not total risky exposure',
                                 'No gross exposure or executed-risk ledger retained in NPZ',
                                 'The three downloads are correlated revisions, not independent samples'])
    (OUT / 'PROVENANCE.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(annual[annual.year.isin([2021, 2023])].to_string(index=False))
    m = pd.DataFrame(monthly); m['year'] = m.month.str[:4].astype(int)
    print('\nMean monthly gaps, log points:')
    print((m[m.year.isin([2021, 2023])].groupby('month')[['linear_return','base_return','gap_log']].mean() * 100).round(3).to_string())
    print('\nReconciliation maximum error:', max(errors))

if __name__ == '__main__':
    main()
