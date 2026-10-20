"""Tests intentionally exercise gradients, group boundaries and label/fold maturity."""
from __future__ import annotations
import unittest
import numpy as np
import torch
import pandas as pd
from tensor149_tcn5d.listwise_losses import VARIANTS,group_loss,listnet_loss,top5_listmle_loss
from tensor149_tcn5d.listwise_run import group_by_date
from tensor149_tcn5d.run import sample_pairs,anchor_indices

class ListwiseLossTests(unittest.TestCase):
    def test_differentiable_and_permutation_invariant(self):
        torch.manual_seed(11)
        n=149
        y=torch.linspace(-1,1,n)
        r=.08*y+.003*torch.randn(n)
        p=torch.randn(n)*.2
        permutation=torch.randperm(n)
        for method in VARIANTS:
            a=p.clone().requires_grad_()
            v=group_loss(a,y,r,method)
            v.backward()
            self.assertTrue(bool(torch.isfinite(v)))
            self.assertTrue(bool(torch.isfinite(a.grad).all()))
            self.assertGreater(float(torch.linalg.vector_norm(a.grad)),1e-9)
            b=group_loss(p[permutation],y[permutation],r[permutation],method)
            self.assertAlmostEqual(float(v.detach()),float(b.detach()),places=4)

    def test_listmle_prefers_true_top_five(self):
        y=torch.linspace(-1,1,149)
        good=6*y
        bad=-6*y
        self.assertLess(float(top5_listmle_loss(good,y)),float(top5_listmle_loss(bad,y)))

    def test_listnet_prefers_proper_full_ranking(self):
        y=torch.linspace(-1,1,149)
        self.assertLess(float(listnet_loss(3.5*y,y)),float(listnet_loss(-3.5*y,y)))

    def test_group_by_date_never_crosses_dates(self):
        p=np.array([[20,0],[20,2],[20,3],[20,4],[20,5],[20,6],[20,7],[20,8],[20,9],[20,10],
                    [25,0],[25,2],[25,3],[25,4],[25,5],[25,6],[25,7],[25,8],[25,9],[25,10]],dtype=np.int32)
        g=group_by_date(p)
        self.assertEqual(len(g),2)
        self.assertEqual([x[0] for x in g],[20,25])
        self.assertEqual(g[0][1].tolist(),p[:10,1].tolist())

    def test_maturity_fence(self):
        dates=pd.bdate_range("2016-01-01",periods=600)
        anchors=np.arange(280,len(dates)-6,5,dtype=np.int32)
        avail=np.ones((len(dates),149),dtype=bool)
        y=np.ones((len(dates),149),dtype=np.float32)
        cutoff=pd.Timestamp("2017-01-01")
        train=sample_pairs(anchors,dates,avail,y,exit_before=cutoff)
        self.assertGreater(len(train),0)
        self.assertTrue(all(dates[t+6]<cutoff for t in train[:,0]))
        self.assertTrue(all(n<149 for n in train[:,1]))

if __name__=="__main__":
    unittest.main()
