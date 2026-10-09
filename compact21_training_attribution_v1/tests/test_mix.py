"""Fail-closed tests for a pure, research-only training-source mixer."""
import unittest
import pandas as pd
import numpy as np

from compact21_training_attribution_v1.mix import mixed_training, assert_common_training_keys

F = ("f1", "f2")
def fixture(shift):
    return pd.DataFrame({
        "signal_date": pd.to_datetime(["2015-01-30", "2015-01-30", "2015-02-27"]),
        "ticker": ["AAA", "BBB", "AAA"],
        "f1": [1.0 + shift, 2.0, np.nan],
        "f2": [0.1, 0.2 + shift, 0.3],
        "target_rank_21": [0.8 + shift, 0.2, 0.5],
        "exit_date_21": pd.to_datetime(["2015-03-02", "2015-03-02", "2015-03-30"]),
        "fwd_ret_21": [0.11 + shift, -0.01, 0.04],
        "untouched": [10, 20, 30],
    })


class TestMix(unittest.TestCase):
    def test_only_labels_are_swapped(self):
        a, b = fixture(0), fixture(.01)
        z = mixed_training(a, b, feature_cols=F, feature_source="own", label_source="repeat2")
        pd.testing.assert_frame_equal(z[list(F)], a[list(F)], check_exact=True)
        pd.testing.assert_frame_equal(z[["target_rank_21", "exit_date_21", "fwd_ret_21"]],
                                      b[["target_rank_21", "exit_date_21", "fwd_ret_21"]], check_exact=True)
        pd.testing.assert_frame_equal(z[["signal_date", "ticker", "untouched"]],
                                      a[["signal_date", "ticker", "untouched"]], check_exact=True)

    def test_only_features_are_swapped(self):
        a, b = fixture(0), fixture(.01)
        z = mixed_training(a, b, feature_cols=F, feature_source="repeat2", label_source="own")
        pd.testing.assert_frame_equal(z[list(F)], b[list(F)], check_exact=True)
        pd.testing.assert_frame_equal(z[["target_rank_21", "exit_date_21", "fwd_ret_21"]],
                                      a[["target_rank_21", "exit_date_21", "fwd_ret_21"]], check_exact=True)

    def test_same_vintage_is_byte_identical(self):
        a = fixture(0)
        z = mixed_training(a, a, feature_cols=F, feature_source="repeat2", label_source="repeat2")
        pd.testing.assert_frame_equal(z, a, check_exact=True)

    def test_reject_row_coverage_change(self):
        a,b=fixture(0),fixture(.01).iloc[:-1]
        with self.assertRaises(ValueError):
            assert_common_training_keys({1:a,2:b,3:a})
        with self.assertRaises(ValueError):
            mixed_training(a, b, feature_cols=F, feature_source="own", label_source="repeat2")

    def test_reject_ordered_key_mismatch(self):
        a,b=fixture(0),fixture(.01).iloc[[1,0,2]].reset_index(drop=True)
        with self.assertRaises(ValueError):
            mixed_training(a, b, feature_cols=F, feature_source="own", label_source="repeat2")

    def test_reject_duplicate_keys_and_missing_feature(self):
        a,b=fixture(0),fixture(.01)
        b.loc[1, "ticker"]="AAA"
        with self.assertRaises(ValueError):
            mixed_training(a, b, feature_cols=F, feature_source="repeat2", label_source="own")
        with self.assertRaises(ValueError):
            mixed_training(a, a.drop(columns="f2"), feature_cols=F, feature_source="repeat2", label_source="own")

    def test_original_inputs_are_not_mutated(self):
        a,b=fixture(0),fixture(.01)
        ca,cb=a.copy(deep=True),b.copy(deep=True)
        mixed_training(a, b, feature_cols=F, feature_source="own", label_source="repeat2")
        pd.testing.assert_frame_equal(a,ca,check_exact=True)
        pd.testing.assert_frame_equal(b,cb,check_exact=True)

    def test_reject_unknown_source(self):
        a = fixture(0)
        with self.assertRaises(ValueError):
            mixed_training(a, a, feature_cols=F, feature_source="foo", label_source="own")


if __name__ == "__main__":
    unittest.main()
