#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math, time
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBRanker
SEEDS=[101,202,303]
REF={'D1':0.15023,'D2':0.22645,'DEV':0.18617,'HOLD':0.27605,'FULL':0.21654064}

def loadmod(path,name):
 s=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def period_metric(E,idx,start,end):
 mask=(idx>=pd.Timestamp(start))&(idx<=pd.Timestamp(end));ids=np.flatnonzero(mask)
 if len(ids)<2:return np.nan
 x=E[:,ids];x=x/x[:,[0]]
 years=(idx[ids[-1]]-idx[ids[0]]).days/365.25
 return float(np.nanmean(np.power(x[:,-1],1/max(years,1e-9))-1))

def main():
 ap=argparse.ArgumentParser();
 for n,t in [('package_root',str),('tag',str),('trees',int),('depth',int),('lr',float),('mcw',float),('lam',float),('alpha',float),('subsample',float),('colsample',float)]: ap.add_argument('--'+n.replace('_','-'),dest=n,required=True,type=t)
 ap.add_argument('--output',required=True);a=ap.parse_args();R=Path(a.package_root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 base=loadmod(R/'source/titanium_retrained_current_data_audit.py','base_arch');v6=loadmod(R/'source/titanium_reconstruction_v6.py','v6_arch')
 df=pd.read_parquet(R/'panels/NPORT_TITANIUM_PANEL.parquet');df['signal_date']=pd.to_datetime(df.signal_date);df['exit_date_21']=pd.to_datetime(df.exit_date_21)
 F=list(base.F2D_FEATURES);params=dict(base.COMPACT_PARAMS);params.update(n_estimators=a.trees,max_depth=a.depth,learning_rate=a.lr,min_child_weight=a.mcw,reg_lambda=a.lam,reg_alpha=a.alpha,subsample=a.subsample,colsample_bytree=a.colsample,n_jobs=4)
 parts={s:[] for s in SEEDS};fit=[];t0=time.time()
 for year in range(2017,2027):
  cut=pd.Timestamp(year,1,1);tr=df[(df.signal_date<cut)&(df.exit_date_21<cut)&df.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=df[df.signal_date.dt.year==year].sort_values(['signal_date','ticker'])
  if te.empty:continue
  groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int);Xtr=tr[F].replace([np.inf,-np.inf],np.nan);Xte=te[F].replace([np.inf,-np.inf],np.nan)
  for seed in SEEDS:
   m=XGBRanker(**params,random_state=seed);m.fit(Xtr,y,group=groups,verbose=False);q=te[['signal_date','ticker']].copy();q[f'v{seed}']=pd.Series(m.predict(Xte),index=te.index).groupby(te.signal_date).rank(pct=True).to_numpy();parts[seed].append(q)
  fit.append({'year':year,'train_rows':len(tr),'test_rows':len(te)})
 z=None
 for seed in SEEDS:
  q=pd.concat(parts[seed],ignore_index=True);z=q if z is None else z.merge(q,on=['signal_date','ticker'],how='inner')
 z['compact_rank']=z[[f'v{s}' for s in SEEDS]].mean(axis=1)
 aux=pd.read_parquet(R/'panels/SUPER_GOLD_OOS_SCORE_PANEL.parquet')[['signal_date','ticker','tail_rank','top_macro','macro_gap_z','macro_category']];aux.signal_date=pd.to_datetime(aux.signal_date)
 q=z.merge(aux,on=['signal_date','ticker'],how='left');q['pre']=.7*q.compact_rank+.3*q.tail_rank;q['bonus']=np.where((q.macro_category==q.top_macro)&(q.macro_gap_z>=.75)&(q.tail_rank>=.80),.15,0.0);q['score']=q.pre+q.bonus;q['TIT_R']=q.groupby('signal_date').score.rank(pct=True)
 cal=pd.read_csv(R/'panels/MONTHLY_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date']);dates=list(cal.signal_date)
 mats={k:pd.read_parquet(R/'data'/f'{k.upper()}.parquet') for k in ['Open','High','Low','Close','Volume']}
 for k,x in mats.items():x.index=pd.to_datetime(x.index).tz_localize(None);x.columns=[str(c).upper() for c in x.columns]
 ticks=sorted(set.intersection(*[set(x.columns) for x in mats.values()]));mats={k:v.reindex(columns=ticks) for k,v in mats.items()};ti={t:i for i,t in enumerate(ticks)}
 mem=pd.read_csv(R/'panels/BASKET_MEMBERSHIP_500.csv');baskets=[np.array([ti[t] for t in g.ticker.astype(str)],int) for _,g in mem.groupby('basket',sort=True)]
 idx,tix,tii,O,L,C,PC,gap,UD1,UNEG,UH,SA,ei,xi,mi=v6.prepare_sim_inputs(mats,cal);assert tix==ticks
 sm=q.pivot(index='signal_date',columns='ticker',values='score').reindex(index=dates,columns=ticks).to_numpy(float);rm=q.pivot(index='signal_date',columns='ticker',values='TIT_R').reindex(index=dates,columns=ticks).to_numpy(float)
 B=len(baskets);K=len(dates);sel=np.full((B,K,2),-1,np.int16);bw=np.zeros((B,K,2))
 for b,ix in enumerate(baskets):
  for k in range(K):
   ok=ix[np.isfinite(sm[k,ix])]
   if len(ok)<2:continue
   order=ok[np.argsort(-sm[k,ok],kind='stable')];u,v=order[:2];w=1.0 if (rm[k,u]-rm[k,v])>=.12 else .75;sel[b,k]=[u,v];bw[b,k]=[w,1-w]
 E=v6.exact_sim(sel[None],bw[None],mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,tii['BIL'],tii['SHV'],v6.COST,v6.STOP_SLIP)[0]
 full=np.array([v6.metrics(E[b],idx) for b in range(B)])[:,0].mean();res={'tag':a.tag,**{k:getattr(a,k) for k in ['trees','depth','lr','mcw','lam','alpha','subsample','colsample']},'D1':period_metric(E,idx,'2017-02-01','2019-12-31'),'D2':period_metric(E,idx,'2020-01-01','2022-12-31'),'DEV':period_metric(E,idx,'2017-02-01','2022-12-31'),'HOLD':period_metric(E,idx,'2023-01-01','2026-12-31'),'FULL':float(full)}
 res['dev_reconstruction_mae']=float(np.mean([abs(res[p]-REF[p]) for p in ['D1','D2','DEV']]))
 res['dev_reconstruction_rmse']=float(math.sqrt(np.mean([(res[p]-REF[p])**2 for p in ['D1','D2','DEV']])))
 res['hold_error']=float(res['HOLD']-REF['HOLD']);res['full_error']=float(res['FULL']-REF['FULL']);res['elapsed_sec']=time.time()-t0
 pd.DataFrame([res]).to_csv(out/'RESULT.csv',index=False);pd.DataFrame(fit).to_csv(out/'FIT_AUDIT.csv',index=False);(out/'RESULT.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2),flush=True)
if __name__=='__main__':main()
