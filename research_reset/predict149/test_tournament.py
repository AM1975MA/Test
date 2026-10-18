"""Scientific invariants for best-ticker predictor tournament."""
import unittest
import numpy as np
import pandas as pd
from research_reset.predict149.tournament import precompute,portfolio,FEATS
from oasis149.canonical import load_149
class BestTickerTests(unittest.TestCase):
    def test_asof_future_prices_do_not_change_features(self):
        dates=pd.bdate_range("2018-01-01",periods=390)
        rng=np.random.default_rng(14)
        names=["SPY","AAA","BBB","CCC","DDD","EEE"]
        data=pd.DataFrame(np.exp(np.cumsum(rng.normal(0,.007,(390,6)),axis=0)),
            index=dates,columns=names)
        roster=pd.DataFrame({"ticker":names,"macro_category":["C01","C01","C01","C02","C02","C03"]})
        sig=dates[250]
        a,_=precompute(data,roster)
        mutated=data.copy()
        mutated.loc[mutated.index>sig,:]*=100.
        b,_=precompute(mutated,roster)
        for feature in FEATS:
            np.testing.assert_allclose(a[feature].loc[sig].to_numpy(float),
                 b[feature].loc[sig].to_numpy(float),rtol=0,atol=0)
    def test_portfolio_no_free_wealth_when_prices_constant(self):
        days=pd.bdate_range("2018-01-01",periods=84)
        names=["A","B","C","D","E","F"]
        marks=np.ones((84,6))*10.
        x,m=portfolio([names[:5],names[:5]],[0,1],marks,names,days)
        self.assertEqual(len(x),43)
        self.assertAlmostEqual(x[-1],1/1.001,places=12)
        self.assertAlmostEqual(x[0],x[-1],places=12)
        self.assertAlmostEqual(m["gross_turnover_notional_initial_units"],1/1.001,places=10)
    def test_real_149_roster_sha_and_exact_count(self):
        roster,O,C,V,days,signals,quality=load_149()
        self.assertEqual(len(roster),149)
        self.assertEqual(roster.ticker.nunique(),149)
        self.assertEqual(len(days),2366)
        self.assertGreaterEqual(quality.pre2017_observations.min(),252)
if __name__=="__main__":unittest.main()
