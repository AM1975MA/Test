#!/usr/bin/env python3
"""OLC100 source-data-only snapshot, with strict audit; NEVER generates ETF orders.

Scope: original OLC19 EU165 + USA149 and original 2026-07-01 anchor.
No future return, labels, trained parameters, changed candidate sets or V6 values.
A successful run is NOT a valid prospective signal; signature and trading-engine
parity are separately required by OLC100 forward packet gate.
"""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,json,os,sys,time,traceback
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
DATA=HERE/'data'
EXPECTED={'EU':165,'USA':149}
START='2026-06-19'
ANCHOR='2026-07-01'
MAX_DRIFT=0.004

def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):
   h.update(chunk)
 return h.hexdigest()

def validate_local_source():
 manifest=json.loads((DATA/'SOURCE_MANIFEST.json').read_text())
 for name,expected_hash in manifest['files'].items():
  actual=digest(DATA/name)
  if actual!=expected_hash:raise RuntimeError(f'FROZEN SOURCE HASH FAIL: {name}: {actual}')
 u=pd.read_csv(DATA/'OLC19_UNIVERSE.csv',dtype=str)
 a=pd.read_csv(DATA/'OLC19_ANCHOR_O_L_C.csv',dtype={'market':str,'ticker':str,'date':str})
 assert not u.duplicated(['market','ticker']).any()
 assert u.groupby('market').size().to_dict()==EXPECTED
 assert not a.duplicated(['market','ticker','date']).any()
 assert set(map(tuple,u[['market','ticker']].itertuples(index=False,name=None)))==set(map(tuple,a[['market','ticker']].drop_duplicates().itertuples(index=False,name=None)))
 assert set(a.date)==set(pd.date_range(START,ANCHOR,freq='B').strftime('%Y-%m-%d')) or len(set(a.date))>=8
 return u,a

def clean_download(df):
 """yfinance raw OHLC plus adjusted ratios; preserve original raw OHLC."""
 if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
 missing={'Open','High','Low','Close','Adj Close','Volume'}-set(df.columns)
 if missing:raise ValueError('provider fields missing '+repr(sorted(missing)))
 if df.empty:raise ValueError('provider empty')
 df=df.sort_index()
 ix=pd.DatetimeIndex(df.index)
 if ix.tz is not None:ix=ix.tz_localize(None)
 if ix.has_duplicates:raise ValueError('duplicate provider date')
 out=df[list(['Open','High','Low','Close','Adj Close','Volume'])].copy()
 out.index=ix.normalize()
 out=out.apply(pd.to_numeric,errors='coerce').dropna()
 if out.empty or (out[['Open','High','Low','Close','Adj Close']]<=0).any().any() or (out.Volume<0).any():
  raise ValueError('invalid OHLCV or adjusted close')
 if (out.Low>out[['Open','Close']].min(axis=1)*1.000001).any():raise ValueError('raw OHLC Low>Open/Close')
 if (out.High<out[['Open','Close']].max(axis=1)*.999999).any():raise ValueError('raw OHLC High<Open/Close')
 ratio=out['Adj Close']/out.Close
 if (ratio<=0).any() or not np.isfinite(ratio).all():raise ValueError('adjustment ratio invalid')
 for col in ['Open','High','Low','Close']:
  out['adj_'+col.lower()]=(out[col]*ratio if col!='Close' else out['Adj Close'])
 out.index.name='date'
 return out

def align_original(q,anchor):
 """Compare provider adjusted levels after one fixed scale at 2026-07-01."""
 if pd.Timestamp(ANCHOR) not in q.index:raise ValueError('provider 2026-07-01 anchor absent')
 a=anchor.set_index(pd.to_datetime(anchor.date))
 if pd.Timestamp(ANCHOR) not in a.index:raise ValueError('OLC19 anchor absent')
 oldclose=float(a.loc[pd.Timestamp(ANCHOR),'close']);newclose=float(q.loc[pd.Timestamp(ANCHOR),'adj_close'])
 scale=oldclose/newclose
 shared=q[['adj_close']].join(a[['close']].rename(columns={'close':'frozen_close'}),how='inner')
 if len(shared)<5:raise ValueError(f'overlap too short: {len(shared)}')
 drift=(shared.adj_close*scale/shared.frozen_close-1).abs()
 return dict(scale_to_olc19=float(scale),overlap_sessions=int(len(shared)),maximum_overlap_relative_error=float(drift.max()),
             original_anchor_close=oldclose,provider_anchor_adjusted_close=newclose,
             overlap_warning=bool(float(drift.max())>MAX_DRIFT))

