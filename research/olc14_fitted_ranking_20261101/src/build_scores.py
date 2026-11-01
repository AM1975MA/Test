"""Build causal forecast streams. Outcomes are used for fitting/evaluation only."""
from __future__ import annotations
import json
import numpy as np,pandas as pd
from common import ROOT,P11,P12,P13,MARKETS,SEEDS,HEADS,TARGETS,VARIANTS,readcsv
from ranking_core import PRIOR,utility,score
from chrono_fit import fit_year,choose_target,anchor_scale
from recovery_core import atomic_json

def compose_current(return_rank,current):
 r=np.asarray(return_rank,float);c=np.asarray(current,float)
 if r.ndim!=2 or r.shape!=c.shape or not len(r):raise ValueError('Aligned monthly score matrices required')
 l1=c[np.maximum(np.arange(len(c))-1,0)];l2=c[np.maximum(np.arange(len(c))-2,0)]
 vals=np.stack([c,l1,l2]);weights=np.array([.4,.3,.3])[:,None,None];ok=np.isfinite(vals);den=(weights*ok).sum(0)
 avg=np.divide((np.where(ok,vals,0)*weights).sum(0),den,out=np.full_like(c,np.nan),where=den>0)
 avg=np.where(ok.all(0),.4*c+.3*l1+.3*l2,avg)
 smooth=np.where(np.isfinite(c),np.clip(avg,0,1)**1.1,np.nan)
 return smooth,.475*r+.525*smooth

def _forecast_set(market,seed,new=True):
 frames=[]
 for s in SEEDS if seed=='MEAN3' else (int(seed),):
  p=ROOT/f'results/{market}_S{s}_HEAD_FORECASTS.csv.gz' if new else P13/f'results/{market}_S{s}_PREDICTIONS.csv.gz'
  frames.append(readcsv(p).sort_values(['signal_date','ticker']).reset_index(drop=True))
 keys=['signal_date','ticker'];out=frames[0][keys].copy()
 for f in frames:pd.testing.assert_frame_equal(out,f[keys])
 for c in frames[0].columns:
  if c not in keys:out[c]=np.stack([f[c].to_numpy() for f in frames]).mean(0)
 return out

def load_frame(market,seed='MEAN3'):
 name='MEAN3' if seed=='MEAN3' else f'S{seed}'
 f=readcsv(P12/f'inputs/{market}_{name}_INPUTS.csv.gz')[['signal_date','ticker','RETURN']]
 f=f.merge(_forecast_set(market,seed,True),on=['signal_date','ticker'],how='left',validate='one_to_one')
 f=f.merge(_forecast_set(market,seed,False),on=['signal_date','ticker'],how='left',validate='one_to_one').sort_values(['signal_date','ticker']).reset_index(drop=True)
 for head in (*HEADS,*TARGETS):
  et=f.groupby('signal_date')[head+'_ET'].rank(pct=True,method='average')
  xg=f.groupby('signal_date')[head+'_XGB'].rank(pct=True,method='average')
  f[head]=(.6*et+.4*xg).where(np.isfinite(f.RETURN))
 valid=np.isfinite(f.ORIGINAL_P15)
 for c in HEADS+TARGETS:assert np.array_equal(valid,np.isfinite(f[c])),(market,seed,c)
 labels=readcsv(P11/f'inputs/{market}_LAYER_LABELS.csv.gz').drop(columns=['source_date'])
 f=f.merge(labels,on=['signal_date','ticker'],how='left',validate='one_to_one')
 return f

def make_groups(frames):
 groups=[]
 for market,f in frames.items():
  for date,g0 in f.groupby('signal_date',sort=True):
   g=g0[np.isfinite(g0.ORIGINAL_P15)]
   if len(g)<20:continue
   rr=g[['fwd_ret_21','fwd_ret_42','fwd_ret_63']].to_numpy(float)
   full=np.isfinite(rr).all() and (rr>-1).all() and g.exit_date_63.notna().all() and np.isfinite(g.TARGET).all()
   groups.append(dict(market=market,date=date,available=g.exit_date_63.max() if full else pd.NaT,
    positions=g.index.to_numpy(),tickers=g.ticker.to_numpy(),CUM=g[['C21','C42','C63']].to_numpy(),INC=g[['C21','I42','I63']].to_numpy(),
    targets={t:g[t].to_numpy() for t in TARGETS},u=utility(rr) if full else np.full(len(g),np.nan),returns=rr,legacy_y=g.TARGET.to_numpy(),full=bool(full)))
 return groups

