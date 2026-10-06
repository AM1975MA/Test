"""Synthetic retained evidence; no financial fits or candidate outcome access."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/etf_trader_v2/src')]
from compact21_rbf_ridge_v1 import summarize as s
from compact21_semidev_v1.tests import test_summary as fixture_module


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        fixture_module.AnnualValidationTests.setUp(self)
        self.r['line']=s.LINE;self.r['variant']=s.VARIANT;self.r['status']=s.LINE+'_COMPLETE';self.r['RIDGE_PARITY_PASS']=True
        self.r.pop('build_protocol_sha256');a=self.r['per_year']['2017'];a.pop('view_audit')
        self.ridge=deepcopy(self.base);self.ridge['sha256']='synthetic-ridge-reference'
        self.r['input_contract'].update(line=s.LINE,train_cohorts='original_native_frozen',changed_columns=[],recipe=deepcopy(s.PARAMS),
            ref_ridge_result_sha256=self.ridge['sha256'],ridge_reference_prediction_sha256=deepcopy(self.ridge['result']['files_sha256']))
        self.r['input_contract'].pop('raw_contract_sha256')
        for index,frame in ((4,self.ridge['native']),(5,self.ridge['common'])):
            name=s.FILES[index];self.frames[name]=frame.copy();(self.root/name).write_bytes(name.encode());self.r['files_sha256'][name]=s.sha(self.root/name)
        names=self.base['native'].ticker.unique();dates=pd.date_range('2012-01-31',periods=59,freq='ME')
        train=pd.DataFrame([(d,t) for d in dates for t in names],columns=['signal_date','ticker'])
        train['exit_date_21']=train.signal_date+pd.Timedelta(days=30)
        train['target_rank_21']=np.tile(np.arange(149)/149,len(dates))
        values=pd.DataFrame(np.zeros((len(train),125)),columns=s.learners.k.F2D_FEATURES)
        train=pd.concat([train,values],axis=1)
        self.trains={v:train.copy() for v in (1,2,3)};states={};seeds={}
        a['ridge_control_transforms']={};a['ridge_control']={}
        a['evaluation_coverage']['train_keys_sha256']={str(v):s.keys_hash(train) for v in (1,2,3)}
        self.base['result']['per_year']['2017']['evaluation_coverage']=deepcopy(a['evaluation_coverage'])
        self.ridge['result']['per_year']['2017']['evaluation_coverage']=deepcopy(a['evaluation_coverage'])
        for v in (1,2,3):
            key=str(v);old=self.base['result']['per_year']['2017']['transforms'][key]
            old.update(train_matrix_sha256=s.learners.array_hash(s.learners.matrix(train).to_numpy()),train_rows=len(train),
                feature_names=list(s.learners.k.F2D_FEATURES),test_matrix_sha256=['common','native'],
                train_groups_sha256=s.learners.array_hash(train.groupby('signal_date').size().to_numpy()))
            a['control_transforms'][key]=deepcopy(old)
            shared=dict(imputer_statistics=np.zeros(125),input_scaler_mean=np.zeros(125),input_scaler_scale=np.ones(125),
                input_scaler_variance=np.zeros(125),input_scaler_n_samples_seen=np.asarray(float(len(train))))
            rold=self.ridge['result']['per_year']['2017']['transforms'][key]
            rold.update(deepcopy(old));rold['train_labels_sha256']=s.learners.array_hash(train.target_rank_21.to_numpy(float))
            rold['learned_state_hashes']={oldname:s.learners.array_hash(shared[newname]) for newname,oldname in (
                ('imputer_statistics','imputer_statistics'),('input_scaler_mean','scaler_mean'),('input_scaler_scale','scaler_scale'),('input_scaler_variance','scaler_variance'))}
            a['ridge_control_transforms'][key]=deepcopy(rold);a['ridge_control'][key]=deepcopy(a['legacy_control'][key])
            fitted=deepcopy(shared)
            for seed in s.SEEDS:
                rng=np.random.RandomState(seed)
                seedstate=dict(rbf_random_weights=np.sqrt(2./125)*rng.normal(size=(125,512)),rbf_random_offset=rng.uniform(0,2*np.pi,512),
                    rbf_scaler_mean=np.zeros(512),rbf_scaler_scale=np.ones(512),rbf_scaler_variance=np.zeros(512),
                    rbf_scaler_n_samples_seen=np.asarray(float(len(train))),ridge_coef=np.zeros(637),ridge_intercept=np.asarray(.5))
                fitted.update({f'seed_{seed}_{name}':value for name,value in seedstate.items()})
            for name,value in fitted.items():states[f'v{v}_{name}']=value
            combined=np.concatenate([self.frames[name].loc[self.frames[name].vintage==v,'pred'].to_numpy() for name in (s.FILES[1],s.FILES[0])])
            seeds[f'predictions_{v}']=np.stack([combined]*3)
            new=deepcopy(old);new.update(kind=s.VARIANT,design_features=637,input_features=125,model_params=deepcopy(s.PARAMS),
                feature_transform='mature_median_standard_linear_skip_plus_scaled_RBF',target='continuous_percentile',
                train_labels_sha256=rold['train_labels_sha256'],learned_state_hashes={name:s.learners.array_hash(value) for name,value in fitted.items()},
                fit_matrix_sha256={str(seed):'fit' for seed in s.SEEDS},test_fit_matrix_sha256={str(seed):['test1','test2'] for seed in s.SEEDS},
                seed_prediction_sha256={str(seed):s.learners.array_hash(combined) for seed in s.SEEDS},
                prediction_sha256=[s.learners.array_hash(self.frames[name].loc[self.frames[name].vintage==v,'pred'].to_numpy()) for name in (s.FILES[1],s.FILES[0])])
            a['transforms'][key]=new
            a['independent_refits'][key].update(refit_audit=deepcopy(new),prediction_sha256=deepcopy(new['prediction_sha256']),
                fitted_states_bytes_exact=True,seed_vectors_bytes_exact=True)
        self.states=states;self.seeds=seeds
        self.write_npz()

    def write_npz(self):
        for filename,values in (('FITTED_STATES.npz',self.states),('SEED_PREDICTIONS.npz',self.seeds)):
            np.savez(self.root/filename,**values);self.r['files_sha256'][filename]=s.sha(self.root/filename)

    def call(self):
        self.path.write_text(json.dumps(self.r,allow_nan=False))
        with patch.object(s.pd,'read_parquet',side_effect=lambda p:self.frames[Path(p).name].copy()),patch.object(s,'select_original_frames',return_value=(self.trains,{},None)):
            return s.load_year(self.path,self.base,self.ridge,{})

    def test_complete_job_with_both_controls_and_state_proof(self):
        self.assertEqual(self.call()['year'],2017)

    def test_seed_mean_not_a_manifest_claim(self):
        self.seeds['predictions_1'][0,0]+=1.;self.write_npz()
        with self.assertRaisesRegex(ValueError,'Retained seed'):self.call()

    def test_fitted_state_hashes_recomputed_from_physical_arrays(self):
        self.states['v1_seed_101_ridge_coef'][0]+=1;self.write_npz()
        with self.assertRaisesRegex(ValueError,'Fitted-state array/hash'):self.call()

    def test_random_projection_reconstructed_independently_even_after_rehash(self):
        self.states['v1_seed_101_rbf_random_offset'][0]+=.001;self.write_npz()
        a=self.r['per_year']['2017'];a['transforms']['1']['learned_state_hashes']['seed_101_rbf_random_offset']=s.learners.array_hash(self.states['v1_seed_101_rbf_random_offset'])
        a['independent_refits']['1']['refit_audit']=deepcopy(a['transforms']['1'])
        with self.assertRaisesRegex(ValueError,'Frozen random RBF'):self.call()

    def test_refit_control_and_frozen_recipe_failures_block(self):
        original=deepcopy(self.r)
        for kind in ('base','ridge','state_refit','seed_refit','solver','labels','nan_maturity','numeric','source'):
            with self.subTest(kind=kind):
                self.r=deepcopy(original);a=self.r['per_year']['2017']
                if kind=='base':a['legacy_control']['1']['native_bytes_exact']=False
                elif kind=='ridge':a['ridge_control']['1']['common_bytes_exact']=False
                elif kind=='state_refit':a['independent_refits']['1']['fitted_states_bytes_exact']=False
                elif kind=='seed_refit':a['independent_refits']['1']['seed_vectors_bytes_exact']=False
                elif kind=='solver':self.r['input_contract']['recipe']['solver']='cholesky'
                elif kind=='labels':a['transforms']['1']['train_labels_sha256']='rounded'
                elif kind=='nan_maturity':a['transforms']['1']['max_exit_date_21']='NaT'
                elif kind=='numeric':self.r['numeric_contract']['pandas']='different'
                else:self.r['fit_sources'][s.FIT_SOURCES[0]]='different'
                with self.assertRaises(ValueError):self.call()

    def test_candidate_outcome_signed_zero_bits_preserved(self):
        self.frames[s.FILES[0]].loc[0,'target_ret_21']=-0.
        with self.assertRaisesRegex(ValueError,'float bits'):self.call()

    def test_physical_training_targets_not_only_declared_hashes(self):
        self.trains[1].loc[0,'target_rank_21']+=.01
        with self.assertRaisesRegex(ValueError,'Physical original feature/target'):self.call()

    def test_missing_retained_state_or_seed_schema_fails(self):
        self.states.pop('v1_seed_101_ridge_coef');self.write_npz()
        with self.assertRaisesRegex(ValueError,'Fitted-state evidence schema'):self.call()

    def test_duplicate_or_incomplete_annual_matrix_fails(self):
        job=self.call()
        def variant(_,name):return self.base if name=='BASE' else self.ridge
        for duplicate in (False,True):
            if duplicate:
                folder=self.root/'duplicate';folder.mkdir();(folder/'RESULT.json').write_text(json.dumps(self.r))
            with patch.object(s,'load_variant',side_effect=variant),patch.object(s,'sha',return_value='synthetic'),patch.object(s,'FROZEN_TI',{str(v):'synthetic' for v in (1,2,3)}),patch.object(s,'load',return_value=None),patch.object(s,'load_year',return_value=job):
                with self.assertRaisesRegex(ValueError,'Duplicate' if duplicate else 'Incomplete 10-job'):
                    s.summarize(self.root,self.root,self.root/'out',{v:self.root for v in (1,2,3)})


if __name__=='__main__':unittest.main()
