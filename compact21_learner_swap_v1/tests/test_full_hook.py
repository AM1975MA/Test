"""Real worker tests on small causal panels; round reduction applies only here."""
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from compact21_learner_swap_v1.run_full_pipeline import make_compact_hook, persist_input_environment_evidence, ENVIRONMENT_GATE_KEYS
from compact21_learner_swap_v1 import learners
from etf_trader.source_only import kernel, models


def fixture():
    rng=np.random.default_rng(501)
    names=['mom21','mom21_pct','mom21_dev']
    rows=[]
    for date in pd.date_range('2015-01-31',periods=20,freq='ME'):
        outcomes=rng.normal(0,.05,9)
        ranks=pd.Series(outcomes).rank(pct=True).to_numpy()
        for j,(outcome,rank) in enumerate(zip(outcomes,ranks)):
            rows.append(dict(signal_date=date,ticker=f'T{j}',
                exit_date_21=date+pd.Timedelta(days=30),exit_date_63=date+pd.Timedelta(days=90),
                target_rank_21=rank,target_rank_63=rank,fwd_ret_21=outcome,
                mom21=rng.normal(0,.1),mom21_pct=(j+1)/9,mom21_dev=rng.normal()))
    frame=pd.DataFrame(rows)
    test=frame.iloc[:9].copy(); test['signal_date']=pd.Timestamp('2017-01-31')
    k=SimpleNamespace(F2D_FEATURES=names,
        COMPACT_PARAMS=dict(kernel.COMPACT_PARAMS,n_estimators=2,min_child_weight=0),
        COMPACT_SEEDS=list(kernel.COMPACT_SEEDS))
    return k,frame,test,pd.Timestamp('2017-01-01')


class FullHookTests(unittest.TestCase):
    def setUp(self):
        self.k,self.frame,self.test,self.cutoff=fixture()
        directory=tempfile.TemporaryDirectory(prefix='learner_full_hook_'); self.addCleanup(directory.cleanup)
        self.root=Path(directory.name)
        env=patch.dict(os.environ,{'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1',
            'ETF_TRADER_XGB_THREADS_PER_WORKER':'1','ETF_TRADER_XGB_WORKERS':'3'})
        env.start();self.addCleanup(env.stop)
        features=patch.object(learners.k,'F2D_FEATURES',self.k.F2D_FEATURES)
        features.start(); self.addCleanup(features.stop)
        # Integration tests still use the actual learner library and same seeds;
        # only compute-budget rounds/minimum sample count are reduced.
        lgbparams=patch.dict(learners.LGBM_PARAMS,{'n_estimators':2,'min_child_samples':2})
        lgbparams.start();self.addCleanup(lgbparams.stop)

    def fit(self,variant,frame=None,name=None):
        frame=self.frame if frame is None else frame
        output=self.root/(name or variant);output.mkdir()
        prediction=make_compact_hook(variant,models)(self.k,frame,self.test,
            pd.Series(True,index=frame.index),self.cutoff,output,2017)[0]
        audit=json.loads((output/'stability_transform_2017.json').read_text())
        return prediction,audit

    def test_base21_and_every63_match_actual_canonical_worker_bytes(self):
        canonical=models._fit_compact_rankers_isolated(self.k,self.frame,self.test,
            pd.Series(True,index=self.frame.index),self.cutoff,self.root,2017)[0]
        for variant in learners.VARIANTS:
            with self.subTest(variant=variant):
                prediction,audit=self.fit(variant)
                self.assertEqual(prediction[63].tobytes(),canonical[63].tobytes())
                if variant=='BASE':self.assertEqual(prediction[21].tobytes(),canonical[21].tobytes())
                self.assertTrue(audit['horizons']['63']['canonical63_input_contract'])
                self.assertTrue(all(x['maturity_ok'] for x in audit['horizons'].values()))
                self.assertFalse(audit['negative_feedback_changed'])
                self.assertEqual(audit['seeds'],[101,202,303])
                self.assertTrue(audit['learner_artifacts_sha256'])

    def test_future_rows_and_outcomes_cannot_change_any_fitted_prediction(self):
        future=self.frame.iloc[:9].copy()
        future['signal_date']=pd.Timestamp('2018-01-31')
        future['exit_date_21']=pd.Timestamp('2018-03-01')
        future['exit_date_63']=pd.Timestamp('2018-05-01')
        future[self.k.F2D_FEATURES]=1e12
        future['target_rank_21']=np.arange(1,10)/9
        future['target_rank_63']=np.arange(1,10)/9
        future['fwd_ret_21']=np.arange(9)*1e8
        frame=pd.concat([self.frame,future],ignore_index=True)
        for variant in learners.VARIANTS:
            with self.subTest(variant=variant):
                before,first=self.fit(variant,name=f'{variant}_before')
                after,last=self.fit(variant,frame,name=f'{variant}_after')
                for horizon in (21,63):
                    self.assertEqual(before[horizon].tobytes(),after[horizon].tobytes())
                    a=dict(first['horizons'][str(horizon)]);b=dict(last['horizons'][str(horizon)])
                    a.pop('fit_seconds',None);b.pop('fit_seconds',None)
                    self.assertEqual(a,b)

    def test_hook_filters_unmatured_labels_at_strict_cutoff(self):
        immature=self.frame.iloc[:9].copy()
        immature['exit_date_21']=self.cutoff
        immature['exit_date_63']=self.cutoff
        immature['signal_date']=pd.Timestamp('2016-12-31')
        immature[self.k.F2D_FEATURES]=1e10
        frame=pd.concat([self.frame,immature],ignore_index=True)
        for variant in learners.VARIANTS:
            with self.subTest(variant=variant):
                _,before=self.fit(variant,name=f'{variant}_mature')
                _,after=self.fit(variant,frame,name=f'{variant}_immature')
                for h in ('21','63'):
                    for key in ('train_rows','Xtr_sha256','y_sha256','groups_sha256','mean_predictions_sha256'):
                        self.assertEqual(before['horizons'][h][key],after['horizons'][h][key])

    def test_shared_learner_rejects_direct_immature_input(self):
        bad=self.frame.copy();bad.loc[bad.index[0],'exit_date_21']=self.cutoff
        for variant in learners.VARIANTS:
            with self.subTest(variant=variant),self.assertRaisesRegex(ValueError,'Immature'):
                learners.fit(bad,[self.test],variant,2017,self.root,variant)


class EnvironmentFailureEvidenceTests(unittest.TestCase):
    def test_blocked_environment_persists_actual_expected_input_before_raise(self):
        with tempfile.TemporaryDirectory(prefix='environment_failure_evidence_') as directory:
            root=Path(directory)
            expected={key:f'frozen_{key}' for key in ENVIRONMENT_GATE_KEYS}
            actual=dict(expected,numpy_build_config={'SIMD Extensions': {'found': ['AVX512F']}})
            contract={'line':'COMPACT21_LEARNER_SWAP_V1','environment':actual}
            report=persist_input_environment_evidence(root,contract,{'environment':expected})
            self.assertFalse(report['passed'])
            self.assertEqual(report['mismatched_keys'],['numpy_build_config'])
            self.assertEqual(json.loads((root/'INPUT_CONTRACT.json').read_text()),contract)
            retained=json.loads((root/'ENVIRONMENT_COMPARISON.json').read_text())
            self.assertEqual(retained['actual']['numpy_build_config'],actual['numpy_build_config'])
            self.assertEqual(retained['expected']['numpy_build_config'],expected['numpy_build_config'])


if __name__=='__main__':unittest.main()
