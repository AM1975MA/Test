"""Paired descriptive frontiers and time-block uncertainty; no posterior claims."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'results/analysis';O.mkdir(exist_ok=True)

def monthly(stage,market,config,end='2024-12'):
 a=np.load(R/'results'/stage/'paths'/f'{market}_{config}.npz');ds=pd.DatetimeIndex(a['dates']);lr=np.diff(np.log(np.r_[1.,a['nav']]))
 s=pd.Series(lr,index=ds).groupby(ds.to_period('M')).sum()
 return s.loc['2019-02':end]

def boot(mat,block,reps=10000):
 n=len(mat);rng=np.random.default_rng(20261031);starts=rng.integers(0,n,size=(reps,(n+block-1)//block))
 ix=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
 samples=mat[ix].mean(axis=1)*1200
 return samples

# Explicit configs, no inferred best-case comparison.
comparisons=[
 ('native','NATIVE_CAL36_PLAIN_ORIGINAL_NONE_C10','NATIVE_LEGACY_PLAIN_ORIGINAL_NONE_C10','rolling36_vs_native'),
 ('native','NATIVE_LEGACY_CORR_ORIGINAL_NONE_C10','NATIVE_LEGACY_PLAIN_ORIGINAL_NONE_C10','correlation_vs_native'),
 ('rebuilt','RETURN_REFIT_PLAIN_ORIGINAL_NONE_C10','NATIVE_REFERENCE_PLAIN_ORIGINAL_NONE_C10','new_return_vs_native'),
 ('rebuilt','HYBRID_REFIT_PLAIN_ORIGINAL_NONE_C10','NATIVE_REFERENCE_PLAIN_ORIGINAL_NONE_C10','new_hybrid_vs_native'),
 ('rebuilt','REBUILT_LEGACY_PLAIN_ORIGINAL_NONE_C10','NATIVE_REFERENCE_PLAIN_ORIGINAL_NONE_C10','full_rebuild_vs_native'),
 ('rebuilt','REBUILT_R25_PLAIN_ORIGINAL_NONE_C10','REBUILT_LEGACY_PLAIN_ORIGINAL_NONE_C10','R25_vs_rebuilt'),
 ('rebuilt','REBUILT_LEGACY_PLAIN_ORIGINAL_SYS_FAST_C10','REBUILT_LEGACY_PLAIN_ORIGINAL_NONE_C10','systemic_fast_vs_rebuilt'),
 ('rebuilt','REBUILT_LEGACY_BUFFER_ORIGINAL_SYS_FAST_C10','REBUILT_LEGACY_PLAIN_ORIGINAL_NONE_C10','buffer_fast_vs_rebuilt'),
 ('rebuilt','REBUILT_LEGACY_PLAIN_HALF_NONE_C10','REBUILT_LEGACY_PLAIN_ORIGINAL_NONE_C10','half_vs_rebuilt')]
rows=[];details=[]
for stage,cand,base,name in comparisons:
 for end,period in [('2024-12','PRE2025'),('2026-06','FULL_COMPLETE_MONTHS')]:
  frame=pd.concat({market:monthly(stage,market,cand,end)-monthly(stage,market,base,end) for market in ['USA','EU']},axis=1).dropna()
  for d,row in frame.iterrows():details.append({'contrast':name,'period':period,'month':str(d),'US_log_difference':row.USA,'EU_log_difference':row.EU})
  for block in [3,6]:
   samp=boot(frame.to_numpy(),block);point=frame.mean().to_numpy()*1200
   row={'contrast':name,'stage':stage,'candidate':cand,'reference':base,'period':period,'first_month':str(frame.index[0]),'last_month':str(frame.index[-1]),'n_months':len(frame),'block_months':block,'resamples':10000,'seed':20261031,'US_log_pp':point[0],'EU_log_pp':point[1],
    'US_ci_low':np.quantile(samp[:,0],.025),'US_ci_high':np.quantile(samp[:,0],.975),'EU_ci_low':np.quantile(samp[:,1],.025),'EU_ci_high':np.quantile(samp[:,1],.975),
    'joint_positive_resampling_fraction':np.mean((samp>0).all(axis=1)),'any_below_minus2pp_resampling_fraction':np.mean((samp< -2).any(axis=1)),
    'interpretation':'Paired circular monthly-block resampling stability, not posterior or future success probability; post-selection exploratory.'}
   rows.append(row)
pd.DataFrame(rows).to_csv(O/'PAIRED_UNCERTAINTY.csv',index=False);pd.DataFrame(details).to_csv(O/'MONTHLY_CONTRASTS.csv',index=False)
front=[];summary=[]
for stage,baseline in [('native','NATIVE_LEGACY_PLAIN_ORIGINAL_NONE_C30'),('rebuilt','REBUILT_LEGACY_PLAIN_ORIGINAL_NONE_C30')]:
 s=pd.read_csv(R/'results'/stage/'SCORECARD.csv');s=s[(s.period=='PRE2025')&(s.fee==.003)]
 a=s.pivot(index='config',columns='market',values=['annual_log','maxdd','cagr']);b=a.loc[baseline]
 # Only compare main source-version candidates in rebuilt selection, not component-graft experiments.
 selection=a.index.str.startswith('REBUILT_') if stage=='rebuilt' else np.ones(len(a),bool)
 dlog=a['annual_log']-b['annual_log'];ddd=a['maxdd']-b['maxdd'];worst=dlog.min(axis=1);risk=ddd.min(axis=1)
 vec=np.column_stack([a['annual_log']['EU'],a['annual_log']['USA'],a['maxdd']['EU'],a['maxdd']['USA']]);pareto=[]
 for j in range(len(a)):
  dom=np.all(vec>=vec[j]-1e-12,axis=1)&np.any(vec>vec[j]+1e-12,axis=1);pareto.append(not dom.any())
 pass_ids=a.index[(worst>1e-12)&(risk>=-1e-12)&selection]
 summary.append({'stage':stage,'reference':baseline,'eligible_configs':int(sum(selection)),'positive_log_and_nonworse_DD_both':len(pass_ids),'interpretation':'This is a descriptive joint growth/DD dominance count, NOT a rule excluding uncertain or risk-return tradeoff candidates.'})
 for j,c in enumerate(a.index):front.append(dict(stage=stage,config=c,eligible_for_rule=bool(selection[j]),EU_CAGR=a.loc[c,('cagr','EU')],US_CAGR=a.loc[c,('cagr','USA')],EU_MaxDD=a.loc[c,('maxdd','EU')],US_MaxDD=a.loc[c,('maxdd','USA')],EU_delta_log_pp=dlog.loc[c,'EU']*100,US_delta_log_pp=dlog.loc[c,'USA']*100,worst_delta_log_pp=worst.loc[c]*100,worst_DD_improvement_pp=risk.loc[c]*100,on_descriptive_four_metric_frontier=pareto[j]))
pd.DataFrame(front).to_csv(O/'DEVELOPMENT_FRONTIER_STRESS.csv',index=False);(O/'FRONTIER_SUMMARY.json').write_text(json.dumps(summary,indent=2))
# Clean report table with actual period returns as well as annualized values.
parts=[]
for stage in ['native','rebuilt','execution']:
 p=R/'results'/stage/'SCORECARD.csv'
 if p.exists():
  f=pd.read_csv(p)
  if 'stage' in f: f=f.rename(columns={'stage':'source_stage'})
  f.insert(0,'stage',stage);parts.append(f)
pd.concat(parts).to_csv(O/'ALL_SCORECARDS.csv',index=False)
print('UNCERTAINTY_ROWS',len(rows));print(json.dumps(summary,indent=2))
print(pd.DataFrame(rows).query('period=="PRE2025" and block_months==6')[['contrast','US_log_pp','EU_log_pp','US_ci_low','US_ci_high','EU_ci_low','EU_ci_high']].to_string(index=False))
