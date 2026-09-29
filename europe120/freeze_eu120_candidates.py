#!/usr/bin/env python3
from __future__ import annotations

import json, re
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

START='2004-01-01'
END='2026-07-02'
LAST=pd.Timestamp('2026-07-01')
PRE=pd.Timestamp('2017-01-31')
MIN_PRE=252
MAX_ABS_DAILY_RETURN=0.25
OUT=Path('europe120/frozen_output')
RAW=OUT/'raw_ticker_csv'
RAW.mkdir(parents=True,exist_ok=True)

ORIGINAL_149=set('''DIA IJR SCHD QQQ QUAL RSP DGRO IJH IWF HDV MDY SCHB IWM MTUM SCHX SPY IVV VTI VO VB VUG VTV IWD IWN SPLV
PPA SMH SOXX IGV IHI KBE HACK IYT KRE IBB ICLN ITA FDN TAN XBI XLK XLF XLE XLV XLI XLY XLP XLU XLB XRT
ACWI EWL EWP EWA EWN IEFA EFA EWH EWQ EWC EWD EWJ EWG EWI EWU VEA VEU VGK EWK EWO EIRL EIS EPOL ENZL EPP
EWS EWY FXI ASHR INDA VWO EWT IEMG KWEB EEM MCHI TUR AAXJ EWZ EZA EIDO EWM THD EPHE SCHE DEM DGS EPI ARGT
AGG BIL EMB IEF IEI LQD BNDX HYG MUB BND JNK SCHP EDV SHY TLT TIP SHV VGSH VGIT VGLT VCIT VCSH MBB BKLN ANGL
COMT GLD SLV GSG IYR PPLT CPER DBB VNQ DBC GDX PALL BNO DBA GDXJ IAU USO UNG DBO USL RWO RWX WOOD CORN URA'''.split())

# Fixed order. No post-2017 performance statistic is used to select replacements.
CANDIDATES={
'C01_US_BROAD_STYLE':[
    'IEUR','IEV','SPEU','HEU.PA','EZU','HEZU','CSSX5E.MI','CSX5.AS','CSX5.L','FEZ','SXRT.DE','IEU.AX','VEUR.SW','DBEU','FDD','EXSA.DE',
    'SC0E.DE','IMEU.L','IMEU.AS','IQQY.DE','IMEU.MI','CSEMU.MI','SXR7.DE','CEU1.AS','CEU1.L'],
'C02_US_SECTOR_THEME':[
    '0BYJ.MU','EUFN','EXV1.DE','EXV2.DE','EXV3.DE','EXV4.DE','EXV5.DE','EXV6.DE','EXV7.DE','EXV8.DE','EXV9.DE',
    'EXH1.DE','EXH2.DE','EXH3.DE','EXH4.DE','EXH5.DE','EXH6.DE','EXH8.DE','EXH9.DE','EXH7.DE',
    'LIRU.DE','LTUG.DE','LHTC.DE','LYYQ.PA','LYXTNO.PA','LYXHEA.PA','SXQPEX.DE'],
'C03_DEVELOPED_GLOBAL':[
    'DAX','EFNL','GREK','EDEN','CMB1.L','CSMIB.MI','SXRY.DE','BBVAI.MC',
    'IAEX.AS','IAEX.L','ISF.L','ISF.AS','ISF.MI','ISF.S','C40.PA','EXS1.DE',
    'CSEMU.S','SXR7.DE','CEU1.AS','CEU1.L','CSEMU.MI','IMEU.MI','IMEU.S','CSSMI.SW',
    'IUSZ.DE','IQQ0.DE','IQQH.DE','IQQW.DE','XMEU.DE','SXR1.DE','SXR4.DE'],
'C04_EMERGING':[
    'IEUS','CES1.L','CSEMUS.MI','SXRJ.DE','DFE','EUDG','IEVL.L','CEMS.DE','IEFV.L','IEVL.MI','IEFQ.L','IEQU.MI','CEMQ.DE',
    'MVEU.L','MVEU.MI','EUN0.DE','IMV.L','HEDJ','FEP','ZPRX.DE','DX2J.DE'],
'C05_BONDS_CASH_CREDIT':[
    'SEGA.L','EUNH.DE','IEGA.AS','SEGA.MI','IEGA.S','IBGM.L','IBGM.MI','IBCM.DE','IBGM.AS','ICOV.MI','IUS6.DE','IUS6.AS',
    'ICOV.S','ERNE.L','ERNE.MI','IS3M.DE','ERNE.AS','ERN1.L','ERNE.S','SXRQ.DE','CE01.L','IEBB.MI','IS06.DE','IEAC.L'],
'C06_REAL_ASSETS':[
    'IPRP.L','IPRP.AS','IQQP.DE','IPRP.S','ZPRP.DE','EURE.S','D5BK.DE','XDER.MI','XDER.L','IFEU','EXH1.S','UTI.MI','UTI.PA','LUTI.DE',
    'SC0Z.DE','BRES.MI','BRES.PA','LBRE.DE','LYBRE.S','EXI5.DE','EXI5.S','SXEPEX.DE','SXPPEX.DE','SXOPEX.DE','SX6PEX.DE','EPRE.PA','EPRE.L','AMREAL.DE','EPRE.MI',
    'EUNL.DE','SXR8.DE','EXS1.DE','EXS3.DE','EXXT.DE','EUNM.DE','IS3N.DE','IUSQ.DE','SXR1.DE','SXR4.DE','XDWD.DE','XMME.DE','XMEU.DE',
    'ZPRG.DE','ZPRX.DE','ZPRV.DE','SPY5.DE','SPY4.DE','4GLD.DE','XAD5.DE','DBX1MW.DE','DBX1DA.DE','D5BM.DE','D5BI.DE','D5BE.DE',
    'EUN2.DE','EUN4.DE','IQQH.DE','IQQW.DE','IQQ0.DE']}


