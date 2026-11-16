"""One structural change: invested monthly rotation, unchanged daily protection."""
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'olc111/src'))
from run_olc111 import MonthlyFitCache,AccountPolicy
from replay_engine import simulate


def load_module():
    path=ROOT/'src/run_rotation_overlay.py'
    assert path.exists(),'OLC112 rotation overlay has not been implemented'
    spec=importlib.util.spec_from_file_location('rotation_overlay_test',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod


class RotationOverlayTest(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('rotation_core',ROOT.parent/'olc110/source/src/core.py')
        self.core=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.core)
        dates=pd.bdate_range('2019-01-01',periods=340)
        p=dict(dates=dates,names=np.array(['A','B']),O=np.full((340,2),100.),
               C=np.full((340,2),100.),observed=np.ones((340,2),bool),benchmark=0)
        monthly=np.r_[dates.month[:-1]!=dates.month[1:],False]
        features=monthly.copy();features[-1]=True
        self.bundle=dict(panel=p,f=self.core.features(p),core=self.core,monthly=monthly,
            feature_monthly=features,targets=np.tile([0.,1.],(340,1)),breadth=np.full(340,.5),begin=300,
            cboe=dict(available=np.ones(340,bool),legacy=np.zeros((340,2)),term=np.zeros((340,2))))

    def cache(self,entry=-.01,cash=-.01):
        bank={}
        for head,y in [('CASH',cash),('FRESH',-.01),('ENTRY',entry)]:
            bank[head]=dict(Xprice=np.zeros((280,5 if head=='ENTRY' else 6)),
                Xlegacy=np.zeros((280,2)),Xterm=np.zeros((280,2)),y=np.full(280,y),
                signal_idx=np.arange(280),terminal_idx=np.arange(280)+21)
        return MonthlyFitCache(bank,self.bundle['panel']['dates'],300,
                               fit_options=dict(min_dates=30,min_blocks=1,n_boot=20))

    def context(self,cash=False,pending=None):
        return dict(initial=False,scheduled=True,units=np.array([0.,0.]) if cash else np.array([50.,0.]),
            cash=10000. if cash else 5000.,nav=10000.,pending=pending,queued=(),
            last_buy_idx=np.array([-1,-1]) if cash else np.array([280,-1]),last_sell_idx=np.array([-1,-1]))

    def test_monthly_rotation_is_preserved_when_learned_switch_is_negative(self):
        m=load_module();policy=m.RotationOverlay(self.bundle,'PRICE_ROTATION',self.cache())
        out=policy(303,np.array([.5,0.]),self.context())
        np.testing.assert_array_equal(out['weights'],[0.,1.])
        self.assertEqual(out['reason'],'SCHEDULED')
        self.assertFalse(out['force'])
        self.assertEqual(policy.trace[-1]['status'],'INVESTED_MONTHLY_ROTATION')

    def test_monthly_cash_book_is_not_forced_to_reenter(self):
        m=load_module();policy=m.RotationOverlay(self.bundle,'PRICE_ROTATION',self.cache())
        self.assertIsNone(policy(303,np.array([0.,0.]),self.context(cash=True)))
        self.assertEqual(policy.trace[-1]['action'],'HOLD')

    def test_monthly_cash_book_can_reenter_on_the_unchanged_positive_signal(self):
        m=load_module();policy=m.RotationOverlay(self.bundle,'PRICE_ROTATION',self.cache(entry=.01))
        out=policy(303,np.array([0.,0.]),self.context(cash=True))
        self.assertEqual(out['reason'],'ENTRY')
        np.testing.assert_array_equal(out['weights'],[0.,1.])

    def test_busy_monthly_account_does_not_replace_its_pending_order(self):
        m=load_module();policy=m.RotationOverlay(self.bundle,'PRICE_ROTATION',self.cache())
        self.assertIsNone(policy(303,np.array([.5,0.]),self.context(pending={'due_idx':304})))
        self.assertEqual(policy.trace[-1]['status'],'BUSY')

    def test_nonscheduled_decision_is_identical_to_olc111(self):
        m=load_module();cache=self.cache(cash=.01)
        old=AccountPolicy(self.bundle,'PRICE',cache)
        new=m.RotationOverlay(self.bundle,'PRICE_ROTATION',cache)
        context=self.context();context['scheduled']=False
        a=old(300,np.array([.5,0.]),context);b=new(300,np.array([.5,0.]),context)
        self.assertEqual(a['reason'],b['reason'])
        self.assertEqual(a['force'],b['force'])
        np.testing.assert_array_equal(a['weights'],b['weights'])
        self.assertEqual(old.trace[-1]['cash_mean'],new.trace[-1]['cash_mean'])

    def test_original_monthly_band_does_not_force_small_rebalance(self):
        m=load_module();self.bundle['targets'][:]=[.5,.5]
        policy=m.RotationOverlay(self.bundle,'PRICE_ROTATION',self.cache())
        monthly=np.zeros(340,bool);monthly[300]=True
        result=simulate(self.bundle['panel'],self.bundle['f'],lambda k,w:[.5,.5],monthly,
            legacy=self.core,account_policy=policy,initial_state=dict(units=[49.5,50.5],cash=0.),
            issue_initial=False,allow_scheduled_hold=True,
            start=str(self.bundle['panel']['dates'][300]),end=str(self.bundle['panel']['dates'][302]))
        self.assertTrue(result['orders'].empty)
        self.assertEqual(result['daily'].nav_close.iloc[-1],10000.)


if __name__=='__main__':unittest.main()
