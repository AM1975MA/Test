"""Independent OLC110 price features and frozen OLC109 selector.

Adapted from OLC109 validation/signal_reference.py (independent_features,
percentiles, stage2_target_from_data) and account_reference.py (prepare_panel).
No production engine, selector, feature, policy, or account core is imported.
The efficient percentile implementation below is algebraically the average
rank definition; the production rankdata implementation is not reused.
"""
from __future__ import annotations

from functools import lru_cache
import numpy as np
import pandas as pd

ARMS = ('BASE', 'STATIC_HALF', 'STATIC_75', 'REFRESH_WEEKLY',
        'EXIT21_MONTHLY', 'EXIT21_SLOW', 'EXIT21_FAST', 'EXIT21_STAGED',
        'EXIT63_STAGED', 'TRAIL15_STAGED', 'VOLTRAIL_STAGED',
        'EXIT21_STAGED_FRESHW', 'EXIT21_STAGED_FRESHD')
SCENARIOS = {'BASE': (1., .0015, 0, 'OPEN'), 'ZERO_COST': (0., 0., 0, 'OPEN'),
             'DOUBLE_COST': (2., .003, 0, 'OPEN'), 'LAG1': (1., .0015, 1, 'OPEN'),
             'LAG2': (1., .0015, 2, 'OPEN'), 'NEXT_CLOSE': (1., .0015, 0, 'CLOSE')}


def prepare_panel(panel):
    dates = pd.DatetimeIndex(panel['dates'])
    names = np.asarray(panel['names']).astype(str)
    assert dates.is_monotonic_increasing and not dates.has_duplicates
    assert len(names) == len(set(names)), 'DUPLICATE_ISIN'
    close_observed = np.asarray(panel['observed'], bool)
    opening_observed = np.asarray(panel.get('open_observed', panel['observed']), bool)
    raw_open, raw_close = np.asarray(panel['O'], float), np.asarray(panel['C'], float)
    assert close_observed.shape == opening_observed.shape == raw_open.shape == raw_close.shape == (len(dates), len(names))
    valid_open = opening_observed & np.isfinite(raw_open) & (raw_open > 0)
    valid_close = close_observed & np.isfinite(raw_close) & (raw_close > 0)
    close = pd.DataFrame(np.where(valid_close, raw_close, np.nan)).ffill().to_numpy()
    with np.errstate(invalid='ignore', divide='ignore'):
        returns = np.vstack((np.full((1, len(names)), np.nan), np.log(close[1:] / close[:-1])))
    return dict(dates=dates, names=names, observed=close_observed,
                raw_open=raw_open, raw_close=raw_close,
                valid_open=valid_open, valid_close=valid_close, C=close, returns=returns)


def prepare_features(p, turnover):
    c = pd.DataFrame(p['C'])
    obs, dates, ret = p['observed'], p['dates'], p['returns']
    out = {'C': p['C'], 'returns': ret}
    for horizon in (5, 21, 63, 126, 252):
        out[f'm{horizon}'] = np.log(c / c.shift(horizon)).to_numpy()
    for horizon in (10, 21, 63, 200):
        out[f'sma{horizon}'] = c.rolling(horizon, min_periods=horizon).mean().to_numpy()
    out['peak63'] = c.rolling(63, min_periods=63).max().to_numpy()
    out['high5_prev'] = c.shift(1).rolling(5, min_periods=5).max().to_numpy()
    out['sigma21'] = pd.DataFrame(ret).rolling(21, min_periods=21).std(ddof=1).to_numpy()
    vol = np.maximum(pd.DataFrame(ret).rolling(63, min_periods=50).std(ddof=1).to_numpy() * np.sqrt(252), .01)
    out['b21'] = out['m21']
    out['a21'] = np.log(c.shift(21) / c.shift(126)).to_numpy() / 5
    out['accel21'] = out['b21'] - out['a21']
    last = np.maximum.accumulate(np.where(obs, np.arange(len(c))[:, None], -1), axis=0)
    days = dates.to_numpy().astype('datetime64[D]').astype(np.int64)
    age = days[:, None] - days[np.maximum(last, 0)]
    recent = pd.DataFrame(obs.astype(int)).rolling(253, min_periods=253).sum().to_numpy()
    score = (4 * out['m63'] + 2 * out['m126'] + out['m252']) / (3 * vol)
    eligible = (recent >= 241) & (obs.cumsum(axis=0) >= 253) & (age <= 5) & np.isfinite(score)
    turnover = np.asarray(turnover)
    assert turnover.shape == c.shape and np.isfinite(turnover).all() and turnover.min() >= 0
    observed_turnover = np.where(obs, turnover, 0.)
    out['adv63'] = pd.DataFrame(observed_turnover).rolling(63, min_periods=63).median().to_numpy()
    out['liquid'] = eligible & obs & (out['adv63'] >= 100000)
    return out


