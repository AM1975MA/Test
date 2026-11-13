#!/usr/bin/env python3
"""OLC103: frozen OLC102 true daily-ML rank persistence as pure confidence/risk signal.
Do not use as a recommendation or evidence of virgin OOS alpha.
"""
from __future__ import annotations
import os
for v in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[v]='1'
import sys,json, math, warnings, hashlib, time
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.preprocessing import StandardScaler
ROOT=Path('/mnt/data/olc103');OUT=ROOT/'results';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,'/mnt/data/olc102')
import sim_backend as b
SEED=103613
REG_FEATURES=['score_margin_2_3','mean_top2_score','past_mom21','past_vol63','early_pair_close_return','gross_V6_at_open']
PRED_FEATURES=REG_FEATURES+['retention']
POLICIES=('BASE','ALL75','ALL50','UNSTABLE75','UNSTABLE50','STABLE75')
WEIGHTS=('HALF','MINVAR63')
COSTS=((.001,.001),(.003,.005))

def safe_log(a,b):
 return float(np.log(a/b)) if np.isfinite(a) and np.isfinite(b) and a>0 and b>0 else np.nan

def build_panel(m,q,dec):
 ml=pd.read_pickle(f'/mnt/data/olc102/results/{m}_DAILY_CONTEXTUAL_RANK.pkl')
 events=np.flatnonzero(q['events']); assert len(events)==len(dec)==90
 mp={str(t):i for i,t in enumerate(q['tickers'])}
 by={int(j):g for j,g in ml.groupby('event_j')}; rows=[];details=[]
 for j in range(len(events)-1):
  k=int(events[j]);nxt=int(events[j+1]);entry=k+2
  assert entry<nxt,(m,j,k,entry,nxt)
  g=by[j];gs={int(s):r for s,r in g.groupby('asof_step')}
  assert set(gs)=={0,1,2},(m,j,set(gs))
  keys=[(t,s) for s in (0,1,2) for t in (str(dec.ticker1.iloc[j]),str(dec.ticker2.iloc[j]))]
  groups={s:r.sort_values(['updated_score','ticker'],ascending=[False,True],kind='mergesort') for s,r in gs.items()}
  sets=[set(gr.ticker.iloc[:2].astype(str)) for gr in groups.values()]
  native=[str(dec.ticker1.iloc[j]),str(dec.ticker2.iloc[j])]
  assert groups[0].ticker.iloc[:2].tolist()==native,(m,j,native,groups[0].ticker.iloc[:2].tolist())
  persist1=len(sets[0]&sets[1]);persist2=len(sets[0]&sets[2]);retention=(persist1+persist2)/4
  stable=int(persist1==2 and persist2==2)
  origin=groups[0].set_index('ticker');final=groups[2].set_index('ticker')
  ix=np.array([mp[x] for x in native]);c=q['C'];o=q['O'];l=q['L']
  mom_values=[safe_log(c[k-1,i],c[k-22,i]) if k>=22 else np.nan for i in ix]
  past_mom=float(np.nanmean(mom_values)) if np.isfinite(mom_values).any() else np.nan
  vols=[]
  for i in ix:
   seq=c[max(0,k-64):k,i]
   lg=np.diff(np.log(seq)) if len(seq)>2 and np.all(np.isfinite(seq)) and np.min(seq)>0 else np.array([])
   vols.append(np.std(lg,ddof=1)*np.sqrt(252) if len(lg)>=45 else np.nan)
  past_vol=float(np.nanmean(vols)) if np.isfinite(vols).any() else np.nan
  early_values=[safe_log(c[k+1,i],c[k-1,i]) if k>0 else np.nan for i in ix]
  early=float(np.nanmean(early_values)) if np.isfinite(early_values).any() else np.nan
  fr=np.array([safe_log(o[nxt,i],o[entry,i]) for i in ix]);
  out=np.nanmean(fr)
  assert np.all(np.isfinite(fr)),(m,j,native,fr)
  elig=groups[0].ticker.astype(str).tolist();eligible_indices=np.array([mp[x] for x in elig]);
  p0=o[entry,eligible_indices];p1=o[nxt,eligible_indices]
  val=np.isfinite(p0)&np.isfinite(p1)&(p0>0)&(p1>0)
  if 'observed' in q:val &= q['observed'][entry,eligible_indices]&q['observed'][nxt,eligible_indices]
  med=float(np.median(np.log(p1[val]/p0[val])))
  quality_ok=bool(val.sum()>=len(eligible_indices)*.65)
  assert val.sum()>=5,(m,j,val.sum())
  sel_obs=bool(np.all(q['observed'][entry,ix]&q['observed'][nxt,ix])) if 'observed' in q else True
  quality_ok = bool(quality_ok and sel_obs)
  last2_open=f'{pd.Timestamp(q["dates"][entry]).date()}'
  eventpair=groups[0].iloc[:2]
  scores=groups[0].updated_score.to_numpy(float)
  scoremargin=float(scores[1]-scores[2]);meanscore=float(scores[:2].mean())
  future_loss=int(out<np.log(.95))
  # Frozen original quote mask absent USA; flag but don't fabricate observed flags
  recorded={'market':m,'j':j,'signal_date':str(pd.Timestamp(dec.signal_date.iloc[j]).date()),
    'entry_day2_open':last2_open,'next_event_open':str(pd.Timestamp(q['dates'][nxt]).date()),
    'ticker1':native[0],'ticker2':native[1],
    'persist_day1':persist1,'persist_day2':persist2,'retention':retention,'full_stable':stable,
    'top1_rank_shift_2':float(final.updated_percentile.loc[native[0]]-origin.updated_percentile.loc[native[0]]),
    'top2_rank_shift_2':float(final.updated_percentile.loc[native[1]]-origin.updated_percentile.loc[native[1]]),
    'score_margin_2_3':scoremargin,'mean_top2_score':meanscore,'past_mom21':past_mom,'past_vol63':past_vol,
    'early_pair_close_return':early,'gross_V6_at_open':float(q['gross'][entry]),
    'future_log_raw':float(out),'future_log_excess':float(out-med),'future_log_universe_median':med,
    'bad_loss_5pct':future_loss,'n_valid_eligibles_for_median':int(val.sum()),'quote_quality_ok':quality_ok,
    'top2_observed_start': bool(np.all(q['observed'][entry,ix])) if 'observed' in q else None,
    'top2_observed_exit': bool(np.all(q['observed'][nxt,ix])) if 'observed' in q else None,
    'max_intramonth_loss_rel_open':float(np.min(l[entry:nxt,ix]/o[entry,ix])-1)}
  rows.append(recorded)
  details.extend({'market':m,'j':j,'step':step,'asof':str(pd.Timestamp(gs[step].asof_date.iloc[0]).date()),
                  'ticker1':str(groups[step].ticker.iloc[0]),'ticker2':str(groups[step].ticker.iloc[1]),
                  'kept_top2':int(len(sets[step]&sets[0]))} for step in [0,1,2])
 data=pd.DataFrame(rows);assert len(data)==89
 return data,pd.DataFrame(details)

