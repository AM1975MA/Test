"""Numerical checks of maturity, training-only state and additive determinism."""
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from compact21_predictive_v2 import additive as a


def fixture():
    rng = np.random.default_rng(718)
    dates = pd.date_range("2015-01-31", periods=20, freq="ME")
    n = len(dates) * 12
    frame = pd.DataFrame(rng.normal(size=(n, 125)), columns=a.k.F2D_FEATURES)
    frame["signal_date"] = np.repeat(dates, 12)
    frame["ticker"] = np.tile([f"T{i:02}" for i in range(12)], len(dates))
    frame["exit_date_21"] = frame.signal_date + pd.Timedelta(days=30)
    frame["target_rank_21"] = frame.groupby("signal_date")[a.k.F2D_FEATURES[0]].rank(pct=True)
    frame.loc[3, a.k.F2D_FEATURES[2]] = np.nan
    test = frame.iloc[:12].copy()
    test["signal_date"] = pd.Timestamp("2017-01-31")
    return frame, test


class AdditiveTests(unittest.TestCase):
    def setUp(self):
        self.tr, self.te = fixture()

    def test_repeat_exact_and_frozen_parameters(self):
        p, meta, y, _ = a.fit(self.tr, [self.te], 2017)
        q, again, _, _ = a.fit(self.tr, [self.te], 2017)
        self.assertEqual(p[0].tobytes(), q[0].tobytes())
        self.assertEqual(meta, again)
        np.testing.assert_array_equal(y, self.tr.target_rank_21)
        self.assertEqual(meta["input_features"], 125)
        self.assertEqual(meta["design_features"], 625)
        self.assertEqual(len(meta["imputer_statistics"]), 125)
        self.assertEqual(len(meta["spline_knots"]), 125)
        self.assertTrue(meta["learned_state_hashes"])
        self.assertEqual(meta["model_params"]["alpha"], 30.0)
        self.assertEqual(meta["model_params"]["n_knots"], 4)
        self.assertEqual(meta["model_params"]["degree"], 3)
        self.assertEqual(meta["model_params"]["extrapolation"], "linear")
        self.assertGreater(np.ptp(p[0]), 0)

    def test_future_rows_excluded_by_caller_and_rejected_if_passed(self):
        future = self.tr.iloc[:12].copy()
        future["signal_date"] = pd.Timestamp("2018-01-31")
        future["exit_date_21"] = pd.Timestamp("2018-03-01")
        future[a.k.F2D_FEATURES] = 1e12
        future["target_rank_21"] = np.linspace(0, 1, 12)
        combined = pd.concat([self.tr, future], ignore_index=True)
        cutoff = pd.Timestamp("2017-01-01")
        mature = combined[(combined.signal_date < cutoff) & (combined.exit_date_21 < cutoff)]
        p, meta, _, _ = a.fit(self.tr, [self.te], 2017)
        q, again, _, _ = a.fit(mature, [self.te], 2017)
        self.assertEqual(p[0].tobytes(), q[0].tobytes())
        self.assertEqual(meta, again)
        with self.assertRaises(ValueError):
            a.fit(combined, [self.te], 2017)

    def test_inference_data_and_labels_never_learn_transform(self):
        p, meta, _, _ = a.fit(self.tr, [self.te], 2017)
        mutated = self.te.copy()
        mutated[a.k.F2D_FEATURES] = 1e5
        mutated["target_rank_21"] = np.nan
        mutated["exit_date_21"] = pd.NaT
        q, again, _, _ = a.fit(self.tr, [self.te, mutated], 2017)
        self.assertEqual(p[0].tobytes(), q[0].tobytes())
        self.assertEqual(meta["learned_state_hashes"], again["learned_state_hashes"])
        self.assertEqual(meta["fit_matrix_sha256"], again["fit_matrix_sha256"])
        self.assertTrue(np.isfinite(q[1]).all())

    def test_all_missing_training_feature_fails_but_missing_test_preserves_columns(self):
        tr = self.tr.copy()
        tr[a.k.F2D_FEATURES[0]] = np.nan
        with self.assertRaisesRegex(ValueError, "Entirely missing"):
            a.fit(tr, [self.te], 2017)
        te = self.te.copy()
        te[a.k.F2D_FEATURES] = np.nan
        p, meta, _, _ = a.fit(self.tr, [te], 2017)
        self.assertTrue(np.isfinite(p[0]).all())
        self.assertEqual(meta["input_features"], 125)
        self.assertEqual(meta["design_features"], 625)

    def test_invalid_keys_maturity_target_and_features_fail_closed(self):
        cases = []
        x = self.tr.copy(); x.loc[0, "exit_date_21"] = pd.Timestamp("2017-01-01"); cases.append(x)
        x = self.tr.copy(); x.loc[0, "signal_date"] = pd.NaT; cases.append(x)
        x = self.tr.iloc[::-1]; cases.append(x)
        x = pd.concat([self.tr, self.tr.iloc[:1]]); cases.append(x)
        x = self.tr.copy(); x.loc[0, "target_rank_21"] = np.inf; cases.append(x)
        x = self.tr.copy(); x.loc[0, "target_rank_21"] = 1.01; cases.append(x)
        x = self.tr.drop(columns=[a.k.F2D_FEATURES[0]]); cases.append(x)
        x = self.tr.iloc[:0]; cases.append(x)
        for i, tr in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(ValueError):
                a.fit(tr, [self.te], 2017)
        for tests in ([], [self.te.iloc[:0]], [pd.concat([self.te, self.te.iloc[:1]])]):
            with self.assertRaises(ValueError):
                a.fit(self.tr, tests, 2017)

    def test_infinite_feature_values_follow_canonical_missing_handling(self):
        tr = self.tr.copy()
        te = self.te.copy()
        tr.loc[0, a.k.F2D_FEATURES[0]] = np.inf
        te.loc[0, a.k.F2D_FEATURES[1]] = -np.inf
        p, meta, _, _ = a.fit(tr, [te], 2017)
        tr.loc[0, a.k.F2D_FEATURES[0]] = np.nan
        te.loc[0, a.k.F2D_FEATURES[1]] = np.nan
        q, again, _, _ = a.fit(tr, [te], 2017)
        self.assertEqual(p[0].tobytes(), q[0].tobytes())
        self.assertEqual(meta, again)

    def test_serialized_model_predicts_same_and_source_audited(self):
        import joblib
        with tempfile.TemporaryDirectory() as td:
            p, meta, _, _ = a.fit(self.tr, [self.te], 2017, td, "control")
            path = Path(td) / "control_additive.joblib"
            self.assertTrue(path.is_file())
            m = joblib.load(path)
            restored = m.predict(self.te[a.k.F2D_FEATURES].to_numpy(dtype=float))
            self.assertEqual(p[0].tobytes(), restored.tobytes())
            self.assertEqual(len(meta["source_sha256"]), 64)

    def test_constant_features_retained_and_recorded_without_new_recipe(self):
        tr = self.tr.copy()
        name = a.k.F2D_FEATURES[0]
        tr[name] = 2.0
        p, meta, _, _ = a.fit(tr, [self.te], 2017)
        self.assertEqual(meta["constant_features"], [name])
        self.assertEqual(meta["input_features"], 125)
        self.assertEqual(meta["design_features"], 625)
        self.assertTrue(np.isfinite(p[0]).all())


if __name__ == "__main__":
    unittest.main()
