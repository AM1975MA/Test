"""Common-state timing labels using the U27 account and protection logic."""

from copy import deepcopy
from dataclasses import dataclass
import inspect

import numpy as np
import pandas as pd


def window_engine(original):
    """Add snapshot/resume points while reusing the original account arithmetic."""
    fields = ("units", "au", "bu", "su", "free", "at", "cd", "force_target",
              "lock_until", "pending_reentry", "tar", "executed", "previous_proposal",
              "last_cohort", "executed_f", "executed_aw", "last_i", "last_j", "last_sig",
              "remaining", "last_proposal_vector", "wait_remaining")
    args = ",".join(fields)
    source = inspect.getsource(original)

    def substitute(before, after):
        nonlocal source
        assert source.count(before) == 1, before
        source = source.replace(before, after)

    substitute("    for k in range(D):", f"""    left, right = q.get('_bounds', (0,D-1))
    if '_resume' in q:
        {args} = clone_state(q['_resume'])
    capture = q.get('_capture', {{}})
    for k in range(left, right+1):
        if k in capture:
            capture[k] = clone_state(({args}))
""")
    substitute("        if k==D-1:", "        if k==right:")
    substitute("    pgap=np.concatenate([gap[:1]*0,gap[:-1]])",
               "    pgap=q['_lagged_gap']")
    substitute("    obs=np.asarray(q.get('observed',np.ones_like(O,bool)),bool)",
               "    obs=q['observed']")
    substitute('        mode=int(q.get("risk_mode",np.zeros(D,int))[k])',
               '        mode=int(q["risk_mode"][k])')
    substitute("        cooldown_rule=int(q.get('cooldown_rule',np.zeros(D,int))[k])",
               "        cooldown_rule=int(q['cooldown_rule'][k])")
    namespace = dict(original.__globals__, clone_state=deepcopy)
    exec(compile(source, "<U27 timing labels>", "exec"), namespace)
    return namespace["simulate"]


@dataclass
class TrailState:
    blocked: np.ndarray
    peak: np.ndarray
    entry: np.ndarray
    previous: np.ndarray
    target: np.ndarray


class ProfitRamp:
    """Evaluate the U24 PROFIT_RAMP branch without rebuilding unrelated variants."""

    def __init__(self, q, benchmark):
        self.is_cash = np.array(["CASH_" in ticker for ticker in q["tickers"]])
        self.cash_id = np.flatnonzero(self.is_cash)[0]
        observed = q.get("low_observed", q.get("observed"))
        close = pd.DataFrame(q["C"])
        if observed is not None:
            close = close.where(observed)
        self.prev = close.shift(1).to_numpy()
        self.ret5 = (close / close.shift(5) - 1).shift(1).to_numpy()
        vol = np.log(close).diff().rolling(21, min_periods=18).std().shift(1).to_numpy()
        self.band = np.clip(2 * vol * np.sqrt(5), .08, .18)
        self.high10 = close.shift(2).rolling(10, min_periods=10).max().to_numpy()
        benchmark_idx = list(q["tickers"]).index(benchmark)
        ema21 = close[benchmark_idx].ewm(span=21, min_periods=21, adjust=False).mean().shift(1)
        recent = (self.prev[:, benchmark_idx] > ema21) & (self.ret5[:, benchmark_idx] > 0)
        self.recovery = recent.rolling(2, min_periods=2).sum().eq(2).to_numpy()

    def empty(self):
        size = len(self.is_cash)
        return TrailState(np.zeros(size, bool), *(np.zeros(size) for _ in range(4)))

    def step(self, state, k, weight):
        prev = self.prev[k]
        prior = state.previous
        present = (weight > 0) & ~self.is_cash
        fresh = present & (prior <= 0)
        valid = np.isfinite(prev)
        active = present & valid
        state.peak[~present] = state.entry[~present] = 0.
        state.blocked[~present] = False
        state.entry[fresh] = np.where(valid[fresh], prev[fresh], 0.)
        state.peak[fresh] = state.entry[fresh]
        state.blocked[fresh] = False
        state.peak[active] = np.maximum(state.peak[active], prev[active])
        band = self.band[k]
        hit = (active & ~state.blocked & (prev < state.peak * (1-band))
               & (state.entry > 0) & (state.peak >= state.entry * (1+band)))
        rebound = active & state.blocked & (prev > self.high10[k]) & (self.ret5[k] > 0)
        state.blocked[hit] = True
        state.blocked[rebound] = False
        state.entry[rebound] = state.peak[rebound] = prev[rebound]
        if k == 0 or k % 5 == 0 or np.max(abs(weight - prior)) > 1e-12:
            moved = weight * state.blocked
            state.target = weight - moved
            state.target[self.cash_id] += moved.sum()
        state.previous = weight
        ids = np.flatnonzero(weight > 0)
        changes = self.ret5[k, ids]
        gate = self.recovery[k] and len(ids) and np.isfinite(changes).all() and weight[ids] @ changes > 0
        return state.target, bool(gate)


