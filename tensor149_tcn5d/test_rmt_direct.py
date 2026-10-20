"""Independent tests of as-of 126 daily returns RMT per ETF; never future."""
from __future__ import annotations
import unittest
import numpy as np
import pandas as pd
from tensor149_tcn5d.rmt_direct_features import build,GLOBAL,ETF,CONTROL
from tensor149_tcn5d.rmt_direct_run import prepare_variant,EXTRAS,VARIANTS

class RmtDirectFeatureQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(26023)
        dates=pd.bdate_range("2019-01-02",periods=180)
        tickers=["SPY"]+[f"ETF{i:03d}" for i in range(148)]
        common=rng.normal(0,.01,(180,1))
        r=.6*common+.6*rng.normal(0,.009,(180,149))
        prices=100*np.exp(np.cumsum(r,axis=0))
        cls.frame=pd.DataFrame(prices,index=dates,columns=tickers)

    def test_prefix_invariant_under_future_truncation_and_mutation(self):
        g,e,c=build(self.frame)
        gp,ep,cp=build(self.frame.iloc[:157])
        for x,y in ((g,gp),(e,ep),(c,cp)):
            np.testing.assert_allclose(x[:157],y,rtol=0,atol=1e-7,equal_nan=True)
        altered=self.frame.copy()
        altered.iloc[157:,:]*=8
        gm,em,cm=build(altered)
        for x,y in ((g,gm),(e,em),(c,cm)):
            np.testing.assert_allclose(x[:157],y[:157],rtol=0,atol=1e-7,equal_nan=True)
        self.assertTrue(np.isfinite(g[150,0]))
        self.assertTrue(np.isfinite(e[150,:,0]).all())

    def test_spectral_ranges_and_idio(self):
        g,e,c=build(self.frame.iloc[:133])
        self.assertEqual(g.shape,(133,5))
        self.assertEqual(e.shape,(133,149,5))
        self.assertEqual(c.shape,(133,149,5))
        self.assertEqual(len(GLOBAL),5)
        self.assertEqual(len(ETF),5)
        self.assertEqual(len(CONTROL),5)
        self.assertTrue(np.all((g[130,:3]>=0)&(g[130,:3]<=1)))
        self.assertTrue(np.all((e[130,:,2]>=0)&(e[130,:,2]<=1)))
        self.assertTrue(np.all((e[130,:,1]>=0)&(e[130,:,1]<=1)))
        self.assertTrue(np.allclose(c[130,:,0],c[130,0,0],atol=1e-6))
        self.assertAlmostEqual(c[130,0,2],1,places=5)

    def test_shapes_when_added_to_original_125_features(self):
        base=np.zeros((4,149,125),dtype=np.float32)
        g=np.zeros((4,5),dtype=np.float32)
        e=np.zeros((4,149,5),dtype=np.float32)
        for v in VARIANTS:
            x=prepare_variant(base,g,e,e,v)
            self.assertEqual(x.shape,(4,149,125+EXTRAS[v]))
            self.assertTrue(np.isfinite(x).all())

if __name__=="__main__":unittest.main()
