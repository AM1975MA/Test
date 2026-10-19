import unittest
import numpy as np
from research_reset.predict149.factor_neutral.diagnose import (
    matched_pair_indices,concordance,bootstrap_month)

class MatchedConditionalSkillTests(unittest.TestCase):
    def test_only_asof_group_and_vol_determine_pairs(self):
        g=np.array(["EQ","EQ","EQ","BOND"])
        vol=np.array([.010,.011,.030,.010])
        a,b=matched_pair_indices(g,vol)
        self.assertEqual(set(zip(a.tolist(),b.tolist())),{(0,1)})
        # Changing future returns cannot affect pair selection
        future1=np.array([.1,-.2,.4,.9])
        future2=np.array([-.9,.9,-.1,.4])
        self.assertNotEqual(concordance([3,2,9,1],future1,a,b),
                            concordance([3,2,9,1],future2,a,b))
        x,y=matched_pair_indices(g,vol)
        np.testing.assert_array_equal(a,x)
        np.testing.assert_array_equal(b,y)
    def test_symmetric_correctness_and_ties(self):
        i=np.array([0]);j=np.array([1])
        self.assertEqual(concordance([2,1],[.5,.1],i,j),1.)
        self.assertEqual(concordance([2,1],[.1,.5],i,j),0.)
        self.assertEqual(concordance([1,1],[.1,.5],i,j),.5)
    def test_identically_random_skill_ci_not_fabricated(self):
        x=np.full(64,.5)
        r=bootstrap_month(x)
        self.assertEqual(r["mean"],.5)
        np.testing.assert_allclose(r["ci95"],[.5,.5],atol=1e-12)
if __name__=="__main__":unittest.main()
