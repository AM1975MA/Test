import unittest
import pandas as pd
from compact21_downvol_cleanup_v1.summarize_training import exact_prediction_cohort

class AnnualSummaryOrderingTests(unittest.TestCase):
    def input_frames(self):
        return pd.DataFrame({
            "vintage":[2,1,1,2],
            "signal_date":pd.to_datetime(["2020-02-28","2020-01-31","2020-02-28","2020-01-31"]),
            "ticker":["AAA"]*4,
            "target_rank_21":[.6,.7,.8,.9],
            "pred":[.1,.2,.3,.4]})
    def test_year_vintage_order_is_not_a_support_change(self):
        original=self.input_frames()
        reordered=original.iloc[[1,3,0,2]].reset_index(drop=True)
        exact_prediction_cohort(reordered,original)

    def test_changed_label_still_fails_after_sorting(self):
        original=self.input_frames()
        changed=original.iloc[::-1].reset_index(drop=True).copy()
        changed.loc[0,"target_rank_21"]=.123
        with self.assertRaises(AssertionError):
            exact_prediction_cohort(changed,original)

if __name__=="__main__":
    unittest.main()
