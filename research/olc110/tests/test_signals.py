"""Behavioral checks for the opportunity hypothesis and information boundary."""
from pathlib import Path
import importlib.util
import sys
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
try:
    import signals
except ImportError:
    signals = None

spec = importlib.util.spec_from_file_location("legacy_signal_tests", ROOT / "source/src/core.py")
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)

def panel_fixture():
    n = 340
    dates = pd.bdate_range("2019-01-01", periods=n)
    rates = np.zeros((n, 6))
    rates[:, 0] = .0015
    rates[218:, 0] = .0003
    rates[:, 1] = .0012
    rates[218:, 1] = .0004
    rates[:, 2] = 0.
    rates[218:, 2] = .002
    rates[:, 3] = .0007
    rates[218:, 3] = -.0005
    rates[:, 4] = -.001
    rates[260:, 4] = .0001
    rates[:, 5] = .0001
    c = 100. * np.exp(np.cumsum(rates, axis=0))
    return dict(dates=dates, names=np.array(["OLD_A", "OLD_B", "NEW_C", "FADE_D", "WEAK_E", "FLAT_F"]),
                C=c, O=c.copy(), observed=np.ones_like(c, dtype=bool), benchmark=0)

class SignalTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(signals, "signals module not implemented")
        self.p = panel_fixture()
        self.f = signals.compute_features(self.p, legacy)
        self.k = 280

    def test_new_quarter_winner_is_detected_outside_annual_leaders(self):
        w, meta = signals.pick(self.p, self.f, self.k, "DUAL_SELECTIVE")
        np.testing.assert_array_equal(np.flatnonzero(w), [0, 2])
        np.testing.assert_allclose(w[[0, 2]], [.5, .5])
        self.assertEqual(meta["leader_indices"], [0, 1])
        self.assertTrue(meta["opportunity_used"])

    def test_fading_old_winner_and_negative_quarter_are_not_opportunities(self):
        _, meta = signals.pick(self.p, self.f, self.k, "EMERGING_ONLY")
        self.assertNotIn(3, meta["emerging_indices"])
        self.assertNotIn(4, meta["emerging_indices"])
        self.assertIn(2, meta["emerging_indices"])

    def test_without_new_opportunity_dual_falls_back_to_two_leaders(self):
        p = panel_fixture()
        p["C"][:, 2] = 100.
        p["O"] = p["C"].copy()
        f = signals.compute_features(p, legacy)
        w, meta = signals.pick(p, f, self.k, "DUAL_SELECTIVE")
        np.testing.assert_array_equal(np.flatnonzero(w), [0, 1])
        self.assertAlmostEqual(w.sum(), 1.)
        self.assertFalse(meta["opportunity_used"])

    def test_single_emerging_candidate_leaves_half_cash_in_diagnostic_sleeve(self):
        w, _ = signals.pick(self.p, self.f, self.k, "EMERGING_ONLY")
        np.testing.assert_array_equal(np.flatnonzero(w), [2])
        self.assertAlmostEqual(w[2], .5)

    def test_future_prices_and_masks_do_not_change_earlier_targets(self):
        q = {k: v.copy() if hasattr(v, "copy") else v for k, v in self.p.items()}
        q["C"][281:] *= np.linspace(1., 6., 59)[:, None]
        q["O"][281:] *= .5
        q["observed"][290:, 2] = False
        g = signals.compute_features(q, legacy)
        for key in ["b", "a", "acceleration", "rank_b", "rank_a", "eligible", "m21"]:
            np.testing.assert_allclose(self.f[key][:281], g[key][:281], equal_nan=True)
        for arm in signals.ARMS:
            w, _ = signals.pick(self.p, self.f, self.k, arm)
            v, _ = signals.pick(q, g, self.k, arm)
            np.testing.assert_array_equal(w, v)

    def test_leader_ties_break_by_identifier_and_do_not_duplicate(self):
        p = panel_fixture()
        p["C"][:, 1] = p["C"][:, 0]
        p["names"][:2] = ["ZZZ", "AAA"]
        f = signals.compute_features(p, legacy)
        w, meta = signals.pick(p, f, self.k, "LEADERS")
        self.assertEqual(meta["leader_indices"], [1, 0])
        self.assertEqual(np.count_nonzero(w), 2)

    def test_allocation_never_negative_leveraged_or_over_two_positions(self):
        for arm in signals.ARMS:
            w, _ = signals.pick(self.p, self.f, self.k, arm)
            self.assertTrue(np.isfinite(w).all())
            self.assertTrue((w >= 0.).all())
            self.assertLessEqual(w.sum(), 1. + 1e-12)
            self.assertLessEqual(np.count_nonzero(w), 2)

    def test_monthly_emergence_catches_new_month_after_quiet_five_months(self):
        self.assertIn("DUAL_SELECTIVE_21", signals.ARMS)
        p = panel_fixture()
        rates = np.zeros(len(p["dates"]))
        rates[301:] = .003
        p["C"][:, 2] = 100. * np.exp(np.cumsum(rates))
        p["O"] = p["C"].copy()
        f = signals.compute_features(p, legacy)
        w, meta = signals.pick(p, f, 321, "DUAL_SELECTIVE_21")
        np.testing.assert_array_equal(np.flatnonzero(w), [0, 2])
        self.assertTrue(meta["opportunity_used"])
        self.assertEqual(meta["horizon"], 21)

if __name__ == "__main__":
    unittest.main(verbosity=2)
