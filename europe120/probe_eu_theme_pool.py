#!/usr/bin/env python3
from pathlib import Path
import pandas as pd, yfinance as yf
START='2004-01-01';END='2026-07-02';PRE=pd.Timestamp('2017-01-31');LAST=pd.Timestamp('2026-07-01')
Q=['Europe dividend ETF','Europe high dividend ETF','Europe quality dividend ETF','Europe growth ETF','Europe value ETF','Europe momentum ETF','Europe minimum volatility ETF','Europe factor ETF','Europe small cap ETF','Europe mid cap ETF','Europe hedged equity ETF','Eurozone hedged equity ETF','Europe AlphaDEX ETF','Eurozone AlphaDEX ETF','Europe smart beta ETF','Europe equal weight ETF','Europe multifactor ETF','Europe income ETF','Europe defensive ETF','Europe cyclicals ETF','Europe consumer ETF','Europe industrial ETF','Europe healthcare ETF','Europe technology ETF','Europe banks ETF','Europe financials ETF']
seen={};rows=[]
for q in Q:
  try: qq=getattr(yf.Search(q,max_results=50,news_count=0),'quotes',None) or []
  except Exception: continue
  for r in qq:
    s=str(r.get('symbol') or '').upper().strip(); typ=str(r.get('quoteType') or '').upper(); name=str(r.get('longname') or r.get('shortname') or '')
    if not s or typ!='ETF' or s in seen: continue
    seen[s]=1
    if not any(k in name.lower() for k in ['europe','eurozone','euro stoxx','emu']): continue
    try:d=yf.download(s,start=START,end=END,auto_adjust=False,actions=False,progress=False,threads=False)
    except Exception:d=None
    if d is None or d.empty:continue
    if isinstance(d.columns,pd.MultiIndex):d.columns=d.columns.get_level_values(0)
    d=d.reset_index();dt=pd.to_datetime(d['Date']);n=int((dt<=PRE).sum());last=dt.max();ok=n>=252 and last>=LAST
    if ok:
      rows.append({'ticker':s,'name':name,'query':q,'pre2017_rows':n,'last':str(last.date())});print('VALID',s,name,flush=True)
out=Path('europe120/theme_probe');out.mkdir(parents=True,exist_ok=True);pd.DataFrame(rows).drop_duplicates('ticker').to_csv(out/'valid.csv',index=False);print('COUNT',len(pd.DataFrame(rows).drop_duplicates('ticker')),flush=True)
