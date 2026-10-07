"""Synthetic-only invariants; no live ETF data or training required."""
from __future__ import annotations

import unittest
import numpy as np
import pandas as pd

from target_redesign_level2_v1.targets import (
    build_forward_targets,
    mature_training_rows,
)


class TargetRedesignTests(unittest.TestCase):
    def setUp(self):
        self.dates = pd.bdate_range("2020-01-01", periods=70)
        self.O = pd.DataFrame(100.0, index=self.dates, columns=["AAA", "BBB", "BIL", "SPY"])
        self.O.loc[:, "BIL"] = 100.0
        self.O.loc[:, "SPY"] = 100.0
        self.O.iloc[23, self.O.columns.get_loc("AAA")] = 110.0
        self.O.iloc[23, self.O.columns.get_loc("BIL")] = 101.0
        self.O.iloc[23, self.O.columns.get_loc("SPY")] = 102.0
        self.L = self.O * 0.99
        self.L.iloc[5, self.L.columns.get_loc("AAA")] = 70.0
        self.L.iloc[23, self.L.columns.get_loc("AAA")] = 1.0  # Not held after exit open.
        self.panel = pd.DataFrame({
            "signal_date": [self.dates[1], self.dates[1]],
            "entry_date": [self.dates[2], self.dates[2]],
            "exit_date_21": [self.dates[23], self.dates[23]],
            "exit_date_42": [self.dates[44], self.dates[44]],
            "exit_date_63": [self.dates[65], self.dates[65]],
            "ticker": ["AAA", "BBB"],
            "fwd_ret_21": [0.1, 0.0],
        })

    def target(self, **kwargs):
        return build_forward_targets(self.panel, self.O, self.L, **kwargs)

    def test_next_open_economics_and_cost(self):
        t = self.target()
        expected_net = 1.1 * 0.999 ** 2 - 1.0
        self.assertAlmostEqual(t.loc[0, "gross_ret_21"], 0.10)
        self.assertAlmostEqual(t.loc[0, "net_ret_21"], expected_net)
        self.assertAlmostEqual(t.loc[0, "alpha_cash_log_21"],
                               np.log1p(expected_net) - np.log(1.01))
        self.assertAlmostEqual(t.loc[0, "alpha_spy_log_21"],
                               np.log1p(expected_net) - np.log(1.02))
        self.assertAlmostEqual(t.loc[1, "net_ret_21"], 0.999 ** 2 - 1)
        self.assertAlmostEqual(t.loc[0, "adverse_excursion_21"], 0.30)
        self.assertAlmostEqual(t.loc[1, "adverse_excursion_21"], 0.01)

    def test_multiple_horizons_have_distinct_targets(self):
        t = self.target()
        self.assertAlmostEqual(t.loc[0, "gross_ret_42"], 0.0)
        self.assertAlmostEqual(t.loc[0, "gross_ret_63"], 0.0)
        self.assertIn("adverse_excursion_63", t.columns)
        self.assertEqual(len(t), 2)

    def test_no_backfilling_of_cash_reference(self):
        O = self.O.copy()
        O.iloc[2, O.columns.get_loc("BIL")] = np.nan
        t = build_forward_targets(self.panel, O, self.L, horizons=(21,))
        self.assertTrue(t.alpha_cash_log_21.isna().all())
        self.assertTrue(t.alpha_spy_log_21.notna().all())
        self.assertTrue(t.net_ret_21.notna().all())

    def test_immature_rows_are_excluded(self):
        labeled = self.target()
        before = mature_training_rows(labeled, self.dates[23], horizon=21)
        after = mature_training_rows(labeled, self.dates[24], horizon=21)
        self.assertTrue(before.empty)
        self.assertEqual(len(after), 2)
        self.assertTrue(mature_training_rows(labeled, self.dates[44], horizon=42).empty)

    def test_low_path_does_not_touch_exit_session(self):
        a = self.target(horizons=(21,))
        L = self.L.copy()
        L.iloc[23, L.columns.get_loc("AAA")] = 60.0
        b = build_forward_targets(self.panel, self.O, L, horizons=(21,))
        self.assertAlmostEqual(a.loc[0, "adverse_excursion_21"],
                               b.loc[0, "adverse_excursion_21"])

    def test_missing_low_does_not_manufacture_downside(self):
        L = self.L.copy()
        L.iloc[10, L.columns.get_loc("AAA")] = np.nan
        t = build_forward_targets(self.panel, self.O, L, horizons=(21,))
        self.assertTrue(np.isnan(t.loc[0, "adverse_excursion_21"]))
        self.assertTrue(np.isfinite(t.loc[0, "net_ret_21"]))

    def test_shuffled_panel_is_order_invariant(self):
        original = self.target(horizons=(21,)).sort_values("ticker").reset_index(drop=True)
        shuffle = self.panel.iloc[[1, 0]].copy()
        shuffle.index = [3, 3]  # repeated indexes must not change numeric alignment
        rerun = build_forward_targets(shuffle, self.O, self.L, horizons=(21,))
        rerun = rerun.sort_values("ticker").reset_index(drop=True)
        for col in ("gross_ret_21", "net_ret_21", "alpha_cash_log_21",
                    "alpha_spy_log_21", "adverse_excursion_21"):
            np.testing.assert_allclose(original[col], rerun[col], rtol=0, atol=0)

    def test_fail_closed_on_wrong_exit(self):
        p = self.panel.copy()
        p.loc[0, "exit_date_21"] = self.dates[22]
        with self.assertRaisesRegex(ValueError, "exactly 21 sessions"):
            build_forward_targets(p, self.O, self.L, horizons=(21,))

    def test_fail_closed_on_forward_return_inconsistency(self):
        p = self.panel.copy()
        p.loc[0, "fwd_ret_21"] = 0.11
        with self.assertRaisesRegex(ValueError, "differs"):
            build_forward_targets(p, self.O, self.L, horizons=(21,))

    def test_absent_benchmark_is_fatal(self):
        with self.assertRaisesRegex(ValueError, "Missing reference ETF"):
            build_forward_targets(self.panel, self.O.drop(columns="BIL"),
                                  self.L.drop(columns="BIL"), horizons=(21,))

    def test_invalid_input_cost_and_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError, "side_cost"):
            self.target(side_cost=-0.01)
        p = pd.concat([self.panel, self.panel.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            build_forward_targets(p, self.O, self.L, horizons=(21,))


if __name__ == "__main__":
    unittest.main()
