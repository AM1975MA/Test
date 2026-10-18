"""OASIS G1 physics invariants: forecasts cannot depend on future quotes."""
import unittest
import numpy as np
import pandas as pd
from oasis_v2.g1.pairwise import features,vector_at,GROUPS,COST

class TestPairedOpportunity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dates=pd.bdate_range("2019-01-01",periods=460)
        rng=np.random.default_rng(20261018)
        a=np.exp(np.cumsum(rng.normal(.0001,.009,(460,12)),axis=0))
        cls.columns=[f"T{i:02d}" for i in range(12)]
        cls.C=pd.DataFrame(a,index=dates,columns=cls.columns)
        cls.groups={t:GROUPS[i//2] for i,t in enumerate(cls.columns)}
        cls.roster=pd.DataFrame({"ticker":cls.columns,
            "macro_category":[cls.groups[t] for t in cls.columns]})
    def test_future_prices_cannot_rewrite_pair_state(self):
        s=self.C.index[360]
        f,r=features(self.C,self.roster)
        before=vector_at(f,r,s,self.columns[0],self.columns[6],
                         self.groups,"BREATHING")
        mutated=self.C.copy()
        mutated.loc[mutated.index>s,:]*=100.
        ff,rr=features(mutated,self.roster)
        after=vector_at(ff,rr,s,self.columns[0],self.columns[6],
                        self.groups,"BREATHING")
        np.testing.assert_allclose(before[0],after[0],atol=0,rtol=0)
        np.testing.assert_allclose(before[1],after[1],atol=0,rtol=0)
        np.testing.assert_allclose(before[2],after[2],atol=0,rtol=0)
        self.assertAlmostEqual(before[3],after[3],places=14)
        self.assertAlmostEqual(before[4],after[4],places=14)
    def test_neutral_identical_pair_has_no_positive_cost_edge(self):
        s=self.C.index[360];f,r=features(self.C,self.roster)
        raw,res,hier,p,mu=vector_at(f,r,s,self.columns[0],
                                 self.columns[0],self.groups,"BREATHING")
        np.testing.assert_allclose(raw,np.zeros(3))
        np.testing.assert_allclose(res,np.zeros(len(res)))
        self.assertLess(p,.5)
        self.assertAlmostEqual(mu,-COST)
    def test_missing_candidate_data_is_not_extrapolated(self):
        broken=self.C.copy()
        s=self.C.index[360]
        broken.loc[s,self.columns[0]]=np.nan
        f,r=features(broken,self.roster)
        self.assertTrue(np.isnan(f["r21"].loc[s,self.columns[0]]))
        self.assertTrue(np.isfinite(f["r21"].loc[s,self.columns[1]]))
if __name__=="__main__":unittest.main()
