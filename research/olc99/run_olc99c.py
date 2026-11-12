#!/usr/bin/env python3
"""OLC99C — native same-state economic Top10 outcome instead of Open-to-Open label."""
from pathlib import Path
import sys,json, numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_olc99 as b
ROOT=b.ROOT;OUT=b.OUT

def main():
 qa={'experiment':'OLC99C','protocol_sha256':b.digest(ROOT/'OLC99C_PROTOCOL_ADDENDUM.md'),
    'metrics_recomputed':0,'markets':{}}
 scorer=[];choices=[];native=[];daily=[];annual=[]
 eng,_=b.state_matched_engine(b._s,b._fill)
 fees={'fee':.001,'exposure_timing':'PREVIOUS','stop_timing':'NOW','stop_friction':.001,
       'ordinary_alarm':False,'fast_stop':True,'lock_days':3}
 for market in ('EU','USA'):
  q,dec,scores,ids=b.source(market)
  panel=pd.read_csv(OUT/'OLC99_TOP10_ECONOMIC_PANEL.csv.gz')
  panel=panel[panel.market==market].copy().sort_values(['event_j','ticker'])
  baseline=b.simulate_native(q,timing='DELAY3')
  snaps={}
  snapshots=eng(q,q['events'],policy='DELAY',fraction=3,snapshot_indices=set(map(int,ids[:-1])),
                snapshot_store=snaps,**fees)
  keys=('nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace')
  assert all(np.array_equal(baseline[z],snapshots[z]) for z in keys)
  assert len(snaps)==89
  mapper={str(t):j for j,t in enumerate(q['tickers'])}
  frame=[];pairs=[]
  for j,k0 in enumerate(ids):
   k=int(k0);e=int(ids[j+1]) if j+1<len(ids) else None
   g=panel[panel.event_j==j].copy().reset_index(drop=True)
   assert len(g)==10
   if e is not None:
    results=[];prevals=[]
    for row in g.itertuples():
     qq={key:val for key,val in q.items()}
     qq['d1']=q['d1'].copy();qq['d2']=q['d2'].copy()
     qq['d1'][0,k:e]=int(mapper[row.ticker]);qq['d2'][0,k:e]=int(mapper[row.ticker])
     r=eng(qq,q['events'],policy='DELAY',fraction=3,start_index=k,end_index=e,
              initial_state=snaps[k],**fees)
     s=float(r['ledger'][k,0]);v=float(r['nav'][e-1]);assert s>0 and v>0
     prevals.append(s);results.append(float(np.log(v/s)))
    assert max(prevals)-min(prevals)<1e-8
    g['native_logr']=results
    g['native_y']=(g.native_logr-g.native_logr.median()).clip(-.25,.25)
   else:
    g['native_logr']=np.nan;g['native_y']=np.nan
   g['sample_weight']=.1
   past=pd.concat(frame,ignore_index=True) if frame else pd.DataFrame()
   tr=past[(past.event_j<=j-2)&past.native_y.notna()] if len(past) else pd.DataFrame()
   n=tr.event_j.nunique() if len(tr) else 0
   g['native_pred']=np.nan
   if n>=24:
    g['native_pred']=b.fill_train_predict(tr,g,b.FEATURES,target='native_y',alpha=100)
   g['ctx_rank']=g.TOP2_CONTEXT_REVALUE_FUSION.rank(pct=True,method='average')
   g['pred_rank']=g.native_pred.rank(pct=True,method='average')
   g['mixed_score']=.8*g.ctx_rank+.2*g.pred_rank if n>=24 else g.ctx_rank
   chosen=g.sort_values(['mixed_score','ticker'],ascending=[False,True],kind='mergesort').head(2).ticker.tolist()
   if n<24:assert chosen==dec.loc[j,['ticker1','ticker2']].tolist()
   pairs.append(chosen)
   choices.append({'market':market,'event_j':j,'signal_date':str(dec.loc[j,'signal_date']),
        'ticker1':chosen[0],'ticker2':chosen[1],'train_n_months':int(n)})
   frame.append(g)
   if j%30==0:print('C TRAIN',market,j,n,flush=True)
  scorer.append(pd.concat(frame))
  qq=b.rerank_q(q,ids,mapper,pairs)
  qa['markets'][market]={'n_matched_single_asset_forks':89*10,
       'baseline_instrumented_native_parity':'7/7 bitwise',
       'n_changes':int(sum(pairs[j]!=dec.loc[j,['ticker1','ticker2']].tolist() for j in range(90)))}
  for fee in (.001,.003):
   r=b.simulate_native(qq,fee,'DELAY3')
   b.add_result(market,'E4_NATIVE_ECONOMIC_20','DELAY3',fee,qq,r,native,daily,annual)
  for zz in native:
   if zz['market']==market and zz['fee']==.001 and zz['period'] in ('FULL','ACTIVE2021_2024'):
    print('C NATIVE',market,zz['period'],zz['cagr'],zz['maxdd'],flush=True)
 pd.concat(scorer).to_csv(OUT/'OLC99C_TOP10_NATIVE_LABELS.csv.gz',compression={'method':'gzip','mtime':0},index=False)
 pd.DataFrame(choices).to_csv(OUT/'OLC99C_SELECTIONS.csv',index=False)
 pd.DataFrame(native).to_csv(OUT/'OLC99C_SCORECARD.csv',index=False)
 pd.concat(daily).to_csv(OUT/'OLC99C_DAILY_LOGRET.csv.gz',compression={'method':'gzip','mtime':0},index=False)
 pd.DataFrame(annual).to_csv(OUT/'OLC99C_ANNUAL.csv',index=False)
 (OUT/'OLC99C_QA.json').write_text(json.dumps(qa,indent=2))
 print('C COMPLETED',qa,flush=True)
if __name__=='__main__':main()