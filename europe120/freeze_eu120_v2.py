#!/usr/bin/env python3
from __future__ import annotations

import ast, json, math, re, time
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

START = '2004-01-01'
END = '2026-07-02'
LAST = pd.Timestamp('2026-07-01')
PRE = pd.Timestamp('2017-01-31')
EVAL = pd.Timestamp('2017-02-01')
MIN_PRE = 252
PER_CLUSTER = 20
MAX_ABS_DAILY_RETURN = 0.25
MAX_ZERO_RETURN_FRAC = 0.05
MAX_CONSEC_ZERO = 5
OUT = Path('europe120/v2_frozen_output')
RAW = OUT / 'raw_ticker_csv'
RAW.mkdir(parents=True, exist_ok=True)

# V2 is deliberately equity-centric.  No bond quota exists.
CLUSTERS = {
    'C01_EUROPE_BROAD': {
        'label': 'Europe broad / Eurozone',
        'queries': [
            'MSCI Europe UCITS ETF', 'STOXX Europe 600 UCITS ETF', 'FTSE Developed Europe UCITS ETF',
            'MSCI EMU UCITS ETF', 'EURO STOXX 50 UCITS ETF', 'Eurozone UCITS ETF',
            'Europe large cap UCITS ETF', 'Europe broad market UCITS ETF',
            'Europe dividend UCITS ETF', 'Europe value UCITS ETF', 'Europe quality UCITS ETF',
            'Europe minimum volatility UCITS ETF'],
        'must_any': ['europe','euro stoxx','eurozone','emu','stoxx 600'],
        'exclude': ['bond','short','inverse','leveraged','2x','3x','sector','bank','technology','healthcare','real estate','property']
    },
    'C02_EUROPE_COUNTRY': {
        'label': 'European country indices',
        'queries': [
            'FTSE MIB UCITS ETF', 'DAX UCITS ETF', 'CAC 40 UCITS ETF', 'IBEX 35 UCITS ETF',
            'AEX UCITS ETF', 'SMI UCITS ETF', 'Switzerland UCITS ETF', 'Germany UCITS ETF',
            'France UCITS ETF', 'Italy UCITS ETF', 'Spain UCITS ETF', 'Netherlands UCITS ETF',
            'Belgium UCITS ETF', 'Austria UCITS ETF', 'Portugal UCITS ETF', 'Greece UCITS ETF',
            'Sweden UCITS ETF', 'Denmark UCITS ETF', 'Norway UCITS ETF', 'Finland UCITS ETF',
            'Poland UCITS ETF', 'United Kingdom UCITS ETF'],
        'must_any': ['mib','dax','cac','ibex','aex','smi','switzerland','germany','france','italy','spain','netherlands','belg','austria','portugal','greece','sweden','denmark','norway','finland','poland','united kingdom','ftse 100'],
        'exclude': ['bond','short','inverse','leveraged','2x','3x']
    },
    'C03_US_EQUITY_EUR': {
        'label': 'US equity via EUR-listed UCITS ETFs',
        'queries': [
            'S&P 500 UCITS ETF EUR', 'Nasdaq 100 UCITS ETF EUR', 'Dow Jones UCITS ETF EUR',
            'MSCI USA UCITS ETF EUR', 'Russell 2000 UCITS ETF EUR', 'US small cap UCITS ETF EUR',
            'USA value UCITS ETF EUR', 'USA quality UCITS ETF EUR', 'USA momentum UCITS ETF EUR',
            'USA minimum volatility UCITS ETF EUR', 'S&P 500 equal weight UCITS ETF EUR',
            'S&P 500 dividend UCITS ETF EUR'],
        'must_any': ['s&p 500','nasdaq','dow jones','msci usa','russell','usa','u.s.','us '],
        'exclude': ['bond','short','inverse','leveraged','2x','3x']
    },
    'C04_WORLD_DEVELOPED': {
        'label': 'Developed world / Pacific / Japan',
        'queries': [
            'MSCI World UCITS ETF EUR', 'FTSE Developed World UCITS ETF EUR', 'MSCI World ex Europe UCITS ETF EUR',
            'MSCI World value UCITS ETF EUR', 'MSCI World quality UCITS ETF EUR', 'MSCI World momentum UCITS ETF EUR',
            'MSCI World minimum volatility UCITS ETF EUR', 'MSCI Japan UCITS ETF EUR', 'TOPIX UCITS ETF EUR',
            'MSCI Pacific UCITS ETF EUR', 'MSCI Pacific ex Japan UCITS ETF EUR', 'Australia UCITS ETF EUR',
            'Canada UCITS ETF EUR'],
        'must_any': ['world','developed','japan','topix','pacific','australia','canada'],
        'exclude': ['bond','emerging','short','inverse','leveraged','2x','3x']
    },
    'C05_EMERGING_ASIA': {
        'label': 'Emerging markets / Asia',
        'queries': [
            'MSCI Emerging Markets UCITS ETF EUR', 'FTSE Emerging Markets UCITS ETF EUR',
            'MSCI Emerging Markets IMI UCITS ETF EUR', 'MSCI China UCITS ETF EUR', 'China A shares UCITS ETF EUR',
            'MSCI India UCITS ETF EUR', 'MSCI Korea UCITS ETF EUR', 'MSCI Taiwan UCITS ETF EUR',
            'MSCI Brazil UCITS ETF EUR', 'MSCI Latin America UCITS ETF EUR', 'MSCI ASEAN UCITS ETF EUR',
            'MSCI Asia ex Japan UCITS ETF EUR', 'Emerging markets small cap UCITS ETF EUR'],
        'must_any': ['emerging','china','india','korea','taiwan','brazil','latin america','asean','asia ex japan'],
        'exclude': ['bond','short','inverse','leveraged','2x','3x']
    },
    'C06_SECTOR_THEMATIC': {
        'label': 'Equity sectors / real assets / themes',
        'queries': [
            'STOXX Europe 600 technology UCITS ETF', 'STOXX Europe 600 banks UCITS ETF',
            'STOXX Europe 600 insurance UCITS ETF', 'STOXX Europe 600 healthcare UCITS ETF',
            'STOXX Europe 600 industrial goods UCITS ETF', 'STOXX Europe 600 automobiles UCITS ETF',
            'STOXX Europe 600 oil gas UCITS ETF', 'STOXX Europe 600 basic resources UCITS ETF',
            'STOXX Europe 600 utilities UCITS ETF', 'STOXX Europe 600 construction UCITS ETF',
            'STOXX Europe 600 food beverage UCITS ETF', 'STOXX Europe 600 telecom UCITS ETF',
            'European real estate UCITS ETF', 'global infrastructure UCITS ETF EUR',
            'semiconductor UCITS ETF EUR', 'clean energy UCITS ETF EUR', 'defence UCITS ETF EUR'],
        'must_any': ['technology','bank','insurance','health','industrial','automobile','oil','gas','energy','basic resources','material','utilit','construction','food','beverage','telecom','real estate','property','infrastructure','semiconductor','clean energy','defence','defense'],
        'exclude': ['bond','short','inverse','leveraged','2x','3x']
    }
}

