import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from paper_ltr_v1 import learner as old
from paper_ltr_monthly_v1.core import MONTHS,mature_frame,split_at,fit_month,fingerprints,sha

class MonthlyTests(unittest.TestCase):
    def frame(self):
        dates=pd.date_range('2008-01-31','2018-12-31',freq='ME')
        rows=[dict(signal_date=d,ticker=t,exit_date_21=d+pd.Timedelta(days=31),target_rank_21=.5) for d in dates for t in ('A','B')]
        f=pd.DataFrame(rows)
        for col in old.FEATURES:f[col]=1.
        return f
    def test_exact_january_parity(self):
        f=mature_frame(self.frame(),'2017-01-01')
        a,b,s=split_at(f,'2017-01-01');x,y,t=old.split_training(f,2017)
        pd.testing.assert_frame_equal(a,x);pd.testing.assert_frame_equal(b,y)
        self.assertEqual(s,t)
    def test_monthly_maturity_and_purge(self):
        f=mature_frame(self.frame(),'2017-06-01')
        self.assertTrue((f.exit_date_21<pd.Timestamp('2017-06-01')).all())
        a,b,s=split_at(f,'2017-06-01')
        self.assertTrue((a.exit_date_21<s).all())
        self.assertTrue((b.signal_date>=s).all())
        with self.assertRaises(ValueError):split_at(self.frame(),'2017-06-01')
    def test_future_input_cannot_change_mature_training(self):
        a=self.frame();b=a.copy();mask=b.signal_date>=pd.Timestamp('2017-06-01')
        b.loc[mask,old.FEATURES]=999.
        pd.testing.assert_frame_equal(mature_frame(a,'2017-06-01'),mature_frame(b,'2017-06-01'))
    def test_fixed_months(self):
        self.assertEqual(len(MONTHS),114)
        self.assertEqual((MONTHS[0],MONTHS[-1]),('2017-01','2026-06'))
        self.assertEqual(sum(x.endswith('-01') for x in MONTHS)*3,30)
    def test_january_reuses_model_without_solver(self):
        frame=self.frame();train=mature_frame(frame,'2017-01-01');sub,val,_=split_at(train,'2017-01-01')
        state=old.fit_transform_state(old.raw_matrix(sub));w=np.zeros(len(old.FEATURES))
        test=frame[frame.signal_date==pd.Timestamp('2017-01-31')].reset_index(drop=True)
        f=test[old.KEYS].copy();f['pred']=0.;f['vintage']=1
        with tempfile.TemporaryDirectory(dir='.') as tmp:
            root=Path(tmp);source=root/'annual';(source/'models').mkdir(parents=True)
            p=source/'models/2017_1_linear.npz';np.savez(p,w=w,**state,feature_names=np.asarray(old.FEATURES))
            meta=dict(**fingerprints(train,sub,val),learned_state_hashes={k:old.array_hash(v) for k,v in state.items()},
                seeds=[dict(seed=0,gradient_inf_norm=0.,parameter_sha256={'w':old.array_hash(w)})],saved_models=[str(p)])
            annual=dict(per_year={'2017':dict(transforms={'1':meta})},model_files_sha256={'models/2017_1_linear.npz':sha(p)})
            with patch('paper_ltr_monthly_v1.core.solver.solve_linear',side_effect=AssertionError('Duplicate fit')):
                pred,audit=fit_month(frame,[test,test],'2017-01',1,root/'monthly',source,annual,[f,f])
            self.assertTrue(audit['reused_annual_january']);self.assertEqual(audit['new_seed_fits'],0)
            self.assertEqual(sha(Path(audit['saved_models'][0])),sha(p))
            np.testing.assert_array_equal(pred[0],np.zeros(len(test)))

if __name__=='__main__':unittest.main()
