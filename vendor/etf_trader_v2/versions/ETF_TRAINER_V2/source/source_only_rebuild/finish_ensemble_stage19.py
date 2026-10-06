#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse,hashlib,json,os,sys,time
import numpy as np
import pandas as pd
ROOT=Path(os.environ.get('ETF_TRAINER_V2_CAMPAIGN_ROOT','/mnt/data/stage19_sourceonly_rebuild')).resolve(); sys.path.insert(0,str(ROOT/'src'))
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.source_only.baskets import build_canonical_baskets,BASKET_SEED
from etf_trader.ma3 import producer,ddfirst,v6,highcagr24
from etf_trader.ma3.ensemble import fit_ensemble_producer,ET_KW,XGB_KW,XGB_ALPHA

def sha256(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def metrics(E,mask):
 lr=np.diff(np.log(np.column_stack([np.ones(E.shape[0]),E])),axis=1)[:,mask]; r=np.expm1(lr); n=lr.shape[1]
 c=np.expm1(lr.sum(axis=1)*252/n); eq=np.exp(np.cumsum(lr,axis=1)); pk=np.maximum.accumulate(np.column_stack([np.ones(E.shape[0]),eq]),axis=1)[:,1:]
 dd=(eq/pk-1).min(axis=1); sd=r.std(axis=1,ddof=1); sh=np.divide(r.mean(axis=1)*np.sqrt(252),sd,out=np.zeros_like(sd),where=sd>0)
 return {'cagr':float(c.mean()),'median_cagr':float(np.median(c)),'p10_cagr':float(np.quantile(c,.1)),'p05_cagr':float(np.quantile(c,.05)),'maxdd':float(dd.mean()),'p10dd':float(np.quantile(dd,.1)),'p05dd':float(np.quantile(dd,.05)),'worst':float(dd.min()),'sharpe':float(sh.mean())}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--end-year',type=int,default=2026,help='historical parity default; extend only for prospective validation')
 ap.add_argument('--n-jobs',type=int,default=2)
 ap.add_argument('--prospective',action='store_true',help='label this rebuild as prospective gate input, not as a historical certification')
 a=ap.parse_args()
 if a.end_year<2017: raise ValueError('--end-year must be >= 2017')
 raw=ROOT/'raw_ticker_csv'; out=ROOT/'out'/'ensemble_source_only_fresh'; out.mkdir(parents=True,exist_ok=True); tit=ROOT/'out'/'titanium'; panel_dir=ROOT/'out'/'ma3_panel'
 for req in [tit/'TIT_R_SOURCE_ONLY.csv',panel_dir/'RAW_FEATURE_PANEL.pkl',panel_dir/'CLUSTER_SOURCE_DATE_AUDIT.csv']:
  if not req.exists(): raise FileNotFoundError(req)
 mats,cats,raw_manifest=load_ticker_csv_folder(raw); tickers=list(map(str,mats['Open'].columns)); ti={t:i for i,t in enumerate(tickers)}
 universe=pd.read_csv(raw/'universe.csv'); membership=build_canonical_baskets(universe,tickers)
 basket_path=out/'GENERATED_CANONICAL_BASKETS.csv'; membership.to_csv(basket_path,index=False); basket_sha=sha256(basket_path)
 expected='36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e'
 if basket_sha!=expected: raise RuntimeError((basket_sha,expected))
 import glob
 tit_ok=True; tit_audit_records=0
 for f in sorted(glob.glob(str(tit/'annual_models/fit_audit_*.json'))):
  for r in json.load(open(f)):
   tit_audit_records+=1; tit_ok &= pd.Timestamp(r['max_exit']) < pd.Timestamp(r['fit_date'])
 ca=pd.read_csv(panel_dir/'CLUSTER_SOURCE_DATE_AUDIT.csv'); cluster_ok=bool((pd.to_datetime(ca.window_end)<=pd.to_datetime(ca.signal_date)).all()) and bool(ca.max_source_date_le_signal.all()) and bool(ca.matching_used_only_previous_membership.all())
 if not tit_ok or not cluster_ok: raise RuntimeError(f'upstream causality failed tit={tit_ok} cluster={cluster_ok}')
 tit_df=pd.read_csv(tit/'TIT_R_SOURCE_ONLY.csv',parse_dates=['signal_date','entry_date','exit_date']); panel=pd.read_pickle(panel_dir/'RAW_FEATURE_PANEL.pkl')
 t0=time.time(); p=fit_ensemble_producer(panel,tit_df,tickers,n_jobs=a.n_jobs,end_year=a.end_year); fit_s=time.time()-t0
 p.predictions.to_csv(out/'ENSEMBLE_TAIL_OOS.csv',index=False); p.fit_audit.to_csv(out/'ENSEMBLE_FIT_AUDIT.csv',index=False)
 if not bool(p.fit_audit.maturity_ok.all()): raise RuntimeError('ensemble maturity failure')
 BM,BOK=producer.basket_arrays(membership,tickers,n_baskets=500)
 Odf=mats['Open'].reindex(columns=tickers).ffill().bfill(); Ldf=mats['Low'].reindex(columns=tickers).ffill().bfill().reindex(Odf.index); Cdf=mats['Close'].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)
 end=pd.Timestamp(p.calendar.exit_date.max()); start=pd.Timestamp(p.calendar.entry_date.min()); Odf=Odf.loc[:end];Ldf=Ldf.reindex(Odf.index);Cdf=Cdf.reindex(Odf.index); st=int(Odf.index.get_loc(start));en=int(Odf.index.get_loc(end));ds=Odf.index[st:en+1]
 gross=np.asarray(ddfirst.sync_c95_m75_gross(Cdf)[st:en+1],float); ex=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
 O,L,C,PC,gap,ud1,uneg,UH,SA=[ex[k][st:en+1] for k in ['O','L','C','PC','gap','ud1','uneg','UH','SA']]
 a=producer.allocations_from_score(p.score,p.calendar,ds,BM,BOK,continuous=True); noalt=np.full_like(a.d1,-1,np.int16); ones=np.ones(len(ds),float)
 Er,Tr,_,_=v6.simulate_with_alt(a.d1,a.d2,a.weight1,O,L,C,PC,gap,ud1,uneg,UH,SA,ti['BIL'],ti['SHV'],ones,noalt,False,.001)
 s6=v6.build_v6_state(Cdf.loc[ds,tickers],a.d1,a.d2,a.weight1,gross)
 Ed,Td,_,_=v6.simulate_with_alt(a.d1,a.d2,a.weight1,O,L,C,PC,gap,ud1,uneg,UH,SA,ti['BIL'],ti['SHV'],gross,noalt,False,.001)
 Ev,Tv,_,_=v6.simulate_with_alt(a.d1,a.d2,a.weight1,O,L,C,PC,gap,ud1,uneg,UH,SA,ti['BIL'],ti['SHV'],gross,s6.alt_idx,True,.001)
 gh,w=highcagr24.apply_highcagr24(gross,a.weight1,a.margin); E24,T24,X24,Aw24=v6.simulate_with_alt(a.d1,a.d2,w,O,L,C,PC,gap,ud1,uneg,UH,SA,ti['BIL'],ti['SHV'],gh,s6.alt_idx,True,.001)
 periods={'pre2020':ds<pd.Timestamp('2020-01-01'),'2020_2022':(ds>=pd.Timestamp('2020-01-01'))&(ds<pd.Timestamp('2023-01-01')),'dev_daily':ds<pd.Timestamp('2023-01-01'),'holdout_daily':ds>=pd.Timestamp('2023-01-01'),'full':np.ones(len(ds),bool)}
 result={'status':'SOURCE_ONLY_ENSEMBLE_REBUILD_COMPLETE','certification':('PROSPECTIVE_REBUILD_INPUT_TO_GATE' if a.prospective else 'CLEAN_CURRENT_RAW_PASS'),'selection':{'et':'selected on 2011-2016 walk-forward','xgb':'selected on 2011-2016 engine benchmark','alpha_xgb':{'value':XGB_ALPHA,'selected_on':'2017-2022 validation only'},'holdout':'2023-2026 not used for parameter selection'},'producer':{'target':'0.45*r21^1.5 + 0.35*r42^1.5 + 0.20*r63^1.5','extra_trees':ET_KW,'xgb':XGB_KW,'alpha_xgb':XGB_ALPHA,'tail_smoothing':[.4,.3,.3],'tail_power':1.10,'base_tail':[.475,.525]},'fit_seconds':fit_s,'calendar':{'start':str(ds.min().date()),'end':str(ds.max().date()),'days':int(len(ds))},'metrics':{},'turnover_ann':{'raw':float(Tr.mean()*252),'ddfirst':float(Td.mean()*252),'v6':float(Tv.mean()*252),'highcagr24':float(T24.mean()*252)},'contract':{'productive_inputs':['raw ETF OHLCV per-ticker CSV','universe/category metadata','repository source'],'historical_scores_consumed':False,'historical_paths_consumed':False,'historical_cluster_membership_consumed':False,'historical_basket_membership_consumed':False,'basket_membership_generated_from_source':True,'basket_seed':BASKET_SEED,'basket_sha256':basket_sha,'cluster_seed':26072026,'titanium_maturity_safe':bool(tit_ok),'titanium_audit_records':tit_audit_records,'cluster_source_causal':cluster_ok,'ensemble_maturity_safe':bool(p.fit_audit.maturity_ok.all())},'raw_manifest':raw_manifest,'source_hashes':{str(x.relative_to(ROOT)):sha256(x) for x in [ROOT/'src/etf_trader/source_only/baskets.py',ROOT/'src/etf_trader/ma3/ensemble.py',ROOT/'src/etf_trader/ma3/producer.py',ROOT/'src/etf_trader/ma3/ddfirst.py',ROOT/'src/etf_trader/ma3/v6.py',ROOT/'src/etf_trader/ma3/highcagr24.py',ROOT/'scripts/build_tit_r_source_only.py',ROOT/'scripts/build_ma3_panel_source_only.py',Path(__file__).resolve()]}}
 for name,mask in periods.items(): result['metrics'][name]={'raw':metrics(Er,mask),'ddfirst':metrics(Ed,mask),'v6':metrics(Ev,mask),'highcagr24':metrics(E24,mask)}
 (out/'RESULT.json').write_text(json.dumps(result,indent=2,default=str)+'\n'); np.savez_compressed(out/'PATH.npz',dates=ds.values,equity=E24,turnover=T24,exposure=X24,alt_weight=Aw24,d1=a.d1,d2=a.d2,wg=w,margin=a.margin,global_gross=gh,alt_idx=s6.alt_idx,tickers=np.asarray(tickers,dtype=object))
 print(json.dumps({'fit_seconds':fit_s,'full':result['metrics']['full'],'holdout':result['metrics']['holdout_daily'],'turnover_ann':result['turnover_ann'],'contract':result['contract']},indent=2))
if __name__=='__main__': main()
