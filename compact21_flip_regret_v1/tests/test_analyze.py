"""Pure-unit regression tests for descriptive flip diagnostics."""
from __future__ import annotations

import unittest
import numpy as np
import pandas as pd

from compact21_flip_regret_v1.analyze import top_choice, pair_record


class FlipRegretUnitTests(unittest.TestCase):
    def test_tie_break_is_lexical_and_zero_score_gap(self):
        df = pd.DataFrame({"ticker":["ZZZ", "BBB", "AAA", "DDD"], "pred":[5.,5.,5.,1.]})
        choice=top_choice(df)
        self.assertEqual(choice["ticker"], "AAA")
        self.assertEqual(choice["raw_margin"], 0.)
        self.assertEqual(choice["norm_margin"], 0.)

    def test_iqr_score_margin_scale_invariant(self):
        df=pd.DataFrame({"ticker":["A","B","C","D"],"pred":[4.,3.,2.,0.]})
        a,b=top_choice(df),top_choice(df.assign(pred=df.pred*100+17))
        self.assertAlmostEqual(a["norm_margin"],b["norm_margin"],places=12)

    def test_two_equal_choices_do_not_claim_return_gap(self):
        o=pd.DataFrame({"ticker":["AAA"],"signal_date":pd.to_datetime(["2020-01-31"]),
                        "exit_date_21":pd.to_datetime(["2020-03-01"]),
                        "fwd_ret_21":[.05]}).set_index("ticker")
        c={"ticker":"AAA", "norm_margin":0.3}
        r=pair_record(c,c,o)
        self.assertFalse(r["flip"])
        self.assertFalse(r["both_future_returns_mature"])
        self.assertIsNone(r["abs_forward_return_difference_pp"])

    def test_forward_return_units_are_percentage_points(self):
        o=pd.DataFrame({"ticker":["AAA","BBB"],
                        "signal_date":pd.to_datetime(["2020-01-31"]*2),
                        "exit_date_21":pd.to_datetime(["2020-03-01"]*2),
                        "fwd_ret_21":[.11,.02]}).set_index("ticker")
        c1={"ticker":"AAA", "norm_margin":0.05}
        c2={"ticker":"BBB", "norm_margin":0.15}
        r=pair_record(c1,c2,o)
        self.assertTrue(r["flip"])
        self.assertTrue(r["weak_margin_0p10"])
        self.assertTrue(r["both_future_returns_mature"])
        self.assertAlmostEqual(r["abs_forward_return_difference_pp"],9.,places=12)
        self.assertAlmostEqual(r["signed_forward_return_difference_pp"],9.,places=12)

    def test_future_immature_outcome_excluded(self):
        o=pd.DataFrame({"ticker":["AAA","BBB"],
                        "signal_date":pd.to_datetime(["2026-06-30"]*2),
                        "exit_date_21":pd.to_datetime(["2026-08-01"]*2),
                        "fwd_ret_21":[.11,.02]}).set_index("ticker")
        x=pair_record({"ticker":"AAA","norm_margin":.3},
                      {"ticker":"BBB","norm_margin":.2},o)
        self.assertTrue(x["flip"])
        self.assertFalse(x["both_future_returns_mature"])
        self.assertIsNone(x["abs_forward_return_difference_pp"])

    def test_zero_iqr_is_reported_missing_not_weak(self):
        df=pd.DataFrame({"ticker":["AAA","BBB","CCC"],"pred":[1.,1.,1.]})
        a=top_choice(df)
        self.assertIsNone(a["norm_margin"])
        o=pd.DataFrame({"ticker":["AAA","BBB"],"signal_date":pd.to_datetime(["2020-01-31"]*2),
            "exit_date_21":pd.to_datetime(["2020-03-01"]*2),"fwd_ret_21":[.1,.02]}).set_index("ticker")
        res=pair_record(a,{"ticker":"BBB","norm_margin":.2},o)
        self.assertIsNone(res["weak_margin_0p10"])

if __name__=="__main__":
    unittest.main()
