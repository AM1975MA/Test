#!/usr/bin/env python3
from __future__ import annotations

import json, re, time, unicodedata
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
MAX_ZERO_RETURN_FRAC=0.08
PER_CLUSTER=20
OUT=Path('europe120/v2_output')
RAW=OUT/'raw_ticker_csv'
RAW.mkdir(parents=True,exist_ok=True)

# Preserve strict disjointness from the original 149-ticker research universe.
ORIGINAL_149=set('''DIA IJR SCHD QQQ QUAL RSP DGRO IJH IWF HDV MDY SCHB IWM MTUM SCHX SPY IVV VTI VO VB VUG VTV IWD IWN SPLV
PPA SMH SOXX IGV IHI KBE HACK IYT KRE IBB ICLN ITA FDN TAN XBI XLK XLF XLE XLV XLI XLY XLP XLU XLB XRT
ACWI EWL EWP EWA EWN IEFA EFA EWH EWQ EWC EWD EWJ EWG EWI EWU VEA VEU VGK EWK EWO EIRL EIS EPOL ENZL EPP
EWS EWY FXI ASHR INDA VWO EWT IEMG KWEB EEM MCHI TUR AAXJ EWZ EZA EIDO EWM THD EPHE SCHE DEM DGS EPI ARGT
AGG BIL EMB IEF IEI LQD BNDX HYG MUB BND JNK SCHP EDV SHY TLT TIP SHV VGSH VGIT VGLT VCIT VCSH MBB BKLN ANGL
COMT GLD SLV GSG IYR PPLT CPER DBB VNQ DBC GDX PALL BNO DBA GDXJ IAU USO UNG DBO USL RWO RWX WOOD CORN URA'''.split())

# User-requested redesign: no mandatory bond bucket; all six clusters are equity / equity-like.
# Search order is fixed before downloading any post-2017 performance statistic.
CLUSTERS={
 'C01_EUROPE_BROAD':[
   'MSCI Europe UCITS ETF EUR','STOXX Europe 600 UCITS ETF EUR','EURO STOXX 50 UCITS ETF EUR',
   'MSCI EMU UCITS ETF EUR','Eurozone UCITS ETF EUR','FTSE Developed Europe UCITS ETF EUR',
   'Europe ESG UCITS ETF EUR','Europe value UCITS ETF EUR','Europe quality UCITS ETF EUR','Europe dividend UCITS ETF EUR'],
 'C02_EUROPE_COUNTRY':[
   'FTSE MIB UCITS ETF','DAX UCITS ETF','CAC 40 UCITS ETF','IBEX 35 UCITS ETF','AEX UCITS ETF',
   'SMI UCITS ETF','Switzerland UCITS ETF EUR','Italy UCITS ETF EUR','Germany UCITS ETF EUR','France UCITS ETF EUR',
   'Spain UCITS ETF EUR','Netherlands UCITS ETF EUR','Belgium UCITS ETF EUR','Austria UCITS ETF EUR',
   'Portugal UCITS ETF EUR','Greece UCITS ETF EUR','Poland UCITS ETF EUR','Nordic UCITS ETF EUR'],
 'C03_US_EQUITY_EUR':[
   'S&P 500 UCITS ETF EUR','NASDAQ 100 UCITS ETF EUR','Dow Jones Industrial UCITS ETF EUR','Russell 2000 UCITS ETF EUR',
   'MSCI USA UCITS ETF EUR','USA value UCITS ETF EUR','USA quality UCITS ETF EUR','USA momentum UCITS ETF EUR',
   'USA small cap UCITS ETF EUR','USA minimum volatility UCITS ETF EUR','S&P 500 equal weight UCITS ETF EUR'],
 'C04_WORLD_DEVELOPED':[
   'MSCI World UCITS ETF EUR','FTSE All World UCITS ETF EUR','MSCI World ex Europe UCITS ETF EUR',
   'MSCI Japan UCITS ETF EUR','Japan TOPIX UCITS ETF EUR','MSCI Pacific UCITS ETF EUR','Australia UCITS ETF EUR',
   'Canada UCITS ETF EUR','World quality UCITS ETF EUR','World momentum UCITS ETF EUR','World value UCITS ETF EUR',
   'World minimum volatility UCITS ETF EUR','World small cap UCITS ETF EUR'],
 'C05_EMERGING_ASIA':[
   'MSCI Emerging Markets UCITS ETF EUR','FTSE Emerging Markets UCITS ETF EUR','MSCI China UCITS ETF EUR',
   'MSCI India UCITS ETF EUR','MSCI Taiwan UCITS ETF EUR','MSCI Korea UCITS ETF EUR','MSCI Brazil UCITS ETF EUR',
   'MSCI Mexico UCITS ETF EUR','MSCI South Africa UCITS ETF EUR','MSCI Eastern Europe UCITS ETF EUR',
   'Emerging Markets small cap UCITS ETF EUR','Emerging Markets dividend UCITS ETF EUR','Asia ex Japan UCITS ETF EUR'],
 'C06_GLOBAL_SECTOR':[
   'World technology UCITS ETF EUR','World financials UCITS ETF EUR','World healthcare UCITS ETF EUR',
   'World industrials UCITS ETF EUR','World consumer discretionary UCITS ETF EUR','World consumer staples UCITS ETF EUR',
   'World energy UCITS ETF EUR','World materials UCITS ETF EUR','World utilities UCITS ETF EUR',
   'World communication services UCITS ETF EUR','semiconductor UCITS ETF EUR','automation robotics UCITS ETF EUR',
   'cyber security UCITS ETF EUR','clean energy UCITS ETF EUR','global infrastructure UCITS ETF EUR',
   'global real estate UCITS ETF EUR']
}

