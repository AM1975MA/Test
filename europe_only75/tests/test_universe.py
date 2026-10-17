"""Fail-closed research universe invariants, no performance-based category filter."""
import csv,json,hashlib,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"europe_only75"
SRC=ROOT/"data/eu120"
def read(name):return list(csv.DictReader((BASE/name).open()))
class EuropeOnlyUniverse(unittest.TestCase):
    def test_all_120_decisions_and_75_europe_only_tickers(self):
        old=list(csv.DictReader((SRC/"raw_ticker_csv/universe.csv").open()))
        audit=read("GEOGRAPHY_AUDIT.csv")
        keep=read("UNIVERSE_EUROPE_ONLY.csv")
        eur=read("UNIVERSE_EUR_LISTED_60.csv")
        self.assertEqual((len(old),len(audit),len(keep),len(eur)),(120,120,75,60))
        original=set(x["ticker"] for x in old)
        retained=set(x["ticker"] for x in keep)
        euro=set(x["ticker"] for x in eur)
        self.assertEqual(len(original),120)
        self.assertEqual(original,set(x["ticker"] for x in audit))
        self.assertEqual(retained,set(x["ticker"] for x in audit if x["decision"]=="KEEP"))
        self.assertEqual(original-retained,set(x["ticker"] for x in audit if x["decision"]=="EXCLUDE"))
        self.assertEqual(len(euro),60)
        self.assertTrue(euro.issubset(retained))
        self.assertTrue(all(x["macro_category"].startswith("EU_") for x in keep))
        self.assertTrue(all(x["ticker"].endswith((".DE",".MI",".AS",".PA",".MC")) for x in eur))
    def test_no_poorly_grounded_global_or_US_funds(self):
        excluded=set(x["ticker"] for x in read("GEOGRAPHY_AUDIT.csv") if x["decision"]=="EXCLUDE")
        for t in ("SXR8.DE","IQQH.DE","IQQW.DE","EUNL.DE","EUNM.DE",
                  "IS3N.DE","IUSQ.DE","ZPRG.DE","ZPRV.DE","SPY5.DE",
                  "4GLD.DE","IDTL.L","SEMB.L","IEBB.MI","IS3M.DE",
                  "IEUR","EZU","IEUS","DAX","GREK"):
            self.assertIn(t,excluded)
    def test_original_source_hash_pinned(self):
        m=(SRC/"manifest.json").read_bytes()
        p=json.loads((SRC/"PROVENANCE.json").read_text())
        local=json.loads((BASE/"MANIFEST.json").read_text())
        digest=hashlib.sha256(m).hexdigest()
        self.assertEqual(p["source_manifest_sha256"],digest)
        self.assertEqual(local["source_eu120_manifest_sha256"],digest)
        self.assertEqual(local["retained_count"],75)
        self.assertEqual(local["excluded_count"],45)
if __name__=="__main__":unittest.main()
