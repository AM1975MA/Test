"""Prove macro factor release fence and exact original149 pair dimensionality."""
import unittest
import numpy as np
import pandas as pd
from oasis149.macro_g4.experiment import macro_asof,SERIES

class TestMacroAsOf(unittest.TestCase):
    def setUp(self):
        days=pd.bdate_range("2019-01-01",periods=200)
        self.source={s:pd.Series(np.linspace(8.,12.,len(days)),
                 index=days) for s in SERIES}
        self.signal=pd.Timestamp("2019-08-20")
    def test_mutation_after_release_cutoff_has_no_effect(self):
        original=macro_asof(self.source,self.signal)
        later={}
        for k,v in self.source.items():
            x=v.copy()
            x.loc[x.index>=self.signal-pd.Timedelta(days=6)]*=100.
            later[k]=x
        result=macro_asof(later,self.signal)
        self.assertIsNotNone(original)
        np.testing.assert_array_equal(result[0],original[0])
        np.testing.assert_array_equal(result[1],original[1])
        self.assertEqual(result[2],original[2])
    def test_empty_macro_series_blocks_instead_of_filling_future(self):
        bad=dict(self.source)
        bad["VIXCLS"]=bad["VIXCLS"].loc[:"2019-01-09"]
        self.assertIsNone(macro_asof(bad,self.signal))
    def test_every_observation_older_than_7_day_lag(self):
        x=macro_asof(self.source,self.signal)
        evidence=x[2]
        for stamp in evidence.values():
            self.assertLessEqual(pd.Timestamp(stamp),
                     self.signal-pd.Timedelta(days=7))
if __name__=="__main__":unittest.main()
