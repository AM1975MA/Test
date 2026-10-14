import unittest
import numpy as np
from paper_ltr_v2.diagnose_linkage import numeric_difference


class NumericalLinkageDiagnostics(unittest.TestCase):
    def test_one_ulp_is_distinguished_from_real_value_or_mask_change(self):
        x=np.array([.1,-.2,0.,np.nan])
        y=x.copy();y[0]=np.nextafter(y[0],np.inf)
        result=numeric_difference(x,y)
        self.assertEqual(result['finite_value_differences'],1)
        self.assertEqual(result['max_ulp_difference'],1)
        self.assertEqual(result['finite_mask_differences'],0)
        y[3]=1.
        self.assertEqual(numeric_difference(x,y)['finite_mask_differences'],1)
        y[0]=.11
        self.assertGreater(numeric_difference(x,y)['max_absolute_difference'],.009)


if __name__=='__main__':unittest.main()
