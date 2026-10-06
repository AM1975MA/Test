#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import yfinance as yf
START='2004-01-01'; END='2026-07-02'; PRE=pd.Timestamp('2017-01-31'); LAST=pd.Timestamp('2026-07-01')
QUERIES=[
'iShares MSCI Europe Financials ETF','iShares STOXX Europe 600 Banks UCITS ETF',
'iShares STOXX Europe 600 Technology UCITS ETF','iShares STOXX Europe 600 Health Care UCITS ETF',
'iShares STOXX Europe 600 Financial Services UCITS ETF','iShares STOXX Europe 600 Insurance UCITS ETF',
'iShares STOXX Europe 600 Media UCITS ETF','iShares STOXX Europe 600 Retail UCITS ETF',
'Europe banks ETF','Europe financials ETF','Europe technology ETF','Europe healthcare ETF','Europe insurance ETF','Europe media ETF','Europe retail ETF'
]
seen={}; rows=[]
for q in QUERIES:
  try: qq=getattr(yf.Search(q,max_results=50,news_count=0),'quotes',None) or []
  except Exception as e: print('SEARCHFAIL',q,e); continue
  for r in qq:
    s=str(r.get('symbol') or '').upper().strip(); typ=str(r.get('quoteType') or '').upper(); name=str(r.get('longname') or r.get('shortname') or '')
    if not s or typ!='ETF' or s in seen: continue
    seen[s]=1
    try: d=yf.download(s,start=START,end=END,auto_adjust=False,actions=False,progress=False,threads=False)
    except Exception: d=None
    if d is None or d.empty: rows.append({'ticker':s,'name':name,'valid':False}); continue
    if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
    d=d.reset_index(); dates=pd.to_datetime(d['Date']) if 'Date' in d else pd.Series([],dtype='datetime64[ns]')
    npre=int((dates<=PRE).sum()); last=dates.max() if len(dates) else pd.NaT; ok=npre>=252 and pd.notna(last) and last>=LAST
    rows.append({'ticker':s,'name':name,'valid':ok,'pre2017_rows':npre,'last':str(last.date()) if pd.notna(last) else ''})
    if ok: print('VALID',s,name,flush=True)
out=Path('europe120/c02_probe');out.mkdir(parents=True,exist_ok=True);df=pd.DataFrame(rows);df.to_csv(out/'probe.csv',index=False);df[df.valid==True].to_csv(out/'valid.csv',index=False);print(df[df.valid==True][['ticker','name']].to_string(index=False),flush=True)
