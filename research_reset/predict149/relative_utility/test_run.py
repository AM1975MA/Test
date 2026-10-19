"""T149-J prove forecast chronology and fully as-of current basket score inputs."""
import unittest
import numpy as np
import pandas as pd
from research_reset.predict149.relative_utility.run import (
    strictly_asof_state, online_model_predictions, FEATURES,MIN_MATURE)
from research_reset.predict149.complementarity.run import monthly_weights
from oasis149.canonical import load_149
class T149RelativeOpportunityTests(unittest.TestCase):
    def test_future_model_labels_cannot_affect_current_online_utility(self):
        ids=list(range(48,112))
        calendar=pd.bdate_range("2017-02-01",periods=112*21+1)
        signals=list(calendar)
        for k in range(1,len(signals)):
            signals[k]=calendar[k-1] # just closed previous session
        rng=np.random.default_rng(17)
        states=rng.normal(size=(64,10))
        y=rng.normal(0,.06,size=64)
        a=online_model_predictions(states,y,calendar,signals,ids)
        k=38
        v=y.copy()
        v[k-1:]+=100. # future includes just finished unavailable prior month!
        b=online_model_predictions(states,v,calendar,signals,ids)
        for key in ("J1_weight_F3","J2_weight_F3","J3_weight_F3",
                    "J2_predicted_signed_excess","J3_predicted_signed_excess",
                    "J2_forecast_sign_prob","J3_forecast_sign_prob"):
            self.assertEqual(float(a.loc[k,key]),float(b.loc[k,key]),key)
        self.assertEqual(int(a.loc[k,"latest_allowed_matured_eval_block"]),k-2)
        self.assertEqual(int(a.loc[k,"n_matured_expert_spreads"]),k-1)
    def test_current_basket_features_are_unchanged_by_future_close(self):
        roster,O,C,V,days,signals,qual=load_149()
        source=signals[56*21]
        names=list(roster.ticker)
        pickF=names[:5];pickH=names[5:10]
        rng=np.random.default_rng(2)
        data={"ticker":names,
            "B0_F3_FROZEN":rng.normal(0,.01,149),
            "H1_FACTOR_ONLY":rng.normal(0,.01,149),
            "R_Q10":np.full(149,-.05),
            "R_Q90":np.full(149,.05)}
        for f in ("SPY","QQQ","IWM","VEA","EEM","TLT","HYG","GLD","USO","IEF"):
            data["beta_"+f]=rng.normal(size=149)
        scores=pd.DataFrame(data)
        F=scores.nlargest(5,"B0_F3_FROZEN").ticker.tolist()
        H=scores.nlargest(5,"H1_FACTOR_ONLY").ticker.tolist()
        v=strictly_asof_state(C,roster,scores,source,F,H)
        later=C.copy()
        later.loc[later.index>source,:]*=75.
        u=strictly_asof_state(later,roster,scores,source,F,H)
        np.testing.assert_array_equal(v,u)
        self.assertEqual(len(v),len(FEATURES))
    def test_underlying_shared_positions_are_summed(self):
        a=monthly_weights([("F3",.75,["A","B","C","D","E"]),
                           ("H1",.25,["A","B","F","G","H"])])
        self.assertEqual(len(a),8)
        self.assertAlmostEqual(a["A"],(.75+.25)/5)
        self.assertAlmostEqual(sum(a.values()),1.)
        self.assertEqual(MIN_MATURE,18)
if __name__=="__main__":unittest.main()
