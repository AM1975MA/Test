#!/usr/bin/env python3
"""OLC100 frozen universe - diagnose Yahoo quote anomalies, not repair them."""
from __future__ import annotations
import argparse,traceback,datetime,json
from pathlib import Path
import numpy as np,pandas as pd
import yfinance as yf
TICKERS={
'EU':['BEL.BR','EL4G.DE','EL4X.DE','EM1015.MI','IMIB.MI','IQQA.DE','ISFA.AS','LYXIB.MC','SYB3.DE','TELE.PA','UTI.MI'],
'USA':['CORN','DGS','EPP','EWD','EWG','EWI','RWO','RWX','SCHB','USL']
}

def inspect(df,market,ticker,method):
 x={'market':market,'ticker':ticker,'method':method,'status':'OK','shape':str(df.shape)}
 try:
  x['original_columns']=repr(df.columns.to_list())[:800]
  if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
  x['columns']=repr(df.columns.to_list())[:800]
  dup=df.columns[df.columns.duplicated()].tolist()
  x['duplicate_columns']=str(dup)
  if dup:
   x['status']='DUPLICATE_COLUMNS';return x
  if df.empty:x['status']='EMPTY';return x
  cols=['Open','High','Low','Close','Adj Close']
  if any(k not in df.columns for k in cols):x['status']='MISSING_FIELDS';return x
  d=df.loc[:,cols].dropna()
  if d.empty:x['status']='ALL_NAN';return x
  x['rows']=int(len(d))
  x['first']=str(d.index[0]);x['last']=str(d.index[-1])
  badlo=(d['Low']>d[['Open','Close']].min(axis=1)*1.000001)
  badhi=(d['High']<d[['Open','Close']].max(axis=1)*.999999)
  x['bad_low_count']=int(badlo.sum());x['bad_high_count']=int(badhi.sum())
  x['max_low_violation_pct']=float(np.max(np.maximum(d['Low']/d[['Open','Close']].min(axis=1)-1,0))*100)
  x['max_high_violation_pct']=float(np.max(np.maximum(d[['Open','Close']].max(axis=1)/d['High']-1,0))*100)
  if badlo.any() or badhi.any():
   z=d.loc[badlo|badhi]
   x['bad_sample']=z.head(3).reset_index().astype(str).to_dict('records')
   x['status']='OHLC_GEOMETRY_ERROR'
  return x
 except Exception as e:
  x['status']='EXCEPTION';x['error']=str(e);return x

def main():
 p=argparse.ArgumentParser();p.add_argument('--asof',default='2026-11-12');p.add_argument('--out',default='olc100_diagnostics');a=p.parse_args()
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 today=datetime.datetime.now(datetime.timezone.utc).date()
 if datetime.date.fromisoformat(a.asof)>today:raise ValueError('future asof')
 result=[]
 for market,tickers in TICKERS.items():
  for t in tickers:
   end=str(datetime.date.fromisoformat(a.asof)+datetime.timedelta(days=1))
   for method in ['download','ticker_history']:
    try:
     if method=='download':df=yf.download(t,start='2026-06-19',end=end,auto_adjust=False,actions=False,threads=False,progress=False,timeout=30)
     else:df=yf.Ticker(t).history(start='2026-06-19',end=end,auto_adjust=False,actions=False,timeout=30)
     record=inspect(df.copy(),market,t,method)
     if record['status']=='OK':
      (out/f'{market}_{t.replace("/","_")}_{method}.csv').write_text(df.to_csv(index=True))
    except Exception as e:record={'market':market,'ticker':t,'method':method,'status':'PROVIDER_EXCEPTION','error':str(e)}
    result.append(record)
    print('OLC100_DIAGNOSTIC',market,t,method,record['status'],record.get('bad_low_count'),record.get('bad_high_count'),flush=True)
 (out/'DIAGNOSTICS.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
 pd.DataFrame([{k:v for k,v in r.items() if k!='bad_sample'} for r in result]).to_csv(out/'DIAGNOSTICS.csv',index=False)
 print('OLC100_DIAGNOSTIC_COMPLETE',len(result),flush=True)
if __name__=='__main__':main()
