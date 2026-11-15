import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import dedup_selectors as ds
import cluster_selectors as cs
from test_cluster_selectors import fixture

class DedupTests(unittest.TestCase):
    def test_only_duplicate_second_leader_is_replaced(self):
        p,l,t=fixture();f=cs.prepare_features(p,l,t)
        f['m252'][300]=[1.,.9,.8,.7,.6,.5]
        s={300:cs.build_snapshot(p,f,300)}
        w,m=ds.make_policy(p,f,s,'DEDUP_LEADERS')(300,np.zeros(6))
        self.assertEqual(m['selected_indices'],[0,2])
        np.testing.assert_array_equal(w,[.5,0.,.5,0.,0.,0.])

    def test_peer_filter_keeps_individual_rank_and_does_not_choose_liquid_rep(self):
        p,l,t=fixture();f=cs.prepare_features(p,l,t)
        f['m252'][300]=[1.,.9,.8,.7,.6,.5]
        s={300:cs.build_snapshot(p,f,300)}
        w,m=ds.make_policy(p,f,s,'DEDUP_DUAL_PEERS2')(300,np.zeros(6))
        self.assertEqual(m['selected_indices'],[0])
        self.assertEqual(w[0],.5)
        self.assertEqual(w[1],0.)

    def test_grid_and_all_targets_are_valid(self):
        p,l,t=fixture();f=cs.prepare_features(p,l,t);s={300:cs.build_snapshot(p,f,300)}
        self.assertEqual(len(ds.ARMS),10)
        for arm in ds.ARMS:
            w,m=ds.make_policy(p,f,s,arm)(300,np.zeros(6))
            self.assertTrue(np.isfinite(w).all(),arm)
            self.assertGreaterEqual(w.min(),0.,arm)
            self.assertLessEqual(w.sum(),1.+1e-12,arm)

if __name__=='__main__':unittest.main()
