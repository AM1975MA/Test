"""Synthetic integration checks for the frozen OLC111 runner and daily callback."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import run_olc111 as runner
from replay_engine import simulate


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = load(ROOT.parent / "olc110/source/src/core.py", "runner_toy_core")

    def setUp(self):
        dates = pd.bdate_range("2019-01-01", periods=340)
        panel = dict(dates=dates, names=np.array(["AAA", "BBB"]),
                     O=np.full((340, 2), 100.), C=np.full((340, 2), 100.),
                     observed=np.ones((340, 2), bool), benchmark=0)
        monthly = np.r_[dates.month[:-1] != dates.month[1:], False]
        feature_monthly = monthly.copy()
        feature_monthly[-1] = True
        self.bundle = dict(panel=panel, f=self.core.features(panel), core=self.core,
                           monthly=monthly, feature_monthly=feature_monthly,
                           targets=np.tile([0., 1.], (340, 1)),
                           breadth=np.full(340, .5), begin=300,
                           cboe=dict(available=np.ones(340, bool),
                                     legacy=np.zeros((340, 2)), term=np.zeros((340, 2))))
        self.bank = self.make_bank(dict(CASH=.01, FRESH=-.01, ENTRY=.01))
        self.bundle["bank"] = self.bank

    def make_bank(self, labels):
        result = {}
        for head in runner.HEADS:
            n = 280
            result[head] = dict(Xprice=np.zeros((n, 5 if head == "ENTRY" else 6)),
                                Xlegacy=np.zeros((n, 2)), Xterm=np.zeros((n, 2)),
                                y=np.full(n, labels[head]), signal_idx=np.arange(n),
                                terminal_idx=np.arange(n) + 21)
        return result

    def cache(self, bank=None, folder=None):
        return runner.MonthlyFitCache(self.bank if bank is None else bank,
                                     self.bundle["panel"]["dates"], 300, folder=folder,
                                     provenance="synthetic-only",
                                     fit_options=dict(min_dates=30, min_blocks=1, n_boot=20))

    def context(self, *, initial=False, scheduled=False):
        return dict(units=np.array([10., 0.]), cash=500., nav=1500., initial=initial,
                    scheduled=scheduled, pending=None, queued=(),
                    last_buy_idx=np.array([280, -1]), last_sell_idx=np.array([-1, -1]))

    def test_monthly_cutoff_uses_calendar_not_first_usable_bank_row(self):
        cache = self.cache()
        self.assertEqual(cache.cutoff(299), 299)
        self.assertEqual(cache.cutoff(310), 304)  # March 2, first panel day in March.
        fit = cache.get(310)["CASH"]
        self.assertEqual(fit["meta"]["cutoff"], 304)
        self.assertLess(fit["meta"]["max_terminal_idx"], 304)
        self.assertIs(cache.get(310), cache.get(312))

    def test_initial_is_baseline_even_when_every_head_is_ready(self):
        policy = runner.AccountPolicy(self.bundle, "TERM", self.cache())
        answer = policy(299, np.array([2./3., 0.]), self.context(initial=True))
        np.testing.assert_array_equal(answer["weights"], [0., 1.])
        self.assertEqual(answer["reason"], "INITIAL")
        self.assertTrue(answer["force"])

    def test_all_three_heads_are_required_before_learned_override(self):
        bank = deepcopy(self.bank)
        for key in bank["ENTRY"]:
            bank["ENTRY"][key] = bank["ENTRY"][key][:0]
        policy = runner.AccountPolicy(self.bundle, "PRICE", self.cache(bank))
        self.assertIsNone(policy(300, np.array([2./3., 0.]), self.context()))
        answer = policy(303, np.array([2./3., 0.]), self.context(scheduled=True))
        self.assertEqual(answer["reason"], "SCHEDULED")
        self.assertFalse(answer["force"])
        np.testing.assert_array_equal(answer["weights"], [0., 1.])
        self.assertFalse(policy.trace[-1]["model_ready_all"])

    def test_native_positive_buffer_is_not_charged_an_extra_cost_hurdle(self):
        bank = self.make_bank(dict(CASH=1e-8, FRESH=-.01, ENTRY=.01))
        policy = runner.AccountPolicy(self.bundle, "PRICE", self.cache(bank))
        answer = policy(300, np.array([2./3., 0.]), self.context())
        self.assertEqual(answer["reason"], "CASH")
        self.assertTrue(answer["force"])
        np.testing.assert_array_equal(answer["weights"], [0., 0.])
        self.assertGreater(policy.trace[-1]["cash_lower"], 0.)

    def test_busy_account_suppresses_new_discretionary_instruction(self):
        policy = runner.AccountPolicy(self.bundle, "PRICE", self.cache())
        context = self.context(scheduled=True)
        context["pending"] = {"due_idx": 301}
        self.assertIsNone(policy(300, np.array([2./3., 0.]), context))
        self.assertEqual(policy.trace[-1]["status"], "BUSY")

    def test_missing_cboe_falls_back_to_matching_price_model(self):
        self.bundle["cboe"]["available"][300] = False
        self.bundle["cboe"]["legacy"][300] = np.nan
        self.bundle["cboe"]["term"][300] = np.nan
        policy = runner.AccountPolicy(self.bundle, "TERM", self.cache())
        answer = policy(300, np.array([2./3., 0.]), self.context())
        self.assertEqual(answer["reason"], "CASH")
        self.assertTrue(policy.trace[-1]["fallback_price"])
        self.assertEqual(policy.trace[-1]["cash_model_arm"], "PRICE")

    def test_fresh_noop_does_not_issue_current_weight_rebalance(self):
        bank = self.make_bank(dict(CASH=-.01, FRESH=.01, ENTRY=.01))
        policy = runner.AccountPolicy(self.bundle, "MEAN", self.cache(bank))
        context = self.context(scheduled=True)
        context.update(units=np.array([0., 10.]), cash=0., nav=1000.)
        self.assertIsNone(policy(303, np.array([0., 1.]), context))
        self.assertEqual(policy.trace[-1]["action"], "HOLD")

    def test_real_toy_fit_scheduled_hold_preserves_quantities_through_gap(self):
        bank = self.make_bank(dict(CASH=-.01, FRESH=-.01, ENTRY=-.01))
        self.bundle["panel"]["O"][301:] = [200., 50.]
        self.bundle["panel"]["C"][301:] = [200., 50.]
        self.bundle["f"] = self.core.features(self.bundle["panel"])
        policy = runner.AccountPolicy(self.bundle, "TERM", self.cache(bank))
        schedule = np.zeros(340, bool)
        schedule[[300, 310]] = True
        result = simulate(self.bundle["panel"], self.bundle["f"], lambda k,w: [0.,1.],
                          schedule, legacy=self.core, account_policy=policy,
                          initial_state=dict(units=[10.,5.], cash=500.), issue_initial=False,
                          allow_scheduled_hold=True, start=str(self.bundle["panel"]["dates"][300]),
                          end=str(self.bundle["panel"]["dates"][320]))
        self.assertTrue(result["orders"].empty)
        self.assertEqual(result["daily"].iloc[-1].nav_close, 2750.)
        self.assertEqual(result["daily"].iloc[-1].cash, 500.)

    def test_cached_model_roundtrip_keeps_real_predictions(self):
        with tempfile.TemporaryDirectory() as folder:
            first = self.cache(folder=folder).get(310)["CASH"]["models"]["TERM"]
            second = self.cache(folder=folder).get(310)["CASH"]["models"]["TERM"]
            self.assertEqual(first.predict(np.ones(6), np.ones(2), np.ones(2)),
                             second.predict(np.ones(6), np.ones(2), np.ones(2)))

    def test_prequential_row_uses_its_calendar_fit_and_not_its_own_outcome(self):
        for head, bank in self.bank.items():
            for key in ("Xprice", "Xlegacy", "Xterm"):
                bank[key] = np.vstack((bank[key], np.zeros((1, bank[key].shape[1]))))
            bank["signal_idx"] = np.r_[bank["signal_idx"], 310]
            bank["terminal_idx"] = np.r_[bank["terminal_idx"], 331]
            bank["y"] = np.r_[bank["y"], 1e9]
        ledger = runner.prequential_forecasts(self.bundle, self.cache())
        row = ledger.query("head == 'CASH' and arm == 'PRICE' and signal_idx == 310").iloc[0]
        self.assertEqual(row.fit_cutoff_idx, 304)
        self.assertLess(row.max_training_terminal_idx, 304)
        self.assertAlmostEqual(row.prediction, .01)
        self.assertEqual(row.outcome, 1e9)

    def test_segment_return_uses_actual_preceding_nav(self):
        daily = pd.DataFrame(dict(k=[300,301,302,303], date=pd.bdate_range("2020-01-01",periods=4),
                                  nav_close=[11000.,12100.,13310.,14641.],
                                  nav_open=[10000.,11000.,12100.,13310.]))
        result = runner.performance_window(self.core, daily, start_idx=302)
        self.assertEqual(result["initial_nav"], 12100.)
        self.assertAlmostEqual(result["cumulative"], .21)

    def test_forecast_diagnostics_are_date_balanced_and_compare_term_to_vix(self):
        rows = []
        for arm, prediction in dict(MEAN=0., PRICE=1., VIX=1.5, TERM=2.).items():
            for signal, outcome in ((300, 0.), (300, 2.), (301, 1.)):
                rows.append(dict(head="CASH", arm=arm, signal_idx=signal,
                    prediction=prediction, lower=prediction-.1, outcome=outcome,
                    head_ready=True, all_heads_ready=True, positive_buffer=prediction > .1))
        scores, bins = runner.forecast_diagnostics(pd.DataFrame(rows))
        common = scores.query("support == 'ALL_HEADS_READY'").set_index("arm")
        # Date300 has total weight .5 (two rows); date301 has total weight .5.
        self.assertAlmostEqual(common.loc["MEAN", "mse"], 1.5)
        self.assertAlmostEqual(common.loc["PRICE", "mse"], .5)
        self.assertAlmostEqual(common.loc["PRICE", "bias"], 0.)
        self.assertAlmostEqual(common.loc["VIX", "mse"], .75)
        self.assertAlmostEqual(common.loc["TERM", "mse_delta_vs_vix"], .75)
        self.assertAlmostEqual(common.loc["TERM", "positive_buffer_realized_mean"], 1.)
        self.assertEqual(common.loc["TERM", "n_dates"], 2)
        self.assertEqual(len(bins.query("support == 'ALL_HEADS_READY'")), 4)

    def test_freeze_hashes_resolve_new_and_parent_source_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            root = parent / "olc111"
            (root / "docs").mkdir(parents=True)
            (root / "src").mkdir()
            (parent / "olc110").mkdir()
            (root / "src/new.py").write_text("new\n")
            (parent / "olc110/old.py").write_text("old\n")
            (root / "docs/DESIGN_AND_PROTOCOL.md").write_text("protocol\n")
            freeze = dict(code_hashes={"src/new.py": runner.sha(root / "src/new.py"),
                                      "../olc110/old.py": runner.sha(parent / "olc110/old.py")},
                          input_hashes={}, protocol_sha256=runner.sha(root / "docs/DESIGN_AND_PROTOCOL.md"),
                          arms=list(runner.ARMS), scenarios=list(runner.SCENARIOS), planned_paths=18)
            (root / "docs/EXPERIMENT_FREEZE.json").write_text(json.dumps(freeze))
            runner.verify_experiment_freeze(root)
            (parent / "olc110/old.py").write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "FREEZE"):
                runner.verify_experiment_freeze(root)


if __name__ == "__main__":
    unittest.main()
