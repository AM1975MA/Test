"""Only synthetic mathematical/integrity checks; no financial replay or tuning."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src")]
from etf_trader.source_only import kernel as k
from compact21_rbf_ridge_v1 import model,run
from compact21_learner_swap_v1.learners import array_hash


def synthetic():
    rng=np.random.default_rng(91)
    train=pd.DataFrame(rng.normal(size=(18,125)),columns=k.F2D_FEATURES)
    train['signal_date']=np.repeat(pd.to_datetime(['2016-01-29','2016-02-29','2016-03-31']),6)
    train['ticker']=[f'T{i}' for i in range(6)]*3
    train['target_rank_21']=np.tile(np.linspace(0,1,6),3)
    train['exit_date_21']=train.signal_date+pd.Timedelta(days=30)
    train.loc[0,k.F2D_FEATURES[0]]=np.nan
    test=pd.DataFrame(rng.normal(size=(6,125)),columns=k.F2D_FEATURES)
    test['signal_date']=pd.Timestamp('2017-01-31');test['ticker']=[f'T{i}' for i in range(6)]
    return train,[test,test.copy()]


class ModelTests(unittest.TestCase):
    def test_fixed_recipe_and_full_state_dimensions(self):
        train,tests=synthetic()
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            p,a,y,_=model.fit(train,tests,2017,td,'one')
            self.assertEqual(a['model_params'],model.PARAMS)
            self.assertEqual(a['design_features'],637)
            self.assertEqual(a['train_labels_sha256'],array_hash(train.target_rank_21.to_numpy(float)))
            np.testing.assert_array_equal(y,train.target_rank_21)
            with np.load(Path(td)/'one_STATES.npz',allow_pickle=False) as s:
                self.assertEqual(set(s.files),set(a['learned_state_hashes']))
                self.assertEqual(s['input_scaler_n_samples_seen'].shape,())
                self.assertEqual(float(s['input_scaler_n_samples_seen']),18.)
                for name in s.files:self.assertEqual(array_hash(s[name]),a['learned_state_hashes'][name])
                for seed in (101,202,303):
                    self.assertEqual(s[f'seed_{seed}_rbf_random_weights'].shape,(125,512))
                    self.assertEqual(s[f'seed_{seed}_ridge_coef'].shape,(637,))
                    random=np.random.RandomState(seed)
                    expected=np.sqrt(2/125)*random.normal(size=(125,512))
                    offset=random.uniform(0,2*np.pi,size=512)
                    np.testing.assert_array_equal(s[f'seed_{seed}_rbf_random_weights'],expected)
                    np.testing.assert_array_equal(s[f'seed_{seed}_rbf_random_offset'],offset)
            seeds=np.load(Path(td)/'one_SEED_PREDICTIONS.npy',allow_pickle=False)
            self.assertEqual(seeds.shape,(3,12));self.assertEqual(seeds.dtype,np.float64)
            self.assertEqual(np.concatenate(p).tobytes(),seeds.mean(axis=0,dtype=np.float64).tobytes())

    def test_independent_refit_exact_and_inference_does_not_fit_state(self):
        train,tests=synthetic()
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            p,a,_,_=model.fit(train,tests,2017,td,'one')
            q,b,_,_=model.fit(train,tests,2017,td,'two')
            self.assertEqual(a,b)
            for x,y in zip(p,q):self.assertEqual(x.tobytes(),y.tobytes())
            mutated=[z.copy() for z in tests]
            for z in mutated:z.loc[:,k.F2D_FEATURES]=1e6
            _,c,_,_=model.fit(train,mutated,2017,td,'future')
            self.assertEqual(a['learned_state_hashes'],c['learned_state_hashes'])
            self.assertEqual(a['fit_matrix_sha256'],c['fit_matrix_sha256'])
            self.assertNotEqual(a['test_matrix_sha256'],c['test_matrix_sha256'])

    def test_actual_exit_not_signal_only_defines_maturity(self):
        train,tests=synthetic();train.loc[0,'exit_date_21']=pd.Timestamp('2017-01-01')
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            with self.assertRaisesRegex(ValueError,'Immature'):
                model.fit(train,tests,2017,td,'bad')

    def test_shared_preprocessing_matches_original_ridge_on_synthetic(self):
        train,tests=synthetic()
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            _,old,_,_=run.learners.fit(train,tests,'RIDGE',2017,td,'old_ridge')
            _,new,_,_=model.fit(train,tests,2017,td,'rbf')
        self.assertEqual(new['train_labels_sha256'],old['train_labels_sha256'])
        for fresh,original in (('imputer_statistics','imputer_statistics'),
            ('input_scaler_mean','scaler_mean'),('input_scaler_scale','scaler_scale'),
            ('input_scaler_variance','scaler_variance')):
            self.assertEqual(new['learned_state_hashes'][fresh],old['learned_state_hashes'][original])

    def test_all_missing_feature_fails_instead_of_changing_dimension(self):
        train,tests=synthetic();train[k.F2D_FEATURES[2]]=np.nan
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            with self.assertRaisesRegex(ValueError,'Entirely missing'):
                model.fit(train,tests,2017,td,'bad')

    def test_duplicate_keys_and_invalid_continuous_target_fail(self):
        train,tests=synthetic();train.loc[1,'ticker']=train.loc[0,'ticker']
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            with self.assertRaisesRegex(ValueError,'duplicate'):
                model.fit(train,tests,2017,td,'bad')
        train,tests=synthetic();train.loc[1,'target_rank_21']=1.2
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            with self.assertRaisesRegex(ValueError,'continuous percentile'):
                model.fit(train,tests,2017,td,'bad')

    def test_ridge_control_audit_tamper_fails_closed(self):
        train,tests=synthetic();trains={i:train for i in (1,2,3)};native={i:tests[0] for i in (1,2,3)}
        ref={'per_year':{'2017':{'transforms':{str(i):{'kind':'RIDGE'} for i in (1,2,3)}}}}
        with patch.object(run.learners,'fit',return_value=([],{'kind':'wrong'},None,0)):
            with self.assertRaisesRegex(ValueError,'RIDGE complete audit'):
                run.ridge_controls(trains,native,tests[0],2017,ref,None,None,None)


if __name__=='__main__':unittest.main()
