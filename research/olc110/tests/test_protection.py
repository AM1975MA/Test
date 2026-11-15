"""Behavioral tests for realized-account cash and rebound decisions.

Fixtures specify literal feature values; expected target changes are hand-derived.
"""
from pathlib import Path
import importlib.util
import sys
import unittest
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


class ProtectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=ROOT/'src/protection.py'
        if not path.exists():
            cls.mod=None
            return
        spec=importlib.util.spec_from_file_location('protection_under_test',path)
        cls.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.mod)

    def setUp(self):
        self.n=4;self.T=320;shape=(self.T,self.n)
        self.p={'names':np.array(['A','B','C','D']),
                'dates':pd.bdate_range('2019-01-01',periods=self.T),
                'observed':np.ones(shape,bool)}
        self.f={key:np.full(shape,value,float) for key,value in {
            'C':100.,'sma10':99.,'sma21':99.,'sma63':99.,'sma200':90.,
            'm5':.01,'m21':.02,'m63':.05,'b21':.02,'a21':.02,
            'acceleration21':0.,'high5_prev':99.,'peak63':100.,'sigma21':.02}.items()}
        self.f['m252']=np.tile([.5,.4,.3,.2],(self.T,1))
        self.f['returns']=np.zeros(shape)
        self.f['liquid_eligible']=np.ones(shape,bool)
        self.f['liquid_features']={'rank_b21':np.full(shape,.5),'rank_a21':np.full(shape,.5)}
        self.monthly=np.zeros(self.T,bool);self.monthly[265]=True
        self.weekly=np.zeros(self.T,bool);self.weekly[[254,259,264]]=True

    def policy(self,arm='EXIT21_STAGED'):
        self.assertIsNotNone(self.mod,'Protection state machine is not implemented')
        return self.mod.make_account_policy(self.p,self.f,self.monthly,self.weekly,arm,252)

    def ctx(self,k,current,*,initial=False,scheduled=False,pending=None,queued=(),buys=None):
        current=np.array(current,float);last=np.full(self.n,-1,int)
        if buys:
            for j,t in buys.items():last[j]=t
        return dict(initial=initial,scheduled=scheduled,units=current*100,
                    nav=10000.,cash=10000*(1-current.sum()),pending=pending,
                    queued=queued,last_buy_idx=last,last_sell_idx=np.full(self.n,-1,int))

    def call(self,pol,k,current,**kw):
        return pol(k,np.array(current,float),self.ctx(k,current,**kw))

    def initialized(self,arm='EXIT21_STAGED'):
        pol=self.policy(arm);a=self.call(pol,252,[0,0,0,0],initial=True,scheduled=True)
        np.testing.assert_allclose(a['weights'],[.5,.5,0,0])
        return pol

    def bad(self,k,j=1):
        self.f['sma21'][k,j]=101.;self.f['m5'][k,j]=-.02

    def fast_not_slow(self,k,j=1):
        self.f['sma63'][k,j]=110.;self.f['m5'][k,j]=.01
        self.f['sma10'][k,j]=99.;self.f['high5_prev'][k,j]=99.

    def exited(self,arm='EXIT21_STAGED'):
        pol=self.initialized(arm);self.bad(253)
        a=self.call(pol,253,[.5,.5,0,0],buys={0:253,1:253})
        np.testing.assert_allclose(a['weights'],[.5,0,0,0])
        return pol

    def test_exit_targets_only_failing_asset(self):
        pol=self.initialized();self.bad(253)
        a=self.call(pol,253,[.6,.4,0,0],buys={0:253,1:253})
        np.testing.assert_array_equal(a['action_mask'],[False,True,False,False])
        self.assertTrue(a['sell_only']);self.assertEqual(a['weights'][1],0)

    def test_slow_does_not_reverse_simultaneous_exit(self):
        pol=self.exited();self.bad(254)
        # Long trend is positive but short trend still orders an exit.
        self.assertIsNone(self.call(pol,254,[.5,0,0,0]))

    def test_monthly_keeps_cash_when_same_asset_still_fails(self):
        pol=self.exited();self.bad(265)
        a=self.call(pol,265,[.5,0,0,0],scheduled=True)
        self.assertEqual(a['weights'][1],0)

    def test_reordered_monthly_slots_preserve_state_by_asset(self):
        pol=self.exited();self.bad(265);self.f['m252'][265,:2]=[.4,.5]
        a=self.call(pol,265,[.5,0,0,0],scheduled=True)
        self.assertEqual(a['weights'][1],0);self.assertEqual(a['weights'][0],.5)

    def test_unsold_asset_cannot_reenter_or_create_vacancy(self):
        pol=self.exited();self.fast_not_slow(254)
        self.assertIsNone(self.call(pol,254,[.5,.5,0,0]))

    def test_busy_book_defers_event_but_later_emits_remaining_exit(self):
        pol=self.initialized();self.bad(253);self.bad(254)
        self.assertIsNone(self.call(pol,253,[.5,.5,0,0],queued=({'instruction_id':1},)))
        a=self.call(pol,254,[.5,.5,0,0]);self.assertEqual(a['weights'][1],0)

    def test_staged_rebound_uses_half_slot(self):
        pol=self.exited();self.fast_not_slow(254)
        a=self.call(pol,254,[.5,0,0,0]);self.assertEqual(a['weights'][1],.25)

    def test_fast_control_rebound_uses_full_slot(self):
        pol=self.exited('EXIT21_FAST');self.fast_not_slow(254)
        a=self.call(pol,254,[.5,0,0,0]);self.assertEqual(a['weights'][1],.5)

    def test_probe_requires_actual_fill_then_later_close(self):
        pol=self.exited();self.fast_not_slow(254)
        self.call(pol,254,[.5,0,0,0])
        self.assertIsNone(self.call(pol,255,[.5,0,0,0]))
        self.assertIsNone(self.call(pol,256,[.5,.25,0,0],buys={1:256}))
        a=self.call(pol,257,[.5,.25,0,0],buys={1:256})
        self.assertEqual(a['weights'][1],.5)

    def test_rebound_uses_own_failure_barrier(self):
        pol=self.exited();self.fast_not_slow(254);self.call(pol,254,[.5,0,0,0])
        self.bad(255);self.f['sma63'][255,1]=110.
        self.assertIsNone(self.call(pol,255,[.5,.25,0,0],buys={1:255}))
        self.bad(256);self.f['sma10'][256,1]=101.
        a=self.call(pol,256,[.5,.25,0,0],buys={1:255});self.assertEqual(a['weights'][1],0)

    def test_monthly_only_reentry_waits_for_calendar(self):
        pol=self.exited('EXIT21_MONTHLY')
        self.assertIsNone(self.call(pol,254,[.5,0,0,0]))
        a=self.call(pol,265,[.5,0,0,0],scheduled=True);self.assertEqual(a['weights'][1],.5)

    def emerging(self,k,j=2):
        self.f['b21'][k,j]=.1;self.f['a21'][k,j]=0.;self.f['acceleration21'][k,j]=.1
        self.f['liquid_features']['rank_b21'][k,j]=1.
        self.f['liquid_features']['rank_a21'][k,j]=.25

    def test_fresh_requires_vacancy_and_starts_as_probe(self):
        pol=self.exited('EXIT21_STAGED_FRESHW');self.bad(254);self.emerging(254)
        a=self.call(pol,254,[.5,0,0,0]);self.assertEqual(a['weights'][2],.25)
        self.assertEqual(a['weights'][1],0)
        self.assertIsNone(self.call(pol,255,[.5,0,.25,0],buys={2:255}))
        a=self.call(pol,256,[.5,0,.25,0],buys={2:255});self.assertEqual(a['weights'][2],.5)

    def test_original_reentry_precedes_fresh_opportunity(self):
        pol=self.exited('EXIT21_STAGED_FRESHW');self.emerging(254)
        a=self.call(pol,254,[.5,0,0,0]);self.assertEqual(a['weights'][1],.5)
        self.assertEqual(a['weights'][2],0)

    def test_fresh_rejects_correlated_actual_holding(self):
        pol=self.exited('EXIT21_STAGED_FRESHW');self.bad(254);self.emerging(254)
        seq=np.linspace(-.01,.01,126);self.f['returns'][129:255,0]=seq;self.f['returns'][129:255,2]=seq
        self.assertIsNone(self.call(pol,254,[.5,0,0,0]))

    def test_primary_held_in_other_slot_does_not_block_fresh_fallback(self):
        pol=self.initialized('EXIT21_STAGED_FRESHW')
        self.weekly[[254,257,260]]=True
        self.bad(253,0);self.call(pol,253,[.5,.5,0,0])
        self.bad(254,0);self.emerging(254,2)
        self.call(pol,254,[0,.5,0,0])  # C replaces exited A.
        self.call(pol,255,[0,.5,.25,0],buys={2:255})
        self.bad(256,1);self.call(pol,256,[0,.5,.25,0],buys={2:255})
        self.bad(257,1);self.emerging(257,0)
        self.call(pol,257,[0,0,.5,0],buys={2:256})  # A replaces exited B.
        self.call(pol,258,[.25,0,.5,0],buys={0:258,2:256})
        self.bad(259,2);self.call(pol,259,[.25,0,.5,0],buys={0:258,2:256})
        self.emerging(260,3)
        a=self.call(pol,260,[.5,0,0,0],buys={0:259})
        self.assertIsNotNone(a,'A held by the other slot cannot suppress a qualified D fallback')
        self.assertEqual(a['weights'][3],.25)

    def test_confirmed_cash_slot_does_not_claim_later_other_slot_holding(self):
        self.monthly[265]=False
        pol=self.initialized('EXIT21_STAGED_FRESHW')
        self.bad(253,0);self.call(pol,253,[.5,.5,0,0])
        self.bad(254,0);self.emerging(254,2);self.call(pol,254,[0,.5,0,0])
        self.bad(255,1);self.call(pol,255,[0,.5,.25,0],buys={2:255})
        self.bad(259,1);self.emerging(259,0);self.call(pol,259,[0,0,.25,0],buys={2:255})
        self.bad(260,0);self.f['sma10'][260,0]=101.
        self.call(pol,260,[.25,0,.5,0],buys={0:260,2:255})  # A probe exits slot1.
        self.bad(262,2);self.bad(262,1)
        self.call(pol,262,[0,0,.5,0],buys={0:260,2:255})  # A sold; C exits slot0.
        self.bad(264,1);a=self.call(pol,264,[0,0,0,0])
        self.assertEqual(a['weights'][0],.5)  # A enters its original slot0.
        a=self.call(pol,266,[.5,0,0,0],buys={0:265})
        self.assertIsNotNone(a,'A already sold by slot1 cannot block its recovered B')
        self.assertEqual(a['weights'][1],.5)

    def test_monthly_preserves_live_owner_over_old_cash_reference(self):
        self.weekly[257]=True
        pol=self.initialized('EXIT21_STAGED_FRESHW')
        self.bad(253,1);self.call(pol,253,[.5,.5,0,0])
        self.bad(254,1);self.emerging(254,2);self.call(pol,254,[.5,0,0,0])
        self.call(pol,255,[.5,0,.25,0],buys={2:255})
        self.bad(256,0);self.call(pol,256,[.5,0,.25,0],buys={2:255})
        self.bad(257,0);self.emerging(257,1);self.call(pol,257,[0,0,.5,0],buys={2:256})
        self.bad(259,1);self.f['sma10'][259,1]=101.
        self.call(pol,259,[0,.25,.5,0],buys={1:258,2:256})
        self.bad(260,0);self.bad(260,2);self.call(pol,260,[0,0,.5,0])
        self.bad(261,0);self.fast_not_slow(261,1);self.call(pol,261,[0,0,0,0])
        self.bad(262,0);self.fast_not_slow(262,1)
        self.call(pol,262,[0,.25,0,0],buys={1:262})
        self.bad(265,0);self.bad(265,1)  # B still above SMA10, so its probe survives.
        a=self.call(pol,265,[0,.25,0,0],scheduled=True,buys={1:262})
        self.assertEqual(a['weights'][1],.25,'Monthly selection must retain the actual live B probe')

    def test_missing_current_close_cannot_generate_exit(self):
        pol=self.initialized();self.bad(253);self.p['observed'][253,1]=False
        self.assertIsNone(self.call(pol,253,[.5,.5,0,0]))

    def test_vol_width_is_frozen_during_loss(self):
        self.f['sigma21'][:]=.01
        pol=self.initialized('VOLTRAIL_STAGED')
        self.f['C'][253,1]=90.;self.f['peak63'][253,1]=100.;self.f['sigma21'][253,1]=.2
        a=self.call(pol,253,[.5,.5,0,0]);self.assertEqual(a['weights'][1],0)

    def test_new_blocked_slot_stays_cash_on_initial_signal(self):
        self.f['peak63'][252,1]=125.
        pol=self.policy('TRAIL15_STAGED')
        a=self.call(pol,252,[0,0,0,0],initial=True,scheduled=True)
        self.assertEqual(a['weights'][1],0.,'A new blocked slot must not rebound-enter on the same signal')

    def test_feature_breakout_excludes_current_close_and_future(self):
        self.assertIsNotNone(self.mod,'Protection state machine is not implemented')
        C=np.tile(np.arange(1.,321.)[:,None],(1,4));f={'C':C}
        a=self.mod.prepare_timing_features(self.p,f.copy())
        self.assertEqual(a['high5_prev'][250,0],250.)
        C2=C.copy();C2[251:]*=10
        b=self.mod.prepare_timing_features(self.p,{'C':C2})
        for key in ['sma10','sma21','m5','sigma21','high5_prev']:
            np.testing.assert_allclose(a[key][:251],b[key][:251],equal_nan=True)


if __name__=='__main__':unittest.main()
