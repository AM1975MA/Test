"""Synthetic controls, query-weight integrity and distinct decision thresholds."""
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
from compact21_blockbag_v1 import summarize as s
from compact21_blockbag_v1 import run
from compact21_semidev_v1.tests import test_summary as fixture_module


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        fixture_module.AnnualValidationTests.setUp(self)
        self.r['line']=s.LINE;self.r['variant']=s.VARIANT;self.r['status']=s.LINE+'_COMPLETE'
        self.r['WEIGHTED_PARITY_PASS']=True
        a=self.r['per_year']['2017'];a.pop('view_audit')
        self.r.pop('build_protocol_sha256')
        self.r['input_contract'].update(line=s.LINE,train_cohorts='original_native_frozen',changed_columns=[],recipe=s.RECIPE)
        self.r['input_contract'].pop('raw_contract_sha256')
        for name in s.FILES[:2]:self.frames[name]['pred']=self.frames[name]['pred'].astype(np.float32)
        for index,old in ((4,self.base['native']),(5,self.base['common'])):
            name=s.FILES[index];self.frames[name]=old.copy();(self.root/name).write_bytes(name.encode())
            self.r['files_sha256'][name]=s.sha(self.root/name)
        dates=pd.date_range('2012-01-31',periods=60,freq='ME')
        train=pd.DataFrame([(d,t) for d in dates for t in self.base['native'].ticker.unique()],columns=['signal_date','ticker'])
        self.trains={v:train.copy() for v in (1,2,3)}
        dates,sizes,weights,a['weights_audit']=run.query_contract(self.trains,2017)
        np.savez(self.root/'WEIGHTS.npz',query_dates=dates,group_sizes=sizes,weights=weights)
        self.r['files_sha256']['WEIGHTS.npz']=s.sha(self.root/'WEIGHTS.npz')
        a['weighted_control_transforms']={};a['weighted_control']={}
        retained_bags={}
        for v in (1,2,3):
            key=str(v);old=self.base['result']['per_year']['2017']['transforms'][key]
            old['model_params']=dict(n_estimators=360,threads=1,seeds=[101,202,303])
            old['test_matrix_sha256']=['common','native'];old['kind']='BASE'
            a['control_transforms'][key]=deepcopy(old)
            wc=deepcopy(old);wc['group_weights_sha256']=s.array_hash(np.ones(60,dtype=np.float64))
            a['weighted_control_transforms'][key]=wc
            a['weighted_control'][key]=dict(common_bytes_exact=True,native_bytes_exact=True,learned_audit_exact=True,four_bag_aggregate_bytes_exact=True)
            candidate=deepcopy(old);candidate['kind']=s.VARIANT
            candidate['model_params']=dict(recipe=deepcopy(s.RECIPE),canonical=deepcopy(old['model_params']))
            candidate['bags']={};candidate['bag_prediction_sha256']={}
            candidate['group_weights_sha256']=[s.array_hash(w) for w in weights]
            for b,w in enumerate(weights):
                bag=deepcopy(old);bag['group_weights_sha256']=s.array_hash(w)
                bag['prediction_sha256']=[s.array_hash(self.frames[name].loc[self.frames[name].vintage==v,'pred'].to_numpy()) for name in (s.FILES[1],s.FILES[0])]
                bag['seed_prediction_sha256']={str(seed):'synthetic' for seed in (101,202,303)}
                candidate['bags'][str(b)]=bag;candidate['bag_prediction_sha256'][str(b)]=bag['prediction_sha256']
            candidate['prediction_sha256']=[s.array_hash(self.frames[name].loc[self.frames[name].vintage==v,'pred'].to_numpy()) for name in (s.FILES[1],s.FILES[0])]
            a['transforms'][key]=candidate
            a['independent_refits'][key]['refit_audit']=deepcopy(candidate)
            a['independent_refits'][key]['prediction_sha256']=deepcopy(candidate['prediction_sha256'])
            combined=np.concatenate([self.frames[name].loc[self.frames[name].vintage==v,'pred'].to_numpy() for name in (s.FILES[1],s.FILES[0])])
            retained_bags[f'predictions_{v}']=np.stack([combined]*4)
        np.savez(self.root/'BAG_PREDICTIONS.npz',**retained_bags)
        self.r['files_sha256']['BAG_PREDICTIONS.npz']=s.sha(self.root/'BAG_PREDICTIONS.npz')

    def call(self):
        self.path.write_text(json.dumps(self.r,allow_nan=False))
        with patch.object(s.pd,'read_parquet',side_effect=lambda p:self.frames[Path(p).name].copy()),patch.object(s,'select_original_frames',return_value=(self.trains,{},None)):
            return s.load_year(self.path,self.base,{})

    def test_valid_retained_job_with_both_controls(self):
        self.assertEqual(self.call()['year'],2017)

    def test_original_and_weighted_control_bits_preserved(self):
        for name in (s.FILES[2],s.FILES[4]):
            saved=self.frames[name].copy();self.frames[name].loc[0,'pred']=-0.
            with self.assertRaisesRegex(ValueError,'float bits'):self.call()
            self.frames[name]=saved

    def test_future_label_signed_zero_bits_preserved(self):
        self.frames[s.FILES[0]].loc[0,'target_ret_21']=-0.
        with self.assertRaisesRegex(ValueError,'float bits'):self.call()

    def test_control_refit_weight_or_recipe_tampering_rejected(self):
        original=deepcopy(self.r)
        for kind in ('control','refit','ones','bag','recipe','numeric','source','maturity'):
            with self.subTest(kind=kind):
                self.r=deepcopy(original);a=self.r['per_year']['2017']
                if kind=='control':a['weighted_control']['1']['common_bytes_exact']=False
                elif kind=='refit':a['independent_refits']['1']['refit_audit']['kind']='changed'
                elif kind=='ones':a['weighted_control_transforms']['1']['group_weights_sha256']='changed'
                elif kind=='bag':a['transforms']['1']['bags']['0']['group_weights_sha256']='changed'
                elif kind=='recipe':self.r['input_contract']['recipe']['bags']=5
                elif kind=='numeric':self.r['numeric_contract']['pandas']='changed'
                elif kind=='source':self.r['fit_sources'][s.FIT_SOURCES[0]]='changed'
                else:a['transforms']['1']['max_exit_date_21']='NaT'
                with self.assertRaises(ValueError):self.call()

    def test_npz_cannot_change_even_with_redeclared_file_digest(self):
        with np.load(self.root/'WEIGHTS.npz') as z:values={k:z[k].copy() for k in z.files}
        values['weights'][0,0]+=1
        np.savez(self.root/'WEIGHTS.npz',**values);self.r['files_sha256']['WEIGHTS.npz']=s.sha(self.root/'WEIGHTS.npz')
        with self.assertRaisesRegex(ValueError,'Weights/query/group'):self.call()

    def test_ensemble_must_match_physical_bag_mean(self):
        with np.load(self.root/'BAG_PREDICTIONS.npz') as z:values={k:z[k].copy() for k in z.files}
        values['predictions_1'][0,0]+=1
        np.savez(self.root/'BAG_PREDICTIONS.npz',**values)
        self.r['files_sha256']['BAG_PREDICTIONS.npz']=s.sha(self.root/'BAG_PREDICTIONS.npz')
        with self.assertRaisesRegex(ValueError,'registered bag mean'):self.call()

    def test_same_group_sizes_do_not_allow_different_training_tickers(self):
        self.trains[3].loc[0,'ticker']='OTHER'
        with self.assertRaises(ValueError):self.call()

    def test_declared_query_hashes_not_trusted(self):
        self.r['per_year']['2017']['weights_audit']['query_dates_sha256']='changed'
        with self.assertRaisesRegex(ValueError,'Declared weight'):self.call()

    def test_canonical_parameters_are_not_tunable(self):
        a=self.r['per_year']['2017'];a['transforms']['1']['bags']['0']['model_params']['n_estimators']=361
        with self.assertRaises(ValueError):self.call()

    def test_incomplete_annual_matrix_rejected(self):
        job=self.call()
        with patch.object(s,'load_variant',return_value=self.base),patch.object(s,'sha',return_value='synthetic'),patch.object(s,'FROZEN_TI',{str(v):'synthetic' for v in (1,2,3)}),patch.object(s,'load',return_value=None),patch.object(s,'load_year',return_value=job):
            with self.assertRaisesRegex(ValueError,'Incomplete 10-job'):
                s.summarize(self.root,self.root,self.root/'out',{v:self.root for v in (1,2,3)})

    def test_duplicate_annual_job_rejected(self):
        job=self.call();duplicate=self.root/'duplicate';duplicate.mkdir()
        (duplicate/'RESULT.json').write_text(json.dumps(self.r))
        with patch.object(s,'load_variant',return_value=self.base),patch.object(s,'sha',return_value='synthetic'),patch.object(s,'FROZEN_TI',{str(v):'synthetic' for v in (1,2,3)}),patch.object(s,'load',return_value=None),patch.object(s,'load_year',return_value=job):
            with self.assertRaisesRegex(ValueError,'Duplicate annual'):
                s.summarize(self.root,self.root,self.root/'out',{v:self.root for v in (1,2,3)})