def transform_fit(train,test,cols):
 xt=train[cols].to_numpy(float);xs=test[cols].to_numpy(float)
 med=np.array([np.median(xt[np.isfinite(xt[:,i]),i]) if np.isfinite(xt[:,i]).any() else 0. for i in range(xt.shape[1])])
 xt=np.where(np.isfinite(xt),xt,med);xs=np.where(np.isfinite(xs),xs,med)
 sc=StandardScaler().fit(xt)
 return sc.transform(xt),sc.transform(xs)

def predict_forward(m,df):
 pred=[]
 for j in range(25,len(df)):
  tr=df.iloc[:j-1].query('quote_quality_ok == True');te=df.iloc[[j]]  # events <= j-2 already mature
  if len(tr)<24 or not bool(te.quote_quality_ok.iloc[0]):continue
  assert tr.j.max()<=j-2 and len(tr)>=24
  yy=tr.future_log_excess.to_numpy(float).clip(-.25,.25)
  bad=tr.bad_loss_5pct.to_numpy(int)
  row={'market':m,'j':j,'signal_date':te.signal_date.iloc[0],
        'retention':float(te.retention.iloc[0]),'future_log_excess':float(te.future_log_excess.iloc[0]),
        'future_log_raw':float(te.future_log_raw.iloc[0]),'bad_loss_5pct':int(te.bad_loss_5pct.iloc[0]),
        'n_train':len(tr)}
  for lab,cols in [('BASE',REG_FEATURES),('STABILITY',PRED_FEATURES)]:
   x,z=transform_fit(tr,te,cols)
   reg=Ridge(alpha=10).fit(x,yy)
   row[f'{lab}_excess_pred']=float(reg.predict(z)[0])
   if bad.min()==bad.max():p=float(bad.mean())
   else:p=float(LogisticRegression(C=.5,solver='lbfgs',max_iter=300,random_state=SEED).fit(x,bad).predict_proba(z)[0,1])
   row[f'{lab}_bad_prob']=p
  for lab in ['BASE','STABILITY']:
   row[f'{lab}_sq_error']=(row[f'{lab}_excess_pred']-row['future_log_excess'])**2
   row[f'{lab}_brier']=(row[f'{lab}_bad_prob']-row['bad_loss_5pct'])**2
  pred.append(row)
 return pd.DataFrame(pred)

