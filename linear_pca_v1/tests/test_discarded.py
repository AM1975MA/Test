import unittest
import numpy as np
from linear_pca_v1.basis import select_basis,fit_basis

class DiscardedTest(unittest.TestCase):
    def test_threshold_sensitivity(self):
        x=np.diag(np.sqrt([70.,20.,7.,2.,1.]))
        self.assertEqual(fit_basis(x,threshold=.90)[2],2)
        self.assertEqual(fit_basis(x,threshold=.95)[2],3)
        self.assertEqual(fit_basis(x,threshold=.99)[2],4)

    def test_complementary_subspaces(self):
        rng=np.random.default_rng(123)
        x=rng.normal(size=(300,10))*np.geomspace(10,.01,10)
        a,ev,k=select_basis(x,False)
        b,ev2,k2=select_basis(x,True)
        self.assertEqual(k,k2)
        np.testing.assert_array_equal(ev,ev2)
        self.assertEqual(a.shape[1]+b.shape[1],10)
        np.testing.assert_allclose(a@a.T+b@b.T,np.eye(10),atol=1e-12)
        np.testing.assert_allclose(a.T@b,0,atol=1e-12)

if __name__=='__main__':unittest.main()
