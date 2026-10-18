"""CBOE extra information must pass strict as-of / no future-quote tests."""
import unittest
import numpy as np
import pandas as pd
from oasis149.cboe_g4b.experiment import macro_asof,SERIES

class TestOptionsMarketAvailability(unittest.TestCase):
    def setUp(self):
        self.signal=pd.Timestamp("2021-06-21")
        dates=pd.bdate_range("2020-01-02",periods=400)
        self.data={name:pd.Series(np.linspace(15.,40.,400),
            index=dates) for name in SERIES}
    def test_future_cboe_quotes_cannot_rewrite_past(self):
        first=macro_asof(self.data,self.signal)
        self.assertIsNotNone(first)
        changed={}
        for name,x in self.data.items():
            y=x.copy()
            y.loc[y.index>self.signal-pd.Timedelta(days=7)]+=4000.
            changed[name]=y
        another=macro_asof(changed,self.signal)
        np.testing.assert_array_equal(first[0],another[0])
        np.testing.assert_array_equal(first[1],another[1])
        self.assertEqual(first[2],another[2])
    def test_stale_macro_index_blocks_no_interpolation(self):
        changed=dict(self.data)
        changed["OVX"]=changed["OVX"].loc[:"2020-12-31"]
        self.assertIsNone(macro_asof(changed,self.signal))
    def test_observation_fence_seven_days(self):
        a=macro_asof(self.data,self.signal)
        for observed in a[2].values():
            self.assertLessEqual(pd.Timestamp(observed),
                self.signal-pd.Timedelta(days=7))
if __name__=="__main__":unittest.main()