def blockci(arr,seed=SEED,n_boot=3000,length=6):
 arr=np.asarray(arr,float);assert len(arr)>20 and np.isfinite(arr).all()
 rng=np.random.default_rng(seed);n=len(arr);nblocks=int(np.ceil(n/length));ix=np.arange(length)
 out=np.empty(n_boot,float)
 for i in range(n_boot):
  bs=rng.integers(0,n,size=nblocks);z=(bs[:,None]+ix[None,:])%n
  out[i]=arr[z.ravel()[:n]].mean()
 return dict(mean=float(arr.mean()),lower=float(np.quantile(out,.025)),upper=float(np.quantile(out,.975)),bootstrap_draws=n_boot,block_months=length)

def grouped_effect(df,metric,seed):
 df=df[df.quote_quality_ok].copy()
 y=df[metric].to_numpy(float);s=df.full_stable.to_numpy(int)
 mean1=float(y[s==1].mean());mean0=float(y[s==0].mean())
 rng=np.random.default_rng(seed);n=len(df);boots=[];l=6;inds=np.arange(l)
 for k in range(3000):
  ix=((rng.integers(0,n,size=int(np.ceil(n/l)))[:,None]+inds)%n).ravel()[:n];ys=y[ix];ss=s[ix]
  if (ss==0).any() and (ss==1).any():boots.append(float(ys[ss==1].mean()-ys[ss==0].mean()))
 return dict(stable_mean=mean1,unstable_mean=mean0,difference=mean1-mean0,ci95=list(np.quantile(boots,[.025,.975]).astype(float)),n_stable=int(sum(s)),n_unstable=int(sum(1-s)))

def make_policy(q,events,pairs,stability,alloc,policy):
 z,_=b.staged(q,events,pairs,'fixed',2,alloc)
 changed=0;bars=0
 for j,k in enumerate(events[:-1]):
  k=int(k);nxt=int(events[j+1]);start=k+2
  s=int(stability[j]);
  if policy=='BASE':cap=None
  elif policy=='ALL75':cap=.75
  elif policy=='ALL50':cap=.50
  elif policy=='UNSTABLE75':cap=.75 if not s else None
  elif policy=='UNSTABLE50':cap=.50 if not s else None
  elif policy=='STABLE75':cap=.75 if s else None
  else:raise ValueError(policy)
  if cap is not None:
   old=z['g'][start:nxt].copy();z['g'][start:nxt]=np.minimum(old,cap)
   changed+=int(np.any(z['g'][start:nxt]!=old));bars+=int(np.sum(z['g'][start:nxt]!=old))
 return z,changed,bars

