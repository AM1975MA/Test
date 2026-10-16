import unittest
import numpy as np
from linear_pca_v1.basis import fit_basis,project

class BasisChecks(unittest.TestCase):
    def test_full_rotation_preserves_scores_and_l2(self):
        rng=np.random.default_rng(2026);x=rng.normal(size=(100,8));x-=x.mean(0)
        q,ev,k=fit_basis(x)
        w=rng.normal(size=8)
        np.testing.assert_allclose(project(x,q)@(q.T@w),x@w,rtol=0,atol=1e-12)
        self.assertAlmostEqual(np.linalg.norm(q.T@w),np.linalg.norm(w),places=12)
        np.testing.assert_allclose(q.T@q,np.eye(8),atol=1e-12)

    def test_variance_threshold_reduces_redundancy(self):
        u=np.array([[1.,0.],[-1.,0.],[0.,1.],[0.,-1.]])
        x=np.c_[u[:,0]*10,u[:,1]]
        q,e,k=fit_basis(x)
        self.assertEqual(k,1)
        self.assertGreaterEqual(e[:k].sum()/e.sum(),.95)
        np.testing.assert_allclose(q.T@(x.T@x/(len(x)-1))@q,np.diag(e),atol=1e-10)

    def test_tied_boundary_keeps_whole_block(self):
        # First 19/20 equal eigenvalues reach95%; retain entire degenerate block.
        x=np.r_[np.eye(20),-np.eye(20)]
        q,e,k=fit_basis(x)
        self.assertEqual(k,20)

    def test_no_future_samples_enter_basis(self):
        rng=np.random.default_rng(1);train=rng.normal(size=(60,6));train-=train.mean(0)
        q,e,k=fit_basis(train)
        future=rng.normal(size=(10,6))*1e9
        project(future,q[:,:k])
        q2,e2,k2=fit_basis(train)
        np.testing.assert_array_equal(q,q2);np.testing.assert_array_equal(e,e2);self.assertEqual(k,k2)

if __name__=='__main__':unittest.main()