# High-confidence EUR-listed seeds are only priority hints. They still must pass
# every metadata, identity, history and data-quality gate below.
SEEDS = {
    'C01_EUROPE_BROAD': ['EXSA.DE','IMEU.AS','SXR7.DE','CSSX5E.MI','CSEMU.MI','XMEU.DE'],
    'C02_EUROPE_COUNTRY': ['CSMIB.MI','EXS1.DE','C40.PA','IAEX.AS','BBVAI.MC'],
    'C03_US_EQUITY_EUR': ['SXR8.DE','SXRV.DE','SPY5.DE','ZPRV.DE'],
    'C04_WORLD_DEVELOPED': ['EUNL.DE','XDWD.DE','IUSQ.DE','SXR4.DE'],
    'C05_EMERGING_ASIA': ['IS3N.DE','EUNM.DE','XMME.DE'],
    'C06_SECTOR_THEMATIC': ['EXV1.DE','EXV2.DE','EXV3.DE','EXV4.DE','EXV6.DE','EXV7.DE','EXV8.DE','EXV9.DE','EXH1.DE','EXH2.DE','EXH3.DE','EXH4.DE','EXH5.DE','EXH6.DE','EXH8.DE','EXH9.DE']
}


def original_149() -> set[str]:
    src = Path('regeneration/etf_trader_raw.py').read_text(encoding='utf-8')
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'CATS':
                    cats = ast.literal_eval(node.value)
                    return {str(t).upper() for xs in cats.values() for t in xs}
    raise RuntimeError('cannot recover canonical 149')