def run_native(m,q,dec,df,qu):
 events=np.flatnonzero(q['events']);pairs=[(str(t1),str(t2)) for t1,t2 in zip(dec.ticker1,dec.ticker2)]
 # Preserve baseline native accounting and V6 construction parity
 orig=b.simulate(q,.001,.001)
 for f in b.F:assert np.array_equal(orig[f],b.orig_ref(m)[f]),(m,f,'original parity')
 assert np.array_equal(b.v6_alt(m,q,qu),q['alt']),(m,'v6 parity')
 observed=pd.read_csv('/mnt/data/olc102/results/OLC102_SCORECARD.csv')
 summaries=[];daily=[];paired=[];run_qa=[];base_log_by_alloc={}
 for alloc in WEIGHTS:
  for policy in POLICIES:
   z,changed,bars=make_policy(q,events,pairs,df.full_stable.to_numpy(int),alloc,policy)
   z['alt'][:]=b.v6_alt(m,z,qu)
   for fee,friction in COSTS:
    r=b.simulate(z,fee,friction,'IMMEDIATE');ms={x['period']:x for x in b.metrics(q,r)}
    full=ms['FULL'];main=ms['ACTIVE2021_2024'];arm=f'FIXED_DAY2_{alloc}'
    if policy=='BASE' and (fee,friction)==(.001,.001):
     prior=observed[(observed.market==m)&(observed.arm==arm)&(observed.fee==fee)]
     assert len(prior)==1,(m,arm)
     cagr=float(prior.CAGR_FULL.iloc[0]);dd=float(prior.MaxDD_FULL.iloc[0]);assert abs(cagr-full['cagr'])<1e-12,(m,arm,cagr,full['cagr']);assert abs(dd-full['maxdd'])<1e-12,(m,arm,'dd mismatch')
    end_nav=r['nav'];dt=pd.DatetimeIndex(q['dates']);nlr=np.diff(np.log(np.r_[1.,end_nav]))[:-1]
    mlogs=[]
    for j in range(89):
     k=int(events[j]);nxt=int(events[j+1]);mlogs.append(float(np.log(end_nav[nxt]/end_nav[k])))
    key=(alloc,fee,friction)
    if policy=='BASE':base_log_by_alloc[key]=np.array(mlogs)
    c=dict(market=m,allocation=alloc,policy=policy,fee=fee,friction=friction,native_CAGR_FULL=float(full['cagr']),native_MaxDD_FULL=float(full['maxdd']),CAGR_MAIN=float(main['cagr']),MaxDD_MAIN=float(main['maxdd']),nav_final=float(end_nav[-1]),n_stops=int(np.sum(r['ledger'][:,8])),turnover=float(np.sum(r['ledger'][:,4])),avg_effective_g_budget=float(np.mean(z['g'][2:-1])),n_capped_months=int(changed),n_capped_bars=int(bars))
    summaries.append(c)
    paired.extend([dict(market=m,allocation=alloc,policy=policy,fee=fee,friction=friction,j=j,signal_date=str(df.signal_date.iloc[j]),monthly_log_return=float(v)) for j,v in enumerate(mlogs)])
    daily.extend([dict(market=m,allocation=alloc,policy=policy,fee=fee,friction=friction,date=str(pd.Timestamp(d).date()),nav=float(n),day_logr=float(v)) for d,n,v in zip(q['dates'][1:],end_nav[:-1],nlr)])
   if policy in ['BASE','UNSTABLE75','UNSTABLE50','ALL75','STABLE75']:
    s=summaries[-2]
    print('NATIVE',m,alloc,policy,round(100*s['native_CAGR_FULL'],3),round(100*s['native_MaxDD_FULL'],3),flush=True)
 return pd.DataFrame(summaries),pd.DataFrame(daily),pd.DataFrame(paired)

