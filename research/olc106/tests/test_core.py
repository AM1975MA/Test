
import unittest
import numpy as np
import pandas as pd
from core import capped_inverse_vol, rebalance, portfolio_metrics, features, simulate

def panel(n=360, assets=5):
    dates=pd.bdate_range("2018-01-02", periods=n)
    close=np.repeat((100*np.exp(np.arange(n)*.001))[:,None],assets,axis=1)
    op=close.copy()
    return dict(dates=dates,names=np.array(["F"+str(i) for i in range(assets)]),O=op,C=close,observed=np.ones_like(close,bool),benchmark=0)

class ContractTests(unittest.TestCase):
    def test_cap_and_cash(self):
        w=capped_inverse_vol(np.array([.1,.2]))
        np.testing.assert_allclose(w,[.25,.25])
        w=capped_inverse_vol(np.array([.05,.1,.2,.25,.3,.4]))
        self.assertLessEqual(w.max(),.25+1e-12)
        self.assertAlmostEqual(w.sum(),1.)
    def test_self_financing(self):
        u,c,orders=rebalance(np.zeros(2),10000.,np.array([100.,50.]),np.array([.5,.5]),1.,.0015,0.,False)
        self.assertGreaterEqual(c,-1e-8)
        self.assertAlmostEqual(float(u@np.array([100.,50.])+c+sum(x["cost"] for x in orders)),10000.,places=7)
        self.assertEqual(len(orders),2)
    def test_missing_open_no_fill(self):
        u,c,orders=rebalance(np.zeros(2),10000.,np.array([np.nan,50.]),np.array([.5,.5]),1.,.0015,0.,False,mark=np.array([100.,50.]))
        self.assertEqual(u[0],0.)
        self.assertEqual(len(orders),1)
        self.assertEqual(orders[0]["j"],1)
    def test_cash_exit_cost(self):
        u,c,orders=rebalance(np.array([50.]),0.,np.array([100.]),np.zeros(1),1.,.0015,.03,True)
        self.assertEqual(float(u[0]),0.)
        self.assertAlmostEqual(c,4991.5)
    def test_no_trade_band(self):
        u,c,orders=rebalance(np.array([50.,50.]),0.,np.array([100.,100.]),np.array([.51,.49]),1.,.0015,.03,False)
        self.assertEqual(len(orders),0)
    def test_metric_peak_does_not_reset(self):
        m=portfolio_metrics([100.,80.,90.,70.,120.],pd.date_range("2020-01-01",periods=5),100.)
        self.assertAlmostEqual(m["maxdd_close"],-.3)
        self.assertAlmostEqual(m["cumulative"],.2)
    def test_passive_price_ratio_and_cost(self):
        p=panel()
        r=simulate(p,"PASSIVE",ticket=1.,impact=.0015,lag=0,start=str(p["dates"][270].date()),end=str(p["dates"][-1].date()))
        expected=(10000-1)/1.0015*p["C"][-1,0]/p["O"][270,0]
        self.assertAlmostEqual(r["daily"].nav_close.iloc[-1],expected,places=7)
        self.assertEqual(len(r["orders"]),1)
    def test_lag_affects_first_fill(self):
        p=panel()
        r=simulate(p,"PASSIVE",lag=2,start=str(p["dates"][270].date()),end=str(p["dates"][-1].date()))
        self.assertEqual(pd.Timestamp(r["orders"].date.iloc[0]),p["dates"][272])
    def test_features_future_mutation(self):
        p=panel()
        a=features(p)
        p["C"][310:]*=2
        b=features(p)
        np.testing.assert_allclose(a["score"][:310],b["score"][:310],equal_nan=True)
    def test_simulation_prefix_invariance(self):
        p=panel(n=420)
        start=str(p["dates"][270].date());end=str(p["dates"][-1].date())
        a=simulate(p,"DIVERSE_RISK15",start=start,end=end)
        p["C"][350:]*=.3;p["O"][350:]*=.3
        b=simulate(p,"DIVERSE_RISK15",start=start,end=end)
        np.testing.assert_allclose(a["daily"].nav_close.values[:80],b["daily"].nav_close.values[:80],rtol=1e-12)
    def test_drawdown_exit_not_retroactive(self):
        p=panel(n=410)
        p["C"][300:]*=.6;p["O"][301:]*=.6
        r=simulate(p,"DIVERSE_GUARD",start=str(p["dates"][270].date()),end=str(p["dates"][-1].date()))
        exits=r["alerts"].query("reason == 'DD_EXIT'")
        self.assertGreaterEqual(len(exits),1)
        self.assertGreater(pd.Timestamp(exits.execution_not_before.iloc[0]),pd.Timestamp(exits.signal_date.iloc[0]))
        self.assertLess(r["daily"].nav_close.min(),r["daily"].nav_close.iloc[0]*.8)
    def test_missing_open_deferred(self):
        p=panel();p["O"][270,0]=np.nan
        r=simulate(p,"PASSIVE",start=str(p["dates"][270].date()),end=str(p["dates"][-1].date()))
        self.assertEqual(pd.Timestamp(r["orders"].date.iloc[0]),p["dates"][271])
        self.assertGreaterEqual(r["deferred_sessions"],1)

if __name__=="__main__":
    unittest.main()
