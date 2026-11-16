"""Synthetic-only contracts for complete-plan model fitting."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np
from sklearn.tree import DecisionTreeRegressor

MODULE = Path(__file__).resolve().parents[1] / "src" / "cycle_model.py"
if MODULE.exists():
    spec = importlib.util.spec_from_file_location("cycle_model", MODULE)
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
else:
    model = None


class CycleModelTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(model, "portable model implementation is missing")
        self.dates = np.arange(np.datetime64("2018-01-01"), np.datetime64("2027-01-01"))

    def fit(self, X, y, signals, *, cutoff=None, **kwargs):
        signals = np.asarray(signals)
        return model.fit_head(np.asarray(X, float), np.asarray(y, float), signals,
                              signals + 42, int(max(signals) + 43) if cutoff is None else cutoff,
                              self.dates, min_dates=kwargs.pop("min_dates", 1),
                              min_months=kwargs.pop("min_months", 1),
                              min_blocks=kwargs.pop("min_blocks", 1), **kwargs)

    def test_strict_maturity_excludes_equal_cutoff_and_future_mutation(self):
        signals = np.array([0, 1, 2, 20, 80])
        X = np.array([[0], [1], [2], [20], [80.]])
        y = np.array([1, 3, 500, 800, 900.])
        first = self.fit(X, y, signals, cutoff=44)
        self.assertEqual(first["meta"]["mature_rows"], 2)
        self.assertEqual(first["models"]["MEAN"].predict([0])["mean"], 2.)
        X[2:] = np.nan
        y[2:] = np.nan
        second = self.fit(X, y, signals, cutoff=44)
        self.assertEqual(first["hashes"], second["hashes"])
        self.assertEqual(first["meta"]["draw_hash"], second["meta"]["draw_hash"])

    def test_repeated_legs_cannot_supply_independent_dates(self):
        self.assertIsNone(self.fit(np.zeros((100, 1)), np.ones(100), np.zeros(100, int),
                                  min_dates=2))

    def test_each_date_has_total_weight_one(self):
        result = self.fit([[0], [0], [10]], [0, 2, 10], [0, 0, 63])
        self.assertEqual(result["models"]["MEAN"].predict([0])["mean"], 5.5)
        np.testing.assert_allclose(result["meta"]["training_weights"], [.5, .5, 1.])
        np.testing.assert_allclose(result["meta"]["scaler"]["mean"], [5.])
        np.testing.assert_allclose(result["meta"]["scaler"]["scale"], [5.])

    def test_calendar_months_are_distinct_not_row_counts(self):
        signals = np.arange(24)
        self.assertIsNone(self.fit(np.zeros((24, 1)), np.ones(24), signals,
                                  min_dates=24, min_months=2))
        result = self.fit([[0], [1]], [0, 1], [0, 31], min_months=2)
        self.assertEqual(result["meta"]["mature_months"], 2)

    def test_readiness_counts_42_session_return_intervals(self):
        signals = np.arange(0, 43, 21)
        self.assertIsNone(self.fit(np.zeros((3, 1)), np.ones(3), signals, min_blocks=3))
        result = self.fit(np.zeros((3, 1)), np.ones(3), signals, min_blocks=2)
        self.assertEqual(result["meta"]["nonoverlap_42"], 2)
        self.assertEqual(result["meta"]["nonoverlap_signal_idx"], [0, 42])

    def test_default_readiness_requires_504_dates_and_24_months(self):
        signals = np.arange(504)
        result = model.fit_head(np.zeros((504, 1)), np.ones(504), signals, signals+42,
                                1000, self.dates)
        self.assertIsNone(result)  # 504 calendar days contain fewer than 24 months.
        signals = np.arange(0, 1008, 2)
        result = model.fit_head(np.zeros((504, 1)), np.ones(504), signals, signals+42,
                                1100, self.dates)
        self.assertIsNotNone(result)
        self.assertEqual(result["meta"]["mature_dates"], 504)
        self.assertGreaterEqual(result["meta"]["nonoverlap_42"], 12)

    def test_ridge_mean_loss_penalty_and_fixed_scaler_bootstraps(self):
        result = self.fit([[0], [2]], [1, 5], [0, 63])
        value = result["models"]["RIDGE"]
        # z=(-1,+1), y=(1,5): intercept 3, coefficient 2/(1+1)=1.
        self.assertAlmostEqual(value.predict([0])["mean"], 2.)
        self.assertAlmostEqual(value.predict([2])["mean"], 4.)
        payload = value.to_dict()
        self.assertEqual(payload["scaler"], {"mean": [1.], "scale": [1.]})
        for draw, fitted in zip(result["meta"]["bootstrap_draws"], payload["bootstraps"]):
            if draw == [0, 0]:
                self.assertAlmostEqual(fitted["intercept"], 1.)
                self.assertAlmostEqual(fitted["coef"][0], 0.)
        restored = model.ValueModel.from_dict(json.loads(json.dumps(payload, allow_nan=False)))
        self.assertEqual(restored.predict([1.25]), value.predict([1.25]))

    def test_portable_tree_matches_sklearn_including_float32_boundaries(self):
        rng = np.random.default_rng(7)
        X = rng.normal(size=(180, 3))
        y = np.where(X[:, 0] > .2, 3., -1.) + np.where(X[:, 1] > 0, .2, -.3)
        result = self.fit(X, y, np.arange(180))
        tree = DecisionTreeRegressor(criterion="squared_error", max_depth=2,
                                    min_weight_fraction_leaf=.2, min_samples_leaf=1,
                                    random_state=114).fit(X, y, sample_weight=np.ones(180))
        probes = [*rng.normal(size=(100, 3))]
        for feature, threshold in zip(tree.tree_.feature, tree.tree_.threshold):
            if feature >= 0:
                point = np.zeros(3)
                point[feature] = np.nextafter(threshold, np.inf)
                probes.append(point)
        value = result["models"]["TREE"]
        restored = model.ValueModel.from_dict(json.loads(json.dumps(value.to_dict(), allow_nan=False)))
        expected = tree.predict(np.asarray(probes))
        np.testing.assert_array_equal([value.predict(x)["mean"] for x in probes], expected)
        self.assertEqual([restored.predict(x) for x in probes], [value.predict(x) for x in probes])
        self.assertLessEqual(sum(np.array(value.to_dict()["fitted"]["children_left"]) == -1), 4)

    def test_paired_bootstraps_share_draws_and_keep_all_legs(self):
        signals = np.array([0, 0, 62, 63, 126, 126, 189])
        a = self.fit(np.arange(7)[:, None], np.arange(7), signals)
        b = self.fit(np.arange(7)[:, None] * 7, -np.arange(7), signals)
        self.assertEqual(a["meta"]["bootstrap_draws"], b["meta"]["bootstrap_draws"])
        self.assertEqual(a["meta"]["draw_hash"], b["meta"]["draw_hash"])
        self.assertEqual(len(a["meta"]["bootstrap_draws"]), 32)
        for draw, fit in zip(a["meta"]["bootstrap_draws"], a["models"]["MEAN"].to_dict()["bootstraps"]):
            # Date means are .5,2,3,4.5,6; first two dates occupy the same fixed block.
            block_sum = {0: 2.5, 1: 3., 2: 4.5, 3: 6.}
            block_dates = {0: 2, 1: 1, 2: 1, 3: 1}
            expected = sum(block_sum[b] for b in draw) / sum(block_dates[b] for b in draw)
            self.assertAlmostEqual(fit["value"], expected)
        again = self.fit(np.arange(7)[:, None], np.arange(7), signals)
        self.assertEqual(a["hashes"], again["hashes"])
        for name, value in a["models"].items():
            raw = json.dumps(value.to_dict(), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode()
            self.assertEqual(a["hashes"][name], hashlib.sha256(raw).hexdigest())
            boot = value.to_dict()["bootstraps"]
            self.assertEqual(len(boot), 32)
        values = [m["value"] for m in a["models"]["MEAN"].to_dict()["bootstraps"]]
        self.assertEqual(a["models"]["MEAN"].predict([0])["lower"], float(np.quantile(values, .1)))

    def test_bootstrap_tree_portability_and_unequal_head_leg_counts(self):
        rng = np.random.default_rng(19)
        signals = np.repeat(np.arange(0, 252, 3), 2)
        X = rng.normal(size=(len(signals), 2))
        y = np.where(X[:, 0] > 0, 2., -1.) + X[:, 1] * .2
        fitted = self.fit(X, y, signals)
        # Different numbers of legs and dates within identical fixed blocks
        # cannot alter the paired block draws.
        other = self.fit([[1], [2], [3], [4]], [4, 3, 2, 1], [0, 63, 126, 189])
        self.assertEqual(fitted["meta"]["draw_hash"], other["meta"]["draw_hash"])
        value = fitted["models"]["TREE"]
        probes = rng.normal(size=(20, 2))
        boot_predictions = []
        for draw, payload in zip(fitted["meta"]["bootstrap_draws"], value.to_dict()["bootstraps"]):
            weights = np.array([.5 * draw.count(int(k // 63)) for k in signals])
            tree = DecisionTreeRegressor(criterion="squared_error", max_depth=2,
                                        min_weight_fraction_leaf=.2, min_samples_leaf=1,
                                        random_state=114).fit(X, y, sample_weight=weights)
            single_payload = value.to_dict()
            single_payload["fitted"] = payload
            portable = model.ValueModel.from_dict(single_payload)
            np.testing.assert_array_equal([portable.predict(x)["mean"] for x in probes], tree.predict(probes))
            boot_predictions.append(tree.predict(probes))
        np.testing.assert_array_equal([value.predict(x)["lower"] for x in probes],
                                      np.quantile(boot_predictions, .1, axis=0))

    def test_tree_float32_input_conversion_controls_boundary_leaf(self):
        fitted = self.fit([[0], [0], [1], [1]], [0, 0, 1, 1], [0, 1, 63, 64])
        # This double is above .5, but sklearn casts it to exactly float32(.5).
        point = np.nextafter(.5, 1.)
        self.assertEqual(fitted["models"]["TREE"].predict([point])["mean"], 0.)
        self.assertEqual(fitted["models"]["TREE"].predict([float(np.nextafter(np.float32(.5), np.float32(1)))])["mean"], 1.)

    def test_saved_model_contains_complete_tree_parameters_and_copy_isolation(self):
        result = self.fit([[0], [1]], [0, 1], [0, 63])
        value = result["models"]["TREE"]
        saved = value.to_dict()
        defaults = DecisionTreeRegressor(criterion="squared_error", max_depth=2,
                                        min_weight_fraction_leaf=.2, min_samples_leaf=1,
                                        random_state=114).get_params()
        self.assertEqual(saved["parameters"], defaults)
        saved["fitted"]["value"][0] = 999.
        scaler = value.training_scaler
        scaler["mean"][0] = 999.
        self.assertEqual(value.training_scaler["mean"], [.5])
        restored = model.ValueModel.from_dict(value.to_dict())
        self.assertEqual(model.model_hash(restored), result["hashes"]["TREE"])
        with self.assertRaises(ValueError):
            restored.predict([np.nan])
        with self.assertRaises(ValueError):
            restored.predict([0, 1])

    def test_wrong_horizon_and_nonfinite_mature_values_rejected(self):
        with self.assertRaises(ValueError):
            model.fit_head([[0]], [1], [0], [21], 100, self.dates,
                           min_dates=1, min_months=1, min_blocks=1)
        with self.assertRaises(ValueError):
            self.fit([[np.nan]], [1], [0])
        with self.assertRaises(ValueError):
            self.fit([[0]], [np.inf], [0])


if __name__ == "__main__":
    unittest.main()
