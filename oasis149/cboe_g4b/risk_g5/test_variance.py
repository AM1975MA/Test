"""Forecast proper as-of vs future realized information separation and class mapping."""
import unittest
import numpy as np
import pandas as pd
from oasis149.cboe_g4b.risk_g5.variance import observed_and_base,implied_by_class,qlike,BONDS

class G5VarianceTests(unittest.TestCase):
    def test_only_realized_label_changes_when_future_quotes_change(self):
        dates=pd.bdate_range("2018-01-01",periods=300)
        rng=np.random.default_rng(77)
        xx=np.exp(np.cumsum(rng.normal(0,.008,len(dates))))
        x=pd.DataFrame({"X":xx},index=dates)
        signal=dates[250];entry=dates[251];last=dates[272]
        a=observed_and_base(x,signal,entry,last,"X")
        changed=x.copy()
        # Positive deterministic changing future return path, never as-of.
        changed.loc[changed.index>=entry,"X"]*=np.linspace(1,1.7,
            len(changed.loc[changed.index>=entry]))
        b=observed_and_base(changed,signal,entry,last,"X")
        self.assertAlmostEqual(a[1],b[1],places=15)
        self.assertAlmostEqual(a[2],b[2],places=15)
        self.assertNotAlmostEqual(a[0],b[0],places=7)
    def test_bond_group_has_no_fabricated_cboe_proxy(self):
        values=np.log1p([20.,100.,40.,30.,35.])
        self.assertIsNone(implied_by_class(BONDS,values))
        for g in ("C01_US_BROAD_STYLE","C04_EMERGING","C06_REAL_ASSETS"):
            self.assertGreater(implied_by_class(g,values),0)
    def test_qlike_is_zero_when_variance_forecast_is_correct(self):
        np.testing.assert_allclose(qlike([.1,.5,3.],[.1,.5,3.]),[0,0,0],atol=1e-14)
if __name__=="__main__":unittest.main()
