import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from compact21_learner_swap_v1.integrity import compare_panels, dataframe_fingerprint, write_ma3_evidence


class IntegrityTest(unittest.TestCase):
    def panel(self):
        return pd.DataFrame({"signal_date": pd.to_datetime(["2020-01-31", "2020-01-31", "2020-02-29"]),
                             "ticker": ["A", "B", "A"], "x": [0., 1., np.nan],
                             "y": [2., np.inf, -np.inf], "label": pd.array([1, None, 3], dtype="Int64")})

    def assert_different(self, other):
        self.assertFalse(compare_panels(self.panel(), other)["exact_equal"])

    def test_block_layout_and_pickle_bytes_irrelevant(self):
        original = self.panel()
        alternate = pd.DataFrame(index=original.index)
        for column in original:
            alternate[column] = original[column].copy()
        self.assertNotEqual(len(original._mgr.blocks), len(alternate._mgr.blocks))
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / "a.pkl", Path(td) / "b.pkl"
            original.to_pickle(a)
            alternate.to_pickle(b)
            self.assertNotEqual(a.read_bytes(), b.read_bytes())
            self.assertTrue(compare_panels(pd.read_pickle(a), pd.read_pickle(b))["exact_equal"])

    def test_ulp_change_detected(self):
        other = self.panel(); other.loc[1, "x"] = np.nextafter(1., np.inf)
        result = compare_panels(self.panel(), other)
        self.assertFalse(result["exact_equal"])
        self.assertEqual(result["max_abs_diff"], np.spacing(1.))

    def test_signed_zero_detected(self):
        other = self.panel(); other.loc[0, "x"] = -0.
        self.assert_different(other)

    def test_nan_payload_normalized(self):
        other = self.panel()
        other.loc[2, "x"] = np.array([0x7FF8000000000123], dtype=np.uint64).view(np.float64)[0]
        self.assertTrue(compare_panels(self.panel(), other)["exact_equal"])

    def test_missing_mask_change_detected(self):
        other = self.panel(); other.loc[1, "x"] = np.nan; other.loc[2, "x"] = 1.
        self.assert_different(other)

    def test_infinity_sign_and_missing_detected(self):
        for value in [-np.inf, np.nan, 1.]:
            other = self.panel(); other.loc[1, "y"] = value
            self.assert_different(other)

    def test_dtype_detected(self):
        other = self.panel(); other["x"] = other.x.astype("float32")
        self.assertFalse(compare_panels(self.panel(), other)["schema_equal"])
        self.assert_different(other)

    def test_index_and_keys_detected(self):
        other = self.panel(); other.index = [1, 2, 3]
        self.assertFalse(compare_panels(self.panel(), other)["index_equal"])
        self.assert_different(other)
        other = self.panel(); other.loc[0, "ticker"] = "B"
        self.assertFalse(compare_panels(self.panel(), other)["key_equal"])
        self.assert_different(other)

    def test_row_column_order_detected(self):
        self.assert_different(self.panel().iloc[::-1].reset_index(drop=True))
        self.assert_different(self.panel()[list(reversed(self.panel().columns))])

    def test_nullable_categorical_timezone_metadata(self):
        frame = pd.DataFrame({"a": pd.Categorical(["x", "y"], ordered=False),
                              "b": pd.date_range("2020-01-01", periods=2, tz="UTC")})
        other = frame.copy(); other["a"] = other.a.cat.as_ordered()
        self.assertFalse(compare_panels(frame, other)["exact_equal"])
        other = frame.copy(); other["b"] = other.b.dt.tz_convert("Europe/Rome")
        self.assertFalse(compare_panels(frame, other)["exact_equal"])

    def test_duplicate_columns_and_unsupported_object_fail(self):
        with self.assertRaises(ValueError):
            dataframe_fingerprint(pd.DataFrame([[1, 2]], columns=["a", "a"]))
        with self.assertRaises(TypeError):
            dataframe_fingerprint(pd.DataFrame({"a": [object()]}))

    def test_evidence_files_retained_and_repeatable(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            self.panel().to_pickle(path / "RAW_FEATURE_PANEL.pkl")
            self.panel()[["signal_date", "ticker"]].to_csv(path / "DYNAMIC_CLUSTER_MEMBERSHIP.csv", index=False)
            first = write_ma3_evidence(path); second = write_ma3_evidence(path)
            self.assertEqual(first, second)
            self.assertTrue((path / "RAW_FEATURE_PANEL.pkl").exists())
            self.assertTrue((path / "SEMANTIC_FINGERPRINT.json").exists())


if __name__ == "__main__":
    unittest.main()
