"""Synthetic policy, execution, saved-fit and artifact-contract regression tests."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent/'olc111/src'))
import run_olc111 as previous
from replay_engine import simulate


def load_module():
    path = ROOT/'src/run_monthly_reset.py'
    assert path.exists(), 'OLC113 monthly reset runner has not been implemented'
    spec = importlib.util.spec_from_file_location('monthly_reset_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConstantModel:
    def __init__(self, value, dimensions):
        self.value = value
        self.transforms = {'price_scaler':dict(active=[True]*dimensions,
                                              mean=[0.]*dimensions, scale=[1.]*dimensions)}

    def predict(self, *args):
        return dict(mean=self.value, lower=self.value)


class ToyCache:
    def __init__(self, entry=-.01, cash=-.01, missing=None):
        self.models = {}
        for head, value in [('CASH',cash), ('FRESH',-.01), ('ENTRY',entry)]:
            self.models[head] = None if head == missing else dict(
                models={a:ConstantModel(value,5 if head=='ENTRY' else 6) for a in previous.LEARNED_ARMS},
                hashes={a:'synthetic-'+a for a in previous.LEARNED_ARMS})

    def cutoff(self, k):
        return 299

    def get(self, k):
        return self.models


class MonthlyResetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('reset_toy_core', ROOT.parent/'olc110/source/src/core.py')
        cls.core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.core)

    def setUp(self):
        dates = pd.bdate_range('2019-01-01', periods=340)
        panel = dict(dates=dates, names=np.array(['A','B']), O=np.full((340,2),100.),
                     C=np.full((340,2),100.), observed=np.ones((340,2),bool), benchmark=0)
        monthly = np.zeros(340,bool); monthly[300]=True
        self.bundle = dict(panel=panel, f=self.core.features(panel), core=self.core,
                           monthly=monthly, feature_monthly=monthly.copy(),
                           targets=np.tile([0.,1.],(340,1)), breadth=np.full(340,.5), begin=300,
                           cboe=dict(available=np.ones(340,bool),legacy=np.zeros((340,2)),term=np.zeros((340,2))))

    def context(self, cash=False, **overrides):
        context = dict(initial=False, scheduled=True, units=np.array([0.,0.]) if cash else np.array([50.,0.]),
                       cash=10000. if cash else 5000., nav=10000., pending=None, queued=(),
                       last_buy_idx=np.array([-1,-1]) if cash else np.array([280,-1]),
                       last_sell_idx=np.array([-1,-1]))
        context.update(overrides)
        return context

    def simulate(self, policy, *, cash=True, end=303):
        return simulate(self.bundle['panel'], self.bundle['f'],lambda k,w:self.bundle['targets'][k],
                        self.bundle['monthly'], legacy=self.core, account_policy=policy,
                        initial_state=dict(units=[0.,0.] if cash else [49.5,50.5], cash=10000. if cash else 0.),
                        issue_initial=False, allow_scheduled_hold=True,
                        start=str(self.bundle['panel']['dates'][300]), end=str(self.bundle['panel']['dates'][end]))

    def test_negative_entry_cannot_veto_scheduled_cash_reset(self):
        m=load_module(); policy=m.ResetOverlay(self.bundle,'PRICE_RESET',ToyCache())
        out=policy(300,np.zeros(2),self.context(cash=True))
        np.testing.assert_array_equal(out['weights'],[0.,1.])
        self.assertEqual(out['reason'],'SCHEDULED'); self.assertFalse(out['force'])
        self.assertEqual(out['meta']['underlying_arm'],'PRICE')
        self.assertEqual(policy.trace[-1]['status'],'MONTHLY_BASELINE_RESET')
        self.assertTrue(policy.trace[-1]['monthly_cash_reset'])
        self.assertTrue(out['meta']['monthly_cash_reset'])

    def test_invested_reset_suppresses_same_close_exit(self):
        m=load_module(); policy=m.ResetOverlay(self.bundle,'TERM_RESET',ToyCache(cash=.01))
        out=policy(300,np.array([.5,0.]),self.context())
        self.assertEqual(out['reason'],'SCHEDULED'); self.assertFalse(out['force'])
        self.assertFalse(policy.trace[-1]['monthly_cash_reset'])

    def test_reset_waits_for_next_accepted_bar_and_reports_actual_fills(self):
        m=load_module(); self.bundle['panel']['observed'][301,1]=False
        policy=m.ResetOverlay(self.bundle,'PRICE_RESET',ToyCache())
        result=self.simulate(policy)
        self.assertEqual(result['daily'].iloc[0].gross,0.)
        self.assertEqual(result['daily'].iloc[1].gross,0.)
        self.assertEqual(result['orders'].execution_idx.tolist(),[302])
        self.assertEqual(result['orders'].signal_idx.tolist(),[300])
        counts=m.monthly_reset_metrics(result)
        self.assertEqual(counts['monthly_cash_reset_instructions'],1)
        self.assertEqual(counts['monthly_cash_reset_realized_instructions'],1)
        self.assertEqual(counts['monthly_cash_reset_unfilled_instructions'],0)
        self.assertEqual(result['orders'].reason.tolist(),['SCHEDULED'])

    def test_unavailable_reset_is_not_counted_as_realized_entry(self):
        m=load_module(); self.bundle['panel']['observed'][301:,1]=False
        result=self.simulate(m.ResetOverlay(self.bundle,'PRICE_RESET',ToyCache()))
        counts=m.monthly_reset_metrics(result)
        self.assertEqual(counts['monthly_cash_reset_instructions'],1)
        self.assertEqual(counts['monthly_cash_reset_realized_instructions'],0)
        self.assertEqual(counts['monthly_cash_reset_unfilled_instructions'],1)
        self.assertTrue(result['orders'].empty)

    def test_original_three_percent_band_is_preserved(self):
        m=load_module(); self.bundle['targets'][:]=[.5,.5]
        result=self.simulate(m.ResetOverlay(self.bundle,'PRICE_RESET',ToyCache()),cash=False)
        self.assertTrue(result['orders'].empty)
        self.assertEqual(result['daily'].nav_close.iloc[-1],10000.)

    def test_pending_and_queued_monthly_instructions_are_untouched(self):
        m=load_module()
        for cash in (True,False):
            for field in ('pending','queued'):
                context=self.context(cash=cash,**{field:({'due_idx':301} if field=='pending' else ({'due_idx':301},))})
                before=deepcopy(context)
                policy=m.ResetOverlay(self.bundle,'PRICE_RESET',ToyCache(entry=.01,cash=.01))
                self.assertIsNone(policy(300,np.zeros(2) if cash else np.array([.5,0.]),context))
                self.assertEqual(policy.trace[-1]['status'],'BUSY')
                self.assertEqual(context[field],before[field])

    def test_nonscheduled_predictions_and_targets_match_parent(self):
        m=load_module()
        for cash,entry,exit_value in [(True,-.01,-.01),(True,.01,-.01),(False,-.01,.01)]:
            cache=ToyCache(entry=entry,cash=exit_value)
            old=previous.AccountPolicy(self.bundle,'TERM',cache)
            new=m.ResetOverlay(self.bundle,'TERM_RESET',cache)
            context=self.context(cash=cash,scheduled=False)
            weights=np.zeros(2) if cash else np.array([.5,0.])
            a=old(300,weights,context); b=new(300,weights,context)
            if a is None:self.assertIsNone(b)
            else:
                np.testing.assert_array_equal(a['weights'],b['weights'])
                self.assertEqual(a['reason'],b['reason']);self.assertEqual(a['force'],b['force'])
                self.assertEqual(a['meta']['predictions'],b['meta']['predictions'])
            for head in previous.HEADS:
                for suffix in ('mean','lower','model_arm','model_sha256'):
                    self.assertEqual(old.trace[-1][head.lower()+'_'+suffix],new.trace[-1][head.lower()+'_'+suffix])

    def test_initial_and_partial_warmup_match_parent(self):
        m=load_module()
        for initial,scheduled,missing in [(True,True,None),(False,True,'ENTRY'),(False,False,'CASH')]:
            cache=ToyCache(missing=missing)
            old=previous.AccountPolicy(self.bundle,'PRICE',cache);new=m.ResetOverlay(self.bundle,'PRICE_RESET',cache)
            context=self.context(cash=True,initial=initial,scheduled=scheduled)
            a=old(300,np.zeros(2),context);b=new(300,np.zeros(2),context)
            if a is None:self.assertIsNone(b)
            else:
                np.testing.assert_array_equal(a['weights'],b['weights'])
                self.assertEqual(a['reason'],b['reason']);self.assertEqual(a['force'],b['force'])
            self.assertEqual(old.trace[-1]['status'],new.trace[-1]['status'])

    def test_missing_saved_fit_never_calls_fit_head(self):
        m=load_module()
        with tempfile.TemporaryDirectory() as folder, patch.object(previous,'fit_head',side_effect=AssertionError('REFIT_SENTINEL')) as sentinel:
            cache=m.SavedOnlyFitCache({},self.bundle['panel']['dates'],300,folder=folder,provenance='test')
            with self.assertRaisesRegex(ValueError,'SAVED_MODEL_MISSING_REFIT_FORBIDDEN'):cache.prepare()
            sentinel.assert_not_called()

    def test_saved_fit_loader_preserves_real_models_without_refitting(self):
        m=load_module()
        with tempfile.TemporaryDirectory() as folder:
            # Use existing saved model bytes, without creating or fitting any model.
            saved=sorted((ROOT.parent/'olc111/results/FITS').glob('FIT_*.json.gz'))[-1]
            stored=previous._read_json(saved);cutoff=stored['cutoff']
            dates=pd.bdate_range('2000-01-01',periods=max(cutoff+2,300))
            cache=m.SavedOnlyFitCache({},dates,cutoff+1,folder=folder,provenance=stored['provenance'])
            target=Path(folder)/saved.name;target.write_bytes(saved.read_bytes())
            with patch.object(previous,'fit_head',side_effect=AssertionError('REFIT_SENTINEL')):
                value=cache.get(cutoff)
                self.assertEqual(set(value),set(previous.HEADS))
                self.assertTrue(all(value[head] is not None for head in previous.HEADS))
                target.unlink()
                self.assertIs(cache.get(cutoff),value)

    def test_baseline_parity_checks_exact_daily_and_entire_order_ledger(self):
        m=load_module()
        result=self.simulate(previous.AccountPolicy(self.bundle,'BASE',ToyCache()))
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'olc111';control=source/'results/BASE__NEXT_CLOSE';control.mkdir(parents=True)
            previous._csv(result['daily'],control/'DAILY.csv.gz');previous._csv(result['orders'],control/'ORDERS.csv.gz')
            out=Path(folder)/'out';out.mkdir()
            receipt=m.compare_mean_with_base(source,'NEXT_CLOSE',result,out)
            self.assertTrue(receipt['exact_baseline_parity']);self.assertTrue(receipt['exact_order_ledger_parity'])
            for field in ('nav_close','k'):
                changed=deepcopy(result);changed['daily'].loc[0,field]+=1e-10 if field=='nav_close' else 1
                with self.assertRaisesRegex(AssertionError,'BASE_PARITY'):m.compare_mean_with_base(source,'NEXT_CLOSE',changed,out)
            changed=deepcopy(result);changed['orders'].loc[0,'ticker']='DIFFERENT'
            with self.assertRaisesRegex(AssertionError,'BASE_PARITY'):m.compare_mean_with_base(source,'NEXT_CLOSE',changed,out)

    def test_receipts_precede_completion_marker_and_resume_rejects_corruption(self):
        m=load_module();result=self.simulate(previous.AccountPolicy(self.bundle,'BASE',ToyCache()))
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);source=folder/'source';control=source/'results/BASE__NEXT_CLOSE';control.mkdir(parents=True)
            previous._csv(result['daily'],control/'DAILY.csv.gz');previous._csv(result['orders'],control/'ORDERS.csv.gz')
            output=folder/'output';policy=m.ResetOverlay(self.bundle,'MEAN_RESET',ToyCache());self.simulate(policy)
            metrics=dict(path_id='MEAN_RESET__NEXT_CLOSE',arm='MEAN_RESET',scenario='NEXT_CLOSE')
            original_write=previous._write_json
            def observe(path,value):
                if Path(path)==output/'METRICS.json':
                    self.assertTrue((output/'MEAN_BASE_REPLICATION.json').exists())
                    self.assertTrue((output/'PATH_RECEIPT.json').exists())
                return original_write(path,value)
            with patch.object(previous,'_write_json',side_effect=observe):m.save_completed_path(output,result,policy.trace,metrics,source)
            m.load_completed_path(output,source,'MEAN_RESET','NEXT_CLOSE')
            (output/'MEAN_BASE_REPLICATION.json').unlink()
            with self.assertRaisesRegex(ValueError,'INCOMPLETE|RECEIPT'):m.load_completed_path(output,source,'MEAN_RESET','NEXT_CLOSE')

    def test_resume_rejects_changed_metrics_even_when_data_are_intact(self):
        m=load_module();result=self.simulate(previous.AccountPolicy(self.bundle,'BASE',ToyCache()))
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'output'
            metrics=dict(path_id='PRICE_RESET__NEXT_CLOSE',arm='PRICE_RESET',scenario='NEXT_CLOSE',cagr=.01)
            m.save_completed_path(output,result,[],metrics,Path(folder))
            saved=previous._read_json(output/'METRICS.json');saved['cagr']=999.
            previous._write_json(output/'METRICS.json',saved)
            with self.assertRaisesRegex(ValueError,'METRICS_RECEIPT_MISMATCH'):
                m.load_completed_path(output,Path(folder),'PRICE_RESET','NEXT_CLOSE')

    def test_synthetic_twelve_path_run_and_resume_do_not_refit_or_reexecute(self):
        m=load_module(); self.bundle['bank']={}
        readiness=dict(postwarmup_start_idx=300)
        cache=ToyCache();cache.prepare=lambda:readiness
        freeze=dict(code_hashes={},input_hashes={})
        with tempfile.TemporaryDirectory() as folder:
            parent=Path(folder);root=parent/'olc113';source=parent/'olc111'
            for study in (root,source):(study/'docs').mkdir(parents=True)
            (root/'docs/EXPERIMENT_FREEZE.json').write_text('{}')
            (source/'docs/EXPERIMENT_FREEZE.json').write_text('{}')
            (source/'results').mkdir();previous._write_json(source/'results/FIT_READINESS.json',readiness)
            for scenario,(ticket,impact,fill) in m.SCENARIOS.items():
                panel=m.execution_panel(self.bundle['panel'],fill)
                base=simulate(panel,self.bundle['f'],lambda k,w:self.bundle['targets'][k],
                    self.bundle['monthly'],legacy=self.core,
                    account_policy=previous.AccountPolicy(self.bundle,'BASE',cache),
                    allow_scheduled_hold=True,ticket=ticket,impact=impact,
                    start=str(panel['dates'][300].date()),end=str(panel['dates'][-1].date()))
                control=source/'results'/f'BASE__{scenario}';control.mkdir()
                previous._csv(base['daily'],control/'DAILY.csv.gz');previous._csv(base['orders'],control/'ORDERS.csv.gz')
            with patch.object(m,'verify_freeze',return_value=freeze), patch.object(m,'build_research_bundle',return_value=self.bundle), patch.object(m,'SavedOnlyFitCache',return_value=cache), patch.object(previous,'fit_head',side_effect=AssertionError('REFIT_SENTINEL')) as sentinel:
                manifest=m.run(root)
                self.assertEqual(manifest['completed_paths'],12)
                self.assertEqual(len(list((root/'results').glob('*__*/METRICS.json'))),12)
                with patch.object(m,'simulate',side_effect=AssertionError('REEXECUTION_SENTINEL')):
                    resumed=m.run(root,resume=True)
                self.assertEqual(resumed['completed_path_ids'],manifest['completed_path_ids'])
                sentinel.assert_not_called()
                damaged=root/'results/PRICE_RESET__NEXT_CLOSE/POLICY_TRACE.csv.gz'
                damaged.write_bytes(b'corrupted')
                with self.assertRaisesRegex(ValueError,'PATH_RECEIPT_HASH_MISMATCH'):
                    m.run(root,resume=True)

    def test_freeze_is_required_before_bundle_or_financial_simulation(self):
        m=load_module()
        with tempfile.TemporaryDirectory() as folder, patch.object(m,'build_research_bundle') as build, patch.object(m,'simulate') as replay:
            with self.assertRaises(FileNotFoundError):m.run(folder)
            build.assert_not_called();replay.assert_not_called()


if __name__=='__main__':unittest.main()
