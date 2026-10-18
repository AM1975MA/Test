"""M0b synthetic placebo matching / exact five-position cash accounting."""
import unittest
import numpy as np
import pandas as pd
from research_reset.m0b.enrichment import (
    rebalance_exact,trial_surrogates,portfolio,STRIDE)

class ConditionalPlaceboTests(unittest.TestCase):
    def test_true_self_financing_fee_when_first_buy(self):
        q={f"A{i}":10. for i in range(5)}
        w={f"A{i}":.2 for i in range(5)}
        h,c,turn,fee,_=rebalance_exact({},1.,w,q)
        self.assertAlmostEqual(c,0.)
        self.assertAlmostEqual(sum(h[t]*q[t] for t in q),1./1.001,places=12)
        self.assertAlmostEqual(fee,1-1/1.001,places=12)
        hh,cc,t2,c2,_=rebalance_exact(h,0.,w,q)
        self.assertLess(t2,1e-10)
        self.assertLess(c2,1e-10)
        self.assertEqual(h,hh)
    def test_both_trade_sides_pay_actual_fee(self):
        q={f"A{i}":10. for i in range(6)}
        w1={f"A{i}":.2 for i in range(5)}
        h,c,_,_,_=rebalance_exact({},1.,w1,q)
        w2={f"A{i}":.2 for i in [0,1,2,3,5]}
        hh,cc,turn,fee,_=rebalance_exact(h,c,w2,q)
        self.assertAlmostEqual(sum(hh[t]*q[t] for t in hh),1./1.001-fee,places=10)
        self.assertGreater(turn,0)
        self.assertGreater(fee,0)
        self.assertAlmostEqual(fee,turn*.001,places=11)
    def test_retained_placeholder_count_and_category_and_vol(self):
        a=[f"A{i:02d}" for i in range(12)]
        b=[f"B{i:02d}" for i in range(12)]
        allnames=a+b
        cat={x:"A" for x in a}|{x:"B" for x in b}
        members={"A":a,"B":b}
        anchors=list(pd.bdate_range("2020-01-01",periods=4))
        vol=pd.DataFrame({
            n:[.01+.0006*(i%12)]*4 for i,n in enumerate(allnames)
        },index=anchors)
        seq=[
            [a[0],a[1],a[2],b[0],b[1]],
            [a[0],a[3],a[4],b[0],b[2]],
            [a[0],a[3],a[5],b[3],b[4]],
            [a[1],a[3],a[6],b[3],b[4]]]
        for kind in ("category_and_vol","category_only"):
            mapped,err=trial_surrogates(seq,anchors,vol,cat,members,kind,np.random.default_rng(99))
            self.assertTrue(np.isfinite(err))
            for t in range(4):
                self.assertEqual(len(set(mapped[t])),5)
                self.assertEqual([cat[n] for n in seq[t]],
                                 [cat[n] for n in mapped[t]])
                if t>0:
                    self.assertEqual(len(set(seq[t])&set(seq[t-1])),
                                 len(set(mapped[t])&set(mapped[t-1])))
    def test_portfolio_constant_prices_cannot_gain_and_does_not_churn(self):
        names=[f"E{i}" for i in range(5)]
        prices=np.full((112*STRIDE+1,5),20.,float)
        days=pd.bdate_range("2017-01-01",periods=len(prices))
        result,path=portfolio([names]*112,prices,names,days)
        self.assertAlmostEqual(path[-1],1/1.001,places=10)
        self.assertEqual(result["trade_days"],1)
        self.assertAlmostEqual(result["total_nominal_fees_initial_units"],1-1/1.001,places=10)
if __name__=="__main__":unittest.main()