# Known liquid EUR listings are placed first, but acceptance still depends only on metadata/coverage/quality gates.
DIRECT={
 'C01_EUROPE_BROAD':['EXSA.DE','IMEU.AS','CSSX5E.MI','SXRT.DE','CSEMU.MI','SXR7.DE','SC0E.DE','MEUD.PA','LYP6.DE','MSE.PA'],
 'C02_EUROPE_COUNTRY':['CSMIB.MI','EXS1.DE','C40.PA','BBVAI.MC','IAEX.AS','CSSMI.SW','SXRY.DE','EXH1.DE','EXH2.DE','EXH3.DE'],
 'C03_US_EQUITY_EUR':['SXR8.DE','SPY5.DE','IUSA.AS','CSPX.AS','EXXT.DE','CNDX.AS','XSPX.DE','XD9U.DE','XRS2.DE','ZPRV.DE','ZPRX.DE'],
 'C04_WORLD_DEVELOPED':['EUNL.DE','IUSQ.DE','XDWD.DE','SPYY.DE','XMWO.DE','EUNM.DE','IS3N.DE','SXR4.DE','XMEU.DE','ZPRG.DE'],
 'C05_EMERGING_ASIA':['EUNM.DE','IS3N.DE','XMME.DE','IQQE.DE','CEMG.MI','XCS6.DE','XCS5.DE','XCS4.DE','XCS3.DE','XCS2.DE'],
 'C06_GLOBAL_SECTOR':['QDVE.DE','XDWT.DE','WTEC.DE','XDWF.DE','XDWH.DE','XDWI.DE','XDWS.DE','XDW0.DE','XDWU.DE','XDWC.DE','SEMI.PA','RBOT.MI','ISPY.L','INRG.MI','INFR.MI','IWDP.AS']
}

ALLOWED_SUFFIXES=('.DE','.MI','.PA','.AS','.MC','.SW','.AT','.BR','.LS','.HE','.ST','.CO','.OL')


