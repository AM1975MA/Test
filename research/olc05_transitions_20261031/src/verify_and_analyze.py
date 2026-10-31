"""Independent arithmetic, temporal invariance, state attribution and paired inference."""
from io_common import *
from vector_engine import simulate
from run_transitions import targets_top4
import sys
OUT=ROOT/'results';PATHS=OUT/'paths'
def phase_method(strategy):
 if strategy in ['LEGACY','IMMEDIATE']:return dict(policy='IMMEDIATE',legacy_slots=strategy=='LEGACY')
 if strategy.startswith('PARTIAL'):return dict(policy='PARTIAL',fraction=int(strategy.split('_')[0][7:])/100)
 if strategy.startswith('PHASE'):return dict(policy='PHASE',fraction=int(strategy.split('_')[0][5:]))
 return dict(policy=strategy)
def main():
 d=pd.concat([pd.read_csv(OUT/f) for f in ['SCORECARD.csv','FINITE_SCORECARD.csv','SENSITIVITY_SCORECARD.csv']],ignore_index=True)
 d.to_csv(OUT/'ALL_SCORECARD.csv',index=False);aud=[];stats=[];dust=[];fee_bridge=[];monthly={};prefix=[];replay=[]
 cache={};rawcache={}
 for config,group in d.groupby('config',sort=True):
  row=group.iloc[0];m=row.market;w=row.weight;s=row.strategy;fee=float(row.fee)
  q,e,cal=cache.setdefault((m,w),load(m,w));ds=pd.DatetimeIndex(q['dates']);value_dates=ds[1:]
  path=PATHS/f'{config}.npz';r=dict(np.load(path,allow_pickle=False));nav=r['nav'];L=r['ledger'];u=r['primary_units'];defu=r['defensive_units']
  # Independent dot products of closing quantities with next observed/valuation Open.
  v=(np.einsum('ij,ij->i',u[:-1],q['O'][1:])+np.einsum('ij,ij->i',defu[:-1],q['O'][1:])+r['free_cash'][:-1])
  err=float(np.max(abs(v-nav[:-1])));assert err<1e-10,(config,err)
  # Self-financing ledger identity and independent sequential ratios.
  ratio=v/L[:-1,0];assert np.max(abs(np.cumprod(ratio)-nav[:-1]))<1e-10
  raw=pd.read_pickle(SOURCE/f'inputs/{m}_Open.pkl') if m not in rawcache else rawcache[m];rawcache[m]=raw
  real=raw.reindex(index=ds,columns=q['tickers']).to_numpy()
  for j,t in enumerate(q['tickers']):
   if t.startswith('EUR_CASH_'):real[:,j]=1.
  delta=np.diff(np.vstack([np.zeros(u.shape[1]),u+defu]),axis=0)
  invalid=int(np.sum((np.abs(delta[:-1])>1e-14)&(~np.isfinite(real[:-1])|(real[:-1]<=0))))
  assert invalid==0,(config,'unobserved execution',invalid)
  # Consequential metrics: product of simple ratios, independent max-wealth traversal.
  maxerr=0.
  for rr in group.itertuples():
   a=pd.Timestamp(rr.first_valuation);b=pd.Timestamp(rr.last_valuation);mask=(value_dates>=a)&(value_dates<=b)
   eq=np.cumprod(ratio[mask]);cagr=float(eq[-1]**(252./len(eq))-1.)
   peak=1.;mdd=0.
   for x in eq:peak=max(peak,x);mdd=min(mdd,x/peak-1.)
   me=max(abs(cagr-rr.cagr),abs(mdd-rr.maxdd),abs(eq[-1]-1-rr.period_return));maxerr=max(maxerr,me)
  assert maxerr<1e-10
  aud.append({'config':config,'rows_checked':len(nav)-1,'independent_nav_error':err,'max_three_metric_error':maxerr,'unobserved_executions':invalid,'path_sha256':digest(path)})
  lr=np.log(ratio);df=pd.DataFrame({'valuation_date':value_dates,'log_return':lr});ser=df.groupby(df.valuation_date.dt.to_period('M')).log_return.sum();monthly[(m,w,s,fee)]=ser
  # Side-by-side legacy decision-label boundary (do not mix with actual-date primary).
  ix=(ds[:-1]>='2021-01-01')&(ds[:-1]<='2024-12-31');eq=np.cumprod(ratio[ix]);mdd=float(np.min(eq/np.maximum.accumulate(np.r_[1.,eq])[1:]-1))
  stats.append({'market':m,'weight':w,'strategy':s,'fee':fee,'period':'LEGACY_DECISION_LABEL_2021_2024','cagr':float(eq[-1]**(252/len(eq))-1),'maxdd':mdd})
  # How much risky primary capital no longer belongs to current CL01 pair?
  pv=u[:-1]*q['O'][:-1];total=pv.sum(1);on=np.zeros(len(total))
  for k in range(len(total)):
   ids=set([int(q['d1'][0,k]),int(q['d2'][0,k])]);on[k]=sum(pv[k,j] for j in ids if j>=0)
  oldshare=np.divide(total-on,total,out=np.zeros_like(on),where=total>1e-14)
  # Reconstruct pre-stop units to characterize micro-position stop events, not a new filter.
  tiny_n=allstops=alltiny_days=0;smallweight=[]
  for k in range(len(nav)-1):
   before=r['targets'][k]*L[k,1]*(L[k,0]-L[k,5])/q['O'][k] if L[k,3] else (np.zeros(u.shape[1]) if k==0 else u[k-1].copy())
   stopped=(before>0)&(u[k]==0)
   nn=int(stopped.sum());assert nn==int(L[k,8]),(config,k,nn,L[k,8])
   if nn:
    wstop=before[stopped]*q['O'][k,stopped]/L[k,0];smallweight+=wstop.tolist();tiny_n+=int((wstop<.001).sum());allstops+=nn
    alltiny_days+=int(np.all(wstop<.001) and not L[k,9])
  dust.append({'market':m,'weight':w,'strategy':s,'fee':fee,'mean_primary_outside_current_pair':float(oldshare.mean()),'stop_executions':allstops,'stops_position_below_0_1pct_nav':tiny_n,'days_only_small_stops_no_systemic':alltiny_days,'median_stopped_position_weight':float(np.median(smallweight)) if smallweight else None})
  # Reexecute every pre-phase path, independently compare all saved arrays after final code.
  if not s.startswith('PHASE'):
   args=phase_method(s.split('_')[0]);args.update(risk_on=not s.endswith('RISKOFF'),lag_systemic=s.endswith('LAG1'))
   rr=simulate(q,e,fee=fee,top4=targets_top4(q,cal,m),**args)
   er=float(np.max(abs(rr['nav']-nav)));assert er==0,(config,er)
   replay.append({'config':config,'max_nav_change_after_phase_code':er})
 pd.DataFrame(aud).to_csv(OUT/'INDEPENDENT_VERIFICATION.csv',index=False);pd.DataFrame(stats).to_csv(OUT/'LEGACY_DATE_CONVENTION.csv',index=False);pd.DataFrame(dust).to_csv(OUT/'HOLDING_AND_STOP_DIAGNOSTICS.csv',index=False);pd.DataFrame(replay).to_csv(OUT/'FINAL_REGRESSION72.csv',index=False)
 # Matched block resampling, same months and sampled blocks in USA/EU.
 results=[];joinrows=[]
 for weight in ['HALF','ORIGINAL']:
  for fee in [.001,.003]:
   for strategy in ['PARTIAL50','TOP4','COHORT2','PHASE3','PHASE5','PHASE7','PHASE21']:
    frame=pd.concat({m:monthly[(m,weight,strategy,fee)]-monthly[(m,weight,'IMMEDIATE',fee)] for m in ['EU','USA']},axis=1).dropna()
    for window,end in [('ACTIVE2021_2024','2024-12'),('FULL_MONTHS','2026-06')]:
     lo='2021-01' if window=='ACTIVE2021_2024' else '2019-02';ff=frame.loc[lo:end];x=ff.to_numpy();n=len(x)
     for block in [3,6]:
      rng=np.random.default_rng(20261031);starts=rng.integers(0,n,(6000,(n+block-1)//block));ix=((starts[:,:,None]+np.arange(block))%n).reshape(6000,-1)[:,:n];dist=x[ix].mean(1)*1200;point=x.mean(0)*1200
      for j,m in enumerate(['EU','USA']):
       low,high=np.quantile(dist[:,j],[.025,.975]);results.append({'market':m,'weight':weight,'fee':fee,'strategy':strategy,'reference':'IMMEDIATE','window':window,'block_months':block,'months':n,'annual_log_difference_pp':float(point[j]),'ci95_low_pp':float(low),'ci95_high_pp':float(high),'bootstrap_positive_fraction':float((dist[:,j]>0).mean()),'interpretation':'paired_resampling_stability_NOT_posterior_or_future_success'})
      joinrows.append({'weight':weight,'fee':fee,'strategy':strategy,'window':window,'block_months':block,'both_positive_fraction':float(np.all(dist>0,axis=1).mean()),'interpretation':'empirical_resampling_NOT_probability_of_future_outperformance'})
 pd.DataFrame(results).to_csv(OUT/'PAIRED_BOOTSTRAP.csv',index=False);pd.DataFrame(joinrows).to_csv(OUT/'PAIRED_JOINT_SUPPORT.csv',index=False)
 monthlyrows=[]
 for (m,w,s,fee),series in monthly.items():
  for mon,lr in series.items():monthlyrows.append({'market':m,'weight':w,'strategy':s,'fee':fee,'month':str(mon),'log_return':lr})
 pd.DataFrame(monthlyrows).to_csv(OUT/'MONTHLY_RETURNS.csv',index=False)
 # Prefix perturbations on actual data, no claim of refitting original experts.
 for m in ['EU','USA']:
  q,e,cal=load(m,'HALF');cut=np.searchsorted(q['dates'],np.datetime64('2023-01-01'));D=len(e)
  for name,args in [('IMMEDIATE',{}),('PARTIAL50',{'policy':'PARTIAL','fraction':.5}),('PHASE5',{'policy':'PHASE','fraction':5}),('COHORT2',{'policy':'COHORT2'})]:
   a=simulate(q,e,**args);mod={k:v.copy() for k,v in q.items()}
   for k in ['O','L','C','PC']:mod[k][cut:]*=1.3
   for k in ['gap','ud1','uneg']:mod[k][cut:]*=-1
   for k in ['d1','d2']:mod[k][:,cut:]=(mod[k][:,cut:]+7)%len(q['tickers'])
   b=simulate(mod,e,**args)
   er=float(np.max(abs(a['nav'][:cut-1]-b['nav'][:cut-1])));te=float(np.max(abs(a['targets'][:cut]-b['targets'][:cut])));assert er==te==0
   prefix.append({'market':m,'policy':name,'cutoff':'2023-01-01','nav_prefix_error':er,'decision_prefix_error':te})
 pd.DataFrame(prefix).to_csv(OUT/'PREFIX_INVARIANCE.csv',index=False)
 # Source snapshot chronology, no new forecasts trained.
 chronology=[]
 for m in ['EU','USA']:
  f=pd.read_csv(ROOT/f'source/paired_frontier_20261031/results/calendar/{m}_FORECASTS.csv.gz',parse_dates=['signal_date','source_date'])
  bad=int((f.source_date>f.signal_date).sum());assert bad==0;chronology.append({'market':m,'forecast_rows':len(f),'source_after_signal':bad})
 summary={'paths':len(aud),'daily_intervals_checked':sum(x['rows_checked'] for x in aud),'metrics_recomputed':len(d)*3,'maximum_nav_error':max(x['independent_nav_error'] for x in aud),'maximum_metric_error':max(x['max_three_metric_error'] for x in aud),'unobserved_executions':sum(x['unobserved_executions'] for x in aud),'previous_paths_reexecuted_unchanged':len(replay),'real_prefix_checks':len(prefix),'source_chronology':chronology,'new_model_fits':0,'date_convention':'primary uses actual next-Open valuation date, excludes terminal flat observation; legacy-decision-label metric separately retained','scope':'synthetic alias audit plus capital transition; not certified real economic group map, survival/time-to-event predictor or live execution'}
 (OUT/'VERIFIED_SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
 print(pd.DataFrame(results).query("strategy=='PHASE5' and weight=='HALF' and block_months==6")[['market','fee','window','annual_log_difference_pp','ci95_low_pp','ci95_high_pp']].to_string(index=False))
if __name__=='__main__':main()
