
import unittest
import numpy as np
import prepare
class SourceBridgeTests(unittest.TestCase):
 def test_constant_units_bridge(self):
  self.assertTrue(hasattr(prepare,"bridge_scale"))
  c=np.array([100.,101.,99.]);o=np.array([99.,100.,100.])
  self.assertAlmostEqual(prepare.bridge_scale(c,o,c/3,o/3),3.)
 def test_nonconstant_bridge_rejected(self):
  self.assertTrue(hasattr(prepare,"bridge_scale"))
  with self.assertRaises(ValueError):prepare.bridge_scale(np.array([100.,101.]),np.array([99.,100.]),np.array([100.,50.]),np.array([99.,100.]))
if __name__=="__main__": unittest.main()
