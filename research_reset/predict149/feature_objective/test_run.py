"""T149-D tests for as-of raw return window and explicit ranking objective."""
import unittest
import numpy as np
import pandas as pd
from lightgbm import LGBMRanker
from research_reset.predict149.feature_objective.run import (
    expand_features,FEATURE_RAW,FEATURE_CONTEXT,RAW,CONTEXT)
from research_reset.predict149.tournament import dataset
from oasis149.canonical import load_149

class TickerFeaturesTests(unittest.TestCase):
    def test_149_RAW_and_context_are_unaffected_by_future_price_mutation(self):
        frame,roster,dates,op,names=dataset()
        source=frame.loc[frame.block==60].copy()
        signal=pd.Timestamp(source.signal.iloc[0])
        _,_,closes,_,_,_,_=load_149()
        initial=expand_features(source.copy(),closes,roster)
        modified=closes.copy()
        modified.loc[modified.index>signal,:]*=1000.
        changed=expand_features(source.copy(),modified,roster)
        self.assertEqual(len(RAW),63)
        self.assertEqual(len(FEATURE_RAW),69)
        self.assertEqual(len(CONTEXT),15)
        self.assertEqual(len(FEATURE_CONTEXT),40)
        for col in FEATURE_RAW+FEATURE_CONTEXT:
            np.testing.assert_array_equal(initial[col].to_numpy(float),
                                          changed[col].to_numpy(float))
        self.assertEqual(int(initial.top15.sum()),15)
        self.assertEqual(int(initial.bottom15.sum()),15)
        self.assertEqual(int((initial.graded_relevance==3).sum()),5)
    def test_rank_model_respects_exact_149_query_groups(self):
        rng=np.random.default_rng(33)
        X=rng.normal(size=(149*4,4))
        y=np.tile(np.r_[np.full(5,3),np.full(10,2),
                         np.full(15,1),np.zeros(119)],4).astype(int)
        model=LGBMRanker(objective="lambdarank",n_estimators=3,
            num_leaves=4,min_child_samples=15,label_gain=[0,1,3,7],
            n_jobs=1,verbosity=-1,random_state=33)
        model.fit(X,y,group=np.array([149]*4,dtype=int))
        p=model.predict(X[:149])
        self.assertEqual(len(p),149)
        self.assertTrue(np.isfinite(p).all())

if __name__=="__main__":unittest.main()
