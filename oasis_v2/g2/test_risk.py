"""G2 core invariants: conservative sizing must not mint money or lever."""
import unittest,math
import numpy as np
import pandas as pd
from oasis_v2.g2.risk_portfolio import execute_targets,limited_weights,student_risk_loss
class G2Tests(unittest.TestCase):
    def test_simplex_exact_and_25pct_cap(self):
        a=limited_weights({f"A{i}":v for i,v in enumerate([12.,2.,1.,1.,1.,1.])})
        self.assertAlmostEqual(sum(a.values()),1.,places=12)
        self.assertLessEqual(max(a.values()),.250000001)
        self.assertEqual(len(a),6)
    def test_fee_preserves_wealth(self):
        prices={f"E{i}":10. for i in range(6)}
        targets={k:1./6. for k in prices}
        h,c,n,fee,_=execute_targets({},1.,targets,prices)
        after=c+sum(q*prices[k] for k,q in h.items())
        self.assertGreaterEqual(c,0)
        self.assertLess(after,1)
        self.assertGreater(n,0)
        self.assertAlmostEqual(fee,1-after)
        self.assertEqual(len(h),6)
    def test_no_free_money_on_rebalancing(self):
        prices={"A":10.,"B":20.}
        h,c,n,fee,_=execute_targets({},1.,{"A":.5,"B":.5},prices)
        prev=c+sum(q*prices[t] for t,q in h.items())
        h,c,n,fee,_=execute_targets(h,c,{"B":.5,"A":.5},prices)
        after=c+sum(q*prices[t] for t,q in h.items())
        self.assertLessEqual(after,prev+1e-12)
    def test_student_scenarios_only_have_positive_tail(self):
        dates=pd.bdate_range("2018-01-01",periods=130)
        rng=np.random.default_rng(55)
        r=pd.DataFrame(rng.normal(0,.009,(130,6)),
            index=dates,columns=[f"E{i}" for i in range(6)])
        w={f"E{i}":1/6 for i in range(6)}
        e=student_risk_loss(r,w,33)
        self.assertTrue(math.isfinite(e))
        self.assertGreaterEqual(e,0)
        self.assertLess(e,1.)
if __name__=="__main__":unittest.main()
