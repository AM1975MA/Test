"""Independent path arithmetic, exact factor decomposition and paired uncertainty."""
from pathlib import Path
import itertools,math,json,hashlib,os
import numpy as np,pandas as pd
from reconcile_math import log_returns,shapley,mobius
B=Path(os.environ.get('RECONCILIATION_ROOT','/mnt/data/reconciliation'));O=B/'results';NAMES=['CONCENTRATION','DD_GROSS','V6','SYSTEMIC_GAP','STOPS','COSTS']

def metric(nav):
 lr=log_returns(nav);pk=np.maximum.accumulate(np.r_[1.,nav])[1:]
 return dict(cagr=float(np.expm1(lr.mean()*252)),ann_log=float(lr.mean()*252),maxdd=float((nav/pk-1).min()),terminal_equity=float(nav[-1]))

def bootstrap(x,labels,family,block=21,reps=10000,seed=20261031):
 x=np.asarray(x);n,p=x.shape;rng=np.random.default_rng(seed)
 full,rem=divmod(n,block);ext=np.r_[x,x[:block]];cs=np.vstack([np.zeros(p),ext.cumsum(0)])
 sums=cs[np.arange(n)+block]-cs[np.arange(n)]
 tail=(cs[np.arange(n)+rem]-cs[np.arange(n)]) if rem else None
 draws=np.zeros((reps,p))
 for start in range(0,reps,250):
  cnt=min(250,reps-start);idx=rng.integers(0,n,size=(cnt,full))
  z=sums[idx].sum(1)
  if rem:z+=tail[rng.integers(0,n,size=cnt)]
  draws[start:start+cnt]=z/n*25200
 point=x.mean(0)*25200;sd=draws.std(0,ddof=1);active=sd>1e-12
 max_t=np.max(np.abs((draws[:,active]-point[active])/sd[active]),axis=1) if active.any() else np.zeros(reps)
 critical=float(np.quantile(max_t,.95));rows=[]
 for j,label in enumerate(labels):
  lo,hi=np.quantile(draws[:,j],[.025,.975])
  rows.append(dict(family=family,component=label,block_sessions=block,n_sessions=n,replicates=reps,seed=seed,annual_log_pp=point[j],ci95_low=lo,ci95_high=hi,simultaneous95_low=point[j]-critical*sd[j],simultaneous95_high=point[j]+critical*sd[j],family_components=p))
 return rows

arch={};checks=[]
for family in ['factorial','mediation']:
 data={}
 for p in sorted((B/family).glob('*/*/FULL_UNIVERSE_PATH.npz')):
  arm=p.parent.parent.name;v=int(p.parent.name[1:]);z=np.load(p,allow_pickle=False)
  ds=pd.DatetimeIndex(z['dates']);nav=z['equity'][0]
  assert len(ds)==2366 and ds.is_monotonic_increasing and ds.is_unique
  if 'dates' in arch:assert np.array_equal(arch['dates'].values,ds.values)
  arch['dates']=ds;data[(arm,v)]={k:z[k] for k in z.files};m=metric(nav)
  ref=json.loads((p.parent/'RESULT.json').read_text())['v2_full_universe']
  err={k:abs(m[k]-ref[k]) for k in ['cagr','maxdd','terminal_equity']}
  assert max(err.values())<1e-12,(family,arm,v,err)
  checks.append(dict(family=family,arm=arm,vintage=v,**m,**{k+'_error':v for k,v in err.items()}))
 arch[family]=data
for v in (1,2,3):
 for key in arch['factorial'][('R_T0_H1',v)]:
  x=arch['factorial'][('R_T0_H1',v)][key];y=arch['mediation'][('R_R',v)][key]
  if x.dtype.kind=='f':assert np.max(np.abs(x-y))<1e-12
  else:assert np.array_equal(x,y)
pd.DataFrame(checks).to_csv(O/'ARCHIVED_51_PATHS_RECONCILIATION.csv',index=False)
dates=arch['dates'];D=len(dates)
sc=np.zeros((3,8,D));score_rows=[]
for v in (1,2,3):
 for mask in range(8):
  R,T,H=[bool(mask&(1<<i)) for i in range(3)];arm=f'{"R" if R else "B"}_T{int(T)}_H{int(H)}'
  nav=arch['factorial'][(arm,v)]['equity'][0];sc[v-1,mask]=log_returns(nav)
  score_rows.append(dict(vintage=v,mask=mask,arm=arm,**metric(nav)))
pd.DataFrame(score_rows).to_csv(O/'SCORE_FACTORIAL_RECOMPUTED.csv',index=False)
score_phi=np.stack([shapley(sc[v]) for v in range(3)])
score_inter=np.stack([mobius(sc[v]) for v in range(3)])
rows=[]
for s in range(1,8):
 label=' x '.join(n for j,n in enumerate(['RETURN_RANK_REPLACEMENT','TITANIUM_TAIL','HYBRID_PACKAGE']) if s&(1<<j))
 rows+=bootstrap(score_inter[:,s].mean(0)[:,None],[label],'score_interaction',21)
