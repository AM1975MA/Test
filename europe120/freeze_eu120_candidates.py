#!/usr/bin/env python3
from __future__ import annotations

import json, re, hashlib
from pathlib import Path
import pandas as pd
import yfinance as yf

START='2004-01-01'
END='2026-07-02'
LAST=pd.Timestamp('2026-07-01')
PRE=pd.Timestamp('2017-01-31')
MIN_PRE=252
OUT=Path('europe120/frozen_output')
RAW=OUT/'raw_ticker_csv'
RAW.mkdir(parents=True,exist_ok=True)

CANDIDATES={
'C01_US_BROAD_STYLE':[
'IEUR','IEV','SPEU','HEU.PA','VGK.MX','EZU','EZU.MX','HEZU','CSSX5E.MI','CSX5.AS','CSX5.L','FEZ','SXRT.DE','IEU.AX','IEV.MX','VEUR.SW','DBEU','HEDJ','HEDJ.MX','FEP','FEP.MX','FDD'],
'C02_US_SECTOR_THEME':[
'0BYJ.MU','EUFN','EUFN.MX','EXV1.DE','EXV2.DE','EXV3.DE','EXV4.DE','EXV5.DE','EXV6.DE','EXV7.DE','EXV8.DE','EXV9.DE','EXH1.DE','EXH2.DE','EXH3.DE','EXH4.DE','EXH5.DE','EXH6.DE','EXH8.DE','EXH9.DE'],
'C03_DEVELOPED_GLOBAL':[
'DAX','EWG.MX','EWQ.MX','EWI.MX','EWP.MX','EWN.MX','EWO.MX','EFNL','EFNL.MX','EIRL.MX','GREK','EPOL.MX','EWD.MX','EDEN','EDEN.MX','CMB1.L','CSMIB.MI','SXRY.DE','BBVAI.MC','EWK.MX'],
'C04_EMERGING':[
'IEUS','CES1.L','CSEMUS.MI','SXRJ.DE','DFE','EUDG',
'IEVL.L','CEMS.DE','IEFV.L','IEVL.MI','IEVL.S',
'IEFQ.L','IEQU.MI','CEMQ.DE','IEQU.S',
'MVEU.L','MVEU.MI','EUN0.DE','IMV.L','MVEU.S'],
'C05_BONDS_CASH_CREDIT':[
'SEGA.L','EUNH.DE','IEGA.AS','SEGA.MI','IEGA.S',
'IBGM.L','IBGM.MI','IBCM.DE','IBGM.AS',
'ICOV.MI','IUS6.DE','IUS6.AS','ICOV.S',
'ERNE.L','ERNE.MI','IS3M.DE','ERNE.AS','ERN1.L','ERNE.S',
'SXRQ.DE','CE01.L','IEBB.MI','IS06.DE'],
'C06_REAL_ASSETS':[
'IPRP.L','IPRP.AS','IQQP.DE','IPRP.S',
'ZPRP.DE','EURE.S',
'D5BK.DE','XDER.MI','XDER.L',
'IFEU','IFEU.MX','EXH1.S',
'UTI.MI','UTI.PA','LUTI.DE','SC0Z.DE',
'BRES.MI','BRES.PA','LBRE.DE','LYBRE.S',
'EXI5.DE','EXI5.S','SXEPEX.DE','SXPPEX.DE','SXOPEX.DE','SX6PEX.DE',
'EPRE.PA','EPRE.L','AMREAL.DE','EPRE.MI'
]}


def dl(sym):
    try:
        d=yf.download(sym,start=START,end=END,auto_adjust=False,actions=False,progress=False,threads=False)
    except Exception as e:
        return None,f'download:{type(e).__name__}:{e}'
    if d is None or d.empty:
        return None,'empty'
    if isinstance(d.columns,pd.MultiIndex):
        d.columns=d.columns.get_level_values(0)
    d=d.reset_index()
    req=['Date','Open','High','Low','Close','Adj Close','Volume']
    if any(c not in d.columns for c in req):
        return None,'missing_columns'
    f=pd.to_numeric(d['Adj Close'],errors='coerce')/pd.to_numeric(d['Close'],errors='coerce').replace(0,pd.NA)
    q=pd.DataFrame({
      'date':pd.to_datetime(d['Date']),
      'Open':pd.to_numeric(d['Open'],errors='coerce')*f,
      'High':pd.to_numeric(d['High'],errors='coerce')*f,
      'Low':pd.to_numeric(d['Low'],errors='coerce')*f,
      'Close':pd.to_numeric(d['Adj Close'],errors='coerce'),
      'Volume':pd.to_numeric(d['Volume'],errors='coerce')
    }).dropna().sort_values('date').drop_duplicates('date',keep='last')
    npre=int((q.date<=PRE).sum())
    if npre<MIN_PRE: return None,f'pre2017:{npre}'
    if q.empty or q.date.max()<LAST: return None,'ends_early'
    return q[q.date<=LAST].copy(),None

sel=[]; rej=[]; data={}
for cat,cands in CANDIDATES.items():
    n=0
    for s in cands:
        if n>=20: break
        q,err=dl(s)
        if q is None:
            rej.append({'ticker':s,'macro_category':cat,'reason':err})
            print('REJECT',cat,s,err,flush=True)
            continue
        n+=1; data[s]=q
        sel.append({'ticker':s,'macro_category':cat,'rows':len(q),'first':str(q.date.min().date()),'last':str(q.date.max().date()),'pre2017_rows':int((q.date<=PRE).sum())})
        print('SELECT',cat,n,'/20',s,flush=True)
    if n!=20:
        pd.DataFrame(sel).to_csv(OUT/'partial_selected.csv',index=False)
        pd.DataFrame(rej).to_csv(OUT/'rejected.csv',index=False)
        raise RuntimeError(f'{cat} only {n}/20')

if len(sel)!=120: raise RuntimeError(len(sel))
for r in sel:
    s=r['ticker']; q=data[s].copy(); q['date']=q.date.dt.strftime('%Y-%m-%d')
    q.to_csv(RAW/f"{re.sub(r'[^A-Za-z0-9._-]','_',s)}.csv",index=False,float_format='%.17g')
pd.DataFrame(sel)[['ticker','macro_category']].to_csv(RAW/'universe.csv',index=False)
pd.DataFrame(sel).to_csv(OUT/'coverage.csv',index=False)
pd.DataFrame(rej).to_csv(OUT/'rejected.csv',index=False)
for fld in ['Open','High','Low','Close','Volume']:
    pd.concat([data[s].set_index('date')[[fld]].rename(columns={fld:s}) for s in data],axis=1).sort_index().to_parquet(OUT/f'{fld.upper()}.parquet')
manifest={'status':'EU120_FROZEN','provider':'Yahoo Finance via yfinance','requested_start':START,'last_included':'2026-07-01','evaluation_start':'2017-02-01','selected_count':120,'per_cluster':20,'performance_used_for_selection':False,'selected':sel}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k!='selected'},indent=2),flush=True)
