"""Literal accounting and state cases for the independent reference only."""
import unittest
import numpy as np
import pandas as pd

from account_reference import independent_orders
from policy_reference import PolicyReference, Slot
from signal_reference import percentile


class Prices:
    def __init__(self):
        self.n = 4
        self.p = {'names':np.array(['A','B','C','D']), 'dates':pd.bdate_range('2020-01-01',periods=20), 'observed':np.ones((20,4),bool)}
        values = dict(C=100.,sma10=99.,sma21=99.,sma63=99.,sma200=90.,m5=.01,m21=.02,high5_prev=99.,peak63=100.,sigma21=.02)
        self.f = {key:np.full((20,4),value) for key,value in values.items()}
        self.weekly = np.ones(20,bool)
        self.pick = [0,1]
        self.correlations = {}
    def selection(self,k):
        w = np.zeros(4);w[self.pick]=.5
        return w,dict(selected_indices=list(self.pick))
    def opportunity_pool(self,k,entry_confirmation=False):
        return (2,3)
    def correlation(self,k,a,b):
        return self.correlations.get((a,b),0.)


class ReferenceTests(unittest.TestCase):
    def test_percentile_ties(self):
        np.testing.assert_allclose(percentile([5,1,1,3]),[1,.375,.375,.75])

    def test_mask_uses_whole_account_budget(self):
        # Untouched A has jumped to EUR 20k; B sale may trade without selling A.
        orders = independent_orders(np.array([100.,50.]),0.,np.array([np.nan,100.]),np.array([200.,100.]),np.array([.8,0.]),1.,.0015,True)
        self.assertEqual(len(orders),1)
        self.assertEqual(orders[0]['j'],1)
        self.assertEqual(orders[0]['side'],'SELL')
        self.assertEqual(orders[0]['quantity'],50.)
        self.assertEqual(orders[0]['cost'],8.5)

    def test_targeted_buy_is_self_financed(self):
        orders = independent_orders(np.array([100.,0.]),5000.,np.array([np.nan,100.]),np.array([200.,100.]),np.array([.8,.5]),1.,.0015,False)
        self.assertEqual(len(orders),1)
        self.assertEqual(orders[0]['j'],1)
        self.assertAlmostEqual(orders[0]['notional']+orders[0]['cost'],5000.)
        self.assertAlmostEqual(orders[0]['notional'],4999/1.0015)

    def test_missing_masked_quote_never_fills(self):
        orders = independent_orders(np.array([0.,20.]),100.,np.array([100.,np.nan]),np.array([100.,100.]),np.zeros(2),1.,.0015,True)
        self.assertEqual(orders,[])

    def context(self,p,k,weights,*,initial=False,scheduled=False,pending=None,queue=(),last_buy=None):
        current=np.array(weights,float)
        buys=np.full(4,-1,int) if last_buy is None else np.array(last_buy)
        return p.decide(k,current,current*100,10000*(1-current.sum()),10000.,buys,pending,queue,initial=initial,scheduled=scheduled)

    def test_probe_requires_completed_buy_and_later_close(self):
        market=Prices();pol=PolicyReference(market,'EXIT21_STAGED')
        self.context(pol,0,[0,0,0,0],initial=True)
        market.f['sma21'][1,1]=101.;market.f['m5'][1,1]=-.01
        self.context(pol,1,[.5,.5,0,0])
        market.f['sma63'][2,1]=110.
        probe,_=self.context(pol,2,[.5,0,0,0]);self.assertEqual(probe['nominal'][1],.25)
        pending,_=self.context(pol,3,[.5,0,0,0]);self.assertIsNone(pending)
        same_close,_=self.context(pol,4,[.5,.25,0,0],last_buy=[1,4,-1,-1]);self.assertIsNone(same_close)
        later,_=self.context(pol,5,[.5,.25,0,0],last_buy=[1,4,-1,-1]);self.assertEqual(later['nominal'][1],.5)
        self.assertEqual(pol.slots[1].first_fill_idx,4)

    def test_busy_exit_updates_state_but_does_not_issue(self):
        market=Prices();pol=PolicyReference(market,'EXIT21_STAGED')
        self.context(pol,0,[0,0,0,0],initial=True)
        market.f['sma21'][1:3,1]=101.;market.f['m5'][1:3,1]=-.01
        blocked,_=self.context(pol,1,[.5,.5,0,0],queue=({'due':2},));self.assertIsNone(blocked)
        self.assertEqual(pol.slots[1].state,'CASH')
        residual,_=self.context(pol,2,[.5,.5,0,0]);self.assertEqual(residual['reason'],'DEFERRED_STATE')
        np.testing.assert_array_equal(residual['action_mask'],[False,True,False,False])

    def test_blocked_new_assignment_does_not_fast_reenter(self):
        market=Prices();market.f['peak63'][0,1]=125.
        pol=PolicyReference(market,'TRAIL15_STAGED')
        answer,_=self.context(pol,0,[0,0,0,0],initial=True)
        self.assertTrue(pol.fast(0,1));self.assertEqual(answer['nominal'][1],0)
        self.assertEqual(pol.slots[1].state,'CASH')

    def test_monthly_latch_and_cross_slot_ownership(self):
        market=Prices();pol=PolicyReference(market,'EXIT21_STAGED_FRESHW')
        pol.slots=[Slot(0,0,'CASH',0.,.1,None,None,0,True),Slot(1,0,'REBOUND',.5,.1,1,2,0,False)]
        market.pick=[0,1]
        pol.update_month(3)
        self.assertEqual(pol.slots[0].state,'REBOUND')
        self.assertEqual(pol.slots[0].entry_signal,1)
        self.assertEqual(pol.slots[0].first_fill_idx,2)

    def test_confirmed_vacancy_survives_same_asset_other_slot(self):
        market=Prices();pol=PolicyReference(market,'EXIT21_STAGED_FRESHW')
        pol.slots=[Slot(0,0,'CASH',0.,.1,None,None,0,True),Slot(1,0,'NORMAL',1.,.1,1,2,0,False)]
        pol.requested[0]=.5
        answer,_=self.context(pol,3,[.5,0,0,0])
        self.assertEqual(answer['nominal'][2],.25)
        self.assertEqual(pol.slots[0].asset,2)
        self.assertEqual(pol.slots[0].state,'REBOUND')

    def test_fresh_rejects_actual_correlated_holding(self):
        market=Prices();market.correlations={(2,0):.95,(3,0):.2}
        pol=PolicyReference(market,'EXIT21_STAGED_FRESHW')
        pol.slots=[Slot(0,0,'NORMAL',1.,.1,0,None,0,False),Slot(1,1,'CASH',0.,.1,None,None,0,True)]
        market.f['sma21'][3,1]=101.;market.f['m5'][3,1]=-.01
        pol.requested[0]=.5
        answer,_=self.context(pol,3,[.5,0,0,0])
        self.assertEqual(answer['nominal'][3],.25);self.assertEqual(answer['nominal'][2],0)
        self.assertEqual(pol.counts['fresh_correlation_rejections'],1)


if __name__=='__main__':
    unittest.main(verbosity=2)
