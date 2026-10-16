"""Preflight checks; actual frozen cohorts are audited in the full Actions run."""
import unittest
from etf_trader.source_only import kernel as k
from pls_xgb_v1.core import VARIANTS,PLS_MAP

class TestExperimentContract(unittest.TestCase):
    def test_frozen_ranker(self):
        self.assertEqual(k.COMPACT_PARAMS['objective'],'rank:pairwise')
        self.assertEqual(k.COMPACT_PARAMS['n_estimators'],360)
        self.assertEqual(k.COMPACT_PARAMS['max_depth'],4)
        self.assertEqual(k.COMPACT_PARAMS['learning_rate'],.035)
        self.assertEqual(k.COMPACT_SEEDS,[101,202,303])
    def test_three_arms_only(self):
        self.assertEqual(VARIANTS,('XGB125_MATCHED','XGB_PLS12','XGB_PLS12_COHERENCE'))
        self.assertEqual(set(PLS_MAP.values()),{'SIGNAL_PLS12','SIGNAL_PLS12_COHERENCE'})
    def test_predefined_dimensions(self):
        from signal_lockin_v1.core import K
        self.assertEqual(K,12)
        self.assertEqual(len(k.F2D_FEATURES),125)

if __name__=='__main__': unittest.main()
