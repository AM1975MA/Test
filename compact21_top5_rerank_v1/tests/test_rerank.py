"""Contract tests: never add ETF outside BASE top-five or change score multiset."""
import unittest
import numpy as np
import pandas as pd
from compact21_top5_rerank_v1.core import rerank

class TestTop5Rerank(unittest.TestCase):
    def panel(self):
        base=[];layer=[]
        for date in ["2021-01-29","2021-02-26"]:
            for i in range(10):
                t=f"ETF{i:02d}"
                base.append(dict(vintage="1",signal_date=pd.Timestamp(date),
                    ticker=t,pred=float(10-i),target_rank_21=float(10-i)/10,
                    target_ret_21=float(10-i)/100))
                layer.append(dict(vintage="1",signal_date=pd.Timestamp(date),
                    ticker=t,pred=float(100 if i==4 else 10-i)))
        return pd.DataFrame(base),pd.DataFrame(layer)
    def test_promotion_limited_to_base_top5(self):
        base,layer=self.panel()
        # The economic layer highly prefers ETF04: must be able to promote it,
        # but ETF05+ outside BASE5 retain exactly same score.
        out,proof=rerank(base,layer)
        for _,g in out.groupby("signal_date"):
            a=g.sort_values(["pred","ticker"],ascending=[False,True])
            self.assertEqual(a.iloc[0].ticker,"ETF04")
            self.assertEqual(set(a.iloc[:5].ticker),{f"ETF{i:02d}" for i in range(5)})
            self.assertTrue(np.array_equal(g.loc[g.ticker>="ETF05","pred"].to_numpy(),
                                           base.loc[(base.signal_date==g.signal_date.iloc[0]) &
                                                    (base.ticker>="ETF05"),"pred"].to_numpy()))
            self.assertEqual(sorted(g.pred),list(range(1,11)))
        self.assertEqual(len(proof),2)
        self.assertTrue(all(x["top1_changed"] for x in proof))
    def test_reject_changed_coverage(self):
        base,layer=self.panel()
        with self.assertRaisesRegex(ValueError,"coverage"):
            rerank(base,layer.iloc[:-1])
    def test_reject_duplicate(self):
        base,layer=self.panel()
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            rerank(base,pd.concat([layer,layer.iloc[:1]],ignore_index=True))
    def test_original_score_unchanged_when_layer_identical(self):
        base,_=self.panel()
        out,proof=rerank(base,base[["vintage","signal_date","ticker","pred"]])
        np.testing.assert_array_equal(out.pred.to_numpy(),base.pred.to_numpy())
        self.assertEqual(sum(x["top1_changed"] for x in proof),0)
    def test_different_target_cannot_influence_predictions(self):
        base,layer=self.panel()
        a,_=rerank(base,layer)
        mutated=base.copy();mutated["target_rank_21"]=0.;mutated["target_ret_21"]=-100.
        b,_=rerank(mutated,layer)
        np.testing.assert_array_equal(a.pred.to_numpy(),b.pred.to_numpy())

if __name__=="__main__":unittest.main()
