"""Small, hand-calculated resumed-account tests; no financial study is run."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT.parent / "olc110"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReplayEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load(ROOT / "src/replay_engine.py", "replay_engine_test")
        cls.original = load(FROZEN / "src/engine.py", "frozen_olc110_engine")
        cls.core = load(FROZEN / "source/src/core.py", "replay_immutable_core")

    def setUp(self):
        self.panel = dict(dates=pd.bdate_range("2019-01-01", periods=340).values,
                          names=np.array(["AAA", "BBB"]),
                          O=np.full((340, 2), 100.), C=np.full((340, 2), 100.),
                          observed=np.ones((340, 2), bool), benchmark=0)

    def schedule(self, *indices):
        mask = np.zeros(340, bool)
        mask[list(indices)] = True
        return mask

    def run_case(self, *, engine=None, panel=None, features=None, policy=None,
                 mask=None, begin=300, end=320, **kwargs):
        panel = self.panel if panel is None else panel
        features = self.core.features(panel) if features is None else features
        return (self.engine if engine is None else engine).simulate(
            panel, features, (lambda k, w: [.5, .5]) if policy is None else policy,
            self.schedule() if mask is None else mask, legacy=self.core,
            start=str(panel["dates"][begin]), end=str(panel["dates"][end]),
            ticket=kwargs.pop("ticket", 2.), impact=kwargs.pop("impact", .01), **kwargs)

    def assert_outputs_equal(self, left, right):
        self.assertEqual(left.keys(), right.keys())
        for key in ("daily", "orders", "alerts", "instructions"):
            pd.testing.assert_frame_equal(left[key], right[key], check_exact=True, obj=key)
        self.assertEqual(len(left["decisions"]), len(right["decisions"]))
        for a, b in zip(left["decisions"], right["decisions"]):
            self.assertEqual(a.keys(), b.keys())
            for key, value in a.items():
                if isinstance(value, np.ndarray):
                    np.testing.assert_array_equal(value, b[key], err_msg=key)
                else:
                    self.assertEqual(value, b[key], key)
        for key in ("deferred_sessions", "max_self_financing_error"):
            self.assertEqual(left[key], right[key], key)

    def test_resumed_hold_keeps_actual_units_cash_and_skips_initial_callback(self):
        self.panel["O"][300:] = [120., 80.]
        self.panel["C"][300:] = [125., 90.]
        state = dict(units=np.array([12.5, 7.]), cash=250.)
        calls = {}
        def hold(k, current, context):
            calls[k] = context
            return None
        result = self.run_case(initial_state=state, issue_initial=False,
                               account_policy=hold)
        self.assertEqual(list(calls), list(range(300, 320)))
        self.assertEqual(len(result["daily"]), 21)
        self.assertTrue(result["orders"].empty)
        self.assertTrue(result["alerts"].empty)
        self.assertEqual(result["decisions"], [])
        # 12.5*120 + 7*80 + 250; then 12.5*125 + 7*90 + 250.
        np.testing.assert_array_equal(result["daily"].nav_open, np.full(21, 2310.))
        np.testing.assert_array_equal(result["daily"].nav_close, np.full(21, 2442.5))
        np.testing.assert_array_equal(result["daily"].cash, np.full(21, 250.))
        for context in calls.values():
            np.testing.assert_array_equal(context["units"], [12.5, 7.])
            np.testing.assert_array_equal(context["last_buy_idx"], [-1, -1])
            np.testing.assert_array_equal(context["last_sell_idx"], [-1, -1])
            self.assertFalse(context["initial"])

    def test_seeded_cash_action_sells_next_open_at_actual_gaps_and_costs(self):
        self.panel["O"][300:] = [80., 120.]
        self.panel["C"][300:] = [50., 150.]
        state = dict(units=np.array([10., 20.]), cash=500.,
                     last_buy_idx=np.array([280, 290]), last_sell_idx=np.array([-1, 270]))
        before = deepcopy(state)
        calls = {}
        def cash_policy(k, current, context):
            calls[k] = (current, context)
            return dict(weights=[0., 0.]) if context["initial"] else None
        result = self.run_case(initial_state=state, account_policy=cash_policy)
        initial_weights, context = calls[299]
        np.testing.assert_allclose(initial_weights, [1000. / 3500., 2000. / 3500.])
        self.assertEqual(context["nav"], 3500.)
        self.assertEqual(context["cash"], 500.)
        orders = result["orders"]
        self.assertEqual(list(orders.side), ["SELL", "SELL"])
        self.assertEqual(list(orders.quantity), [10., 20.])
        self.assertEqual(list(orders.price), [80., 120.])
        self.assertEqual(list(orders.cost), [10., 26.])
        self.assertEqual(list(orders.signal_idx), [299, 299])
        self.assertEqual(list(orders.execution_idx), [300, 300])
        # 500 + 800 + 2400 - (2+.01*800) - (2+.01*2400).
        self.assertEqual(result["daily"].iloc[0].nav_open, 3700.)
        np.testing.assert_array_equal(result["daily"].nav_close, np.full(21, 3664.))
        np.testing.assert_array_equal(calls[300][1]["last_sell_idx"], [300, 300])
        np.testing.assert_array_equal(calls[300][1]["last_buy_idx"], [280, 290])
        for key in ("units", "last_buy_idx", "last_sell_idx"):
            np.testing.assert_array_equal(state[key], before[key])
        self.assertEqual(state["cash"], before["cash"])

    def test_hold_cash_and_fresh_share_one_economic_starting_account(self):
        self.panel["O"][300:] = [80., 120.]
        self.panel["C"][300:] = [90., 132.]
        state = dict(units=[10., 0.], cash=500.)
        hold = self.run_case(initial_state=state, issue_initial=False)
        cash = self.run_case(initial_state=state, policy=lambda k, w: [0., 0.])
        fresh = self.run_case(initial_state=state, policy=lambda k, w: [0., 1.])
        for result in (hold, cash, fresh):
            self.assertEqual(result["daily"].iloc[0].nav_open, 1300.)
            self.assertEqual(len(result["daily"]), 21)
        self.assertEqual(hold["daily"].iloc[-1].nav_close, 1400.)
        self.assertEqual(cash["daily"].iloc[-1].nav_close, 1290.)
        # Sell 10 AAA at 80: cash becomes 1290. Buy BBB with (1290-2)/1.01.
        bought_notional = 1288. / 1.01
        self.assertEqual(list(fresh["orders"].side), ["SELL", "BUY"])
        self.assertAlmostEqual(fresh["orders"].iloc[1].notional, bought_notional)
        self.assertAlmostEqual(fresh["orders"].iloc[1].quantity, bought_notional / 120.)
        self.assertAlmostEqual(fresh["daily"].iloc[-1].nav_close, bought_notional * 1.1)
        self.assertAlmostEqual(fresh["daily"].iloc[-1].cash, 0.)
        self.assertLess(fresh["max_self_financing_error"], 1e-9)

    def test_monthly_continuation_matches_direct_original_account(self):
        dates = pd.DatetimeIndex(self.panel["dates"])
        monthly = np.r_[dates.month[:-1] != dates.month[1:], False]
        self.panel["O"][301:, 0] = 200.
        self.panel["C"][301:, 0] = 200.
        captured = {}
        def baseline(k, current, context):
            if k == 299:
                captured.update(context)
            if context["initial"] or context["scheduled"]:
                return dict(weights=[.6, .2] if k < 300 else [.2, .7])
            return None
        direct = self.run_case(engine=self.original, begin=280, mask=monthly,
                               account_policy=baseline)
        self.assertIsNone(captured["pending"])
        self.assertEqual(captured["queued"], ())
        # Initial buys cost 62+22, leaving the actual 60/20 units and 1916 cash.
        np.testing.assert_array_equal(captured["units"], [60., 20.])
        self.assertEqual(captured["cash"], 1916.)
        resumed = self.run_case(initial_state=captured, issue_initial=False,
                                mask=monthly, account_policy=baseline)
        pd.testing.assert_frame_equal(
            resumed["daily"], direct["daily"].query("k >= 300").reset_index(drop=True),
            check_exact=True)
        pd.testing.assert_frame_equal(
            resumed["orders"].drop(columns="instruction_id"),
            direct["orders"].query("execution_idx >= 300").drop(
                columns="instruction_id").reset_index(drop=True), check_exact=True)
        self.assertEqual(list(resumed["orders"].execution_date), ["2020-03-02"] * 2)
        # At NAV 15916, targets are 3183.2 and 11141.2: sell 8816.8, buy 9141.2.
        self.assertAlmostEqual(resumed["orders"].iloc[0].quantity, 44.084)
        self.assertAlmostEqual(resumed["orders"].iloc[1].quantity, 91.412)
        self.assertAlmostEqual(resumed["daily"].iloc[-1].cash, 1408.02)

    def test_missing_open_never_uses_future_quote_or_fills_after_replay_end(self):
        self.panel["O"][300:303, 0] = np.nan
        self.panel["O"][303:, 0] = 80.
        self.panel["C"][300, 0] = 100.
        self.panel["C"][301, 0] = 70.
        self.panel["C"][302:, 0] = 60.
        options = dict(initial_state=dict(units=[10., 0.], cash=500.),
                       policy=lambda k, w: [0., 0.])
        short = self.run_case(end=302, **options)
        longer = self.run_case(end=304, **options)
        self.assertTrue(short["orders"].empty)
        self.assertEqual(short["deferred_sessions"], 3)
        self.assertEqual(short["daily"].iloc[-1].cash, 500.)
        self.assertEqual(short["daily"].iloc[-1].nav_close, 1100.)
        pd.testing.assert_frame_equal(short["daily"], longer["daily"].iloc[:3],
                                      check_exact=True)
        self.assertEqual(list(longer["orders"].execution_idx), [303])
        self.assertEqual(list(longer["orders"].price), [80.])
        self.assertEqual(longer["daily"].iloc[-1].cash, 1290.)

    def test_seed_arrays_are_detached_from_later_caller_mutation(self):
        state = dict(units=np.array([10., 0.]), cash=500.,
                     last_buy_idx=np.array([280, -1]), last_sell_idx=np.array([-1, 270]))
        observed = {}
        def hold(k, current, context):
            observed[k] = context
            if k == 300:
                state["units"][:] = 999.
                state["last_buy_idx"][:] = 1
                state["last_sell_idx"][:] = 2
            return None
        result = self.run_case(initial_state=state, issue_initial=False, account_policy=hold)
        np.testing.assert_array_equal(observed[301]["units"], [10., 0.])
        np.testing.assert_array_equal(observed[301]["last_buy_idx"], [280, -1])
        np.testing.assert_array_equal(observed[301]["last_sell_idx"], [-1, 270])
        self.assertEqual(result["daily"].iloc[-1].nav_close, 1500.)

    def test_invalid_seed_values_and_nonempty_instruction_state_are_rejected(self):
        invalid = [dict(units=[-1., 0.], cash=500.),
                   dict(units=[np.nan, 0.], cash=500.),
                   dict(units=[np.inf, 0.], cash=500.),
                   dict(units=[1.], cash=500.),
                   dict(units=[0., 0.], cash=-1.),
                   dict(units=[0., 0.], cash=np.inf),
                   dict(units=[0., 0.], cash=np.nan),
                   dict(units=[0., 0.], cash=0.),
                   dict(units=[1., 0.], cash=500., pending={"due_idx": 300}),
                   dict(units=[1., 0.], cash=500., queued=({"due_idx": 302},)),
                   dict(units=[1., 0.], cash=500., last_buy_idx=[299]),
                   dict(units=[1., 0.], cash=500., last_sell_idx=[1.5, -1])]
        for state in invalid:
            with self.subTest(state=state), self.assertRaisesRegex(ValueError, "INITIAL_STATE"):
                self.run_case(initial_state=state, issue_initial=False)

    def test_seed_mark_must_be_finite_positive_only_for_held_units(self):
        features = self.core.features(self.panel)
        for bad in (np.nan, np.inf, 0., -1.):
            with self.subTest(mark=bad):
                features["C"][299, 0] = bad
                with self.assertRaisesRegex(ValueError, "INITIAL_STATE"):
                    self.run_case(features=features, initial_state=dict(units=[1., 0.], cash=500.),
                                  issue_initial=False)
                result = self.run_case(features=features,
                                       initial_state=dict(units=[0., 0.], cash=500.),
                                       issue_initial=False)
                self.assertEqual(result["daily"].iloc[-1].nav_close, 500.)

    def test_seed_capital_ignores_legacy_initial_and_preserves_window_checks(self):
        state = dict(units=[1., 0.], cash=500., pending=None, queued=())
        result = self.run_case(initial_state=state, issue_initial=False, initial=np.nan)
        self.assertEqual(result["daily"].iloc[-1].nav_close, 600.)
        with self.assertRaisesRegex(ValueError, "CONFIG"):
            self.run_case(initial=np.nan)
        for options in (dict(begin=252), dict(end=300)):
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, "WARMUP_OR_WINDOW"):
                self.run_case(initial_state=state, issue_initial=False, **options)

    def test_allowed_scheduled_hold_keeps_units_through_large_open_gap(self):
        self.panel["O"][301:] = [200., 50.]
        self.panel["C"][301:] = [200., 50.]
        calls = {}
        def hold(k, current, context):
            calls[k] = context
            return None
        result = self.run_case(initial_state=dict(units=[10., 5.], cash=500.),
                               issue_initial=False, account_policy=hold,
                               allow_scheduled_hold=True, mask=self.schedule(300, 310))
        self.assertTrue(calls[300]["scheduled"])
        self.assertTrue(result["orders"].empty)
        self.assertTrue(result["alerts"].empty)
        self.assertEqual(result["daily"].iloc[1].nav_open, 2750.)
        self.assertEqual(result["daily"].iloc[-1].nav_close, 2750.)
        np.testing.assert_array_equal(calls[301]["units"], [10., 5.])
        self.assertEqual(calls[301]["cash"], 500.)

    def test_allowed_scheduled_cash_hold_stays_cash_until_entry_signal(self):
        def cash_then_entry(k, current, context):
            return dict(weights=[1., 0.], reason="ENTRY", force=True) if k == 305 else None
        result = self.run_case(initial_state=dict(units=[0., 0.], cash=1000.),
                               issue_initial=False, account_policy=cash_then_entry,
                               allow_scheduled_hold=True, mask=self.schedule(300, 310))
        np.testing.assert_array_equal(result["daily"].query("k <= 305").cash,
                                      np.full(6, 1000.))
        self.assertEqual(list(result["orders"].execution_idx), [306])
        self.assertEqual(list(result["orders"].reason), ["ENTRY"])
        self.assertAlmostEqual(result["orders"].iloc[0].notional, 998. / 1.01)

    def test_scheduled_none_is_strict_by_default_and_initial_none_always_raises(self):
        hold = lambda k, current, context: None
        with self.assertRaisesRegex(ValueError, "ACCOUNT_POLICY_REQUIRED"):
            self.run_case(initial_state=dict(units=[1., 0.], cash=500.),
                          issue_initial=False, account_policy=hold, mask=self.schedule(300))
        with self.assertRaisesRegex(ValueError, "ACCOUNT_POLICY_REQUIRED"):
            self.run_case(initial_state=dict(units=[1., 0.], cash=500.),
                          account_policy=hold, allow_scheduled_hold=True)

    def test_default_invocations_preserve_all_original_outputs_exactly(self):
        grid = np.arange(340)
        self.panel["C"][:, 0] = 100. * np.exp(.0005 * grid + .02 * np.sin(grid / 5.))
        self.panel["C"][:, 1] = 100. * np.exp(.0003 * grid + .02 * np.cos(grid / 7.))
        self.panel["O"][1:] = self.panel["C"][:-1]
        self.panel["O"][302:304, 1] = np.nan
        selector = lambda k, w: ([.6, .4] if k % 2 else [.2, .7], {"signal": k})
        def account(k, current, context):
            if context["initial"] or context["scheduled"]:
                weights, meta = selector(k, current)
                return dict(weights=weights, meta=meta)
            return None
        for risk in (None, .01):
            for callback in (None, account):
                with self.subTest(risk=risk, account=callback is not None):
                    options = dict(policy=selector, mask=self.schedule(303, 306, 309, 312),
                                   lag=2, ticket=1., impact=.0015, risk_target=risk,
                                   account_policy=callback, guard_mask=self.schedule(305),
                                   guard_policy=lambda k, w: w * .7)
                    old = self.run_case(engine=self.original, **options)
                    self.assert_outputs_equal(old, self.run_case(**options))
                    self.assert_outputs_equal(old, self.run_case(initial_state=None,
                        issue_initial=True, allow_scheduled_hold=False, **options))


if __name__ == "__main__":
    unittest.main()
