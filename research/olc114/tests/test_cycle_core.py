"""Synthetic finite-plan and native accounting contracts; no market fits."""
from copy import deepcopy
import importlib.util
import inspect
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import cycle_engine


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


class EngineFixture(unittest.TestCase):
    def setUp(self):
        self.old=load(ROOT.parent/'olc111/src/replay_engine.py','original111')
        self.core=load(ROOT.parent/'olc110/source/src/core.py','core114test')
        self.p=dict(dates=pd.bdate_range('2019-01-01',periods=380),names=np.array(['A','B','C']),
                    O=np.full((380,3),100.),C=np.full((380,3),100.),observed=np.ones((380,3),bool))
        self.f=dict(C=self.p['C'],returns=np.random.default_rng(11).normal(0,.01,(380,3)))
        self.monthly=np.zeros(380,bool);self.monthly[[310,332,353,375]]=True
        self.seed=dict(units=np.array([40.,40.,0.]),cash=2000.)
    def run_engine(self,engine=cycle_engine,**kw):
        return engine.simulate(self.p,self.f,lambda k,w:np.array([.5,.5,0.]),self.monthly,
            legacy=self.core,start=str(self.p['dates'][300].date()),end=str(self.p['dates'][345].date()),**kw)

class EngineTests(EngineFixture):
    def test_default_native_parity(self):
        a=self.run_engine();b=self.run_engine(self.old)
        for key in ('daily','orders','instructions','alerts'):
            pd.testing.assert_frame_equal(a[key],b[key],check_exact=True)
    def test_seeded_targeted_optin_exists(self):
        self.assertIn('allow_initial_targeted',inspect.signature(cycle_engine.simulate).parameters)
    def test_targeted_sale_keeps_other_units_across_gap(self):
        self.p['O'][300:,1]=250.;self.p['C'][300:,1]=250.
        seen=[]
        def cb(k,w,c):
            seen.append(c['units'].copy())
            if c['initial']:return dict(weights=np.zeros(3),action_mask=np.array([True,False,False]),force=True,sell_only=True)
            if c['scheduled']:return dict(weights=w)
        r=self.run_engine(initial_state=self.seed,account_policy=cb,allow_initial_targeted=True)
        self.assertEqual(seen[1][1],40.)
        self.assertEqual(r['orders'].iloc[0]['j'],0)
    def test_optin_requires_seed(self):
        with self.assertRaisesRegex(ValueError,'INITIAL_TARGETED_REQUIRES_SEED'):
            self.run_engine(allow_initial_targeted=True)
    def test_default_and_scheduled_reject_partial_masks(self):
        def cb(k,w,c):return dict(weights=np.zeros(3),action_mask=np.array([True,False,False]))
        with self.assertRaisesRegex(ValueError,'ACCOUNT_SCHEDULED_MASK'):
            self.run_engine(initial_state=self.seed,account_policy=cb)
        with self.assertRaisesRegex(ValueError,'ACCOUNT_SCHEDULED_MASK'):
            self.run_engine(initial_state=self.seed,account_policy=cb,allow_initial_targeted=True)
    def test_wrong_mask_type_rejected(self):
        def cb(k,w,c):return dict(weights=np.zeros(3),action_mask=np.array([1,0,0]))
        with self.assertRaisesRegex(ValueError,'ACTION_MASK'):
            self.run_engine(initial_state=self.seed,account_policy=cb,allow_initial_targeted=True)


class PlanFixture(EngineFixture):
    def setUp(self):
        super().setUp()
        import cycle_core
        self.cc=cycle_core
        weekly=np.zeros(380,bool);weekly[[300,301,305,310,315,320,325,330,335,340,345,350,355,360,365,370,375]]=True
        self.b=dict(panel=self.p,f=self.f,core=self.core,monthly=self.monthly,feature_monthly=self.monthly,
                    weekly=weekly,targets=np.tile([.5,.5,0.],(380,1)),selected_order=[[2,0] for _ in range(380)],begin=300)
    def plan_run(self,head='REDEPLOY',**kwargs):
        plan=self.cc.PlanExecutor(self.b,head,0,299)
        result=self.run_engine(account_policy=plan,initial_state=self.seed,allow_initial_targeted=True,**kwargs)
        return plan,result

