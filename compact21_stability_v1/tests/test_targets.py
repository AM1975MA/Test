import numpy as np
import pandas as pd
import unittest

from compact21_stability_v1.targets import (
    RETURN_QUANTUM,
    build_labels,
    quantize_returns,
    training_labels,
)


def panel(outcomes, dates=None):
    frame = pd.DataFrame({
        "signal_date": dates or ["2020-01-02"] * len(outcomes),
        "ticker": [f"T{i}" for i in range(len(outcomes))],
        "fwd_ret_21": outcomes,
        "exit_date_21": "2020-02-03",
    })
    frame["target_rank_21"] = frame.groupby("signal_date")["fwd_ret_21"].rank(pct=True)
    return frame


class TargetTests(unittest.TestCase):
    def test_economic_ties_and_negative_returns(self):
        f = panel([-0.020021, -0.020019, 0, 0.000019, 0.020001])
        assert training_labels(f, "2021-01-01").tolist() == [0, 0, 1, 1, 2]
    
    
    def test_row_and_ticker_order_do_not_break_ties(self):
        f = panel([0.001001, 0.001002, -0.002, 0.004])
        original = build_labels(f)
        shuffled = f.iloc[[3, 1, 0, 2]].copy()
        shuffled["ticker"] = ["Z", "B", "A", "C"]
        assert build_labels(shuffled).sort_index().equals(original)
        # Repeated dataframe index labels do not change positional assignment.
        shuffled.index = [0, 0, 0, 0]
        assert build_labels(shuffled).tolist() == [2, 1, 1, 0]
    
    
    def test_dates_are_ranked_independently(self):
        f = panel([0.01, 0.02, -0.02, -0.01], ["2020-01-02"] * 2 + ["2020-01-03"] * 2)
        assert build_labels(f).tolist() == [0, 1, 0, 1]
    
    
    def test_fixed_grid_removes_interior_small_perturbations(self):
        a = panel([0.001001, 0.001003, 0.002001, 0.003002])
        b = panel([0.001002, 0.001004, 0.002002, 0.003001])
        assert build_labels(a).equals(build_labels(b))
        assert RETURN_QUANTUM == 0.0001
    
    
    def test_grid_edges_have_no_invariance_guarantee(self):
        q = quantize_returns(np.array([0.00005 - 1e-12, 0.00005 + 1e-12]))
        assert q.tolist() == [0, 1]
    
    
    def test_ordinal_isolates_percentile_rounding(self):
        a = panel([0.01, 0.02, 0.03])
        a["target_rank_21"] = [0.104999999, 0.105000001, 0.9]
        b = a.copy()
        b["target_rank_21"] = [0.105000002, 0.105000003, 0.900000001]
        assert build_labels(a, "ordinal").tolist() == [0, 1, 2]
        assert build_labels(a, "ordinal").equals(build_labels(b, "ordinal"))
        assert not build_labels(a, "legacy").equals(build_labels(b, "legacy"))
    
    
    def test_invalid_labels_retained_and_not_trainable(self):
        f = panel([0.01, np.nan, 0.02])
        labels = build_labels(f)
        assert labels.iloc[0] == 0 and np.isnan(labels.iloc[1]) and labels.iloc[2] == 1
        with self.assertRaisesRegex(ValueError, "Invalid"):
            training_labels(f, "2021-01-01")
        f.loc[1, "fwd_ret_21"] = np.inf
        assert np.isnan(build_labels(f).iloc[1])
    
    
    def test_maturity_strictly_before_cutoff(self):
        for column, value in [("signal_date", "2021-01-01"), ("exit_date_21", "2021-01-01"), ("exit_date_21", None)]:
            with self.subTest(column=column, value=value):
                f = panel([0.01, 0.02])
                f.loc[0, column] = value
                with self.assertRaisesRegex(ValueError, "Immature"):
                    training_labels(f, "2021-01-01")
    
    
    def test_no_future_outcomes_are_used_to_configure_quantum(self):
        past = panel([0.001001, 0.001002, 0.002001])
        future = panel([-0.99, 9, 0.7])
        future["signal_date"] = "2025-01-01"
        combined = pd.concat([past, future], ignore_index=True)
        assert build_labels(combined).iloc[:3].tolist() == build_labels(past).tolist()
    
    
    def test_duplicate_keys_rejected(self):
        f = panel([0.01, 0.02])
        f.loc[1, "ticker"] = f.loc[0, "ticker"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            build_labels(f)
    
    
    def test_rank_source_mismatches_rejected(self):
        f = panel([0.01, 0.02])
        f.loc[0, "target_rank_21"] = np.nan
        with self.assertRaisesRegex(ValueError, "validity mismatch"):
            build_labels(f)
        f = panel([0.01, 0.02])
        f["target_rank_21"] = [1.0, 0.5]
        with self.assertRaisesRegex(ValueError, "ordering or tie mismatch"):
            build_labels(f)
    
    
    def test_subset_percentile_denominators_need_not_match(self):
        f = panel([0.01, 0.02, 0.03, 0.04]).iloc[[0, 3]]
        assert f.target_rank_21.tolist() == [0.25, 1.0]
        assert build_labels(f).tolist() == [0, 1]
    
    
    def test_oversized_coordinate_rejected(self):
        with self.assertRaisesRegex(ValueError, "coordinate range"):
            quantize_returns(np.array([1e300]))


if __name__ == "__main__":
    unittest.main()
