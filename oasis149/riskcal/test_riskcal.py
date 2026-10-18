"""Risk probability forecasts must not access prices after the signal close."""
import unittest
import numpy as np
import pandas as pd
from oasis149.riskcal.run import make_risk_forecast

class RiskCalTests(unittest.TestCase):
    def test_future_mutation_cannot_modify_probability(self):
        dates=pd.bdate_range("2018-01-01",periods=420)
        rng=np.random.default_rng(5)
        names=["ETF1","ETF2","ETF3","ETF4","ETF5","ETF6"]
        close=pd.DataFrame(np.exp(np.cumsum(rng.normal(0,.01,(420,6)),axis=0)),
                           index=dates,columns=names)
        signal=dates[350]
        before=make_risk_forecast(close,signal,names,32)
        after=close.copy()
        after.loc[after.index>signal,:]*=.20
        later=make_risk_forecast(after,signal,names,32)
        self.assertEqual(before,later)
        for k in ["K1_GAUSSIAN","K2_T5_COVARIANCE","K3_HISTORICAL_BLOCKS"]:
            self.assertTrue(0<before[k]<1)
    def test_single_holding_is_finite(self):
        dates=pd.bdate_range("2018-01-01",periods=300)
        close=pd.DataFrame({"A":np.exp(np.cumsum(np.sin(np.arange(300))/100))},index=dates)
        x=make_risk_forecast(close,dates[280],["A"],55)
        self.assertIsNotNone(x)
        self.assertTrue(np.isfinite(x["K1_GAUSSIAN"]))
if __name__=="__main__":unittest.main()
