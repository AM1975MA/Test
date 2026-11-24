from run20 import *

def make(m,filtered=True):
 q=base(m);u=base('USA');ed=pd.DatetimeIndex(q['dates']);ud=pd.DatetimeIndex(u['dates']);ut=list(u['tickers']);et=list(q['tickers']);bmu=ut.index('SPY');bme=et.index('SXR8.DE' if m=='EU' else 'IE00B5BMR087')
 q['d1'][:]=-1;q['d2'][:]=-1;q['events'][:]=False;q['weights'][:]=.5;q['basew'][:]=.5
 common=ed.intersection(ud);eix=ed.get_indexer(common);uix=ud.get_indexer(common)
 EC=q['C'][eix];UC=u['C'][uix];OBS=q.get('low_observed',np.ones_like(q['C'],bool));eligible=np.ones(len(et),bool);eligible[-2:]=False
 if m=='TR':
  cl=pd.read_csv(DATA/'TR1846_CLASSIFICATION.csv');allowed=set(cl.loc[cl.tradable,'isin']);eligible &= np.array([s in allowed for s in et])
 decisions=[]
 for sk in np.flatnonzero(u['events']):
  date=ud[sk];k=ed.searchsorted(date)
  if k>=len(ed):continue
  end=common.searchsorted(ed[k],side='left');inds=np.arange(end-1,max(-1,end-253),-5)[::-1]
  if len(inds)<27:continue
  er=np.diff(np.log(EC[inds]),axis=0);ur=np.diff(np.log(UC[inds]),axis=0)
  er=er-(er[:,bme]-ur[:,bmu])[:,None]
  er-=er.mean(0);ur-=ur.mean(0)
  good=eligible & OBS[max(0,k-63):k].mean(0).__ge__(.9) & OBS[k-1]
  pair=[]
  for slot,j in enumerate([int(u['d1'][0,sk]),int(u['d2'][0,sk])]):
   y=ur[:,j];var=float(y@y);err=np.sqrt(((er-y[:,None])**2).sum(0)/max(var,1e-15));corr=(y@er)/np.sqrt(np.maximum(var*(er*er).sum(0),1e-30))
   candidates=np.flatnonzero(good & np.isfinite(err))
   if len(candidates):t=int(candidates[np.argmin(err[candidates])]);eratio=float(err[t]);co=float(corr[t])
   else:t=-1;eratio=float('nan');co=float('nan')
   passed=t>=0 and co>=.75 and eratio<=.75
   picked=t if (passed or (not filtered and t>=0)) else len(et)-2+slot
   pair.append(picked)
   decisions.append(dict(market=m,filtered=filtered,execution_date=str(ed[k].date()),source_effective_date=str(date.date()),last_data_date=str(common[inds[-1]].date()),source_ticker=ut[j],best_proxy=et[t] if t>=0 else '',ticker=et[picked],correlation=co,tracking_ratio=eratio,passed=passed,weeks=len(inds)-1,slot=slot))
  q['d1'][0,k:]=pair[0];q['d2'][0,k:]=pair[1];q['events'][k]=True
 # Rebuild only V6 alternatives on the mapped pair, using the existing causal library.
 vc=pd.DataFrame(q['C'],index=ed,columns=et).rename(columns={'EUR_CASH_A':'BIL','EUR_CASH_B':'SHV'});vc['SPY']=macro(ed).SPY
 allow=np.column_stack([q['observed'][:,:-2],np.zeros((len(ed),3),bool)])
 ns=v6.__dict__.copy();exec((LEG/'work/V6_PORT_SOURCE.py').read_text(),ns)
 q['alt']=ns['build_v6_state'](vc,q['d1'],q['d2'],q['basew'],q['gross'],allowed=allow).alt_idx
 q['stop_threshold'],q['rebound']=signals(q)
 q=crop(q,'2020-01-02');tag='TRANSFER' if filtered else 'TRANSFER_UNFILTERED';np.savez_compressed(STATES/f'{m}_{tag}.npz',**q)
 pd.DataFrame(decisions).to_csv(DEST/f'{m}_{tag}_MAPPING.csv',index=False);return q,tag

def main():
 rows=[];months=[]
 for m in ['EU','TR']:
  for filt in [True,False]:
   q,tag=make(m,filt)
   for mode in ['BASE','NO_RISK']:
    # This BASE has different signals; parity only applies to old LOCAL/NATIVE streams.
    name='TRANSFER_BASE' if mode=='BASE' else 'NO_RISK'
    r,mm=run(q,name,m,tag);rows.append(r);months.extend(mm)
 pd.DataFrame(rows).to_csv(DEST/'TRANSFER_SUMMARY.csv',index=False);pd.DataFrame(months).to_csv(DEST/'MONTHLY_TRANSFER.csv',index=False)
if __name__=='__main__':main()
