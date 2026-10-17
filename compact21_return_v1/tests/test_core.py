"""Synthetic correctness tests, before any real research outcomes are inspected."""
import unittest
import numpy as np,pandas as pd
from etf_trader.source_only import kernel as k
from compact21_return_v1.core import VARIANTS,prepare_targets,recipe,native_x

class TestReturnObjective(unittest.TestCase):
    def fixture(self):
        rng=np.random.default_rng(11)
        dates=pd.to_datetime(["2020-01-31"]*9+["2020-02-29"]*9)
        z=pd.DataFrame(rng.normal(size=(18,125)),columns=k.F2D_FEATURES)
        z["signal_date"]=dates
        z["ticker"]=[f"ETF{i:02d}" for i in range(9)]*2
        z["exit_date_21"]=pd.to_datetime(["2020-03-05"]*9+["2020-04-05"]*9)
        z["fwd_ret_21"]=np.array([.05,-.15,.11,.02,.01,.08,-.05,.03,.45,
                                    -.1,-.04,.03,.02,.01,.05,-.2,.07,.12])
        z["target_rank_21"]=z.groupby("signal_date").fwd_ret_21.rank(pct=True)
        return z
    def test_canonical_feature_count_and_missing(self):
        z=self.fixture();z.loc[0,k.F2D_FEATURES[0]]=np.inf
        x=native_x(z);self.assertEqual(x.shape,(18,125))
        self.assertTrue(np.isnan(x[0,0]))
        self.assertEqual(set(VARIANTS),{"RETURN_RANK_NDCG","RETURN_REG_PSEUDOHUBER"})
    def test_grade_sensitive_to_real_return_gap(self):
        z=self.fixture()
        y,g,m=prepare_targets(z,"RETURN_RANK_NDCG")
        self.assertEqual(y.dtype,np.int32);self.assertEqual(g.tolist(),[9,9])
        self.assertTrue(((y>=0)&(y<=15)).all())
        self.assertGreater(y[8],y[1])
        # ranking unchanged by positive affine transformation *within* a date.
        revised=z.copy();mask=revised.signal_date==revised.signal_date.iloc[0]
        revised.loc[mask,"fwd_ret_21"] = revised.loc[mask,"fwd_ret_21"]*2+.04
        yy,_,_=prepare_targets(revised,"RETURN_RANK_NDCG")
        np.testing.assert_array_equal(y,yy)
        self.assertEqual(recipe("RETURN_RANK_NDCG")[0]["objective"],"rank:ndcg")
    def test_regression_is_relative_clipped_and_robust(self):
        z=self.fixture()
        y,g,m=prepare_targets(z,"RETURN_REG_PSEUDOHUBER")
        self.assertEqual(y.dtype,np.float32)
        self.assertEqual(g.tolist(),[9,9])
        self.assertLessEqual(float(y.max()),.25)
        self.assertGreaterEqual(float(y.min()),-.25)
        self.assertEqual(recipe("RETURN_REG_PSEUDOHUBER")[0]["objective"],"reg:pseudohubererror")
        zz=z.copy()
        zz.loc[zz.signal_date==zz.signal_date.iloc[0],"fwd_ret_21"]+=.07
        w,_,_=prepare_targets(zz,"RETURN_REG_PSEUDOHUBER")
        np.testing.assert_allclose(y,w,atol=1e-7)
    def test_no_training_with_unknown_future_return(self):
        z=self.fixture();z.loc[0,"fwd_ret_21"]=np.nan
        with self.assertRaisesRegex(ValueError,"Nonfinite"):
            prepare_targets(z,"RETURN_REG_PSEUDOHUBER")

if __name__=="__main__": unittest.main()