def norm_name(name:str)->str:
    x=unicodedata.normalize('NFKD',name or '').encode('ascii','ignore').decode().lower()
    # Remove listing/share-class noise while retaining index/fund identity.
    x=re.sub(r'\b(ucits|etf|acc|accumulating|dist|distributing|eur|usd|gbp|hedged|unhedged|class|share|shares)\b',' ',x)
    x=re.sub(r'\b(i|ii|iii|iv)\b',' ',x)
    x=re.sub(r'[^a-z0-9]+',' ',x)
    return ' '.join(x.split())


def meta(sym):
    try:
        t=yf.Ticker(sym)
        fi=t.fast_info
        currency=str(getattr(fi,'currency',None) or fi.get('currency') or '').upper()
    except Exception:
        currency=''
    try:
        info=yf.Ticker(sym).get_info()
        name=str(info.get('longName') or info.get('shortName') or sym)
        quote_type=str(info.get('quoteType') or '').upper()
        exchange=str(info.get('exchange') or '')
    except Exception:
        name=sym; quote_type=''; exchange=''
    return currency,name,quote_type,exchange


def download(sym):
    try:
        d=yf.download(sym,start=START,end=END,auto_adjust=False,actions=False,progress=False,threads=False)
    except Exception as e:
        return None,f'download:{type(e).__name__}:{e}',{}
    if d is None or d.empty:return None,'empty',{}
    if isinstance(d.columns,pd.MultiIndex):d.columns=d.columns.get_level_values(0)
    d=d.reset_index(); req=['Date','Open','High','Low','Close','Adj Close','Volume']
    if any(c not in d.columns for c in req):return None,'missing_columns',{}
    rawc=pd.to_numeric(d['Close'],errors='coerce').replace(0,pd.NA)
    adj=pd.to_numeric(d['Adj Close'],errors='coerce'); f=adj/rawc
    q=pd.DataFrame({'date':pd.to_datetime(d['Date']),
                    'Open':pd.to_numeric(d['Open'],errors='coerce')*f,
                    'High':pd.to_numeric(d['High'],errors='coerce')*f,
                    'Low':pd.to_numeric(d['Low'],errors='coerce')*f,
                    'Close':adj,'Volume':pd.to_numeric(d['Volume'],errors='coerce')}).dropna().sort_values('date').drop_duplicates('date',keep='last')
    q=q[q.date<=LAST].copy()
    q=q[(q[['Open','High','Low','Close']]>0).all(axis=1)].copy()
    if q.empty:return None,'no_positive_ohlc',{}
    q['High']=q[['Open','High','Low','Close']].max(axis=1); q['Low']=q[['Open','High','Low','Close']].min(axis=1)
    npre=int((q.date<=PRE).sum())
    if npre<MIN_PRE:return None,f'pre2017:{npre}',{}
    if q.date.max()<LAST:return None,'ends_early',{}
    r=q.Close.pct_change(fill_method=None).replace([np.inf,-np.inf],np.nan)
    maxjump=float(r.abs().max())
    if not np.isfinite(maxjump) or maxjump>MAX_ABS_DAILY_RETURN:return None,f'quality_jump:{maxjump:.6f}',{'max_abs_daily_return':maxjump}
    evalr=q.loc[q.date>=pd.Timestamp('2017-02-01'),'Close'].pct_change(fill_method=None)
    zero_frac=float((evalr.abs()<1e-14).mean())
    if zero_frac>MAX_ZERO_RETURN_FRAC:return None,f'stale:{zero_frac:.6f}',{'max_abs_daily_return':maxjump,'zero_return_frac':zero_frac}
    return q,None,{'max_abs_daily_return':maxjump,'zero_return_frac':zero_frac,'pre2017_rows':npre}


def search_pool(query):
    try: rows=getattr(yf.Search(query,max_results=50,news_count=0),'quotes',None) or []
    except Exception:return []
    out=[]
    for r in rows:
        s=str(r.get('symbol') or '').upper().strip(); qt=str(r.get('quoteType') or '').upper()
        if not s or qt!='ETF':continue
        if s in ORIGINAL_149 or s.endswith('.MX'):continue
        if not s.endswith(ALLOWED_SUFFIXES):continue
        out.append(s)
    return out

