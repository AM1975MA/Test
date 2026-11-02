"""Declared post-observation extension: learn contribution after frozen fusion."""
import numpy as np,pandas as pd
from core import CONTEXT,recent_skill,predict_gate,mix_scores,compose_current
from prepare import group_outcome
from gating import FEATURE_SETS,fit_year
from io_utils import ROOT,MARKETS,FUSION_VARIANTS,readcsv,dump

def fusion_differential(frame):
 x=frame.drop(columns=['CUM_FIXED_MAPPED','CUM_FIT_MAPPED'],errors='ignore').rename(columns={'CUM_FIXED_FUSION':'CUM_FIXED_MAPPED','CUM_FIT_FUSION':'CUM_FIT_MAPPED'})
 return group_outcome(x)

def main():
 panel=readcsv(ROOT/'inputs/GATE_PANEL.csv').drop(columns=['delta','u_fixed','u_fit','full','n','available','recent','recent_count']);outs=[]
 for m in MARKETS:
  sc=readcsv(ROOT/f'inputs/{m}_MEAN3_SCORES.csv.gz');f=readcsv(ROOT/f'inputs/{m}_FITTING_FRAME.csv.gz')
  cols=[c for c in f if c.startswith(('fwd_ret_','exit_date_'))]+['signal_date','ticker']
  data=sc.merge(f[cols],on=['signal_date','ticker'],how='left',validate='one_to_one')
  for d,g in data.groupby('signal_date'):
   g=g[np.isfinite(g.ORIGINAL_CURRENT)];outs.append(dict(market=m,date=d,**fusion_differential(g)))
 panel=panel.merge(pd.DataFrame(outs),on=['market','date'],validate='one_to_one')
 panel['recent']=0.;panel['recent_count']=0
 for i,r in panel.iterrows():panel.loc[i,['recent','recent_count']]=recent_skill(panel,r.date,r.market)
 panel.to_csv(ROOT/'inputs/FUSION_GATE_PANEL.csv',index=False)
 params={};aud=[]
 for year in range(2022,2027):
  params[str(year)]={}
  for name,features in FEATURE_SETS.items():
   cfg=fit_year(panel,year,features);params[str(year)][name]=cfg;dump(ROOT/f'models/{year}_F_{name}.json',cfg)
   aud.append(dict(year=year,variant='F_'+name,active=cfg['active'],penalty=cfg.get('model',{}).get('penalty'),EU=cfg['counts'].get('EU',0),USA=cfg['counts'].get('USA',0),inner_fits=len(cfg.get('inner',[])),max_available=cfg.get('max_train_available')))
  dump(ROOT/'results/FUSION_ANNUAL_GATES.json',params)
 rows=[]
 for m in MARKETS:
  f=readcsv(ROOT/f'inputs/{m}_MEAN3_SCORES.csv.gz');out=readcsv(ROOT/f'results/{m}_SCORES.csv.gz');c=panel[panel.market.eq(m)].set_index('date').sort_index();lag=c[CONTEXT].shift(1)
  for v in FUSION_VARIANTS:
   for stage in ['CURRENT','SMOOTH','FUSION']:out[v+'_'+stage]=np.nan
  for d,g in f.groupby('signal_date'):
   row=c.loc[[d]];active=params.get(str(d.year),{})
   for v in FUSION_VARIANTS:
    name=v[2:].replace('_LAG','');cfg=active.get(name);w=1.;pred=np.nan;adapt=False
    if cfg and cfg['active']:
     inp=row.copy()
     if v.endswith('_LAG'):inp.loc[:,CONTEXT]=lag.loc[[d]].to_numpy()
     if inp[CONTEXT].notna().all(axis=1).iloc[0]:
      pr=predict_gate(cfg['model'],inp);w=float(pr['g'][0]);pred=float(pr['delta'][0]);adapt=True
    out.loc[g.index,v+'_CURRENT']=mix_scores(g.CUM_FIXED_MAPPED,g.CUM_FIT_MAPPED,w)
    rows.append(dict(market=m,date=d,variant=v,g=w,predicted_delta=pred,adaptive=adapt,realized_delta=row.delta.iloc[0],available=row.available.iloc[0],context_source_date=row.context_source_date.iloc[0],recent=row.recent.iloc[0],recent_count=int(row.recent_count.iloc[0])))
  dates=pd.DatetimeIndex(sorted(f.signal_date.unique()));ticks=sorted(f.ticker.unique());di=dates.get_indexer(f.signal_date);ti=pd.Index(ticks).get_indexer(f.ticker)
  mat=lambda col:out.pivot(index='signal_date',columns='ticker',values=col).reindex(index=dates,columns=ticks).to_numpy(float)
  for v in FUSION_VARIANTS:
   sm,fu=compose_current(mat('RETURN'),mat(v+'_CURRENT'));out[v+'_SMOOTH']=sm[di,ti];out[v+'_FUSION']=fu[di,ti]
  out.to_csv(ROOT/f'results/{m}_SCORES.csv.gz',index=False,compression='gzip')
 old=readcsv(ROOT/'results/GATE_TRACE.csv');old=old[~old.variant.str.startswith('F_')]
 pd.concat([old,pd.DataFrame(rows)],ignore_index=True).to_csv(ROOT/'results/GATE_TRACE.csv',index=False)
 pd.DataFrame(aud).to_csv(ROOT/'results/FUSION_GATE_FIT_AUDIT.csv',index=False)
 dump(ROOT/'results/FUSION_GATING_COMPLETE.json',dict(actual_outer_fits=sum(r['active'] for r in aud),inner_fits=sum(r['inner_fits'] for r in aud),extension_post_observation=True))
 print(pd.DataFrame(rows).query('adaptive').groupby(['market','variant']).g.agg(['min','mean','max']).to_string())
if __name__=='__main__':main()
