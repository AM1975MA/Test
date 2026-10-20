"""Contract tests for R1/R2 strictly causal price/sector relations and train maturity."""
from __future__ import annotations
import tempfile,unittest
from pathlib import Path
import numpy as np
import pandas as pd
from tensor149_tcn5d.relational_features import make_r1r2
from tensor149_tcn5d.daily_ablation import prepare,signal_train_dates,training_pairs
from tensor149_tcn5d.run import anchor_indices

class DailyAblationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        g=np.random.default_rng(2126)
        days=pd.bdate_range("2013-01-02",periods=320)
        tickers=["SPY"]+[f"ETF{j}" for j in range(148)]
        rr=g.normal(0,.009,(len(days),len(tickers)))
        close=np.exp(np.cumsum(rr,axis=0))*100
        cls.mats={"Close":pd.DataFrame(close,index=days,columns=tickers)}
        cls.universe=pd.DataFrame(dict(ticker=tickers,macro_category=[
            f"CAT{i%6}" for i in range(len(tickers))]))
        cls.tmp=tempfile.TemporaryDirectory()
        cls.path=Path(cls.tmp.name)/"universe.csv";cls.universe.to_csv(cls.path,index=False)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_r1r2_prefix_causality_exact(self):
        a,n1,b,n2=make_r1r2(self.mats,self.path)
        self.assertEqual(a.shape,(320,149,14))
        self.assertEqual(b.shape,(320,149,20))
        past={"Close":self.mats["Close"].iloc[:251]}
        c,p1,d,p2=make_r1r2(past,self.path)
        self.assertEqual(n1,p1)
        self.assertEqual(n2,p2)
        np.testing.assert_allclose(a[:251],c,equal_nan=True,atol=1e-7)
        np.testing.assert_allclose(b[:251],d,equal_nan=True,atol=1e-7)
        self.assertTrue(np.isfinite(a[280]).any())
        self.assertTrue(np.isfinite(b[280]).any())

    def test_self_exclusion_peer_vs_universe(self):
        a,n1,b,n2=make_r1r2(self.mats,self.path)
        rank_idx=n1.index("r1_peer_pct_21")
        for t in (200,250,300):
            v=a[t,:,rank_idx]
            self.assertTrue(np.all((v[np.isfinite(v)]>=0)&(v[np.isfinite(v)]<=1)))
        corr_idx=n2.index("r2_corr_universe_63")
        z=b[310,:,corr_idx]
        self.assertTrue(bool(np.isfinite(z).all()))
        self.assertTrue(bool(np.all((z>=-1.00001)&(z<=1.00001))))

    def test_daily_train_fivefold_density_and_frozen_eval_anchor(self):
        dates=self.mats["Close"].index
        daily=signal_train_dates(dates,1)
        weekly=signal_train_dates(dates,5)
        self.assertGreater(len(daily),len(weekly)*4)
        self.assertTrue(np.array_equal(weekly,anchor_indices(dates)))
        self.assertTrue(set(weekly).issubset(set(daily)))

    def test_dims_model_base_r1_r1r2(self):
        x=np.zeros((4,149,125),np.float32)
        r1=np.zeros((4,149,14),np.float32)
        r2=np.zeros((4,149,20),np.float32)
        for v,n in [("B_DAILY_BASE",125),("C_DAILY_R1",139),
                    ("D_DAILY_R1R2",159),("E_XGB_R1R2",159)]:
            a,fields=prepare(x,r1,r2,v)
            self.assertEqual(a.shape,(4,149,n))
            self.assertEqual(len(fields),n)

if __name__=="__main__":unittest.main()
