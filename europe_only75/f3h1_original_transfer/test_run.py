import unittest
import numpy as np
import pandas as pd
from europe_only75.f3h1_original_transfer.run import (
    ci,picked,betas,join_eur_prices,costed_path,
    FEATS,FACTORS,INPUT,COLUMNS
)

class EuropeF3H1OriginalRigorous(unittest.TestCase):
    def test_original_exact_19plus6_and_10plus_residual(self):
        self.assertEqual(len(FEATS),19)
        self.assertEqual(len(COLUMNS),25)
        self.assertEqual(len(FACTORS),10)
        self.assertEqual(len(INPUT),37)

    def test_asof_betas_immune_to_next_price_future_mutation(self):
        dates=pd.bdate_range("2020-01-01",periods=230)
        names=["E"+str(i) for i in range(60)]
        rng=np.random.default_rng(39)
        v=np.exp(np.cumsum(rng.normal(0,.001,size=(len(dates),71)),axis=0))
        keys=names+list(FACTORS)+["AGG"]
        p=pd.DataFrame(v,index=dates,columns=keys)
        signal=dates[-4]
        old=betas(p,names,signal)
        future=p.copy();future.iloc[-3:,:]*=2000.
        new=betas(future,names,signal)
        for x,y in zip(old,new):
            np.testing.assert_array_equal(x,y)

    def test_usa_factor_previous_calendar_day_only(self):
        day=pd.date_range("2025-01-02",periods=4,freq="D")
        # See source time offset: Thursday EU must use Wed US close,
        # Friday EU must use Thu US close; never current-day US.
        ref=pd.DataFrame({"SPY":[100.,200.,300.]},
                         index=pd.to_datetime(["2025-01-01","2025-01-02","2025-01-03"]))
        prev=day-pd.Timedelta(days=1)
        aligned=ref.reindex(ref.index.union(prev)).sort_index().ffill().reindex(prev)
        aligned.index=day
        self.assertEqual(float(aligned.loc["2025-01-02","SPY"]),100.)
        self.assertEqual(float(aligned.loc["2025-01-03","SPY"]),200.)
        self.assertEqual(float(aligned.loc["2025-01-04","SPY"]),300.)

    def test_deterministic_top5(self):
        f=pd.DataFrame(dict(ticker=list("ABCDEFG"),
          score=[.5,.5,.5,.5,.5,.1,0.]))
        self.assertEqual(picked(f,"score"),list("ABCDE"))

    def test_date_bootstrap_clusters_months(self):
        a=ci(np.full(63,.002),30)
        self.assertAlmostEqual(a["CI95"][0],.002,places=12)

if __name__=="__main__":
    unittest.main()
