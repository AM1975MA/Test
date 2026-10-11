import unittest
import pandas as pd
from history_window_v1.contract import trim, mature_rows, selection_disagreement

class ContractTests(unittest.TestCase):
    def test_cutoff_inclusive_and_values_preserved(self):
        x = pd.DataFrame({'date': pd.to_datetime(['2010-12-31','2011-01-01','2012-01-01']), 'Close':[99.,100.,101.]})
        y = trim(x)
        pd.testing.assert_frame_equal(y, x.iloc[1:].reset_index(drop=True))

    def test_warmup_and_strict_maturity(self):
        x = pd.DataFrame({'signal_date':pd.to_datetime(['2011-12-30','2012-01-31','2016-12-30']), 'exit_date_21':pd.to_datetime(['2012-02-01','2012-03-01','2017-01-01'])})
        self.assertEqual(mature_rows(x, 'exit_date_21',2017).index.tolist(), [1])

    def test_disagreement_aligns_dates_and_order(self):
        a=pd.DataFrame({'date':['a','b'],'top1':['X','X'],'top2':['Y','Y']})
        b=pd.DataFrame({'date':['b','a'],'top1':['X','Y'],'top2':['Y','X']})
        r=selection_disagreement([a,b,a])
        self.assertEqual(r['top1_any_count'],1)
        self.assertEqual(r['top2_ordered_any_count'],1)
        self.assertEqual(r['top2_set_any_count'],0)

if __name__ == '__main__': unittest.main()
