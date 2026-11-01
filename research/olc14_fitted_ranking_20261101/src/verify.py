"""Independent calculations, chronology audits and real future-perturbation tests."""
from __future__ import annotations
import os
for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[k]='1'
import json,copy
import numpy as np,pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import ndcg_score
from common import ROOT,P11,P12,MARKETS,SEEDS,VARIANTS,readcsv
from build_scores import load_frame,make_groups
from chrono_fit import fit_year
from recovery_core import atomic_json
from ranking_core import score

def independent_weights(s):
 order=np.sort(np.asarray(s));cut=order[-2];high=s>cut;eq=s==cut
 w=np.zeros(len(s));w[high]=.5;w[eq]=(2-high.sum())/(2*eq.sum());return w

def independent_util(r):
 l1=np.log(1+r[:,0]);l2=np.log((1+r[:,1])/(1+r[:,0]));l3=np.log((1+r[:,2])/(1+r[:,1]));q=np.sqrt(.5)
 return (l1+q*l2+.5*l3)/(1+q+.5)

def native_checks():
 ref=readcsv(ROOT/'results/OPPORTUNITY_MONTHS.csv.gz');ty=readcsv(ROOT/'results/TARGET_MONTHS.csv.gz')
 cols=['top2_return','top2_excess','top2_regret','selected_negative_return','bottom_quintile_fraction','top5_capture'];rows=[];nc=0;ne=0.
 for m in MARKETS:
  labels=readcsv(P11/f'inputs/{m}_LAYER_LABELS.csv.gz').drop(columns=['source_date'])
  for seed in ('MEAN3',*SEEDS):
   f=readcsv(ROOT/f'results/{m}_{seed}_SCORES.csv.gz').merge(labels,on=['signal_date','ticker'],how='left',validate='one_to_one')
   sub=ref[(ref.market==m)&(ref.seed.astype(str)==str(seed))].drop_duplicates(['date','variant','stage','horizon'])
   groups={d:g[np.isfinite(g.ORIGINAL_CURRENT)] for d,g in f.groupby('signal_date')}
   for date,rday in sub.groupby('date'):
    g=groups[date];r=g[['fwd_ret_21','fwd_ret_42','fwd_ret_63']].to_numpy();n=len(g)
    outcomes={'U42':independent_util(r),'0_21':r[:,0],'0_42':r[:,1],'0_63':r[:,2],
     '21_42':np.exp(np.log1p(r[:,1])-np.log1p(r[:,0]))-1,'42_63':np.exp(np.log1p(r[:,2])-np.log1p(r[:,1]))-1}
    for (variant,stage),rr in rday.groupby(['variant','stage']):
     p=g[variant+'_'+stage].to_numpy();w=independent_weights(p)
     for z in rr.itertuples():
      y=outcomes[z.horizon];ranks=pd.Series(y).rank(method='average').to_numpy();sel=float(np.sum(w*y))
      vals=[sel,sel-float(np.mean(y)),float(np.sort(y)[-2:].sum()/2-sel),float(w@(y<0)),float(w@(ranks/n<=.2)),float(w@(ranks>n-5))]
      errors=[abs(v-getattr(z,c)) for c,v in zip(cols,vals)];assert max(errors)<2e-12,(m,seed,date,variant,stage,z.horizon,errors)
      rows.append(dict(market=m,seed=str(seed),date=date,variant=variant,stage=stage,horizon=z.horizon,max_error=max(errors)))
     # Independent external NDCG implementation, all unique metric cases.
     a=ty[(ty.market==m)&(ty.seed.astype(str)==str(seed))&(ty.date==date)&(ty.variant==variant)&(ty.stage==stage)]
     if len(a):
      val=ndcg_score(g.TARGET.to_numpy()[None,:],p[None,:],k=2);err=abs(val-a.iloc[0].ndcg2);assert err<1e-12
      nc+=1;ne=max(ne,err)
   print('NATIVE_CHECK',m,seed,len(rows),flush=True)
 pd.DataFrame(rows).to_csv(ROOT/'results/INDEPENDENT_NATIVE_CHECKS.csv.gz',index=False,compression='gzip')
 return dict(unique_native_rows=len(rows),individual_payoff_checks=len(rows)*6,max_error=max(x['max_error'] for x in rows),ndcg_checks=nc,max_ndcg_error=ne)

