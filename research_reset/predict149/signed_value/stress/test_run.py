import unittest
import numpy as np
from research_reset.predict149.signed_value.stress.run import bootstrap,monthly_increment
class F3AdversarialStatisticsTests(unittest.TestCase):
    def test_positive_constant_differences_have_nonzero_lower_ci(self):
        r=bootstrap(np.full(64,.004),123)
        self.assertAlmostEqual(r["mean"],.004,places=14)
        np.testing.assert_allclose(r["block_bootstrap_95pct"],[.004,.004],atol=1e-12)
    def test_zero_wealth_differences_cannot_suggest_alpha(self):
        p=np.ones(64*21+1)
        a=monthly_increment(p)
        self.assertEqual(len(a),64)
        np.testing.assert_allclose(a,0)
if __name__=="__main__":unittest.main()
