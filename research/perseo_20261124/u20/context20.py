from transfer20 import *

def correlation_modes(q,threshold=.8):
 d1=q['d1'][0];d2=q['d2'][0];market='USA' if 'SPY' in q['tickers'] else ('EU' if 'SXR8.DE' in q['tickers'] else 'TR')
 hist=base(market)
 if market=='USA':hist=add_cash(hist)
 pre=hist['dates']<q['dates'][0];offset=int(pre.sum());c=np.concatenate([hist['C'][pre],q['C']]);obs=np.concatenate([hist.get('low_observed',np.ones_like(hist['C'],bool))[pre],q.get('low_observed',np.ones_like(q['C'],bool))]);modes=np.zeros(len(d1),int);corr=np.full(len(d1),np.nan)
 for kk in range(len(d1)):
  k=kk+offset
  if k<64:continue
  i,j=d1[kk],d2[kk]
  if min(i,j)<0 or i==j:continue
  a=c[k-64:k][:,[i,j]];o=obs[k-64:k][:,[i,j]];good=(o[1:]&o[:-1]).all(1)
  if good.sum()<45:continue
  r=np.diff(np.log(a),axis=0)[good]
  if np.min(np.std(r,axis=0))<1e-9:continue
  corr[kk]=np.corrcoef(r.T)[0,1];modes[kk]=int(corr[kk]<threshold)
 return modes,corr

def fallback(m):
 q=load(STATES/f'{m}_TRANSFER.npz');loc=prepare(m,'LOCAL');names=list(q['tickers']);assert np.array_equal(q['dates'],loc['dates']);src1=q['d1'].copy();src2=q['d2'].copy()
 for k in np.flatnonzero(q['events']):
  pair=[int(src1[0,k]),int(src2[0,k])];original=pair.copy();lp=[int(loc['d1'][0,k]),int(loc['d2'][0,k])]
  for slot in [0,1]:
   if 'CASH_' not in names[original[slot]]:continue
   pick=lp[slot]
   if pick==pair[1-slot] and lp[1-slot]!=pick:pick=lp[1-slot]
   pair[slot]=pick
  q['d1'][0,k:]=pair[0];q['d2'][0,k:]=pair[1]
 # Supply pre-2020 warmup prices so V6 alternatives remain causal and initialized.
 raw=base(m);ds=pd.DatetimeIndex(raw['dates']);n=len(ds)-len(q['dates']);raw['d1'][:]=-1;raw['d2'][:]=-1;raw['d1'][0,n:]=q['d1'][0];raw['d2'][0,n:]=q['d2'][0]
 vc=pd.DataFrame(raw['C'],index=ds,columns=raw['tickers']).rename(columns={'EUR_CASH_A':'BIL','EUR_CASH_B':'SHV'});vc['SPY']=macro(ds).SPY
 allow=np.column_stack([raw['observed'][:,:-2],np.zeros((len(ds),3),bool)])
 ns=v6.__dict__.copy();exec((LEG/'work/V6_PORT_SOURCE.py').read_text(),ns);q['alt']=ns['build_v6_state'](vc,raw['d1'],raw['d2'],raw['basew'],raw['gross'],allowed=allow).alt_idx[:,n:]
 np.savez_compressed(STATES/f'{m}_TRANSFER_LOCAL.npz',**q);return q

def main():
 rows=[];months=[]
 for m in ['EU','USA','TR']:
  families=['LOCAL']+(['NATIVE_REFERENCE'] if m!='TR' else [])
  for family in families:
   q=prepare(m,family);modes,co=correlation_modes(q)
   pd.DataFrame(dict(date=q['dates'],corr63=co,risk_mode=modes)).to_csv(DEST/f'{m}_{family}_CORRELATION.csv',index=False)
   for bps in [15,30]:
    r,mm=run(q,'CORRELATION80',m,family,bps,modes);rows.append(r);months.extend(mm)
  if m=='USA':continue
  q=fallback(m)
  for threshold in [.7,.8,.9]:
   modes,co=correlation_modes(q,threshold);name=f'CORRELATION{int(100*threshold)}'
   for bps in ([15,30] if threshold==.8 else [15]):
    r,mm=run(q,name,m,'TRANSFER_LOCAL',bps,modes);rows.append(r);months.extend(mm)
  for name in ['TRANSFER_BASE','NO_RISK']:
   r,mm=run(q,name,m,'TRANSFER_LOCAL');rows.append(r);months.extend(mm)
  # Additional execution delay: postpone only the translated selection, not market risk.
  delayed={k:v.copy() for k,v in q.items()}
  for k in ['d1','d2']:delayed[k][:,1:]=q[k][:,:-1]
  delayed['events'][1:]=q['events'][:-1];delayed['events'][0]=True
  # Delay the already known alternative signal as well; deliberately test a full one-day stale decision.
  delayed['alt'][:,1:]=q['alt'][:,:-1]
  modes,_=correlation_modes(delayed)
  r,mm=run(delayed,'CORRELATION80_LAG1',m,'TRANSFER_LOCAL',15,modes);rows.append(r);months.extend(mm)
 pd.DataFrame(rows).to_csv(DEST/'CONTEXT_SUMMARY.csv',index=False);pd.DataFrame(months).to_csv(DEST/'MONTHLY_CONTEXT.csv',index=False)
if __name__=='__main__':main()
