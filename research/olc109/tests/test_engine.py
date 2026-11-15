"""Causal execution and accounting regressions, using the immutable OLC106 core."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import unittest

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / "source"


def load(path, name):
    assert path.exists(), "The generic execution engine must be implemented"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def legacy():
    return load(SOURCE / "src/core.py", "legacy_engine_test")


def simulate():
    return load(Path(__file__).resolve().parents[1] / "src/engine.py", "engine_test").simulate


def synthetic(legacy, n=340):
    p = dict(dates=pd.bdate_range("2019-01-01", periods=n).values,
             names=np.array(["AAA", "BBB"]), O=np.full((n, 2), 100.),
             C=np.full((n, 2), 100.), observed=np.ones((n, 2), bool), benchmark=0)
    return p, legacy.features(p)


def run(simulate, legacy, p, f, policy, mask=None, **kwargs):
    if mask is None:
        mask = np.zeros(len(p["dates"]), bool)
    return simulate(p, f, policy, mask, legacy=legacy, start=str(p["dates"][300]),
                    end=str(p["dates"][320]), ticket=0., impact=0., **kwargs)


def test_revised_target_waits_for_its_own_due_date(simulate, legacy):
    # Updating an old instruction in place would buy BBB before session 304.
    p, f = synthetic(legacy)
    mask = np.zeros(340, bool); mask[[300, 301]] = True
    targets = {299: np.array([.8, 0.]), 300: np.array([.4, 0.]), 301: np.array([0., .8])}
    r = run(simulate, legacy, p, f, lambda k, w: targets[k], mask, lag=2)
    orders = r["orders"]
    assert orders.iloc[0]["execution_idx"] == 302
    assert orders.iloc[0]["signal_idx"] == 299
    assert np.isclose(orders.iloc[0]["notional"], 8000.)
    assert orders.loc[orders.ticker == "BBB", "execution_idx"].min() == 304
    assert (orders.execution_idx >= orders.signal_idx + 3).all()
    assert np.array_equal(targets[299], [.8, 0.])


def test_initial_and_scheduled_signals_use_next_open(simulate, legacy):
    p, f = synthetic(legacy)
    p["C"][300:, 0] = 150.; p["O"][301:, 0] = 150.
    f = legacy.features(p)
    mask = np.zeros(340, bool); mask[300] = True
    r = run(simulate, legacy, p, f, lambda k, w: [.5, 0.] if k == 299 else [0., 1.], mask)
    initial = r["orders"].iloc[0]
    assert (initial.signal_idx, initial.execution_idx, initial.price) == (299, 300, 100.)
    assert r["daily"].iloc[0].nav_close == 12500.
    assert r["orders"].query("signal_idx == 300").execution_idx.min() == 301
    decision = r["decisions"][1]
    assert decision["cash"] == 5000.
    assert np.array_equal(decision["units"], [50., 0.])
    assert np.allclose(decision["current_weights"], [.6, 0.])


def test_missing_open_is_deferred_and_later_signal_cannot_fill_early(simulate, legacy):
    p, f = synthetic(legacy)
    p["O"][302:304, 0] = np.nan
    mask = np.zeros(340, bool); mask[301] = True
    r = run(simulate, legacy, p, f, lambda k, w: [1., 0.] if k == 299 else [0., 1.], mask, lag=2)
    assert r["deferred_sessions"] == 2
    assert not (r["orders"].execution_idx < 304).any()
    assert list(r["orders"].ticker) == ["BBB"]
    assert r["orders"].iloc[0].signal_idx == 301


def test_missing_open_partial_fill_remains_pending(simulate, legacy):
    p, f = synthetic(legacy)
    p["O"][300:302, 1] = np.nan
    r = run(simulate, legacy, p, f, lambda k, w: [.5, .5])
    assert r["deferred_sessions"] == 2
    assert list(r["orders"].execution_idx) == [300, 302]
    assert list(r["orders"].ticker) == ["AAA", "BBB"]
    assert r["daily"].iloc[0].cash == 5000.
    assert r["daily"].iloc[2].cash == 0.


def test_repeated_daily_risk_reductions_do_not_postpone_matured_target(simulate, legacy):
    p, f = synthetic(legacy)
    # Starting at 303 covariance becomes large: real covariance_at calculates it.
    f["returns"][303:, 0] = np.resize([.20, -.20], 37)
    r = run(simulate, legacy, p, f, lambda k, w: [1., 0.], lag=2, risk_target=.15)
    risk = r["orders"].query("reason == 'VOL_REDUCE'")
    assert len(risk) > 0
    assert risk.iloc[0].signal_idx == 303
    assert risk.iloc[0].execution_idx == 306
    assert (risk.execution_idx >= risk.signal_idx + 3).all()
    alerts = r["alerts"].set_index("instruction_id")
    first = risk.iloc[0]
    target = np.array(alerts.loc[first.instruction_id, "target_weights"])
    # A revised signal at 304 may differ but cannot overwrite the 303 target.
    assert np.isclose(first.notional, 10000. * (1. - target[0]))


def test_cash_and_equity_reconcile_without_leverage(simulate, legacy):
    p, f = synthetic(legacy)
    mask = np.zeros(340, bool); mask[300:320:2] = True
    r = simulate(p, f, lambda k, w: [1., 0.] if k % 2 else [0., 1.], mask,
                 legacy=legacy, start=str(p["dates"][300]), end=str(p["dates"][320]))
    assert r["daily"].cash.min() >= -1e-9
    assert r["daily"].gross.max() <= 1. + 1e-12
    assert abs(r["daily"].iloc[-1].nav_close + r["orders"].cost.sum() - 10000.) < 1e-8
    assert r["max_self_financing_error"] < 1e-8


def test_stale_risk_instruction_cannot_buy_back_an_earlier_reduction(simulate, legacy):
    # A slightly falling covariance generates larger queued risk targets before
    # the first reduction fills. Later risk-only executions must not buy back.
    p, f = synthetic(legacy)
    f["returns"][303, 0] = .20
    f["returns"][304:, 0] = .20 / 63
    r = run(simulate, legacy, p, f, lambda k, w: [1., 0.], lag=2, risk_target=.15)
    risk = r["orders"].query("reason == 'VOL_REDUCE'")
    assert len(risk) > 0
    assert set(risk.side) == {"SELL"}, risk.to_string(index=False)
    targets = r["alerts"].query("reason == 'VOL_REDUCE'").set_index("signal_idx")
    assert targets.loc[304, "target_weights"][0] > targets.loc[303, "target_weights"][0]


def test_risk_instruction_cannot_buy_after_asymmetric_open_gap(simulate, legacy):
    p, f = synthetic(legacy)
    f["returns"][303:, :] = np.resize([.20, -.20], 37)[:, None]
    p["O"][306, 0] = 10.
    r = run(simulate, legacy, p, f, lambda k, w: [.5, .5], lag=2, risk_target=.15)
    risk = r["orders"].query("reason == 'VOL_REDUCE'")
    assert len(risk) > 0
    assert set(risk.side) == {"SELL"}, risk.to_string(index=False)
    first = r["alerts"].query("reason == 'VOL_REDUCE'").iloc[0]
    # Requested close-signal target stays immutable despite execution clamping.
    assert np.allclose(first.target_weights, [.1875, .1875])
    assert len(risk.query("execution_idx == 306 and ticker == 'BBB'")) == 1
    assert len(risk.query("execution_idx == 306 and ticker == 'AAA'")) == 0


def test_future_prices_and_observed_flags_cannot_change_prior_simulation(simulate, legacy):
    p, _ = synthetic(legacy)
    grid = np.arange(340)
    p["C"][:, 0] = 100. * np.exp(.0005 * grid + .02 * np.sin(grid / 5.))
    p["C"][:, 1] = 100. * np.exp(.0003 * grid + .02 * np.cos(grid / 7.))
    p["O"][1:] = p["C"][:-1]
    changed = {key: value.copy() if hasattr(value, "copy") else value for key, value in p.items()}
    cutoff = 310
    changed["C"][cutoff + 1:, 0] *= np.linspace(2., 20., 29)
    changed["O"][cutoff + 1:, 1] *= .01
    changed["observed"][cutoff + 1::2, 0] = False
    changed["observed"][cutoff + 2::2, 1] = False
    mask = np.zeros(340, bool); mask[300:320:2] = True

    def evaluate(panel):
        features = legacy.features(panel)
        def policy(k, current):
            winner = int(np.nanargmax(features["m252"][k]))
            w = np.zeros(2); w[winner] = 1.
            return w, {"winner": winner}
        return run(simulate, legacy, panel, features, policy, mask, lag=2, risk_target=.15)

    before, after = evaluate(p), evaluate(changed)
    pd.testing.assert_frame_equal(before["daily"].query("k <= @cutoff"),
                                  after["daily"].query("k <= @cutoff"))
    pd.testing.assert_frame_equal(before["orders"].query("execution_idx <= @cutoff"),
                                  after["orders"].query("execution_idx <= @cutoff"))
    pd.testing.assert_frame_equal(before["alerts"].query("signal_idx <= @cutoff"),
                                  after["alerts"].query("signal_idx <= @cutoff"))
    old_decisions = [d for d in before["decisions"] if d["k"] <= cutoff]
    new_decisions = [d for d in after["decisions"] if d["k"] <= cutoff]
    assert len(old_decisions) == len(new_decisions)
    for old, new in zip(old_decisions, new_decisions):
        for key in ["units", "current_weights", "raw_weights", "weights"]:
            np.testing.assert_array_equal(old[key], new[key])
        assert old["cash"] == new["cash"]
        assert old["meta"] == new["meta"]


def test_actual_selective_policies_preserve_full_prefix_under_future_mutation(simulate, legacy):
    """Catch look-ahead across real selector features, policies and execution."""
    from test_signals import panel_fixture
    signals = load(BASE / "src/signals.py", "integrated_selective_signals")
    p = panel_fixture()
    # A quiet asset starts rising late enough to activate the actual monthly
    # and quarterly opportunity branches during this simulation's prefix.
    rates = np.zeros(len(p["dates"]))
    rates[301:] = .003
    p["C"][:, 2] = 100. * np.exp(np.cumsum(rates))
    p["O"] = p["C"].copy()
    cutoff = 325
    changed = {key: value.copy() if hasattr(value, "copy") else value for key, value in p.items()}
    future_count = len(p["dates"]) - cutoff - 1
    changed["C"][cutoff + 1:, 2] *= np.linspace(3., 30., future_count)
    changed["C"][cutoff + 1:, 0] *= .10
    changed["O"][cutoff + 1:, 1] *= .02
    changed["O"][cutoff + 1:, 2] *= 10.
    changed["observed"][cutoff + 1::2, 0] = False
    changed["observed"][cutoff + 2::2, 2] = False

    for arm in ["DUAL_SELECTIVE", "DUAL_SELECTIVE_21"]:
        def evaluate(panel):
            features = signals.compute_features(panel, legacy)
            return simulate(
                panel, features, signals.make_policy(panel, features, arm),
                signals.decision_mask(panel["dates"], "WEEKLY"), legacy=legacy,
                start=str(panel["dates"][260]), end=str(panel["dates"][-1]),
                lag=2, risk_target=.15)

        original, mutated = evaluate(p), evaluate(changed)
        for table, index in [("daily", "k"), ("orders", "execution_idx"),
                             ("alerts", "signal_idx"), ("instructions", "signal_idx")]:
            left = original[table].loc[original[table][index] <= cutoff]
            right = mutated[table].loc[mutated[table][index] <= cutoff]
            pd.testing.assert_frame_equal(left, right, check_exact=True, obj=f"{arm} {table}")
        old_decisions = [d for d in original["decisions"] if d["k"] <= cutoff]
        new_decisions = [d for d in mutated["decisions"] if d["k"] <= cutoff]
        assert len(old_decisions) == len(new_decisions) >= 10, arm
        assert any(d["meta"]["opportunity_used"] for d in old_decisions), arm
        assert len(original["orders"].query("execution_idx <= @cutoff")) >= 4, arm
        for old, new in zip(old_decisions, new_decisions):
            assert old.keys() == new.keys()
            for key in old:
                if isinstance(old[key], np.ndarray):
                    np.testing.assert_array_equal(old[key], new[key], err_msg=f"{arm} {key}")
                else:
                    assert old[key] == new[key], (arm, key, old["k"])


def test_frozen_monthly_mom252_matches_original_to_1e_minus_10(simulate, legacy):
    with np.load(SOURCE / "data/TR29.npz", allow_pickle=False) as z:
        p = {k: z[k] for k in z.files}
    f = legacy.features(p)
    dates = pd.DatetimeIndex(p["dates"])
    mask = np.r_[dates.month[:-1] != dates.month[1:], False]
    original = legacy.simulate(p, "MOM252_TOP2", f=f)
    new = simulate(p, f, lambda k, w: legacy.chosen_weights(p, f, k, "MOM252_TOP2")[0],
                   mask, legacy=legacy)
    for col in ["nav_open", "nav_close", "cash", "gross", "positions"]:
        assert np.max(np.abs(new["daily"][col].to_numpy() - original["daily"][col].to_numpy())) < 1e-10
    for col in ["quantity", "notional", "cost"]:
        assert np.max(np.abs(new["orders"][col].to_numpy() - original["orders"][col].to_numpy())) < 1e-10


def test_rejects_nonfinite_negative_or_leveraged_targets(simulate, legacy):
    p, f = synthetic(legacy)
    for target in [[1.1, 0.], [-.1, .1], [np.nan, 0.]]:
        with unittest.TestCase().assertRaisesRegex(ValueError, "WEIGHTS"):
            run(simulate, legacy, p, f, lambda k, w: target)


class EngineTests(unittest.TestCase):
    pass


def _method(fn):
    def method(self):
        fn(simulate(), legacy())
    method.__name__ = fn.__name__
    return method


for _name, _fn in list(globals().items()):
    if _name.startswith("test_") and callable(_fn):
        setattr(EngineTests, _name, _method(_fn))


if __name__ == "__main__":
    unittest.main(verbosity=2)