def download_one(market,ticker,anchor,asof,out):
 import yfinance as yf
 trouble=None
 for attempt in range(3):
  try:
   # Explicit end-exclusive cutoff; future timestamps rejected below.
   df=yf.download(ticker,start=START,end=(asof+timedelta(days=1)).isoformat(),auto_adjust=False,
                  actions=False,threads=False,progress=False,timeout=30)
   q=clean_download(df)
   if q.index[-1].date()>asof:raise ValueError('provider data after asof')
   a=align_original(q,anchor)
   new=q.loc[q.index>pd.Timestamp(ANCHOR)].copy()
   if new.empty:raise ValueError('no new rows beyond locked OLC19 last date')
   outname=f'{market}_{ticker.replace("/","_")}.csv'
   tmp=new.reset_index()
   tmp['date']=tmp.date.dt.strftime('%Y-%m-%d')
   tmp['market']=market;tmp['ticker']=ticker
   tmp['bridge_scale_only']=a['scale_to_olc19']
   tmp.to_csv(out/outname,index=False,float_format='%.17g')
   late_days=(asof-new.index[-1].date()).days
   status='OVERLAP_DRIFT' if a['overlap_warning'] else ('STALE' if late_days>4 else 'OK')
   return dict(market=market,ticker=ticker,status=status,first_date=str(new.index[0].date()),
         last_date=str(new.index[-1].date()),late_calendar_days=late_days,n_sessions=len(new),file=outname,
         sha256=digest(out/outname),**a)
  except Exception as e:
   trouble=str(e)
   time.sleep(.6*(attempt+1))
 return dict(market=market,ticker=ticker,status='PROVIDER_FAIL',error=trouble,n_sessions=0)

def capture(asof,out,max_workers,only=None):
 u,a=validate_local_source();out.mkdir(parents=True,exist_ok=True);(out/'quotes').mkdir(exist_ok=True)
 now=datetime.now(timezone.utc)
 if asof>now.date():raise ValueError('future asof not permitted')
 if asof<pd.Timestamp(ANCHOR).date():raise ValueError('asof before 2026-07-01')
 candidates=[tuple(x) for x in u[['market','ticker']].itertuples(index=False,name=None)]
 if only:candidates=[(m,t) for m,t in candidates if (m,t) in only]
 rowmap={(m,t):q for (m,t),q in a.groupby(['market','ticker'])}
 seen=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
  pending={pool.submit(download_one,m,t,rowmap[(m,t)],asof,out/'quotes'):(m,t) for m,t in candidates}
  for fu in concurrent.futures.as_completed(pending):
   res=fu.result();seen.append(res)
   print('OLC100_SOURCE',res['market'],res['ticker'],res['status'],res.get('last_date'),flush=True)
 seen=sorted(seen,key=lambda q:(q['market'],q['ticker']))
 pd.DataFrame(seen).to_csv(out/'COVERAGE.csv',index=False)
 counts=pd.DataFrame(seen).groupby(['market','status']).size().unstack(fill_value=0).to_dict('index')
 all_ok=(len(seen)==sum(EXPECTED.values()) and all(r['status']=='OK' for r in seen))
 status='SOURCE_QA_PASS' if all_ok else 'SOURCE_QA_INCOMPLETE'
 manifest=dict(schema='OLC100_SOURCE_CAPTURE_V1',status=status,asof=str(asof),captured_at_utc=now.isoformat(),
             completed_at_utc=datetime.now(timezone.utc).isoformat(),markets=counts,requested_count=len(candidates),
             original_universe=EXPECTED,source_archive_sha256=json.loads((DATA/'SOURCE_MANIFEST.json').read_text())['source_sha256'],
             cutoff_policy='no data after asof; yfinance revision as of capture; provider raw preserved; bridge comparison only',
             status_note='This archive is NOT an OLC19 signal, order, V6 state or validated prospective backtest',
             trading_authorized=False,score_generation_attempted=False,comparison_eligible=False,
             branch_ref=os.getenv('GITHUB_REF','local'),workflow_run=os.getenv('GITHUB_RUN_ID','local'),
             workflow_sha=os.getenv('GITHUB_SHA','local'),universe_sha256=digest(DATA/'OLC19_UNIVERSE.csv'),
             anchor_sha256=digest(DATA/'OLC19_ANCHOR_O_L_C.csv'))
 with (out/'SUMMARY.json').open('w') as f:json.dump(manifest,f,indent=2,sort_keys=True)
 hashes={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file() and p.name!='SHA256SUMS.json'}
 (out/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2,sort_keys=True)+'\n')
 print('OLC100_CAPTURE_RESULT',json.dumps({k:manifest[k] for k in ['status','asof','requested_count','markets']},sort_keys=True),flush=True)
 return status

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--asof',required=True)
 ap.add_argument('--out',required=True)
 ap.add_argument('--max-workers',type=int,default=3)
 ap.add_argument('--preview-only',action='store_true',help='validate frozen source metadata; no network')
 args=ap.parse_args()
 if args.preview_only:
  u,a=validate_local_source();print('OLC100_FROZEN_UNIVERSE_PASS',u.groupby('market').size().to_dict(),len(a));return
 status=capture(date.fromisoformat(args.asof),Path(args.out),args.max_workers)
 if status!='SOURCE_QA_PASS':raise SystemExit(2)
if __name__=='__main__':main()
