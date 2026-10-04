"""Gates and complete annual evidence are fixed before observing outcomes."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from compact21_learner_swap_v1.summarize import summarize, VARIANTS, YEARS, PAIRS


def fixture(variant):
    stable = {'rank_mean_abs': .1 if variant=='BASE' else .075,
              'rank_p99_abs': .2, 'mean_daily_spearman': .9,
              'top1_disagreement_fraction': .2, 'top5_jaccard': .8}
    quality = {'daily_spearman_vs_target': .2, 'ndcg5': .8 if variant=='BASE' else .76,
               'ndcg10': .8, 'pred_top1_mean_realized_pct': .8 if variant=='BASE' else .76,
               'top5_realized_overlap': .5}
    cell = {'common_inference': {p:copy.deepcopy(stable) for p in PAIRS},
            'native_inference': {p:copy.deepcopy(stable) for p in PAIRS},
            'quality': {r:copy.deepcopy(quality) for r in ('1','2','3')},
            'train_rows':dict.fromkeys(('1','2','3'),100), 'test_rows':dict.fromkeys(('1','2','3'),20),
            'common_test_rows':20, 'evaluation_coverage':{'common_keys_sha256':'a'*64,'common_rows':20,'common_queries':2, **{k:dict.fromkeys(('1','2','3'),'a'*64) for k in ('train_keys_sha256','test_keys_sha256','quality_keys_sha256')}, 'quality_rows':dict.fromkeys(('1','2','3'),20),'quality_queries':dict.fromkeys(('1','2','3'),2)},
            'maturity_PASS':True, 'determinism':{'PASS':True,'max_abs':0.0,'common_and_native_bytes_exact':True}}
    return {'status':'COMPACT21_LEARNER_SWAP_V1_BENCHMARK_COMPLETE','variant':variant,'years':YEARS,
            'per_year':{str(y):copy.deepcopy(cell) for y in YEARS},
            'aggregate':{'common_inference':copy.deepcopy(stable),'native_inference':copy.deepcopy(stable),'quality':copy.deepcopy(quality)},
            'environment':{'numpy':'2.3.5'}, 'input_sha256':dict.fromkeys(('1','2','3'),'a'*64),
            'input_contract':{'protocol':'COMPACT21_LEARNER_SWAP_V1','years':YEARS,'train_cohorts':'native_no_intersection',
                              'common_inference_repeat':2,'signal_cutoff':'2026-06-30','quality_exit_cutoff':'2026-07-01',
                              'canonical_source_sha256':{'models.py':'b'*64}, 'learner_source_sha256':{'learners.py':'c'*64}},
            'ALL_MATURITY_PASS':True,'ALL_DETERMINISM_PASS':True}


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        for v in VARIANTS: self.write(v,fixture(v))
    def tearDown(self): self.tmp.cleanup()
    def write(self,v,q): (self.root/(v+'.json')).write_text(json.dumps(q))
    def mutate(self,v,edit):
        q=json.loads((self.root/(v+'.json')).read_text()); edit(q); self.write(v,q)
    def result(self,v='RIDGE'): return next(q for q in summarize(self.root)['ranking'] if q['variant']==v)
    def change_metric(self,v,scope,key,value):
        def edit(q):
            for c in q['per_year'].values():
                for m in c[scope].values(): m[key]=value
            q['aggregate'][scope][key]=value
        self.mutate(v,edit)
    def test_boundaries_pass_and_unconditional_diagnostic_matrix(self):
        q=summarize(self.root); self.assertEqual(q['eligible'],['RIDGE','LGBM_LAMBDARANK'])
        self.assertEqual(len(q['full_matrix']['include']),9)
        self.assertFalse(q['production_adoption'])
    def test_top1_quality_below_boundary_rejects_without_cagr_rescue(self):
        self.change_metric('RIDGE','quality','pred_top1_mean_realized_pct',.759999)
        self.assertFalse(self.result()['checks']['quality_top1_realized_pct_ge95pct'])
        self.assertFalse(self.result()['ADVANCE_FULL_REPLAY'])
        self.assertEqual(len(summarize(self.root)['full_matrix']['include']),9)
    def test_other_gate_boundaries(self):
        for scope,key,val in [('common_inference','rank_mean_abs',.075001),('common_inference','top1_disagreement_fraction',.200001),('native_inference','top1_disagreement_fraction',.200001),('common_inference','mean_daily_spearman',.899999),('quality','ndcg5',.759999)]:
            self.write('RIDGE',fixture('RIDGE')); self.change_metric('RIDGE',scope,key,val)
            self.assertFalse(self.result()['ADVANCE_FULL_REPLAY'],key)
    def test_missing_year_pair_and_repeat_fail_closed(self):
        for scope,member in [('common_inference','1-3'),('native_inference','2-3'),('quality','3')]:
            self.write('RIDGE',fixture('RIDGE')); self.mutate('RIDGE',lambda q:q['per_year']['2017'][scope].pop(member))
            with self.assertRaisesRegex(ValueError,'Incomplete'): summarize(self.root)
        self.write('RIDGE',fixture('RIDGE')); self.mutate('RIDGE',lambda q:q['per_year'].pop('2026'))
        with self.assertRaisesRegex(ValueError,'annual'): summarize(self.root)
    def test_forged_aggregate_fails(self):
        self.mutate('RIDGE',lambda q:q['aggregate']['quality'].update(ndcg5=.99))
        with self.assertRaisesRegex(ValueError,'Aggregate inconsistent'): summarize(self.root)
    def test_provenance_coverage_missing_contract_fail(self):
        for key in ('environment','input_sha256','input_contract'):
            self.write('RIDGE',fixture('RIDGE')); self.mutate('RIDGE',lambda q:q.pop(key))
            with self.assertRaises(ValueError): summarize(self.root)
        self.write('RIDGE',fixture('RIDGE')); self.mutate('RIDGE',lambda q:q['per_year']['2020']['evaluation_coverage'].update(common_keys_sha256='d'*64))
        with self.assertRaisesRegex(ValueError,'cohorts/coverage'): summarize(self.root)
    def test_maturity_determinism_false_or_missing_reject(self):
        for edit in (lambda q:q['per_year']['2017'].update(maturity_PASS=False), lambda q:q['per_year']['2026']['determinism'].update(max_abs=1e-10), lambda q:q.pop('ALL_DETERMINISM_PASS')):
            self.write('RIDGE',fixture('RIDGE')); self.mutate('RIDGE',edit)
            self.assertFalse(self.result()['ADVANCE_FULL_REPLAY'])
    def test_nonfinite_nested_and_duplicate_json_key_reject(self):
        self.mutate('RIDGE',lambda q:q.update(diagnostic=float('inf')))
        with self.assertRaisesRegex(ValueError,'Nonfinite'): summarize(self.root)
        self.write('RIDGE',fixture('RIDGE')); p=self.root/'RIDGE.json'; p.write_text(p.read_text()[:-1]+',"variant":"RIDGE"}')
        with self.assertRaisesRegex(ValueError,'Duplicate JSON'): summarize(self.root)
    def test_missing_variant_fail(self):
        (self.root/'RIDGE.json').unlink()
        with self.assertRaisesRegex(ValueError,'Incomplete variants'): summarize(self.root)

if __name__=='__main__': unittest.main()