class PlanTests(PlanFixture):
    def test_sale_then_strict_weekly_and_actual_cash_entry(self):
        plan,r=self.plan_run()
        self.assertEqual(plan.summary['sale_complete_idx'],300)
        self.assertEqual(plan.summary['entry_attempt_idx'],301)
        buys=r['orders'].query("reason == 'REDEPLOY_ENTRY'")
        self.assertEqual(buys.execution_idx.tolist(),[302])
        entry=[d for d in r['decisions'] if d['reason']=='REDEPLOY_ENTRY'][0]
        self.assertAlmostEqual(entry['raw_weights'][2],entry['cash']/(entry['cash']+entry['units']@self.f['C'][301]))
        self.assertNotAlmostEqual(entry['raw_weights'][2],.5)
        self.assertEqual(plan.summary['handoff_idx'],310)
        self.assertFalse(plan.active)
    def test_delayed_sale_moves_weekly_entry(self):
        self.p['observed'][300:306,0]=False
        plan,r=self.plan_run()
        self.assertEqual(plan.summary['sale_complete_idx'],306)
        self.assertIsNone(plan.summary['entry_attempt_idx'])
        self.assertEqual(plan.summary['handoff_idx'],310)
    def test_lag_one_strictly_after_actual_fill(self):
        plan,r=self.plan_run(lag=1)
        self.assertEqual(plan.summary['sale_complete_idx'],301)
        self.assertEqual(plan.summary['entry_attempt_idx'],305)
        self.assertEqual(r['orders'].query("reason == 'REDEPLOY_ENTRY'").execution_idx.tolist(),[307])
    def test_no_candidate_has_only_one_attempt(self):
        self.b['selected_order'][301]=[1]
        plan,r=self.plan_run()
        self.assertEqual(plan.summary['entry_attempt_idx'],301)
        self.assertIsNone(plan.summary['entry_candidate_idx'])
        self.assertFalse((r['orders'].reason=='REDEPLOY_ENTRY').any())
    def test_handoff_supersedes_unfilled_entry(self):
        self.p['observed'][302:313,2]=False
        plan,r=self.plan_run()
        self.assertEqual(plan.summary['handoff_idx'],310)
        self.assertFalse((r['orders'].reason=='REDEPLOY_ENTRY').any())
        self.assertTrue(any(d['k']==310 and d['reason']=='SCHEDULED' for d in r['decisions']))
    def test_monthly_priority_with_busy_sale(self):
        self.p['observed'][300:315,0]=False
        plan,r=self.plan_run()
        self.assertEqual(plan.summary['handoff_idx'],310)
        self.assertIsNone(plan.summary['entry_attempt_idx'])
        self.assertFalse((r['orders'].reason=='PARK_SALE').any())
    def test_candidate_order_and_retained_correlation(self):
        self.b['selected_order'][299]=[2,0]
        self.assertEqual(self.cc.candidate_for(self.b,299,[1]),2)
        self.f['returns'][:,2]=self.f['returns'][:,1]
        self.assertEqual(self.cc.candidate_for(self.b,299,[1]),0)
    def test_features_exact_dimensions_and_future_invariance(self):
        current=np.array([.4,.4,0.])
        p=self.cc.plan_features(self.b,299,current,10000.,0,'PARK')
        x=self.cc.plan_features(self.b,299,current,10000.,0,'REDEPLOY')
        self.assertEqual(p.shape,(8,));self.assertEqual(x.shape,(12,))
        self.assertAlmostEqual(x[7],.0001);self.assertAlmostEqual(x[11],2/5)
        self.f['returns'][300:]=999
        self.b['selected_order'][300:]=[[1] for _ in range(80)]
        np.testing.assert_array_equal(x,self.cc.plan_features(self.b,299,current,10000.,0,'REDEPLOY'))
    def test_unavailable_candidate_still_valid(self):
        self.b['selected_order'][299]=[1]
        x=self.cc.plan_features(self.b,299,np.array([.4,.4,0]),10000,0,'REDEPLOY')
        np.testing.assert_array_equal(x[8:11],np.zeros(3))
    def test_counterfactual_42_base_matches_frozen_continuation(self):
        self.monthly[299]=False
        r=self.run_engine(initial_state=self.seed,issue_initial=False)
        self.b['baseline_nav']={int(row.k):float(row.nav_close) for row in r['daily'].itertuples()}
        group=self.cc.counterfactual_group(self.b,299,self.seed)
        self.assertEqual(group['status'],'OK')
        self.assertEqual(group['terminal_idx'],341)
        self.assertEqual(len(group['records']),4)
        self.assertLess(group['base_replay_error'],1e-8)
        self.assertTrue(all(row['terminal_idx']==341 for row in group['records']))
    def test_one_branch_stale_mark_censors_entire_group(self):
        self.p['observed'][303:310,2]=False
        group=self.cc.counterfactual_group(self.b,299,self.seed)
        self.assertEqual(group['status'],'CENSORED_STALE_MARK')
        self.assertEqual(group['records'],[])
    def test_missing_seed_mark_is_explicit_censor(self):
        self.f['C'][299,0]=np.nan
        group=self.cc.counterfactual_group(self.b,299,self.seed)
        self.assertEqual(group['status'],'CENSORED_MISSING_MARK')
        self.assertEqual(group['records'],[])
    def test_base_mismatch_stops_instead_of_labeling(self):
        self.b['baseline_nav']={341:1234.}
        with self.assertRaisesRegex(AssertionError,'BASE_REPLAY_MISMATCH'):
            self.cc.counterfactual_group(self.b,299,self.seed)
    def test_partial_sale_waits_for_final_actual_fill(self):
        plan=self.cc.PlanExecutor(self.b,'REDEPLOY',0,299)
        context=dict(units=self.seed['units'].copy(),cash=2000.,nav=10000.,pending=None,queued=(),
                     last_sell_idx=np.full(3,-1),scheduled=False)
        plan(299,np.array([.4,.4,0]),context)
        context.update(units=np.array([10.,40.,0.]),last_sell_idx=np.array([300,-1,-1]))
        self.assertIsNone(plan(301,np.array([.1,.4,0]),context))
        self.assertIsNone(plan.summary['sale_complete_idx'])
        context.update(units=np.array([0.,40.,0.]),last_sell_idx=np.array([305,-1,-1]))
        self.assertIsNone(plan(305,np.array([0.,.4,0]),context))
        self.assertEqual(plan.summary['sale_complete_idx'],305)
        self.assertIsNone(plan.summary['entry_attempt_idx'])
    def test_local_subset_preserves_global_identity(self):
        plan=self.cc.PlanExecutor(self.b,'PARK',1,299,local_ids=[1,2])
        context=dict(units=np.array([40.,0]),cash=6000.,nav=10000.,pending=None,queued=(),
                     last_sell_idx=np.full(2,-1),scheduled=False)
        answer=plan(299,np.array([.4,0]),context)
        np.testing.assert_array_equal(answer['action_mask'],[True,False])
        answer=plan(310,np.array([0.,0]),dict(context,scheduled=True))
        np.testing.assert_array_equal(answer['weights'],[.5,0.])
    def test_reconstruct_selector_order_does_not_sort_global_ids(self):
        def selector(k,w):return np.array([.5,0.,.5]),dict(selected_indices=[2,0])
        targets=np.tile([.5,0.,.5],(380,1))
        order=self.cc.reconstruct_selected_order(self.p,targets,299,selector)
        self.assertEqual(order[299],[2,0])
        targets[300]=[.5,.5,0]
        with self.assertRaisesRegex(AssertionError,'CAUSAL_TARGET_MISMATCH'):
            self.cc.reconstruct_selected_order(self.p,targets,299,selector)
    def test_busy_and_right_edge_are_explicit(self):
        self.assertEqual(self.cc.counterfactual_group(self.b,299,dict(self.seed,busy=True))['status'],'BUSY_STATE')
        self.assertEqual(self.cc.counterfactual_group(self.b,350,self.seed)['status'],'RIGHT_EDGE')