def main():
 ts=time.time();pdata={};data={m:b.source(m) for m in ['EU','USA']};qu=data['USA'][0]
 print('FROZEN_PROTOCOL_SHA256',hashlib.sha256((ROOT/'PROTOCOL_PRE_RESULTS.md').read_bytes()).hexdigest(),flush=True)
 det=[];preds=[];market_coh=[];outcome=[]
 for m,(q,dec,score) in data.items():
  panel,details=build_panel(m,q,dec);pdata[m]=panel;panel.to_csv(OUT/f'{m}_EVENT_STABILITY.csv',index=False)
  details.to_csv(OUT/f'{m}_STEP_TOP2.csv',index=False)
  p=predict_forward(m,panel);preds.append(p)
  cohorts={metric:grouped_effect(panel,metric,SEED) for metric in ['future_log_raw','future_log_excess','bad_loss_5pct','max_intramonth_loss_rel_open']}
  good=panel[panel.quote_quality_ok].copy()
  ic={metric:float(spearmanr(good.retention,good[metric]).statistic) for metric in ['future_log_raw','future_log_excess','bad_loss_5pct','max_intramonth_loss_rel_open']}
  increments={metric:blockci((p[f'BASE_{metric}']-p[f'STABILITY_{metric}']).to_numpy(float),SEED) for metric in ['sq_error','brier']}
  predictors={k:float(p[k].mean()) for k in ['BASE_sq_error','STABILITY_sq_error','BASE_brier','STABILITY_brier']}
  outcome.append(dict(market=m,n=89,n_quality_valid=int(panel.quote_quality_ok.sum()),excluded_quote_events=panel.loc[~panel.quote_quality_ok,'signal_date'].tolist(),stable=int(good.full_stable.sum()),unstable=int((1-good.full_stable).sum()),retention_mean=float(good.retention.mean()),corr=ic,cohorts=cohorts,prequential={'n':len(p),'metrics':predictors,'incremental_improvement':increments,'baseline_features':REG_FEATURES,'added':'retention'}))
  print('PRED',m,'stable',int(panel.full_stable.sum()),'bad',panel.bad_loss_5pct.mean(),'mse_delta',increments['sq_error']['mean'],'brier_delta',increments['brier']['mean'],flush=True)
 pd.concat(preds,ignore_index=True).to_csv(OUT/'OLC103_PREQUENTIAL_PREDICTIONS.csv',index=False)
 snaps=[];ds=[];month=[]
 for m,(q,dec,score) in data.items():
  s,d,mo=run_native(m,q,dec,pdata[m],qu);snaps.append(s);ds.append(d);month.append(mo)
 summary=pd.concat(snaps);monthly=pd.concat(month);summary.to_csv(OUT/'OLC103_NATIVE_SCORECARD.csv',index=False);monthly.to_csv(OUT/'OLC103_NATIVE_MONTHLY.csv',index=False);pd.concat(ds).to_csv(OUT/'OLC103_NATIVE_DAILY.csv.gz',index=False,compression='gzip')
 risk=[]
 for (m,alloc,fee,friction),group in monthly.groupby(['market','allocation','fee','friction']):
  x=group.pivot(index='j',columns='policy',values='monthly_log_return')
  baseline=x['BASE'].to_numpy(float)
  for policy in POLICIES:
   if policy=='BASE':continue
   delta=x[policy].to_numpy(float)-baseline
   boot=blockci(12*delta,SEED)
   risk.append(dict(market=m,allocation=alloc,fee=fee,friction=friction,policy=policy,delta_annual_log=float(boot['mean']),ci_low=float(boot['lower']),ci_high=float(boot['upper']),n=len(delta)))
 risk=pd.DataFrame(risk);risk.to_csv(OUT/'OLC103_PAIRED_CI.csv',index=False)
 report={'status':'HISTORICAL_CAUSAL_TEST_COMPLETED_NO_PROSPECTIVE_VALIDATION','n_events_per_market':89,'n_prequential_per_market':'effective per market in outcomes','num_native_paths':len(summary),'source':'OLC102 genuine daily ML contextual rankings frozen at monthly S0 and recalculated after S1/S2','no_ETF_selection_changes':True,'start_signal':'2019-01-31','end_signal':'2026-05-29','all_policy_entry':'k+2 third opening','cost_scenarios':COSTS,'outcomes':outcome,'run_time_s':time.time()-ts}
 (OUT/'OLC103_DIAGNOSTIC_QA.json').write_text(json.dumps(report,indent=2,default=str))
 print('DONE',len(summary),'native paths',round(time.time()-ts,2),'s',flush=True)
if __name__=='__main__':main()