def dl(sym):
    diag={'raw_rows':0,'dropped_nonpositive':0,'ohlc_envelope_fixes':0}
    if sym in ORIGINAL_149:
        return None,'overlap_original149',None,diag
    if sym.endswith('.MX'):
        return None,'provider_mx_excluded',None,diag
    try:
        d=yf.download(sym,start=START,end=END,auto_adjust=False,actions=False,progress=False,threads=False)
    except Exception as e:
        return None,f'download:{type(e).__name__}:{e}',None,diag
    if d is None or d.empty:
        return None,'empty',None,diag
    if isinstance(d.columns,pd.MultiIndex):
        d.columns=d.columns.get_level_values(0)
    d=d.reset_index()
    req=['Date','Open','High','Low','Close','Adj Close','Volume']
    if any(c not in d.columns for c in req):
        return None,'missing_columns',None,diag
    raw_close=pd.to_numeric(d['Close'],errors='coerce').replace(0,pd.NA)
    adj_close=pd.to_numeric(d['Adj Close'],errors='coerce')
    f=adj_close/raw_close
    q=pd.DataFrame({
        'date':pd.to_datetime(d['Date']),
        'Open':pd.to_numeric(d['Open'],errors='coerce')*f,
        'High':pd.to_numeric(d['High'],errors='coerce')*f,
        'Low':pd.to_numeric(d['Low'],errors='coerce')*f,
        'Close':adj_close,
        'Volume':pd.to_numeric(d['Volume'],errors='coerce')
    }).dropna().sort_values('date').drop_duplicates('date',keep='last')
    q=q[q.date<=LAST].copy()
    diag['raw_rows']=int(len(q))

    # Deterministic provider sanitation, independent of future performance.
    good=(q[['Open','High','Low','Close']]>0).all(axis=1)
    diag['dropped_nonpositive']=int((~good).sum())
    q=q.loc[good].copy()
    if q.empty:
        return None,'no_positive_ohlc',None,diag
    old_hi=q['High'].copy(); old_lo=q['Low'].copy()
    q['High']=q[['Open','High','Low','Close']].max(axis=1)
    q['Low']=q[['Open','High','Low','Close']].min(axis=1)
    diag['ohlc_envelope_fixes']=int(((q['High']!=old_hi)|(q['Low']!=old_lo)).sum())

    npre=int((q.date<=PRE).sum())
    if npre<MIN_PRE:
        return None,f'pre2017:{npre}',None,diag
    if q.date.max()<LAST:
        return None,'ends_early',None,diag
    r=q['Close'].pct_change(fill_method=None).replace([np.inf,-np.inf],np.nan)
    max_abs=float(r.abs().max()) if r.notna().any() else np.nan
    if (not np.isfinite(max_abs)) or max_abs>MAX_ABS_DAILY_RETURN:
        return None,f'quality_jump:{max_abs:.6f}',max_abs,diag
    return q,None,max_abs,diag

