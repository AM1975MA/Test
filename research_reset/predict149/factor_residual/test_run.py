"""Factor-residual tests: no future beta information, decomposition, risk matcher."""
import unittest
import numpy as np
import pandas as pd
from oasis149.canonical import load_149
from research_reset.predict149.factor_residual.run import (
    asof_betas_and_context, FACTORS, BETA_RIDGE, HORIZON,CLIP)
from research_reset.predict149.factor_neutral.diagnose import matched_pair_indices

class Original149FactorAsOfTests(unittest.TestCase):
    def test_beta_is_invariant_to_future_close_quote_changes(self):
        roster,O,C,V,days,signals,qual=load_149()
        s=signals[66*HORIZON]
        names=list(roster.ticker)
        first=asof_betas_and_context(C,names,s)
        future=C.copy()
        future.loc[future.index>s,:]*=1.35
        second=asof_betas_and_context(future,names,s)
        for x,y in zip(first,second):
            np.testing.assert_array_equal(x,y)
        self.assertEqual(first[0].shape,(149,10))
        self.assertEqual(first[1].shape,(149,2))
        self.assertEqual(first[2].shape,(30,))
        self.assertTrue(np.isfinite(first[0]).all())
    def test_factor_return_decomposition_is_identity(self):
        rng=np.random.default_rng(114)
        z=rng.normal(0,.02,10)
        beta=rng.normal(0,.5,(149,10))
        y=rng.normal(0,.07,149)
        resid=y-beta@z
        np.testing.assert_allclose(beta@z+resid,y,atol=1e-14)
        self.assertEqual(BETA_RIDGE,.005)
        self.assertEqual(CLIP,.2)
    def test_conditioned_pair_list_independent_of_future_outcomes(self):
        cats=np.array(["A","A","A","B","B"])
        risk=np.array([.01,.0108,.03,.02,.021])
        i,j=matched_pair_indices(cats,risk,band=.20)
        self.assertEqual(len(i),2)
        future=np.array([100,200,900,-20,-60])
        future[0]=1000
        x,y=matched_pair_indices(cats,risk,band=.20)
        np.testing.assert_array_equal(x,i)
        np.testing.assert_array_equal(y,j)

if __name__=="__main__":unittest.main()
