"""Unit checks for the two missing factorial cells."""
import unittest
import numpy as np
import pandas as pd
from etf_trader.source_only import kernel as k
from xgb125_factorial_v1.core import NEW_VARIANTS,ALL_VARIANTS,select_matrices

class TestFactorial(unittest.TestCase):
    def test_frozen_four_cell_design(self):
        self.assertEqual(NEW_VARIANTS,("XGB_FULL_PREP","XGB_REDUCED_NATIVE"))
        self.assertEqual(ALL_VARIANTS,("BASE","XGB_FULL_PREP","XGB_REDUCED_NATIVE","XGB125_MATCHED"))
        self.assertEqual(len(k.F2D_FEATURES),125)
        self.assertEqual(k.COMPACT_SEEDS,[101,202,303])
        self.assertEqual(k.COMPACT_PARAMS["n_estimators"],360)
        self.assertEqual(k.COMPACT_PARAMS["objective"],"rank:pairwise")
    def test_missing_and_training_partition(self):
        feature=list(k.F2D_FEATURES)
        rng=np.random.default_rng(7)
        base=pd.DataFrame(rng.normal(size=(12,125)),columns=feature)
        base.loc[2,feature[0]]=np.nan
        base.loc[4,feature[1]]=np.inf
        sub=base.iloc[:8].copy()
        tests=[base.iloc[8:].copy()]
        fitted,z,te,state,policy=select_matrices(base,sub,tests,"XGB_FULL_PREP")
        self.assertEqual(len(fitted),12)
        self.assertEqual(policy["support"],"full")
        self.assertTrue(np.isfinite(z).all())
        self.assertTrue(np.isfinite(te[0]).all())
        self.assertEqual(set(state),{"median","mean","scale"})
        fitted,z,te,state,policy=select_matrices(base,sub,tests,"XGB_REDUCED_NATIVE")
        self.assertEqual(len(fitted),8)
        self.assertEqual(policy["support"],"reduced")
        self.assertTrue(np.isnan(z[2,0]))
        self.assertTrue(np.isnan(z[4,1]))
        self.assertEqual(state,{})
        with self.assertRaises(ValueError):
            select_matrices(base,sub,tests,"BASE")
if __name__=="__main__":unittest.main()
