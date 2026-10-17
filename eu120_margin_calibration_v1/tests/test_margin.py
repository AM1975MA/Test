"""Unit checks: no tuning, year-cluster uncertainty, known mechanical margins."""
import unittest
import numpy as np,pandas as pd
from eu120_margin_calibration_v1.run import stat,newyear_bootstrap
class TestMarginCalibration(unittest.TestCase):
    def setUp(self):
        x=[]
        for year in range(2017,2027):
            for month in range(1,13):
                i=(year-2017)*12+month
                m=.01 if i%2 else .09
                x.append(dict(year=year,month=month,margin=m,
                    spread=.03 if m==.09 else -.02))
        self.df=pd.DataFrame(x)
    def test_original_high_low_threshold_carries_predictive_spread(self):
        z=stat(self.df,.06)
        self.assertEqual(z["high_months"],60)
        self.assertEqual(z["low_months"],60)
        self.assertAlmostEqual(z["high_minus_low_mean_spread"],.05,places=14)
        self.assertEqual(z["high_winner_probability"],1.)
        self.assertEqual(z["low_winner_probability"],0.)
    def test_uncertainty_uses_year_resampling(self):
        z=newyear_bootstrap(self.df,.06,234,N=25)
        ci=z["year_cluster_bootstrap_95pct_CI_high_minus_low"]
        self.assertTrue(ci[0]<=.05<=ci[1])
        self.assertEqual(z["permutations"],25)
    def test_margin_disabled_negative_control(self):
        self.assertTrue(np.array_equal(
            (self.df.margin>=.06).to_numpy(),(self.df.margin>.04).to_numpy()))
if __name__=="__main__":unittest.main()
