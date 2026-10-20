"""Contract for TRUE regularized differentiable Spearman, fixed pilot settings."""
from __future__ import annotations
import unittest
import numpy as np
import torch
from tensor149_tcn5d.softspearman_losses import (
 VARIANTS,softspearman_loss,RANK_REGULARIZATION,TOP5_TRUTH_WEIGHT)

class SoftSpearmanTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(492)
        torch.set_num_threads(2)
        self.y=torch.linspace(-1,1,149)
        self.r=torch.linspace(-.06,.09,149)

    def test_finite_strong_gradient(self):
        for variant in VARIANTS:
            s=(self.y+torch.randn(149)*.6).detach().clone().requires_grad_(True)
            v=softspearman_loss(s,self.y,self.r,variant)
            v.backward()
            self.assertTrue(bool(torch.isfinite(s.grad).all()))
            self.assertGreater(float(s.grad.norm()),1e-5)
            self.assertTrue(np.isfinite(float(v.detach())))

    def test_known_order_and_inverse(self):
        forward=softspearman_loss(self.y,self.y,self.r,"SOFTSPEARMAN")
        reverse=softspearman_loss(-self.y,self.y,self.r,"SOFTSPEARMAN")
        self.assertLess(float(forward),.2)
        self.assertGreater(float(reverse),1.8)

    def test_query_permutation_invariance(self):
        p=torch.randperm(149)
        for v in VARIANTS:
            s=torch.randn(149)
            one=softspearman_loss(s,self.y,self.r,v)
            two=softspearman_loss(s[p],self.y[p],self.r[p],v)
            self.assertAlmostEqual(float(one),float(two),places=4)

    def test_translation_scale_invariance_of_pure_spearman(self):
        s=torch.randn(149)
        a=softspearman_loss(s,self.y,self.r,"SOFTSPEARMAN")
        b=softspearman_loss(4*s+2,self.y,self.r,"SOFTSPEARMAN")
        self.assertAlmostEqual(float(a),float(b),places=4)

    def test_true_target_top5_weight(self):
        self.assertEqual(TOP5_TRUTH_WEIGHT,5.)
        pred=self.y.clone()
        pred[-5:]=-pred[-5:]*3
        a=softspearman_loss(pred,self.y,self.r,"SOFTSPEARMAN")
        b=softspearman_loss(pred,self.y,self.r,"SOFTSPEARMAN_TOP5")
        self.assertGreater(float(b),float(a))

    def test_hybrid_relative_label_only(self):
        s=torch.randn(149)
        base=softspearman_loss(s,self.y,self.r,"SOFTSPEARMAN_RETURN")
        changed=softspearman_loss(s,self.y,self.r.flip(0),"SOFTSPEARMAN_RETURN")
        self.assertNotAlmostEqual(float(base),float(changed),places=5)

if __name__=="__main__":unittest.main()
