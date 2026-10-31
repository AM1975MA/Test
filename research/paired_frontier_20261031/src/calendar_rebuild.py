"""CL01: explicit as-of, native-session feature reconstruction from frozen raw bytes.
Original raw feature formulas, regenerated cross sections/clusters, no stale trade quote.
This is a new calendar/source version, NOT assumed parity with old scores.
"""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
from pathlib import Path
import sys,inspect,json,warnings,hashlib,time
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT/'legacy'
SRC=OLD/'source/research/tail-only-and-allocation-ablation-20261017';VENDOR=SRC/'vendor/etf_trader_v2'
sys.path[:0]=[str(SRC),str(VENDOR/'src')]
from etf_trader.source_only import kernel as k
from etf_trader.source_only.a4_cluster_destination import build_persistent_membership,DEFAULT_SEED
from etf_trader.ma3.producer import FEATURES_42
from frontier_helpers import asof_snapshot
OUT=ROOT/'results/calendar';OUT.mkdir(exist_ok=True,parents=True)
FIELDS=['Open','High','Low','Close','Volume']

def raw_frames(market):
 if market=='USA':
  folder=OLD/'raw/_repeat1';u=pd.read_csv(folder/'universe.csv');folder_prices=folder
 else:
  folder=OLD/'inputs/eu/source_v4/input/EU165_SPECIALISTS_20261029';u=pd.read_csv(folder/'input/universe.csv');folder_prices=folder/'prices'
 frames={}
 for t in u.ticker:
  f=pd.read_csv(folder_prices/f'{t}.csv',index_col=0,parse_dates=True,float_precision='round_trip').sort_index().loc[:'2026-07-01']
  good=np.isfinite(f[['Open','High','Low','Close']]).all(axis=1)&(f[['Open','High','Low','Close']]>0).all(axis=1)
  frames[t]=f.loc[good,FIELDS]
 return frames,u

def source_functions(benchmark):
 src=inspect.getsource(k.build_features).split('    bases=')[0]+'    return compact\n'
 original="mkt=ret['SPY'] if 'SPY' in ret else ret.median(axis=1)"
 assert src.count(original)==1
 src=src.replace(original,"mkt=BENCHMARK.reindex(C.index,method='ffill').pct_change(fill_method=None)")
 ns=dict(k.__dict__,BENCHMARK=benchmark);exec(compile(src,'<native-session-compact125>','exec'),ns)
 p=(VENDOR/'scripts/build_ma3_panel_source_only.py').read_text()
 start=p.index('    close=mats["Close"].astype(float)');end=p.index('    locmap=',start)
 body=p[start:end];fs='def hybrid_raw(mats):\n    cols=list(mats["Close"].columns)\n'+body+'    return F\n'
 nh={'np':np,'pd':pd};exec(compile(fs,'<native-session-hybrid-source-formulas>','exec'),nh)
 return ns['build_features'],nh['hybrid_raw'],src,fs

def observed_labels(frames,master,dates):
 records=[]
 for sd in dates:
  pos=master.searchsorted(sd,side='right')
  if pos>=len(master):continue
  scheduled=master[pos]
  for ticker,f in frames.items():
   ep=f.index.searchsorted(scheduled);rec={'signal_date':sd,'ticker':ticker,'entry_date':pd.NaT}
   if ep>=len(f) or (f.index[ep]-scheduled).days>5:
    for h in [21,42,63]:rec[f'exit_date_{h}']=pd.NaT;rec[f'fwd_ret_{h}']=np.nan
   else:
    entry=f.index[ep];rec['entry_date']=entry
    for h in [21,42,63]:
     # Horizon kept on common session grid; first executable opening at target exit.
     xp=pos+h
     if xp>=len(master):xd=pd.NaT;val=np.nan
     else:
      target=master[xp];xi=f.index.searchsorted(target)
      if xi>=len(f) or (f.index[xi]-target).days>5:xd=pd.NaT;val=np.nan
      else:xd=f.index[xi];val=f.Open.iloc[xi]/f.Open.iloc[ep]-1.
     rec[f'exit_date_{h}']=xd;rec[f'fwd_ret_{h}']=val
   records.append(rec)
 return pd.DataFrame(records)

