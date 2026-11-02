"""Build context from frozen past prices and separate availability-aware outcomes."""
import numpy as np,pandas as pd
from core import benchmark_context,leadership,recent_skill
from layer_metrics import topk_weights
from io_utils import ROOT,MARKETS,readcsv,dump,sha

def utility(rr):
 a=np.asarray(rr,float)
 if a.ndim!=2 or a.shape[1]!=3 or not np.isfinite(a).all() or (a<=-1).any():raise ValueError('Complete positive-gross endpoints required')
 l=np.log1p(a);inc=np.column_stack([l[:,0],l[:,1]-l[:,0],l[:,2]-l[:,1]])
 w=np.exp2(-np.arange(3)/2);return inc@w/w.sum()

def group_outcome(frame):
 rr=frame[['fwd_ret_21','fwd_ret_42','fwd_ret_63']].to_numpy(float)
 full=np.isfinite(rr).all() and (rr>-1).all() and frame.exit_date_63.notna().all()
 out=dict(full=bool(full),n=len(frame),available=frame.exit_date_63.max() if full else pd.NaT,delta=np.nan)
 if full:
  u=utility(rr);a=topk_weights(frame.CUM_FIXED_MAPPED);b=topk_weights(frame.CUM_FIT_MAPPED)
  out.update(delta=float((b-a)@u),u_fixed=float(a@u),u_fit=float(b@u))
 return out

def main():
 rows=[];inputs=[];pricechecks=[]
 for m in MARKETS:
  p=ROOT/f'inputs/{m}_FITTING_FRAME.csv.gz';f=readcsv(p);scores=readcsv(ROOT/f'inputs/{m}_MEAN3_SCORES.csv.gz')
  labs=[c for c in f.columns if c not in scores.columns or c in ['signal_date','ticker']]
  s=scores.merge(f[labs],on=['signal_date','ticker'],validate='one_to_one',how='left')
  q=dict(np.load(ROOT/f'inputs/{m}_STATE_HALF.npz',allow_pickle=False));tick='SPY' if m=='USA' else 'EXSA.DE';i=list(q['tickers']).index(tick)
  c=pd.Series(q['C'][:,i],index=pd.DatetimeIndex(q['dates']))
  observed=q.get('observed',np.isfinite(q['C']))[:,i];c=c.loc[observed & np.isfinite(c) & (c>0)]
  ctx=benchmark_context(c);previous=None
  for date,g in s.groupby('signal_date',sort=True):
   good=g[np.isfinite(g.ORIGINAL_CURRENT)].copy();assert len(good)>0
   for col in ['CUM_FIXED_MAPPED','CUM_FIT_MAPPED']:assert good[col].notna().all()
   rec=dict(market=m,date=date,benchmark=tick,**group_outcome(good))
   known=ctx.loc[:date];rec['context_source_date']=known.index[-1] if len(known) else pd.NaT
   if len(known) and (date-known.index[-1]).days<=5:rec.update(known.iloc[-1].to_dict())
   else:rec.update({k:np.nan for k in ctx.columns})
   current=good.set_index('ticker').CUM_FIXED_MAPPED
   rec['leadership']=leadership(current,previous) if previous is not None else np.nan
   rec['matched_leadership_tickers']=len(current.index.intersection(previous.index)) if previous is not None else 0
   previous=current;rows.append(rec)
  c.to_csv(ROOT/f'inputs/{m}_BENCHMARK_CLOSE.csv',header=['close'],index_label='date')
  inputs.append(dict(market=m,fitting_frame_sha=sha(p),score_sha=sha(ROOT/f'inputs/{m}_MEAN3_SCORES.csv.gz'),state_sha=sha(ROOT/f'inputs/{m}_STATE_HALF.npz')))
  pricechecks.append(dict(market=m,benchmark=tick,valid_closes=len(c),first=str(c.index[0].date()),last=str(c.index[-1].date()),nonobserved_removed=int((~observed).sum()),data_source='frozen OLC12 execution state; no new price download; USA explicit quote mask absent'))
 panel=pd.DataFrame(rows).sort_values(['date','market']).reset_index(drop=True)
 panel['recent']=0.;panel['recent_count']=0
 for k,row in panel.iterrows():panel.loc[k,['recent','recent_count']]=recent_skill(panel,row.date,row.market)
 assert (panel.context_source_date.dropna()<=panel.loc[panel.context_source_date.notna(),'date']).all()
 panel.to_csv(ROOT/'inputs/GATE_PANEL.csv',index=False)
 dump(ROOT/'results/CONTEXT_INPUT_AUDIT.json',dict(inputs=inputs,benchmark=pricechecks,rows=len(panel),complete_outcome_groups=panel.groupby('market').full.sum().to_dict(),informative_after_2021=True,context_scope='local equity benchmark plus model-score leadership; not a complete cross-asset macro regime'))
 print(panel.groupby('market').agg(rows=('date','size'),full=('full','sum'),first=('date','min'),last=('date','max')).to_string())
 print('CONTEXT_COMPLETE')
if __name__=='__main__':main()
