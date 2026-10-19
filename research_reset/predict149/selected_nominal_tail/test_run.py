import unittest
import numpy as np
import pandas as pd
from research_reset.predict149.selected_nominal_tail.run import (
    held_weights, eligible_matured, future_nominal, ci_month, K
)

class ScientificChronology(unittest.TestCase):
    def test_held_membership_and_null(self):
        f=list("ABCDE")
        h=list("CDEFG")
        static=held_weights(f,h)
        equal=held_weights(f,h,{t:.19 for t in set(f+h)})
        self.assertEqual(set(static), set(equal))
        for ticker in static:
            self.assertAlmostEqual(static[ticker],equal[ticker],places=12)
        varied=held_weights(f,h,{t:.04+.04*i for i,t in enumerate(sorted(set(f+h)))})
        self.assertEqual(set(varied),set(static))
        self.assertAlmostEqual(sum(varied.values()),1,places=12)
        self.assertNotEqual(varied,static)

    def test_unmatured_recent_event_embargoed(self):
        t=pd.DataFrame({"block":[1,2,3],
                        "maturity":["2021-03-02","2021-04-02","2021-05-02"],
                        "loss5":[0,1,0]})
        z=eligible_matured(t,"2021-04-02")
        self.assertEqual(z.block.tolist(),[1])
        self.assertNotIn(2,z.block.tolist())

    def test_exact_entry_and_exit_open_label(self):
        d=pd.date_range("2021-01-01",periods=K+1)
        opens=pd.DataFrame({"A":np.linspace(100,90,K+1),
                            "B":np.linspace(100,100,K+1)},index=d)
        a,b,m=future_nominal(opens,d,["A","B"],[.5,.5])
        self.assertAlmostEqual(b,-.05,places=12)
        self.assertAlmostEqual(m,-.05,places=12)
        self.assertTrue(np.allclose(a,[-.10,0.]))

    def test_anchor_resample_not_independent_etf_rows(self):
        v=ci_month(np.ones(43)*.007,20261019,n=30)
        self.assertAlmostEqual(v["mean"],.007)
        self.assertAlmostEqual(v["ci95"][0],.007)

if __name__=="__main__":
    unittest.main()
