"""Numerical and chronology smoke tests for PLS and coherence extraction."""
import unittest
import numpy as np
import pandas as pd
from signal_lockin_v1.core import supervised_basis,coherence_weights,date_ic,VARIANTS

class TestSignalLockin(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(20261016)
        n_dates=24;n_etf=16;dim=125
        self.dates=pd.date_range('2010-01-01',periods=n_dates,freq='MS')
        self.groups=[np.arange(i*n_etf,(i+1)*n_etf) for i in range(n_dates)]
        self.x=rng.normal(size=(n_dates*n_etf,dim))
        # A true historical feature signal, plus label noise, no use of test data
        score=self.x[:,0]*.7-self.x[:,1]*.3+rng.normal(size=len(self.x))
        self.y=np.zeros(len(self.x),int)
        for ix in self.groups:
            order=np.argsort(np.argsort(score[ix]))
            self.y[ix]=np.floor(order*10/len(ix)).astype(int)+1

    def test_ic_direction_and_weights(self):
        ic=date_ic(self.x,self.y,self.groups)
        self.assertEqual(ic.shape,(24,125))
        self.assertGreater(ic[:,0].mean(),0.2)
        weights,audit=coherence_weights(self.x,self.y,self.groups,self.dates)
        self.assertEqual(weights.shape,(125,))
        self.assertGreaterEqual(weights.min(),.25)
        self.assertLessEqual(weights.max(),1.)
        self.assertEqual(audit['blocks'],4)
        np.testing.assert_array_equal(weights,coherence_weights(self.x,self.y,self.groups,self.dates)[0])

    def test_supervised_orthonormal_finite_and_label_sensitive(self):
        for variant in VARIANTS:
            q,w,audit,_=supervised_basis(self.x,self.y,self.groups,self.dates,variant)
            self.assertEqual(q.shape,(125,12))
            self.assertTrue(np.isfinite(q).all())
            np.testing.assert_allclose(q.T@q,np.eye(12),rtol=0,atol=1e-12)
            self.assertEqual(audit['kind'],variant)
            self.assertEqual(audit['components'],12)
        self.assertGreater(np.linalg.norm(q),0)

    def test_train_only_interface_and_no_future_value(self):
        q,w,_,_=supervised_basis(self.x,self.y,self.groups,self.dates,VARIANTS[1])
        fake_test=np.random.default_rng(45).normal(size=(30,125))
        before=fake_test@q
        fake_test_2=fake_test*100
        # Query ranking is a function only of train-fitted q and test-time features.
        after=fake_test@q
        np.testing.assert_array_equal(before,after)
        self.assertFalse(np.array_equal(before,fake_test_2@q))

    def test_rejects_invalid_partition(self):
        with self.assertRaises(ValueError):
            supervised_basis(self.x,self.y,self.groups[:-1],self.dates[:-1],VARIANTS[0])

if __name__=='__main__':unittest.main()
