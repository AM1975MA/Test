#!/usr/bin/env python3
import pandas as pd, yfinance as yf
CANDS=['DBEZ.MX','FEUZ.MX','DBEU.MX','SPEU.MX','IEUR.MX','HEZU.MX','FEZ.MX','FDD.MX','DFE.MX','EUDG.MX','IEUS.MX','FEP.MX','HEDJ.MX','EZU.MX','IEV.MX','EFNL.MX','EDEN.MX','GREK.MX','VGK.MX','EUFN.MX']
PRE=pd.Timestamp('2017-01-31'); LAST=pd.Timestamp('2026-07-01')
valid=[]
for s in CANDS:
    try:
        d=yf.download(s,start='2004-01-01',end='2026-07-02',auto_adjust=False,actions=False,progress=False,threads=False)
        if d is None or d.empty: continue
        if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
        d=d.reset_index(); dt=pd.to_datetime(d['Date'])
        if int((dt<=PRE).sum())>=252 and dt.max()>=LAST:
            print('VALID',s,flush=True); valid.append(s)
    except Exception as e: print('ERR',s,e,flush=True)
print('VALID_COUNT',len(valid),valid,flush=True)
