"""Economic as-of oil vs growth and independent exposure risk budget."""
import unittest
import numpy as np
import pandas as pd
from research_reset.predict149.complementarity.mechanisms.run import dynamic_weights
class T149EconomicMechanisms(unittest.TestCase):
    def test_no_future_close_impacts_either_causal_allocations(self):
        names=["USO","QQQ","A","B","C","D","E","F","G","H"]
        dates=pd.bdate_range("2017-01-02",periods=200)
        r=np.random.default_rng(19)
        clos=pd.DataFrame(np.exp(np.cumsum(r.normal(0,.01,(200,10)),axis=0)),
            columns=names,index=dates)
        f3=["A","B","C","D","E"];h1=["B","D","F","G","H"]
        signal=dates[170]
        a,b,meta=dynamic_weights(clos,signal,f3,h1)
        changed=clos.copy()
        changed.loc[changed.index>signal,:]*=10000.
        c,d,other=dynamic_weights(changed,signal,f3,h1)
        self.assertEqual(a,c)
        self.assertEqual(b,d)
        self.assertEqual(meta,other)
        self.assertAlmostEqual(sum(a.values()),1.)
        self.assertAlmostEqual(sum(b.values()),1.)
        self.assertTrue(.2<=meta["allocated_weight_f3_inverse_risk"]<=.8)
    def test_exact_equal_vol_gives_equal_expert_weight(self):
        names=["USO","QQQ","A","B","C","D","E","F","G","H"]
        dates=pd.bdate_range("2018-01-01",periods=150)
        r=np.random.default_rng(14)
        one=np.exp(np.cumsum(r.normal(0,.01,150)))
        data=pd.DataFrame({t:one.copy() for t in names},index=dates)
        f3=["A","B","C","D","E"];h1=["B","D","F","G","H"]
        oil,balanced,details=dynamic_weights(data,dates[130],f3,h1)
        self.assertAlmostEqual(details["allocated_weight_f3_inverse_risk"],.5)
        self.assertAlmostEqual(sum(balanced.values()),1.)
if __name__=="__main__":unittest.main()
