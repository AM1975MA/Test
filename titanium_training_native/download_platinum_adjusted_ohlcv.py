#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, time
from pathlib import Path
import numpy as np, pandas as pd


def load_module(path:Path):
    spec=importlib.util.spec_from_file_location('base_spec',str(path)); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def get_series(raw, field:str, ticker:str):
    if raw is None or raw.empty: return None
    if isinstance(raw.columns,pd.MultiIndex):
        if (field,ticker) in raw.columns: return raw[(field,ticker)].copy()
        if (ticker,field) in raw.columns: return raw[(ticker,field)].copy()
        l0=list(raw.columns.get_level_values(0)); l1=list(raw.columns.get_level_values(1))
        if field in l0 and ticker in l1:
            try: return raw[field][ticker].copy()
            except Exception: pass
        if ticker in l0 and field in l1:
            try: return raw[ticker][field].copy()
            except Exception: pass
    elif field in raw.columns:
        return raw[field].copy()
    return None

def download(yf,tickers,start,end):
    return yf.download(tickers,start=start,end=end,auto_adjust=False,actions=True,repair=False,group_by='column',progress=False,threads=True,timeout=60)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--base-module',required=True); ap.add_argument('--output',required=True); ap.add_argument('--start',default='2005-01-01'); ap.add_argument('--end',default='2026-08-03'); a=ap.parse_args()
    import yfinance as yf
    base=load_module(Path(a.base_module)); tickers=list(base.TICKER_CATEGORY.keys()); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    store={k:{} for k in ['Open','High','Low','Close','Volume']}; logs=[]
    fields=['Open','High','Low','Close','Adj Close','Volume']
    for st in range(0,len(tickers),25):
        batch=tickers[st:st+25]; raw=None; err=None
        for attempt in range(4):
            try:
                raw=download(yf,batch,a.start,a.end)
                if raw is None or raw.empty: raise RuntimeError('empty batch')
                break
            except Exception as exc:
                err=repr(exc); time.sleep(2**attempt)
        for t in batch:
            ser={f:get_series(raw,f,t) for f in fields} if raw is not None else {}
            if ser.get('Adj Close') is None or ser.get('Open') is None or ser.get('Close') is None or pd.to_numeric(ser.get('Adj Close'),errors='coerce').notna().sum()<126:
                r1=None; e1=None
                for attempt in range(4):
                    try:
                        r1=download(yf,[t],a.start,a.end)
                        if r1 is None or r1.empty: raise RuntimeError('empty ticker')
                        break
                    except Exception as exc:
                        e1=repr(exc); time.sleep(2**attempt)
                ser={f:get_series(r1,f,t) for f in fields} if r1 is not None else {}
                err=e1 or err
            if any(ser.get(f) is None for f in fields):
                logs.append({'ticker':t,'ok':False,'error':err or 'missing field'}); continue
            idx=pd.DatetimeIndex(ser['Close'].index).tz_localize(None)
            q=pd.DataFrame({f:pd.to_numeric(ser[f],errors='coerce').to_numpy() for f in fields},index=idx).sort_index()
            factor=q['Adj Close']/q['Close'].where(q['Close'].abs()>1e-12)
            adj_open=q['Open']*factor
            adj_high=(q['High']*factor).ffill(limit=3)
            adj_low=(q['Low']*factor).ffill(limit=3)
            adj_close=q['Adj Close'].ffill(limit=3)
            volume=q['Volume'].ffill(limit=3)
            store['Open'][t]=adj_open; store['High'][t]=adj_high; store['Low'][t]=adj_low; store['Close'][t]=adj_close; store['Volume'][t]=volume
            logs.append({'ticker':t,'ok':bool(adj_close.notna().sum()>=126),'rows':int(adj_close.notna().sum()),'first':str(adj_close.first_valid_index()),'last':str(adj_close.last_valid_index())})
    mats={k:pd.DataFrame(v).sort_index().reindex(columns=tickers) for k,v in store.items()}
    for k,x in mats.items(): x.to_parquet(out/f'{k.upper()}.parquet')
    pd.DataFrame(logs).to_csv(out/'PLATINUM_DOWNLOAD_LOG.csv',index=False)
    ok=[t for t in tickers if t in mats['Close'].columns and mats['Close'][t].notna().sum()>=126]
    print('requested',len(tickers),'usable>=126',len(ok),'missing',[t for t in tickers if t not in ok])
    print('range',mats['Close'].index.min(),mats['Close'].index.max())

if __name__=='__main__': main()