def estimate_parameters(groups):
 params={};summary=[]
 for year in range(2021,2027):
  c=pd.Timestamp(year,1,1);out={}
  for rep in ['CUM','INC']:
   p=fit_year(groups,c,rep);out[rep]=p
   assert pd.Timestamp(p['max_training_exit'])<c
   summary.append(dict(year=year,representation=rep,alpha=p['alpha'],shrinkage=p['lambda'],b1=p['beta'][0],b2=p['beta'][1],b3=p['beta'][2],training_EU=p['training_groups']['EU'],training_USA=p['training_groups']['USA'],inner_fits=p['inner_fits'],max_training_exit=p['max_training_exit']))
   print('FIT',year,rep,'beta',p['beta'],'alpha',p['alpha'],'lambda',p['lambda'],flush=True)
   atomic_json(ROOT/f'models/FUSION_{year}_{rep}.json',p)
  out['TARGET']=choose_target(groups,c,list(TARGETS));print('TARGET',year,out['TARGET']['target'],flush=True)
  params[str(year)]=out;atomic_json(ROOT/'results/FITTED_PARAMETERS.json',params)
 pd.DataFrame(summary).to_csv(ROOT/'results/PARAMETER_PATH.csv',index=False)
 return params

def score_frames(frames,groups,params):
 results={};mapping=[]
 for market,f in frames.items():
  out=f[['signal_date','ticker','RETURN']].copy()
  for v in VARIANTS:
   out[v+'_CURRENT']=np.nan;out[v+'_MAPPED']=np.nan
  for g in groups:
   if g['market']!=market:continue
   idx=g['positions'];date=g['date'];p=params.get(str(date.year))
   out.loc[idx,'ORIGINAL_CURRENT']=g['targets']['ORIGINAL_P15'];out.loc[idx,'ORIGINAL_MAPPED']=g['targets']['ORIGINAL_P15']
   target=p['TARGET']['target'] if p else 'ORIGINAL_P15'
   out.loc[idx,'TARGET_SELECT_CURRENT']=g['targets'][target];out.loc[idx,'TARGET_SELECT_MAPPED']=g['targets'][target]
   for rep in ['CUM','INC']:
    anchor=score(g[rep],PRIOR);cfg=p[rep] if p else dict(beta=PRIOR,alpha=1.)
    raw=score(g[rep],cfg['beta'],cfg['alpha']);mapped=anchor_scale(raw,anchor)
    out.loc[idx,rep+'_FIXED_CURRENT']=anchor;out.loc[idx,rep+'_FIXED_MAPPED']=anchor
    out.loc[idx,rep+'_FIT_CURRENT']=raw;out.loc[idx,rep+'_FIT_MAPPED']=mapped
    mapping.append(dict(market=market,date=date,representation=rep,raw_unique=len(np.unique(raw)),mapped_unique=len(np.unique(mapped)),anchor_unique=len(np.unique(anchor)),max_scale_change=float(np.max(abs(raw-mapped)))))
  dates=pd.DatetimeIndex(sorted(f.signal_date.unique()));ticks=sorted(f.ticker.unique());di=dates.get_indexer(f.signal_date);ti=pd.Index(ticks).get_indexer(f.ticker)
  def mat(col):return out.pivot(index='signal_date',columns='ticker',values=col).reindex(index=dates,columns=ticks).to_numpy(float)
  r=mat('RETURN')
  for v in VARIANTS:
   sm,fu=compose_current(r,mat(v+'_MAPPED'));out[v+'_SMOOTH']=sm[di,ti];out[v+'_FUSION']=fu[di,ti]
  results[market]=out
 return results,pd.DataFrame(mapping)

def main():
 assert json.loads((ROOT/'results/TRAINING_COMPLETE.json').read_text())['new_models']==480
 frames={m:load_frame(m) for m in MARKETS};groups=make_groups(frames)
 for m,f in frames.items():f.to_csv(ROOT/f'inputs/{m}_FITTING_FRAME.csv.gz',index=False,compression='gzip')
 params=estimate_parameters(groups)
 for seed in ('MEAN3',*SEEDS):
  fs=frames if seed=='MEAN3' else {m:load_frame(m,seed) for m in MARKETS};gs=groups if seed=='MEAN3' else make_groups(fs)
  outs,mapping=score_frames(fs,gs,params)
  mapping.to_csv(ROOT/f'results/MAPPING_{seed}.csv',index=False)
  for m,out in outs.items():
   out.to_csv(ROOT/f'results/{m}_{seed}_SCORES.csv.gz',index=False,compression='gzip')
   if seed=='MEAN3':
    old=readcsv(P13/f'results/{m}_SCORES.csv.gz');z=out.merge(old[['signal_date','ticker','ORIGINAL_P15_CURRENT','ORIGINAL_P15_FUSION']],on=['signal_date','ticker'],validate='one_to_one')
    np.testing.assert_array_equal(z.ORIGINAL_CURRENT,z.ORIGINAL_P15_CURRENT)
    np.testing.assert_array_equal(z.ORIGINAL_FUSION,z.ORIGINAL_P15_FUSION)
  print('SCORES',seed,flush=True)
 ninner=sum(p[r]['inner_fits'] for p in params.values() for r in ['CUM','INC'])
 atomic_json(ROOT/'results/FITTING_COMPLETE.json',dict(final_constrained_fits=12,inner_constrained_fits=ninner,target_selections=6,original_score_parity=True,future_outcomes_not_for_eligibility=True,parameter_rules_common_both_markets=True))
if __name__=='__main__':main()
