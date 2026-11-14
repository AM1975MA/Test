"""Capture frozen candidates; no performance-directed replacements or fitting."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, time, re
import pandas as pd
import numpy as np
import yfinance as yf

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'source_capture'
END='2026-11-14'  # exclusive: completed sessions through 2026-11-13
SUFFIXES=('.DE','.MI','.AS','.PA')

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def geometry(f):
    required=['Open','High','Low','Close']
    bad=(~np.isfinite(f[required]).all(axis=1))|(f[required]<=0).any(axis=1)
    tol=1e-6*f[required].abs().max(axis=1).clip(lower=1)
    return bad|(f.Low>f[['Open','Close']].min(axis=1)+tol)|(f.High<f[['Open','Close']].max(axis=1)-tol)

def capture(symbol, role, identity):
    obj=yf.Ticker(symbol)
    f=obj.history(start='2005-01-01',end=END,auto_adjust=False,actions=True,repair=False,keepna=True,rounding=False,timeout=30)
    if f.empty: raise ValueError('EMPTY_SERIES')
    meta=obj.get_history_metadata()
    currency=meta.get('currency')
    if role=='candidate' and currency!='EUR':raise ValueError('NON_EUR_OR_UNKNOWN_CURRENCY:'+str(currency))
    f.index=f.index.tz_localize(None).normalize()
    f.index.name='date';f=f.sort_index()
    if f.index.has_duplicates:raise ValueError('DUPLICATE_DATES')
    if (f.index>=pd.Timestamp(END)).any():raise ValueError('FUTURE_BAR')
    if 'Adj Close' not in f:raise ValueError('NO_ADJUSTED_CLOSE')
    f['geometry_bad']=geometry(f)
    p=OUT/'prices'/(symbol+'.csv.gz');p.parent.mkdir(parents=True,exist_ok=True)
    f.to_csv(p,float_format='%.17g',compression={'method':'gzip','mtime':0})
    (OUT/'metadata'/(symbol+'.json')).write_text(json.dumps(meta,indent=2,default=str))
    return dict(symbol=symbol,role=role,isin=identity,currency=currency,rows=len(f),first_date=str(f.index[0].date()),
      last_date=str(f.index[-1].date()),geometry_bad=int(f.geometry_bad.sum()),zero_volume=int(f.Volume.fillna(0).eq(0).sum()),
      sha256=sha(p),status='CAPTURED_NOT_EXECUTION_CERTIFIED')

def main():
    OUT.mkdir(exist_ok=True);(OUT/'metadata').mkdir(exist_ok=True);(OUT/'search').mkdir(exist_ok=True)
    candidates=pd.read_csv(ROOT/'CANDIDATES_FROZEN.csv')
    known=set((ROOT/'KNOWN_LISTING_TOKENS.txt').read_text().split())
    rows=[];sources=[]
    # Resolve every identity and apply novelty exclusions before downloading any price history.
    for rec in candidates.to_dict('records'):
        isin=rec['isin'];quotes=[];error=None
        for retry in range(3):
            try:
                quotes=yf.Search(isin,max_results=20,news_count=0).quotes
                if quotes:break
            except Exception as e:error=repr(e)
            time.sleep(1+retry)
        (OUT/'search'/(isin+'.json')).write_text(json.dumps(dict(query=isin,quotes=quotes,error=error),indent=2,default=str))
        choices=[q for q in quotes if q.get('quoteType')=='ETF' and str(q.get('symbol','')).endswith(SUFFIXES)]
        seen=sorted({q.get('symbol') for q in quotes}&known)
        if seen:row=dict(rec,status='EXCLUDED_PRIOR_ALIAS',prior_aliases=';'.join(seen),symbol='')
        elif not choices:row=dict(rec,status='NO_EUR_LISTING_RESOLVED',symbol='',prior_aliases='')
        else:
            choices.sort(key=lambda q:(next(i for i,s in enumerate(SUFFIXES) if q['symbol'].endswith(s)),q['symbol']))
            row=dict(rec,status='RESOLVED_ISIN_QUERY',symbol=choices[0]['symbol'],prior_aliases='',yahoo_name=choices[0].get('longname',choices[0].get('shortname','')))
        rows.append(row);print('IDENTITY',isin,row['status'],row.get('symbol',''),flush=True)
    pd.DataFrame(rows).to_csv(OUT/'ROSTER_RESOLUTION.csv',index=False)
    for row in rows:
        if row['status']!='RESOLVED_ISIN_QUERY':continue
        try:
            record=capture(row['symbol'],'candidate',row['isin']);row['status']=record['status'];sources.append(record)
        except Exception as e:
            row['status']='PRICE_CAPTURE_FAILED';row['error']=repr(e)
        print('CAPTURE',row['isin'],row['symbol'],row['status'],flush=True)
    for sym in ['EXSA.DE','SPY']:
        try:sources.append(capture(sym,'context_only','KNOWN_BENCHMARK_NOT_HOLDOUT'))
        except Exception as e:sources.append(dict(symbol=sym,role='context_only',status='FAILED',error=repr(e)))
    pd.DataFrame(rows).to_csv(OUT/'ROSTER_RESOLUTION.csv',index=False)
    pd.DataFrame(sources).to_csv(OUT/'COVERAGE_QA.csv',index=False)
    manifest=dict(status='CAPTURE_COMPLETED_WITH_EXPLICIT_GATES',captured_at_utc=datetime.now(timezone.utc).isoformat(),
      end_exclusive=END,provider='Yahoo Finance via yfinance',yfinance_version=yf.__version__,
      candidate_file_sha256=sha(ROOT/'CANDIDATES_FROZEN.csv'),known_identifiers_sha256=sha(ROOT/'KNOWN_LISTING_TOKENS.txt'),
      raw_auto_adjust=False,actions=True,repair=False,prices_are_trade_republic_fills=False,
      historical_point_in_time_certified=False,account_availability_certified=False,
      sources=sources,files={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()})
    (OUT/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,default=str))
    print('SUMMARY',pd.DataFrame(rows).status.value_counts().to_dict(),flush=True)
    assert len([s for s in sources if s.get('role')=='candidate' and s.get('status','').startswith('CAPTURED')])>=12, 'Insufficient mapped candidates; no model result may be inferred.'
if __name__=='__main__':main()