def norm_name(x: str) -> str:
    x = (x or '').lower()
    x = re.sub(r'\b(ucits|etf|fund|acc|dist|distributing|accumulating|eur|usd|gbp|hedged)\b', ' ', x)
    x = re.sub(r'[^a-z0-9]+', ' ', x)
    return ' '.join(x.split())


def text_ok(spec: dict, name: str) -> bool:
    x = (name or '').lower()
    if any(k in x for k in spec['exclude']):
        return False
    return any(k in x for k in spec['must_any'])


def search_rows(query: str) -> list[dict]:
    try:
        rows = getattr(yf.Search(query, max_results=50, news_count=0), 'quotes', None) or []
    except Exception as e:
        print('SEARCH_FAIL', query, type(e).__name__, str(e), flush=True)
        return []
    out=[]
    for r in rows:
        sym=str(r.get('symbol') or '').upper().strip()
        typ=str(r.get('quoteType') or '').upper()
        name=str(r.get('longname') or r.get('shortname') or '').strip()
        if sym and typ == 'ETF':
            out.append({'ticker':sym,'name':name,'exchange':r.get('exchange'),'search_currency':r.get('currency'),'query':query})
    return out


def metadata(row: dict) -> dict:
    sym=row['ticker']; t=yf.Ticker(sym)
    currency=row.get('search_currency')
    exchange=row.get('exchange')
    name=row.get('name') or ''
    try:
        fi=t.fast_info
        currency=currency or getattr(fi,'currency',None)
        exchange=exchange or getattr(fi,'exchange',None)
    except Exception:
        pass
    isin=None
    try:
        z=getattr(t,'isin',None)
        if isinstance(z,str) and re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}[0-9]',z): isin=z
    except Exception:
        pass
    if not name:
        try:
            info=t.get_info()
            name=str(info.get('longName') or info.get('shortName') or '')
            currency=currency or info.get('currency')
            exchange=exchange or info.get('exchange')
        except Exception:
            pass
    return {'currency':str(currency or '').upper(),'exchange':str(exchange or ''),'isin':isin,'name':name}


def runlen_zero(mask: pd.Series) -> int:
    best=cur=0
    for v in mask.fillna(False).to_numpy(bool):
        cur=cur+1 if v else 0
        best=max(best,cur)
    return int(best)


def download(sym: str):
    try:
        d=yf.download(sym,start=START,end=END,auto_adjust=False,actions=False,progress=False,threads=False)
    except Exception as e:
        return None,f'download:{type(e).__name__}:{e}',{}
    if d is None or d.empty: return None,'empty',{}
    if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
    d=d.reset_index()
    req=['Date','Open','High','Low','Close','Adj Close','Volume']
    if any(c not in d.columns for c in req): return None,'missing_columns',{}
    rawc=pd.to_numeric(d['Close'],errors='coerce').replace(0,pd.NA)
    adj=pd.to_numeric(d['Adj Close'],errors='coerce'); f=adj/rawc
    q=pd.DataFrame({'date':pd.to_datetime(d['Date']),
                    'Open':pd.to_numeric(d['Open'],errors='coerce')*f,
                    'High':pd.to_numeric(d['High'],errors='coerce')*f,
                    'Low':pd.to_numeric(d['Low'],errors='coerce')*f,
                    'Close':adj,
                    'Volume':pd.to_numeric(d['Volume'],errors='coerce')}).dropna().sort_values('date').drop_duplicates('date',keep='last')
    q=q[q.date<=LAST].copy()
    good=(q[['Open','High','Low','Close']]>0).all(axis=1); q=q.loc[good].copy()
    if q.empty:return None,'no_positive_ohlc',{}
    q['High']=q[['Open','High','Low','Close']].max(axis=1); q['Low']=q[['Open','High','Low','Close']].min(axis=1)
    npre=int((q.date<=PRE).sum())
    if npre<MIN_PRE:return None,f'pre2017:{npre}',{'pre2017_rows':npre}
    if q.date.max()<LAST:return None,'ends_early',{'last':str(q.date.max().date())}
    r=q.Close.pct_change(fill_method=None).replace([np.inf,-np.inf],np.nan)
    mx=float(r.abs().max()) if r.notna().any() else math.inf
    if not np.isfinite(mx) or mx>MAX_ABS_DAILY_RETURN:return None,f'quality_jump:{mx:.6f}',{'max_abs_daily_return':mx}
    rz=r.iloc[1:].abs().le(1e-12); zf=float(rz.mean()) if len(rz) else 1.0; zr=runlen_zero(rz)
    if zf>MAX_ZERO_RETURN_FRAC:return None,f'stale_zero_frac:{zf:.6f}',{'zero_return_frac':zf,'max_zero_run':zr}
    if zr>MAX_CONSEC_ZERO:return None,f'stale_zero_run:{zr}',{'zero_return_frac':zf,'max_zero_run':zr}
    # Liquidity quality is measured only on the pre-2017 window; it does not use future performance.
    pre=q[q.date<=PRE]
    nz=pre.loc[pre.Volume>0,'Volume']
    medvol=float(nz.median()) if len(nz) else 0.0
    if medvol<500:return None,f'pre2017_median_volume:{medvol:.1f}',{'pre2017_median_volume':medvol,'zero_return_frac':zf,'max_zero_run':zr}
    return q,None,{'pre2017_rows':npre,'max_abs_daily_return':mx,'zero_return_frac':zf,'max_zero_run':zr,'pre2017_median_volume':medvol}


