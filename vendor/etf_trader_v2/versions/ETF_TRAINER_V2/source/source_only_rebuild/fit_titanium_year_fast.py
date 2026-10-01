from pathlib import Path
import argparse,sys,json,os,time,tempfile,subprocess,shutil
import numpy as np, pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
ROOT=Path('/mnt/data/stage19_sourceonly_rebuild');sys.path.insert(0,str(ROOT/'src'))
from etf_trader.source_only import kernel as k
from etf_trader.source_only.features import GROUPS
from etf_trader.source_only.raw_io import load_ticker_csv_folder

def main(year):
 raw=ROOT/'raw_ticker_csv'; feat=ROOT/'out'/'titanium_features'; out=ROOT/'out'/'titanium'/'annual_models';out.mkdir(parents=True,exist_ok=True)
 mats,cats,_=load_ticker_csv_folder(raw);cols=list(mats['Close'].columns);k.ALL_TICKERS=sorted(cols);k.TICKER_CATEGORY=cats;k.CATEGORY_TICKERS={c:sorted([t for t in cols if cats[t]==c]) for c in sorted(set(cats.values()))}
 compact=pd.read_pickle(feat/'compact.pkl');tail=pd.read_pickle(feat/'tail.pkl');macro=pd.read_pickle(feat/'macro.pkl');extra=pd.read_pickle(feat/'extra.pkl');mfeatures=json.loads((feat/'mfeatures.json').read_text())
 frame=compact.merge(extra,on=['signal_date','ticker'],validate='one_to_one')
 cutoff=pd.Timestamp(year,1,1);valid=frame[k.F2D_FEATURES].notna().sum(axis=1)>=30
 tr=frame[(frame.signal_date<cutoff)&(frame.exit_date_21<cutoff)&frame.target_rank_pct.notna()&valid].sort_values(['signal_date','ticker'])
 te=frame[(frame.signal_date.dt.year==year)&valid].sort_values(['signal_date','ticker'])
 if te.empty: raise RuntimeError('no test rows')
 if tr.signal_date.nunique()<60: raise RuntimeError('insufficient mature history')
 o=te[['signal_date','ticker','entry_date','exit_date']].copy(); audits=[]
 params=dict(k.COMPACT_PARAMS);rounds=int(params.pop('n_estimators'));params.pop('n_jobs',None); params_json=json.dumps(params,separators=(',',':'),sort_keys=True)
 worker=ROOT/'src/etf_trader/source_only/_xgb_worker.py'; yrdir=out/'fast_scratch'/str(year); shutil.rmtree(yrdir,ignore_errors=True);yrdir.mkdir(parents=True)
 Xte=te[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan).to_numpy()
 for horizon in (21,63):
  train=frame[(frame.signal_date<cutoff)&(frame[f'exit_date_{horizon}']<cutoff)&frame[f'target_rank_{horizon}'].notna()&valid].sort_values(['signal_date','ticker'])
  Xtr=train[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan).to_numpy();y=(train[f'target_rank_{horizon}']*100).round().astype(int).to_numpy();groups=train.groupby('signal_date',sort=True).size().to_numpy()
  data=yrdir/f'data_{horizon}.npz';np.savez(data,Xtr=Xtr,Xte=Xte,y=y,groups=groups)
  ps=[]
  t=time.time()
  for seed in k.COMPACT_SEEDS:
   pred=yrdir/f'pred_{horizon}_{int(seed)}.npy'
   cmd=[sys.executable,str(worker),'--data',str(data),'--seed',str(int(seed)),'--threads','2','--rounds',str(rounds),'--params-json',params_json,'--output',str(pred)]
   ps.append(subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True,env={**os.environ,'PYTHONPATH':str(ROOT/'src')}))
  for p in ps:
   p.wait()
   if p.returncode: raise RuntimeError(f'worker failed {p.returncode}')
  pp=[np.load(yrdir/f'pred_{horizon}_{int(seed)}.npy') for seed in k.COMPACT_SEEDS];o[f'compact{horizon}']=np.mean(pp,axis=0)
  audits.append({'year':year,'model':f'compact{horizon}','train_rows':len(train),'max_exit':str(train[f'exit_date_{horizon}'].max()),'fit_date':str(cutoff),'mode':'isolated_parallel_workers_fastexec','workers':3,'threads_per_worker':2,'elapsed':time.time()-t})
 for group,features in {**GROUPS,'all':sum(GROUPS.values(),[])}.items():
  model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=100.));model.fit(tr[features],tr.target_rank_pct);o[group]=model.predict(te[features])
 tv=tail[k.TAIL_FEATURES].notna().sum(axis=1)>=12;ttr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()&tv];tte=tail[(tail.signal_date.dt.year==year)&tv]
 model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.));model.fit(ttr[k.TAIL_FEATURES],ttr.y_tailmix);t=tte[['signal_date','ticker']].copy();t['tail']=model.predict(tte[k.TAIL_FEATURES]);o=o.merge(t,on=['signal_date','ticker'],validate='one_to_one')
 mtr=macro[(macro.signal_date<cutoff)&(macro.label_exit_date_63<cutoff)&macro.target_rank.notna()];mte=macro[macro.signal_date.dt.year==year];model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.));model.fit(mtr[mfeatures],mtr.target_rank);q=mte[['signal_date','macro_category']].copy();q['raw']=model.predict(mte[mfeatures]);q['z']=q.groupby('signal_date').raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12));records=[]
 for dt,g in q.groupby('signal_date'):
  g=g.sort_values(['z','macro_category'],ascending=[False,True]);records.append({'signal_date':dt,'top_macro':g.iloc[0].macro_category,'macro_gap':g.iloc[0].z-g.iloc[1].z})
 o=o.merge(pd.DataFrame(records),on='signal_date');o['macro_category']=o.ticker.map(k.TICKER_CATEGORY)
 audits += [{'year':year,'model':'tail','max_exit':str(ttr.exit_date_63.max()),'fit_date':str(cutoff)},{'year':year,'model':'macro','max_exit':str(mtr.label_exit_date_63.max()),'fit_date':str(cutoff)}]
 o.to_csv(out/f'scores_{year}.csv',index=False);(out/f'fit_audit_{year}.json').write_text(json.dumps(audits,indent=2));print(json.dumps({'year':year,'rows':len(o),'audits':audits[:2]},indent=2),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('year',type=int);a=ap.parse_args();main(a.year)
