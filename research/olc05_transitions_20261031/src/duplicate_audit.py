"""Synthetic alias invariance: no fitted model, economic metadata or future selection."""
from pathlib import Path
import numpy as np,pandas as pd,json
from methods import blend_forecasts,collapse_columns
B=Path(__file__).resolve().parents[1];S=B/'source';OUT=B/'results';OUT.mkdir(exist_ok=True)
def chosen(s,ids):
    valid=np.flatnonzero(np.isfinite(s))
    if len(valid)<2:return ()
    p=valid[np.argpartition(s[valid],-2)[-2:]];p=p[np.argsort(-s[p])]
    return tuple(ids[j] for j in p)
def rank(a):return pd.DataFrame(a).rank(axis=1,pct=True).to_numpy()
def main():
 summary=[];details=[];checks=[]
 for market in ['EU','USA']:
  score=pd.read_csv(S/f'lifecycle_execution_20261031/inputs/{market}_SCORE.csv',index_col=0,parse_dates=True,float_precision='round_trip')
  f=pd.read_csv(S/f'paired_frontier_20261031/results/calendar/{market}_FORECASTS.csv.gz',parse_dates=['signal_date'],float_precision='round_trip')
  ids=score.columns.tolist();raw=[f.pivot(index='signal_date',columns='ticker',values=c).reindex(index=score.index,columns=ids).to_numpy() for c in ['RETURN_RAW','ET_RAW','XGB_RAW']]
  base=blend_forecasts(*[rank(a) for a in raw]);err=np.nanmax(abs(base-score.to_numpy()));assert err<1e-12,err
  q=np.load(S/f'lifecycle_execution_20261031/inputs/{market}_STATE_HALF.npz');allids=q['tickers'].tolist();sref=score.to_numpy();orig=[chosen(s,ids) for s in sref]
  for kind,copies in [('EVERY10',1),('EVERY10',4),('ALL',1),('ALL',4)]:
   anchors=list(range(0,len(ids),10)) if kind=='EVERY10' else list(range(len(ids)))
   ix=list(range(len(ids)))+[j for j in anchors for _ in range(copies)];aliases=[ids[j] for j in ix]
   expanded=[a[:,ix] for a in raw];rerank=blend_forecasts(*[rank(a) for a in expanded]);frozen=sref[:,ix]
   collapsed=[collapse_columns(a,aliases)[0] for a in expanded];restored=blend_forecasts(*[rank(a) for a in collapsed]);resterr=np.nanmax(abs(restored-base));assert resterr==0.
   # Alias price copying changes counting weights, not market prices.
   gap=q['gap'];extra=[allids.index(ids[j]) for j in anchors for _ in range(copies)]
   gnew=np.concatenate([gap,gap[:,extra]],axis=1)
   b1=(gnew<-.01).mean(1);b0=(gnew<0).mean(1)
   pg=.5*gap[np.arange(len(gap)),np.maximum(q['d1'][0],0)]+.5*gap[np.arange(len(gap)),np.maximum(q['d2'][0],0)]
   oldtr=((pg<=-.032)&(q['ud1']>=.70))|((pg<=-.044)&(q['uneg']>=.75))
   newtr=((pg<=-.032)&(b1>=.70))|((pg<=-.044)&(b0>=.75))
   breadth_diff=int((oldtr!=newtr).sum())
   for mode,a in [('FROZEN_SCORES',frozen),('RECOMPUTED_PERCENTILES',rerank)]:
    dup=0;change=0;top_change=0
    for i,sd in enumerate(score.index):
     pair=chosen(a[i],aliases);b=orig[i]
     collapsed_pair=set(pair);different=collapsed_pair!=set(b)
     dup+=int(len(collapsed_pair)<len(pair));change+=int(different);top_change+=int(pair[0]!=b[0])
     details.append({'market':market,'case':f'{kind}_COPY{copies}','score_mode':mode,'signal_date':str(sd.date()),'base_pair':'|'.join(b),'alias_pair':'|'.join(pair),'distinct_exposures':len(collapsed_pair),'changed_exposures':different,'top1_changed':pair[0]!=b[0]})
    summary.append({'market':market,'case':f'{kind}_COPY{copies}','score_mode':mode,'base_count':len(ids),'alias_count':len(aliases),'months':len(orig),'changed_pair_months':change,'single_exposure_months':dup,'changed_top1_months':top_change,'breadth_trigger_days_changed':breadth_diff,'maximum_breadth_difference':float(max(np.max(abs(b1-q['ud1'])),np.max(abs(b0-q['uneg'])))),'identity_collapse_error':resterr})
   checks.append({'market':market,'case':f'{kind}_COPY{copies}','score_parity_error':float(err),'identity_collapse_error':float(resterr),'model_refits':0})
 pd.DataFrame(summary).to_csv(OUT/'DUPLICATE_SUMMARY.csv',index=False)
 pd.DataFrame(details).to_csv(OUT/'DUPLICATE_DECISIONS.csv',index=False)
 (OUT/'DUPLICATE_CHECKS.json').write_text(json.dumps(checks,indent=2))
 print(pd.DataFrame(summary).to_string(index=False))
if __name__=='__main__':main()
