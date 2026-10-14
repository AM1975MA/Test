import importlib.util
import tempfile
import unittest
from pathlib import Path
import numpy as np


class LearnerTests(unittest.TestCase):
    def learner(self):
        self.assertIsNotNone(importlib.util.find_spec('paper_ltr_v2.learner'), 'Il learner v2 deve esistere')
        from paper_ltr_v2 import learner
        return learner

    def test_linear_gradient_matches_independent_finite_difference(self):
        m=self.learner(); x=np.array([[1.,0.],[0.,1.],[-1.,0.],[0.,-1.]])
        y=np.array([1,10,4,8]); groups=[np.arange(2),np.arange(2,4)]; w=np.array([.1,-.2])
        loss,gradient=m.linear_objective(w,x,y,groups)
        for j in range(2):
            step=np.zeros(2);step[j]=1e-6
            numeric=(m.linear_objective(w+step,x,y,groups)[0]-m.linear_objective(w-step,x,y,groups)[0])/2e-6
            self.assertAlmostEqual(numeric,gradient[j],places=7)

    def test_linear_converges_reproducibly_to_stationary_solution(self):
        m=self.learner(); x=np.tile(np.arange(8)[:,None]/7,(3,2)); y=np.tile(np.arange(2,10),3)
        groups=[np.arange(i*8,(i+1)*8) for i in range(3)]
        w,a=m.solve_linear(x,y,groups); z,b=m.solve_linear(x,y,groups)
        np.testing.assert_array_equal(w,z);self.assertEqual(a,b)
        self.assertLessEqual(np.max(np.abs(m.linear_objective(w,x,y,groups)[1])),m.LINEAR_RECIPE['gradient_tolerance'])
        self.assertLess(m.linear_objective(w,x,y,groups)[0],m.linear_objective(np.zeros(2),x,y,groups)[0])

    def test_prefix_tampering_rejected(self):
        m=self.learner(); original=dict(initial_train_loss=2.,initial_validation_loss=2.5,history=[dict(epoch=1,train_loss=1.,validation_loss=2.)])
        extended={**original,'history':[dict(epoch=1,train_loss=1.1,validation_loss=2.)]}
        with self.assertRaises(ValueError):m.check_prefix(extended,original)
        self.assertTrue(m.check_prefix(original,original))

    def test_mixed_fresh_and_reused_seeds_certified_without_false_reuse_claim(self):
        m=self.learner()
        self.assertTrue(callable(getattr(m,'reuse_integrity',None)), 'Serve certificare la combinazione di semi nuovi e riusati')
        self.assertTrue(m.reuse_integrity([
            dict(new_fit_executed=True,reuse_original_PASS=False,prefix100_PASS=True),
            dict(new_fit_executed=False,reuse_original_PASS=True,prefix100_PASS=True)]))
        self.assertFalse(m.reuse_integrity([
            dict(new_fit_executed=False,reuse_original_PASS=False,prefix100_PASS=True)]))

    def test_checkpoint_tampering_rejected(self):
        m=self.learner()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'model.npz';np.savez(path,W1=np.array([1.]))
            digest=m.sha(path);np.savez(path,W1=np.array([2.]))
            with self.assertRaises(ValueError):m.load_checkpoint(path,digest)

    def test_runner_refuses_unbound_nofit_audit_before_fit(self):
        self.assertIsNotNone(importlib.util.find_spec('paper_ltr_v2.run'), 'Il runner v2 deve esistere')
        from paper_ltr_v2.run import verify_diagnostic
        with tempfile.TemporaryDirectory() as temp:
            import json
            path=Path(temp)/'AUDIT.json'
            path.write_text(json.dumps(dict(status='PAPER_LTR_V2_NOFIT_AUDIT_COMPLETE',input_sha256={'1':'other'},result_sha256='original')))
            with self.assertRaises(ValueError):verify_diagnostic(path,{'1':'expected'},'original')

    def test_temporal_split_unchanged_and_immature_labels_rejected(self):
        m=self.learner(); import pandas as pd
        dates=pd.date_range('2013-01-01',periods=20,freq='MS')
        frame=pd.DataFrame(dict(signal_date=dates,ticker='A',exit_date_21=dates+pd.Timedelta(days=28),target_rank_21=.5))
        sub,val,start=m.V1.split_training(frame,2015)
        self.assertTrue((sub.exit_date_21<start).all());self.assertTrue((val.signal_date>=start).all())
        frame.loc[0,'exit_date_21']=pd.Timestamp('2015-01-01')
        with self.assertRaises(ValueError):m.V1.split_training(frame,2015)

    def test_reused_patience_models_keep_parameters_predictions_and_file_bytes(self):
        m=self.learner();import pandas as pd;import json
        dates=pd.date_range('2013-01-01',periods=20,freq='MS')
        train=pd.DataFrame(dict(signal_date=dates,ticker='A',exit_date_21=dates+pd.Timedelta(days=28),target_rank_21=.5))
        train=pd.concat([train,pd.DataFrame({name:np.arange(20)/20+j/125 for j,name in enumerate(m.V1.FEATURES)})],axis=1)
        sub,val,_=m.V1.split_training(train,2015);state=m.V1.fit_transform_state(m.V1.raw_matrix(sub))
        tests=[val.copy(),val.copy()]
        x=m.V1.transform(m.V1.raw_matrix(sub),state);vx=m.V1.transform(m.V1.raw_matrix(val),state)
        old=dict(recipe=m.V1.RECIPE.copy(),train_keys_sha256=m.V1.keys_hash(train),
                 train_matrix_sha256=m.V1.array_hash(m.V1.raw_matrix(train)),
                 train_labels_sha256=m.V1.array_hash(m.V1.decile_labels(train)),
                 subtrain_keys_sha256=m.V1.keys_hash(sub),validation_keys_sha256=m.V1.keys_hash(val),
                 fit_matrix_sha256=m.V1.array_hash(x),validation_matrix_sha256=m.V1.array_hash(vx),
                 test_fit_matrix_sha256=[m.V1.array_hash(vx)]*2,seeds=[])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);original=root/'original';models=original/'models';models.mkdir(parents=True)
            hashes={};by_seed=[]
            for seed in m.V1.RECIPE['seeds']:
                params=m.V1.initialize(125,np.random.default_rng(seed));pred=m.V1.forward(vx,params)[0];by_seed.append(pred)
                path=models/f'2015_1_listnet_{seed}.npz';np.savez(path,**params,**state,feature_names=np.asarray(m.V1.FEATURES))
                hashes[f'models/{path.name}']=m.sha(path)
                old['seeds'].append(dict(seed=seed,stop_reason='patience',best_epoch=1,epochs_executed=26,
                    parameter_sha256={n:m.V1.array_hash(p) for n,p in params.items()},
                    prediction_sha256=[m.V1.array_hash(pred)]*2))
            result=dict(status='PAPER_LTR_V1_COMPLETE',ALL_MATURITY_PASS=True,
                sources={'paper_ltr_v1/learner.py':m.sha(m.V1.__file__)},
                per_year={'2015':{'transforms':{'1':old}}},model_files_sha256=hashes)
            (original/'RESULT.json').write_text(json.dumps(result))
            predictions,meta,_,_=m.fit_budget(train,tests,2015,root/'out','2015_1',original)
            self.assertEqual(meta['new_seed_fits'],0);self.assertEqual(meta['reused_seeds'],3)
            self.assertTrue(meta['reuse_original_PASS']);self.assertTrue(meta['prefix100_PASS'])
            np.testing.assert_array_equal(predictions[0],np.mean(by_seed,axis=0))
            for seed in m.V1.RECIPE['seeds']:
                self.assertEqual(m.sha(root/'out'/f'2015_1_listnet_{seed}.npz'),hashes[f'models/2015_1_listnet_{seed}.npz'])

    def test_adapter_compiles_without_mutating_original_runner(self):
        from paper_ltr_v2.run import adapter_source,ROOT
        path=ROOT/'paper_ltr_v1/run.py';before=path.read_bytes()
        source=adapter_source(path.read_text());compile(source,str(path),'exec')
        self.assertEqual(path.read_bytes(),before)

if __name__=='__main__':unittest.main()
