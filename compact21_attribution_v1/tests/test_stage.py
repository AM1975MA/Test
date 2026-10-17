"""Regression tests for the exact unchanged V2 stage19 score algebra."""
import unittest
import numpy as np,pandas as pd
from compact21_attribution_v1.analyze import preallocation,numeric_frame,check_exact_keys

class TestStageAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dates=pd.date_range("2017-01-31",periods=114,freq="ME")
        tickers=[f"T{i:03d}" for i in range(149)]
        d=pd.MultiIndex.from_product([dates,tickers],names=["signal_date","ticker"]).to_frame(index=False)
        i=np.tile(np.arange(149),114);t=np.repeat(np.arange(114),149)
        d["BASE"]=((i*.017+t*.013)%149)/148
        d["ET_TAIL"]=((i*.011+t*.009)%149)/148
        d["XGB_TAIL"]=((i*.023+t*.031)%149)/148
        d["TAIL_HYBRID"]=(.6*d.ET_TAIL+.4*d.XGB_TAIL)
        cls.frame=d
    def test_titanium_only_changes_stage19_score_with_fixed_coefficient(self):
        b=self.frame.copy();c=b.copy()
        c["BASE"]+=.02
        u=preallocation(b);v=preallocation(c)
        check_exact_keys(u,v)
        np.testing.assert_allclose(
            v.score.to_numpy()-u.score.to_numpy(),
            .475*(c.BASE.to_numpy()-b.BASE.to_numpy()),
            atol=1e-12,rtol=0)
    def test_initial_months_tail_lags_replicate_initial_month(self):
        a=self.frame.copy()
        result=preallocation(a)
        group=a[a.signal_date==a.signal_date.iloc[0]]
        p=result[result.signal_date==result.signal_date.iloc[0]]
        t=.6*group.ET_TAIL.to_numpy()+.4*group.XGB_TAIL.to_numpy()
        expected=.475*group.BASE.to_numpy()+.525*np.clip(t,0,1)**1.10
        np.testing.assert_allclose(p.score.to_numpy(),expected,rtol=0,atol=1e-12)
    def test_duplicate_forecast_keys_rejected(self):
        bad=pd.concat([self.frame,self.frame.iloc[:1]],ignore_index=True)
        with self.assertRaisesRegex(ValueError,"duplicate"):
            numeric_frame(bad,"BASE")
    def test_incomplete_original149_rejected(self):
        with self.assertRaisesRegex(ValueError,"Unequal|Original149"):
            preallocation(self.frame.iloc[:-1])
    def test_nonfinite_scores_rejected(self):
        z=self.frame.copy();z.loc[0,"BASE"]=np.nan
        with self.assertRaisesRegex(ValueError,"Missing preallocation cohort|nonfinite"):
            preallocation(z)

if __name__=="__main__":unittest.main()
