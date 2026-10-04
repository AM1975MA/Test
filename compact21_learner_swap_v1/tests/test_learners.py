"""Real numerical fits. Reduced rounds apply exclusively inside test patches."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from compact21_learner_swap_v1 import learners as l
from ranker_stability_v1.run_ranker_benchmark_full import fit_predict, train_frame


def fixture():
    rng=np.random.default_rng(718)
    dates=pd.date_range('2015-01-31',periods=20,freq='ME')
    n=len(dates)*12
    x=rng.normal(size=(n,len(l.k.F2D_FEATURES)))
    frame=pd.DataFrame(x,columns=l.k.F2D_FEATURES)
    frame['signal_date']=np.repeat(dates,12)
    frame['ticker']=np.tile([f'T{i:02}' for i in range(12)],len(dates))
    frame['exit_date_21']=frame.signal_date+pd.Timedelta(days=30)
    frame['target_rank_21']=frame.groupby('signal_date')[l.k.F2D_FEATURES[0]].rank(pct=True)
    frame.loc[3,l.k.F2D_FEATURES[2]]=np.nan
    test=frame.iloc[:12].copy(); test['signal_date']=pd.Timestamp('2017-01-31')
    return frame,test


class LearnerTests(unittest.TestCase):
    def setUp(self):
        self.tr,self.te=fixture(); self.td=tempfile.TemporaryDirectory(); self.addCleanup(self.td.cleanup)
        self.root=Path(self.td.name)
        self.p1=patch.dict(l.k.COMPACT_PARAMS,n_estimators=2,min_child_weight=0)
        self.p2=patch.dict(l.LGBM_PARAMS,n_estimators=2,min_child_samples=4)
        self.p1.start(); self.p2.start(); self.addCleanup(self.p1.stop); self.addCleanup(self.p2.stop)
    def fit(self,variant,tr=None,tag='fit'):
        return l.fit(self.tr if tr is None else tr,[self.te],variant,2017,self.root,tag)
    def test_base_exact_canonical_worker_bytes(self):
        expected,_=fit_predict('XGB_CANONICAL',self.tr,[self.te],self.root,'canonical')
        actual,meta,y,_=self.fit('BASE')
        self.assertEqual(actual[0].tobytes(),expected[0].tobytes())
        np.testing.assert_array_equal(y,(self.tr.target_rank_21*100).round().astype(int))
        self.assertEqual(meta['feature_transform'],'identity')
        self.assertEqual(list(meta['seed_prediction_sha256']),['101','202','303'])
    def test_actual_ridge_and_lgbm_determinism_states_and_targets(self):
        for variant in ('RIDGE','LGBM_LAMBDARANK'):
            with self.subTest(variant=variant):
                p,meta,y,_=self.fit(variant,tag=variant)
                q,again,_,_=self.fit(variant,tag=variant+'again')
                self.assertEqual(p[0].tobytes(),q[0].tobytes())
                self.assertEqual(meta,again)
                self.assertTrue(meta['learned_state_hashes'])
                self.assertGreater(np.ptp(p[0]),0)
                if variant=='RIDGE':
                    self.assertEqual(meta['model_params']['alpha'],30.)
                    np.testing.assert_array_equal(y,self.tr.target_rank_21)
                    self.assertEqual(len(meta['scaler_mean']),len(l.k.F2D_FEATURES))
                    self.assertTrue((self.root/f'{variant}_ridge.joblib').exists())
                else:
                    self.assertEqual(meta['model_params']['objective'],'lambdarank')
                    self.assertEqual(meta['model_params']['label_gain'],list(range(101)))
                    self.assertTrue((self.root/f'{variant}_lgbm_101.txt').exists())
    def test_future_mutation_excluded_before_annual_fit(self):
        future=self.tr.iloc[:12].copy(); future['signal_date']=pd.Timestamp('2018-01-31')
        future['exit_date_21']=pd.Timestamp('2018-03-01'); future[l.k.F2D_FEATURES]=1e12
        future['target_rank_21']=np.linspace(0,1,12)
        mutated=pd.concat([self.tr,future],ignore_index=True)
        for variant in l.VARIANTS:
            p,a,_,_=self.fit(variant,train_frame(self.tr,2017),variant+'old')
            q,b,_,_=self.fit(variant,train_frame(mutated,2017),variant+'future')
            self.assertEqual(p[0].tobytes(),q[0].tobytes()); self.assertEqual(a,b)
    def test_invalid_maturity_group_keys_and_targets_fail_closed(self):
        cases=[]
        x=self.tr.copy(); x.loc[0,'exit_date_21']=pd.Timestamp('2017-01-01'); cases.append(x)
        x=self.tr.iloc[::-1]; cases.append(x)
        x=pd.concat([self.tr,self.tr.iloc[:1]]); cases.append(x)
        x=self.tr.copy(); x.loc[0,'target_rank_21']=np.inf; cases.append(x)
        for x in cases:
            with self.assertRaises(ValueError): self.fit('RIDGE',x)

class FrozenParametersTests(unittest.TestCase):
    def test_phase_b_parameters_are_frozen(self):
        self.assertEqual(l.RIDGE_PARAMS,dict(imputer_strategy='median',scaler='StandardScaler',alpha=30.))
        self.assertEqual(l.LGBM_PARAMS['n_estimators'],360)
        self.assertEqual(l.LGBM_PARAMS['min_child_samples'],40)
        self.assertEqual(l.LGBM_PARAMS['max_depth'],4)
        self.assertEqual(l.LGBM_PARAMS['n_jobs'],1)
        self.assertEqual(list(l.k.COMPACT_SEEDS),[101,202,303])
if __name__=='__main__': unittest.main()
