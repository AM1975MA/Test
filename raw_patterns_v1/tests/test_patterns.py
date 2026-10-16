import unittest
import numpy as np
import pandas as pd
from raw_patterns_v1.patterns import flatten_views, leave_one_out, split_dates

class PatternsTest(unittest.TestCase):
    def test_causal_scale_invariant(self):
        a=np.column_stack([np.arange(1.,181)+k for k in (1,3,0,2,100)])
        z=flatten_views(a,130)
        self.assertEqual(z.shape,(315,))
        b=a.copy();b[131:]*=9
        np.testing.assert_array_equal(z,flatten_views(b,130))
        b=a.copy();b[:,:4]*=7;b[:,4]*=5
        np.testing.assert_allclose(z,flatten_views(b,130),atol=1e-12)
        with self.assertRaises(ValueError):flatten_views(a,124)
    def test_context_excludes_self(self):
        x=np.array([[1.,2.],[3.,4.],[7.,8.]])
        c=leave_one_out(x)
        np.testing.assert_array_equal(c[0],x[1:].mean(axis=0))
        x[0]*=9
        np.testing.assert_array_equal(c[0],leave_one_out(x)[0])
    def test_purge_maturity(self):
        d=pd.date_range('2012-01-31',periods=47,freq='ME')
        f=pd.DataFrame(dict(signal_date=d,exit_date_21=d+pd.Timedelta(days=32)))
        sub,val,test=split_dates(f,2015)
        self.assertEqual(val.signal_date.nunique(),12)
        self.assertTrue((sub.exit_date_21<val.signal_date.min()).all())
        self.assertTrue((val.exit_date_21<pd.Timestamp('2015-01-01')).all())
        self.assertTrue((test.signal_date.dt.year==2015).all())

if __name__=='__main__':unittest.main()
