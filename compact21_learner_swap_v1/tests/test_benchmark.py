import unittest
import numpy as np
import pandas as pd
from compact21_learner_swap_v1.run_benchmark import score_gap,evaluation_coverage

class DiagnosticTests(unittest.TestCase):
    def keys(self):
        return pd.DataFrame({'signal_date':[pd.Timestamp('2017-01-31')]*3,'ticker':['A','B','C']})
    def test_sufficient_margin_stays_and_swaps_only_below_bound(self):
        stable=score_gap(self.keys(),np.array([3.,1.,0.]),np.array([3.01,1.,0.]))
        self.assertEqual(stable['summary']['top1_swaps'],0)
        self.assertEqual(stable['summary']['sufficient_margin_queries'],1)
        swap=score_gap(self.keys(),np.array([1.01,1.,0.]),np.array([1.,1.01,0.]))
        self.assertEqual(swap['summary']['top1_swaps'],1)
        self.assertEqual(swap['summary']['sufficient_margin_queries'],0)
    def test_positive_affine_score_scale_does_not_change_diagnostic(self):
        p=np.array([3.,1.,0.]); q=np.array([2.9,1.1,0.])
        a=score_gap(self.keys(),p,q)['queries'][0]
        b=score_gap(self.keys(),p*12+500,q*.1-7)['queries'][0]
        for key in ('margin_a','margin_b','observed_epsilon'):
            self.assertAlmostEqual(a[key],b[key],places=12)
    def test_flat_scores_and_genuine_ties_are_explicit(self):
        z=score_gap(self.keys(),np.ones(3),np.array([1.,2.,1.]))
        self.assertTrue(z['queries'][0]['flat_a'])
        self.assertEqual(z['queries'][0]['margin_a'],0.)
        self.assertEqual(z['summary']['top1_swaps'],1)
    def test_coverage_hash_uses_keys_not_future_outcomes(self):
        z=self.keys(); z['target_rank_21']=[1,.5,0]; z['exit_date_21']=pd.Timestamp('2017-03-01')
        f={i:z.copy() for i in (1,2,3)}
        a=evaluation_coverage(f,f,z); f[3]['target_rank_21']=[0,.5,1]
        b=evaluation_coverage(f,f,z)
        self.assertEqual(a,b)
        f[3].loc[0,'ticker']='D'
        self.assertNotEqual(evaluation_coverage(f,f,z)['test_keys_sha256'],a['test_keys_sha256'])
if __name__=='__main__': unittest.main()
