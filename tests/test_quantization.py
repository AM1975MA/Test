"""Meaningful contract tests for causal feature-only quantization."""
import ast
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from compact21_stability_v1.quantization import ScaleAwareQuantizer


class QuantizationTests(unittest.TestCase):
    def test_all_125_canonical_features_are_audited_and_transformed(self):
        source = (Path(__file__).parents[1] /
                  "vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py")
        tree = ast.parse(source.read_text())
        names = next(ast.literal_eval(node.value) for node in tree.body
                     if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == "F2D_FEATURES"
                             for target in node.targets))
        self.assertEqual(len(names), 125)
        frame = pd.DataFrame(np.random.default_rng(21).normal(size=(8, 125)), columns=names)
        q = ScaleAwareQuantizer(names).fit(frame)
        output = q.transform(frame)
        self.assertEqual(output.shape, (8, 125))
        self.assertEqual([entry["name"] for entry in q.to_dict()["features"]], names)
        pd.testing.assert_frame_equal(output, q.transform(output))

    def test_feature_specific_resolution_and_kernel_domains(self):
        train = pd.DataFrame({"mom21": [0.0, 0.1, 0.2, 0.3, 1000.0],
                              "vol21": [0, 10, 20, 30, 100000.0],
                              "mom21_pct": [0.1] * 5, "mom21_dev": [0.0] * 5,
                              "sign_entropy63": [0.0] * 5, "rsi14": [0.0] * 5})
        quantizer = ScaleAwareQuantizer(list(train)).fit(train)
        self.assertEqual(quantizer.steps_[1] / quantizer.steps_[0], 128.0)
        self.assertEqual(quantizer.steps_[2], 2**-12)
        self.assertEqual(quantizer.steps_[3], 2**-8)
        self.assertEqual(quantizer.steps_[4], 2**-12)
        self.assertEqual(quantizer.steps_[5], 2**-5)
        # A tail outlier does not set the raw feature's IQR scale.
        self.assertAlmostEqual(quantizer.to_dict()["features"][0]["scale"], 0.2)

    def test_only_training_features_determine_audit(self):
        train = pd.DataFrame({"mom21": [0.0, 0.1, 0.2, 0.3],
                              "target_rank_21": [0.0, 0.1, 0.2, 0.3]})
        quantizer = ScaleAwareQuantizer(["mom21"]).fit(train)
        reference = quantizer.to_dict()
        other_targets = train.assign(target_rank_21=[100, -10, 1e10, np.nan])
        self.assertEqual(reference, ScaleAwareQuantizer(["mom21"]).fit(other_targets).to_dict())
        quantizer.transform(pd.DataFrame({"mom21": [1e10, -1e10]}))
        self.assertEqual(reference, quantizer.to_dict())

    def test_dataframe_order_metadata_and_input_not_mutated(self):
        frame = pd.DataFrame({"ticker": ["A", "B"], "vol21": [0.12, 0.23],
                              "mom21": [0.34, 0.45]}, index=[10, 20])
        original = frame.copy(deep=True)
        q = ScaleAwareQuantizer(["mom21", "vol21"]).fit(frame)
        out = q.transform(frame[["vol21", "ticker", "mom21"]])
        self.assertEqual(list(out), ["mom21", "vol21"])
        pd.testing.assert_index_equal(out.index, frame.index)
        np.testing.assert_array_equal(out, q.transform(frame[["mom21", "vol21"]].to_numpy()))
        pd.testing.assert_frame_equal(frame, original)

    def test_nan_inf_and_degenerate_training_columns(self):
        x = np.array([[np.nan, 0.0, 12.0], [np.inf, 0.0, 12.0], [-np.inf, 0.0, 12.0]])
        q = ScaleAwareQuantizer(["empty", "zero", "constant"]).fit(x)
        out = q.transform(x)
        self.assertTrue(np.isnan(out[:, 0]).all())
        np.testing.assert_array_equal(out[:, 1:], x[:, 1:])
        self.assertTrue(np.isfinite(q.steps_).all())
        self.assertTrue((q.steps_ > 0).all())
        self.assertTrue(np.isinf(x[1:, 0]).all())
        self.assertEqual(q.to_dict()["features"][0]["nonfinite_training_count"], 3)

    def test_idempotence_json_roundtrip_and_no_clipping(self):
        q = ScaleAwareQuantizer(["mom21_pct", "vol21"]).fit(np.array([[0, 0], [1, 100]]))
        restored = ScaleAwareQuantizer.from_dict(json.loads(json.dumps(q.to_dict(), allow_nan=False)))
        x = np.array([[0.1234567, 0.1234567], [2, 10000], [-1, -1e300], [np.nan, np.inf]])
        out = q.transform(x)
        np.testing.assert_array_equal(out, q.transform(out))
        np.testing.assert_array_equal(out, restored.transform(x))
        self.assertEqual(out[1, 0], 2.0)
        self.assertEqual(out[2, 1], -1e300)

    def test_bins_can_have_unavoidable_boundary_disagreement(self):
        q = ScaleAwareQuantizer(["mom21_pct"]).fit(np.array([[0], [1]]))
        step = q.steps_[0]
        x = np.array([[0.25 * step], [0.25 * step + 1e-10],
                      [0.5 * step - 1e-10], [0.5 * step + 1e-10]])
        out = q.transform(x).ravel()
        self.assertEqual(out[0], out[1])
        self.assertNotEqual(out[2], out[3])
        np.testing.assert_array_equal(q.transform(np.array([[0.5 * step], [1.5 * step]])),
                                      [[0.0], [2.0 * step]])

    def test_zero_anchor_and_row_permutation_are_deterministic(self):
        x = np.array([[0.0], [0.01], [0.02], [0.03], [0.04]])
        q = ScaleAwareQuantizer(["mom21"]).fit(x)
        q_reverse = ScaleAwareQuantizer(["mom21"]).fit(x[::-1])
        self.assertEqual(q.to_dict(), q_reverse.to_dict())
        np.testing.assert_array_equal(q.transform(x), q.transform(x[::-1])[::-1])
        self.assertEqual(q.to_dict()["anchor"], 0.0)

    def test_preregistered_floor_and_invalid_inputs(self):
        q = ScaleAwareQuantizer(["mom21"], minimum_steps={"mom21": 0.01}).fit(np.zeros((2, 1)))
        self.assertEqual(q.steps_[0], 2**-6)
        audit = q.to_dict()
        audit["features"][0]["step"] = 0
        with self.assertRaises(ValueError):
            ScaleAwareQuantizer.from_dict(audit)
        with self.assertRaises(ValueError):
            ScaleAwareQuantizer(["target_rank_21"])
        with self.assertRaises(ValueError):
            ScaleAwareQuantizer(["a", "a"])
        with self.assertRaises(RuntimeError):
            ScaleAwareQuantizer(["a"]).transform([[1]])
        with self.assertRaises(ValueError):
            q.transform(pd.DataFrame({"other": [1]}))
        with self.assertRaises(ValueError):
            q.transform([[1, 2]])
        with self.assertRaises(ValueError):
            q.fit(np.empty((0, 1)))


if __name__ == "__main__":
    unittest.main()
