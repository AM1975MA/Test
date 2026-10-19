"""Invariants: strict old model replay, 10bp funded mixture, prior-Close states."""
import unittest
import numpy as np
import pandas as pd
from research_reset.predict149.complementarity.run import (
    monthly_weights,trade_policy,state_from_past,causal_decisions,K)

class ComplementaryExpertsTests(unittest.TestCase):
    def test_merge_weights_uses_underlying_etfs_and_overlap_correctly(self):
        w=monthly_weights([("F3",.5,["A","B","C","D","E"]),
                           ("H1",.5,["A","B","F","G","H"])])
        self.assertEqual(len(w),8)
        self.assertAlmostEqual(sum(w.values()),1.,places=14)
        self.assertAlmostEqual(w["A"],.2,places=14)
        self.assertAlmostEqual(w["C"],.1,places=14)
        self.assertAlmostEqual(w["H"],.1,places=14)
    def test_price_change_after_signal_does_not_change_expert_regime(self):
        rng=np.random.default_rng(101)
        names=["SPY","HYG","AGG","A","B"]
        prices=pd.DataFrame(np.exp(np.cumsum(
            rng.normal(0,.007,(200,len(names))),axis=0)),
            index=pd.bdate_range("2018-01-01",periods=200),columns=names)
        roster=pd.DataFrame({"ticker":names})
        sig=prices.index[150]
        a,f=state_from_past(prices,roster,sig,.4)
        modified=prices.copy()
        modified.loc[modified.index>sig,:]*=40.
        b,g=state_from_past(modified,roster,sig,.4)
        np.testing.assert_array_equal(a,b)
        self.assertEqual(f,g)
    def test_fixed_mixture_money_conservation_and_churn(self):
        names=["A","B","C","D","E","F","G","H"]
        days=pd.bdate_range("2020-01-01",periods=50)
        px=pd.DataFrame(np.full((50,len(names)),10.),index=days,columns=names)
        w=monthly_weights([("F3",.5,names[:5]),("H1",.5,["A","B","F","G","H"])])
        cash,econ=trade_policy([w,w],px,days,[0,1],names)
        self.assertEqual(len(cash),43)
        np.testing.assert_allclose(cash,1/1.001,atol=1e-12)
        self.assertEqual(econ["trade_dates"],1)
    def test_online_expert_never_looks_at_just_finished_unavailable_month(self):
        signal_dates=pd.bdate_range("2021-01-01",periods=120*21)
        # use decision signal date = day before month START open:
        prior=[d-pd.Timedelta(days=1) for d in signal_dates]
        asof_diff=np.linspace(-.05,.05,64)
        m={"F3":asof_diff, "H1":np.zeros(64)}
        x=np.random.default_rng(12).normal(0,1,(64,8))
        a=causal_decisions(m,x,signal_dates,prior)
        k=25
        # k-1 month would END at current Open, hence must be invisible;
        # future months must not affect current decision either.
        changed=asof_diff.copy()
        changed[k-1:]+=2000
        b=causal_decisions({"F3":changed,"H1":np.zeros(64)},x,signal_dates,prior)
        for mode in ("SWITCH_PAST3","SWITCH_PAST6","ONLINE_RIDGE_GATE"):
            self.assertAlmostEqual(a[mode][k],b[mode][k],places=12)
        # Previous *matured* data k-2 must influence switch timing in theory.
        assert all(len(a[k])==64 for k in a)
if __name__=="__main__":unittest.main()