def calendars(dates):
    dates = pd.DatetimeIndex(dates)
    month, week = np.zeros(len(dates), bool), np.zeros(len(dates), bool)
    for k in range(len(dates) - 1):
        month[k] = (dates[k].year, dates[k].month) != (dates[k+1].year, dates[k+1].month)
        week[k] = dates[k].isocalendar()[:2] != dates[k+1].isocalendar()[:2]
    return month, week


def percentile(values):
    values = np.asarray(values, float)
    assert np.isfinite(values).all()
    if not len(values):
        return np.zeros(0)
    _, inverse, count = np.unique(values, return_inverse=True, return_counts=True)
    below = np.r_[0, np.cumsum(count)[:-1]]
    return (below[inverse] + (count[inverse] + 1) / 2) / len(values)


class SelectorReference:
    """Share only immutable price-derived caches across account scenarios."""
    def __init__(self, prepared, features):
        self.p, self.f = prepared, features
        self.names = prepared['names']
        self.n = len(self.names)
        self.monthly, self.weekly = calendars(prepared['dates'])

    @lru_cache(maxsize=None)
    def correlation(self, k, a, b):
        if a == b:
            return 1.
        data = self.f['returns'][k-125:k+1, [a, b]]
        assert data.shape == (126, 2) and np.isfinite(data).all(), ('CORRELATION_HISTORY', k, a, b)
        centered = data - data.mean(axis=0)
        denominator = np.linalg.norm(centered, axis=0).prod()
        return 0. if denominator <= 1e-14 else float(np.corrcoef(data, rowvar=False)[0, 1])

    @lru_cache(maxsize=None)
    def opportunity_pool(self, k, entry_confirmation=False):
        f = self.f
        ids = np.flatnonzero(f['liquid'][k])
        rb, ra = percentile(f['b21'][k, ids]), percentile(f['a21'][k, ids])
        result = []
        for i, j in enumerate(ids):
            if not (f['b21'][k,j] > 0 and rb[i] >= 2/3 and ra[i] < 2/3
                    and f['accel21'][k,j] > 0 and f['C'][k,j] > f['sma63'][k,j]
                    and f['m252'][k,j] > 0 and f['m63'][k,j] > 0 and f['C'][k,j] > f['sma200'][k,j]):
                continue
            if entry_confirmation and not (f['C'][k,j] > f['sma10'][k,j] and f['m5'][k,j] > 0):
                continue
            result.append(int(j))
        result.sort(key=lambda j: (-float(f['accel21'][k,j]), str(self.names[j])))
        return tuple(result)

    @lru_cache(maxsize=None)
    def selection(self, k):
        f = self.f
        ids = np.flatnonzero(f['liquid'][k])
        ranking = sorted(ids, key=lambda j: (-float(f['m252'][k,j]), str(self.names[j])))
        leaders = []
        for j in ranking:
            if not leaders or self.correlation(k, int(j), leaders[0]) <= .85 + 1e-12:
                leaders.append(int(j))
                if len(leaders) == 2:
                    break
        eligible_opportunities = [j for j in self.opportunity_pool(k) if j not in leaders]
        chosen, challenger, used = list(leaders), None, False
        if len(leaders) == 2:
            for j in eligible_opportunities:
                if self.correlation(k, j, leaders[0]) <= .85 + 1e-12:
                    challenger = j
                    if f['b21'][k,j] > f['b21'][k,leaders[1]]:
                        chosen[1], used = j, True
                    break
        weights = np.zeros(self.n)
        weights[chosen] = .5
        metadata = dict(arm='DEDUP_DUAL_TREND_OPP', leader_indices=leaders,
                        selected_indices=chosen, selected_names=[str(self.names[j]) for j in chosen],
                        invested_indices=np.flatnonzero(weights > 0).tolist(),
                        opportunity_used=used, challenger_available=bool(eligible_opportunities),
                        challenger=challenger, eligible_count=int(len(ids)),
                        selected_pair_correlation=self.correlation(k, *chosen) if len(chosen) == 2 else None)
        weights.setflags(write=False)
        return weights, metadata