def build(market):
 start=time.time();frames,u=raw_frames(market);tickers=u.ticker.tolist()
 C=pd.DataFrame({t:f.Close for t,f in frames.items()}).sort_index();master=C.index
 dates=pd.DatetimeIndex(pd.Series(master,index=master).groupby(master.to_period('M')).last().values)
 dates=dates[dates<='2026-06-30']
 # Market index only uses current or earlier observations; no test-label eligibility.
 if market=='USA':benchmark=C['SPY'].dropna()
 else:benchmark=(1+C.ffill(limit=3).pct_change(fill_method=None).median(axis=1).fillna(0.)).cumprod()
 compact_func,hy_func,src,hs=source_functions(benchmark)
 (OUT/'COMPACT_SOURCE.py').write_text(src);(OUT/'HYBRID_RAW_SOURCE.py').write_text(hs)
 comparts=[];hyparts=[];age=[]
 with warnings.catch_warnings():
  warnings.simplefilter('ignore')
  for count,(t,f) in enumerate(frames.items()):
   mats={fld:f[[fld]].rename(columns={fld:t}) for fld in FIELDS}
   comp=compact_func(mats)
   # Native snapshot dates are month ends of this ticker's own observations.
   native=pd.DataFrame({name:x[t] for name,x in comp.items()})
   snap,srcdates=asof_snapshot(native,dates,5);snap['signal_date']=dates;snap['ticker']=t
   localpos=f.index.searchsorted(dates,side='right')-1
   # Freshness based on actual quote, not individual feature NaN; no forward filling internal feature NaNs.
   exists=localpos>=0;safe=np.maximum(localpos,0);fresh=exists&((dates-f.index[safe]).days<=5)
   lastsrc=f.index[safe]
   for name in comp:
    # Retain original NaN semantics in raw features, even if earlier month had a finite number.
    snap[name]=native[name].reindex(lastsrc).to_numpy()
   snap.loc[~fresh,list(comp)]=np.nan
   snap['source_date']=pd.to_datetime(np.where(fresh,lastsrc.values,np.datetime64('NaT')))
   comparts.append(snap)
   F=hy_func(mats);rec=pd.DataFrame({'signal_date':dates,'ticker':t,'source_date':snap.source_date.values})
   for name,x in F.items():rec[name]=x[t].reindex(lastsrc).to_numpy()
   logs=np.log(f.Close).to_numpy();lr=np.diff(logs,prepend=np.nan)
   for w in [21,63]:
    slope=np.full(len(dates),np.nan);autoc=np.full(len(dates),np.nan)
    xc=np.arange(w)-(w-1)/2.;den=np.sum(xc**2)
    for j,ip in enumerate(localpos):
     if not fresh[j] or ip-w+1<0:continue
     a=logs[ip-w+1:ip+1];slope[j]=np.sum((a-a.mean())*xc)/den
     r=lr[ip-w+1:ip+1]
     if np.isfinite(r).all() and np.std(r[1:])>0 and np.std(r[:-1])>0:autoc[j]=np.corrcoef(r[1:],r[:-1])[0,1]
    rec[f'slope_{w}']=slope;rec[f'autocorr1_{w}']=autoc
   dom=np.full(len(dates),np.nan)
   for j,ip in enumerate(localpos):
    if not fresh[j] or ip<64:continue
    a=lr[ip-63:ip+1];a=a-np.nanmean(a);powr=abs(np.fft.rfft(np.nan_to_num(a)))[1:]**2
    if powr.sum()>0:dom[j]=powr.max()/powr.sum()
   rec['dominant_energy64']=dom
   numeric=[n for n in rec if n not in ['signal_date','ticker','source_date']];rec.loc[~fresh,numeric]=np.nan
   hyparts.append(rec)
   age.extend({'ticker':t,'signal_date':str(d.date()),'source_date':str(lastsrc[j].date()) if fresh[j] else None,'age_days':int((d-lastsrc[j]).days) if fresh[j] else None} for j,d in enumerate(dates))
   if (count+1)%40==0:print('FEATURES',market,count+1,round(time.time()-start),flush=True)
 compact=pd.concat(comparts,ignore_index=True);compact=compact.replace([np.inf,-np.inf],np.nan)
 bases=[n for n in k.F2D_FEATURES if not n.endswith('_pct') and not n.endswith('_dev')]
 for n in bases:
  if n+'_pct' in k.F2D_FEATURES:compact[n+'_pct']=compact.groupby('signal_date')[n].rank(pct=True)
  if n+'_dev' in k.F2D_FEATURES:
   wide=compact.pivot(index='signal_date',columns='ticker',values=n)
   dev=k.cs_robust_dev(wide).stack(dropna=False).rename(n+'_dev').reset_index()
   compact=compact.merge(dev,on=['signal_date','ticker'],validate='one_to_one')
 compact['eligible']=compact[k.F2D_FEATURES].notna().sum(axis=1)>=30
 labels=observed_labels(frames,master,dates)
 compact=compact.merge(labels,on=['signal_date','ticker'],how='left',validate='one_to_one')
 for h in [21,42,63]:compact[f'target_rank_{h}']=compact[f'fwd_ret_{h}'].where(compact.eligible).groupby(compact.signal_date).rank(pct=True)
 compact['target_rank_pct']=compact.target_rank_21
 compact.to_pickle(OUT/f'{market}_COMPACT.pkl')
 # Persistent clusters see only current eligibility and historical prices, never future label availability.
 categories=dict(zip(u.ticker,u.macro_category));categories={t:('C05_BONDS_CASH_CREDIT' if ('BOND' in str(c) or str(c)=='SOVEREIGN_EUR') else c) for t,c in categories.items()}
 eligible=compact[compact.eligible][['signal_date','ticker']].copy()
 # Membership uses only ticker identities; validator requires label columns, deliberately blank.
 for horizon in [42,63]:
  eligible[f'fwd_ret_{horizon}']=np.nan;eligible[f'exit_date_{horizon}']=pd.NaT
 with warnings.catch_warnings():
  warnings.simplefilter('ignore');clusters=build_persistent_membership(C.ffill(limit=3),eligible,dates,categories,seed=DEFAULT_SEED)
 clusters.membership.to_csv(OUT/f'{market}_CLUSTERS.csv',index=False);clusters.source_audit.to_csv(OUT/f'{market}_CLUSTER_AUDIT.csv',index=False)
 panel=pd.concat(hyparts,ignore_index=True).merge(clusters.membership,on=['signal_date','ticker'],how='inner',validate='one_to_one')
 panel=panel.replace([np.inf,-np.inf],np.nan)
 num=[c for c in panel if c not in ['signal_date','ticker','source_date','cluster_id']]
 for c in num:panel[c+'_rank']=panel.groupby('signal_date')[c].rank(pct=True,method='average')
 for c in ['ret_21','ret_63','ret_126','vol_63','acc_5_21','eff_63','signed_volume21']:
  panel[f'cluster_{c}_mean']=panel.groupby(['signal_date','cluster_id'])[c].transform('mean');panel[f'{c}_vs_cluster']=panel[c]-panel[f'cluster_{c}_mean']
  panel[f'{c}_cluster_rank']=panel.groupby(['signal_date','cluster_id'])[c].rank(pct=True);panel[f'cluster_{c}_univ_rank']=panel.groupby('signal_date')[f'cluster_{c}_mean'].rank(pct=True)
 for h in [21,63]:panel[f'cluster_breadth{h}']=panel.groupby(['signal_date','cluster_id'])[f'ret_{h}'].transform(lambda x:(x>0).mean())
 context=[c for c in panel if (c.startswith('cluster_') or c.endswith('_vs_cluster') or c.endswith('_cluster_rank')) and pd.api.types.is_numeric_dtype(panel[c])]
 for c in context:
  if c+'_rank' not in panel:panel[c+'_rank']=panel.groupby('signal_date')[c].rank(pct=True)
 panel=panel.merge(labels,on=['signal_date','ticker'],how='left',validate='one_to_one')
 for h in [21,42,63]:panel[f'target_rank_{h}']=panel.groupby('signal_date')[f'fwd_ret_{h}'].rank(pct=True)
 assert not set(FEATURES_42)-set(panel)
 panel.to_pickle(OUT/f'{market}_HYBRID.pkl');pd.DataFrame(age).to_csv(OUT/f'{market}_FEATURE_DATES.csv.gz',index=False,compression='gzip')
 cal=pd.DataFrame({'signal_date':dates});cal['entry_date']=[master[master.searchsorted(d,side='right')] for d in dates];cal['exit_date']=cal.entry_date.shift(-1);cal.loc[cal.index[-1],'exit_date']=master[-1]
 cal.to_csv(OUT/f'{market}_CALENDAR.csv',index=False)
 C.to_pickle(OUT/f'{market}_CLOSE.pkl');pd.DataFrame({t:f.Open for t,f in frames.items()}).to_pickle(OUT/f'{market}_OPEN.pkl')
 stats={'market':market,'compact_rows':len(compact),'hybrid_rows':len(panel),'n_tickers':len(tickers),'signal_dates':len(dates),'hybrid_signal_dates':int(panel.signal_date.nunique()),'source_semantics':'native observed sessions; last feature within5calendar days; native raw formulas and source persistent clusters; no future entry used for eligibility','source_sha256':hashlib.sha256(src.encode()).hexdigest(),'hybrid_source_sha256':hashlib.sha256(hs.encode()).hexdigest(),'elapsed':time.time()-start}
 (OUT/f'{market}_BUILD.json').write_text(json.dumps(stats,indent=2));print('BUILD_DONE',stats,flush=True)
if __name__=='__main__':build(sys.argv[1])
