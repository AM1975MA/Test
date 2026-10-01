#!/usr/bin/env python3
import json
from pathlib import Path
import pandas as pd
import yfinance as yf

START='2004-01-01'; END='2026-07-02'; PRE=pd.Timestamp('2017-01-31'); LAST=pd.Timestamp('2026-07-01')
QUERIES=[
'iShares European Property Yield UCITS ETF',
'SPDR FTSE EPRA Europe ex UK Real Estate UCITS ETF',
'Xtrackers FTSE EPRA NAREIT Developed Europe Real Estate UCITS ETF',
'iShares STOXX Europe 600 Real Estate UCITS ETF',
'iShares STOXX Europe 600 Oil Gas UCITS ETF',
'iShares STOXX Europe 600 Basic Resources UCITS ETF',
'iShares STOXX Europe 600 Construction Materials UCITS ETF',
'iShares STOXX Europe 600 Utilities UCITS ETF',
'Invesco European Utilities Sector UCITS ETF',
'Amundi STOXX Europe 600 Utilities UCITS ETF',
'Amundi STOXX Europe 600 Basic Resources UCITS ETF',
'Amundi STOXX Europe 600 Oil Gas UCITS ETF',
'Amundi STOXX Europe 600 Construction Materials UCITS ETF',
'Lyxor STOXX Europe 600 Utilities ETF',
'Lyxor STOXX Europe 600 Basic Resources ETF',
'Lyxor STOXX Europe 600 Oil Gas ETF',
'Europe infrastructure UCITS ETF',
'Europe real estate ETF',
'Europe property ETF',
'Europe utilities ETF',
'Europe basic resources ETF',
'Europe materials ETF',
'Europe energy ETF',
]
seen={}; rows=[]
for q in QUERIES:
    try: quotes=getattr(yf.Search(q,max_results=50,news_count=0),'quotes',None) or []
    except Exception as e:
        print('SEARCHFAIL',q,e,flush=True); continue
    for r in quotes:
        s=str(r.get('symbol') or '').upper().strip(); typ=str(r.get('quoteType') or '').upper(); name=str(r.get('longname') or r.get('shortname') or '')
        if not s or typ!='ETF' or s in seen: continue
        seen[s]=(q,name)
        try: d=yf.download(s,start=START,end=END,auto_adjust=False,actions=False,progress=False,threads=False)
        except Exception as e:
            rows.append({'ticker':s,'name':name,'query':q,'valid':False,'reason':type(e).__name__}); continue
        if d is None or d.empty:
            rows.append({'ticker':s,'name':name,'query':q,'valid':False,'reason':'empty'}); continue
        if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
        d=d.reset_index(); dates=pd.to_datetime(d['Date']) if 'Date' in d else pd.Series([],dtype='datetime64[ns]')
        npre=int((dates<=PRE).sum()); last=dates.max() if len(dates) else pd.NaT
        valid=npre>=252 and pd.notna(last) and last>=LAST
        rows.append({'ticker':s,'name':name,'query':q,'valid':bool(valid),'reason':'' if valid else f'pre={npre};last={last}','pre2017_rows':npre,'last':str(last.date()) if pd.notna(last) else ''})
        if valid: print('VALID',s,name,flush=True)
out=Path('europe120/c06_probe'); out.mkdir(parents=True,exist_ok=True)
pd.DataFrame(rows).to_csv(out/'probe.csv',index=False)
valid=pd.DataFrame(rows); valid=valid[valid.valid==True] if len(valid) else valid
valid.to_csv(out/'valid.csv',index=False)
print('VALID_COUNT',len(valid),flush=True)
print(valid[['ticker','name']].to_string(index=False) if len(valid) else 'NONE',flush=True)
