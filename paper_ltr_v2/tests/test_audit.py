import unittest
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import tempfile

class AuditTests(unittest.TestCase):
    def api(self):
        path=Path(__file__).resolve().parents[1]/'audit.py'
        self.assertTrue(path.exists(), 'Manca audit senza fit')
        spec=importlib.util.spec_from_file_location('audit_under_test',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def frame(self):
        return pd.DataFrame({'signal_date':pd.to_datetime(['2016-01-01']*2),
                             'ticker':['A','B'],'target_rank_21':[.1,1.],
                             'exit_date_21':pd.to_datetime(['2016-02-01']*2)})

    def test_perfect_target_scores_have_zero_kl(self):
        api=self.api(); result=api.query_diagnostics(self.frame(),np.array([1.,10.]))
        self.assertAlmostEqual(result['aggregate']['kl'],0.,places=12)
        self.assertAlmostEqual(result['aggregate']['uniform_loss'],np.log(2),places=12)
        self.assertAlmostEqual(result['aggregate']['top_decile_mass'],.9998766054240137,places=12)

    def test_uniform_scores_kl_equals_log_n_minus_entropy(self):
        result=self.api().query_diagnostics(self.frame(),np.zeros(2))['aggregate']
        self.assertAlmostEqual(result['cross_entropy'],np.log(2),places=12)
        self.assertAlmostEqual(result['kl'],np.log(2)-result['target_entropy'],places=12)
        self.assertEqual(result['top1_tie_rows'],2)

    def test_realized_returns_are_available_without_rank_to_return_conversion(self):
        f=self.frame();f['fwd_ret_21']=[.2,-.1]
        r=self.api().query_diagnostics(f,np.array([10.,1.]))
        self.assertEqual(r['selected_return_distribution']['median'],.2)
        self.assertEqual(r['aggregate']['top1_in_worst_decile'],1.)

    def test_checkpoint_audit_checks_parameter_hash_without_training(self):
        api=self.api();m=api.original
        dates=pd.date_range('2013-01-01',periods=20,freq='MS')
        f=pd.DataFrame([(d,t) for d in dates for t in ('A','B')],columns=['signal_date','ticker'])
        f['exit_date_21']=f.signal_date+pd.Timedelta(days=28);f['target_rank_21']=np.tile([.1,1.],20)
        f=pd.concat([f,pd.DataFrame(np.zeros((40,len(m.FEATURES))),columns=m.FEATURES)],axis=1)
        sub,val,_=m.split_training(f,2015);state=m.fit_transform_state(m.raw_matrix(sub))
        parameters=dict(W1=np.zeros((125,64)),b1=np.zeros(64),W2=np.zeros((64,64)),b2=np.zeros(64),W3=np.zeros((64,1)),b3=np.zeros(1))
        meta=dict(train_keys_sha256=m.keys_hash(f),subtrain_keys_sha256=m.keys_hash(sub),validation_keys_sha256=m.keys_hash(val),
                  train_matrix_sha256=m.array_hash(m.raw_matrix(f)),train_labels_sha256=m.array_hash(m.decile_labels(f)),
                  learned_state_hashes={k:m.array_hash(v) for k,v in state.items()},
                  seeds=[dict(seed=101,best_validation_loss=np.log(2),parameter_sha256={k:m.array_hash(v) for k,v in parameters.items()})])
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'checkpoint.npz';np.savez(path,**state,**parameters,feature_names=np.asarray(m.FEATURES))
            self.assertEqual(api.audit_saved_fit(f,2015,[path],meta)['new_fits_executed'],0)
            parameters['b3'][0]=1.
            np.savez(path,**state,**parameters,feature_names=np.asarray(m.FEATURES))
            with self.assertRaises(ValueError):api.audit_saved_fit(f,2015,[path],meta)

    def test_diagnostics_reject_nonfinite_and_partial_maturity(self):
        api=self.api()
        with self.assertRaises(ValueError):api.query_diagnostics(self.frame(),np.array([np.nan,1.]))
        f=self.frame();f.loc[0,'exit_date_21']=pd.Timestamp('2027-01-01')
        with self.assertRaises(ValueError):api.query_diagnostics(f,np.ones(2),cutoff='2017-01-01')

    def gate_records(self,n=63):
        return [dict(key=str(i),support_sha256='a',target_sha256='b',target_entropy=.2,
                     kl=1.,top1_quality=.6,ndcg5=.7) for i in range(n)]

    def test_budget_gate_requires_42_improvements_not_mean_only(self):
        api=self.api();old=self.gate_records();new=[dict(r,kl=.98 if i<41 else 1.) for i,r in enumerate(old)]
        result=api.budget_gate(old,new)
        self.assertFalse(result['PASS']);self.assertFalse(result['checks']['at_least42_improved'])
        new[41]['kl']=.98
        self.assertTrue(api.budget_gate(old,new)['PASS'])

    def test_budget_gate_rejects_entropy_or_support_change(self):
        api=self.api();old=self.gate_records();new=[dict(r,kl=.98) for r in old]
        new[0]['target_entropy']=.3
        with self.assertRaises(ValueError):api.budget_gate(old,new)
        new[0]['target_entropy']=.2;new[0]['support_sha256']='wrong'
        with self.assertRaises(ValueError):api.budget_gate(old,new)

    def test_reduction_gate_zero_and_missing_are_fail_closed(self):
        path=Path(__file__).resolve().parents[1]/'summarize.py'
        self.assertTrue(path.exists(),'Manca aggregatore v2')
        spec=importlib.util.spec_from_file_location('summary_under_test',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertTrue(module.reduction_gate(0.,0.))
        self.assertFalse(module.reduction_gate(.01,0.))
        self.assertFalse(module.reduction_gate(None,.1))
        self.assertFalse(module.reduction_gate(np.nan,.1))

if __name__=='__main__':unittest.main()
