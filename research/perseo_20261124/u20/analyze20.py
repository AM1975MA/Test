from run20 import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64,html
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})

def nav(m,kind,bps=15):
 if kind=='LOCAL':p=DEST/f'{m}_LOCAL_BASE_{bps}.npz'
 elif kind=='NATIVE':p=DEST/f'{m}_NATIVE_REFERENCE_BASE_{bps}.npz'
 elif kind=='UNIFIED':p=DEST/('USA_NATIVE_REFERENCE_BASE_'+str(bps)+'.npz' if m=='USA' else f'{m}_TRANSFER_LOCAL_TRANSFER_BASE_{bps}.npz')
 elif kind=='WF':p=DEST/f'{m}_ARCHITECTURE_WF_ARCH_ECONOMIC_{bps}.npz'
 elif kind=='ISOLATED_NATIVE':p=DEST/f'{m}_NATIVE_REFERENCE_ISOLATED_{bps}.npz'
 elif kind=='BENCHMARK':
  q=prepare(m,'LOCAL');j=list(q['tickers']).index('SPY' if m=='USA' else ('SXR8.DE' if m=='EU' else 'IE00B5BMR087'));a=9999/(1+bps/10000)/10000*q['O'][:,j]/q['O'][0,j];a[0]=1;return pd.Series(a,index=pd.DatetimeIndex(q['dates']))
 else:raise ValueError(kind)
 z=load(p);return pd.Series(z['nav'],index=pd.DatetimeIndex(z['dates']))

def months(s):
 # Attribute each opening-to-next-opening P&L to the starting trading session.
 r=pd.Series(s.to_numpy()[1:]/s.to_numpy()[:-1]-1,index=s.index[:-1]);return (1+r).groupby(r.index.to_period('M')).prod()-1

def audit_accounts():
 out=[]
 for p in sorted(DEST.glob('*.npz')):
  m=p.name.split('_')[0]
  if m not in ['EU','USA','TR']:continue
  q=prepare(m,'LOCAL');z=load(p);O=q['O'];names=list(q['tickers']);units=z['primary_units']+z['defensive_units'];n=len(O);cashids=np.array(['CASH_' in t for t in names]);cash=float(1);oldunits=np.zeros(O.shape[1]);maxdu=maxcash=0.
  orders=pd.read_csv(p.with_name(p.stem+'_ORDERS.csv'));sp=p.with_name(p.stem+'_STOPS.csv')
  st=pd.read_csv(sp) if sp.stat().st_size>2 else pd.DataFrame();stopprice={} if st.empty else {(int(r.signal_index),r.ticker):r.fill_price for r in st.itertuples()}
  groups={int(k):x for k,x in orders.groupby('index')}
  for k in range(n-1):
   du=np.zeros(len(names));flow=0.
   if k in groups:
    for r in groups[k].itertuples():
     j=names.index(r.ticker);price=O[k,j] if r.kind=='REBALANCE' else stopprice[k,r.ticker];du[j]+=r.signed_notional_eur/10000/price;flow+=r.signed_notional_eur/10000+r.cost_eur/10000
   maxdu=max(maxdu,float(np.max(np.abs((units[k]-oldunits-du)[~cashids]))));cash-=flow
   actual=float(z['free_cash'][k]+(units[k,cashids]*O[k,cashids]).sum());maxcash=max(maxcash,abs(cash-actual));oldunits=units[k]
  assert maxdu<1e-10 and maxcash<1e-9,(p,maxdu,maxcash)
  out.append(dict(file=p.name,max_units_residual=maxdu,max_cash_residual=maxcash))
 pd.DataFrame(out).to_csv(DEST/'INDEPENDENT_LEDGER_AUDIT.csv',index=False);return out