selected=[]; rejected=[]; data={}; used_tickers=set(); used_names=set()
for cat,queries in CLUSTERS.items():
    pool=[]
    for s in DIRECT.get(cat,[]):
        if s not in pool:pool.append(s)
    for q in queries:
        for s in search_pool(q):
            if s not in pool:pool.append(s)
        time.sleep(.12)
    n=0
    for s in pool:
        if n>=PER_CLUSTER:break
        if s in used_tickers or s in ORIGINAL_149:continue
        currency,name,qt,exchange=meta(s)
        fp=norm_name(name)
        if currency!='EUR':
            rejected.append({'ticker':s,'cluster':cat,'reason':f'currency:{currency}','name':name});continue
        if qt and qt!='ETF':
            rejected.append({'ticker':s,'cluster':cat,'reason':f'quoteType:{qt}','name':name});continue
        if fp and fp in used_names:
            rejected.append({'ticker':s,'cluster':cat,'reason':'duplicate_fund_name','name':name});continue
        q,err,diag=download(s)
        if q is None:
            rejected.append({'ticker':s,'cluster':cat,'reason':err,'name':name,**diag});continue
        used_tickers.add(s); used_names.add(fp); data[s]=q; n+=1
        selected.append({'ticker':s,'cluster':cat,'name':name,'name_fingerprint':fp,'currency':currency,'exchange':exchange,
                         'rows':len(q),'first':str(q.date.min().date()),'last':str(q.date.max().date()),**diag})
        print('SELECT',cat,n,'/20',s,name,flush=True)
    if n!=PER_CLUSTER:
        pd.DataFrame(selected).to_csv(OUT/'partial_selected.csv',index=False)
        pd.DataFrame(rejected).to_csv(OUT/'rejected.csv',index=False)
        raise RuntimeError(f'{cat} only {n}/20; pool={len(pool)}')

if len(selected)!=120 or len(used_tickers)!=120:raise RuntimeError('EU120-v2 cardinality failure')

for rec in selected:
    s=rec['ticker']; q=data[s].copy(); q['date']=q.date.dt.strftime('%Y-%m-%d')
    q.to_csv(RAW/f"{re.sub(r'[^A-Za-z0-9._-]','_',s)}.csv",index=False,float_format='%.17g')
pd.DataFrame(selected)[['ticker','cluster','name','currency','exchange']].to_csv(RAW/'universe.csv',index=False)
pd.DataFrame(selected).to_csv(OUT/'coverage.csv',index=False)
pd.DataFrame(rejected).to_csv(OUT/'rejected.csv',index=False)
for fld in ['Open','High','Low','Close','Volume']:
    pd.concat([data[s].set_index('date')[[fld]].rename(columns={fld:s}) for s in data],axis=1).sort_index().to_parquet(OUT/f'{fld.upper()}.parquet')

manifest={
 'status':'EU120_V2_FROZEN', 'provider':'Yahoo Finance via yfinance', 'requested_start':START,
 'last_included':'2026-07-01','evaluation_start':'2017-02-01','selected_count':120,'per_cluster':20,
 'unique_tickers':len(used_tickers),'unique_fund_name_fingerprints':len(used_names),'original149_overlap':0,
 'performance_used_for_selection':False,'currency_rule':'EUR only',
 'clusters':{k:PER_CLUSTER for k in CLUSTERS},
 'quality_rules':{'min_pre2017_rows':MIN_PRE,'max_abs_adjusted_daily_return':MAX_ABS_DAILY_RETURN,
                  'max_zero_return_fraction_2017_2026':MAX_ZERO_RETURN_FRAC,'nonpositive_ohlc_rows_dropped':True},
 'selection_rule':'fixed direct candidates followed by frozen Yahoo ETF search-query order; EUR metadata, fund-name dedupe, historical coverage and data-quality gates only; no 2017-2026 return statistic used to rank/select',
 'selected':selected}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k!='selected'},indent=2),flush=True)
