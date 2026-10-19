import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
import pandas as pd
from isin_first2026.build import check_isin,identify,read_prices,pair_compare,assess

class ISINIdentity(unittest.TestCase):
    def test_true_official_and_bad_isin(self):
        self.assertTrue(check_isin("DE000A0F5UJ7"))
        self.assertTrue(check_isin("IE00BKWQ0H23"))
        self.assertFalse(check_isin("DE000A0F5UJ8"))
        self.assertFalse(check_isin("LU0292100800"))

    def test_never_replace_official_disagreement_with_issuer_claim(self):
        proposals={"TEST.DE":dict(ticker="TEST.DE",catalogs=["issuer"],
             macro_categories=set(["EU_SECTOR"]),proposed_isins=set(["IE00BKWQ0H23"]),
             families=set(),subsectors=set())}
        xetra={"TEST":[dict(ISIN="DE000A0F5UJ7",Mnemonic="TEST",
                **{"MIC Code":"XETR","Product Status":"Active",
                   "Instrument Status":"Active","Instrument Type":"ETF",
                   "Currency":"EUR"})]}
        r=identify(proposals,xetra).iloc[0]
        self.assertEqual(r.status,"ISIN_CONFLICT_ISSUER_VS_XETRA")
        self.assertEqual(r.isin,"")

    def test_venue_return_correlation_cannot_be_relabelled_independent_vendor(self):
        dates=pd.bdate_range("2020-01-01",periods=300)
        v=70*np.exp(np.cumsum(np.random.default_rng(1).normal(0,.01,300)))
        p=pd.DataFrame(index=dates)
        p["Close"]=v;p["Open"]=v;p["High"]=v+1;p["Low"]=v-1;p["Volume"]=100.
        q=p.copy()
        z=pair_compare("AAA.DE","BBB.MI","IE00BKWQ0H23",{"AAA.DE":p,"BBB.MI":q})
        self.assertAlmostEqual(z["daily_return_corr"],1.0,places=10)
        self.assertEqual(z["median_absolute_return_difference_bps"],0)

    def test_no_price_synthesis_for_invalid_ohlc(self):
        p=pd.DataFrame(index=pd.bdate_range("2016-01-01","2026-07-01"))
        for k in ("Open","High","Low","Close"):p[k]=10.
        p["Volume"]=100.
        p.loc[p.index[-300],"High"]=5.
        with TemporaryDirectory() as td:
            f=Path(td)/"x";f.write_text("csv")
            stat=assess("ANY.DE",pd.Series(dict(isin="DE000A0F5UJ7",market="XETR",
                       macro_categories="EU_SECTOR",status="XETRA")),
                        p,f,"TEST_VENDOR_RAW")
            self.assertGreater(stat["bad_envelope"],0)

if __name__=="__main__":unittest.main()
