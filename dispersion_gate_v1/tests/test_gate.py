import unittest
import numpy as np
import pandas as pd
from dispersion_gate_v1.gate import historical_dispersion,annual_gate

class GateTest(unittest.TestCase):
    def test_causality_and_price_scale(self):
        d=pd.bdate_range('2010-01-01','2018-12-31');rng=np.random.default_rng(6)
        x=pd.DataFrame(np.exp(np.cumsum(rng.normal(0,.01,(len(d),100)),axis=0)),index=d)
        a=historical_dispersion(x)
        y=x.copy();y.loc[y.index<'2011-01-01']=-100.;y.loc[y.index>'2016-06-30']*=100
        b=historical_dispersion(y)
        pd.testing.assert_frame_equal(a[a.signal_date<='2016-06-30'],b[b.signal_date<='2016-06-30'])
        c=historical_dispersion(x*np.arange(1,101)[None,:])
        np.testing.assert_allclose(a.dispersion,c.dispersion,atol=1e-14)
        self.assertGreaterEqual(a.signal_date.min(),pd.Timestamp('2011-02-01'))
    def test_fixed_past_median_and_direction(self):
        d=pd.date_range('2012-01-31',periods=84,freq='ME')
        f=pd.DataFrame(dict(signal_date=d,dispersion=np.arange(84.)+1,eligible=149))
        a=annual_gate(f,2017)
        self.assertTrue(a.use_full.all());self.assertEqual(a.threshold.iloc[0],30.5)
        f.loc[f.signal_date=='2017-02-28','dispersion']=0.
        b=annual_gate(f,2017)
        self.assertEqual(b.threshold.nunique(),1)
        self.assertFalse(b.loc[b.signal_date=='2017-02-28','use_full'].iloc[0])
        f.loc[f.signal_date.dt.year==2018,'dispersion']=9999
        pd.testing.assert_frame_equal(b,annual_gate(f,2017))
    def test_observed_return_definition(self):
        d=pd.bdate_range('2011-01-03',periods=66)
        x=pd.DataFrame(np.tile(np.arange(1.,67)[:,None],(1,100)),index=d)
        x.iloc[-1,0]*=2
        z=historical_dispersion(x)
        date=z.signal_date.iloc[-1];pos=x.index.get_loc(date)
        self.assertAlmostEqual(z.dispersion.iloc[-1],(x.iloc[pos]/x.iloc[pos-21]-1).std(ddof=1),places=14)

if __name__=='__main__':unittest.main()
