#!/usr/bin/env python3
"""OLC38 EU factor attribution / leader falsification. Preregistered before outcomes (GitHub 3a335ab).
NO adjustments to existing ETF predictors, NAVs, USA, main, trading contracts or timestamps.
"""
from __future__ import annotations
import argparse,io,zipfile,hashlib,json,math
from pathlib import Path
from collections import defaultdict
import numpy as np,pandas as pd
from scipy.optimize import minimize
from scipy.stats import spearmanr

H19='3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540'
H32='aef33c5c1aac60a944f7cf767b7ee637eb4ca254710b431c95b5f13a67fd6b8d'
HMINI='6b4d59814dfeaab8fac415498755cdad664e76b20a424eb0e0aac6568a771f8d'
BASE=['EXSA.DE','SXR8.DE','SXRV.DE','QDVE.DE','EXX1.DE']
ADD=['VVSM.DE','EXV5.DE','EXV9.DE']
FAC=BASE+ADD
YRS=[2021,2022,2023,2024]
SEED=38001


def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as fh:
  for b in iter(lambda:fh.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

def npzin(z,suffix):
 keys=[n for n in z.namelist() if n.endswith(suffix)]
 assert len(keys)==1,(suffix,keys)
 with np.load(io.BytesIO(z.read(keys[0])),allow_pickle=False) as x:return {k:x[k] for k in x.files}

def csvin(z,suffix):
 keys=[n for n in z.namelist() if n == suffix or (suffix.startswith('/') and n.endswith(suffix))]
 assert len(keys)==1,(suffix,keys)
 return pd.read_csv(io.BytesIO(z.read(keys[0])),compression='gzip' if suffix.endswith('.gz') else None)

def style_fit(X,y):
 assert X.ndim==2 and X.shape[0]==252 and X.shape[1]>=5 and len(y)==252
 lam=1e-7;k=X.shape[1]
 def f(w):
  e=y-X@w;return float(np.mean(e*e)+lam*w@w)
 def grad(w):return (-2*X.T@(y-X@w)/len(y)+2*lam*w)
 r=minimize(f,np.ones(k)/(2*k),jac=grad,method='SLSQP',bounds=[(0,1)]*k,
   constraints=[{'type':'ineq','fun':lambda w:1-w.sum(), 'jac':lambda w:-np.ones(k)}],
   options={'ftol':1e-14,'maxiter':5000})
 if not r.success:raise RuntimeError(f'solver {r.message}')
 w=np.maximum(0,r.x)
 assert w.sum()<=1+1e-9
 return w

def basic_metrics(v):
 v=np.asarray(v,float);r=np.diff(v)/v[:-1];n=len(r)
 return {'n_intervals':int(n),'end_index':float(v[-1]/v[0]*100),
  'cagr_252_pct':float(100*((v[-1]/v[0])**(252/n)-1)),
  'annual_vol_pct':float(100*np.std(r,ddof=1)*np.sqrt(252)),
  'maxdd_pct':float(100*np.min(v/np.maximum.accumulate(v)-1)),
  'annual_loggrowth_pct':float(100*252*np.mean(np.log1p(r)))}

def month_metrics(v):
 v=np.asarray(v,float);ret=np.diff(v)/v[:-1];n=len(ret)
 return {'n_months':int(n),'ending_index':float(100*v[-1]/v[0]),
   'cagr_12_pct':float(100*((v[-1]/v[0])**(12/n)-1)),
   'ann_vol_from_monthly_pct':float(100*np.std(ret,ddof=1)*np.sqrt(12)),
   'maxdd_monthly_pct':float(100*np.min(v/np.maximum.accumulate(v)-1))}

def half_l1(w0,w1):return float(.5*np.abs(w0-w1).sum())

def monthly_boot_ci(d,months,draw=4000):
 """Circular consecutive 6-calendar-month block bootstrap, predetermined."""
 assert len(d)==len(months) and len(d)>=36
 labels=pd.PeriodIndex(months,freq='M')
 assert labels.is_unique and labels.is_monotonic_increasing
 assert all(labels[i]+1==labels[i+1] for i in range(len(labels)-1))
 rng=np.random.default_rng(SEED);n=len(d);means=[]
 for it in range(draw):
  ids=[]
  while len(ids)<n:
   start=int(rng.integers(n));ids.extend((start+j)%n for j in range(6))
  means.append(float(np.mean(np.asarray(d)[ids[:n]])))
 return np.asarray(means)


def prepare(source19,source32):
 h19=digest(source19);h32=digest(source32)
 mini=(source19.resolve()==source32.resolve() and h19==HMINI)
 if not mini and (h19!=H19 or h32!=H32):raise RuntimeError(f'SHA mismatch {h19},{h32}')
 with zipfile.ZipFile(source19) as z:
  s=npzin(z,'/inputs/EU_STATE_HALF.npz');p=npzin(z,'/results/paths/EU_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz')
  card=csvin(z,'olc19_combined_risk_20261102/results/SCORECARD.csv')
 with zipfile.ZipFile(source32) as z:
  cal=csvin(z,'results/REPAIRED_CALENDAR_AUDIT.csv')
  labels=csvin(z,'results/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz')
 dates=pd.DatetimeIndex(s['dates']);ticks=s['tickers'].astype(str);O=s['O'];obs=s['observed']
 assert dates.is_monotonic_increasing and dates.is_unique and pd.Index(ticks).is_unique
 assert dates.equals(pd.DatetimeIndex(p['dates'])) and np.array_equal(ticks,p['tickers'].astype(str))
 assert O.shape==obs.shape==(len(dates),len(ticks))
 nav=np.r_[1.,p['nav'][:-1]];assert (nav>0).all()
 ix=np.array([np.where(ticks==t)[0].item() for t in FAC],int)
 pr=O[:,ix];bo=obs[:,ix]&np.isfinite(pr)&(pr>0)
 # Official parent scorecard, not a new NAV or backtest.
 sub=card[(card.market=='EU')&(card.variant=='TOP2_CONTEXT_REVALUE')&
  (card.contract=='FAST_LOCK3')&(np.isclose(card.fee,.001))&(np.isclose(card.stop_friction,.001))&
  (~card.stress.astype(bool))&(card.period=='ACTIVE2021_2024')]
 assert len(sub)==1
 assert abs(sub.cagr.iloc[0]-.232)<1e-4
 cal=cal[cal.market=='EU'].copy();cal[['signal_date','entry_date','exit_date']]=cal[['signal_date','entry_date','exit_date']].apply(pd.to_datetime);cal=cal.sort_values('signal_date').reset_index(drop=True)
 assert cal.signal_date.is_unique and len(cal)==90
 labels=labels[labels.market=='EU'].copy()
 return {'h19':H19 if mini else h19,'h32':H32 if mini else h32,'compact_source_sha':HMINI if mini else None,'dates':dates,'ticks':ticks,'O':O,'obs':obs,'nav':nav,'pr':pr,'bo':bo,'ix':ix,'p':p,'cal':cal,'labels':labels,'card':sub.iloc[0]}


def audit(data,out):
 dates=data['dates'];bo=data['bo'];pr=data['pr'];obs=data['obs'];ticks=data['ticks'];O=data['O'];nav=data['nav']
 is_main=(dates.year>=2021)&(dates.year<=2024)
 named_mech=['EU_SOURCE_OBSERVED', 'ORIGINAL_EU_OPEN_QUOTES']
 rows=[]
 for j,t in enumerate(FAC):
  ids=np.flatnonzero(bo[:,j]);rows.append({'ticker':t,'first_observed_open':str(dates[ids[0]].date()),
    'observed_dates_total':len(ids),'observed_2021_24':int(bo[is_main,j].sum()),
    'raw_2021_24':int(is_main.sum())})
 pd.DataFrame(rows).to_csv(out/'PROXY_AVAILABILITY.csv',index=False)
 not_all=dates[is_main&(~bo.all(axis=1))]
 return {'EU_total_dates':len(dates),'EU_tickers':len(ticks),'EU_main_calendar_dates':int(is_main.sum()),
  'all_eight_observed_main_dates':int((is_main&bo.all(axis=1)).sum()),
  'dates_not_common_eight_main':list(not_all.strftime('%Y-%m-%d')),
  'state_2020_06_01_observed':int(obs[dates.get_loc('2020-06-01')].sum()),
  'state_2020_06_02_observed':int(obs[dates.get_loc('2020-06-02')].sum()),
  'LEEU_observed_2024_05_02':bool(obs[dates.get_loc('2024-05-02'),np.where(ticks=='LEEU.DE')[0][0]]),
  'universe_is_source_observed_165_not_independently_PIT':True,
  'issuer_total_return_distribution_not_reconciled':True,
  'GateA':'FAIL_INCOMPLETE_PIT_TR_EXECUTION','US_engine_unchanged':True}


def f1_clones(D,out):
 dates=D['dates'];pr=D['pr'];bo=D['bo'];nav=D['nav'];
 # Comparable 2021-24 eight-way observed sessions, no price invention.
 valix=np.flatnonzero(bo.all(axis=1)&(dates>=pd.Timestamp('2021-01-04'))&(dates<=pd.Timestamp('2024-12-30')))
 vd=dates[valix];P=pr[valix];N=nav[valix];assert len(vd)>980 and len(vd)==len(pd.DatetimeIndex(vd).unique())
 # Train windows evaluated separately, 5 versus 7/8 proxies. All labels end strictly before year start.
 models={};fits=[]
 for y in YRS:
  for tag,feat in [('F0_FIVE',list(range(5))),('F1_EIGHT_ASOF',list(range(8)) if y>=2022 else [0,1,2,3,4,6,7])]:
   qualified=bo[:,feat].all(axis=1)&(dates<pd.Timestamp(f'{y}-01-01'))
   idx=np.flatnonzero(qualified)
   assert len(idx)>=253,(tag,y,len(idx))
   vs=idx[-253:] # exactly 252 returns with source observed at both endpoints
   ret=pr[vs[1:],:][:,feat]/pr[vs[:-1],:][:,feat]-1
   yret=nav[vs[1:]]/nav[vs[:-1]]-1
   assert len(yret)==252 and dates[vs[-1]]<pd.Timestamp(f'{y}-01-01')
   w=style_fit(ret,yret);k=np.zeros(len(FAC));k[feat]=w;models[(y,tag)]=k
   fitR=ret@w
   fits.append({'year':y,'clone':tag,'last_fit_open':str(dates[vs[-1]].date()),'n_train_paired':len(yret),
    'n_factor_proxies':len(feat),'cash_weight_pct':100*(1-w.sum()),'train_error_rmse_bp':1e4*np.sqrt(np.mean((yret-fitR)**2)),
    'train_return_corr':np.corrcoef(yret,fitR)[0,1],**{f'weight_{t}':k[j] for j,t in enumerate(FAC)}})
 fit=pd.DataFrame(fits);fit.to_csv(out/'F1_STYLE_TRAIN_BY_YEAR.csv',index=False)
 # Independently replay both clones on same index. Source NAV no change; fees on only annual rebalance.
 trace=[{'date':str(vd[0].date()),'year':int(vd[0].year),'strategy':100.0}]
 portfolios={};trades=[]
 for tag in ['F0_FIVE','F1_EIGHT_ASOF']:
  w=models[(int(vd[0].year),tag)].copy();cash=1-w.sum();
  initial_fee=.001*half_l1(np.r_[np.zeros(8),1],np.r_[w,cash]);value=100*(1-initial_fee)
  portfolios[tag]={'weight':w,'value':value,'cum_fee':initial_fee,'fees':[initial_fee],'vals':[100.0]}
  trace[0][tag]=100.0  # initial fee is paid out of 100 starting wealth in the first interval
  trades.append({'clone':tag,'date':str(vd[0].date()),'year':int(vd[0].year),'turnover':half_l1(np.r_[np.zeros(8),1],np.r_[w,cash]),'fee_fraction':initial_fee,'cash_weight_after':cash})
 for j in range(1,len(vd)):
  date=vd[j];r=P[j]/P[j-1]-1
  row={'date':str(date.date()),'year':int(date.year),'strategy':float(100*N[j]/N[0])}
  for tag in ['F0_FIVE','F1_EIGHT_ASOF']:
   z=portfolios[tag];g=1+float(z['weight']@r);assert g>0
   z['value']*=g;z['weight']=z['weight']*(1+r)/g
   if vd[j-1].year!=date.year:
    target=models[(int(date.year),tag)].copy()
    hto=half_l1(np.r_[z['weight'],1-z['weight'].sum()],np.r_[target,1-target.sum()])
    fee=.001*hto;z['value']*=1-fee;z['cum_fee']+=fee;z['fees'].append(fee)
    z['weight']=target
    trades.append({'clone':tag,'date':str(date.date()),'year':int(date.year),'turnover':hto,'fee_fraction':fee,'cash_weight_after':1-target.sum()})
   row[tag]=z['value']
   row['weight_'+tag+'_cash']=1-z['weight'].sum()
  trace.append(row)
 tr=pd.DataFrame(trace);tr.to_csv(out/'F1_CLONE_MATCHED_DAILY.csv',index=False,float_format='%.12g')
 pd.DataFrame(trades).to_csv(out/'F1_CLONE_TRADES.csv',index=False)
 # actual portfolio period return process aligned to eight valid days
 yN=N[1:]/N[:-1]-1
 percs={}
 for tag in ['F0_FIVE','F1_EIGHT_ASOF']:
  v=tr[tag].to_numpy();xr=v[1:]/v[:-1]-1
  m=basic_metrics(v);m['tracking_rmse_bp_day']=float(1e4*np.sqrt(np.mean((yN-xr)**2)))
  m['out_of_time_daily_return_corr']=float(np.corrcoef(yN,xr)[0,1]);m['mean_daily_residual_bp']=float(1e4*np.mean(yN-xr));m['target_vol_ratio']=float(np.std(xr)/np.std(yN))
  m['total_nominal_fee_fracs']=float(portfolios[tag]['cum_fee']);percs[tag]=m
 percs['OLC19_SOURCE_MATCHED']=basic_metrics(100*N/N[0]);percs['matched_period']=[str(vd[0].date()),str(vd[-1].date())]
 # paired ex-post residual by calendar month, descriptive month blocks and no promotion
 dtmp=pd.DataFrame({'date':vd[1:],'actual':yN,'r0':tr.F0_FIVE.to_numpy()[1:]/tr.F0_FIVE.to_numpy()[:-1]-1,'r1':tr.F1_EIGHT_ASOF.to_numpy()[1:]/tr.F1_EIGHT_ASOF.to_numpy()[:-1]-1})
 dtmp['month']=dtmp.date.dt.to_period('M');monthly=dtmp.groupby('month').agg(n=('actual','size'),rmse0=('actual',lambda x:np.nan),mean_actual=('actual','mean'))
 bymonth=[]
 for mon,x in dtmp.groupby('month'):
  bymonth.append({'month':str(mon),'n_return_intervals':len(x),'mse_F0_bp2':float(1e8*np.mean((x.actual-x.r0)**2)),
   'mse_F1_bp2':float(1e8*np.mean((x.actual-x.r1)**2)),'monthly_mse_improvement_bp2':float(1e8*np.mean((x.actual-x.r0)**2-(x.actual-x.r1)**2))})
 ms=pd.DataFrame(bymonth);ms.to_csv(out/'F1_TRACKING_MONTHLY.csv',index=False)
 percs['F1_tracking_month_avg_improvement_bp2']=float(ms.monthly_mse_improvement_bp2.mean())
 return percs,fit,tr,models,ms


def f2_holdings(D,out):
 dates=D['dates'];nav=D['nav'];p=D['p'];O=D['O'];obs=D['obs'];ix=D['ix'];
 qty=p['primary_units'];assert qty.shape==O.shape
 own_val=np.maximum(qty,0)*np.where(np.isfinite(O),O,0)
 badval=own_val*(~obs)
 direct=own_val[:,ix]/nav[:,None]
 primary_all=own_val.sum(axis=1)/nav
 ok=(dates.year>=2021)&(dates.year<=2024)
 rows=[];groups=[]
 for y in YRS:
  m=ok&(dates.year==y)
  for j,t in enumerate(FAC):
   w=direct[m,j];rows.append({'year':y,'ticker':t,'mean_NAV_weight_pct':100*float(np.mean(w)),
       'days_positive_pct':100*float(np.mean(w>1e-8)),
       'bad_observed_fraction_when_held':float(np.sum((~obs[m][:,ix[j]])&(w>1e-8))/max(1,np.sum(w>1e-8)))})
  groups.append({'year':y,'mean_primary_NAV_pct':100*float(primary_all[m].mean()),
    'mean_eight_direct_NAV_pct':100*float(direct[m].sum(axis=1).mean()),
    'mean_unmapped_primary_NAV_pct':100*float((primary_all[m]-direct[m].sum(axis=1)).mean()),
    'mean_fraction_of_primary_direct_covered_pct':100*float(np.mean(np.divide(direct[m].sum(axis=1),primary_all[m],out=np.zeros(m.sum()),where=primary_all[m]>0))),
    'max_direct_eight_NAV_pct':100*float(np.max(direct[m].sum(axis=1)))})
 out1=pd.DataFrame(rows);out2=pd.DataFrame(groups);out1.to_csv(out/'F2_NAMED_HOLDINGS_BY_YEAR.csv',index=False);out2.to_csv(out/'F2_HOLDINGS_COVERAGE_BY_YEAR.csv',index=False)
 return {'coverage':out2.to_dict('records'),'semis_it_holdings_2024_pct':float(100*np.mean(direct[ok&(dates.year==2024)][:,[FAC.index('VVSM.DE'),FAC.index('QDVE.DE')]].sum(axis=1)))}


def signal_126(D,signal):
 """Decision-only. Fails if future market data are not available -> never read any future outcome columns."""
 dates=D['dates'];pr=D['pr'];bo=D['bo']
 rows=[]
 for j,t in enumerate(FAC):
  allowed=np.flatnonzero(bo[:,j]&(dates<=signal))
  if len(allowed)<127:continue
  i=allowed[-1];prev=allowed[-127]
  if (signal-dates[i]).days>7:continue
  r=math.log(pr[i,j]/pr[prev,j]);rows.append((t,float(r),j,str(dates[i].date()),str(dates[prev].date())))
 return sorted(rows,key=lambda a:(-a[1],a[0]))


def eval_one(D,tickers,date_in,date_out):
 """Observed-only payoff, no effect on signal generation."""
 dates=D['dates'];pr=D['pr'];bo=D['bo'];
 if date_in not in dates or date_out not in dates:return None,'missing_calendar_date'
 i=dates.get_loc(date_in);e=dates.get_loc(date_out)
 jj=[FAC.index(t) for t in tickers]
 if not np.all(bo[[i,e]][:,jj]):return None,'missing_observed_price'
 return dict(zip(tickers,(pr[e,jj]/pr[i,jj]-1).tolist())),'ok'


def state_return(target,rmap,state):
 """Rebalance at entry, fee on turnover incl cash; holdings drift until next entry."""
 w=np.array([target.get(t,0.) for t in FAC]);assert abs(w.sum()-1)<1e-12
 now=np.r_[w,0.]
 prior=np.r_[state,1-state.sum()] if state is not None else np.r_[np.zeros(len(FAC)),1.]
 hto=half_l1(prior,now);fee=.001*hto
 ret=np.array([rmap.get(t,0.) for t in FAC]);g=1+float(w@ret)
 if g<=0:raise AssertionError('negative account')
 net=(1-fee)*g
 drift=w*(1+ret)/g
 return float(net-1),drift,hto,fee


def f3_leaders(D,out):
 cal=D['cal'].copy(); cal=cal[(cal.signal_date>=pd.Timestamp('2021-01-01'))&(cal.signal_date<pd.Timestamp('2027-01-01'))].copy()
 assert len(cal)>=48
 records=[];s0=None;s1=None;v0=100.;v1=100.;month_seq=[];path_valid=True;skipped=0;invalid_dates=[]
 for _,sig in cal.iterrows():
  date=pd.Timestamp(sig.signal_date);rank=signal_126(D,date)
  names=[r[0] for r in rank]
  top=names[:2]
  assert len(top)==2 and len(names)>=5
  ref=names
  # The final OLC32 date 2026-06-30 has entry==exit at 2026-07-01; NOT a zero-return label.
  rmap,reason=(None,'terminal_no_future_label') if pd.Timestamp(sig.exit_date)<=pd.Timestamp(sig.entry_date) else eval_one(D,ref,pd.Timestamp(sig.entry_date),pd.Timestamp(sig.exit_date))
  year=int(date.year)
  row={'market':'EU','signal_date':str(date.date()),'entry_date':str(pd.Timestamp(sig.entry_date).date()),
    'exit_date':str(pd.Timestamp(sig.exit_date).date()),'year':year,'n_asof_factors':len(ref),
    'rank_top1':top[0],'rank_top2':top[1],'rank_table':';'.join(names),
    'ret_top1_trail_126':rank[0][1],'ret_top2_trail_126':rank[1][1],
    'source_date_top1':rank[0][3],'source_date_top2':rank[1][3],
    'past_earliest_obs_top1':rank[0][4], 'payoff_valid':bool(rmap is not None),'invalid_reason':reason}
  if rmap is not None:
   t0={t:.5 for t in top};t1={t:1/len(ref) for t in ref}
   vA,sA,hA,cA=state_return(t0,rmap,s0);vB,sB,hB,cB=state_return(t1,rmap,s1)
   s0=sA;s1=sB
   v0*=1+vA;v1*=1+vB
   future_sorted=sorted(ref,key=lambda t:(-rmap[t],t))
   hit=len(set(top)&set(future_sorted[:2]))
   rank_r={t:ix for ix,t in enumerate(names)}
   future_rank={t:ix for ix,t in enumerate(future_sorted)}
   sp=float(spearmanr([rank_r[t] for t in ref],[future_rank[t] for t in ref]).statistic)
   row.update({'leader_month_net_pct':100*vA,'EW_month_net_pct':100*vB,'log_delta_bp':1e4*(math.log1p(vA)-math.log1p(vB)),
    'leader_hl1':hA,'EW_hl1':hB,'leader_fee':cA,'EW_fee':cB,'future_best':future_sorted[0],
    'future_top2_hit_n':hit,'spearman_prior126_vs_nextmonth':sp,'leader_NAV_proxy':v0 if path_valid else np.nan,
    'EW_NAV_proxy':v1 if path_valid else np.nan,'EXSA_month_price_return_pct':100*rmap.get('EXSA.DE',float('nan')),
    'SXR8_month_price_return_pct':100*rmap.get('SXR8.DE',float('nan'))})
  else:
   skipped+=1;path_valid=False;invalid_dates.append(str(date.date()))
   s0=None;s1=None
   for k in ['leader_month_net_pct','EW_month_net_pct','log_delta_bp','future_top2_hit_n','spearman_prior126_vs_nextmonth','leader_NAV_proxy','EW_NAV_proxy']:row[k]=np.nan
  records.append(row)
 df=pd.DataFrame(records);df.to_csv(out/'F3_SIGNAL_DECISIONS_AND_PAYOFFS.csv',index=False)
 p=df[(df.year<=2024)].copy();assert len(p)==48
 good=p[p.payoff_valid].copy();d=good.log_delta_bp.to_numpy()
 monthly={'signals_main':len(p),'complete_common_payoff_main':len(good),'incomplete_main':list(p[~p.payoff_valid].signal_date),
   'mean_top2_minus_ew_net_bp_per_month':float(d.mean()) if len(d) else None,
   'total_top2_hit_n':int(good.future_top2_hit_n.sum()),'total_available_2slots':int(2*len(good)),
   'mean_spearman':float(good.spearman_prior126_vs_nextmonth.mean()),'n_missing_total':skipped,
   'linked_monthly_NAV_valid':bool(p.payoff_valid.all())}
 if len(good)==48:
  boot=monthly_boot_ci(d,p.signal_date,4000)
  b=pd.DataFrame({'draw':np.arange(4000),'mean_delta_bp':boot});b.to_csv(out/'F3_BOOTSTRAP_BLOCK6.csv',index=False)
  ci=np.quantile(boot,[.025,.975]);monthly['paired_6month_bootstrap_95pct_mean_bp']=[float(ci[0]),float(ci[1])]
  monthly['main_gate']='PASS_EXPLORATORY_ONLY' if (d.mean()>0 and ci[0]>0) else 'FAIL';
  monthly['leader_proxy_metrics']=month_metrics(np.r_[100,p.leader_NAV_proxy.to_numpy()]) if np.isfinite(p.leader_NAV_proxy).all() else None
  monthly['EW_proxy_metrics']=month_metrics(np.r_[100,p.EW_NAV_proxy.to_numpy()]) if np.isfinite(p.EW_NAV_proxy).all() else None
 else:
  monthly['main_gate']='NOT_EVALUABLE_ALL_MONTHS'
  (out/'F3_BOOTSTRAP_BLOCK6.csv').write_text('draw,mean_delta_bp\n')
 # Ex-post yearly paired performance, not choice of rule.
 year=[]
 for y,g in p.groupby('year'):
  val=g[g.payoff_valid];year.append({'year':int(y),'n_total':len(g),'n_valid':len(val),
    'mean_log_delta_bp':float(val.log_delta_bp.mean()),'top2_future_top2_hits':int(val.future_top2_hit_n.sum()),
    'hit_fraction':float(val.future_top2_hit_n.sum()/max(1,2*len(val))),'mean_rank_spearman':float(val.spearman_prior126_vs_nextmonth.mean())})
 pd.DataFrame(year).to_csv(out/'F3_BY_YEAR.csv',index=False)
 return monthly,df


def figures(out):
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 df=pd.read_csv(out/'F1_CLONE_MATCHED_DAILY.csv')
 fig,ax=plt.subplots(figsize=(10,5.5));x=pd.to_datetime(df.date)
 for c,l in [('strategy','OLC19 EU autentico'),('F0_FIVE','Clone 5 proxy'),('F1_EIGHT_ASOF','Clone ampliato 7/8 proxy')]:ax.plot(x,df[c],label=l)
 ax.set_title('OLC38 — curve diagnostiche EU 2021–2024 (non factor-neutral alpha)');ax.set_ylabel('Indice = 100');ax.grid(alpha=.25);ax.legend();fig.autofmt_xdate();fig.tight_layout();fig.savefig(out/'OLC38_CLONE_CURVES.png',dpi=140);plt.close(fig)
 h=pd.read_csv(out/'F2_NAMED_HOLDINGS_BY_YEAR.csv');sel=['VVSM.DE','QDVE.DE','EXV5.DE','EXV9.DE','EXX1.DE'];p=h[h.ticker.isin(sel)].pivot(index='year',columns='ticker',values='mean_NAV_weight_pct').reindex(columns=sel).fillna(0)
 fig,ax=plt.subplots(figsize=(10,5.5));p.plot.bar(stacked=True,ax=ax);ax.set_title('OLC38 — pesi NAV reali, ETF nominati (solo posizioni primary)');ax.set_ylabel('Quota % media NAV');ax.legend(loc='upper left',ncol=3,fontsize=8);ax.grid(axis='y',alpha=.25);fig.tight_layout();fig.savefig(out/'OLC38_NAMED_HOLDINGS.png',dpi=140);plt.close(fig)
 f=pd.read_csv(out/'F3_SIGNAL_DECISIONS_AND_PAYOFFS.csv');f=f[(f.year<=2024)&f.payoff_valid]
 fig,ax=plt.subplots(figsize=(10,4.5));ax.bar(pd.to_datetime(f.signal_date),f.log_delta_bp,width=18)
 ax.axhline(0,ls='--',lw=.8);ax.set_title('OLC38 — leader 126d Top2 meno equiponderato, bp netti/mese');ax.set_ylabel('Differenza di rendimento log, bp');fig.autofmt_xdate();fig.tight_layout();fig.savefig(out/'OLC38_FACTOR_LEADERS_MONTHS.png',dpi=140);plt.close(fig)


def main():
 pa=argparse.ArgumentParser();pa.add_argument('--olc19',type=Path);pa.add_argument('--olc32',type=Path);pa.add_argument('--compact-source',type=Path);pa.add_argument('--out',type=Path,required=True);a=pa.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 if a.compact_source:
  assert a.olc19 is None and a.olc32 is None
  D=prepare(a.compact_source,a.compact_source)
 else:
  assert a.olc19 and a.olc32
  D=prepare(a.olc19,a.olc32)
 audit_data=audit(D,a.out);styles,weights,clones,models,months=f1_clones(D,a.out);holdings=f2_holdings(D,a.out);leaders,dec=f3_leaders(D,a.out)
 figures(a.out)
 obj={'source_sha':{'OLC19':D['h19'],'OLC32':D['h32']},'protocol_github_commit':'3a335ab57bd38543a41c826806b7632cd4ec010b','compact_source_sha':D['compact_source_sha'],
  'data_audit':audit_data,'F1_styles':styles,'F2_holdings':holdings,'F3_leadership':leaders,
  'production_changed':False,'USA_changed':False,'evidence_posture':'EXPLORATORY_NOT_PIT_TR_CERTIFIED','GateA':'FAIL','candidate_promoted':False}
 (a.out/'OLC38_RESULTS.json').write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=str))
 for k,v in obj.items():
  if k in ('F1_styles','F2_holdings','F3_leadership','data_audit'):print(k,json.dumps(v,ensure_ascii=False)[:9000])

if __name__=='__main__':main()
