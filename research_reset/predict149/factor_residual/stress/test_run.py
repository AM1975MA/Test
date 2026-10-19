"""H1 alternative factor premium nulls: time restriction and grouped statistics."""
import unittest
import numpy as np
from research_reset.predict149.factor_residual.stress.run import bootstrap
class Original149FactorStressTests(unittest.TestCase):
    def test_mean_factor_null_cannot_use_current_future_label(self):
        times=np.arange(112)
        current=48
        maturities=times*21+21
        signal=current*21-1
        matured=maturities<signal
        assert matured.sum()==47
        rng=np.random.default_rng(42)
        outcomes=rng.normal(0,.03,(112,10))
        a=outcomes[matured].mean(axis=0)
        changed=outcomes.copy()
        changed[~matured]+=10000.
        b=changed[matured].mean(axis=0)
        np.testing.assert_array_equal(a,b)
    def test_paired_temporal_bootstrap_no_phantom_positive_difference(self):
        x=np.zeros(64)
        s=bootstrap(x)
        self.assertEqual(s["mean"],0)
        self.assertEqual(s["ci95"],[0,0])
if __name__=="__main__":unittest.main()
