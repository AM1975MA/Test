import unittest
import pandas as pd
import numpy as np
from research_reset.predict149.k1_risk_overlay.run import allocate
class TestK1RiskOverlay(unittest.TestCase):
 def setUp(self):
  self.f=["A","B","C","D","E"];self.h=["C","D","F","G","H"]
  self.data=pd.DataFrame({"P_DOWN5":[.05,.10,.20,.30,.40,.25,.10,.30],
   "v63":[.02,.04,.06,.08,.10,.06,.03,.07]},
   index=["A","B","C","D","E","F","G","H"])
 def test_no_new_tickers_and_budget(self):
  for name in ("STATIC_F3_H1_50","L1_K1_WITHIN","L2_K1_BETWEEN",
               "L3_K1_TWO_LEVELS","L4_VOL63_WITHIN"):
   w=allocate(self.f,self.h,self.data,name)
   self.assertEqual(set(w),set(self.f+self.h))
   self.assertAlmostEqual(sum(w.values()),1.,places=12)
   self.assertTrue(all(v>0 for v in w.values()))
 def test_expert_selection_not_changed_even_when_risk_reversed(self):
  old=allocate(self.f,self.h,self.data,"L1_K1_WITHIN")
  changed=self.data.copy()
  changed["P_DOWN5"]=changed["P_DOWN5"].iloc[::-1].to_numpy()
  new=allocate(self.f,self.h,changed,"L1_K1_WITHIN")
  self.assertEqual(set(old),set(new))
  self.assertNotEqual(old,new)
if __name__=="__main__":unittest.main()
