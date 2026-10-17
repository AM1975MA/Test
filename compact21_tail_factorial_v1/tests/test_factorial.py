import unittest
import numpy as np
import pandas as pd
from compact21_tail_factorial_v1.score import titanium_score
from compact21_tail_factorial_v1.replay import replay
class TestFactorial(unittest.TestCase):
    def test_titanium_score_as_is(self):
        p=pd.DataFrame({"signal_date":["2020-01-01"]*3,
            "ticker":["A","B","C"],"BASE":[.7,.3,.5]})
        z=titanium_score(p,["2020-01-01"],["A","B","C"])
        np.testing.assert_array_equal(z,[[.7,.3,.5]])
    def test_canonical_methods_restored(self):
        class Stage:
            @staticmethod
            def score_matrix(*args):return "unchanged"
            @staticmethod
            def confidence_weights(*args):return "unchanged"
        class Compare:
            stage19=Stage
            @staticmethod
            def replay_full_universe(state):
                assert Compare.stage19.score_matrix(None,None,None)!="unchanged"
                return dict(PASS=True)
        origin_score=Compare.stage19.score_matrix
        origin_weights=Compare.stage19.confidence_weights
        with self.assertRaises((TypeError,AttributeError)):
            replay(Compare,{},False)
        self.assertIs(Compare.stage19.score_matrix,origin_score)
        self.assertIs(Compare.stage19.confidence_weights,origin_weights)
    def test_full_on_does_not_change_original_functions(self):
        class Stage:
            @staticmethod
            def score_matrix(*args):return 3
            @staticmethod
            def confidence_weights(*args):return 4
        class Compare:
            stage19=Stage
            @staticmethod
            def replay_full_universe(state):
                return Compare.stage19.score_matrix(None,None,None)
        self.assertEqual(replay(Compare,{},True),3)
if __name__=="__main__":unittest.main()
