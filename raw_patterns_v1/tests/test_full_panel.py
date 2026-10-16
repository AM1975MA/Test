import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'vendor/etf_trader_v2/src'))
from raw_patterns_v1.run import build_panel

class FullPanelTest(unittest.TestCase):
    def test_unknown_last_label_keeps_input_cohort(self):
        dates=pd.bdate_range('2010-01-01','2017-07-01');cols=[f'T{i:03}' for i in range(100)]
        x=np.tile((100+np.arange(len(dates))*.01)[:,None],(1,100))
        mats={k:pd.DataFrame(x.copy(),index=dates,columns=cols) for k in ('Open','High','Low','Close','Volume')}
        f,a,c,_=build_panel(mats,last_signal='2017-06-30',data_end='2017-07-02')
        end=f[f.signal_date=='2017-06-30']
        self.assertEqual(len(end),100)
        self.assertTrue(end.exit_date_21.isna().all())
        self.assertTrue(end.target_rank_21.isna().all())
        self.assertTrue(np.isfinite(a).all())
        for v in mats.values():v.loc[v.index<'2011-01-01']=-99.
        f2,a2,c2,_=build_panel(mats,last_signal='2017-06-30',data_end='2017-07-02')
        pd.testing.assert_frame_equal(f,f2);np.testing.assert_array_equal(a,a2);np.testing.assert_array_equal(c,c2)

if __name__=='__main__':unittest.main()
