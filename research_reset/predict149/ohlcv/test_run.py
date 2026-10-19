"""True OHLCV 21 bar + 21 engineered feature as-of robustness."""
import unittest
import numpy as np
import pandas as pd
from research_reset.predict149.ohlcv.run import (
    load_bars,feature_frames,fill_features,RAW,EXTRA)
from research_reset.predict149.tournament import dataset
from oasis149.canonical import load_149

class OHLCVFeatureTests(unittest.TestCase):
    def test_true_bar_and_engineered_features_cannot_see_future(self):
        table,roster,_,_,_=dataset()
        sub=table.loc[table.block==60].copy()
        s=pd.Timestamp(sub.signal.iloc[0])
        _,O,C,V,_,_,_=load_149()
        H,L=load_bars(roster)
        def build(op,hi,lo,cl,vol):
            raw,extra=feature_frames(op,hi,lo,cl,vol)
            return fill_features(sub.copy(),roster,raw,extra)
        a=build(O,H,L,C,V)
        op=O.copy();hi=H.copy();lo=L.copy();cl=C.copy();vol=V.copy()
        for data in (op,hi,lo,cl):data.loc[data.index>s,:]*=3.
        vol.loc[vol.index>s,:]*=100.
        b=build(op,hi,lo,cl,vol)
        for k in RAW+EXTRA:
            np.testing.assert_array_equal(a[k].to_numpy(float),
                                          b[k].to_numpy(float))
        self.assertEqual(len(RAW),105)
        self.assertEqual(len(EXTRA),21)
        self.assertTrue(np.isfinite(a[list(RAW)+list(EXTRA)].to_numpy(float)).all())
    def test_prior_top15_labels_not_inside_ohlcv_feature_names(self):
        self.assertFalse(any("future" in name or "top15" in name for name in RAW+EXTRA))
if __name__=="__main__":unittest.main()