class BankTests(PlanFixture):
    def test_bank_schema_resume_and_freeze_mutation(self):
        import tempfile,json,hashlib
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'docs').mkdir()
            (root/'docs/DESIGN_AND_PROTOCOL.md').write_text('synthetic')
            (root/'source.py').write_text('frozen source')
            sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
            freeze=dict(code_hashes={'source.py':sha(root/'source.py')},input_hashes={},
                protocol_sha256=sha(root/'docs/DESIGN_AND_PROTOCOL.md'))
            (root/'docs/BANK_FREEZE.json').write_text(json.dumps(freeze))
            self.b['begin']=299
            self.b['states']=dict(k=np.array([299,310,350]),units=np.array([self.seed['units']]*3),
                cash=np.array([2000.]*3),nav=np.array([10000.]*3),busy=np.array([False]*3))
            bank=self.cc.build_bank(root,self.b)
            for head,dim in [('PARK',8),('REDEPLOY',12)]:
                self.assertEqual(set(bank[head]),{'X','y','signal_idx','terminal_idx','asset_idx'})
                self.assertEqual(bank[head]['X'].shape,(2,dim))
            resumed=self.cc.build_bank(root,self.b,resume=True)
            np.testing.assert_array_equal(resumed['PARK']['X'],bank['PARK']['X'])
            with self.assertRaises(FileExistsError):self.cc.build_bank(root,self.b)
            (root/'source.py').write_text('changed')
            with self.assertRaisesRegex(ValueError,'FROZEN_INPUT_CHANGED'):
                self.cc.build_bank(root,self.b,resume=True)
    def test_bank_cannot_start_without_freeze(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):self.cc.build_bank(Path(directory),self.b)

if __name__=='__main__':unittest.main()