def metrics(eq: pd.Series) -> dict:
    eq=eq.dropna()
    if len(eq)<2:return {}
    ret=eq.pct_change().dropna(); years=(eq.index[-1]-eq.index[0]).days/365.25
    cagr=float((eq.iloc[-1]/eq.iloc[0])**(1/years)-1)
    dd=eq/eq.cummax()-1
    sh=float(np.sqrt(252)*ret.mean()/ret.std(ddof=1)) if ret.std(ddof=1)>0 else np.nan
    return {'cagr':cagr,'maxdd':float(dd.min()),'sharpe':sh,'terminal_equity':float(eq.iloc[-1]/eq.iloc[0])}


def main():
    original=original_149(); selected=[]; rejected=[]; quality=[]; data={}; used_tickers=set(); used_funds=set()
    for cat,spec in CLUSTERS.items():
        pool=[]; seen=set(); qrank={q:i for i,q in enumerate(spec['queries'])}
        for i,s in enumerate(SEEDS.get(cat,[])):
            if s not in seen:
                pool.append({'ticker':s,'name':'','exchange':'','search_currency':'','query':f'00_SEED_{i:02d}'})
                seen.add(s)
        for q in spec['queries']:
            for r in search_rows(q):
                if r['ticker'] in seen: continue
                seen.add(r['ticker'])
                if text_ok(spec,r['name']): pool.append(r)
            time.sleep(0.10)
        pool.sort(key=lambda r:(0 if str(r['query']).startswith('00_SEED') else 1,qrank.get(r['query'],999),r['ticker']))
        chosen=0
        for row in pool:
            if chosen>=PER_CLUSTER: break
            sym=row['ticker']
            if sym in original:
                rejected.append({**row,'macro_category':cat,'reason':'overlap_original149'}); continue
            if sym in used_tickers: continue
            q,err,qd=download(sym)
            quality.append({'ticker':sym,'macro_category':cat,'accepted_price_gate':q is not None,'price_reason':err or 'ok',**qd})
            if q is None:
                rejected.append({**row,'macro_category':cat,'reason':err}); continue
            meta=metadata(row); name=meta['name'] or row.get('name') or ''
            if meta['currency']!='EUR':
                rejected.append({**row,'macro_category':cat,'reason':f"currency:{meta['currency'] or 'unknown'}",**meta}); continue
            fundkey=meta['isin'] or norm_name(name)
            if not fundkey:
                rejected.append({**row,'macro_category':cat,'reason':'identity_missing',**meta}); continue
            if fundkey in used_funds:
                rejected.append({**row,'macro_category':cat,'reason':'duplicate_fund_or_isin','fund_key':fundkey,**meta}); continue
            rec={'ticker':sym,'macro_category':cat,'cluster_label':spec['label'],'name':name,'currency':meta['currency'],
                 'exchange':meta['exchange'],'isin':meta['isin'],'fund_key':fundkey,'identity_basis':'isin' if meta['isin'] else 'normalized_name',
                 'rows':int(len(q)),'first':str(q.date.min().date()),'last':str(q.date.max().date()),**qd}
            selected.append(rec); data[sym]=q; used_tickers.add(sym); used_funds.add(fundkey); chosen+=1
            print('SELECT',cat,chosen,'/20',sym,name,meta['currency'],meta['isin'],flush=True)
        if chosen!=PER_CLUSTER:
            OUT.mkdir(parents=True,exist_ok=True)
            pd.DataFrame(selected).to_csv(OUT/'partial_selected.csv',index=False)
            pd.DataFrame(rejected).to_csv(OUT/'rejected.csv',index=False)
            pd.DataFrame(quality).to_csv(OUT/'quality_audit.csv',index=False)
            raise RuntimeError(f'{cat} only {chosen}/20 from pool {len(pool)}')

    if len(selected)!=120 or len(used_funds)!=120: raise RuntimeError(f'bad cardinality selected={len(selected)} funds={len(used_funds)}')
    for rec in selected:
        s=rec['ticker']; z=data[s].copy(); z['date']=z.date.dt.strftime('%Y-%m-%d')
        z.to_csv(RAW/f"{re.sub(r'[^A-Za-z0-9._-]','_',s)}.csv",index=False,float_format='%.17g')
    pd.DataFrame(selected)[['ticker','macro_category','cluster_label','name','currency','exchange','isin','fund_key']].to_csv(RAW/'universe.csv',index=False)
    pd.DataFrame(selected).to_csv(OUT/'coverage.csv',index=False); pd.DataFrame(rejected).to_csv(OUT/'rejected.csv',index=False); pd.DataFrame(quality).to_csv(OUT/'quality_audit.csv',index=False)
    for fld in ['Open','High','Low','Close','Volume']:
        pd.concat([data[s].set_index('date')[[fld]].rename(columns={fld:s}) for s in data],axis=1).sort_index().to_parquet(OUT/f'{fld.upper()}.parquet')

    manifest={'status':'EU120_V2_FROZEN','provider':'Yahoo Finance via yfinance','requested_start':START,'last_included':str(LAST.date()),
              'evaluation_start':str(EVAL.date()),'selected_count':120,'per_cluster':20,'unique_tickers':len(used_tickers),'unique_funds':len(used_funds),
              'original149_overlap':len(used_tickers & original),'performance_used_for_selection':False,
              'selection_design':'equity-centric; EUR listings only; one ISIN/fund identity; no mandatory bond cluster',
              'quality_rules':{'minimum_pre2017_rows':MIN_PRE,'max_abs_daily_return':MAX_ABS_DAILY_RETURN,
                               'max_zero_return_fraction':MAX_ZERO_RETURN_FRAC,'max_consecutive_zero_returns':MAX_CONSEC_ZERO,
                               'min_pre2017_median_nonzero_volume':500},'selected':selected}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

    # Performance diagnostics are computed only AFTER the universe is frozen and never feed selection.
    close=pd.concat([data[s].set_index('date')[['Close']].rename(columns={'Close':s}) for s in data],axis=1).sort_index()
    close=close.loc[(close.index>=EVAL)&(close.index<=LAST)].ffill()
    norm=close/close.iloc[0]; ew=norm.mean(axis=1)
    diag={'equal_weight':metrics(ew)}
    rows=[]
    for s in close.columns:
        m=metrics(close[s]/close[s].dropna().iloc[0]); rows.append({'ticker':s,**m})
    perf=pd.DataFrame(rows).sort_values('cagr',ascending=False); perf.to_csv(OUT/'diagnostic_performance.csv',index=False)
    if len(perf): diag['best_single_ex_post']=perf.iloc[0].to_dict()
    (OUT/'diagnostic_summary.json').write_text(json.dumps(diag,indent=2,default=float)+'\n')
    print(json.dumps({'manifest':{k:v for k,v in manifest.items() if k!='selected'},'diagnostic':diag},indent=2,default=float),flush=True)

if __name__=='__main__': main()
