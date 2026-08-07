#!/usr/bin/env python3
from pathlib import Path
import pandas as pd, yfinance as yf
ROOT=Path('prices/titanium_retrained_output')
fields=['Open','High','Low','Close','Volume']
for t in ['VUG','PIN']:
    raw=yf.download(t,start='2005-01-01',end='2026-08-08',auto_adjust=True,actions=False,repair=True,progress=False,threads=False,multi_level_index=False,timeout=60)
    if raw.empty or len(raw)<252: raise RuntimeError(f'{t}: insufficient rows {len(raw)}')
    raw.index=pd.to_datetime(raw.index).tz_localize(None)
    for f in fields:
        mat=pd.read_parquet(ROOT/f'{f.upper()}.parquet'); mat.index=pd.to_datetime(mat.index).tz_localize(None)
        s=pd.to_numeric(raw[f],errors='coerce').reindex(mat.index)
        mat[t]=s
        mat.to_parquet(ROOT/f'{f.upper()}.parquet',compression='zstd')
    print(t,len(raw),raw.index.min(),raw.index.max())
