import unittest
import numpy as np
import pandas as pd
from paper_ltr_monthly_v1.plot_years import annual_returns

class AnnualChartTests(unittest.TestCase):
    def test_compounding_and_partial_years_are_not_annualized(self):
        dates=pd.to_datetime(['2017-02-01','2017-12-29','2018-01-02','2026-07-01'])
        values=np.array([1.1,1.21,1.089,1.3068])
        y=annual_returns(dates,values)
        self.assertAlmostEqual(y.loc[2017],.21)
        self.assertAlmostEqual(y.loc[2018],-.1)
        self.assertAlmostEqual(y.loc[2026],.2)
        self.assertAlmostEqual(np.prod(1+y),values[-1])
    def test_invalid_dates_fail(self):
        with self.assertRaises(ValueError):annual_returns(pd.to_datetime(['2020-01-01','2020-01-01']),np.ones(2))

if __name__=='__main__':unittest.main()
