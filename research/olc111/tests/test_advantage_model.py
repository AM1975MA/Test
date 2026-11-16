"""Behavioral tests for mature, date-balanced action-advantage estimation."""
from pathlib import Path
import importlib.util
import json
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "advantage_model.py"


class AdvantageModelTests(unittest.TestCase):
    def load(self):
        self.assertTrue(MODULE.is_file(), "Action-advantage learner has not been implemented")
        spec = importlib.util.spec_from_file_location("advantage_model_under_test", MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def fixture(self, n=252):
        rng = np.random.default_rng(410)
        p = rng.normal(size=(n, 3))
        legacy = np.column_stack((0.3 * p[:, 0] + rng.normal(size=n), rng.normal(size=n)))
        term = np.column_stack((0.2 * legacy[:, 0] + rng.normal(size=n), rng.normal(size=n)))
        y = 0.004 + 0.012 * p[:, 0] + 0.008 * legacy[:, 0] - 0.006 * term[:, 0]
        signal = np.arange(n)
        terminal = signal + 21
        return p, legacy, term, y, signal, terminal

    def fit(self, data, cutoff=None, **kw):
        if cutoff is None:
            cutoff = int(np.max(data[-1])) + 1
        options = {"min_dates": 20, "min_blocks": 1, "n_boot": 30, "seed": 111}
        options.update(kw)
        return self.load().fit_head(*data, cutoff, **options)

    def predictions(self, result, point):
        return {name: model.predict(*point) for name, model in result["models"].items()}

    def test_not_ready_until_distinct_dates_and_nonoverlap_intervals_both_pass(self):
        # Counting ETF/state rows as independent dates or horizon blocks breaks this.
        data = self.fixture(30)
        doubled = tuple(np.repeat(a, 20, axis=0) for a in data)
        self.assertIsNone(self.fit(doubled, min_dates=31, min_blocks=1))
        self.assertIsNone(self.fit(data, min_dates=30, min_blocks=3))
        self.assertIsNotNone(self.fit(data, min_dates=30, min_blocks=2))

    def test_default_readiness_needs_504_mature_dates(self):
        # A >= maturity boundary or a row-count warmup would enable fitting early.
        data = self.fixture(504)
        module = self.load()
        self.assertIsNone(module.fit_head(*data, 524, n_boot=8))
        result = module.fit_head(*data, 525, n_boot=8)
        self.assertIsNotNone(result)
        self.assertEqual(result["meta"]["n_dates"], 504)
        self.assertEqual(result["meta"]["n_nonoverlap_blocks"], 24)

    def test_terminal_equal_cutoff_is_excluded_and_future_label_mutation_is_irrelevant(self):
        # <= instead of < would allow the deliberately extreme boundary label.
        data = list(self.fixture(210))
        cutoff = 150
        before = self.fit(data, cutoff)
        future = data[-1] >= cutoff
        data[3] = data[3].copy()
        data[3][future] = 1e80
        after = self.fit(data, cutoff)
        self.assertEqual(before["meta"]["max_terminal_idx"], cutoff - 1)
        for name in before["models"]:
            self.assertEqual(before["models"][name].to_dict(), after["models"][name].to_dict())

    def test_prefix_and_extreme_future_features_give_identical_fitted_artifacts(self):
        # Fitting scalers or residual projections before the mature mask breaks this.
        full = list(self.fixture(250))
        cutoff = 180
        prefix = tuple(a[:159].copy() for a in full)
        expected = self.fit(prefix, cutoff)
        for index in (0, 1, 2):
            full[index] = full[index].copy()
            full[index][159:] = 1e100
        actual = self.fit(full, cutoff)
        for name in expected["models"]:
            self.assertEqual(expected["models"][name].to_dict(), actual["models"][name].to_dict())

    def test_duplicate_date_weight_does_not_multiply_one_dates_influence(self):
        # Ordinary row weighting would overweight this appended high-value date.
        data = self.fixture(126)
        duplicate = tuple(np.concatenate((a, np.repeat(a[7:8], 19, axis=0)), axis=0) for a in data)
        base = self.fit(data)
        repeated = self.fit(duplicate)
        point = (data[0][45], data[1][45], data[2][45])
        for name in base["models"]:
            a = base["models"][name].predict(*point)
            b = repeated["models"][name].predict(*point)
            np.testing.assert_allclose([a["mean"], a["lower"]], [b["mean"], b["lower"]], atol=2e-13, rtol=2e-13)

    def test_common_finite_support_is_used_for_all_four_arms(self):
        # Allowing PRICE or MEAN to retain rows missing TERM changes the comparison.
        data = list(self.fixture(130))
        data[2] = data[2].copy()
        data[2][12, 0] = np.nan
        result = self.fit(data)
        explicit = self.fit(tuple(np.delete(a, 12, axis=0) for a in data))
        self.assertEqual(result["meta"]["n_dates"], 129)
        for name in result["models"]:
            self.assertEqual(result["models"][name].to_dict(), explicit["models"][name].to_dict())

    def test_collinear_legacy_and_term_blocks_add_no_predictive_information(self):
        # Scaling numerical OLS residue into a unit-variance feature breaks this.
        p, _, _, _, signal, terminal = self.fixture(189)
        legacy = np.column_stack((2 * p[:, 0] - 3 * p[:, 1] + 7, p[:, 2] - 4))
        term = np.column_stack((3 * legacy[:, 0] + p[:, 1] + 9, 2 * legacy[:, 1] - p[:, 0]))
        y = 0.02 * p[:, 0] - 0.01 * p[:, 1]
        result = self.fit((p, legacy, term, y, signal, terminal))
        point = (p[11], legacy[11], term[11])
        pred = self.predictions(result, point)
        for name in ("VIX", "TERM"):
            np.testing.assert_allclose(list(pred[name].values()), list(pred["PRICE"].values()), atol=2e-12)

    def test_ridge_penalty_is_on_mean_loss_not_unscaled_row_sum(self):
        # A library alpha=1 on an unnormalized row sum barely shrinks this slope.
        n = 126
        x = np.tile([-1.0, 1.0], n // 2)
        data = (x[:, None], np.zeros((n, 2)), np.zeros((n, 2)), 0.01 + 0.02 * x, np.arange(n), np.arange(n) + 21)
        model = self.fit(data, penalty=1.0)["models"]["PRICE"]
        self.assertAlmostEqual(model.predict([1.0], [0.0, 0.0], [0.0, 0.0])["mean"], 0.02, places=13)
        self.assertAlmostEqual(model.predict([-1.0], [0.0, 0.0], [0.0, 0.0])["mean"], 0.0, places=13)

    def test_native_net_advantage_is_not_charged_another_fee_or_clipped(self):
        # An extra fee offset or return clipping would move these already-net labels.
        data = list(self.fixture(126))
        data[3] = np.full(126, -0.35)
        result = self.fit(data)
        point = (data[0][0], data[1][0], data[2][0])
        for prediction in self.predictions(result, point).values():
            self.assertAlmostEqual(prediction["mean"], -0.35, places=13)
            self.assertAlmostEqual(prediction["lower"], -0.35, places=13)

    def test_bootstrap_uses_whole_fixed_63_session_blocks(self):
        # Row resampling would produce many intermediate means, not just0,.5,1.
        n = 126
        data = (np.zeros((n, 1)), np.zeros((n, 2)), np.zeros((n, 2)), np.repeat([0.0, 1.0], 63), np.arange(n), np.arange(n) + 21)
        result = self.fit(data, n_boot=100)
        for model in result["models"].values():
            values = np.asarray(model.to_dict()["bootstrap_coefficients"])[:, 0]
            self.assertTrue(set(np.round(values, 12)).issubset({0.0, 0.5, 1.0}))
        self.assertEqual(result["models"]["MEAN"].predict([0.0], [0.0, 0.0], [0.0, 0.0])["lower"], 0.0)

    def test_bootstrap_is_deterministic_and_paired_across_information_arms(self):
        # Independent RNG draws per arm would give different means on constant inputs.
        data = list(self.fixture(252))
        for i in (0, 1, 2):
            data[i] = np.zeros_like(data[i])
        a, b = self.fit(data, n_boot=40), self.fit(data, n_boot=40)
        serialized = [model.to_dict() for model in a["models"].values()]
        means = [np.asarray(item["bootstrap_coefficients"])[:, 0] for item in serialized]
        for current in means[1:]:
            np.testing.assert_allclose(current, means[0], atol=2e-15)
        for name in a["models"]:
            self.assertEqual(a["models"][name].to_dict(), b["models"][name].to_dict())

    def test_serialized_model_is_complete_finite_json(self):
        # Omitting transforms/bootstrap coefficients would prevent auditable replay.
        result = self.fit(self.fixture(126))
        for model in result["models"].values():
            exported = model.to_dict()
            json.dumps(exported, allow_nan=False)
            self.assertIn("transforms", exported)
            self.assertIn("coefficients", exported)
            self.assertIn("bootstrap_coefficients", exported)

    def test_price_fallback_does_not_require_missing_external_features(self):
        # Validating unused options at PRICE prediction would break the fallback.
        data = self.fixture(126)
        result = self.fit(data)
        normal = result["models"]["PRICE"].predict(data[0][0], data[1][0], data[2][0])
        missing = result["models"]["PRICE"].predict(data[0][0], [np.nan, np.nan], [np.nan, np.nan])
        self.assertEqual(normal, missing)
        with self.assertRaises(ValueError):
            result["models"]["TERM"].predict(data[0][0], data[1][0], [np.nan, np.nan])

    def test_bad_shapes_and_nonpositive_bootstrap_count_are_rejected(self):
        data = list(self.fixture(30))
        with self.assertRaises(ValueError):
            self.fit(data, n_boot=0)
        data[1] = data[1][:-1]
        with self.assertRaises(ValueError):
            self.fit(data)


if __name__ == "__main__":
    unittest.main()
