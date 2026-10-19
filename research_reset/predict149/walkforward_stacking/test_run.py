"""No-lookahead audit of F3/H1 walkforward learned stacking."""
import unittest
import numpy as np
import pandas as pd
from research_reset.predict149.complementarity.run import from_archive,monthly_weights
from research_reset.predict149.walkforward_stacking.run import (
    prepare_features,training_rows,DIMS,ARM_NAMES,TRAIN_MIN_ANCHORS)

class TestFrozenF3H1MetaFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame,cls.old,cls.roster,_,cls.C,cls.days,cls.signals,cls.ids,cls.chosen=from_archive()
    def test_149_inputs_are_strictly_asof_and_target_mutations_cannot_change_them(self):
        frame=prepare_features(self.frame)
        self.assertEqual(len(DIMS),12)
        self.assertEqual(len(frame),64*149)
        k=31
        b=self.ids[k]
        original=frame.loc[frame.block==b,list(DIMS)].to_numpy(float)
        changed=self.frame.copy()
        loc=changed.block>=b
        changed.loc[loc,"future_excess"]*=10000.
        changed.loc[loc,"future_log"]*=10000.
        again=prepare_features(changed).loc[lambda d:d.block==b,list(DIMS)].to_numpy(float)
        np.testing.assert_array_equal(original,again)
    def test_embargo_ends_at_k_minus_two_and_train_signals_are_prequential(self):
        allrows=prepare_features(self.frame)
        for k in (0,1,12,13,30,63):
            old,next_=training_rows(allrows,k,self.ids)
            self.assertEqual(old.block.nunique(),max(0,k-1))
            self.assertEqual(len(next_),149)
            if len(old):
                self.assertTrue((pd.to_datetime(old.maturity)<
                    pd.Timestamp(next_.signal.iloc[0])).all())
                self.assertEqual(max(old.block),self.ids[k-2])
    def test_exact_shared_portfolio_weights_and_frozen_arms(self):
        a=["A","B","C","D","E"]
        b=["B","C","F","G","H"]
        w=monthly_weights([("A",.75,a),("B",.25,b)])
        self.assertAlmostEqual(w["B"],.20,places=12)
        self.assertAlmostEqual(w["A"],.15,places=12)
        self.assertAlmostEqual(w["F"],.05,places=12)
        self.assertAlmostEqual(sum(w.values()),1.,places=12)
        self.assertEqual(TRAIN_MIN_ANCHORS,12)
        self.assertEqual(len(ARM_NAMES),9)
if __name__=="__main__":unittest.main()
