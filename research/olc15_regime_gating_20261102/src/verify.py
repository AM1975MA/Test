"""Independent numerical checks and actual-prefix perturbation audits."""
import json,math
import numpy as np,pandas as pd
from io_utils import ROOT,MARKETS,VARIANTS,readcsv,dump
from core import CONTEXT,benchmark_context,recent_skill,predict_gate
from gating import fit_year
from portfolio_adapter import adapt_state
from vector_engine import simulate

def independent_weights(a):
 a=np.asarray(a,float)
 if len(a)<2 or not np.isfinite(a).all():raise ValueError('Explicit finite forecast support required')
 cut=np.sort(a)[-2];high=a>cut;tie=a==cut;w=np.zeros(len(a));w[high]=.5;w[tie]=(2-high.sum())/(2*tie.sum());return w

def main():
 causal=[];modelerrs=[]
 for label,fn,prefix in [('native','GATE_PANEL.csv',''),('fused','FUSION_GATE_PANEL.csv','F_')]:
  p=readcsv(ROOT/'inputs'/fn)
  for year in [2023,2025]:
   cutoff=pd.Timestamp(year,1,1);mut=p.copy();future=mut.available>=cutoff;mut.loc[future,'delta']=500.
   mut.loc[mut.date>=cutoff,CONTEXT]=5e4
   for i,r in mut.iterrows():mut.loc[i,['recent','recent_count']]=recent_skill(mut,r.date,r.market)
   for features in [['recent'],CONTEXT+['recent']]:
    a=fit_year(p,year,features);b=fit_year(mut,year,features)
    assert json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True)
    causal.append(dict(target=label,year=year,features=len(features),future_perturbation_unchanged=True))
  for path in sorted((ROOT/'models').glob(f'*_{prefix}*.json')):
   # Do not double-count a native file in the fused group or vice versa.
   is_fused='_F_' in path.stem
   if is_fused!=(label=='fused'):continue
   r=json.loads(path.read_text())
   if not r['active']:continue
   restored=fit_year(p,r['year'],r['features']);a=r['model'];b=restored['model']
   assert a['penalty']==b['penalty'];err=float(np.max(abs(np.r_[a['intercept'],a['coef']]-np.r_[b['intercept'],b['coef']])))
   assert err<1e-12;modelerrs.append(dict(model=path.name,max_parameter_error=err))
 for m in MARKETS:
  c=pd.read_csv(ROOT/f'inputs/{m}_BENCHMARK_CLOSE.csv',parse_dates=['date']).set_index('date').close
  for cutoff in [pd.Timestamp('2023-01-01'),pd.Timestamp('2025-01-01')]:
   x=c.copy();x.loc[x.index>=cutoff]*=3.5;old=benchmark_context(c);new=benchmark_context(x)
   pd.testing.assert_frame_equal(old.loc[old.index<cutoff],new.loc[new.index<cutoff])
   causal.append(dict(market=m,cutoff=str(cutoff.date()),price_prefix_unchanged=True))
 dump(ROOT/'results/CAUSAL_VERIFICATION.json',causal);pd.DataFrame(modelerrs).to_csv(ROOT/'results/GATE_REFIT_VERIFICATION.csv',index=False)
 # Completely independent native U, return, regret and universe subtraction.
 observations=readcsv(ROOT/'results/OPPORTUNITY_MONTHS.csv.gz').drop_duplicates(['market','date','variant','stage','horizon']).set_index(['market','date','variant','stage','horizon'])
 errors=[];checked=0
 for m in MARKETS:
  f=readcsv(ROOT/f'inputs/{m}_FITTING_FRAME.csv.gz');s=readcsv(ROOT/f'results/{m}_SCORES.csv.gz');cols=[c for c in f if c.startswith(('fwd_ret_','exit_date_'))]+['signal_date','ticker']
  z=s.merge(f[cols],on=['signal_date','ticker'],validate='one_to_one')
  for date,g in z.groupby('signal_date'):
   if (m,date) not in observations.index.droplevel([2,3,4]):continue
   g=g[np.isfinite(g.ORIGINAL_CURRENT)].copy()
   rr=g[['fwd_ret_21','fwd_ret_42','fwd_ret_63']].to_numpy();q=math.sqrt(.5)
   u=np.array([(math.log1p(a)+q*math.log((1+b)/(1+a))+q*q*math.log((1+c)/(1+b)))/(1+q+q*q) for a,b,c in rr])
   values={'U42':u,'0_21':rr[:,0],'0_42':rr[:,1],'0_63':rr[:,2],'21_42':(1+rr[:,1])/(1+rr[:,0])-1,'42_63':(1+rr[:,2])/(1+rr[:,1])-1}
   for v in VARIANTS:
    for stage in ['CURRENT','SMOOTH','FUSION']:
     w=independent_weights(g[v+'_'+stage].to_numpy())
     for h,arr in values.items():
      rec=observations.loc[(m,date,v,stage,h)];selected=sum(float(a)*float(b) for a,b in zip(w,arr));mean=sum(float(x) for x in arr)/len(arr);best=sum(sorted(arr)[-2:])/2
      for name,val in [('top2_return',selected),('top2_excess',selected-mean),('top2_regret',best-selected)]:
       e=abs(val-rec[name]);assert e<1e-12,(m,date,v,stage,h,name,e);errors.append(e);checked+=1
 # Separate portfolio implementation uses ratios/products rather than engine log helper.
 scorecard=readcsv(ROOT/'results/SCORECARD.csv');porterrors=[];capitalerrors=[];intervals=0
 for m in MARKETS:
  state=dict(np.load(ROOT/f'inputs/{m}_STATE_HALF.npz',allow_pickle=False))
  for config,ss in scorecard[scorecard.market.eq(m)].groupby('config'):
   r=np.load(ROOT/'results/paths'/f'{config}.npz');nav=r['nav'];dates=pd.DatetimeIndex(r['dates'])[1:]
   cap=(r['primary_units'][:-1]*state['O'][1:]).sum(1)+(r['defensive_units'][:-1]*state['O'][1:]).sum(1)+r['free_cash'][:-1]
   e=float(np.max(abs(cap-nav[:-1])));assert e<1e-10;capitalerrors.append(e);intervals+=len(cap)
   ret=nav[:-1]/np.r_[1.,nav[:-2]]
   for row in ss.itertuples():
    mask=(dates>=pd.Timestamp(row.first_valuation))&(dates<=pd.Timestamp(row.last_valuation));returns=ret[mask]
    wealth=np.cumprod(returns);peak=1.;worst=0.
    for a in wealth:peak=max(peak,a);worst=min(worst,a/peak-1)
    vals={'cagr':float(wealth[-1]**(252/len(wealth))-1),'maxdd':worst,'period_return':float(wealth[-1]-1),'annual_log':float(math.log(wealth[-1])*252/len(wealth))}
    for key,val in vals.items():
     e=abs(val-getattr(row,key));assert e<2e-10,(config,row.period,key,e);porterrors.append(e)
 # Every full replay begins from the same preset state; verify future score mutation.
 for m in MARKETS:
  st0=dict(np.load(ROOT/f'inputs/{m}_STATE_HALF.npz',allow_pickle=False));cal=readcsv(ROOT/f'inputs/{m}_CALENDAR.csv');s=readcsv(ROOT/f'results/{m}_SCORES.csv.gz');v='F_CONTEXT_RECENT_FUSION';cutoff=pd.Timestamp('2024-01-01')
  mutated=s.copy();mask=mutated.signal_date>=cutoff;mutated.loc[mask,v]=-mutated.loc[mask,v]
  a,ev,_=adapt_state(st0,cal,s,v);b,eb,_=adapt_state(st0,cal,mutated,v);ra=simulate(a,ev);rb=simulate(b,eb)
  mask=pd.DatetimeIndex(st0['dates'])<pd.Timestamp('2023-12-29')
  for key in ra:np.testing.assert_array_equal(ra[key][mask],rb[key][mask])
  causal.append(dict(market=m,future_score_perturbation_portfolio_prefix=True))
 dump(ROOT/'results/CAUSAL_VERIFICATION.json',causal)
 report=dict(saved_gate_refits=len(modelerrs),max_refit_error=max(x['max_parameter_error'] for x in modelerrs),causal_checks=len(causal),native_metric_checks=checked,max_native_error=max(errors),portfolio_paths=scorecard.config.nunique(),portfolio_metric_checks=len(porterrors),max_portfolio_metric_error=max(porterrors),capital_intervals=intervals,max_capital_error=max(capitalerrors),review='author verification with independent calculations, not external review')
 dump(ROOT/'results/VERIFIED_SUMMARY.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
