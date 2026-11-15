"""Real-account regressions for isolated protection and cash-funded reentry.

Each fixture uses hand-derived cash, quantities, and execution dates.  The
frozen OLC109 engine is the oracle only for the explicitly unchanged path.
"""
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


class AccountPolicyEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load(ROOT / "src/engine.py", "account_policy_engine_test")
        cls.original = load(ROOT / "research/engine/olc109_engine_reference.py",
                            "frozen_olc109_account_engine")
        cls.core = load(ROOT / "source/src/core.py", "account_policy_immutable_core")

    def setUp(self):
        self.panel = dict(dates=pd.bdate_range("2019-01-01", periods=340).values,
                          names=np.array(["AAA", "BBB"]),
                          O=np.full((340, 2), 100.), C=np.full((340, 2), 100.),
                          observed=np.ones((340, 2), bool), benchmark=0)

    def schedule(self, *indices):
        mask = np.zeros(340, bool)
        mask[list(indices)] = True
        return mask

    def run_case(self, *, panel=None, features=None, policy=None, mask=None,
                 engine=None, **kwargs):
        panel = self.panel if panel is None else panel
        features = self.core.features(panel) if features is None else features
        policy = (lambda k, w: [.5, .5]) if policy is None else policy
        mask = self.schedule() if mask is None else mask
        engine = self.engine if engine is None else engine
        if "account_policy" in kwargs:
            self.assertIn("account_policy", inspect.signature(engine.simulate).parameters,
                          "The optional account-policy execution path is missing")
        return engine.simulate(panel, features, policy, mask, legacy=self.core,
                               start=str(panel["dates"][300]), end=str(panel["dates"][320]),
                               ticket=kwargs.pop("ticket", 0.),
                               impact=kwargs.pop("impact", 0.), **kwargs)

    def account_policy(self, events, initial=(.5, .5), scheduled=None):
        def callback(k, current, context):
            if context["initial"]:
                return dict(weights=initial)
            if context["scheduled"]:
                return dict(weights=initial if scheduled is None else scheduled)
            return events.get(k)
        return callback

    def assert_equal_existing_outputs(self, left, right, *, exact_keys=True):
        for key in ("daily", "orders", "alerts", "instructions"):
            a, b = left[key], right[key]
            if not exact_keys:
                b = b.loc[:, a.columns]
            pd.testing.assert_frame_equal(a, b, check_exact=True, obj=key)
        self.assertEqual(len(left["decisions"]), len(right["decisions"]))
        for a, b in zip(left["decisions"], right["decisions"]):
            if exact_keys:
                self.assertEqual(a.keys(), b.keys())
            for key, value in a.items():
                if isinstance(value, np.ndarray):
                    np.testing.assert_array_equal(value, b[key], err_msg=key)
                else:
                    self.assertEqual(value, b[key], key)
        self.assertEqual(left["deferred_sessions"], right["deferred_sessions"])
        self.assertEqual(left["max_self_financing_error"], right["max_self_financing_error"])

    def test_none_preserves_every_frozen_olc109_output_exactly(self):
        # Changes in the old execution, guard, risk, or ledger path fail this.
        grid = np.arange(340)
        self.panel["C"][:, 0] = 100. * np.exp(.0005 * grid + .02 * np.sin(grid / 5.))
        self.panel["C"][:, 1] = 100. * np.exp(.0003 * grid + .02 * np.cos(grid / 7.))
        self.panel["O"][1:] = self.panel["C"][:-1]
        self.panel["O"][302:304, 1] = np.nan
        policy = lambda k, w: ([.6, .4] if k % 2 else [.2, .7], {"signal": k})
        for risk_target in (None, .01):
            with self.subTest(risk_target=risk_target):
                options = dict(policy=policy, mask=self.schedule(303, 306, 309, 312),
                               lag=2, ticket=1., impact=.0015, risk_target=risk_target,
                               guard_mask=self.schedule(305),
                               guard_policy=lambda k, w: w * .7)
                old = self.run_case(engine=self.original, **options)
                new = self.run_case(account_policy=None, **options)
                self.assert_equal_existing_outputs(old, new)

    def test_noop_adapter_preserves_all_existing_financial_and_decision_values(self):
        # A callback must not alter full rebalance semantics or add daily orders.
        selector = lambda k, w: ([.6, .4] if k % 2 else [.2, .7], {"signal": k})
        def adapter(k, current, context):
            if not (context["initial"] or context["scheduled"]):
                return None
            weights, meta = selector(k, current)
            return dict(weights=weights, meta=meta)
        options = dict(policy=selector, mask=self.schedule(303, 306, 309, 312),
                       lag=2, ticket=1., impact=.0015)
        self.assert_equal_existing_outputs(self.run_case(engine=self.original, **options),
                                           self.run_case(account_policy=adapter, **options),
                                           exact_keys=False)

    def test_callback_observes_actual_fills_pending_queue_and_every_nonfinal_close(self):
        # Requested entries cannot appear in last_buy_idx before an accepted fill.
        self.panel["O"][302:304, 0] = np.nan
        calls = {}
        def callback(k, current, context):
            calls[k] = (current.copy(), context)
            if context["initial"]:
                return dict(weights=[.5, 0.])
            if k == 304:
                return dict(weights=[0., 0.], action_mask=[True, False],
                            sell_only=True, force=True, reason="EXIT")
            return None
        result = self.run_case(account_policy=callback, lag=2)
        self.assertEqual(list(calls), list(range(299, 320)))
        self.assertTrue(calls[299][1]["initial"])
        self.assertFalse(calls[299][1]["scheduled"])
        self.assertIsNone(calls[299][1]["pending"])
        self.assertEqual(len(calls[299][1]["queued"]), 0)
        self.assertEqual(calls[300][1]["queued"][0]["due_idx"], 302)
        self.assertIsNone(calls[300][1]["pending"])
        self.assertEqual(calls[302][1]["pending"]["signal_idx"], 299)
        np.testing.assert_array_equal(calls[303][1]["last_buy_idx"], [-1, -1])
        np.testing.assert_array_equal(calls[304][1]["units"], [50., 0.])
        np.testing.assert_array_equal(calls[304][0], [.5, 0.])
        np.testing.assert_array_equal(calls[304][1]["last_buy_idx"], [304, -1])
        self.assertEqual((calls[304][1]["cash"], calls[304][1]["nav"]), (5000., 10000.))
        np.testing.assert_array_equal(calls[306][1]["last_sell_idx"], [-1, -1])
        np.testing.assert_array_equal(calls[307][1]["last_sell_idx"], [307, -1])
        self.assertEqual(list(result["orders"].execution_idx), [304, 307])
        self.assertEqual(result["deferred_sessions"], 2)

    def test_masked_exit_does_not_sell_unaffected_favorable_open_gap(self):
        # Without masking core quotes BBB would be cut from 50 to 37.5 units.
        self.panel["O"][301:, 1] = 200.
        self.panel["C"][301:, 1] = 200.
        account = self.account_policy({300: dict(weights=[0., .5],
                    action_mask=[True, False], sell_only=True, force=True, reason="EXIT_A")})
        result = self.run_case(account_policy=account)
        trades = result["orders"].query("signal_idx == 300")
        self.assertEqual(list(trades.ticker), ["AAA"])
        self.assertEqual(list(trades.side), ["SELL"])
        self.assertEqual(list(trades.quantity), [50.])
        self.assertEqual(result["daily"].iloc[1].nav_open, 15000.)
        self.assertEqual(result["daily"].iloc[1].nav_close, 15000.)
        self.assertEqual(result["daily"].iloc[1].cash, 5000.)
        self.assertEqual(result["instructions"].iloc[-1].action_indices, [0])

    def test_masked_buy_uses_available_cash_and_never_sells_untouched_asset(self):
        # Cash funds the entry despite a gap making its nominal target too large.
        self.panel["O"][301:, 1] = 200.
        self.panel["C"][301:, 1] = 200.
        account = self.account_policy({300: dict(weights=[.5, .5],
                    action_mask=[True, False], force=True, reason="REENTER")}, initial=[0., .5])
        result = self.run_case(account_policy=account, ticket=2., impact=.01)
        trades = result["orders"].query("signal_idx == 300")
        self.assertEqual(list(trades.ticker), ["AAA"])
        self.assertEqual(list(trades.side), ["BUY"])
        # Initial BBB notional 5000, fee 52, remaining cash 4948.
        self.assertAlmostEqual(trades.iloc[0].notional, 4946. / 1.01)
        self.assertAlmostEqual(result["daily"].iloc[1].cash, 0.)
        self.assertEqual(len(result["orders"].query("ticker == 'BBB'")), 1)
        self.assertGreaterEqual(result["daily"].cash.min(), 0.)
        self.assertLess(result["max_self_financing_error"], 1e-8)

    def test_target_budget_preserves_unmasked_signal_exposure(self):
        # A sparse desired target may not ignore the already committed capital.
        account = self.account_policy({300: dict(weights=[.8, 0.],
                    action_mask=[True, False], force=True, reason="PROBE")}, initial=[0., .5])
        result = self.run_case(account_policy=account)
        instruction = result["instructions"].iloc[-1]
        self.assertEqual(instruction.raw_weights, (.8, 0.))
        self.assertEqual(instruction.target_weights, (.5, .5))
        self.assertEqual(list(result["orders"].query("signal_idx == 300").quantity), [50.])

    def test_only_missing_masked_quotes_defer_an_instruction(self):
        # An unexecutable untouched holding must not keep a completed exit pending.
        self.panel["O"][301:303, 0] = np.nan
        self.panel["O"][301:, 1] = np.nan
        seen = {}
        base = self.account_policy({300: dict(weights=[0., .5],
                    action_mask=[True, False], sell_only=True, force=True, reason="EXIT_A")})
        def callback(k, current, context):
            seen[k] = context
            return base(k, current, context)
        result = self.run_case(account_policy=callback)
        trades = result["orders"].query("signal_idx == 300")
        self.assertEqual(list(trades.execution_idx), [303])
        self.assertEqual(list(trades.ticker), ["AAA"])
        self.assertEqual(result["deferred_sessions"], 2)
        self.assertIsNotNone(seen[302]["pending"])
        self.assertIsNone(seen[303]["pending"])
        np.testing.assert_array_equal(seen[303]["units"], [0., 50.])

    def test_open_observed_gate_is_respected_for_the_masked_asset(self):
        self.panel["open_observed"] = np.ones((340, 2), bool)
        self.panel["open_observed"][301, 0] = False
        account = self.account_policy({300: dict(weights=[0., .5],
                    action_mask=[True, False], sell_only=True, force=True)})
        result = self.run_case(account_policy=account)
        self.assertEqual(list(result["orders"].query("signal_idx == 300").execution_idx), [302])
        self.assertEqual(result["deferred_sessions"], 1)

    def test_account_action_waits_for_its_own_next_open_plus_lag(self):
        # Neither a same-Close fill nor reuse of an older due date is permitted.
        account = self.account_policy({303: dict(weights=[0., .5],
                    action_mask=[True, False], sell_only=True, force=True, reason="EXIT_A")})
        result = self.run_case(account_policy=account, lag=2)
        self.assertEqual(list(result["orders"].execution_idx), [302, 302, 306])
        self.assertEqual(list(result["orders"].query("signal_idx == 303").due_idx), [306])
        self.assertEqual(result["daily"].query("k == 305").iloc[0].positions, 2)

    def test_sell_only_rejects_addition_even_when_total_exposure_falls(self):
        for action_mask in (None, [True, True], [False, True]):
            account = self.account_policy({300: dict(weights=[0., .6],
                        action_mask=action_mask, sell_only=True)})
            with self.subTest(action_mask=action_mask), self.assertRaisesRegex(
                    ValueError, "ACCOUNT_ADDS"):
                self.run_case(account_policy=account)

    def test_sell_only_ignores_nominal_weights_outside_the_action_mask(self):
        # A valid exit cannot be rejected because an untouched slot has a
        # different nominal target; both higher and lower intent are ignored.
        self.panel["O"][301:, 0] = 125.
        self.panel["C"][301:, 0] = 125.
        for nominal_unaffected in (.5, .2):
            with self.subTest(nominal_unaffected=nominal_unaffected):
                seen = {}
                base = self.account_policy({300: dict(weights=[nominal_unaffected, 0.],
                           action_mask=[False, True], sell_only=True, force=True,
                           reason="EXIT_B")}, initial=[.4, .6])
                def callback(k, current, context):
                    seen[k] = context
                    return base(k, current, context)
                try:
                    result = self.run_case(account_policy=callback)
                except ValueError as error:
                    self.fail(f"Untouched nominal exposure rejected a valid masked exit: {error}")
                instruction = result["instructions"].iloc[-1]
                self.assertEqual(instruction.raw_weights, (nominal_unaffected, 0.))
                self.assertEqual(instruction.target_weights, (.4, 0.))
                self.assertEqual(instruction.action_indices, [1])
                trades = result["orders"].query("signal_idx == 300")
                self.assertEqual(list(trades.ticker), ["BBB"])
                self.assertEqual(list(trades.side), ["SELL"])
                self.assertEqual(list(trades.quantity), [60.])
                np.testing.assert_array_equal(seen[301]["units"], [40., 0.])
                self.assertEqual(seen[301]["cash"], 6000.)
                self.assertEqual(seen[301]["nav"], 11000.)

    def test_sell_only_stale_instruction_cannot_rebuy_an_earlier_sale(self):
        # The second signal is valid at Close 304 but A was sold by its execution.
        self.panel["O"][307, 0] = 10.
        account = self.account_policy({
            303: dict(weights=[0., .5], action_mask=[True, False],
                      sell_only=True, force=True, reason="EXIT_A"),
            304: dict(weights=[.5, 0.], action_mask=[True, True],
                      sell_only=True, force=True, reason="EXIT_B")})
        result = self.run_case(account_policy=account, lag=2)
        trades = result["orders"].query("signal_idx >= 303")
        self.assertEqual(list(trades.execution_idx), [306, 307])
        self.assertEqual(list(trades.ticker), ["AAA", "BBB"])
        self.assertEqual(list(trades.side), ["SELL", "SELL"])
        self.assertEqual(result["daily"].iloc[-1].positions, 0)

    def test_returned_weights_mask_and_metadata_are_frozen_at_issue(self):
        # Reusing mutable callback buffers must not rewrite an eligible order.
        target = np.array([0., .5])
        action_mask = np.array([True, False])
        metadata = {"nested": {"event": "original"}}
        def callback(k, current, context):
            if context["initial"]:
                return dict(weights=[.5, .5])
            if k == 303:
                return dict(weights=target, action_mask=action_mask, meta=metadata,
                            sell_only=True, force=True, reason="EXIT_A")
            if k == 304:
                target[:] = [1., 0.]
                action_mask[:] = [False, True]
                metadata["nested"]["event"] = "mutated"
            return None
        result = self.run_case(account_policy=callback, lag=2)
        instruction = result["instructions"].iloc[-1]
        self.assertEqual(instruction.target_weights, (0., .5))
        self.assertEqual(instruction.action_indices, [0])
        self.assertEqual(instruction.meta, {"nested": {"event": "original"}})
        decision = result["decisions"][-1]
        self.assertEqual(decision["meta"], {"nested": {"event": "original"}})
        self.assertEqual(list(result["orders"].query("signal_idx == 303").ticker), ["AAA"])

    def test_context_arrays_and_immutable_summaries_cannot_change_account_or_queue(self):
        # Even deliberate mutation of detached snapshots cannot create cash or fills.
        calls = {}
        def callback(k, current, context):
            calls[k] = (current.copy(), context)
            if context["initial"]:
                return dict(weights=[.5, 0.])
            if k == 300:
                summary = context["queued"][0]
                with self.assertRaises(TypeError):
                    summary["due_idx"] = 300
                with self.assertRaises(TypeError):
                    summary["target_weights"][0] = 1.
                context["units"].setflags(write=True)
                context["units"][:] = 999.
                context["last_buy_idx"].setflags(write=True)
                context["last_buy_idx"][:] = 300
                current[:] = 1.
                context["cash"] = 999999.
            return None
        result = self.run_case(account_policy=callback, lag=2)
        self.assertEqual(list(result["orders"].execution_idx), [302])
        self.assertEqual(list(result["orders"].quantity), [50.])
        self.assertEqual(calls[301][1]["cash"], 10000.)
        np.testing.assert_array_equal(calls[301][1]["units"], [0., 0.])
        np.testing.assert_array_equal(calls[301][1]["last_buy_idx"], [-1, -1])

    def test_scheduled_full_instruction_supersedes_partial_only_after_its_due_date(self):
        # Future monthly instructions may not cancel today's eligible exit.
        calls = {}
        base = self.account_policy({303: dict(weights=[0., .5],
                    action_mask=[True, False], sell_only=True, force=True, reason="EXIT_A")},
                    scheduled=[.2, .8])
        def callback(k, current, context):
            calls[k] = context
            return base(k, current, context)
        def forbidden_selector(k, current):
            self.fail("An account policy owns the initial and scheduled targets")
        result = self.run_case(account_policy=callback, policy=forbidden_selector,
                               mask=self.schedule(304), lag=2)
        self.assertTrue(calls[304]["scheduled"])
        self.assertFalse(calls[304]["initial"])
        trades = result["orders"].query("signal_idx >= 303")
        self.assertEqual(list(trades.execution_idx), [306, 307, 307])
        self.assertEqual(list(trades.ticker), ["AAA", "AAA", "BBB"])
        self.assertEqual(list(trades.side), ["SELL", "BUY", "BUY"])
        self.assertEqual(list(trades.quantity), [50., 20., 30.])
        self.assertEqual(result["instructions"].iloc[-1].reason, "SCHEDULED")
        self.assertIsNone(result["instructions"].iloc[-1].action_indices)
        self.assertEqual([decision["k"] for decision in result["decisions"]], [299, 303, 304])

    def test_scheduled_full_instruction_can_supersede_a_missing_quote_pending_exit(self):
        self.panel["O"][306, 0] = np.nan
        account = self.account_policy({303: dict(weights=[0., .5],
                    action_mask=[True, False], sell_only=True, force=True, reason="EXIT_A")},
                    scheduled=[0., 1.])
        result = self.run_case(account_policy=account, mask=self.schedule(304), lag=2)
        trades = result["orders"].query("execution_idx > 302")
        self.assertEqual(list(trades.execution_idx), [307, 307])
        self.assertEqual(list(trades.signal_idx), [304, 304])
        self.assertEqual(list(trades.ticker), ["AAA", "BBB"])
        self.assertEqual(result["deferred_sessions"], 1)

    def test_initial_and_scheduled_require_complete_callback_instructions(self):
        for fail_initial in (True, False):
            def callback(k, current, context):
                if context["initial"] and not fail_initial:
                    return dict(weights=[.5, .5])
                return None
            with self.subTest(fail_initial=fail_initial), self.assertRaisesRegex(
                    ValueError, "ACCOUNT_POLICY_REQUIRED"):
                self.run_case(account_policy=callback, mask=self.schedule(300))

    def test_scheduled_partial_masks_are_rejected_and_full_masks_are_normalized(self):
        for action_mask in ([True, False], [False, False]):
            with self.subTest(action_mask=action_mask), self.assertRaisesRegex(
                    ValueError, "ACCOUNT_SCHEDULED_MASK"):
                self.run_case(account_policy=lambda k, w, c: dict(
                    weights=[.5, .5], action_mask=action_mask))
        result = self.run_case(account_policy=lambda k, w, c:
                               dict(weights=[.5, .5], action_mask=[True, True])
                               if c["initial"] else None)
        self.assertIsNone(result["instructions"].iloc[0].action_indices)

    def test_invalid_targets_masks_and_callback_results_are_rejected(self):
        for target in ([np.nan, 0.], [-.1, .1], [.6, .6], [.1]):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "WEIGHTS"):
                self.run_case(account_policy=lambda k, w, c: dict(weights=target))
        for action_mask in ([True], [1, 0], [[True, False]]):
            account = self.account_policy({300: dict(weights=[0., .5], action_mask=action_mask)})
            with self.subTest(action_mask=action_mask), self.assertRaisesRegex(ValueError, "ACTION_MASK"):
                self.run_case(account_policy=account)
        for answer in ([.5, .5], {"meta": {}}, {"weights": [.5, .5], "meta": []}):
            with self.subTest(answer=answer), self.assertRaisesRegex(ValueError, "ACCOUNT_POLICY_RESULT"):
                self.run_case(account_policy=lambda k, w, c: answer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