def main():
 rows=[];mr=[];ar=[];reg=[]
 for m in ['EU','USA','TR']:
  for kind in ['LOCAL','UNIFIED','WF','BENCHMARK']+(['NATIVE'] if m!='TR' else []):
   s=nav(m,kind);rows.append(dict(market=m,strategy=kind,**metrics(s.index,s.to_numpy())))
   mo=months(s)
   mr.extend(dict(market=m,strategy=kind,month=str(d),net_return=float(v)) for d,v in mo.items())
   ar.extend(dict(market=m,strategy=kind,year=int(y),net_return=float((1+v).prod()-1)) for y,v in mo.groupby(mo.index.year))
   for label,a,b in [('2020-2022','2020-01-02','2023-01-03'),('2023-2026','2023-01-03','2026-07-01')]:
    ss=s[(s.index>=a)&(s.index<=b)];reg.append(dict(market=m,strategy=kind,regime=label,**metrics(ss.index,ss.to_numpy()/ss.iloc[0])))
 summary=pd.DataFrame(rows);monthly=pd.DataFrame(mr);annual=pd.DataFrame(ar)
 summary.to_csv(DEST/'SUMMARY_FINAL.csv',index=False);monthly.to_csv(DEST/'MONTHLY_FINAL.csv',index=False);annual.to_csv(DEST/'ANNUAL_FINAL.csv',index=False);pd.DataFrame(reg).to_csv(DEST/'REGIMES_FINAL.csv',index=False)
 rng=np.random.default_rng(20261123);n=78;ix=((rng.integers(0,n,(3000,7,1))+np.arange(12))%n).reshape(3000,-1)[:,:n];stats=[]
 for ref in ['LOCAL','BENCHMARK']:
  dif=[]
  for m in ['EU','USA','TR']:
   a=months(nav(m,'UNIFIED'));b=months(nav(m,ref));assert len(a)==n and a.index.equals(b.index);d=(np.log1p(a)-np.log1p(b)).to_numpy();dif.append(d);boot=d[ix].mean(1)*12
   stats.append(dict(reference=ref,market=m,annual_log_excess=float(d.mean()*12),ci_low=float(np.quantile(boot,.025)),ci_high=float(np.quantile(boot,.975)),positive_fraction=float((boot>0).mean())))
  d=np.array(dif).T;boot=np.min(d[ix].mean(1)*12,axis=1);stats.append(dict(reference=ref,market='WORST_OF_THREE',annual_log_excess=float(min(d.mean(0)*12)),ci_low=float(np.quantile(boot,.025)),ci_high=float(np.quantile(boot,.975)),positive_fraction=float((boot>0).mean())))
 pd.DataFrame(stats).to_csv(DEST/'CONFIDENCE_FINAL.csv',index=False)
 # All monthly failures and gains, not just winning examples.
 diag=[]
 for m in ['EU','USA','TR']:
  a=months(nav(m,'UNIFIED'));b=months(nav(m,'LOCAL'));bench=months(nav(m,'BENCHMARK'))
  for dt in a.index:diag.append(dict(market=m,month=str(dt),unified=float(a[dt]),local=float(b[dt]),benchmark=float(bench[dt]),delta_vs_local=float(a[dt]-b[dt]),delta_vs_benchmark=float(a[dt]-bench[dt])))
 pd.DataFrame(diag).to_csv(DEST/'MONTHLY_DIAGNOSIS.csv',index=False)
 # Prior-close tracking and prefix invariance checks on the new stop features.
 checks=[]
 for m in ['EU','USA','TR']:
  q=base(m)
  if m=='USA':q=add_cash(q)
  full=signals(q)
  for k in [250,800,1400]:
   cut={key:(v[:k+1] if getattr(v,'ndim',0)>0 and v.shape[0]==len(q['dates']) else v) for key,v in q.items()};short=signals(cut)
   for a,b in zip(full,short):assert np.array_equal(a[:k+1],b)
   changed={key:v.copy() for key,v in q.items()};changed['C'][k:]*=1.23
   alt=signals(changed)
   for a,b in zip(full,alt):assert np.array_equal(a[:k+1],b[:k+1])
   checks.append(dict(market=m,cutoff=str(pd.Timestamp(q['dates'][k]).date()),prefix=True,current_and_future_mutation=True))
 for m in ['EU','TR']:
  for f in ['TRANSFER','TRANSFER_UNFILTERED']:
   x=pd.read_csv(DEST/f'{m}_{f}_MAPPING.csv');assert (x.last_data_date<x.execution_date).all();assert(x.source_effective_date<=x.execution_date).all()
 audit=audit_accounts()
 (DEST/'QA_FINAL.json').write_text(json.dumps(dict(status='PASS',accounts=len(audit),feature_checks=checks,base_parity_accounts=5,scope='Causal new transforms and independent cash/units ledger; no certification of upstream point-in-time catalogues or price availability'),indent=2))
 # New portfolio capacity, using only earlier observed turnover.
 p=load(DATA/'TR1846_OHLCV.npz');names=list(p['names']);ds=pd.DatetimeIndex(p['dates']);turn=pd.DataFrame(p['C']*p['V'],index=ds,columns=names).where(p['observed']);adv=turn.rolling(63,min_periods=20).mean().shift(1)
 q=prepare('TR','LOCAL');orders=pd.read_csv(DEST/'TR_TRANSFER_LOCAL_TRANSFER_BASE_15_ORDERS.csv');liq=[]
 for r in orders.itertuples():
  d=pd.Timestamp(q['dates'][r.index]);a=float(adv.loc[d,r.ticker]);liq.append(dict(date=str(d.date()),ticker=r.ticker,notional=r.notional_eur,adv63=a,participation=r.notional_eur/a if a>0 else np.nan))
 pd.DataFrame(liq).to_csv(DEST/'TR_UNIFIED_LIQUIDITY.csv',index=False)
 # Inspect all proxy sources of the economic improvements.
 fig,axes=plt.subplots(2,3,figsize=(15,8),sharex='col');cols={'LOCAL':'#9a9a9a','UNIFIED':'#007f78','BENCHMARK':'#cc8730','WF':'#9e559c'}
 for col,m in enumerate(['EU','USA','TR']):
  for kind in ['LOCAL','UNIFIED','BENCHMARK','WF']:
   s=nav(m,kind);axes[0,col].plot(s.index,s*10000,label={'LOCAL':'U19 comune','UNIFIED':'Candidato trasferimento','BENCHMARK':'S&P 500','WF':'Scelta annuale WF'}[kind],color=cols[kind],lw=1.5);axes[1,col].plot(s.index,100*(s/s.cummax()-1),color=cols[kind],lw=1)
  axes[0,col].set_title(m+' — apertura / apertura');axes[0,col].set_yscale('log');axes[0,col].grid(alpha=.2);axes[1,col].grid(alpha=.2);axes[1,col].tick_params(axis='x',rotation=40)
 axes[0,0].set_ylabel('Capitale, scala log');axes[1,0].set_ylabel('Drawdown %');axes[0,0].legend(fontsize=8);fig.suptitle('Perseo U20 — candidato strutturale e processo walk-forward',fontsize=15);fig.tight_layout();fig.savefig(NEW/'PERSEO_U20_CONFRONTO.png',dpi=150);plt.close(fig)
 print(summary[['market','strategy','cagr','maxdd']].to_string(index=False));print(pd.DataFrame(stats).to_string(index=False));print('AUDITED',len(audit),flush=True)
if __name__=='__main__':main()
