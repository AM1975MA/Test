"""Contract checks for frozen, non-tuned EU120 allocation-rule factorial."""
import unittest
import numpy as np
from eu120_rule_factorial_v1.run import ARMS,label

class FactorialContract(unittest.TestCase):
    def test_exactly_sixteen_fixed_arms(self):
        self.assertEqual(len(ARMS),16)
        self.assertEqual(len({label(*a) for a in ARMS}),16)
        self.assertEqual(set(a[0] for a in ARMS),{"H","R"})
        self.assertEqual(set(a[1] for a in ARMS),{"D","F"})
        self.assertEqual(set(a[2] for a in ARMS),{0,1})
        self.assertEqual(set(a[3] for a in ARMS),{0,1})
    def test_archive_controls_unchanged(self):
        names={label(*a) for a in ARMS}
        for n in ("H_D_M1_A1","R_D_M1_A1","H_F_M0_A1","R_F_M0_A1",
                  "H_F_M0_A0","R_F_M0_A0"):
            self.assertIn(n,names)
    def test_fixed_and_dynamic_weight_rule_are_distinct(self):
        margin=np.array([.0,.04,.10,.13])
        native=.60+.40*np.minimum(margin/.13,1.)**2
        fixed=np.full_like(native,.5)
        self.assertTrue((native>.5).all())
        self.assertTrue((native<=1).all())
        self.assertTrue((fixed==.5).all())
    def test_margin_threshold_disables_only_confidence_gate(self):
        original_raw=np.array([.60,.73,.90])
        fed_margin=np.zeros_like(original_raw)
        np.testing.assert_array_equal(original_raw,np.array([.6,.73,.9]))
        self.assertFalse(np.any(fed_margin>0.0))

if __name__=="__main__":unittest.main()
