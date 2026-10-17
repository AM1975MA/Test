"""Synthetic causal-contract tests for the OOS-only economic calibration."""
import unittest
import numpy as np,pandas as pd
from compact21_econ_layer_v1.core import VARIANT,AUX_FEATURES,learn,predict,prepare,MIN_DATES

class TestEconomicLayer(unittest.TestCase):
    def panel(self,n_dates=24):
        rows=[]
        for month in range(n_dates):
            date=pd.Timestamp("2017-01-31")+pd.DateOffset(months=month)
            for i in range(9):
                rec=dict(signal_date=date,ticker=f"ETF{i:02d}",
                    exit_date_21=date+pd.Timedelta(days=28),
                    fwd_ret_21=.01*i-.02+(month%3)*.005,
                    _base_pred=float(i)*.05+(month%4)*.01)
                for j,col in enumerate(AUX_FEATURES):rec[col]=(i+j+month%5)/20.
                rows.append(rec)
        return pd.DataFrame(rows).sort_values(["signal_date","ticker"]).reset_index(drop=True)
    def test_prepared_columns(self):
        x,r=prepare(self.panel(2))
        self.assertEqual(x.shape,(18,9))
        self.assertTrue(np.isfinite(x).all())
        self.assertLessEqual(float(r.max()),1.)
    def test_early_year_falls_back_byte_exact(self):
        f=self.panel(12);model,a=learn(f,"2019-01-01")
        self.assertIsNone(model);self.assertEqual(a["training_dates"],12)
        np.testing.assert_array_equal(predict(f,model),f._base_pred.to_numpy(float))
    def test_oos_ridge_and_determinism(self):
        f=self.panel(24)
        m,a=learn(f,"2020-01-01")
        self.assertIsNotNone(m);self.assertEqual(a["training_dates"],24)
        p=predict(f,m)
        q=predict(f,learn(f,"2020-01-01")[0])
        self.assertTrue(np.isfinite(p).all())
        np.testing.assert_array_equal(p,q)
        self.assertTrue(((p>=0)&(p<=1)).all())
    def test_future_label_rejected(self):
        f=self.panel(24);f.loc[0,"exit_date_21"]=pd.Timestamp("2025-03-01")
        with self.assertRaisesRegex(ValueError,"not-yet-mature"):
            learn(f,"2020-01-01")
    def test_target_not_used_during_prediction(self):
        f=self.panel(24);m,_=learn(f,"2020-01-01")
        p=predict(f.drop(columns=["fwd_ret_21","exit_date_21"]),m)
        np.testing.assert_array_equal(p,predict(f,m))
if __name__=="__main__":unittest.main()
