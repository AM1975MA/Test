from pathlib import Path
import sys,json,time
import numpy as np,pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
ROOT=Path('/mnt/data/stage19_sourceonly_rebuild');sys.path.insert(0,str(ROOT/'src'))
from etf_trader.source_only import kernel as k
from etf_trader.source_only.features import GROUPS
from etf_trader.source_only.models import variants
from etf_trader.source_only.raw_io import load_ticker_csv_folder
raw=ROOT/'raw_ticker_csv';feat=ROOT/'out'/'titanium_features';xdir=ROOT/'out'/'titanium'/'xgb_data';out=ROOT/'out'/'titanium';am=out/'annual_models';am.mkdir(parents=True,exist_ok=True)
mats,cats,_=load_ticker_csv_folder(raw);cols=list(mats['Close'].columns);k.ALL_TICKERS=sorted(cols);k.TICKER_CATEGORY=cats;k.CATEGORY_TICKERS={c:sorted([t for t in cols if cats[t]==c]) for c in sorted(set(cats.values()))}
compact=pd.read_pickle(feat/'compact.pkl');tail=pd.read_pickle(feat/'tail.pkl');macro=pd.read_pickle(feat/'macro.pkl');extra=pd.read_pickle(feat/'extra.pkl');mfeatures=json.loads((feat/'mfeatures.json').read_text());frame=compact.merge(extra,on=['signal_date','ticker'],validate='one_to_one');valid=frame[k.F2D_FEATURES].notna().sum(axis=1)>=30
outs=[];elig=[]
for year in range(2017,2027):
 t0=time.time();cut=pd.Timestamp(year,1,1);tr=frame[(frame.signal_date<cut)&(frame.exit_date_21<cut)&frame.target_rank_pct.notna()&valid].sort_values(['signal_date','ticker']);te=frame[(frame.signal_date.dt.year==year)&valid].sort_values(['signal_date','ticker']);o=te[['signal_date','ticker','entry_date','exit_date']].copy(); audits=[]
 for h in (21,63):
  train=frame[(frame.signal_date<cut)&(frame[f'exit_date_{h}']<cut)&frame[f'target_rank_{h}'].notna()&valid].sort_values(['signal_date','ticker'])
  pp=[np.load(xdir/str(year)/f'pred_{h}_{s}.npy') for s in k.COMPACT_SEEDS];o[f'compact{h}']=np.mean(pp,axis=0);audits.append({'year':year,'model':f'compact{h}','train_rows':len(train),'max_exit':str(train[f'exit_date_{h}'].max()),'fit_date':str(cut),'mode':'fresh_raw_same_model_external_worker_orchestration','workers':'isolated','threads_per_worker':5})
 for group,features in {**GROUPS,'all':sum(GROUPS.values(),[])}.items():
  m=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=100.));m.fit(tr[features],tr.target_rank_pct);o[group]=m.predict(te[features])
 tv=tail[k.TAIL_FEATURES].notna().sum(axis=1)>=12;ttr=tail[(tail.signal_date<cut)&(tail.exit_date_63<cut)&tail.y_tailmix.notna()&tv];tte=tail[(tail.signal_date.dt.year==year)&tv];m=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.));m.fit(ttr[k.TAIL_FEATURES],ttr.y_tailmix);tt=tte[['signal_date','ticker']].copy();tt['tail']=m.predict(tte[k.TAIL_FEATURES]);o=o.merge(tt,on=['signal_date','ticker'],validate='one_to_one')
 mtr=macro[(macro.signal_date<cut)&(macro.label_exit_date_63<cut)&macro.target_rank.notna()];mte=macro[macro.signal_date.dt.year==year];m=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.));m.fit(mtr[mfeatures],mtr.target_rank);q=mte[['signal_date','macro_category']].copy();q['raw']=m.predict(mte[mfeatures]);q['z']=q.groupby('signal_date').raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12)); rec=[]
 for dt,g in q.groupby('signal_date'):
  g=g.sort_values(['z','macro_category'],ascending=[False,True]);rec.append({'signal_date':dt,'top_macro':g.iloc[0].macro_category,'macro_gap':g.iloc[0].z-g.iloc[1].z})
 o=o.merge(pd.DataFrame(rec),on='signal_date');o['macro_category']=o.ticker.map(k.TICKER_CATEGORY);audits += [{'year':year,'model':'tail','max_exit':str(ttr.exit_date_63.max()),'fit_date':str(cut)},{'year':year,'model':'macro','max_exit':str(mtr.label_exit_date_63.max()),'fit_date':str(cut)}]
 o.to_csv(am/f'scores_{year}.csv',index=False);(am/f'fit_audit_{year}.json').write_text(json.dumps(audits,indent=2));outs.append(o);elig.append({'year':year,'status':'FIT','train_signal_dates':int(tr.signal_date.nunique())});print('FINALIZED',year,len(o),'sec',round(time.time()-t0,2),flush=True)
(am/'eligibility_audit.json').write_text(json.dumps(elig,indent=2))
pred=pd.concat(outs,ignore_index=True);pred=pred[(pred.signal_date>='2017-01-31')&(pred.signal_date<='2026-06-30')].copy();base=variants(pred)['baseline'].rename(columns={'score':'TIT_R'});calendar=pred[['signal_date','ticker','entry_date','exit_date']].drop_duplicates(['signal_date','ticker']);panel=base.merge(calendar,on=['signal_date','ticker'],how='inner',validate='one_to_one');panel=panel[['signal_date','entry_date','exit_date','ticker','TIT_R']].sort_values(['signal_date','ticker']);panel.to_csv(out/'TIT_R_SOURCE_ONLY.csv',index=False);print(json.dumps({'status':'FRESH_RAW_TIT_R_COMPLETE','rows':len(panel),'signal_dates':int(panel.signal_date.nunique()),'tickers':int(panel.ticker.nunique())},indent=2))
