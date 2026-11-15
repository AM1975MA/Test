import sys
import unittest
from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import cluster_selectors as cs


def fixture():
    rng = np.random.default_rng(109)
    t=340
    a=rng.normal(.001,.01,t)
    b=rng.normal(.0007,.008,t)
    c=rng.normal(.0004,.006,t)
    rr=np.column_stack([a,a,b,c,-a,rng.normal(.0003,.005,t)])
    prices=100*np.exp(np.cumsum(rr,axis=0))
    p=dict(dates=pd.bdate_range('2019-01-01',periods=t),names=np.array(['AA','AB','BA','CA','DA','EA']),
           C=prices,O=prices.copy(),observed=np.ones(prices.shape,bool),open_observed=np.ones(prices.shape,bool),benchmark=2)
    spec=importlib.util.spec_from_file_location('test_core109',ROOT/'source/src/core.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    turnover=np.full(prices.shape,200000.)
    turnover[:,1]=400000.
    return p,legacy,turnover


class ClusterTests(unittest.TestCase):
    def test_identical_exposures_share_group_and_liquid_member_represents_it(self):
        p,l,t=fixture(); f=cs.prepare_features(p,l,t)
        s=cs.build_snapshot(p,f,300)
        pair=[g for g in s['groups'] if 0 in g['members']][0]
        self.assertIn(1,pair['members'])
        self.assertEqual(pair['representative'],1)
        self.assertNotIn(4,pair['members'])

    def test_future_price_and_volume_changes_cannot_change_past_snapshot(self):
        p,l,t=fixture(); f=cs.prepare_features(p,l,t); s=cs.build_snapshot(p,f,300)
        q={k:(v.copy() if hasattr(v,'copy') else v) for k,v in p.items()}
        q['C'][301:]*=1000.; t[301:]=1e15
        g=cs.prepare_features(q,l,t); z=cs.build_snapshot(q,g,300)
        self.assertEqual(s['groups'],z['groups'])
        np.testing.assert_array_equal(s['rep_corr'],z['rep_corr'])

    def test_zero_turnover_sessions_count_in_median_and_current_observation_required(self):
        p,l,t=fixture();t[270:301,2]=0;t[301,2]=0
        p['observed'][301,3]=False
        f=cs.prepare_features(p,l,t)
        self.assertTrue(f['liquid_eligible'][300,2])
        self.assertFalse(f['liquid_eligible'][301,2])
        self.assertFalse(f['liquid_eligible'][301,3])

    def test_no_eligible_instruments_produces_cash(self):
        p,l,t=fixture();t[:]=0
        f=cs.prepare_features(p,l,t);sn={300:cs.build_snapshot(p,f,300)}
        for arm in cs.ARMS:
            if arm.startswith('CLUSTER') or arm.startswith('LIQ'):
                w,m=cs.make_policy(p,f,sn,arm)(300,np.zeros(6))
                self.assertEqual(w.sum(),0.,arm)

    def test_all_cluster_weights_long_only_and_exposures_not_duplicated(self):
        p,l,t=fixture();f=cs.prepare_features(p,l,t);sn={300:cs.build_snapshot(p,f,300)}
        for arm in cs.ARMS:
            if not arm.startswith('CLUSTER'):continue
            w,m=cs.make_policy(p,f,sn,arm)(300,np.zeros(6))
            self.assertTrue(np.isfinite(w).all(),arm)
            self.assertGreaterEqual(w.min(),0.,arm)
            self.assertLessEqual(w.sum(),1.+1e-12,arm)
            self.assertFalse(w[0]>0 and w[1]>0,arm)
            ids=np.flatnonzero(w>0)
            for i,j in zip(*np.triu_indices(len(ids),1)):
                corr=np.corrcoef(f['returns'][175:301,ids[[i,j]]].T)[0,1]
                self.assertLessEqual(corr,.85+1e-12,arm)

    def test_single_group_leaves_unfilled_slot_in_cash(self):
        p,l,t=fixture();t[:,2:]=0
        f=cs.prepare_features(p,l,t);sn={300:cs.build_snapshot(p,f,300)}
        w,_=cs.make_policy(p,f,sn,'CLUSTER_LEADERS')(300,np.zeros(6))
        self.assertEqual(w[1],.5)
        self.assertEqual(w.sum(),.5)

    def test_guard_only_exits_existing_positions_and_never_allocates_cash(self):
        p,l,t=fixture();f=cs.prepare_features(p,l,t)
        f['C'][300,1]=10.;f['sma63'][300,1]=20.;f['m21'][300,1]=-.2
        current=np.array([0.,.4,.3,0.,0.,0.])
        answer=cs.make_guard(f,'EXIT63')(300,current)
        self.assertIsNotNone(answer)
        w,meta=answer
        self.assertEqual(w[1],0.)
        self.assertEqual(w[2],.3)
        self.assertTrue((w<=current).all())
        self.assertIsNone(cs.make_guard(f,'EXIT63')(300,np.zeros(6)))

    def test_guard_drawdown_uses_trailing_close_high(self):
        p,l,t=fixture();f=cs.prepare_features(p,l,t)
        f['C'][300,1]=84.;f['peak63'][300,1]=100.
        w,_=cs.make_guard(f,'TRAIL15')(300,np.array([0.,.5,.5,0.,0.,0.]))
        self.assertEqual(w[1],0.)

    def test_fixed_grid_contains_exactly_twenty_two_distinct_arms(self):
        self.assertEqual(len(cs.ARMS),22)
        self.assertEqual(len(set(cs.ARMS)),22)

if __name__=='__main__':unittest.main()
