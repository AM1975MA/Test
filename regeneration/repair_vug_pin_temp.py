#!/usr/bin/env python3
from pathlib import Path
import io, time, requests
import pandas as pd, numpy as np, yfinance as yf
ROOT=Path('prices/titanium_retrained_output')
fields=['Open','High','Low','Close','Volume']

def yahoo_direct(t):
    p1=int(pd.Timestamp('2005-01-01',tz='UTC').timestamp()); p2=int(pd.Timestamp('2026-08-08',tz='UTC').timestamp())
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplits&includeAdjustedClose=true'
    r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=60); r.raise_for_status(); z=r.json()['chart']['result'][0]
    q=z['indicators']['quote'][0]; adj=z['indicators'].get('adjclose',[{}])[0].get('adjclose',q['close']); idx=pd.to_datetime(z['timestamp'],unit='s',utc=True).tz_convert(None)
    raw=pd.DataFrame({'Open':q['open'],'High':q['high'],'Low':q['low'],'Close':q['close'],'Volume':q['volume'],'Adj Close':adj},index=idx)
    fac=raw['Adj Close']/raw['Close'].replace(0,np.nan)
    for f in ['Open','High','Low','Close']: raw[f]=raw[f]*fac
    return raw[['Open','High','Low','Close','Volume']].dropna(how='all')

def stooq(t):
    url=f'https://stooq.com/q/d/l/?s={t.lower()}.us&i=d&d1=20050101&d2=20260220'
    r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=60); r.raise_for_status(); x=pd.read_csv(io.StringIO(r.text)); x['Date']=pd.to_datetime(x['Date']); x=x.set_index('Date'); return x.rename(columns=str.title)[fields]

for t in ['VUG','PIN']:
    try: raw=yf.download(t,start='2005-01-01',end='2026-08-08',auto_adjust=True,actions=False,repair=True,progress=False,threads=False,multi_level_index=False,timeout=60)
    except Exception: raw=pd.DataFrame()
    if raw.empty or len(raw)<252:
        try: raw=yahoo_direct(t)
        except Exception as e:
            print(t,'Yahoo direct failed',repr(e)); raw=stooq(t)
    if raw.empty or len(raw)<252: raise RuntimeError(f'{t}: insufficient rows {len(raw)}')
    raw.index=pd.to_datetime(raw.index).tz_localize(None)
    for f in fields:
        mat=pd.read_parquet(ROOT/f'{f.upper()}.parquet'); mat.index=pd.to_datetime(mat.index).tz_localize(None)
        mat[t]=pd.to_numeric(raw[f],errors='coerce').reindex(mat.index)
        mat.to_parquet(ROOT/f'{f.upper()}.parquet',compression='zstd')
    print(t,len(raw),raw.index.min(),raw.index.max(),int(raw['Close'].notna().sum()))
