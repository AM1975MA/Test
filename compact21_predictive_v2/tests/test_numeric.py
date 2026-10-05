import copy,unittest
from compact21_predictive_v2.summarize import normalized_numeric

def contract():
    active=['SSE','SSE2','SSE3','SSSE3','SSE41','POPCNT','SSE42','AVX','F16C','FMA3','AVX2']
    inactive=['AVX512F','AVX512CD','AVX512_KNL','AVX512_KNM','AVX512_SKX','AVX512_CLX','AVX512_CNL','AVX512_ICL','AVX512_SPR']
    return dict(python='3.13',machine='x86_64',numpy='2.3.5',pandas='2.2.3',scipy='1.17.0',sklearn='1.8.0',execution_env={'OPENBLAS_CORETYPE':'Haswell'},
      numpy_build_config={'SIMD Extensions':{'baseline':active[:3],'found':active[3:],'not found':inactive}},
      effective_cpu_features={**dict.fromkeys(active,True),**dict.fromkeys(inactive,False),'AVX512VL':False},
      threadpools=[dict(user_api='blas',internal_api='openblas',num_threads=1,version='0.3.30',architecture='Haswell',threading_layer='pthreads')])

class NumericTests(unittest.TestCase):
    def test_inactive_constituent_flag_is_not_a_compiled_target(self):
        a=contract();b=copy.deepcopy(a);b['effective_cpu_features']['AVX512VL']=True
        self.assertEqual(normalized_numeric(a),normalized_numeric(b))
        self.assertTrue(b['effective_cpu_features']['AVX512VL'])
    def test_active_target_mismatch_and_contradictory_evidence_fail(self):
        for name in ('AVX2','AVX512F'):
            a=contract();a['effective_cpu_features'][name]=not a['effective_cpu_features'][name]
            with self.assertRaises(ValueError):normalized_numeric(a)
    def test_missing_compiled_target_and_unknown_wheel_fail(self):
        a=contract();a['numpy_build_config']['SIMD Extensions']['not found'].pop()
        with self.assertRaises(ValueError):normalized_numeric(a)
        a=contract();a['numpy']='2.4.0'
        with self.assertRaises(ValueError):normalized_numeric(a)
    def test_blas_thread_or_architecture_changes_are_preserved(self):
        for key,value in [('num_threads',2),('architecture','SkylakeX')]:
            a=contract();b=copy.deepcopy(a);b['threadpools'][0][key]=value
            self.assertNotEqual(normalized_numeric(a),normalized_numeric(b))

if __name__=='__main__':unittest.main()
