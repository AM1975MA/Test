import copy
import json
from pathlib import Path
import tempfile
import unittest
import pandas as pd
from compact21_learner_swap_v1.integrity import compare_panels, write_ma3_evidence
from compact21_learner_swap_v1.summarize_full import summarize, sha256, disagreement
from compact21_learner_swap_v1.summarize import LINE, VARIANTS, YEARS


class FullSummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)/'inputs'; self.root.mkdir()
        self.refs=Path(self.tmp.name)/'refs'; self.refs.mkdir()
        self.bench=Path(self.tmp.name)/'benchmark.json'
        self.bench.write_text(json.dumps({'status':LINE+'_BENCHMARK_SUMMARY','ranking':[{'variant':v,'ADVANCE_FULL_REPLAY':v!='BASE'} for v in VARIANTS],
                                         'full_matrix':{'include':[{'variant':v,'repeat':i} for v in VARIANTS for i in (1,2,3)]}}))
        env={k:'frozen' for k in ('python','machine','numpy','pandas','scipy','sklearn','execution_env','numpy_build_config')}
        self.panel=pd.DataFrame({'signal_date':['2020-01-02'],'ticker':['A'],'feature':[.5]})
        self.clusters=pd.DataFrame({'ticker':['A'],'cluster':[1]})
        report={'panel':compare_panels(self.panel,self.panel),'clusters':compare_panels(self.clusters,self.clusters)}
        for repeat in (1,2,3):
            ref=self.refs/f'learner-ma3-reference-r{repeat}'; ref.mkdir(); self.make_ma3(ref)
            self.make_ma3(ref/'repeat_rebuild')
            contract={'line':LINE,'purpose':'independent_ma3_reference','historical_outputs_consumed':False,
                      'titanium_scores_consumed':False,'must_not_replace_replay_generated_panel':True,
                      'repeat_verification':{'requested':True,'passed':True,**copy.deepcopy(report)},
                      'raw_files_sha256':{'A.csv':'a'*64},'environment':env,
                      'ma3_panel_semantic_sha256':report['panel']['own_sha256'],
                      'cluster_membership_semantic_sha256':report['clusters']['own_sha256']}
            (ref/'INPUT_CONTRACT.json').write_text(json.dumps(contract))
            for variant in VARIANTS:
                folder=self.root/f'learner-full-{variant}-r{repeat}'; folder.mkdir()
                evidence=folder/'evidence'; evidence.mkdir(); self.make_ma3(evidence/'ma3')
                pd.DataFrame({'signal_date':['2020-01-02'],'ticker':['A'],'BASE':[repeat],
                              'ET_TAIL':[.5],'XGB_TAIL':[.6],'TAIL_HYBRID':[.55]}).to_csv(evidence/'ENSEMBLE_TAIL_OOS.csv',index=False)
                pd.DataFrame({'signal_date':['2020-01-02'],'ticker':['A'],'compact21':[repeat], 'compact63':[.5],'tail':[.6]}).to_csv(evidence/'ANNUAL_PREDICTIONS.csv',index=False)
                result={'line':LINE,'sessions':2,'start':'2020-01-02','end':'2020-01-03','candidate_count':149,'completed_signals':1,
                        'v2_full_universe':{'cagr':.3+repeat*(.01 if variant=='BASE' else .005),'maxdd':-.2,'sharpe':1.1,'annualized_turnover':10},
                        'source_only':{**dict.fromkeys(('titanium_full_sha256','titanium_candidates_sha256','predictions_sha256','ma3_panel_sha256'),'a'*64),
                                       'historical_scores_consumed':False,'historical_paths_consumed':False},
                        'ma3_semantic_reference':{'passed':True,**copy.deepcopy(report),'reference_contract_sha256':sha256(ref/'INPUT_CONTRACT.json')},
                        'stability':{'variant':variant,'maturity_all':True,'negative_feedback_changed':False,
                                     'compact63_mean_prediction_sha256':{str(y):'a'*64 for y in YEARS},
                                     'transforms':[{'year':y,'horizons':{h:{'fit_cutoff':f'{y}-01-01','max_signal':f'{y-1}-11-30','max_exit':f'{y-1}-12-31','maturity_ok':True,
                                                                       'Xtr_sha256':'a'*64,'Xte_sha256':'a'*64,'y_sha256':'a'*64,'groups_sha256':'a'*64} for h in ('21','63')}} for y in YEARS]}}
                (evidence/'annual_models').mkdir()
                for y in YEARS:
                    (evidence/'annual_models'/f'fit_audit_{y}.json').write_text(json.dumps([{'year':y,'model':m,'fit_date':f'{y}-01-01','max_exit':f'{y-1}-12-31'} for m in ('compact21','compact63','tail','macro')]))
                pd.DataFrame([{'year':y,'n_train':100,'n_predict':20,'max_train_signal':f'{y-1}-11-30','max_train_exit63':f'{y-1}-12-31','cutoff':f'{y}-01-01','maturity_ok':True} for y in YEARS]).to_csv(evidence/'ENSEMBLE_FIT_AUDIT.csv',index=False)
                result['evidence_files_sha256']={str(p.relative_to(evidence)):sha256(p) for p in evidence.rglob('*') if p.is_file()}
                fullcontract={'line':LINE,'variant':variant,'canonical_models_sha256':'a'*64,'canonical_compare_sha256':'b'*64,
                              'raw_files_sha256':contract['raw_files_sha256'],'negative_feedback_changed':False,'CAGR_used_for_selection':False,
                              'environment':env,'execution_control':{'hybrid_n_jobs':1},'runner_sha256':'c'*64,
                              'intervention_sources_sha256':{'learners.py':'c'*64},'reference_infrastructure_sha256':{'D.csv':'d'*64},
                              'ma3_reference_contract_sha256':sha256(ref/'INPUT_CONTRACT.json'),'ma3_reference_contract':contract}
                (folder/f'RESULT_{variant}.json').write_text(json.dumps(result)); (folder/'INPUT_CONTRACT.json').write_text(json.dumps(fullcontract))
                (folder/f'DAILY_LEADERS_{variant}.csv').write_text('date,top1,top2\n2020-01-02,A,B\n2020-01-03,A,B\n')
    def make_ma3(self,folder):
        folder.mkdir(exist_ok=True); self.panel.to_pickle(folder/'RAW_FEATURE_PANEL.pkl'); self.clusters.to_csv(folder/'DYNAMIC_CLUSTER_MEMBERSHIP.csv',index=False); write_ma3_evidence(folder)
    def tearDown(self):self.tmp.cleanup()
    def run_summary(self):return summarize(self.root,benchmark_summary=self.bench,ma3_reference_inputs=self.refs)
    def mutate(self,edit):
        p=self.root/'learner-full-RIDGE-r1'/'RESULT_RIDGE.json'; q=json.loads(p.read_text()); edit(q); p.write_text(json.dumps(q))
    def gate(self):return self.run_summary()['models']['RIDGE']['comparison_to_new_BASE']['ECONOMIC_ROBUSTNESS_GATE_PASS']
    def test_complete_outcomes_and_joint_gate(self):
        q=self.run_summary();self.assertTrue(self.gate());self.assertTrue(q['models']['RIDGE']['RESEARCH_CANDIDATE_PASS']);self.assertFalse(q['production_adoption']);self.assertEqual(set(q['models']),set(VARIANTS))
    def test_benchmark_failed_not_rescued_by_full_cagr(self):
        q=json.loads(self.bench.read_text());q['ranking'][1]['ADVANCE_FULL_REPLAY']=False;self.bench.write_text(json.dumps(q))
        model=self.run_summary()['models']['RIDGE'];self.assertTrue(model['comparison_to_new_BASE']['ECONOMIC_ROBUSTNESS_GATE_PASS']);self.assertFalse(model['RESEARCH_CANDIDATE_PASS'])
    def test_drawdown_and_turnover_gates(self):
        for metric,value in [('maxdd',-.260001),('annualized_turnover',13.0001)]:
            p=self.root/'learner-full-RIDGE-r1'/'RESULT_RIDGE.json';original=p.read_text();self.mutate(lambda q:q['v2_full_universe'].update({metric:value}));self.assertFalse(self.gate());p.write_text(original)
    def test_maturity_source_and63_failure_retained_rejected(self):
        p=self.root/'learner-full-RIDGE-r1'/'RESULT_RIDGE.json';original=p.read_text()
        for edit in (lambda q:q['source_only'].update(historical_scores_consumed=True),lambda q:q['stability']['transforms'][0]['horizons']['21'].update(max_exit='2017-01-01'),lambda q:q['stability']['transforms'][0]['horizons']['63'].update(Xtr_sha256='f'*64)):
            self.mutate(edit);self.assertFalse(self.gate());p.write_text(original)
    def test_pickle_bytes_not_semantic_gate(self):
        self.mutate(lambda q:q['source_only'].update(ma3_panel_sha256='f'*64));self.assertTrue(self.gate())
    def test_manifest_or_actual_semantics_tampering_fail_closed(self):
        p=self.root/'learner-full-RIDGE-r1'/'evidence'/'ma3'/'RAW_FEATURE_PANEL.pkl';p.write_bytes(p.read_bytes()+b'x')
        with self.assertRaisesRegex(ValueError,'manifest'):self.run_summary()
    def test_preflight_repeat_mutation_fail_closed(self):
        p=self.refs/'learner-ma3-reference-r1'/'repeat_rebuild'/'RAW_FEATURE_PANEL.pkl';f=pd.read_pickle(p);f.loc[0,'feature']+=1e-12;f.to_pickle(p)
        with self.assertRaisesRegex(ValueError,'repeat data'):self.run_summary()
    def test_missing_result_or_date_coverage_rejected(self):
        p=self.root/'learner-full-RIDGE-r1'/'DAILY_LEADERS_RIDGE.csv';p.write_text('date,top1,top2\n2020-01-02,A,B\n')
        with self.assertRaisesRegex(ValueError,'scope dates|coverage'):self.run_summary()
        p.write_text('date,top1,top2\n2020-01-02,A,B\n2020-01-03,A,B\n')
        (self.root/'learner-full-RIDGE-r3'/'RESULT_RIDGE.json').unlink()
        with self.assertRaisesRegex(ValueError,'Incomplete'):self.run_summary()
    def refresh_manifest(self):
        evidence=self.root/'learner-full-RIDGE-r1'/'evidence'
        self.mutate(lambda q:q.update(evidence_files_sha256={str(p.relative_to(evidence)):sha256(p) for p in evidence.rglob('*') if p.is_file()}))
    def test_invariant_tail_ulp_change_rejects_even_valid_manifest(self):
        import numpy as np
        evidence=self.root/'learner-full-RIDGE-r1'/'evidence'
        p=evidence/'ENSEMBLE_TAIL_OOS.csv'; frame=pd.read_csv(p,float_precision='round_trip')
        frame.loc[0,'ET_TAIL']=np.nextafter(frame.loc[0,'ET_TAIL'],1.0);frame.to_csv(p,index=False)
        self.refresh_manifest();self.assertFalse(self.gate())
    def test_retained_tail_maturity_rejects_even_valid_manifest(self):
        p=self.root/'learner-full-RIDGE-r1'/'evidence'/'annual_models'/'fit_audit_2017.json'
        audit=json.loads(p.read_text());next(a for a in audit if a['model']=='tail')['max_exit']='2017-01-01';p.write_text(json.dumps(audit))
        self.refresh_manifest();self.assertFalse(self.gate())
    def test_nonfinite_rejects_and_no_inner_join(self):
        self.mutate(lambda q:q['v2_full_universe'].update(cagr=float('nan')))
        with self.assertRaisesRegex(ValueError,'Nonfinite'):self.run_summary()
        with self.assertRaises(ValueError):disagreement({'2020-01-01':('A','B')},{'2020-01-02':('A','B')})

if __name__=='__main__':unittest.main()
