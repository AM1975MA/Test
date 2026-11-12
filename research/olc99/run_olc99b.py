#!/usr/bin/env python3
"""OLC99B: fit economic value across whole eligible universe; only re-rank native Top10."""
from __future__ import annotations
import sys,json
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_olc99 as b
R=b.ROOT;O=b.OUT

def panel_for(m,q,dec,scores,ids):
 by={str(d):g for d,g in scores.groupby('signal_date',sort=False)}
 mapper={str(s):i for i,s in enumerate(q['tickers'])}
 records=[];models=[];pairs=[];chosen=[]
 for j,k in enumerate(ids):
  date=str(dec.loc[j,'signal_date'])
  original=by[date].dropna(subset=['ORIGINAL_SMOOTH','ORIGINAL_FUSION','TOP2_CONTEXT_REVALUE_FUSION']).copy()
  n=len(original);assert n>=100
  top=original.sort_values(['ORIGINAL_FUSION','ticker'],ascending=[False,True],kind='mergesort').head(10)
  assert set(dec.loc[j,['ticker1','ticker2']]).issubset(set(top.ticker))
  entries=[]
  for item in original.itertuples(index=False):
   idx=mapper[item.ticker]
   row={'market':m,'event_j':j,'signal_date':date,'ticker':item.ticker}
   for f in b.BASE_COLS:row[f]=float(getattr(item,f))
   row['context_minus_fusion']=row['TOP2_CONTEXT_REVALUE_FUSION']-row['ORIGINAL_FUSION']
   row.update(b.lookback_features(q,int(k),idx))
   end=int(ids[j+1]) if j+1<len(ids) else None
   row['future_logr']=b.safe_log_ratio(q['O'][end,idx],q['O'][k,idx]) if end is not None else np.nan
   entries.append(row)
  g=pd.DataFrame(entries)
  g['y_train']=(g.future_logr-g.future_logr.median()).clip(-.25,.25)
  g['sample_weight']=1./len(g)
  past=pd.concat(records,ignore_index=True) if records else pd.DataFrame()
  eligible=past[(past.event_j<=j-2)&past.y_train.notna()] if len(past) else pd.DataFrame()
  fit_months=eligible.event_j.nunique() if len(eligible) else 0
  shortlist=g[g.ticker.isin(top.ticker)].copy()
  shortlist['economic_pred']=np.nan
  if fit_months>=24:
   yhat=b.fill_train_predict(eligible,shortlist,b.FEATURES,target='y_train',alpha=100)
   shortlist['economic_pred']=yhat
  shortlist['context_rank']=shortlist.TOP2_CONTEXT_REVALUE_FUSION.rank(method='average',pct=True)
  shortlist['learned_rank']=shortlist.economic_pred.rank(method='average',pct=True)
  shortlist['mixed_score']=(.8*shortlist.context_rank+.2*shortlist.learned_rank) if fit_months>=24 else shortlist.context_rank
  selection=shortlist.sort_values(['mixed_score','ticker'],ascending=[False,True],kind='mergesort').head(2).ticker.tolist()
  if fit_months<24:assert selection==dec.loc[j,['ticker1','ticker2']].tolist()
  pairs.append(selection)
  chosen.append({'market':m,'event_j':j,'signal_date':date,'ticker1':selection[0],'ticker2':selection[1],
                 'n_train_months':int(fit_months),'top10_n':len(shortlist)})
  shortlist['stage']='TOP10';shortlist['train_months']=fit_months;models.append(shortlist)
  records.append(g)
  if j%30==0:print('RETRAIN',m,j,'n prior',int(fit_months),'candidate count',n,flush=True)
 return pairs,pd.concat(models),pd.DataFrame(chosen),sum(len(x) for x in records)

def main():
 qa={'experiment':'OLC99B','protocol_sha256':b.digest(R/'OLC99B_PROTOCOL_ADDENDUM.md'),'markets':{}}
 selections=[];candidate=[];sc=[];daily=[];annual=[]
 for m in ['EU','USA']:
  q,dec,scores,ids=b.source(m)
  pairs,rows,selection,nrows=panel_for(m,q,dec,scores,ids)
  mapper={str(t):i for i,t in enumerate(q['tickers'])}
  qq=b.rerank_q(q,ids,mapper,pairs)
  candidate.append(rows);selections.append(selection)
  changes=int(sum(pairs[j]!=dec.loc[j,['ticker1','ticker2']].tolist() for j in range(90)))
  qa['markets'][m]={'n_universe_training_rows':nrows,'candidate_rows':len(rows),'n_changes':changes}
  for timing in ('IMMEDIATE','DELAY3'):
   for fee in (.001,.003):
    res=b.simulate_native(qq,fee,timing)
    b.add_result(m,'E3_GLOBAL_ECONOMIC_20',timing,fee,qq,res,sc,daily,annual)
  x=[c for c in sc if c['market']==m and c['timing']=='DELAY3' and c['fee']==.001 and c['period'] in ('FULL','ACTIVE2021_2024')]
  print('E3',m,[(z['period'],round(100*z['cagr'],3),round(100*z['maxdd'],2)) for z in x],flush=True)
 pd.concat(candidate).to_csv(O/'OLC99B_TOP10_PREDICTIONS.csv',index=False)
 pd.concat(selections).to_csv(O/'OLC99B_SELECTIONS.csv',index=False)
 pd.DataFrame(sc).to_csv(O/'OLC99B_NATIVE_SCORECARD.csv',index=False)
 pd.concat(daily).to_csv(O/'OLC99B_NATIVE_DAILY_LOGRET.csv.gz',compression={'method':'gzip','mtime':0},index=False)
 pd.DataFrame(annual).to_csv(O/'OLC99B_ANNUAL.csv',index=False)
 (O/'OLC99B_QA.json').write_text(json.dumps(qa,indent=2))
 print('B COMPLETED',qa,flush=True)

if __name__=='__main__':main()