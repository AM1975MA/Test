import unittest
import pandas as pd
import numpy as np

from compact21_xgb_ridge_hybrid_v1.evaluate import blend_percentiles


class FrozenBlendTests(unittest.TestCase):
    @staticmethod
    def example(base=(3.0,2.0,1.0),ridge=(1.0,2.0,3.0)):
        f=pd.DataFrame({"signal_date":pd.to_datetime(["2020-01-31"]*3),
          "ticker":["AAA","BBB","CCC"],"vintage":[1]*3,
          "target_rank_21":[.9,.5,.1],
          "exit_date_21":pd.to_datetime(["2020-03-02"]*3),
          "pred":list(base)})
        g=f.copy(deep=True)
        g["pred"]=list(ridge)
        return f,g

    def test_fixed_numerical_blend_and_no_mutation(self):
        f,g=self.example()
        old=f.copy(deep=True)
        new=blend_percentiles(f,g)
        self.assertEqual(new.pred.to_list(), [.75*(1.)+.25*(1/3), .75*(2/3)+.25*(2/3),
                                                 .75*(1/3)+.25*(1.)])
        pd.testing.assert_frame_equal(f,old,check_exact=True)

    def test_tie_average_percentile(self):
        f,g=self.example(base=(1.,1.,0.),ridge=(2.,1.,0.))
        x=blend_percentiles(f,g)
        self.assertAlmostEqual(x.pred.iloc[0], .75*(5/6)+.25)
        self.assertAlmostEqual(x.pred.iloc[1], .75*(5/6)+.25*(2/3))

    def test_refuses_changed_target(self):
        f,g=self.example()
        g.loc[0,"target_rank_21"]=.1
        with self.assertRaises(AssertionError):
            blend_percentiles(f,g)

    def test_refuses_unmatched_keys(self):
        f,g=self.example()
        g.loc[1,"ticker"]="YYY"
        with self.assertRaises(AssertionError):
            blend_percentiles(f,g)

    def test_refuses_nonfinite_and_missing(self):
        f,g=self.example()
        g.loc[0,"pred"]=np.nan
        with self.assertRaises(ValueError):
            blend_percentiles(f,g)
        g=f.iloc[:2]
        with self.assertRaises(ValueError):
            blend_percentiles(f,g)

if __name__=="__main__":
    unittest.main()