pd.DataFrame(rows).to_csv(O/'SCORE_INTERACTIONS.csv',index=False)
ci=[];summary=[]
contexts={
 'BASE_tail_packages':(sc[:,[0,2,4,6]],['TITANIUM_TAIL','HYBRID_PACKAGE']),
 'RETURN_tail_packages':(sc[:,[1,3,5,7]],['TITANIUM_TAIL','HYBRID_PACKAGE']),
 'BASE_full_to_RETURN_without_ridge':(sc[:,[6,7,4,5]],['RETURN_RANK_REPLACEMENT','REMOVE_TITANIUM_TAIL']),
 'FULL_three_score_changes':(sc,['RETURN_RANK_REPLACEMENT','TITANIUM_TAIL','HYBRID_PACKAGE'])}
med=np.stack([[log_returns(arch['mediation'][(arm,v)]['equity'][0]) for arm in ['H_H','R_H','H_R','R_R']] for v in (1,2,3)])
contexts['TAIL_only_to_RETURN_Hybrid']=(med,['SELECTION','WEIGHT_AND_MARGIN'])
for family,(values,labels) in contexts.items():
 phi=np.stack([shapley(v) for v in values]);mean=phi.mean(0).T
 for block in (21,63):ci+=bootstrap(mean,labels,family,block)
 base=values[:,0].sum(1)*252/D;end=values[:,-1].sum(1)*252/D
 summary.append(dict(family=family,base_ann_log_pp=float(base.mean()*100),end_ann_log_pp=float(end.mean()*100),total_delta_ann_log_pp=float((end-base).mean()*100),base_equivalent_cagr=float(np.expm1(base.mean())),end_equivalent_cagr=float(np.expm1(end.mean())),efficiency_error=float(np.max(np.abs(phi.sum(1)-(values[:,-1]-values[:,0]))))))
 if family=='TAIL_only_to_RETURN_Hybrid':
  perdate=pd.DataFrame(mean,index=dates,columns=labels);perdate['TOTAL']=values[:,-1].mean(0)-values[:,0].mean(0)
  perdate.to_csv(O/'MEDIATION_DAILY_LOG.csv',index_label='decision_date')
  inter=(values[:,3]-values[:,2]-values[:,1]+values[:,0]).mean(0)
  ci+=bootstrap(inter[:,None],['SELECTION_x_WEIGHT'],'mediation_interaction',21)
policy=pd.read_csv(O/'POLICY_FACTORIAL.csv');allphi={};yearrows=[];conditional=[];ddrows=[];events=[];fullpaths={}
for arm in ['B_T1_H1','R_T0_H1']:
 vals=np.empty((3,64,D));dds=np.empty((3,64))
 for v in (1,2,3):
  for mask in range(64):
   z=np.load(O/'policy_paths'/arm/f'r{v}'/f'{mask:02d}.npz',allow_pickle=False)
   assert np.array_equal(z['dates'],dates.values)
   vals[v-1,mask]=log_returns(z['nav']);dds[v-1,mask]=metric(z['nav'])['maxdd']
   if mask==63:fullpaths[(arm,v)]={k:z[k] for k in z.files}
 phi=np.stack([shapley(val) for val in vals]);allphi[arm]=phi
 mean=phi.mean(0).T
 for block in (21,63):ci+=bootstrap(mean,NAMES,'policy_'+arm,block)
 for j,name in enumerate(NAMES):
  contrast=(vals[:,63]-vals[:,63^(1<<j)]).mean(0)
  cr=bootstrap(contrast[:,None],[name],'leave_one_out_'+arm,21)[0]
  paired=policy[(policy.arm==arm)&policy['mask'].isin([63,63^(1<<j)])].pivot(index='vintage',columns='mask',values='cagr')
  cr['mean_delta_cagr_pp']=float((paired[63]-paired[63^(1<<j)]).mean()*100)
  paired_dd=policy[(policy.arm==arm)&policy['mask'].isin([63,63^(1<<j)])].pivot(index='vintage',columns='mask',values='maxdd')
  cr['mean_dd_improvement_pp']=float((paired_dd[63]-paired_dd[63^(1<<j)]).mean()*100)
  conditional.append(cr)
 ddphi=np.stack([shapley(dd[:,None])[:,0] for dd in dds])
 for j,n in enumerate(NAMES):ddrows.append(dict(arm=arm,component=n,shapley_maxdd_improvement_pp=float(ddphi[:,j].mean()*100)))
 for year in sorted(set(dates.year)):
  idx=dates.year==year
  for j,n in enumerate(NAMES):yearrows.append(dict(arm=arm,year=year,component=n,period_log_contribution_pp=float(mean[idx,j].sum()*100),contribution_to_fullsample_ann_log_pp=float(mean[idx,j].sum()*25200/D)))
 base=vals[:,0].sum(1)*252/D;end=vals[:,-1].sum(1)*252/D
 summary.append(dict(family='policy_'+arm,base_ann_log_pp=float(base.mean()*100),end_ann_log_pp=float(end.mean()*100),total_delta_ann_log_pp=float((end-base).mean()*100),base_equivalent_cagr=float(np.expm1(base.mean())),end_equivalent_cagr=float(np.expm1(end.mean())),efficiency_error=float(np.max(np.abs(phi.sum(1)-(vals[:,-1]-vals[:,0]))))))
 pd.DataFrame(mean,index=dates,columns=NAMES).to_csv(O/f'POLICY_DAILY_SHAPLEY_{arm}.csv',index_label='decision_date')
