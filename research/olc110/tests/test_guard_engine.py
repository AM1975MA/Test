"""Public guard behavior under real account fills, prices, and schedules."""
from pathlib import Path
import importlib.util
import inspect
import unittest

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GuardEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load(ROOT / "src/engine.py", "guard_engine_under_test")
        cls.original = load(ROOT / "research/engine/olc108_engine_reference.py",
                            "immutable_olc108_engine")
        cls.legacy = load(ROOT / "source/src/core.py", "guard_test_account_core")

    def setUp(self):
        self.p = dict(dates=pd.bdate_range("2019-01-01", periods=340).values,
                      names=np.array(["AAA", "BBB"]), O=np.full((340, 2), 100.),
                      C=np.full((340, 2), 100.), observed=np.ones((340, 2), bool),
                      benchmark=0)

    def run_case(self, panel=None, features=None, policy=None, mask=None,
                 engine=None, **kwargs):
        panel = self.p if panel is None else panel
        features = self.legacy.features(panel) if features is None else features
        policy = (lambda k, current: [.5, .5]) if policy is None else policy
        mask = np.zeros(340, bool) if mask is None else mask
        engine = self.engine if engine is None else engine
        if "guard_policy" in kwargs or "guard_mask" in kwargs:
            # An absent public capability is a clear failing assertion in the
            # initial RED run; all tests below also verify account behavior.
            self.assertIn("guard_policy", inspect.signature(engine.simulate).parameters)
            self.assertIn("guard_mask", inspect.signature(engine.simulate).parameters)
        return engine.simulate(panel, features, policy, mask, legacy=self.legacy,
                               start=str(panel["dates"][300]), end=str(panel["dates"][320]),
                               ticket=0., impact=0., **kwargs)

    def schedule(self, *indices):
        mask = np.zeros(340, bool)
        mask[list(indices)] = True
        return mask

    def assert_same_results(self, left, right, cutoff=None):
        for name, index in [("daily", "k"), ("orders", "execution_idx"),
                            ("alerts", "signal_idx"), ("instructions", "signal_idx")]:
            a, b = left[name], right[name]
            if cutoff is not None:
                a, b = a[a[index] <= cutoff], b[b[index] <= cutoff]
            pd.testing.assert_frame_equal(a, b, check_exact=True, obj=name)
        a = [d for d in left["decisions"] if cutoff is None or d["k"] <= cutoff]
        b = [d for d in right["decisions"] if cutoff is None or d["k"] <= cutoff]
        self.assertEqual(len(a), len(b))
        for old, new in zip(a, b):
            self.assertEqual(old.keys(), new.keys())
            for key in old:
                if isinstance(old[key], np.ndarray):
                    np.testing.assert_array_equal(old[key], new[key])
                else:
                    self.assertEqual(old[key], new[key])
        if cutoff is None:
            self.assertEqual(left["deferred_sessions"], right["deferred_sessions"])
            self.assertEqual(left["max_self_financing_error"], right["max_self_financing_error"])

    def test_disabled_guard_exactly_preserves_immutable_engine_outputs(self):
        # Any alteration of the existing schedule, risk, or execution path fails.
        grid = np.arange(340)
        self.p["C"][:, 0] = 100. * np.exp(.0005 * grid + .02 * np.sin(grid / 5.))
        self.p["C"][:, 1] = 100. * np.exp(.0003 * grid + .02 * np.cos(grid / 7.))
        self.p["O"][1:] = self.p["C"][:-1]
        self.p["O"][302:304, 1] = np.nan
        policy = lambda k, current: ([.6, .4] if k % 2 else [.2, .7], {"k": k})
        for risk_target in (None, .01):
            with self.subTest(risk_target=risk_target):
                opts = dict(policy=policy, mask=self.schedule(303, 306, 309, 312, 315),
                            lag=2, risk_target=risk_target)
                self.assert_same_results(self.run_case(engine=self.original, **opts),
                                         self.run_case(**opts))

    def test_guard_sees_actual_close_weights_and_waits_until_lagged_open(self):
        self.p["C"][303:, 0] = 150.
        self.p["O"][304:, 0] = 150.
        calls = []
        def guard(k, current):
            calls.append((k, current.copy()))
            current[1] = 0.
            return current, {"failed": "BBB"}
        r = self.run_case(lag=2, guard_policy=guard, guard_mask=self.schedule(303))
        self.assertEqual(calls[0][0], 303)
        np.testing.assert_array_equal(calls[0][1], [.6, .4])
        alert = r["alerts"].query("reason == 'TREND_REDUCE'").iloc[0]
        self.assertEqual((alert.signal_idx, alert.due_idx, alert.force), (303, 306, True))
        self.assertEqual(alert.target_weights, (.6, 0.))
        self.assertEqual(alert.raw_weights, (.6, .4))
        trades = r["orders"].query("reason == 'TREND_REDUCE'")
        self.assertEqual(list(trades.execution_idx), [306])
        self.assertEqual(list(trades.side), ["SELL"])
        self.assertEqual(list(trades.ticker), ["BBB"])
        self.assertAlmostEqual(trades.iloc[0].notional, 5000.)
        self.assertEqual(len(r["decisions"]), 1)
        self.assertEqual(r["decisions"][0]["k"], 299)

    def test_missing_open_keeps_guard_pending_without_buying_partial_fills_back(self):
        self.p["O"][301:303, 0] = np.nan
        self.p["O"][302:304, 1] = 50.
        r = self.run_case(guard_policy=lambda k, w: [0., .25],
                          guard_mask=self.schedule(300))
        trades = r["orders"].query("reason == 'TREND_REDUCE'")
        self.assertEqual(r["deferred_sessions"], 2)
        self.assertEqual(list(trades.execution_idx), [301, 303])
        self.assertEqual(list(trades.ticker), ["BBB", "AAA"])
        self.assertEqual(list(trades.side), ["SELL", "SELL"])
        self.assertEqual(list(trades.quantity), [25., 50.])
        self.assertAlmostEqual(r["daily"].iloc[-1].cash, 7500.)
        self.assertLess(r["max_self_financing_error"], 1e-8)

    def test_asymmetric_open_gap_cannot_buy_an_unchanged_guard_leg(self):
        self.p["O"][306, 0] = 10.
        r = self.run_case(lag=2, guard_policy=lambda k, w: [w[0], 0.],
                          guard_mask=self.schedule(303))
        trades = r["orders"].query("reason == 'TREND_REDUCE'")
        self.assertEqual(list(trades.ticker), ["BBB"])
        self.assertEqual(list(trades.side), ["SELL"])
        self.assertEqual(list(trades.execution_idx), [306])
        self.assertEqual(r["alerts"].iloc[-1].target_weights, (.5, 0.))

    def test_queued_guard_targets_are_immutable_and_never_rebuy_an_earlier_sale(self):
        target = np.zeros(2)
        def guard(k, current):
            target[:] = [0., .5] if k == 303 else [.5, 0.]
            return target
        r = self.run_case(lag=2, guard_policy=guard, guard_mask=self.schedule(303, 304))
        alerts = r["alerts"].query("reason == 'TREND_REDUCE'")
        self.assertEqual(list(alerts.target_weights), [(0., .5), (.5, 0.)])
        trades = r["orders"].query("reason == 'TREND_REDUCE'")
        self.assertEqual(list(trades.execution_idx), [306, 307])
        self.assertEqual(list(trades.ticker), ["AAA", "BBB"])
        self.assertEqual(list(trades.side), ["SELL", "SELL"])
        self.assertEqual(r["daily"].iloc[-1].positions, 0)
        np.testing.assert_array_equal(target, [.5, 0.])

    def test_guard_runs_only_on_requested_nonfinal_closes(self):
        calls = []
        def guard(k, current):
            calls.append(k)
            return None
        r = self.run_case(guard_policy=guard, guard_mask=self.schedule(299, 300, 302, 319, 320))
        self.assertEqual(calls, [300, 302, 319])
        self.assertEqual(list(r["alerts"].reason), ["INITIAL"])

    def test_monthly_decision_takes_precedence_and_can_reenter_after_a_guard(self):
        calls = []
        def guard(k, current):
            calls.append(k)
            return np.zeros(2)
        r = self.run_case(policy=lambda k, w: [.5, .5], mask=self.schedule(303),
                          guard_policy=guard, guard_mask=self.schedule(300, 303))
        self.assertEqual(calls, [300])
        self.assertEqual(list(r["alerts"].reason), ["INITIAL", "TREND_REDUCE", "SCHEDULED"])
        self.assertEqual([d["k"] for d in r["decisions"]], [299, 303])
        buys = r["orders"].query("side == 'BUY' and execution_idx > 300")
        self.assertEqual(list(buys.execution_idx), [304, 304])
        self.assertEqual(set(buys.reason), {"SCHEDULED"})

    def test_none_and_unchanged_guard_results_emit_no_instruction(self):
        baseline = self.run_case()
        for guard in (lambda k, w: None, lambda k, w: w, lambda k, w: (w, {"noop": True})):
            self.assert_same_results(baseline, self.run_case(guard_policy=guard,
                                     guard_mask=np.ones(340, bool)))

    def test_missing_guard_mask_disables_guard(self):
        def guard(k, current):
            self.fail("An absent guard mask must not schedule guard evaluation")
        self.assert_same_results(self.run_case(), self.run_case(guard_policy=guard))

    def test_guard_rejects_any_addition_even_when_gross_exposure_falls(self):
        with self.assertRaisesRegex(ValueError, "GUARD_ADDS"):
            self.run_case(guard_policy=lambda k, w: [0., .6], guard_mask=self.schedule(300))

    def test_guard_rejects_nonfinite_negative_leveraged_or_wrong_shape_weights(self):
        for target in ([np.nan, 0.], [-.1, .1], [.6, .6], [.1]):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "WEIGHTS"):
                self.run_case(guard_policy=lambda k, w: target, guard_mask=self.schedule(300))

    def test_guard_mask_requires_the_same_calendar_as_the_panel(self):
        with self.assertRaisesRegex(ValueError, "PANEL_OR_SCHEDULE"):
            self.run_case(guard_policy=lambda k, w: None, guard_mask=np.ones(339, bool))

    def test_guard_emission_takes_precedence_over_volatility_reduction(self):
        features = self.legacy.features(self.p)
        features["returns"][303:, :] = np.resize([.20, -.20], 37)[:, None]
        r = self.run_case(features=features, lag=2, risk_target=.15,
                          guard_policy=lambda k, w: [0., w[1]] if k == 303 else None,
                          guard_mask=self.schedule(303, 304))
        alerts = r["alerts"]
        self.assertEqual(list(alerts.query("signal_idx == 303").reason), ["TREND_REDUCE"])
        self.assertEqual(list(alerts.query("signal_idx == 304").reason), ["VOL_REDUCE"])
        self.assertTrue(alerts.signal_idx.is_unique)

    def test_future_data_and_guard_schedule_cannot_change_the_completed_prefix(self):
        self.p["C"][304:, 0] = 70.
        self.p["C"][309:, 1] = 60.
        self.p["O"][1:] = self.p["C"][:-1]
        cutoff = 310
        changed = {key: value.copy() if hasattr(value, "copy") else value
                   for key, value in self.p.items()}
        changed["C"][cutoff + 1:, 0] *= np.linspace(2., 20., 29)
        changed["O"][cutoff + 1:, 1] *= .01
        changed["observed"][cutoff + 1::2, 0] = False
        changed["observed"][cutoff + 2::2, 1] = False
        def evaluate(panel, altered):
            features = self.legacy.features(panel)
            guards = np.ones(340, bool)
            if altered:
                guards[cutoff + 1:] = False
            def guard(k, current):
                failed = features["C"][k] < .9 * features["C"][k - 1]
                if not np.any(failed & (current > 0)):
                    return None
                current[failed] = 0.
                return current
            return self.run_case(panel=panel, features=features, lag=2,
                                 mask=self.schedule(300, 305, 310, 315),
                                 guard_policy=guard, guard_mask=guards)
        original, mutated = evaluate(self.p, False), evaluate(changed, True)
        self.assertGreaterEqual(len(original["alerts"].query("reason == 'TREND_REDUCE' and signal_idx <= @cutoff")), 2)
        self.assert_same_results(original, mutated, cutoff=cutoff)


if __name__ == "__main__":
    unittest.main(verbosity=2)
