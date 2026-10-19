"""Risk overlay must NEVER replace F3/H1 names or see tomorrow's market."""
import unittest
import numpy as np
import pandas as pd
from research_reset.predict149.k1_overlay.run import (
  basket_tilt,merge_baskets,load_archive,WARMUP,per_period_event_risk)
class FrozenK1RiskOverlayTests(unittest.TestCase):
    def test_tilt_preserves_all_expert_names_full_investment(self):
        F=["A","B","C","D","E"];H=["A","B","F","G","H"]
        p=dict(zip(sorted(set(F+H)),[.02,.05,.1,.12,.15,.17,.19,.22]))
        for within,expert in ((True,False),(False,True),(True,True)):
            w,frac,_,_=merge_baskets(F,H,p,within,expert)
            self.assertEqual(set(w),set(F+H))
            self.assertAlmostEqual(sum(w.values()),1.,places=12)
            self.assertGreaterEqual(frac,.25)
            self.assertLessEqual(frac,.75)
        self.assertEqual(len(basket_tilt(F,p)),5)
        inv,_,_,_=merge_baskets(F,H,p,True,True,True)
        self.assertAlmostEqual(sum(inv.values()),1.,places=12)
    def test_equal_probability_replays_original_50_50_exactly(self):
        F=["A","B","C","D","E"];H=["A","B","F","G","H"]
        p={t:.127 for t in set(F+H)}
        w,frac,_,_=merge_baskets(F,H,p,True,True)
        self.assertEqual(frac,.5)
        expected={t:(int(t in F)+int(t in H))*.1 for t in set(F+H)}
        for t in w:self.assertAlmostEqual(w[t],expected[t],places=14)
    def test_base_K1_is_frozen_and_signal_is_previous_close(self):
        frame,roster,O,C,days,signals,ids,selected,ref=load_archive()
        self.assertEqual(len(frame),149*64)
        self.assertEqual(WARMUP,13)
        for k,b in enumerate(ids):
            self.assertLess(pd.Timestamp(signals[b*21]),
                            pd.Timestamp(days[b*21]))
            self.assertEqual(len(selected["F3"][k]),5)
            self.assertEqual(len(selected["H1"][k]),5)
            if k>=13:
                sub=frame.loc[frame.block==b]
                got=per_period_event_risk(
                    sub,selected["F3"][k],selected["H1"][k])
                self.assertTrue(np.isfinite(got["prob_error_gain"]))
                self.assertTrue(0<=got["selected_pred_pdown"]<=1)
                self.assertTrue(0<=got["selected_relative_negative_tail_event_rate"]<=1)
if __name__=="__main__":unittest.main()
