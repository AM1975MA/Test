from __future__ import annotations
import unittest
import numpy as np
import pandas as pd
from tensor149_tcn5d.features import daily_compact,labels_next_open,eligible,FIELDS
from tensor149_tcn5d.run import TinyTCN,anchor_indices,sample_pairs
from etf_trader.source_only import kernel as k

class TensorContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(109)
        days=pd.bdate_range("2010-01-04",periods=375)
        tickers=["SPY"]+[f"TEST{j}" for j in range(11)]
        close=np.exp(np.cumsum(rng.normal(0,.012,(len(days),len(tickers))),axis=0))*100
        opening=close*np.exp(rng.normal(0,.004,close.shape))
        high=np.maximum(close,opening)*1.008
        low=np.minimum(close,opening)*.992
        vol=rng.integers(100000,1000000,close.shape).astype(float)
        cls.mats={name:pd.DataFrame(arr,index=days,columns=tickers) for name,arr in
                  (("Open",opening),("Close",close),("High",high),("Low",low),("Volume",vol))}
        cls.X=daily_compact(cls.mats)
        cls.dates=days

    def test_exact_125_monthly_formula_parity(self):
        _,frame,_,_=k.build_features(self.mats)
        assert len(FIELDS)==125
        months=k.month_end_dates(self.dates)
        for _,row in frame.iterrows():
            t=self.dates.get_loc(row.signal_date)
            j=self.mats["Open"].columns.get_loc(row.ticker)
            actual=self.X[t,j]
            expected=row[list(FIELDS)].to_numpy(float)
            np.testing.assert_allclose(actual,expected,rtol=5e-5,atol=2e-4,equal_nan=True)

    def test_past_prefix_invariant_and_next_open(self):
        earlier={name:v.iloc[:350].copy() for name,v in self.mats.items()}
        limited=daily_compact(earlier)
        np.testing.assert_allclose(self.X[349],limited[-1],rtol=1e-5,atol=2e-4,equal_nan=True)
        ret,y=labels_next_open(self.mats,5)
        O=self.mats["Open"].to_numpy()
        np.testing.assert_allclose(ret[300,0],O[306,0]/O[301,0]-1)
        self.assertFalse(np.isfinite(ret[-6:,0]).any())
        mask=eligible(self.X,O)
        self.assertTrue(mask[300,:].all())
        anchors=anchor_indices(self.dates)
        cut=pd.Timestamp(self.dates[310])
        pairs=sample_pairs(anchors,self.dates,mask,y,exit_before=cut)
        self.assertTrue(all(self.dates[t+6]<cut for t in pairs[:,0]))

    def test_neural_forward(self):
        import torch
        p=TinyTCN()
        p.eval()
        with torch.no_grad():
            actual=p(torch.zeros(4,30,125))
        self.assertEqual(tuple(actual.shape),(4,))
        self.assertTrue(torch.isfinite(actual).all())

if __name__=="__main__":
    unittest.main()
