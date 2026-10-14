import unittest
import numpy as np
import pandas as pd
from opportunity_v1.core import causal_features, mature_training, router_decisions, period_shadow

class OpportunityCausality(unittest.TestCase):
    def test_forward_target_predictors_are_excluded(self):
        names=['ret_21_mean','target_excess_max','target_excess_max_rank','cluster_is_0']
        self.assertEqual(causal_features(names),['ret_21_mean','cluster_is_0'])

    def test_training_requires_mature_exit_and_past_signal(self):
        f=pd.DataFrame({'signal_date':pd.to_datetime(['2019-01-01','2019-01-01','2020-01-01']),
                        'label_exit_date_21':pd.to_datetime(['2019-02-01','2020-01-01','2019-12-01']),
                        'target_excess_max':[1.,1.,1.]})
        self.assertEqual(list(mature_training(f,pd.Timestamp('2020-01-01')).index),[0])

    def test_router_uses_only_shadow_available_at_signal(self):
        signal=pd.to_datetime(['2020-01-01','2020-02-01','2020-03-01'])
        exits=pd.to_datetime(['2019-01-01']*11+['2020-01-02','2020-02-02'])
        logs=np.array([.01]*12+[-1.])
        active,count,sums=router_decisions(signal,exits,logs)
        np.testing.assert_array_equal(active,[False,True,False])
        np.testing.assert_array_equal(count,[11,12,13])
        self.assertLess(sums[-1],0)

    def test_future_shadow_changes_do_not_change_past_router(self):
        signal=pd.date_range('2020-01-01',periods=5,freq='MS')
        exits=pd.date_range('2018-01-01',periods=30,freq='MS')
        logs=np.ones(30)*.01
        a=router_decisions(signal,exits,logs)[0]
        logs[exits>signal.max()]=-100
        np.testing.assert_array_equal(a,router_decisions(signal,exits,logs)[0])

    def test_shadow_respects_equity_next_open_convention(self):
        ds=pd.date_range('2020-01-01',periods=5,freq='D')
        cal=pd.DataFrame({'entry_date':[ds[0],ds[2]],'exit_date':[ds[2],ds[4]]})
        # E[k] is valuation at open k+1, final row duplicates terminal open.
        base=np.array([1.,1.,1.,1.,1.]); direct=np.array([1.1,1.21,1.331,1.4641,1.4641])
        s=period_shadow(ds,cal,base,direct)
        np.testing.assert_allclose(s,np.log([1.21,1.21]),atol=1e-14)

if __name__=='__main__':unittest.main()
