"""Preregistered RED tests: causal downside semideviation repairs threshold NaNs."""
from __future__ import annotations
import unittest
import numpy as np
import pandas as pd
from compact21_downvol_cleanup_v1.clean import downside_semideviation, repair_downvol_family


class DownvolCleanerTests(unittest.TestCase):
    def setup_ret(self,h=63,negative=10):
        return pd.DataFrame({"AAA": np.array([-.01]*negative+[.005]*(h-negative),float)},
                            index=pd.date_range("2020-01-01",periods=h,freq="B"))

    def test_few_down_days_is_finite_even_if_legacy_nan(self):
        x=self.setup_ret()
        old=x.where(x<0).rolling(63,min_periods=31).std(ddof=0).iloc[-1,0]
        self.assertTrue(np.isnan(old))
        y=downside_semideviation(x,63)
        self.assertAlmostEqual(y.iloc[-1,0],np.sqrt(10*.01**2/63*252),places=14)

    def test_positive_window_is_zero_not_missing(self):
        x=self.setup_ret(63,negative=0)
        y=downside_semideviation(x,63)
        self.assertTrue(np.isnan(y.iloc[61,0]))
        self.assertEqual(float(y.iloc[-1,0]),0.)

    def test_missing_return_is_not_imputed_or_zeroed(self):
        x=self.setup_ret()
        x.iloc[13,0]=np.nan
        y=downside_semideviation(x,63)
        self.assertTrue(np.isnan(y.iloc[-1,0]))

    def test_no_future_dependency(self):
        x=self.setup_ret(126)
        first=downside_semideviation(x.iloc[:63],63)
        x.iloc[-1,0]=9000.
        final=downside_semideviation(x,63)
        pd.testing.assert_series_equal(first.iloc[-1],final.iloc[62])

    def test_consistent_full_family_replacement_and_nonfamily_identity(self):
        dates=pd.DatetimeIndex([pd.Timestamp("2020-03-27"),pd.Timestamp("2020-05-07")])
        idx=pd.MultiIndex.from_product([dates,["AAA"]],names=["signal_date","ticker"])
        panel=pd.DataFrame({"downvol21":[np.nan,1.],"downvol21_pct":[np.nan,.5],
            "downvol21_dev":[np.nan,3.],"other":[9.,10.]},index=idx).reset_index()
        other_before=panel["other"].copy()
        raw=self.setup_ret(90,negative=9)
        repaired=repair_downvol_family(panel,raw,dates,[21])
        pd.testing.assert_series_equal(panel.other,other_before,check_exact=True)
        self.assertTrue(repaired["downvol21"].notna().any())
        self.assertEqual(repaired["downvol21_pct"].iloc[0],1.)
        self.assertTrue(repaired["downvol21_dev"].isna().all())
        self.assertTrue(panel.downvol21.isna().iloc[0])

    def test_reject_duplicate_keys(self):
        raw=self.setup_ret(63)
        p=pd.DataFrame({"signal_date":["2020-03-27","2020-03-27"],"ticker":["AAA","AAA"],
            "downvol21":[np.nan,np.nan],"downvol21_pct":[np.nan,np.nan],"downvol21_dev":[np.nan,np.nan]})
        with self.assertRaises(ValueError):
            repair_downvol_family(p,raw,pd.to_datetime(["2020-03-27"]),[21])

if __name__=="__main__":
    unittest.main()