contr=(sc[:,5]-sc[:,6]).mean(0)
ci+=bootstrap(contr[:,None],['RETURN_no_RIDGE_minus_BASE_full'],'final_strategy_contrast',21)
ci+=bootstrap(contr[:,None],['RETURN_no_RIDGE_minus_BASE_full'],'final_strategy_contrast',63)
ctr=pd.DataFrame({'date':dates,'log_diff':contr})
month=ctr.groupby(ctr.date.dt.to_period('M')).log_diff.sum().reset_index();month['calendar_month']=month['date'].astype(str);month['log_difference_pp']=month.log_diff*100;month['contribution_to_total_ann_log_pp']=month.log_diff*25200/D
month[['calendar_month','log_difference_pp','contribution_to_total_ann_log_pp']].to_csv(O/'FINAL_CONTRAST_MONTHLY.csv',index=False)
cy=[]
for yr in sorted(set(dates.year)):
 mask=dates.year==yr
 cy.append(dict(year=yr,n_decision_dates=int(mask.sum()),base_log_return_pp=float(sc[:,6,mask].sum(1).mean()*100),challenger_log_return_pp=float(sc[:,5,mask].sum(1).mean()*100),difference_log_pp=float(contr[mask].sum()*100),contribution_to_total_ann_log_pp=float(contr[mask].sum()*25200/D)))
pd.DataFrame(cy).to_csv(O/'FINAL_CONTRAST_YEARLY.csv',index=False)
for v in (1,2,3):
 base=fullpaths[('B_T1_H1',v)];new=fullpaths[('R_T0_H1',v)];lb=base['ledger'];ln=new['ledger']
 tickers=json.loads((O/'policy_paths/B_T1_H1'/f'r{v}'/'TICKERS.json').read_text())
 def tk(i):return tickers[int(i)] if int(i)>=0 else 'NONE'
 for i,d in enumerate(dates[:-1]):
  events.append(dict(vintage=v,decision_date=str(d.date()),valuation_date=str(dates[i+1].date()),base_top1=tk(lb[i,19]),base_top2=tk(lb[i,20]),challenger_top1=tk(ln[i,19]),challenger_top2=tk(ln[i,20]),base_top1_weight=lb[i,2],challenger_top1_weight=ln[i,2],base_gross=lb[i,1],challenger_gross=ln[i,1],base_rebalanced=int(lb[i,4]),challenger_rebalanced=int(ln[i,4]),base_stops=int(lb[i,7]+lb[i,8]),challenger_stops=int(ln[i,7]+ln[i,8]),log_pnl_difference=log_returns(new['nav'])[i]-log_returns(base['nav'])[i]))
pd.DataFrame(events).to_csv(O/'DECISION_TO_EXECUTION_LEDGER.csv',index=False)
pd.DataFrame(ci).to_csv(O/'ATTRIBUTION_CONFIDENCE_INTERVALS.csv',index=False)
pd.DataFrame(summary).to_csv(O/'ACCOUNTING_RECONCILIATION.csv',index=False)
pd.DataFrame(conditional).to_csv(O/'POLICY_LEAVE_ONE_OUT.csv',index=False)
pd.DataFrame(ddrows).to_csv(O/'DRAWDOWN_SHAPLEY.csv',index=False)
pd.DataFrame(yearrows).to_csv(O/'POLICY_YEAR_ATTRIBUTION.csv',index=False)
res=dict(archived_paths_recomputed=len(checks),new_policy_replays=len(policy),raw_revisions=3,sessions=D,first=str(dates[0].date()),last=str(dates[-1].date()),max_archived_cagr_error=max(r['cagr_error'] for r in checks),max_archived_dd_error=max(r['maxdd_error'] for r in checks),max_shapley_daily_identity_error=max(r['efficiency_error'] for r in summary),all_on_replays_verified=6,new_model_fits=0,annualization_convention='252/2366; initial NAV=1 included; last flat observation retained exactly as canonical engine',time_label_warning='Canonical E[k] values next-open wealth for decision date k; ledger explicitly retains next valuation date. Monthly/yearly attribution follows canonical decision-date label, not brokerage settlement accounting.',statistical_status='Exploratory historical paired time-block inference; vintage mean first; simultaneous intervals are per declared family, not across all prior research.')
(O/'VERIFIED_SUMMARY.json').write_text(json.dumps(res,indent=2))
print(json.dumps(res,indent=2))
print(pd.DataFrame(ci).query('block_sessions==21')[['family','component','annual_log_pp','ci95_low','ci95_high']].to_string(index=False))
