"""Technical resolution of the frozen roster, never a performance-selected replacement."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
import pandas as pd
import capture_prices as c
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'source_complete'
def main():
 OUT.mkdir(exist_ok=True);(OUT/'metadata').mkdir(exist_ok=True);c.OUT=OUT
 old=pd.read_csv(ROOT/'source_capture/ROSTER_RESOLUTION.csv').set_index('isin')
 official=pd.read_csv(ROOT/'exchange_metadata/OFFICIAL_LISTING_MAP.csv').set_index('isin')
 aliases=pd.read_csv(ROOT/'EXCHANGE_ALIASES.csv').set_index('isin')
 known=set((ROOT/'KNOWN_LISTING_TOKENS.txt').read_text().split());rows=[];sources=[]
 for row in pd.read_csv(ROOT/'CANDIDATES_FROZEN.csv').to_dict('records'):
  isin=row['isin'];choices=[];authority=[]
  if isin in old.index and pd.notna(old.loc[isin,'symbol']):choices.append(old.loc[isin,'symbol'])
  if isin in official.index and pd.notna(official.loc[isin,'yahoo_symbol']):choices.append(official.loc[isin,'yahoo_symbol']);authority.append(official.loc[isin,'source_url'])
  if isin in aliases.index:choices.append(aliases.loc[isin,'symbol']);authority.append(aliases.loc[isin,'source_url'])
  prior=sorted(set(choices)&known)
  if prior:row.update(status='EXCLUDED_PRIOR_ALIAS',prior_aliases=';'.join(prior),symbol='')
  elif not choices:row.update(status='UNRESOLVED_OFFICIAL_EUR_IDENTITY',symbol='')
  else:
   choices=sorted(set(choices),key=lambda s:(next(j for j,x in enumerate(c.SUFFIXES) if s.endswith(x)),s))
   row.update(status='MAPPED_BEFORE_PRICES',symbol=choices[0],verified_aliases=';'.join(choices),identity_sources=';'.join(authority))
  rows.append(row)
 pd.DataFrame(rows).to_csv(OUT/'ROSTER_RESOLUTION_PRE_DOWNLOAD.csv',index=False)
 print('FROZEN_MAPPING',pd.DataFrame(rows)[['isin','symbol','status']].to_string(index=False),flush=True)
 for row in rows:
  if row['status']!='MAPPED_BEFORE_PRICES':continue
  try:
   r=c.capture(row['symbol'],'candidate',row['isin']);row['status']=r['status'];sources.append(r)
  except Exception as e:row.update(status='PRICE_CAPTURE_FAILED',error=repr(e))
  print('CAPTURE',row['isin'],row['symbol'],row['status'],flush=True)
 for s in ['EXSA.DE','SPY','HYG','IEF']:
  try:sources.append(c.capture(s,'context_only','KNOWN_INPUT_NOT_HOLDOUT'))
  except Exception as e:sources.append(dict(symbol=s,role='context_only',status='FAILED',error=repr(e)))
 pd.DataFrame(rows).to_csv(OUT/'ROSTER_RESOLUTION.csv',index=False)
 pd.DataFrame(sources).to_csv(OUT/'COVERAGE_QA.csv',index=False)
 manifest=dict(status='CAPTURE_COMPLETED_WITH_EXPLICIT_GATES',captured_at_utc=datetime.now(timezone.utc).isoformat(),
  provider='Yahoo Finance / yfinance',version=c.yf.__version__,end_exclusive=c.END,
  candidate_isins_changed=False,prior_source_preserved=True,actual_TradeRepublic_fills=False,prospective=False,
  sources=sources,files={str(p.relative_to(OUT)):c.sha(p) for p in OUT.rglob('*') if p.is_file()})
 (OUT/'MANIFEST.json').write_text(json.dumps(manifest,indent=2))
 print('SUMMARY',pd.DataFrame(rows).status.value_counts().to_dict(),flush=True)
 assert sum(s.get('role')=='candidate' and s.get('status','').startswith('CAPTURED') for s in sources)>=12
if __name__=='__main__':main()
