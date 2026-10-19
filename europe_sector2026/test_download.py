import unittest
from pathlib import Path
import pandas as pd
import numpy as np
from europe_sector2026.download import diagnose_and_normalize

class EuropeSectorYahooTests(unittest.TestCase):
  def test_raw_large_market_moves_retained_and_ohlc_not_modified(self):
    dates=pd.bdate_range("2020-01-01",periods=300)
    q=pd.DataFrame(index=dates)
    q["Open"]=100.
    q["High"]=105.
    q["Low"]=95.
    q["Close"]=100.
    q["Adj Close"]=95.
    q["Volume"]=10.
    q["Dividends"]=0.
    q["Stock Splits"]=0.
    q.iloc[240,q.columns.get_loc("Close")]=180.0
    q.iloc[240,q.columns.get_loc("Adj Close")]=171.0
    q.iloc[240,q.columns.get_loc("High")]=150.0 # deliberately invalid OHLC
    raw,adjusted,metric=diagnose_and_normalize(q)
    self.assertEqual(len(raw),len(q))
    self.assertEqual(len(adjusted),len(q))
    self.assertEqual(raw.loc[dates[240],"High"],150.0)
    self.assertEqual(raw.loc[dates[240],"Close"],180.0)
    self.assertAlmostEqual(adjusted.loc[dates[240],"Close"],171.0)
    self.assertAlmostEqual(adjusted.loc[dates[240],"High"],142.5)
    self.assertGreater(metric["study_bad_ohlc_envelope"],0)
    self.assertGreater(metric["study_abs_adjusted_ret_over_25pct"],0)

  def test_zero_volume_preserved_and_invalid_price_audited(self):
    dates=pd.bdate_range("2019-01-01",periods=280)
    q=pd.DataFrame({c:10. for c in ["Open","High","Low","Close","Adj Close"]},
                   index=dates)
    q["Volume"]=0.
    q.loc[dates[5],"Close"]=np.nan
    raw,adj,stat=diagnose_and_normalize(q)
    self.assertEqual(stat["source_rows"],280)
    self.assertEqual(stat["study_zero_volume"],280)
    self.assertEqual(stat["source_invalid_price_or_adjustment"],1)
    self.assertEqual(len(adj),279)

  def test_catalog_is_30_no_us_or_fx(self):
    cat=pd.read_csv(Path(__file__).with_name("CATALOG.csv"))
    self.assertEqual(len(cat),30)
    self.assertEqual(cat.ticker.nunique(),30)
    self.assertEqual(cat.ticker.str.endswith(".DE").sum(),30)
    self.assertEqual(len(set(cat.sector_11)-{"CONSUMER_MIXED"}),11)
    self.assertEqual(cat[cat.provider.str.startswith("SPDR")].shape[0],11)

if __name__=="__main__":unittest.main()
