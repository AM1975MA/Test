import unittest
import numpy as np
import pandas as pd
from europe_only75.risk_ablation.run import (
    rebalance, model_policies, ci_bootstrap, selections
)

class EuropeOnlyRiskControls(unittest.TestCase):
    def test_self_funded_half_cash_no_cash_fee(self):
        shares,cash,turn,fee=rebalance({},1.,{"X":.4,"Y":.4},
                                          {"X":100.,"Y":100.})
        self.assertAlmostEqual(sum(shares[t]*100 for t in shares)+cash,1-fee,places=11)
        self.assertAlmostEqual(fee,turn*.001,places=12)
        self.assertTrue(.199<cash<.201)
        second=rebalance(shares,cash,{"X":.4,"Y":.4},
                         {"X":100.,"Y":100.})
        self.assertAlmostEqual(second[3],0,places=12)

    def test_full_funded_zero_cash(self):
        shares,cash,turn,fee=rebalance({},1.,{"X":.5,"Y":.5},
                                          {"X":100.,"Y":100.})
        self.assertAlmostEqual(cash,0.,places=11)
        self.assertAlmostEqual(sum(shares[t]*100 for t in shares),1-fee,places=11)

    def test_previous_close_features_not_future_mutation(self):
        dates=pd.bdate_range("2021-01-01",periods=200)
        v=np.arange(len(dates))
        close=pd.DataFrame({
            "X":np.exp(.0005*v+.001*np.sin(v)),
            "Y":np.exp(.0003*v+.002*np.cos(v))},index=dates)
        cats={"X":"EU_BROAD","Y":"EU_BROAD"}
        sigma=np.r_[.99,.85,np.linspace(.80,.05,58)]
        allnames=["X","Y"]+[f"ETF{i}" for i in range(58)]
        past=dates[-2]
        a,b,c=model_policies(["X","Y"],0,sigma,allnames,cats,close,past,[])
        altered=close.copy()
        altered.iloc[-1]=[1e6,1e-6]
        aa,bb,cc=model_policies(["X","Y"],0,sigma,allnames,cats,altered,past,[])
        self.assertEqual(a,aa)
        self.assertEqual(b,bb)
        self.assertEqual(c,cc)
        self.assertEqual(set(a["E1_CATEGORY"]),{"X","Y"})
        self.assertAlmostEqual(sum(a["E1_CATEGORY"].values()),.8)

    def test_frozen_top2_stable(self):
        names=["A","B","C","D"]
        pred=np.array([[.8,.9,.1,float("nan")]])
        self.assertEqual(selections(pred,names),[["B","A"]])

    def test_bootstrap_paired_dates_not_rows(self):
        x=ci_bootstrap(np.full(113,.007),n=50)
        self.assertAlmostEqual(x["ci_98_75"][0],.007)

if __name__=="__main__":
    unittest.main()
