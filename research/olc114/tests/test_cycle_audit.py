"""Adversarial boundaries of the results-only OLC114 audit."""
from pathlib import Path
import importlib.util
import unittest
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


class AuditTests(unittest.TestCase):
    def setUp(self):
        path=ROOT/'src/analyze_cycles.py'
        self.assertTrue(path.exists(),'audit implementation missing')
        spec=importlib.util.spec_from_file_location('independent_cycle_audit_test',path)
        self.a=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.a)

    def fixture(self,lag=0):
        dates=pd.bdate_range('2020-01-01',periods=5).to_numpy(dtype='datetime64[D]')
        panel=dict(dates=dates,names=np.array(['A','B']),C=np.full((5,2),100.),observed=np.ones((5,2),bool))
        due=1+lag;fee=1.+.0015*4000
        rows=[]
        for k in range(1,5):
            nav=10000.-fee if k>=due else 10000.
            rows.append(dict(k=k,date=str(dates[k]),nav_open=10000. if k==due else nav,nav_close=nav,
                cash=10000.-4000.-fee if k>=due else 10000.,gross=4000./nav if k>=due else 0.,positions=1 if k>=due else 0))
        orders=pd.DataFrame([dict(j=0,side='BUY',quantity=40.,price=100.,notional=4000.,cost=fee,
            execution_idx=due,date=str(dates[due]),execution_date=str(dates[due]),signal_idx=0,due_idx=due,
            ticker='A',reason='INITIAL',instruction_id=0)])
        inst=pd.DataFrame([dict(instruction_id=0,signal_idx=0,due_idx=due,target_weights='[0.4,0.0]',
                               action_indices='null',sell_only=False,reason='INITIAL',force=True)])
        return pd.DataFrame(rows),orders,inst,panel

    def test_lag_one_is_checked_against_immutable_due(self):
        d,o,i,p=self.fixture(1)
        summary,_,_=self.a.reconcile_account(d,o,i,p,'DELAY1_CLOSE')
        self.assertTrue(summary['pass_all'])
        with self.assertRaisesRegex(ValueError,'INSTRUCTION_CONTRACT'):
            self.a.reconcile_account(d,o,i,p,'NEXT_CLOSE')

    def test_target_mask_excludes_unrelated_missing_quote(self):
        d,o,i,p=self.fixture()
        i.loc[0,'action_indices']='[0]';p['observed'][1,1]=False
        summary,_,_=self.a.reconcile_account(d,o,i,p,'NEXT_CLOSE')
        self.assertEqual(summary['deferred_sessions'],0)
        self.assertTrue(summary['pass_all'])

    def test_csv_null_mask_decodes_as_full_instruction(self):
        d,o,i,p=self.fixture();i.loc[0,'action_indices']=np.nan
        summary,_,_=self.a.reconcile_account(d,o,i,p,'NEXT_CLOSE')
        self.assertTrue(summary['pass_all'])

    def test_out_of_mask_order_is_rejected(self):
        d,o,i,p=self.fixture();i.loc[0,'action_indices']='[1]'
        with self.assertRaisesRegex(ValueError,'ORDER_OUTSIDE_MASK|TARGET_EXECUTION_MISMATCH'):
            self.a.reconcile_account(d,o,i,p,'NEXT_CLOSE')

    def test_corrupted_cost_is_rejected_by_reconciliation(self):
        d,o,i,p=self.fixture();o.loc[0,'cost']+=1.
        summary,_,_=self.a.reconcile_account(d,o,i,p,'NEXT_CLOSE')
        self.assertFalse(summary['pass_all'])
        self.assertAlmostEqual(summary['maximum_fee_error'],1.)

    def test_balanced_fill_above_immutable_target_is_rejected(self):
        d,o,i,p=self.fixture();i.loc[0,'target_weights']='[0.2,0.0]'
        with self.assertRaisesRegex(ValueError,'TARGET_EXECUTION_MISMATCH'):
            self.a.reconcile_account(d,o,i,p,'NEXT_CLOSE')

    def test_signal_target_restores_retained_units_budget(self):
        current=np.array([.35,.40,0.])
        got=self.a.signal_target(np.array([0.,0.,.6]),[2],False,current)
        np.testing.assert_allclose(got,[.35,.40,.25])
        sold=self.a.signal_target(np.zeros(3),[0],True,current)
        np.testing.assert_allclose(sold,[0.,.4,0.])

    def test_plan_sale_must_request_full_zero_target(self):
        from types import SimpleNamespace
        row=SimpleNamespace(reason='PARK_SALE',action_indices='[0]',sell_only=True,force=True,raw_weights='[0.2,0.0]')
        with self.assertRaisesRegex(ValueError,'PLAN_SALE_INSTRUCTION'):
            self.a.validate_sale_instruction(row,'PARK',0)
        row.raw_weights='[0.0,0.0]'
        self.a.validate_sale_instruction(row,'PARK',0)

    def test_material_growth_requires_both_windows(self):
        base={w:dict(cagr=.20,maxdd_sampled=-.3) for w in ('whole','post')}
        cand=dict(whole=dict(cagr=.24,maxdd_sampled=-.3),post=dict(cagr=.22,maxdd_sampled=-.3))
        self.assertFalse(self.a.material_criterion(cand,base)['material_both_windows'])
        cand['post']['cagr']=.24
        self.assertTrue(self.a.material_criterion(cand,base)['material_both_windows'])
        cand['post']['maxdd_sampled']=-.31
        self.assertFalse(self.a.material_criterion(cand,base)['material_both_windows'])

    def test_plan_chronology_strict_weekly_and_nonoverlap(self):
        monthly=np.zeros(30,bool);monthly[10]=True;monthly[20]=True
        weekly=np.zeros(30,bool);weekly[[5,10,15,20,25]]=True
        p=dict(signal_idx=2,head='REDEPLOY',asset=0,sale_complete_idx=4,entry_attempt_idx=5,
               entry_candidate_idx=1,handoff_idx=10,right_censored=False)
        self.assertTrue(self.a.check_plan_chronology([p],monthly,weekly,29)['pass_all'])
        bad=dict(p,entry_attempt_idx=4)
        with self.assertRaisesRegex(ValueError,'PLAN_ENTRY_TIMING'):
            self.a.check_plan_chronology([bad],monthly,weekly,29)
        with self.assertRaisesRegex(ValueError,'PLAN_OVERLAP'):
            self.a.check_plan_chronology([p,dict(p,signal_idx=8)],monthly,weekly,29)

    def test_nonoverlap_uses42_not21(self):
        self.assertEqual(self.a.nonoverlap([0,21,42,63,84]),3)

    def test_terminal_sale_is_filled_but_has_no_later_policy_confirmation(self):
        fills=pd.DataFrame([dict(execution_idx=9)])
        states={9:dict(units=np.array([0.]))}
        self.assertIsNone(self.a.confirmed_sale(fills,states,0,9))
        self.assertEqual(self.a.confirmed_sale(fills,states,0,10),9)

    def test_window_uses_own_previous_nav(self):
        d,_,_,_=self.fixture()
        result=self.a.audit.performance_window(d,start_idx=3)
        self.assertEqual(result['initial_nav'],d.nav_close.iloc[1])

if __name__=='__main__':unittest.main()
