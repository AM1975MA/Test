import unittest
import numpy as np
import pandas as pd
from causal_target_contract import signal_eligible, original_relative_target, mature_groups_only, compare_base_and_extended

class ContractTests(unittest.TestCase):
    def rows(self,with_new=False,dec="2022-01-31"):
        d=pd.Timestamp(dec)
        data=[
          {"signal_date":d,"ticker":"A","fwd_ret_21":.01,"fwd_ret_42":.02,"fwd_ret_63":.04,"exit_date_63":d+pd.Timedelta(days=90)},
          {"signal_date":d,"ticker":"B","fwd_ret_21":.03,"fwd_ret_42":.08,"fwd_ret_63":.05,"exit_date_63":d+pd.Timedelta(days=90)},
          {"signal_date":d,"ticker":"C","fwd_ret_21":-.01,"fwd_ret_42":-.03,"fwd_ret_63":-.07,"exit_date_63":d+pd.Timedelta(days=90)}
        ]
        if with_new:
            data.append({"signal_date":d,"ticker":"D","fwd_ret_21":.15,"fwd_ret_42":.23,"fwd_ret_63":.38,"exit_date_63":d+pd.Timedelta(days=90)})
        return pd.DataFrame(data)

    def test_relative_label_changes_with_universe(self):
        old=self.rows()
        new=self.rows(True)
        x=compare_base_and_extended(old,new)
        self.assertEqual(len(x),3)
        self.assertTrue(x.changed.any())
        self.assertTrue((x.delta_target<0).any())

    def test_target_matches_declared_powers(self):
        g=self.rows()
        z=original_relative_target(g)
        self.assertTrue((z.TARGET>0).all())
        ranks=g[["fwd_ret_21","fwd_ret_42","fwd_ret_63"]].rank(axis=0,pct=True)
        expected=.45*ranks.fwd_ret_21**1.5+.35*ranks.fwd_ret_42**1.5+.2*ranks.fwd_ret_63**1.5
        np.testing.assert_allclose(z.TARGET.to_numpy(),expected.to_numpy(),atol=0,rtol=0)

    def test_reject_missing_future_outcome_for_training(self):
        g=self.rows()
        g.loc[g.ticker=="A","fwd_ret_63"]=float("nan")
        with self.assertRaises(ValueError):
            original_relative_target(g)
        self.assertEqual(len(mature_groups_only(g,"2023-01-01")),0)

    def test_full_group_maturity_and_cutoff(self):
        a=self.rows()
        b=self.rows(dec="2022-11-30")
        cohort=pd.concat([a,b],ignore_index=True)
        result=mature_groups_only(cohort,"2023-01-01")
        self.assertEqual(result.signal_date.nunique(),1)
        self.assertEqual(set(result.ticker),{"A","B","C"})
        self.assertTrue((pd.to_datetime(result.signal_date)<pd.Timestamp("2023-01-01")).all())

    def test_eligibility_asof_invariant_to_future_data(self):
        dt=pd.bdate_range("2020-01-01","2023-10-31")
        prices=pd.DataFrame({"date":dt,"open":100.,"high":101.,"low":99.,"close":100.})
        pre=prices[prices.date.lt("2022-05-31")].copy()
        got=signal_eligible(pre,"2022-05-31")
        self.assertTrue(got)
        future=prices[prices.date.ge("2022-05-31")].copy()
        future[["open","high","low","close"]]=1000000.
        mutated=pd.concat([pre,future],ignore_index=True)
        self.assertEqual(got,signal_eligible(mutated,"2022-05-31"))

    def test_close_outside_range_not_eligible(self):
        dt=pd.bdate_range("2020-01-01","2022-12-30")
        prices=pd.DataFrame({"date":dt,"open":100.,"high":101.,"low":99.,"close":100.})
        self.assertTrue(signal_eligible(prices,"2022-12-31"))
        prices.loc[prices.date.eq(pd.Timestamp("2022-11-14")),"close"]=110.0
        self.assertFalse(signal_eligible(prices,"2022-12-31"))

    def test_baseline_old_return_cannot_be_rewritten(self):
        a=self.rows();b=self.rows(True)
        b.loc[b.ticker=="A","fwd_ret_21"]=.999
        with self.assertRaises(ValueError):
            compare_base_and_extended(a,b)

    def test_reject_duplicate_cohort(self):
        a=self.rows()
        with self.assertRaises(ValueError):
            original_relative_target(pd.concat([a,a.iloc[:1]],ignore_index=True))

if __name__=="__main__":
    unittest.main(verbosity=2)
