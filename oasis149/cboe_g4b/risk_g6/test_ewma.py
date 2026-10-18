import unittest
import numpy as np
import pandas as pd
from oasis149.cboe_g4b.risk_g6.ewma_allocation import ewma_weights

class EWMAWeightTests(unittest.TestCase):
    def test_asof_no_future_price_contamination(self):
        dates=pd.bdate_range("2018-01-01",periods=350)
        names=[f"ETF{i}" for i in range(6)]
        rng=np.random.default_rng(101)
        v=np.exp(np.cumsum(rng.normal(0,.008,(350,6)),axis=0))
        df=pd.DataFrame(v,index=dates,columns=names)
        s=dates[320]
        before=ewma_weights(df,s,names)
        changed=df.copy()
        changed.loc[changed.index>s,:]*=100.
        after=ewma_weights(changed,s,names)
        self.assertEqual(before,after)
        self.assertAlmostEqual(sum(before.values()),1.,places=10)
        self.assertLessEqual(max(before.values()),.25+1e-10)
    def test_requires_same_six_distinct_names(self):
        d=pd.DataFrame({"ETF0":np.linspace(1,10,160)},
            index=pd.bdate_range("2017-01-01",periods=160))
        with self.assertRaises(AssertionError):
            ewma_weights(d,d.index[-1],["ETF0"]*6)
if __name__=="__main__":unittest.main()
