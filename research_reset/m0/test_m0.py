"""M0 invariants: no free wealth, no fictitious oracle deployability and matched null."""
import unittest
import numpy as np
from research_reset.m0.experiment import (
    simulate,matched_class_switch_null,choose_rank,STRIDE,FEE)

class M0Tests(unittest.TestCase):
    def setUp(self):
        self.names=("AAA","BBB","CCC","SPY","AGG")
        days=112*STRIDE+1
        self.prices=np.tile(np.array([10.,15.,20.,100.,100.]),(days,1)).astype(float)
    def test_no_trade_is_bought_once_and_never_churns(self):
        picks=["AAA"]*112
        w,logs,f=simulate(picks,self.prices,self.names,0)
        self.assertAlmostEqual(w[-1],1./(1.+FEE),places=14)
        self.assertEqual(f["switches"],0)
        self.assertEqual(f["fee_sides"],1)
    def test_one_switch_pays_both_market_sides(self):
        picks=["AAA"]*30+["BBB"]*82
        w,logs,f=simulate(picks,self.prices,self.names,0)
        self.assertAlmostEqual(w[-1],1./(1+FEE)*(1-FEE)/(1+FEE),places=12)
        self.assertEqual(f["switches"],1)
        self.assertEqual(f["fee_sides"],3)
    def test_clairvoyant_execution_delay_is_delayed_exactly(self):
        self.prices[1:,"AAA"]=12.
        self.prices[1:,"SPY"]=105.
        picks=["AAA"]*112
        direct,_,_=simulate(picks,self.prices,self.names,0)
        late,_,_=simulate(picks,self.prices,self.names,3)
        self.assertNotAlmostEqual(float(direct[-1]),float(late[-1]),places=4)
        self.assertLess(late[0],1.)
    def test_null_exact_switches_and_class_match(self):
        groups={"AAA":"E","BBB":"E","CCC":"F","SPY":"F","AGG":"F"}
        members={"E":["AAA","BBB"],"F":["CCC","SPY","AGG"]}
        seq=["AAA","AAA","BBB","CCC","CCC","AAA","SPY"]*16
        rng=np.random.default_rng(14)
        for _ in range(20):
            generated=matched_class_switch_null(seq,groups,members,rng)
            self.assertEqual(len(generated),112)
            self.assertEqual(sum(a!=b for a,b in zip(seq[:-1],seq[1:])),
                sum(a!=b for a,b in zip(generated[:-1],generated[1:])))
            self.assertTrue(all(groups[x]==groups[y] for x,y in zip(seq,generated)))
    def test_rank_does_not_peek_at_future_quote(self):
        import pandas as pd
        base=pd.Series({"AAA":.10,"BBB":-.2,"CCC":.05})
        chosen=choose_rank(base)
        future_prices=pd.Series({"AAA":1e6,"BBB":.01,"CCC":2e5})
        self.assertEqual(choose_rank(base),chosen)
        self.assertNotEqual(choose_rank(future_prices),chosen)
if __name__=="__main__":unittest.main()
