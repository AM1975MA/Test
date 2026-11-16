"""Audit boundaries: economic gates, cash-reset fills, and accepted executions."""
import importlib.util
import hashlib
import json
from pathlib import Path
import unittest
import tempfile

import numpy as np
import pandas as pd

SOURCE = Path(__file__).resolve().parents[1]/'src/analyze_results.py'


class ResultAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SOURCE.exists():
            spec=importlib.util.spec_from_file_location('olc113_result_audit_under_test',SOURCE)
            cls.module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)

    def setUp(self):
        self.assertTrue(SOURCE.exists(),'Independent auditor implementation is not yet present')
        self.audit=self.module

    def test_material_gate_requires_both_windows_and_separate_30_target(self):
        base={'whole':{'cagr':.20,'maxdd_sampled':-.25},'post':{'cagr':.12,'maxdd_sampled':-.20}}
        candidate={'whole':{'cagr':.23,'maxdd_sampled':-.25},'post':{'cagr':.15,'maxdd_sampled':-.19}}
        result=self.audit.material_criterion(candidate,base)
        self.assertTrue(result['material_both_windows'])
        self.assertFalse(result['target30_whole'])
        candidate['post']['cagr']=.149
        self.assertFalse(self.audit.material_criterion(candidate,base)['material_both_windows'])

    def test_drawdown_sign_cannot_reward_a_deeper_loss(self):
        base={'whole':{'cagr':.20,'maxdd_sampled':-.20},'post':{'cagr':.20,'maxdd_sampled':-.20}}
        candidate={'whole':{'cagr':.30,'maxdd_sampled':-.21},'post':{'cagr':.30,'maxdd_sampled':-.19}}
        result=self.audit.material_criterion(candidate,base)
        self.assertFalse(result['material_both_windows'])
        self.assertFalse(result['whole']['drawdown_nonworse'])
        self.assertTrue(result['target30_whole'])

    def reset_fixture(self,fill_idx=3):
        count=max(fill_idx+2,6)
        dates=pd.bdate_range('2024-01-29',periods=count)
        monthly=np.r_[dates[:-1].to_period('M')!=dates[1:].to_period('M'),False]
        targets=np.ones((count,1))
        daily=pd.DataFrame([dict(k=k,date=str(dates[k].date()),nav_open=100.,nav_close=100.,
            cash=100. if k<fill_idx else 0.,gross=0. if k<fill_idx else 1.,positions=0 if k<fill_idx else 1)
            for k in range(1,count)])
        busy={k:bool(3<=k<fill_idx) for k in range(count)}
        trace=pd.DataFrame([dict(k=k,date=str(dates[k].date()),initial=k==0,scheduled=bool(monthly[k]),
            gross=0. if k<fill_idx else 1.,model_ready_all=k>0,
            action='INITIAL' if k==0 else 'SCHEDULED' if k==2 else 'HOLD',
            status='BASE_INITIAL' if k==0 else 'MONTHLY_BASELINE_RESET' if k==2 else 'BUSY' if busy[k] else 'HOLD_BUFFER',
            monthly_cash_reset=k==2) for k in range(count-1)])
        instructions=pd.DataFrame([dict(instruction_id=1,signal_idx=2,signal_date=str(dates[2].date()),
            due_idx=3,reason='SCHEDULED',force=False,target_weights='[1.0]',raw_weights='[1.0]',
            meta=json.dumps(dict(monthly_cash_reset=True,status='MONTHLY_BASELINE_RESET')))])
        orders=pd.DataFrame([dict(instruction_id=1,signal_idx=2,execution_idx=fill_idx,due_idx=3,
            side='BUY',quantity=10.,notional=100.,reason='SCHEDULED')])
        attempts=pd.DataFrame([dict(k=k,instruction_id=1,missing_count=1 if k<fill_idx else 0,
            missing_tickers='A' if k<fill_idx else '',deferred=k<fill_idx) for k in range(3,fill_idx+1)])
        return dict(trace=trace,instructions=instructions,orders=orders,daily=daily,
                    targets=targets,monthly=monthly,busy_by_k=busy,attempts=attempts,ready_idx=1)

    def test_monthly_cash_reset_is_verified_against_executed_buy(self):
        summary,events,spells=self.audit.audit_monthly_resets(**self.reset_fixture())
        self.assertEqual(summary['cash_reset_instructions'],1)
        self.assertEqual(summary['cash_reset_instructions_with_buys'],1)
        self.assertEqual(events.iloc[0]['first_buy_delay_sessions'],1)
        self.assertEqual(spells.iloc[0]['ending_instruction_reason'],'SCHEDULED')

    def test_missing_idle_monthly_reset_cannot_pass_as_hold(self):
        fixture=self.reset_fixture()
        fixture['trace'].loc[fixture['trace'].k==2,['status','action','monthly_cash_reset']]=['HOLD_BUFFER','HOLD',False]
        with self.assertRaisesRegex(ValueError,'MONTHLY_RESET_CONTRACT'):
            self.audit.audit_monthly_resets(**fixture)

    def test_false_readiness_flag_cannot_hide_a_required_cash_reset(self):
        fixture=self.reset_fixture()
        fixture['trace'].loc[fixture['trace'].k==2,['model_ready_all','status','action','monthly_cash_reset']]=[False,'HOLD_BUFFER','HOLD',False]
        fixture['instructions']=fixture['instructions'].iloc[:0]
        fixture['orders']=fixture['orders'].iloc[:0]
        fixture['daily'].loc[:,['cash','gross','positions']]=[100.,0.,0]
        fixture['trace'].loc[:,'gross']=0.
        with self.assertRaisesRegex(ValueError,'MODEL_READINESS_TRACE_MISMATCH'):
            self.audit.audit_monthly_resets(**fixture)

    def test_false_invested_trace_cannot_hide_a_cash_reset(self):
        fixture=self.reset_fixture()
        fixture['trace'].loc[fixture['trace'].k==2,['gross','monthly_cash_reset']]=[1.,False]
        fixture['instructions'].loc[0,'meta']=json.dumps(dict(monthly_cash_reset=False,status='MONTHLY_BASELINE_RESET'))
        with self.assertRaisesRegex(ValueError,'TRACE_ACCOUNT_STATE_MISMATCH'):
            self.audit.audit_monthly_resets(**fixture)

    def test_same_close_reset_fill_is_rejected(self):
        fixture=self.reset_fixture()
        fixture['orders'].loc[0,'execution_idx']=2
        with self.assertRaisesRegex(ValueError,'RESET_EXECUTION_TIMING'):
            self.audit.audit_monthly_resets(**fixture)

    def test_quote_deferred_cash_spell_may_exceed_21_sessions(self):
        summary,events,spells=self.audit.audit_monthly_resets(**self.reset_fixture(fill_idx=27))
        self.assertTrue(summary['mechanical_contract_pass'])
        self.assertEqual(summary['cash_reset_deferred_attempt_sessions'],24)
        self.assertEqual(events.iloc[0]['first_buy_delay_sessions'],25)
        self.assertEqual(spells.iloc[0]['cash_sessions'],26)
        self.assertEqual(summary['scheduled_cash_busy_rows'],1)

    def ledger_fixture(self):
        dates=pd.date_range('2024-01-29',periods=3)
        panel=dict(dates=dates.values,names=np.array(['A']),C=np.ones((3,1))*10.,O=np.ones((3,1))*10.,
                   observed=np.ones((3,1),bool),open_observed=np.ones((3,1),bool))
        daily=pd.DataFrame([dict(k=1,date='2024-01-30',nav_open=10000.,nav_close=9997.5,cash=8997.5,gross=1000/9997.5,positions=1),
                            dict(k=2,date='2024-01-31',nav_open=9997.5,nav_close=9997.5,cash=8997.5,gross=1000/9997.5,positions=1)])
        instructions=pd.DataFrame([dict(instruction_id=0,signal_idx=0,due_idx=1,target_weights='[0.1]',reason='INITIAL')])
        orders=pd.DataFrame([dict(instruction_id=0,signal_idx=0,due_idx=1,execution_idx=1,j=0,ticker='A',side='BUY',
                                 quantity=100.,price=10.,notional=1000.,cost=2.5,date='2024-01-30',execution_date='2024-01-30',reason='INITIAL')])
        return dict(daily=daily,orders=orders,instructions=instructions,panel=panel,scenario='NEXT_CLOSE')

    def test_cost_formula_is_checked_independently_of_recorded_cost(self):
        fixture=self.ledger_fixture()
        summary,_,_=self.audit.audit_execution_ledger(**fixture)
        self.assertTrue(summary['fee_and_execution_pass'])
        self.assertEqual(summary['maximum_fee_formula_error'],0.)
        fixture['orders'].loc[0,'cost']=2.6
        summary,_,_=self.audit.audit_execution_ledger(**fixture)
        self.assertFalse(summary['fee_and_execution_pass'])
        self.assertAlmostEqual(summary['maximum_fee_formula_error'],.1)

    def test_valid_receipt_cannot_be_relocated_under_another_arm(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace=Path(temporary)
            folder=workspace/'PRICE_RESET__NEXT_CLOSE'
            folder.mkdir()
            native=dict(path_id='TERM_RESET__NEXT_CLOSE',arm='TERM_RESET',scenario='NEXT_CLOSE')
            artifact_hashes={}
            for name in self.audit.ARTIFACTS:
                (folder/name).write_bytes(b'unchanged artifact')
                artifact_hashes[name]=hashlib.sha256(b'unchanged artifact').hexdigest()
            receipt=dict(path_id=native['path_id'],artifacts=artifact_hashes,
                metrics_payload_sha256=hashlib.sha256(json.dumps(native,sort_keys=True,separators=(',',':')).encode()).hexdigest())
            receipt_path=folder/'PATH_RECEIPT.json'
            receipt_path.write_text(json.dumps(receipt))
            native['path_receipt_sha256']=hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'PATH_RECEIPT_EXPECTED_PATH'):
                self.audit._verify_receipt(folder,native,{},workspace)


if __name__=='__main__':
    unittest.main()
