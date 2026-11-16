"""Integration boundaries for finite plans; only synthetic data."""
from pathlib import Path
import importlib
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT/'src/run_cycles.py').exists(), 'runner implementation missing')
        self.r=importlib.import_module('run_cycles')

    def test_strict_qualification_and_ties_use_isin(self):
        p=[dict(head='REDEPLOY',asset=0,mean=.1,lower=.02),
           dict(head='PARK',asset=1,mean=.1,lower=.02),
           dict(head='PARK',asset=2,mean=.1,lower=.02),
           dict(head='PARK',asset=3,mean=0.,lower=.5)]
        best=self.r.select_plan(p,np.array(['Z','Y','A','B']))
        self.assertEqual((best['head'],best['asset']),('PARK',2))
        self.assertIsNone(self.r.select_plan([dict(head='PARK',asset=0,mean=.1,lower=0.)],['A']))

    def synthetic_bank(self):
        dates=pd.bdate_range('2020-01-01',periods=170)
        signal=np.arange(2,120,dtype=int)
        rng=np.random.default_rng(51)
        bank={head:dict(X=rng.normal(size=(len(signal),dim)),y=rng.normal(0,.02,len(signal)),
                       signal_idx=signal,terminal_idx=signal+42,asset_idx=np.zeros(len(signal),int))
              for head,dim in [('PARK',8),('REDEPLOY',12)]}
        return dates,bank

    def test_monthly_cache_portable_and_future_invariant(self):
        dates,bank=self.synthetic_bank()
        options=dict(min_dates=3,min_months=1,min_blocks=1,n_boot=2)
        with tempfile.TemporaryDirectory() as folder:
            a=self.r.MonthlyCycleCache(bank,dates,2,folder=folder,provenance='test',
                                      fit_options=options,min_activation_idx=80)
            fit=a.get(90);cutoff=a.cutoff(90)
            self.assertTrue(all(fit[h]['meta']['max_terminal_idx']<cutoff for h in self.r.HEADS))
            stored={h:fit[h]['hashes'] for h in self.r.HEADS}
            with patch.object(self.r,'fit_head',side_effect=AssertionError('cache refit')):
                b=self.r.MonthlyCycleCache(bank,dates,2,folder=folder,provenance='test',
                                          fit_options=options,min_activation_idx=80)
                self.assertEqual(stored,{h:b.get(90)[h]['hashes'] for h in self.r.HEADS})
            for head in self.r.HEADS:
                bank[head]['y'][bank[head]['terminal_idx']>=cutoff]=999.
            c=self.r.MonthlyCycleCache(bank,dates,2,fit_options=options,min_activation_idx=80)
            self.assertEqual(stored,{h:c.get(90)[h]['hashes'] for h in self.r.HEADS})

    def test_readiness_obeys_minimum_activation_and_own_cutoff(self):
        dates,bank=self.synthetic_bank()
        c=self.r.MonthlyCycleCache(bank,dates,2,fit_options=dict(min_dates=3,min_months=1,min_blocks=1,n_boot=2),
                                  min_activation_idx=110)
        ready=c.prepare()
        self.assertLess(ready['raw_all_heads_first_ready_idx'],110)
        self.assertEqual(ready['all_heads_first_ready_idx'],110)
        self.assertEqual(ready['postwarmup_start_idx'],111)
        self.assertEqual(c.cutoff(90),87)

    def test_cache_tamper_does_not_silently_load(self):
        dates,bank=self.synthetic_bank()
        with tempfile.TemporaryDirectory() as folder:
            kw=dict(folder=folder,provenance='test',fit_options=dict(min_dates=3,min_months=1,min_blocks=1,n_boot=2))
            c=self.r.MonthlyCycleCache(bank,dates,2,**kw);c.get(90)
            path=Path(folder)/f'FIT_{c.cutoff(90):06d}.json.gz'
            raw=self.r.previous._read_json(path);raw['heads']['PARK']['meta']['max_terminal_idx']=999
            self.r.previous._write_json(path,raw)
            d=self.r.MonthlyCycleCache(bank,dates,2,**kw)
            with self.assertRaisesRegex(ValueError,'FIT_CACHE'):
                d.get(90)

    def make_policy(self,arm='TREE_CYCLE'):
        from test_cycle_core import PlanFixture
        f=PlanFixture();f.setUp()
        class Model:
            def predict(self,x):return dict(mean=.02,lower=.01)
        fitted={head:dict(models={name:Model() for name in ('MEAN','RIDGE','TREE')},
                          hashes={name:'toy-'+name for name in ('MEAN','RIDGE','TREE')},
                          meta=dict(scaler=dict(mean=[0]*dim,scale=[1]*dim),feature_min=[-10]*dim,feature_max=[10]*dim))
                for head,dim in [('PARK',8),('REDEPLOY',12)]}
        class Cache:
            min_activation_idx=299
            def cutoff(self,k):return 280
            def get(self,k):return fitted
        return f,self.r.CyclePolicy(f.b,arm,Cache())

    def test_policy_one_plan_until_handoff_and_exact_targets(self):
        f,p=self.make_policy()
        result=f.run_engine(account_policy=p)
        first=[d for d in result['decisions'] if d['reason'].endswith('_SALE')][0]
        self.assertEqual(first['k'],300)
        plans=p.export_plans()
        self.assertEqual(plans[0]['handoff_idx'],310)
        self.assertTrue(all(q['signal_idx']>=310 for q in plans[1:]))
        scheduled=[d for d in result['decisions'] if d['k']==310][0]
        np.testing.assert_array_equal(scheduled['raw_weights'],f.b['targets'][310])
        self.assertFalse(scheduled['force'])

    def test_policy_scheduled_target_even_while_busy(self):
        f,p=self.make_policy()
        f.p['observed'][301:315,0]=False
        result=f.run_engine(account_policy=p)
        scheduled=[d for d in result['decisions'] if d['k']==310]
        self.assertEqual(len(scheduled),1)
        self.assertEqual(scheduled[0]['reason'],'SCHEDULED')
        self.assertEqual(p.export_plans()[0]['handoff_idx'],310)

    def test_live_redeploy_uses_shared_executor_and_no_second_plan(self):
        f,p=self.make_policy()
        fitted=p.fit_cache.get(300)
        class RedeployOnly:
            def predict(self,x):return dict(mean=.02 if len(x)==12 else -.01,lower=.01 if len(x)==12 else -.02)
        for head in self.r.HEADS:fitted[head]['models']['TREE']=RedeployOnly()
        result=f.run_engine(account_policy=p)
        first=p.export_plans()[0]
        self.assertEqual(first['head'],'REDEPLOY')
        self.assertEqual(first['signal_idx'],300)
        self.assertEqual(first['sale_complete_idx'],301)
        self.assertEqual(first['entry_attempt_idx'],305)
        self.assertEqual(first['handoff_idx'],310)
        entry=result['orders'].query("reason == 'REDEPLOY_ENTRY'").iloc[0]
        self.assertEqual(entry.execution_idx,306)
        self.assertTrue(all(q['signal_idx']>310 for q in p.export_plans()[1:]))

    def test_controls_match_legacy_policy(self):
        from test_cycle_core import PlanFixture
        f=PlanFixture();f.setUp()
        class Cache:
            def cutoff(self,k):return 280
            def get(self,k):raise AssertionError('control must not fit')
        p=self.r.CyclePolicy(f.b,'BASE',Cache())
        actual=f.run_engine(account_policy=p)
        expected=f.run_engine()
        pd.testing.assert_frame_equal(actual['daily'],expected['daily'],check_exact=True)
        pd.testing.assert_frame_equal(actual['orders'],expected['orders'],check_exact=True)

    def test_path_receipt_rejects_changed_artifact_and_metrics(self):
        f,p=self.make_policy('BASE')
        result=f.run_engine(account_policy=p)
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            metrics=dict(arm='BASE',scenario='NEXT_CLOSE',path_id='BASE__NEXT_CLOSE',cagr=.01)
            self.r.save_completed_path(folder,result,p,metrics,'freeze')
            loaded,_=self.r.load_completed_path(folder,'BASE','NEXT_CLOSE','freeze')
            self.assertEqual(loaded['cagr'],.01)
            changed=self.r.previous._read_json(folder/'METRICS.json');changed['cagr']=.5
            self.r.previous._write_json(folder/'METRICS.json',changed)
            with self.assertRaisesRegex(ValueError,'PATH_RECEIPT_METRICS'):
                self.r.load_completed_path(folder,'BASE','NEXT_CLOSE','freeze')
            self.r.previous._write_json(folder/'METRICS.json',loaded)
            (folder/'POLICY_TRACE.csv.gz').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'PATH_RECEIPT'):
                self.r.load_completed_path(folder,'BASE','NEXT_CLOSE','freeze')

if __name__=='__main__':unittest.main()
