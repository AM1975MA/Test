#!/usr/bin/env python3
"""OLC100 bridge source audit. Never generates new ETF selections or NAV.

Read the V3 GitHub-archived USA149 price extension from 2026-10-24 and check
compatibility with the frozen OLC19 July-1 opening anchor, without rewriting
original historic prices. This archive is source-only, not a complete EU/USA
forward OLC19 strategy input.
"""
from __future__ import annotations
import argparse,hashlib,io,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--zip',default='/mnt/data/V3_149_FORWARD_20261024.zip')
 ap.add_argument('--root',default='/mnt/data/olc100_workspace/OLC98_Model_Review_20261112')
 ap.add_argument('--out',default='/mnt/data/olc100_package/results')
 args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 ip=Path(args.root)/'native/olc19_combined_risk_20261102/restore/olc18_execution_20261102/inputs/USA_TOP2_CONTEXT_REVALUE.npz'
 with np.load(ip) as npz:q={k:v.copy() for k,v in npz.items()}
 d0=pd.DatetimeIndex(q['dates']);k=int(d0.get_indexer([pd.Timestamp('2026-07-01')])[0]);assert k==len(d0)-1
 idx={str(t):i for i,t in enumerate(q['tickers'])}; assert len(idx)==149
 rows=[];counts=[];first_dates=[];last_dates=[];unique_calendars=[]
 with zipfile.ZipFile(args.zip) as z:
  assert z.testzip() is None
  assert 'PROVENANCE.json' in z.namelist()
  p=json.loads(z.read('PROVENANCE.json'))
  assert p['anchor']=='2026-07-01' and p['last_requested']=='2026-10-23'
  assert p['original_historic_prefix_unchanged'] is True
  assert p.get('original_tickers')==149
  assert len(p['rows'])==149
  tickers=pd.read_csv(io.BytesIO(z.read('universe.csv'))).ticker.astype(str).tolist()
  assert set(tickers)==set(idx) and len(tickers)==149
  dates_ref=None
  for t in tickers:
   item=pd.read_csv(io.BytesIO(z.read(t+'.csv')),float_precision='round_trip',parse_dates=['date'])
   assert item.date.is_unique and item.date.is_monotonic_increasing
   assert set(['date','Open','High','Low','Close','Volume']).issubset(item.columns)
   old=item[item.date.between(pd.Timestamp('2026-06-19'),pd.Timestamp('2026-07-01'))]
   assert len(old)>=7
   juneidx=d0.get_indexer(old.date)
   assert (juneidx>=0).all()
   n=idx[t];anchor=item[item.date.eq('2026-07-01')]
   assert len(anchor)==1
   anchor=anchor.iloc[0]
   scale=float(q['O'][k,n]/anchor.Open)
   old_ratio=old.Open.to_numpy(float)*scale/q['O'][juneidx,n]-1
   close_ratio=old.Close.to_numpy(float)*scale/q['C'][juneidx,n]-1
   diff_before_scale=float(anchor.Open/q['O'][k,n]-1)
   overlap=float(max(np.max(np.abs(old_ratio)),np.max(np.abs(close_ratio))))
   tail=item[item.date.gt('2026-07-01')]
   assert len(tail)==80 and str(tail.date.iloc[0].date())=='2026-07-02' and str(tail.date.iloc[-1].date())=='2026-10-23'
   x=tail[['Open','High','Low','Close','Volume']].to_numpy(float)
   assert np.isfinite(x).all() and np.min(x[:,:4])>0 and np.min(x[:,4])>=0
   assert (x[:,1]>=np.maximum.reduce([x[:,0],x[:,2],x[:,3]])-1e-8).all()
   assert (x[:,2]<=np.minimum.reduce([x[:,0],x[:,1],x[:,3]])+1e-8).all()
   cal=tuple(tail.date.dt.strftime('%Y-%m-%d'))
   if dates_ref is None:dates_ref=cal
   assert cal==dates_ref
   assert overlap<.0001,(t,'non-constant overlap adjustment',overlap)
   last_dates.append(str(tail.date.iloc[-1].date()));first_dates.append(str(tail.date.iloc[0].date()));counts.append(len(tail))
   rows.append(dict(ticker=t,olc19_july_open=float(q['O'][k,n]),v3_july_open=float(anchor.Open),
     original_anchor_relative_gap=diff_before_scale,scale_to_olc19=scale,
     max_8day_relative_overlap_drift=overlap,new_rows=len(tail),latest_new_close=float(tail.Close.iloc[-1])*scale))
 diag=pd.DataFrame(rows).sort_values('ticker');diag.to_csv(out/'OLC100_USA_PRICE_BRIDGE_DIAGNOSTICS.csv',index=False)
 # This is a single-pair price-only exercise, NOT OLC19/V6/FAST_LOCK3 returns.
 s=pd.read_csv(Path(args.root).parent/'OLC56_ROBUST_20261106'/'results'/'USA_DECISIONS.csv')
 e=s.tail(1).iloc[0];assert e.entry_date=='2026-07-01'
 ret=[]
 with zipfile.ZipFile(args.zip) as z:
  for t in [e.ticker1,e.ticker2]:
   f=pd.read_csv(io.BytesIO(z.read(t+'.csv')))
   x=f.loc[f.date.eq('2026-07-01'),'Open'];y=f.loc[f.date.eq('2026-08-03'),'Open']
   assert len(x)==len(y)==1
   ret.append(float(y.iloc[0]/x.iloc[0]-1))
 w=float(e['weight__B1_MINVAR63_CAP25']); half=.5*(ret[0]+ret[1]);mw=w*ret[0]+(1-w)*ret[1]
 details={'signal_date':'2026-06-30','entry_date':'2026-07-01','exit_date':'2026-08-03',
 'selected_top2':[e.ticker1,e.ticker2],'price_only_returns_top2':ret,'minvar63_weight_top1':w,
 'hypothetical_static_pair_return_half':half,'hypothetical_static_pair_return_minvar':mw,
 'scope':'ONE USA FROZEN JUNE SIGNAL, gross opening price returns, no V6/no timing/no protective stops/no costs. NOT candidate CAGR or entire July-Dec bridge'}
 (out/'OLC100_USA_ONE_SIGNAL_PRICE_ONLY.json').write_text(json.dumps(details,indent=2)+'\n')
 qa={'status':'USA_PRICE_BRIDGE_SOURCE_PASS__STRATEGY_FORWARD_BLOCKED',
 'source':'V3 raw adjusted OHLCV Github Action 40082539622, artifact 12555507287, retrieved 2026-11-12',
 'artifact_sha256':sha(args.zip),'universe_count':len(idx),'raw_tickers_matched':len(rows),
 'new_trading_sessions_per_ticker':int(min(counts)), 'new_rows_total':int(sum(counts)),
 'latest_session':max(last_dates),'max_overlap_drift_after_constant_scale':float(diag.max_8day_relative_overlap_drift.max()),
 'n_anchor_open_gaps_over_1bp_before_scale':int((diag.original_anchor_relative_gap.abs()>.0001).sum()),
 'anchor_gap_tickers_over_1bp':diag.loc[diag.original_anchor_relative_gap.abs()>.0001,'ticker'].tolist(),
 'eu_prices_available':False,'eu_updated_signals_available':False,'usa_updated_olc19_signals_available':False,
 'new_forecast_model_parity_verified':False,'new_v6_exposure_verified':False,
 'olc100_forward_native_replays_completed':0,'claims_genuine_prospective_oos':False,
 'blocking_gates':['updated EU 167-column observed/quote panel not supplied',
 'updated USA+EU OLC19 original and contextual Top2 signals not supplied',
 'V6 exposure & risk inputs not certified after July 1','timestamped pre-outcome live signal receipts unavailable',
 'USA adjusted-price variation must be explicitly anchored; do not revise historical observations']}
 (out/'OLC100_BRIDGE_SOURCE_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
 print(json.dumps({k:v for k,v in qa.items() if k not in ['blocking_gates']},indent=2))
 print('STATIC_ONE_SIGNAL',json.dumps(details))
if __name__=='__main__':main()
