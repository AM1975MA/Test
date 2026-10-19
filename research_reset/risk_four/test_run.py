import unittest
import numpy as np
import pandas as pd
from research_reset.risk_four.run import (
    rebalance_cash, factor_weights, vol20_weights, trend126_weights,
    buffer_expert
)

class TestRiskFour(unittest.TestCase):
    def test_exact_cash_budget_and_fee_only_on_etf(self):
        shares,cash,turn,fee=rebalance_cash({},1.,{"A":.60},{"A":100.})
        self.assertAlmostEqual(cash,.4*(1-fee),places=10)
        self.assertAlmostEqual(sum(shares.values())*100+cash,1-fee,places=10)
        self.assertAlmostEqual(fee,0.001*turn,places=12)
        self.assertGreater(cash,.39)
        shares2,cash2,turn2,fee2=rebalance_cash(shares,cash,{"A":.60},{"A":100.})
        self.assertAlmostEqual(fee2,0.,places=11)
        self.assertAlmostEqual(cash2,cash,places=11)

    def test_full_investment_no_double_charging(self):
        shares,cash,turn,fee=rebalance_cash({},1.,{"A":.5,"B":.5},
                                             {"A":100.,"B":100.})
        self.assertAlmostEqual(1-fee,1/1.001,places=12)
        self.assertAlmostEqual(cash,0.,places=12)
        self.assertAlmostEqual(turn,1-fee,places=12)
        self.assertAlmostEqual(sum(shares.values())*100,1-fee,places=12)

    def test_factor_group_equity_and_no_hidden_substitution(self):
        dates=pd.bdate_range("2022-01-03",periods=150)
        t=np.arange(150,dtype=float)
        base=np.cumsum(.01*np.sin(t*.7))
        closes=pd.DataFrame({"A":np.exp(base),
                             "B":np.exp(base+0.0001*np.sin(t)),
                             "C":np.exp(np.cumsum(.015*np.cos(t*.5)))},index=dates)
        factor=pd.DataFrame(index=dates)
        for j,k in enumerate(("SPY","TLT","GLD","USO","HYG","UUP","VNQ","XLE")):
            factor[k]=np.exp(base) if j==0 else np.exp(
                np.cumsum(.01*np.cos(t*(j+1)*.1)))
        src={"A":.4,"B":.35,"C":.25}
        new,info=factor_weights(src,closes,factor,dates[-1])
        self.assertEqual(set(new),set(src))
        self.assertAlmostEqual(sum(new.values()),1.,places=12)
        self.assertTrue(info["distinct_factors"]>=1)

    def test_risk_signal_strictly_past(self):
        dates=pd.bdate_range("2021-01-01",periods=200)
        vals=np.linspace(10,20,200)
        prices=pd.DataFrame({"A":vals,"B":vals*1.03+0.2*np.sin(np.arange(200))},
                            index=dates)
        w={"A":.5,"B":.5}
        vol1,s1=vol20_weights(w,prices,dates[-2])
        trend1,s2=trend126_weights(w,prices,dates[-2])
        mutated=prices.copy()
        mutated.iloc[-1,:]=1e9
        vol2,_=vol20_weights(w,mutated,dates[-2])
        trend2,_=trend126_weights(w,mutated,dates[-2])
        self.assertEqual(vol1,vol2)
        self.assertEqual(trend1,trend2)

    def test_buffer_keeps_strict_rank_control(self):
        allnames=[f"T{i:03d}" for i in range(149)]
        data=pd.Series(np.linspace(2.,0.,149),index=allnames)
        initial=allnames[:5]
        self.assertEqual(buffer_expert(data,"F3",[],initial),initial)
        selection=buffer_expert(data,"F3",initial,initial)
        self.assertEqual(len(set(selection)),5)
        self.assertEqual(set(selection),set(initial))

if __name__=="__main__":
    unittest.main()
