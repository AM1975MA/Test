"""Acquire the prespecified same-ISIN alternate EUR listings, no performance selection."""
from pathlib import Path
from datetime import datetime,timezone
import json
import pandas as pd
import capture_prices as c
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'source_alternates'
def main():
 OUT.mkdir(exist_ok=True);(OUT/'metadata').mkdir(exist_ok=True);c.OUT=OUT
 roster=pd.read_csv(ROOT/'ALTERNATE_LISTINGS.csv');known=set((ROOT/'KNOWN_LISTING_TOKENS.txt').read_text().split());rows=[]
 for row in roster.to_dict('records'):
  assert row['symbol'] not in known, 'Previously studied alternate listing: '+row['symbol']
  try:row.update(c.capture(row['symbol'],'candidate',row['isin']))
  except Exception as e:row.update(status='CAPTURE_FAILED',error=repr(e))
  rows.append(row);print('ALT',row,flush=True)
 pd.DataFrame(rows).to_csv(OUT/'COVERAGE_QA.csv',index=False)
 (OUT/'MANIFEST.json').write_text(json.dumps({'status':'ALTERNATE_CAPTURE_COMPLETE','captured_at_utc':datetime.now(timezone.utc).isoformat(),'roster_sha256':c.sha(ROOT/'ALTERNATE_LISTINGS.csv'),'funds_unchanged':True,'prospective':False,'sources':rows,'files':{str(p.relative_to(OUT)):c.sha(p) for p in OUT.rglob('*') if p.is_file()}},indent=2))
 assert all(r['status'].startswith('CAPTURED') for r in rows), 'Some prespecified alternate histories unavailable; inspect before model test.'
if __name__=='__main__':main()