def raw_weight(pair, weight, size):
    out = np.zeros(size)
    i, j = pair
    out[i] += 1. if i == j else weight
    if i != j:
        out[j] += 1 - weight
    return out


def baseline_signals(q, pair, features, capture):
    trail = features.empty()
    target = np.zeros_like(q["O"])
    gate = np.zeros(len(pair), bool)
    snapshots = {}
    for k, legs in enumerate(pair):
        if k in capture:
            snapshots[k] = deepcopy(trail)
        target[k], gate[k] = features.step(trail, k, raw_weight(legs, .5, target.shape[1]))
    return target, gate, snapshots


def make_labels(q, pair, corr, old_corr, controls, benchmark, engine, choices, bps):
    original_returns = controls[0]["PROFIT_RAMP"], controls[1]
    profit = ProfitRamp(q, benchmark)
    eligible = choices.loc[choices.changed & choices.label_end.notna()]
    event_indices = set(eligible["index"])
    target, gate, trail_snapshots = baseline_signals(q, pair, profit, event_indices)
    np.testing.assert_array_equal(target, original_returns[0])
    np.testing.assert_array_equal(gate, original_returns[1])
    snapshots = dict.fromkeys(event_indices)
    state = dict(q, observed=q.get("observed", np.ones_like(q["O"], bool)),
                 _lagged_gap=np.concatenate([q["gap"][:1]*0, q["gap"][:-1]]),
                 risk_mode=corr, recovery=gate, cooldown_rule=gate.astype(int)*2,
                 _capture=snapshots)
    args = dict(policy="IMMEDIATE", fee=0, stop_friction=0, exposure_timing="PREVIOUS",
                stop_timing="NOW", fast_stop=True, lock_days=3,
                broker={"initial":10000., "ticket":1., "impact":bps/10000})
    base = engine(state, state["events"], selection_hook=lambda k,*args: target[k], **args)
    nav = base["ledger"][:,0].copy()
    del base
    assert all(value is not None for value in snapshots.values())
    out = []
    for event in eligible.itertuples():
        k, end = event.index, event.label_index
        left = pair[k-1]
        left_weight = raw_weight(left, .5, target.shape[1])
        right_weight = raw_weight(pair[k], .5, target.shape[1])
        original = nav[end] / nav[k]
        row = {"index":k, "bps":bps, **{f"log_gain_{n}":0. for n in range(1,6)}}
        for n in range(1,6):
            start = k+n-1
            alt = dict(state, _bounds=(k,end), _resume=snapshots[k], _capture={})
            keys = ("d1", "d2", "risk_mode", "cooldown_rule")
            for key in keys:
                alt[key] = state[key].copy()
            alt["d1"][0,k:start] = left[0]
            alt["d2"][0,k:start] = left[1]
            alt["risk_mode"][k:start] = old_corr[k:start]
            trail = deepcopy(trail_snapshots[k])
            overlay = {}
            for day in range(k,end):
                dest = left_weight if day < start else right_weight
                weight, r = profit.step(trail, day, dest)
                overlay[day] = weight
                alt["cooldown_rule"][day] = 2*int(r)
            replica = engine(alt, state["events"], selection_hook=lambda k,*args: overlay[k], **args)
            ledger = replica["ledger"]
            assert ledger[k,0] == nav[k]
            assert np.max(abs(ledger[k:end,-1])) < 1e-9
            if n == 1:
                np.testing.assert_array_equal(ledger[k:end+1,0], nav[k:end+1])
            row[f"log_gain_{n}"] = float(np.log((ledger[end,0]/ledger[k,0])/original))
            del replica,ledger
        out.append(row)
    return pd.DataFrame(out), nav
