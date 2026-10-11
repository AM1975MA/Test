import unittest
import pandas as pd
from paper_ltr_v1.summarize import stability, common_truth

class SummaryTest(unittest.TestCase):
    def frame(self):
        return pd.DataFrame([dict(vintage=i,signal_date='2020-01-02',ticker=t,pred=p,target_rank_21=q,exit_date_21=pd.Timestamp('2020-02-03')) for i in (1,2,3) for t,p,q in (('A',3.,.1),('B',2.,.7),('C',1.,1.))])

    def test_stability_denominator_and_ordered_top2(self):
        f=self.frame(); f.loc[(f.vintage==3)&(f.ticker=='B'),'pred']=4.
        s=stability(f)
        self.assertEqual(s['queries'],1)
        self.assertAlmostEqual(s['aggregate']['top1_disagreement'],2/3)
        self.assertAlmostEqual(s['aggregate']['ordered_top2_disagreement'],2/3)
        self.assertEqual(s['aggregate']['unordered_top2_disagreement'],0.)

    def test_support_loss_rejected(self):
        f=self.frame().drop(index=0)
        with self.assertRaises(ValueError):stability(f)

    def test_repeat2_outcomes_used_for_every_model(self):
        truth=self.frame(); truth.loc[truth.vintage!=2,'target_rank_21']=.99
        f=common_truth(truth,truth)
        self.assertTrue(f[f.ticker=='A'].target_rank_21.eq(.1).all())
        missing=truth[~((truth.vintage==2)&(truth.ticker=='A'))]
        with self.assertRaises(ValueError):common_truth(truth,missing)
