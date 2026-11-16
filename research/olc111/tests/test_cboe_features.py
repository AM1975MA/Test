"""Behavioral tests for the causal Cboe daily-close boundary."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src/cboe_features.py"
SYMBOLS = ("VIX9D", "VIX", "VIX3M")


class CboeFeaturesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raw = Path(self.temp.name)
        dates = pd.bdate_range("2023-12-01", "2024-01-31")
        dates = dates.difference(pd.to_datetime(["2023-12-25", "2024-01-01", "2024-01-15"]))
        self.frames = {}
        for symbol, value in zip(SYMBOLS, (10.0, 20.0, 40.0)):
            self.frames[symbol] = pd.DataFrame({"DATE": dates.strftime("%m/%d/%Y"), "CLOSE": value})
        self.write_sources()

    def write_sources(self):
        for symbol, frame in self.frames.items():
            frame.to_csv(self.raw / f"{symbol}_History.csv", index=False)

    def load(self, dates):
        self.assertTrue(MODULE.is_file(), "Causal Cboe feature loader has not been implemented")
        spec = importlib.util.spec_from_file_location("cboe_features_under_test", MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.load_cboe_features(self.raw, dates)

    def set_close(self, symbol, date, value):
        self.frames[symbol].loc[self.frames[symbol]["DATE"] == date, "CLOSE"] = value

    def assert_unavailable(self, result, row=0):
        self.assertFalse(result["available"][row])
        self.assertTrue(np.isnan(result["term"][row]).all())
        self.assertTrue(np.isnan(result["legacy"][row]).all())

    def test_same_day_us_close_is_excluded_even_for_intraday_decisions(self):
        # A <= rather than < boundary would use these same-day extreme closes.
        for symbol in SYMBOLS:
            self.set_close(symbol, "01/30/2024", 9000.0)
        self.write_sources()
        out = self.load(["2024-01-30 17:30:00"])
        self.assertTrue(out["available"][0])
        np.testing.assert_array_equal(out["dates"], np.array(["2024-01-30"], dtype="datetime64[D]"))
        np.testing.assert_array_equal(out["source_dates"][0], np.array(["2024-01-29"] * 3, dtype="datetime64[D]"))
        np.testing.assert_allclose(out["legacy"][0], [np.log(20.0), 0.0])

    def test_weekend_and_us_holiday_use_previous_source_session(self):
        # Calendar shifting by one day would fail the holiday and weekend rows.
        out = self.load(["2024-01-13", "2024-01-15", "2024-01-16"])
        np.testing.assert_array_equal(out["available"], [True, True, True])
        np.testing.assert_array_equal(out["source_dates"], np.full((3, 3), np.datetime64("2024-01-12", "D")))
        np.testing.assert_array_equal(out["source_age_days"], [[1, 1, 1], [3, 3, 3], [4, 4, 4]])

    def test_age_seven_is_allowed_and_age_eight_is_unavailable(self):
        # An unbounded forward fill, or a six-day cutoff, breaks this boundary.
        for symbol in SYMBOLS:
            frame = self.frames[symbol]
            self.frames[symbol] = frame[pd.to_datetime(frame["DATE"], format="%m/%d/%Y") <= "2024-01-12"]
        self.write_sources()
        out = self.load(["2024-01-19", "2024-01-20"])
        self.assertTrue(out["available"][0])
        self.assert_unavailable(out, 1)
        np.testing.assert_array_equal(out["source_age_days"][1], [8, 8, 8])

    def test_no_source_before_decision_never_backfills_from_future(self):
        out = self.load(["2023-12-01"])
        self.assert_unavailable(out)
        self.assertTrue(np.isnat(out["source_dates"]).all())
        self.assertTrue(np.isnan(out["source_age_days"]).all())

    def test_common_mask_requires_twenty_one_source_session_vix_history(self):
        # The legacy change needs 22 observed closes, not 21 observations.
        dates = pd.to_datetime(self.frames["VIX"]["DATE"], format="%m/%d/%Y")
        out = self.load([dates.iloc[21], dates.iloc[22]])
        self.assert_unavailable(out, 0)
        self.assertTrue(out["available"][1])
        np.testing.assert_allclose(out["legacy"][1], [np.log(20.0), 0.0])

    def test_ratios_and_legacy_change_use_source_session_lag(self):
        # Jan 31 is 21 listed source sessions after Dec 29, across US holidays.
        self.set_close("VIX", "12/29/2023", 5.0)
        self.write_sources()
        out = self.load(["2024-02-01"])
        self.assertTrue(out["available"][0])
        np.testing.assert_allclose(out["term"][0], [-0.6931471805599453, -0.6931471805599453])
        np.testing.assert_allclose(out["legacy"][0], [2.995732273553991, 1.3862943611198906])

    def test_future_close_mutation_changes_hashes_but_not_earlier_features(self):
        # Global scaling or use of future rows would move the earlier features.
        decisions = ["2024-01-16", "2024-01-17", "2024-01-18"]
        before = self.load(decisions)
        for frame in self.frames.values():
            future = pd.to_datetime(frame["DATE"], format="%m/%d/%Y") >= "2024-01-18"
            frame.loc[future, "CLOSE"] = 1e100
        self.write_sources()
        after = self.load(decisions)
        for key in ("dates", "available", "source_dates", "source_age_days", "term", "legacy"):
            np.testing.assert_array_equal(before[key], after[key], err_msg=key)
        self.assertNotEqual(before["metadata"]["sources"], after["metadata"]["sources"])

    def test_mismatched_latest_source_dates_invalidate_without_backdating(self):
        frame = self.frames["VIX9D"]
        self.frames["VIX9D"] = frame[frame["DATE"] != "01/31/2024"]
        self.write_sources()
        out = self.load(["2024-02-01"])
        self.assert_unavailable(out)
        np.testing.assert_array_equal(out["source_dates"][0], np.array(["2024-01-30", "2024-01-31", "2024-01-31"], dtype="datetime64[D]"))

    def test_invalid_latest_close_never_falls_back_to_an_earlier_value(self):
        # Dropping bad closes silently would use the valid Jan 30 quote instead.
        for symbol in SYMBOLS:
            original = self.frames[symbol].copy()
            for value in (0.0, -1.0, np.nan, np.inf):
                with self.subTest(symbol=symbol, value=value):
                    self.set_close(symbol, "01/31/2024", value)
                    self.write_sources()
                    out = self.load(["2024-02-01"])
                    self.assert_unavailable(out)
                    np.testing.assert_array_equal(out["source_dates"][0], np.array(["2024-01-31"] * 3, dtype="datetime64[D]"))
            self.frames[symbol] = original

    def test_invalid_twenty_one_session_lag_invalidates_common_mask(self):
        self.set_close("VIX", "12/29/2023", 0.0)
        self.write_sources()
        self.assert_unavailable(self.load(["2024-02-01"]))

    def test_duplicate_source_dates_are_rejected(self):
        self.frames["VIX"] = pd.concat([self.frames["VIX"], self.frames["VIX"].iloc[[-1]]], ignore_index=True)
        self.write_sources()
        with self.assertRaises(ValueError):
            self.load(["2024-02-01"])

    def test_unsorted_source_dates_are_rejected(self):
        self.frames["VIX"] = self.frames["VIX"].iloc[::-1]
        self.write_sources()
        with self.assertRaises(ValueError):
            self.load(["2024-02-01"])

    def test_empty_decisions_keep_array_shapes(self):
        out = self.load([])
        self.assertEqual(out["dates"].shape, (0,))
        self.assertEqual(out["available"].shape, (0,))
        self.assertEqual(out["source_dates"].shape, (0, 3))
        self.assertEqual(out["source_age_days"].shape, (0, 3))
        self.assertEqual(out["term"].shape, (0, 2))
        self.assertEqual(out["legacy"].shape, (0, 2))


if __name__ == "__main__":
    unittest.main()
