#!/usr/bin/env python3
from pathlib import Path
import io, requests
import numpy as np
import pandas as pd
import yfinance as yf

ROOT=Path('prices/titanium_retrained_output')
FIELDS=['Open','High','Low','Close','Volume']

def direct(t,start,end):
    try:
        p1=int(pd.Timestamp(start,tz='UTC').timestamp()); p2=int(pd.Timestamp(end,tz='UTC').timestamp())
        url=f'https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplits&includeAdjustedClose=true'
        r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=60); r.raise_for_status()
        res=r.json().get('chart',{}).get('result') or []
        if not res: return pd.DataFrame()
        z=res[0]; q=z['indicators']['quote'][0]; adj=(z['indicators'].get('adjclose') or [{}])[0].get('adjclose',q.get('close'))
        idx=pd.to_datetime(z['timestamp'],unit='s',utc=True).tz_convert(None).normalize()
        raw=pd.DataFrame({'Open':q.get('open'),'High':q.get('high'),'Low':q.get('low'),'Close':q.get('close'),'Volume':q.get('volume'),'Adj Close':adj},index=idx)
        raw=raw[~raw.index.duplicated(keep='last')].sort_index()
        fac=raw['Adj Close']/raw['Close'].replace(0,np.nan)
        for f in ['Open','High','Low','Close']: raw[f]=raw[f]*fac
        return raw[FIELDS].dropna(how='all')
    except Exception as e:
        print(t,'Yahoo direct failed',repr(e)); return pd.DataFrame()

def yfdl(t,start,end):
    try:
        x=yf.download(t,start=start,end=end,auto_adjust=True,actions=False,repair=True,progress=False,threads=False,multi_level_index=False,timeout=60)
        if isinstance(x.columns,pd.MultiIndex): x.columns=x.columns.get_level_values(0)
        if x.empty: return pd.DataFrame()
        x.index=pd.to_datetime(x.index).tz_localize(None).normalize()
        x=x[~x.index.duplicated(keep='last')].sort_index()
        return x[FIELDS].apply(pd.to_numeric,errors='coerce').dropna(how='all')
    except Exception as e:
        print(t,'yf failed',repr(e)); return pd.DataFrame()

def stooq_pin():
    try:
        url='https://stooq.com/q/d/l/?s=pin.us&i=d&d1=20050101&d2=20260220'
        r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=60); r.raise_for_status()
        x=pd.read_csv(io.StringIO(r.text))
        if 'Date' not in x or len(x)<252: return pd.DataFrame()
        x['Date']=pd.to_datetime(x['Date']).dt.normalize(); x=x.set_index('Date').rename(columns=str.title)
        return x[FIELDS].apply(pd.to_numeric,errors='coerce').dropna(how='all')
    except Exception as e:
        print('PIN Stooq failed',repr(e)); return pd.DataFrame()

def best(t,start,end,min_rows=5):
    x=direct(t,start,end)
    if len(x)>=min_rows: return x
    x=yfdl(t,start,end)
    return x

vug=best('VUG','2005-01-01','2026-08-12',252)
if len(vug)<252: raise RuntimeError(f'VUG insufficient rows {len(vug)}')

# PIN was renamed IMVP on 2026-02-23. Prefer the successor ticker's complete
# backfilled economic history; it is the same fund and avoids a false break.
imvp_full=best('IMVP','2005-01-01','2026-08-12',252)
if len(imvp_full)>=252:
    pin=imvp_full.copy()
    print('PIN reconstructed from full IMVP backfilled history:',pin.index.min(),pin.index.max(),len(pin))
else:
    print('IMVP full history unavailable, falling back to pre/post stitching; rows',len(imvp_full))
    pin_old=best('PIN','2005-01-01','2026-02-21',252)
    if len(pin_old)<252:
        pin_old=stooq_pin()
        print('PIN old history using Stooq fallback',len(pin_old))
    if len(pin_old)<252: raise RuntimeError(f'PIN pre-rename insufficient rows {len(pin_old)}')
    imvp=best('IMVP','2026-02-23','2026-08-12',5)
    if len(imvp)<5: raise RuntimeError(f'IMVP successor insufficient rows {len(imvp)}')
    pin=pd.concat([pin_old,imvp]).sort_index(); pin=pin[~pin.index.duplicated(keep='last')]
    print('PIN/IMVP stitched continuity:',pin_old.index.min(),pin_old.index.max(),len(pin_old),'->',imvp.index.min(),imvp.index.max(),len(imvp),'combined',len(pin))

for ticker,raw in [('VUG',vug),('PIN',pin)]:
    raw=raw.copy(); raw.index=pd.to_datetime(raw.index).normalize()
    for f in FIELDS:
        mat=pd.read_parquet(ROOT/f'{f.upper()}.parquet'); mat.index=pd.to_datetime(mat.index).tz_localize(None).normalize()
        aligned=pd.to_numeric(raw[f],errors='coerce').reindex(mat.index)
        if int(aligned.notna().sum())<252:
            raise RuntimeError(f'{ticker} {f} alignment failed: {int(aligned.notna().sum())} rows')
        mat[ticker]=aligned
        mat.to_parquet(ROOT/f'{f.upper()}.parquet',compression='zstd')
    print(ticker,'rows',len(raw),'first',raw.index.min(),'last',raw.index.max(),'close_nonnull',int(raw.Close.notna().sum()))
