import unittest
import pandas as pd

from feature_ablation_v1.run_feature_ablation import (
    bh_qvalues,
    orthogonal_greedy,
    semantic_family,
)


class FeatureAblationContractTests(unittest.TestCase):
    def test_semantic_family(self):
        self.assertEqual(semantic_family("mom21"), "mom21")
        self.assertEqual(semantic_family("mom21_pct"), "mom21")
        self.assertEqual(semantic_family("mom21_dev"), "mom21")

    def test_bh_qvalues_are_bounded_and_monotone_by_p(self):
        p = {"a": 0.001, "b": 0.01, "c": 0.2, "d": 0.9}
        q = bh_qvalues(p)
        self.assertTrue(all(0.0 <= x <= 1.0 for x in q.values()))
        self.assertLessEqual(q["a"], q["b"])
        self.assertLessEqual(q["b"], q["c"])
        self.assertLessEqual(q["c"], q["d"])

    def test_greedy_never_duplicates_semantic_family(self):
        features = ["a", "a_pct", "b", "b_dev", "c"]
        score = {"a": 1.0, "a_pct": 0.9, "b": 0.8, "b_dev": 0.7, "c": 0.6}
        corr = pd.DataFrame(
            [
                [1.0, .99, .1, .1, .2],
                [.99, 1.0, .1, .1, .2],
                [.1, .1, 1.0, .99, .3],
                [.1, .1, .99, 1.0, .3],
                [.2, .2, .3, .3, 1.0],
            ],
            index=features,
            columns=features,
        )
        chosen, _ = orthogonal_greedy(features, score, corr)
        self.assertEqual(len(chosen), 3)
        self.assertEqual(len({semantic_family(f) for f in chosen}), 3)


if __name__ == "__main__":
    unittest.main()