def portfolio_checks():
 sc=readcsv(ROOT/'results/SCORECARD.csv');rows=[];navchecks=[]
 for config,g in sc.groupby('config'):
  r=g.iloc[0];p=np.load(ROOT/f'results/paths/{config}.npz');q=np.load(P12/f'inputs/{r.market}_STATE_HALF.npz')
  reconstructed=((p['primary_units'][:-1]+p['defensive_units'][:-1])*q['O'][1:]).sum(1)+p['free_cash'][:-1]
  err=float(np.max(abs(reconstructed-p['nav'][:-1])));assert err<1e-10
  navchecks.append(dict(config=config,intervals=len(reconstructed),max_error=err))
  daily=p['nav'][:-1]/np.r_[1,p['nav'][:-2]];dates=pd.DatetimeIndex(p['dates'])[1:]
  for row in g.itertuples():
   mask=(dates>=pd.Timestamp(row.first_valuation))&(dates<=pd.Timestamp(row.last_valuation));ratios=daily[mask];wealth=np.cumprod(ratios)
   dd=wealth/np.maximum.accumulate(np.r_[1,wealth])[1:]-1
   vals={'cagr':float(np.prod(ratios)**(252/len(ratios))-1),'maxdd':float(dd.min()),'period_return':float(np.prod(ratios)-1),'annual_log':float(np.log(np.prod(ratios))*252/len(ratios))}
   for k,v in vals.items():
    error=abs(v-getattr(row,k));assert error<1e-10,(config,row.period,k,error);rows.append(dict(config=config,period=row.period,metric=k,error=error))
 pd.DataFrame(rows).to_csv(ROOT/'results/INDEPENDENT_PORTFOLIO_CHECKS.csv',index=False)
 pd.DataFrame(navchecks).to_csv(ROOT/'results/INDEPENDENT_NAV_CHECKS.csv',index=False)
 return dict(paths=len(navchecks),intervals=sum(x['intervals'] for x in navchecks),metrics=len(rows),max_metric_error=max(x['error'] for x in rows),max_nav_error=max(x['max_error'] for x in navchecks))

def chronology_and_perturbation():
 params=json.loads((ROOT/'results/FITTED_PARAMETERS.json').read_text());rows=[]
 for year,p in params.items():
  cut=pd.Timestamp(int(year),1,1)
  for rep in ['CUM','INC']:
   a=p[rep];assert pd.Timestamp(a['max_training_exit'])<cut
   assert min(a['beta'])>=0 and abs(sum(a['beta'])-1)<1e-12
   for cv in a['cv']:
    for f in cv['folds']:
     assert pd.Timestamp(f['max_training_exit'])<pd.Timestamp(f['year'],1,1)
     assert pd.Timestamp(f['max_validation_exit'])<cut
   rows.append(dict(year=int(year),representation=rep,inner_fits=a['inner_fits'],passed=True))
  assert pd.Timestamp(p['TARGET']['max_validation_exit'])<cut
 groups=make_groups({m:load_frame(m) for m in MARKETS});pert=[]
 for year in [2022,2025]:
  cut=pd.Timestamp(year,1,1);changed=copy.deepcopy(groups)
  for g in changed:
   if pd.isna(g['available']) or g['available']>=cut:g['u']=np.linspace(100,-100,len(g['u']))
  for rep in ['CUM','INC']:
   original=fit_year(groups,cut,rep);new=fit_year(changed,cut,rep);stored=params[str(year)][rep]
   np.testing.assert_array_equal(new['beta'],original['beta']);assert new['alpha']==original['alpha'] and new['lambda']==original['lambda']
   gap=float(np.max(abs(np.array(original['beta'])-np.array(stored['beta']))));assert gap<1e-12
   decision_checks=0
   for g in groups:
    if g['date'].year==year:
     a=independent_weights(score(g[rep],original['beta'],original['alpha']));b=independent_weights(score(g[rep],stored['beta'],stored['alpha']))
     np.testing.assert_array_equal(a,b);decision_checks+=1
   pert.append(dict(year=year,representation=rep,perturbed_vs_unperturbed_coefficients_exact=True,stored_vs_refit_max_difference=gap,stored_vs_refit_top2_exact=decision_checks))
 atomic_json(ROOT/'results/CAUSAL_CHECKS.json',dict(annual=rows,future_perturbations=pert))
 return dict(annual_models=len(rows),future_perturbations=len(pert),inner_fits=sum(r['inner_fits'] for r in rows))

if __name__=='__main__':
 portfolio=portfolio_checks();print('PORTFOLIOS_VERIFIED',portfolio,flush=True)
 causal=chronology_and_perturbation();print('CAUSAL_VERIFIED',causal,flush=True)
 native=native_checks();model=json.loads((ROOT/'results/MODEL_RELOAD_COMPLETE.json').read_text())
 atomic_json(ROOT/'results/VERIFIED_SUMMARY.json',dict(portfolio=portfolio,causal=causal,native=native,model=model,external_reviewer=False))
 print('VERIFIED_ALL',flush=True)
