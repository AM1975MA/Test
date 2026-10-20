"""Tests for frozen-score two-stage Top5 selection without any future labels."""
from __future__ import annotations
import unittest
import numpy as np
from tensor149_tcn5d.two_stage_top5 import candidate_scores,rank_percentile,staged_scores,DEPTHS,TWO_STAGE,BLENDS

class StageTop5Tests(unittest.TestCase):
    def test_shortlist_rule_fully_deterministic(self):
        rng=np.random.default_rng(59)
        for n in (110,149):
            p=rng.standard_normal(n)
            s=rng.standard_normal(n)
            for k in (20,30):
                z=staged_scores(p,s,k)
                cand=np.argsort(-p,kind="stable")[:k]
                expected=cand[np.argsort(-s[cand],kind="stable")[:5]]
                actual=np.argsort(-z,kind="stable")[:5]
                np.testing.assert_array_equal(np.sort(actual),np.sort(expected))
                self.assertTrue(np.all(z[cand]>1))
                self.assertTrue(np.all(z[np.setdiff1d(np.arange(n),cand)]<0))

    def test_same_source_scores_independent_of_future_outcome(self):
        rng=np.random.default_rng(42)
        pred={d:rng.normal(0,1,149) for d in DEPTHS}
        a=candidate_scores(pred)
        # There is no realized return/target argument to the function.
        b=candidate_scores(pred)
        for k in a:
            np.testing.assert_allclose(a[k],b[k],rtol=0,atol=0)
            self.assertTrue(np.isfinite(a[k]).all())
        self.assertEqual(len(a),len(DEPTHS)+len(TWO_STAGE)+len(BLENDS))

    def test_equal_weight_percentile_blend_invariant_under_monotonic_score_transform(self):
        p=np.linspace(-3,2,149)
        q=np.cos(np.linspace(0,15,149))
        x=.5*rank_percentile(p)+.5*rank_percentile(q)
        y=.5*rank_percentile(np.exp(p))+.5*rank_percentile(q)
        np.testing.assert_allclose(x,y,rtol=0,atol=0)

    def test_no_shortlist_outside_top5_and_require_n_greater(self):
        p=np.arange(149,dtype=float)
        q=-p
        with self.assertRaises(ValueError):
            staged_scores(p,q,4)
        with self.assertRaises(ValueError):
            staged_scores(p,q,149)
        z=staged_scores(p,q,20)
        eligible=set(np.argsort(-p)[:20])
        self.assertTrue(set(np.argsort(-z)[:5]).issubset(eligible))

if __name__=="__main__":unittest.main()
