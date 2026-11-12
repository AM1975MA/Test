#!/usr/bin/env python3
"""OLC100 readiness gate: no new forecast, no source mutation, fail-closed.

Reconcile model availability, original event decisions, quote snapshot integrity,
and intraday OHLC consistency. Read-only, deterministic with pinned archives.
"""
from __future__ import annotations
import io, json, hashlib, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
CK=Path('/mnt/data/frozen_sources/OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
QUOTES=Path('/mnt/data/OLC100_20261112_SOURCE_FINAL.zip')
SOURCE_SHA='3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540'
STEM='olc19_combined_risk_20261102/'
NATIVE=STEM+'restore/olc18_execution_20261102/'
OLC16=NATIVE+'parent_archive/parent/olc16_contextual_rank_20261102/'

def h(b):return hashlib.sha256(b).hexdigest()

def main():
 assert h(CK.read_bytes())==SOURCE_SHA, 'Original model source hash mismatch'
 with zipfile.ZipFile(CK) as z, zipfile.ZipFile(QUOTES) as q:
  checksum=json.loads(q.read('SHA256SUMS.json'))
  checks={n:h(q.read(n))==digest for n,digest in checksum.items()}
  assert all(checks.values())
  data=json.loads(q.read('SUMMARY.json'))
  coverage=pd.read_csv(io.BytesIO(q.read('COVERAGE.csv')))
  assert len(coverage)==314 and not coverage.duplicated(['market','ticker']).any()
  model_files=[s for s in z.namelist() if s.startswith(OLC16+'models/')]
  refscore={};last_events={};parity={};counts={};source_period={}
  for market,expect in [('EU',165),('USA',149)]:
   a=pd.read_csv(io.BytesIO(z.read(OLC16+f'results/{market}_SCORES.csv.gz')),compression='gzip')
   decisions=pd.read_csv(io.BytesIO(z.read(NATIVE+f'inputs/{market}_TOP2_CONTEXT_REVALUE_DECISIONS.csv')))
   past=pd.read_csv(io.BytesIO(z.read(OLC16+f'inputs/{market}_FITTING_FRAME.csv.gz')),compression='gzip')
   with np.load(io.BytesIO(z.read(NATIVE+f'inputs/{market}_TOP2_CONTEXT_REVALUE.npz')),allow_pickle=False) as npz:
    dates=npz['dates'];event=npz['events'];tick=npz['tickers']
   assert (decisions.ticker1.notna()&decisions.ticker2.notna()).all()
   score_col='TOP2_CONTEXT_REVALUE_FUSION'
   assert score_col in a.columns
   if len(decisions)!=90:raise AssertionError((market,'expected 90 native decisions'))
   result=[]
   for row in decisions.itertuples():
    df=a[(a.signal_date==row.signal_date) & a[score_col].notna() & a.ticker.isin(tick)]
    top=df.sort_values([score_col,'ticker'],ascending=[False,True],kind='mergesort').head(2)
    result.append(tuple(top.ticker)==(row.ticker1,row.ticker2))
   assert all(result), (market,'selection mismatch',result.count(False))
   last=str(pd.Timestamp(dates[-1]).date())
   refscore[market]=str(pd.Timestamp(a.signal_date.max()).date())
   last_events[market]=str(decisions.signal_date.iloc[-1])
   parity[market]=f'{sum(result)}/{len(result)} exact frozen pair identities'
   counts[market]={'score_rows':len(a),'fitting_rows':len(past),'frozen_event_count':len(decisions),
                   'last_model_input_signal':refscore[market],'last_native_session':last,
                   'last_original_pair':[decisions.ticker1.iloc[-1],decisions.ticker2.iloc[-1]],
                   'unique_scored_tickers_last_signal':int(a[a.signal_date==a.signal_date.max()].ticker.nunique()),
                   'source_frozen_ticker_count':len(tick)}
   assert len(coverage[coverage.market.eq(market)])==expect
   assert len(model_files)>0
  invalids=[];allrows=0;months={};time_hist={}
  for row in coverage.itertuples(index=False):
   f=pd.read_csv(io.BytesIO(q.read('quotes/'+row.file)))
   allrows+=len(f)
   assert f.date.is_unique and f.date.is_monotonic_increasing
   a=f[['Open','High','Low','Close']].to_numpy(float)
   assert np.isfinite(a).all()
   below=np.maximum(a[:,2]-np.minimum(a[:,0],a[:,3]),0)
   above=np.maximum(np.maximum(a[:,0],a[:,3])-a[:,1],0)
   breach=np.maximum(below,above)/np.maximum(np.maximum(a[:,0],a[:,3]),1.e-9)
   idx=np.flatnonzero(f.raw_ohlc_invalid.astype(bool).to_numpy())
   assert np.array_equal(idx,np.flatnonzero(breach>1e-8)),'provider invalid flag not aligned to numeric condition'
   for j in idx:
    invalids.append({'market':row.market,'ticker':row.ticker,'date':f.date.iloc[j],
                     'breach_rel':float(breach[j]),'breach_bps':float(breach[j]*10000)})
   months[f'{row.market}:{row.ticker}']=sorted(set(pd.to_datetime(f.date).dt.to_period('M').astype(str)))
  bad=pd.DataFrame(invalids)
  print('post_anchor_badcount',len(bad),'max_bps',bad.breach_bps.max(),'median_bps',bad.breach_bps.median())
  assert allrows==29845 and len(bad)==79
  assert int(coverage.raw_ohlc_invalid_rows.sum())==83
  # The provider downloader reports invalids on full 2026-06-19.. run,
  # while the persisted CSV contains only dates AFTER the 2026-07-01 anchor.
  # Four anomalous provider bars fall inside the UNPERSISTED overlap window.
  overlap_count=int(coverage.raw_ohlc_invalid_rows.sum())-len(bad)
  assert overlap_count==4
  thresholds={str(bp):int((bad.breach_bps>bp).sum()) for bp in [0.1,1,5,10,25,50,100]}
  risk={'universe_pit':'NOT CERTIFIED','usa_original_observed_mask':'NOT CERTIFIED',
        'intraday_stop_fills':'NOT CERTIFIED','us_fx_dividends':'NOT CERTIFIED'}
  output={
   'status':'BLOCKED_NOT_A_CERTIFIED_OLC19_SIGNAL',
   'asof_snapshot':data['asof'],
   'new_model_scores_generated':False,
   'archives_verified':{'olc19_sha256':SOURCE_SHA,'quote_checksums':f'{sum(checks.values())}/{len(checks)}'},
   'original_model':{'2026_top2_context_model_present':OLC16+'models/2026_TOP2_CONTEXT.json' in z.namelist(),
    '2026_pair_context_model_present':OLC16+'models/2026_PAIR_CONTEXT.json' in z.namelist(),
    'serialized_first_stage_ET_XGB_in_checkpoint':len([name for name in z.namelist() if name.endswith(('.ubj','.joblib','.onnx','.bin','.pkl')) and 'EU_Close.pkl' not in name])>0,
    'last_signal':last_events,'historical_selection_parity':parity,'market_detail':counts,
    'missing_new_model_outputs':['EU_RETURN125','EU_ET_XGB_HYBRID42','USA_RETURN125','USA_ET_XGB_HYBRID42',
      'EU_NEW_CONTEXTUAL_FUSION','USA_NEW_CONTEXTUAL_FUSION','EU_USA_V6_FAST_LOCK3_CARRIED_ACCOUNT']},
   'quotes':{'download_count':len(coverage),'rows':allrows,'market_rows':{m:int(coverage[coverage.market==m].n_sessions.sum()) for m in ['EU','USA']},
     'valid_series':int((coverage.status=='OK').sum()),
     'anomalous_series':int((coverage.status!='OK').sum()),
     'invalid_bars_persisted_post_anchor':len(bad),
     'invalid_bars_reported_full_download':int(coverage.raw_ohlc_invalid_rows.sum()),
     'invalid_bars_in_unpersisted_overlap':overlap_count,
     'count_discrepancy_cause':'Coverage counts whole provider download from 2026-06-19, saved quotes exclude <=2026-07-01; exact overlap anomalous records were not archived',
     'invalid_bars_by_market':bad.groupby('market').size().to_dict(),
     'invalid_tickers_by_market':{m:sorted(bad[bad.market==m].ticker.unique().tolist()) for m in ['EU','USA']},
     'breach_bps_median':round(float(bad.breach_bps.median()),4),
     'breach_bps_max':round(float(bad.breach_bps.max()),4),
     'breaches_over_bps':thresholds,
     'invalid_last_dates':bad.groupby('market').date.max().to_dict(),
     'monthly_coverage':{m:sorted(set(x for k,v in months.items() if k.startswith(m+':') for x in v)) for m in ['EU','USA']}},
   'remaining_certification':risk,
   'forward_months_ever_generated':0,
   'portfolio_forward_cagr':None,
   'next_action':'Locate/reproduce frozen first-stage model and training provenance. Require 2026-01..06 score parity, then generate 2026-07..10 inputs on as-of snapshots, reconcile OHLC, and only then replay account. Do not emit a Top2 or performance before all gates pass.'
  }
  (ROOT/'OLC100_ASOF_READINESS.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
  bad.sort_values(['market','ticker','date']).to_csv(ROOT/'OLC100_SUSPECT_OHLC.csv',index=False,float_format='%.8f')
  print(json.dumps(output,indent=2,ensure_ascii=False)[:9000])
if __name__=='__main__':main()
