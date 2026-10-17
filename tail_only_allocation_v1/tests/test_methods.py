import unittest
import numpy as np,pandas as pd
from tail_only_allocation_v1.intervene import run_replay
from tail_only_allocation_v1.scores import score_channel
class TestTailOnly(unittest.TestCase):
    def test_pure_tail_has_no_base_score(self):
        dates=pd.date_range("2017-01-31",periods=114,freq="ME")
        tickers=[f"ETF{i:03d}" for i in range(149)]
        x=pd.MultiIndex.from_product([dates,tickers],names=["signal_date","ticker"]).to_frame(index=False)
        a=np.tile(np.arange(149),114)
        x["ET_TAIL"]=(a+1)/149
        x["XGB_TAIL"]=(150-a)/149
        cal=pd.DataFrame({"signal_date":dates})
        scores=score_channel(x,cal,tickers,"HYBRID")
        self.assertEqual(scores.shape,(114,149))
        expected=np.power(.6*(a[:149]+1)/149+.4*(150-a[:149])/149,1.1)
        np.testing.assert_allclose(scores[0],expected,rtol=0,atol=1e-15)
        # A bogus original Compact21/Titanium value is not consulted.
        x["BASE"]=np.nan
        np.testing.assert_array_equal(scores,score_channel(x,cal,tickers,"HYBRID"))
    def test_source_only_channels(self):
        dates=pd.date_range("2017-01-31",periods=114,freq="ME")
        tickers=[f"ETF{i:03d}" for i in range(149)]
        x=pd.MultiIndex.from_product([dates,tickers],names=["signal_date","ticker"]).to_frame(index=False)
        x["ET_TAIL"]=.2;x["XGB_TAIL"]=.8
        cal=pd.DataFrame({"signal_date":dates})
        self.assertAlmostEqual(float(score_channel(x,cal,tickers,"ET")[8,0]),.2**1.1)
        self.assertAlmostEqual(float(score_channel(x,cal,tickers,"XGB")[8,0]),.8**1.1)
    def test_replay_functions_restored_on_failure(self):
        class Stage:
            @staticmethod
            def score_matrix(*x):return None
            @staticmethod
            def confidence_weights(*x):return None
        class Allocation:
            @staticmethod
            def allocations_from_score(*x,**y):return None
        class Compare:
            stage19=Stage
            producer=Allocation
            @staticmethod
            def replay_full_universe(state):raise RuntimeError("synthetic abort")
        olds=(Compare.stage19.score_matrix,Compare.stage19.confidence_weights,
              Compare.producer.allocations_from_score)
        with self.assertRaisesRegex(RuntimeError,"synthetic abort"):
            run_replay(Compare,{},np.ones((114,149)),ma3_agreement=False)
        self.assertIs(Compare.stage19.score_matrix,olds[0])
        self.assertIs(Compare.stage19.confidence_weights,olds[1])
        self.assertIs(Compare.producer.allocations_from_score,olds[2])
if __name__=="__main__":unittest.main()