sel=[]; rej=[]; audit=[]; data={}; used=set()
for cat,cands in CANDIDATES.items():
    n=0
    for s in cands:
        if n>=20: break
        if s in used:
            rej.append({'ticker':s,'macro_category':cat,'reason':'duplicate_global'})
            continue
        q,err,max_abs,diag=dl(s)
        audit.append({'ticker':s,'macro_category':cat,'accepted':q is not None,'reason':err or 'ok','max_abs_daily_return':max_abs,**diag})
        if q is None:
            rej.append({'ticker':s,'macro_category':cat,'reason':err})
            print('REJECT',cat,s,err,diag,flush=True)
            continue
        n+=1; used.add(s); data[s]=q
        sel.append({'ticker':s,'macro_category':cat,'rows':len(q),'first':str(q.date.min().date()),'last':str(q.date.max().date()),
                    'pre2017_rows':int((q.date<=PRE).sum()),'max_abs_daily_return':max_abs,**diag})
        print('SELECT',cat,n,'/20',s,'maxjump',f'{max_abs:.4%}','san',diag,flush=True)
    if n!=20:
        pd.DataFrame(sel).to_csv(OUT/'partial_selected.csv',index=False)
        pd.DataFrame(rej).to_csv(OUT/'rejected.csv',index=False)
        pd.DataFrame(audit).to_csv(OUT/'quality_audit.csv',index=False)
        raise RuntimeError(f'{cat} only {n}/20')

if len(sel)!=120 or len(used)!=120:
    raise RuntimeError(f'selected={len(sel)} unique={len(used)}')
if any(s in ORIGINAL_149 for s in used):
    raise RuntimeError('original149 overlap')

for r in sel:
    s=r['ticker']; q=data[s].copy(); q['date']=q.date.dt.strftime('%Y-%m-%d')
    q.to_csv(RAW/f"{re.sub(r'[^A-Za-z0-9._-]','_',s)}.csv",index=False,float_format='%.17g')
pd.DataFrame(sel)[['ticker','macro_category']].to_csv(RAW/'universe.csv',index=False)
pd.DataFrame(sel).to_csv(OUT/'coverage.csv',index=False)
pd.DataFrame(rej).to_csv(OUT/'rejected.csv',index=False)
pd.DataFrame(audit).to_csv(OUT/'quality_audit.csv',index=False)

for fld in ['Open','High','Low','Close','Volume']:
    pd.concat([data[s].set_index('date')[[fld]].rename(columns={fld:s}) for s in data],axis=1).sort_index().to_parquet(OUT/f'{fld.upper()}.parquet')

manifest={
    'status':'EU120_FROZEN_QUALITY_GATED',
    'provider':'Yahoo Finance via yfinance',
    'requested_start':START,
    'last_included':'2026-07-01',
    'evaluation_start':'2017-02-01',
    'selected_count':120,
    'per_cluster':20,
    'unique_tickers':len(used),
    'original149_overlap':0,
    'performance_used_for_selection':False,
    'data_quality_rules':{
        'mexico_listings_excluded':True,
        'drop_nonpositive_ohlc_rows':True,
        'rebuild_high_low_as_ohlc_envelope':True,
        'max_abs_adjusted_daily_return':MAX_ABS_DAILY_RETURN,
        'minimum_pre2017_rows_after_sanitation':MIN_PRE,
        'must_reach_last_date':str(LAST.date())
    },
    'replacement_policy':'Continue in fixed candidate order after any coverage/data-quality rejection; no post-2017 return statistic used.',
    'c06_filler_policy':'After real-asset instruments, remaining slots may use authorised EUR/Xetra instruments with canonical data coverage only; no performance criterion.',
    'selected':sel
}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k!='selected'},indent=2),flush=True)