class GateTests(unittest.TestCase):
    def fixture(self):
        ev=dict(aggregate_by_date=dict(top1_realized_percentile=.6,top5_overlap=.2),
            per_date=[dict(vintage=v,top1_realized_percentile=.6) for v in ('1','2','3')])
        paired=dict(difference=dict(top1_realized_percentile=0),bootstrap={'3':{'intervals_95pct':{'top1_realized_percentile':dict(lower95_one_sided=-.01,lower98_75_one_sided=-.02)}}})
        def stability(mad,flip):
            return dict(mean=dict(rank_mad=mad,top1_disagreement=flip),pairs={p:dict(mean=dict(rank_mad=mad,top1_disagreement=flip)) for p in ('1-2','1-3','2-3')})
        return ev,deepcopy(ev),paired,stability(.004,.04),stability(.004,.04),stability(.05,.5),stability(.05,.5)

    def test_repeatable_similar_is_distinct_from_strict_improvement(self):
        r=s.decision_gates(*self.fixture())
        self.assertTrue(r['STABLE_WITH_CONSERVED_QUALITY']);self.assertFalse(r['FULL_IMPROVEMENT'])
        self.assertFalse(r['production_adoption'])

    def test_pilot_is_not_resolution(self):
        args=list(self.fixture())
        for st in args[3:5]:
            st['mean']['rank_mad']=.02;st['mean']['top1_disagreement']=.2
            for p in st['pairs'].values():p['mean'].update(rank_mad=.02,top1_disagreement=.2)
        r=s.decision_gates(*args)
        self.assertTrue(r['STABILITY_PILOT_PASS']);self.assertFalse(r['NEAR_REPEATABILITY_PASS'])

    def test_operational_threshold_eachpair_not_average_only(self):
        args=list(self.fixture());args[3]['pairs']['1-2']['mean']['rank_mad']=.006
        self.assertFalse(s.decision_gates(*args)['NEAR_REPEATABILITY_PASS'])
        args=list(self.fixture());args[4]['pairs']['1-2']['mean']['top1_disagreement']=.051
        self.assertFalse(s.decision_gates(*args)['NEAR_REPEATABILITY_PASS'])

    def test_quality_uncertainty_bound_strict(self):
        args=list(self.fixture());args[2]['bootstrap']['3']['intervals_95pct']['top1_realized_percentile']['lower95_one_sided']=-.03
        self.assertFalse(s.decision_gates(*args)['QUALITY_CONSERVATION_PASS'])

    def test_each_vintage_primary_guard(self):
        args=list(self.fixture());args[0]['per_date'][0]['top1_realized_percentile']=.56
        self.assertFalse(s.decision_gates(*args)['QUALITY_CONSERVATION_PASS'])

    def test_integrity_failure_blocks_every_classification(self):
        r=s.decision_gates(*self.fixture(),controls=False)
        for name in ('STABILITY_PILOT_PASS','NEAR_REPEATABILITY_PASS','QUALITY_CONSERVATION_PASS','FULL_IMPROVEMENT'):
            self.assertFalse(r[name])


if __name__=='__main__':unittest.main()
