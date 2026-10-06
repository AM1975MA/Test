import unittest
import numpy as np
import pandas as pd
from compact21_factorial_v1.run import mix_rows,keys_hash,k

def donor():
    f=pd.DataFrame({'signal_date':pd.to_datetime(['2016-10-31']*3),'ticker':['A','B','C'],
       'exit_date_21':pd.to_datetime(['2016-12-01']*3),'target_rank_21':[.2,.6,.9]})
    return pd.concat([f,pd.DataFrame({n:[1.,2.,3.] for n in k.F2D_FEATURES})],axis=1)

class InterventionTests(unittest.TestCase):
    def test_shuffled_donor_aligns_by_keys_and_preserves_features(self):
        a=donor();b=a.copy();b['target_rank_21']=[.9,.2,.6];b=b.iloc[[2,0,1]]
        z=mix_rows(a,b,2017)
        np.testing.assert_array_equal(z[k.F2D_FEATURES],a[k.F2D_FEATURES])
        np.testing.assert_array_equal(z.target_rank_21,[.9,.2,.6])
        self.assertEqual(keys_hash(z),keys_hash(a))
    def test_donor_future_exit_rejected_even_when_feature_donor_mature(self):
        a=donor();b=a.copy();b.loc[1,'exit_date_21']=pd.Timestamp('2017-01-01')
        with self.assertRaises(ValueError):mix_rows(a,b,2017)
    def test_missing_duplicate_or_mismatched_donor_keys_rejected(self):
        a=donor()
        for b in (a.iloc[:2],a.iloc[[0,0,2]],a.assign(ticker=['A','B','Z'])):
            with self.assertRaises(ValueError):mix_rows(a,b,2017)
    def test_future_unused_fields_do_not_enter_feature_or_rank_target(self):
        a=donor();b=a.copy();b['fwd_ret_21']=1e9
        z=mix_rows(a,b,2017)
        pd.testing.assert_frame_equal(z[k.F2D_FEATURES],a[k.F2D_FEATURES])
        np.testing.assert_array_equal(z.target_rank_21,a.target_rank_21)

if __name__=='__main__':unittest.main()
