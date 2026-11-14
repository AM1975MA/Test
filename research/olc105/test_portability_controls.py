"""Contract tests for the declared World/momentum CONTROLS, not OLC19 forecasts."""
import importlib.util
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

SPEC=importlib.util.find_spec('portability_controls')
if SPEC is not None:
    import portability_controls as p
else:
    p=None

class RequiredImplementation(unittest.TestCase):
    def test_engine_exists(self):
        self.assertIsNotNone(p, 'CONTROL_ENGINE_NOT_IMPLEMENTED')

@unittest.skipIf(p is None, 'implementation not present yet')
class Accounting(unittest.TestCase):
    def test_initial_fee_and_spread_are_financed(self):
        u,c,cost,orders=p.rebalance(np.zeros(2),1000.,np.array([10.,20.]),np.array([.5,.5]),1.,.001)
        expected=(1000.-2.)/1.001
        self.assertAlmostEqual(float(u@np.array([10.,20.])+c),expected,places=8)
        self.assertAlmostEqual(cost,1000.-expected,places=8)
        self.assertGreaterEqual(c,-1e-8)
        self.assertEqual(orders,2)
    def test_sell_and_buy_have_separate_tickets(self):
        u,c,cost,orders=p.rebalance(np.array([10.,0.]),0.,np.array([10.,10.]),np.array([0.,1.]),1.,0.)
        np.testing.assert_allclose(u,[0.,9.8])
        self.assertAlmostEqual(cost,2.)
        self.assertEqual(orders,2)
    def test_no_trade_has_no_fee(self):
        u,c,cost,orders=p.rebalance(np.array([10.,10.]),0.,np.array([10.,10.]),np.array([.5,.5]),1.,.01)
        np.testing.assert_array_equal(u,[10.,10.]);self.assertEqual(cost,0.);self.assertEqual(orders,0)
    def test_invalid_prices_rejected(self):
        with self.assertRaises(ValueError):p.rebalance(np.zeros(2),100.,np.array([10.,np.nan]),np.array([.5,.5]),1.,.001)
    def test_invalid_weights_rejected(self):
        with self.assertRaises(ValueError):p.rebalance(np.zeros(2),100.,np.array([10.,10.]),np.array([.5,.6]),1.,.001)
    def test_higher_cost_does_not_create_money(self):
        for fee in (0.,1.,2.):
            for bps in (0.,5.,15.,30.):
                old=np.array([7.,2.,1.]);px=np.array([11.,25.,19.]);cash=231.
                u,c,co,n=p.rebalance(old,cash,px,np.array([.3,.5,.2]),fee,bps/10000)
                self.assertAlmostEqual(float(old@px+cash),float(u@px+c+co),places=7)
                self.assertTrue(np.all(u>=0));self.assertGreaterEqual(c,-1e-7)
    def test_zero_cost_preserves_equity(self):
        u,c,co,n=p.rebalance(np.array([4.,0.]),20.,np.array([10.,5.]),np.array([.5,.5]),0.,0.)
        self.assertAlmostEqual(float(u@np.array([10.,5.])+c),60.)
    def test_future_prices_cannot_change_past_signal(self):
        dates=pd.bdate_range('2020-01-01',periods=270)
        s=pd.Series(np.linspace(10.,15.,270),index=dates)
        cutoff=dates[255]
        a=p.momentum_asof(s,cutoff)
        s.loc[s.index>cutoff]*=100
        self.assertEqual(a,p.momentum_asof(s,cutoff))
    def test_short_history_is_ineligible(self):
        s=pd.Series(np.ones(251),index=pd.bdate_range('2020-01-01',periods=251))
        self.assertIsNone(p.momentum_asof(s,s.index[-1]))
    def test_stale_price_is_ineligible(self):
        s=pd.Series(np.ones(260),index=pd.bdate_range('2020-01-01',periods=260))
        self.assertIsNone(p.momentum_asof(s,s.index[-1]+pd.Timedelta(days=6)))
    def test_drawdown_includes_initial_capital(self):
        d=pd.bdate_range('2020-01-01',periods=3)
        m=p.metrics(np.array([90.,95.,100.]),100.,d)
        self.assertAlmostEqual(m['max_drawdown'],-.1)
        self.assertAlmostEqual(m['net_cumulative'],0.)
    def test_world_no_cost_total_return_identity(self):
        px=np.array([10.,12.,9.,15.]);u=100./px[0]
        self.assertAlmostEqual(u*px[-1]/100.-1.,.5)

if __name__=='__main__':unittest.main(verbosity=2)
