"""Fit small shared gates, persist every annual fit, then blend actual scores."""
from core import CONTEXT,predict_gate,mix_scores,compose_current
from gating import FEATURE_SETS,fit_year
from io_utils import ROOT,MARKETS,BASE_VARIANTS as VARIANTS,readcsv,dump,sha
import numpy as np,pandas as pd,json

def main():
 parity=json.loads((ROOT/'results/PARENT_PARITY.json').read_text())
 if parity['paths']!=48:raise RuntimeError('All48 parent controls must be verified first')
 p=readcsv(ROOT/'inputs/GATE_PANEL.csv');models={};rows=[]
 for year in range(2022,2027):
  models[str(year)]={}
  for name,features in FEATURE_SETS.items():
   r=fit_year(p,year,features);models[str(year)][name]=r
   dump(ROOT/f'models/{year}_{name}.json',r)
   rows.append(dict(year=year,variant=name,active=r['active'],penalty=r.get('model',{}).get('penalty'),EU=r['counts'].get('EU',0),USA=r['counts'].get('USA',0),inner_fits=len(r.get('inner',[])),max_available=r.get('max_train_available')))
  print('GATE_YEAR',year,[f"{n}:{models[str(year)][n]['active']}" for n in FEATURE_SETS],flush=True)
  dump(ROOT/'results/ANNUAL_GATES.json',models);pd.DataFrame(rows).to_csv(ROOT/'results/GATE_FIT_AUDIT.csv',index=False)
 traces=[]
 for m in MARKETS:
  f=readcsv(ROOT/f'inputs/{m}_MEAN3_SCORES.csv.gz');out=f[['signal_date','ticker','RETURN']].copy();context=p[p.market.eq(m)].sort_values('date').set_index('date');lag=context[CONTEXT].shift(1)
  for v in VARIANTS:
   for stage in ['CURRENT','SMOOTH','FUSION']:out[v+'_'+stage]=np.nan
  for date,g in f.groupby('signal_date',sort=True):
   idx=g.index;row=context.loc[[date]].copy();active=models.get(str(date.year),{})
   for v in VARIANTS:
    info={};dhat=np.nan;adaptive=False
    if v in ['ORIGINAL','CUM_FIXED','CUM_FIT']:
     for stage in ['CURRENT','SMOOTH','FUSION']:out.loc[idx,v+'_'+stage]=g[v+'_'+('MAPPED' if stage=='CURRENT' else stage)].to_numpy()
     if v=='ORIGINAL':continue
     weight=0. if v=='CUM_FIXED' else 1.
    else:
     weight=.5 if v=='HALF' else 1.
     if v!='HALF':
      key='CONTEXT_RECENT' if v=='CONTEXT_RECENT_LAG' else v;r=active.get(key)
      if r and r['active']:
       inp=row.copy()
       if v=='CONTEXT_RECENT_LAG':inp.loc[:,CONTEXT]=lag.loc[[date]].to_numpy()
       if inp[CONTEXT].notna().all(axis=1).iloc[0]:
        pred=predict_gate(r['model'],inp);weight=float(pred['g'][0]);dhat=float(pred['delta'][0]);adaptive=True
     out.loc[idx,v+'_CURRENT']=mix_scores(g.CUM_FIXED_MAPPED,g.CUM_FIT_MAPPED,weight)
    traces.append(dict(market=m,date=date,variant=v,g=weight,predicted_delta=dhat,adaptive=adaptive,realized_delta=row.delta.iloc[0],available=row.available.iloc[0],context_source_date=row.context_source_date.iloc[0],recent=row.recent.iloc[0],recent_count=int(row.recent_count.iloc[0])))
  dates=pd.DatetimeIndex(sorted(f.signal_date.unique()));ticks=sorted(f.ticker.unique());di=dates.get_indexer(f.signal_date);ti=pd.Index(ticks).get_indexer(f.ticker)
  mat=lambda c:out.pivot(index='signal_date',columns='ticker',values=c).reindex(index=dates,columns=ticks).to_numpy(float)
  for v in VARIANTS:
   if v in ['ORIGINAL','CUM_FIXED','CUM_FIT']:continue
   sm,fu=compose_current(mat('RETURN'),mat(v+'_CURRENT'));out[v+'_SMOOTH']=sm[di,ti];out[v+'_FUSION']=fu[di,ti]
  out.to_csv(ROOT/f'results/{m}_SCORES.csv.gz',index=False,compression='gzip')
 tr=pd.DataFrame(traces);tr.to_csv(ROOT/'results/GATE_TRACE.csv',index=False)
 dump(ROOT/'results/GATING_COMPLETE.json',dict(annual_records=len(rows),actual_outer_fits=sum(x['active'] for x in rows),inner_fits=sum(x['inner_fits'] for x in rows),base_models_refitted=0,first_adaptive_signal=str(tr.loc[tr.adaptive,'date'].min()),panel_sha256=sha(ROOT/'inputs/GATE_PANEL.csv'),sources={p.name:sha(p) for p in (ROOT/'src').glob('*.py')}))
 print(tr[tr.adaptive].groupby(['market','variant']).g.agg(['size','min','mean','max']).to_string())
if __name__=='__main__':main()
