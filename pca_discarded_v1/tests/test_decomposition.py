import unittest
import numpy as np
from pca_discarded_v1.decomposition import split_weights,energy_split

class DecompositionChecks(unittest.TestCase):
    def test_weights_and_scores_reconstruct_exactly(self):
        rng=np.random.default_rng(4);q,_=np.linalg.qr(rng.normal(size=(8,8)))
        b=q[:,:3];w=rng.normal(size=8);x=rng.normal(size=(30,8))
        kept,lost=split_weights(w,b)
        np.testing.assert_allclose(kept+lost,w,atol=1e-14)
        np.testing.assert_allclose(x@kept+x@lost,x@w,atol=1e-13)
        self.assertAlmostEqual(float(kept@lost),0.,places=12)

    def test_within_between_energy_reconciles(self):
        x=np.array([[1.,2.],[2.,4.],[8.,3.],[9.,4.],[10.,5.]])
        b=np.array([[1.],[0.]])
        d=energy_split(x,[np.arange(2),np.arange(2,5)],b)
        self.assertAlmostEqual(d['total'],d['within']+d['between'],places=12)
        self.assertAlmostEqual(d['retained_total'],d['retained_within']+d['retained_between'],places=12)

if __name__=='__main__':unittest.main()
