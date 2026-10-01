#!/usr/bin/env python3
"""EU110 frozen P45 zero-shot transfer runner.

Stage 'download' uses yfinance on the canonical raw window and persists the
five OHLCV matrices. Stage 'p45' is intentionally fail-closed until the exact
frozen P45 transfer path from Trader_selector is located; it must not silently
retrain on EU110 data.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent
UNIVERSE = ROOT / 'eu110_universe.csv'
OUT = ROOT / 'eu110_output'
START = '2004-01-01'
END = '2026-07-02'


def download():
    OUT.mkdir(parents=True, exist_ok=True)
    u = pd.read_csv(UNIVERSE)
    fields = {k: {} for k in ['OPEN','HIGH','LOW','CLOSE','VOLUME']}
    audit=[]
    for i,row in u.iterrows():
        t=row['ticker']
        df=yf.download(t,start=START,end=END,auto_adjust=False,actions=False,progress=False,threads=False)
        if isinstance(df.columns,pd.MultiIndex):
            df.columns=df.columns.get_level_values(0)
        if df.empty:
            raise RuntimeError(f'{t}: empty')
        need=['Open','High','Low','Close','Adj Close','Volume']
        miss=[c for c in need if c not in df.columns]
        if miss: raise RuntimeError(f'{t}: missing {miss}')
        fac=(df['Adj Close']/df['Close']).replace([np.inf,-np.inf],np.nan)
        for src,dst in [('Open','OPEN'),('High','HIGH'),('Low','LOW'),('Close','CLOSE')]:
            fields[dst][t]=(df[src]*fac).astype(float)
        fields['VOLUME'][t]=df['Volume'].astype(float)
        pre=int((pd.to_datetime(df.index)<pd.Timestamp('2017-01-01')).sum())
        audit.append({'ticker':t,'macro_category':row['macro_category'],'rows':len(df),'first':str(df.index.min().date()),'last':str(df.index.max().date()),'pre2017_rows':pre})
        print(f'DOWNLOAD {i+1:03d}/110 {t} rows={len(df)} pre2017={pre}',flush=True)
    for name,cols in fields.items():
        m=pd.concat(cols,axis=1).sort_index()
        m.index.name='Date'
        m.to_parquet(OUT/f'{name}.parquet')
    pd.DataFrame(audit).to_csv(OUT/'COVERAGE.csv',index=False)
    (OUT/'DOWNLOAD_MANIFEST.json').write_text(json.dumps({'count':len(u),'start':START,'end':END,'categories':u.groupby('macro_category').size().to_dict()},indent=2))
    print('EU110 DOWNLOAD COMPLETE',flush=True)


def p45(trader_selector: Path):
    # Fail closed: exact transfer must use the frozen original-training model
    # path; never fit on EU110 observations.
    candidates=[
        trader_selector/'docs'/'V2_HOLDOUT100_ZERO_SHOT_TRANSFER_20260928.md',
        trader_selector/'research'/'p45_continuous_posterior_router_20260928'/'run_p45_local.py',
    ]
    for p in candidates:
        print(f'FOUND {p}: {p.exists()}',flush=True)
    raise RuntimeError('P45 transfer adapter not yet bound; refusing to retrain on EU110. Bind exact frozen zero-shot inference path first.')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--stage',choices=['download','p45'],required=True); ap.add_argument('--trader-selector',type=Path)
    a=ap.parse_args()
    if a.stage=='download': download()
    else: p45(a.trader_selector)
