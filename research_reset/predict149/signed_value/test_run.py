"""Freeze signed profit forecasts separately from 'volatile enough for top15'."""
import unittest
import numpy as np
import pandas as pd
from research_reset.predict149.signed_value.run import enrich,parameters,pinball,prob_score
from research_reset.predict149.tournament import precompute
class SignedForecastTests(unittest.TestCase):
    def test_signed_events_and_tail_magnitudes_are_distinct(self):
        frame=pd.DataFrame(dict(block=[0]*149,
            future_excess=np.r_[np.full(40,.07),np.full(40,-.08),
                                 np.full(69,0.)],
            future_log=np.arange(149,dtype=float),
            signal=["2021-01-01"]*149))
        frame["top15"]=0
        f=enrich(frame)
        self.assertEqual(int(f.event_up.sum()),40)
        self.assertEqual(int(f.event_down.sum()),40)
        self.assertEqual(int(f.signed_pos.sum()),40)
        self.assertTrue((f.conditional_positive>=0).all())
        self.assertTrue((f.conditional_negative>=0).all())
        self.assertEqual(int(f.bottom15.sum()),15)
    def test_19_price_features_and_categories_are_asof_only(self):
        rng=np.random.default_rng(18)
        ds=pd.bdate_range("2018-01-01",periods=300)
        names=["SPY","AAA","BBB","CCC"]
        frame=pd.DataFrame(np.exp(np.cumsum(
            rng.normal(0,.01,(300,4)),axis=0)),
            index=ds,columns=names)
        groups=pd.DataFrame({"ticker":names,
            "macro_category":["C1","C1","C2","C2"]})
        when=ds[230]
        a,_=precompute(frame,groups)
        mutated=frame.copy()
        mutated.loc[mutated.index>when,:]*=30.
        b,_=precompute(mutated,groups)
        for key in a:
            np.testing.assert_allclose(a[key].loc[when].to_numpy(float),
                 b[key].loc[when].to_numpy(float),atol=0,rtol=0)
    def test_objective_scoring_and_parameters_are_fixed(self):
        self.assertAlmostEqual(pinball([.03,-.01],[.03,-.01],.1),0)
        a=prob_score([0,1],[.1,.9])
        self.assertLess(a["brier"],.05)
        p=parameters()
        self.assertEqual(p["n_estimators"],80)
        self.assertEqual(p["num_leaves"],9)
if __name__=="__main__":unittest.main()
