import unittest

import numpy as np
import pandas as pd

from compact21_factorial_v1 import metrics as fm


def panel():
    return pd.DataFrame(dict(signal_date=pd.Timestamp("2020-01-31"), ticker=["A","B","C","D"],
        predAA=[0.,1.,2.,3.], predBA=[0.,1.,2.,3.], predAB=[0.,1.,2.,3.], predBB=[0.,1.,2.,3.]))


class FactorialMetricsTests(unittest.TestCase):
    def test_feature_only_response_labels_zero_and_identity(self):
        f = panel()
        f["predBA"] = f["predBB"] = [3.,2.,1.,0.]
        result = fm.evaluate_factorial(f)
        first = result["rank_effects"][0]
        self.assertAlmostEqual(first["signed_feature"], .75)
        self.assertEqual(first["signed_label"], 0.)
        self.assertEqual(first["interaction"], 0.)
        self.assertAlmostEqual(result["aggregate"]["contrasts"]["AA-BA"]["rank_mad"], .5)
        self.assertEqual(result["aggregate"]["contrasts"]["AA-AB"]["rank_mad"], 0.)
        self.assertTrue(result["identity"]["PASS"])
        for record in result["rank_effects"]:
            self.assertAlmostEqual(record["signed_feature"]+record["signed_label"], record["total_rank_change"], places=12)

    def test_label_only_response_features_zero(self):
        f = panel()
        f["predAB"] = f["predBB"] = [3.,2.,1.,0.]
        result = fm.evaluate_factorial(f)
        self.assertEqual(result["rank_effects"][0]["signed_feature"], 0.)
        self.assertAlmostEqual(result["rank_effects"][0]["signed_label"], .75)
        self.assertEqual(result["aggregate"]["effects"]["interaction_mean_abs"], 0.)

    def test_joint_only_interaction_is_not_added_again(self):
        f = panel()
        f["predBB"] = [3.,2.,1.,0.]
        result = fm.evaluate_factorial(f)
        first = result["rank_effects"][0]
        self.assertAlmostEqual(first["signed_feature"], .375)
        self.assertAlmostEqual(first["signed_label"], .375)
        self.assertAlmostEqual(first["interaction"], .75)
        self.assertAlmostEqual(first["total_rank_change"], .75)
        contrasts = result["aggregate"]["contrasts"]
        self.assertEqual(contrasts["AA-BA"]["rank_mad"], 0.)
        self.assertEqual(contrasts["AA-AB"]["rank_mad"], 0.)
        self.assertAlmostEqual(contrasts["AB-BB"]["rank_mad"], .5)
        self.assertAlmostEqual(contrasts["BA-BB"]["rank_mad"], .5)

    def test_cancelling_effects_total_zero_no_percentage_share(self):
        f = panel()
        f["predBA"] = [3.,2.,1.,0.]
        result = fm.evaluate_factorial(f)
        first = result["rank_effects"][0]
        self.assertAlmostEqual(first["signed_feature"], .375)
        self.assertAlmostEqual(first["signed_label"], -.375)
        self.assertEqual(first["total_rank_change"], 0.)
        self.assertTrue(first["exact_total_cancellation"])
        self.assertEqual(result["aggregate"]["effects"]["exact_total_cancellation_fraction"], 1.)
        self.assertEqual(result["aggregate"]["contrasts"]["AA-BB"]["rank_mad"], 0.)
        self.assertGreater(result["aggregate"]["effects"]["feature_mean_abs"], 0.)
        self.assertFalse(any("share" in key for key in first))

    def test_average_tie_ranks_and_deterministic_ticker_winner(self):
        f = panel()
        for cell in fm.CELLS:
            f["pred"+cell] = 1.
        a = fm.evaluate_factorial(f)
        b = fm.evaluate_factorial(f.sample(frac=1, random_state=10))
        self.assertEqual(a, b)
        self.assertEqual(a["rank_effects"][0]["rankAA"], .625)
        c = a["aggregate"]["contrasts"]["AA-BB"]
        self.assertIsNone(c["spearman"])
        self.assertEqual(c["defined_spearman_dates"], 0)
        self.assertEqual(c["top1_flip"], 0.)
        self.assertEqual(a["per_date"][0]["contrasts"]["AA-BB"]["top1_a"], "A")
        self.assertEqual(a["per_date"][0]["ties"]["AA"]["top1_tie_count"], 4)

    def test_top5_set_overlap_and_boundary_tie(self):
        f = pd.DataFrame(dict(signal_date=pd.Timestamp("2020-01-31"), ticker=list("ABCDEFGH")))
        for cell in fm.CELLS:
            f["pred"+cell] = 0.
        # BB lifts H, hence AA chooses A-E and BB chooses H,A-D.
        f.loc[f.ticker == "H", "predBB"] = 1.
        result = fm.evaluate_factorial(f)
        c = result["aggregate"]["contrasts"]["AA-BB"]
        self.assertAlmostEqual(c["top5_jaccard"], 4/6)
        self.assertEqual(c["top1_flip"], 1.)
        self.assertEqual(result["per_date"][0]["ties"]["BB"]["top5_boundary_tie_count"], 7)

    def test_equal_date_weights_do_not_weight_large_universe_more(self):
        f = panel().iloc[:2].copy()
        f["predBB"] = [1.,0.]
        second = pd.DataFrame(dict(signal_date=pd.Timestamp("2020-02-29"), ticker=[f"T{i}" for i in range(10)]))
        for cell in fm.CELLS:
            second["pred"+cell] = np.arange(10.)
        result = fm.evaluate_factorial(pd.concat([f,second], ignore_index=True))
        c = result["aggregate"]["contrasts"]["AA-BB"]
        self.assertAlmostEqual(c["rank_mad"], .25)
        self.assertNotAlmostEqual(c["rank_mad"], 1/12)
        self.assertAlmostEqual(c["top1_flip"], .5)
        self.assertEqual(result["coverage"]["dates"], 2)

    def test_positive_score_scaling_and_offsets_do_not_change_rank_attribution(self):
        f = panel()
        f["predBB"] = [3.,2.,1.,0.]
        a = fm.evaluate_factorial(f)
        for i,cell in enumerate(fm.CELLS):
            f["pred"+cell] = f["pred"+cell] * (i+2) + 100*i
        self.assertEqual(fm.evaluate_factorial(f), a)

    def test_unrelated_outcome_columns_are_ignored(self):
        f = panel()
        original = fm.evaluate_factorial(f)
        f["future_return"] = np.inf
        f["target_rank_21"] = np.nan
        self.assertEqual(fm.evaluate_factorial(f), original)

    def test_reject_duplicate_missing_empty_or_invalid_date_keys(self):
        invalid = [pd.concat([panel(),panel().iloc[[0]]]), panel().assign(ticker=None),
            panel().assign(ticker=" "), panel().assign(signal_date=pd.NaT),
            panel().assign(signal_date=pd.Timestamp("2020-01-31 12:00")),
            panel().assign(signal_date=pd.Timestamp("2020-01-31",tz="UTC")), panel().iloc[:0], panel().iloc[:1]]
        for f in invalid:
            with self.subTest(rows=len(f)):
                with self.assertRaises(ValueError):
                    fm.evaluate_factorial(f)

    def test_reject_nonfinite_predictions_in_each_cell(self):
        for cell in fm.CELLS:
            for value in (np.nan, np.inf, -np.inf):
                with self.subTest(cell=cell,value=value):
                    f = panel()
                    f.loc[0,"pred"+cell] = value
                    with self.assertRaisesRegex(ValueError,"Nonfinite predictions"):
                        fm.evaluate_factorial(f)

    def test_expected_coverage_rejects_missing_complete_row(self):
        f = panel()
        keys = f[["signal_date","ticker"]]
        fm.evaluate_factorial(f,expected_keys=keys.sample(frac=1,random_state=8))
        with self.assertRaisesRegex(ValueError,"coverage differs"):
            fm.evaluate_factorial(f.iloc[1:],expected_keys=keys)

    def test_custom_date_column_and_invalid_tolerance(self):
        renamed = panel().rename(columns={"signal_date":"date","ticker":"symbol"})
        result = fm.evaluate_factorial(renamed,date_col="date",ticker_col="symbol")
        self.assertIn("date",result["rank_effects"][0])
        self.assertIn("symbol",result["rank_effects"][0])
        for value in (0., -1., np.nan, np.inf):
            with self.subTest(tolerance=value):
                with self.assertRaises(ValueError):
                    fm.evaluate_factorial(panel(),tolerance=value)


if __name__ == "__main__":
    unittest.main()
