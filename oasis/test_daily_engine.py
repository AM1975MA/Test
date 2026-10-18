"""OASIS model and execution unit tests with pure synthetic prices."""
import unittest
import numpy as np
import pandas as pd
from oasis.observers import (prepare,market_states,ranks,relative_lower_bound,
       ChangePointObserver,switch_names)
from oasis.daily_backtest import execute

class TestOASIS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        idx=pd.bdate_range("2014-01-01",periods=720)
        rng=np.random.default_rng(20261018)
        base=rng.normal(.0003,.007,(720,40))
        base[:,1:]=base[:,1:]+base[:,:1]*.3
        cls.p=pd.DataFrame(np.exp(np.cumsum(base,axis=0)),
             index=idx,columns=[f"E{i:02d}" for i in range(40)])
    def test_no_future_close_signal_or_regime_leak(self):
        d=self.p.index[600]
        f=prepare(self.p)
        g=market_states(f)
        q=self.p.copy()
        q.loc[q.index>d,:]*=100.
        ff=prepare(q)
        gg=market_states(ff)
        row=f["score"].loc[d].to_numpy()
        newrow=ff["score"].loc[d].to_numpy()
        np.testing.assert_allclose(row,newrow,atol=0,rtol=0,equal_nan=True)
        self.assertEqual(g.loc[d].state,gg.loc[d].state)
        self.assertEqual(ranks(f,600),ranks(ff,600))
    def test_no_trading_without_actual_open(self):
        shares,cash,book=execute({},1.,["A","B"],1.,
            {"A":10.,"B":np.nan},{"A":10.,"B":20.})
        self.assertEqual(book["blocked_orders"],1)
        self.assertNotIn("B",shares)
        self.assertGreaterEqual(cash,0.)
        self.assertLessEqual(cash+sum(q*{"A":10.,"B":20.}[t] for t,q in shares.items()),1.)
    def test_decision_near_tie_no_switch(self):
        f=prepare(self.p)
        idx=650
        held=ranks(f,idx)[:2]
        updated,reason=switch_names(f,idx,held,
            {held[0]:15,held[1]:15},"P2")
        self.assertEqual(len(updated),2)
        self.assertEqual(len(set(updated)),2)
        self.assertTrue(all(t in self.p.columns for t in updated))
    def test_missing_incumbent_is_not_an_alpha_exit(self):
        original=prepare(self.p)
        k=650
        previous=ranks(original,k)[:2]
        broken=dict(original)
        broken["score"]=original["score"].copy()
        broken["score"].loc[self.p.index[k],previous[0]]=np.nan
        chosen,reason=switch_names(broken,k,previous,
            {previous[0]:30,previous[1]:30},"P2")
        self.assertEqual(chosen,previous)
        self.assertEqual(reason,"INCUMBENT_CLOSE_MISSING_HOLD")
    def test_partial_position_preserved(self):
        original=prepare(self.p);k=650
        keep=ranks(original,k)[10]
        chosen,reason=switch_names(original,k,[keep],{keep:10},"P2")
        self.assertIn(keep,chosen)
        self.assertEqual(len(chosen),2)
        self.assertEqual(reason,"FILL_MISSING_POSITION")
    def test_bocpd_posteriors_normalize(self):
        a=ChangePointObserver()
        for z in [0.,.25,-.1]*30+[-4.,-3.]:
            a.update(z)
            self.assertAlmostEqual(a.p.sum(),1.,places=11)
            self.assertTrue((a.p>=0).all())
    def test_multiplicity_conservative(self):
        f=prepare(self.p);i=650
        picks=ranks(f,i)
        lo=relative_lower_bound(f,i,picks[0],picks[2],1)
        hi=relative_lower_bound(f,i,picks[0],picks[2],60)
        self.assertLessEqual(hi,lo)
    def test_state_names(self):
        states=market_states(prepare(self.p))
        self.assertTrue(set(states.state.unique()).issubset(
            {"BREATHING","SHOCK","CONTINUATION","RECOVERY"}))

if __name__=="__main__":unittest.main()
