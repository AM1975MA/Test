"""Offline unit tests for source lock, OHLC normalization, point-in-time bounds."""
import unittest
from pathlib import Path
import pandas as pd
import numpy as np
import capture_asof as C

class FrozenCapture(unittest.TestCase):
 def test_universe_and_manifest(self):
  u,a=C.validate_local_source()
  self.assertEqual(u.groupby('market').size().to_dict(),{'EU':165,'USA':149})
  self.assertEqual(len(a),2677)
 def test_price_clean_rejects_bad_bar(self):
  index=pd.to_datetime(['2026-06-30','2026-07-01','2026-07-02'])
  df=pd.DataFrame({'Open':[9,10,11],'High':[11,12,13],'Low':[8,9,10],
                   'Close':[10,11,12],'Adj Close':[8,8.8,9.6], 'Volume':[1,2,3]},index=index)
  q=C.clean_download(df)
  self.assertAlmostEqual(float(q.loc[index[0],'adj_close']),8.0,places=8)
  self.assertAlmostEqual(float(q.loc[index[1],'adj_open']),8.0,places=8)
  bad=df.copy();bad.loc[index[0],'Low']=20
  with self.assertRaises(ValueError):C.clean_download(bad)
 def test_anchor_matches_no_future(self):
  idx=pd.to_datetime(['2026-06-22','2026-06-23','2026-06-24','2026-06-25','2026-06-26','2026-06-29','2026-06-30','2026-07-01','2026-07-02'])
  q=pd.DataFrame({'adj_close':np.arange(20.,29.)},index=idx)
  a=pd.DataFrame({'date':idx[:8].strftime('%Y-%m-%d'),'close':np.arange(20.,28.)*2})
  r=C.align_original(q,a)
  self.assertAlmostEqual(r['scale_to_olc19'],2.0)
  self.assertFalse(r['overlap_warning'])
  a.loc[0,'close']=50
  r2=C.align_original(q,a)
  self.assertTrue(r2['overlap_warning'])
 def test_duplicate_source_is_fatal(self):
  p=Path(__file__).resolve().parent/'data/SOURCE_MANIFEST.json'
  self.assertTrue(p.exists())

if __name__=='__main__':unittest.main(verbosity=2)
