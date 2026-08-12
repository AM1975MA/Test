#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd


def find1(root:Path,name:str):
    xs=list(root.rglob(name))
    if not xs: raise FileNotFoundError(f'{name} under {root}')
    return xs[0]

def wide(raw,col):
    z=raw[['date','ticker',col]].copy();z['date']=pd.to_datetime(z.date).dt.tz_localize(None);z['ticker']=z.ticker.astype(str).str.upper()
    return z.pivot_table(index='date',columns='ticker',values=col,aggfunc='last').sort_index()

def compare(a,b,label):
    ix=a.index.intersection(b.index);co=a.columns.intersection(b.columns);x=a.loc[ix,co].to_numpy(float);y=b.loc[ix,co].to_numpy(float);m=np.isfinite(x)&np.isfinite(y)
    d=np.abs(x[m]-y[m]);den=np.maximum(np.abs(y[m]),1e-12);rel=d/den
    return {'label':label,'n':int(m.sum()),'mae':float(d.mean()) if d.size else None,'max_abs':float(d.max()) if d.size else None,'mean_rel':float(rel.mean()) if d.size else None,'p99_rel':float(np.quantile(rel,.99)) if d.size else None,'exact_1e12':float(np.mean(d<=1e-12)) if d.size else None}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--matrix-root',required=True);ap.add_argument('--raw-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();mroot=Path(a.matrix_root);rroot=Path(a.raw_root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    rp=find1(rroot,'DAILY_OHLCV_ACTIONS_150ETF.parquet');raw=pd.read_parquet(rp);raw.columns=[str(c).strip().lower().replace(' ','_') for c in raw.columns]
    missing=[c for c in ['date','ticker','open','close'] if c not in raw.columns]
    if missing: raise RuntimeError(f'raw missing {missing}; cols={list(raw.columns)}')
    if 'adj_close' not in raw.columns:
        for c in ['adjclose','adjusted_close']:
            if c in raw.columns: raw['adj_close']=raw[c];break
    if 'adj_close' not in raw.columns: raw['adj_close']=raw['close']
    raw['adj_close']=pd.to_numeric(raw.adj_close,errors='coerce');raw['close']=pd.to_numeric(raw.close,errors='coerce');raw['open']=pd.to_numeric(raw.open,errors='coerce')
    factor=raw.adj_close/raw.close.where(raw.close.abs()>1e-12);raw['adj_open_rebuilt']=raw.open*factor
    if 'adj_open_calc' in raw.columns: raw['adj_open_calc']=pd.to_numeric(raw.adj_open_calc,errors='coerce')
    op=pd.read_parquet(find1(mroot,'OPEN.parquet'));op.index=pd.to_datetime(op.index).tz_localize(None);op.columns=op.columns.astype(str).str.upper()
    cl=pd.read_parquet(find1(mroot,'CLOSE.parquet'));cl.index=pd.to_datetime(cl.index).tz_localize(None);cl.columns=cl.columns.astype(str).str.upper()
    wr=wide(raw,'open');wa=wide(raw,'adj_open_rebuilt');wc=wide(raw,'close');wac=wide(raw,'adj_close')
    checks=[compare(op,wr,'OPEN_matrix_vs_raw_open'),compare(op,wa,'OPEN_matrix_vs_open_x_adjclose_over_close'),compare(cl,wc,'CLOSE_matrix_vs_raw_close'),compare(cl,wac,'CLOSE_matrix_vs_adj_close')]
    if 'adj_open_calc' in raw.columns: checks.append(compare(op,wide(raw,'adj_open_calc'),'OPEN_matrix_vs_stored_adj_open_calc'))
    summary={'raw_path':str(rp),'matrix_root':str(mroot),'raw_rows':int(len(raw)),'raw_tickers':int(raw.ticker.astype(str).nunique()),'raw_first':str(pd.to_datetime(raw.date).min()),'raw_last':str(pd.to_datetime(raw.date).max()),'raw_columns':list(raw.columns),'open_shape':list(op.shape),'close_shape':list(cl.shape),'checks':checks}
    Path(out/'ADJUSTED_OHLC_AUDIT.json').write_text(json.dumps(summary,indent=2,default=str));pd.DataFrame(checks).to_csv(out/'ADJUSTED_OHLC_CHECKS.csv',index=False);print(json.dumps(summary,indent=2,default=str))
if __name__=='__main__':main()
