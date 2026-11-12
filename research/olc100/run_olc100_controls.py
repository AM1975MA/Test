#!/usr/bin/env python3
"""OLC100: replay the six 2026-11-12 frozen layers on historic, already-mined data.

This is an integration/parity smoke test ONLY. The 2019--Jul 2026 outcomes are
known and cannot count as a prospective holdout. No new signals are generated.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

EXPECTED = {
 "OLC19_Rischio_Rientro_Checkpoint_20261102.zip":"3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540",
 "OLC56_TESTS_20261106_VERIFICATI.zip":"f22b92a5c4b5024d6f8afef6504b794e1f46ff53ffa87adfaa8f3a2e0e3e2573",
 "OLC67_Strategia_ETF_Verificata.zip":"dbfb2cec587fa7b1a118209856d474236707692b6f7ed68fa99c1c27df9661c4",
 "OLC98_Model_Review_Completa_20261112_VERIFICATO.zip":"85a38f82946186cdc393982542cb012818f85f33a42489db7f17e5cbb002fa83",
 "OLC99_Economic_Top10_Allocazione_20261112_VERIFICATO.zip":"0659c1d91c233851b2380f54f442a376704308e07a5d026cf1f3b38d8c768672",
}
ARMS = {
 "B_BASE":("CONTEXT","HALF","IMMEDIATE","FAST_LOCK3"),
 "C_CANDIDATE":("CONTEXT","MINVAR63","DELAY3","FAST_LOCK3"),
 "D_SELECTION":("ORIGINAL","HALF","IMMEDIATE","FAST_LOCK3"),
 "D_ALLOCATION":("CONTEXT","MINVAR63","IMMEDIATE","FAST_LOCK3"),
 "D_TIMING":("CONTEXT","HALF","DELAY3","FAST_LOCK3"),
 "D_PROTECTION":("CONTEXT","HALF","IMMEDIATE","BASE"),
}
CONTRASTS = {
 "TOP2_CONTEXT_vs_ORIGINAL":("B_BASE","D_SELECTION"),
 "ALLOCATION_MINVAR_vs_HALF_IMMEDIATE":("D_ALLOCATION","B_BASE"),
 "ALLOCATION_MINVAR_vs_HALF_DELAY3":("C_CANDIDATE","D_TIMING"),
 "TIMING_DELAY3_vs_IMMEDIATE_HALF":("D_TIMING","B_BASE"),
 "TIMING_DELAY3_vs_IMMEDIATE_MINVAR":("C_CANDIDATE","D_ALLOCATION"),
 "PROTECTION_FASTLOCK3_vs_BASE":("B_BASE","D_PROTECTION"),
 "INTEGRATED_CANDIDATE_vs_BASE":("C_CANDIDATE","B_BASE"),
}
ACCOUNTING_ARRAYS=['nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace']

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for x in iter(lambda:f.read(1024*1024),b''):h.update(x)
 return h.hexdigest()

def data_path(root,market,selection):
 return root/'native'/'olc19_combined_risk_20261102'/'restore'/'olc18_execution_20261102'/'inputs'/f'{market}_{selection}.npz'

def as_dict(npz_path):
 with np.load(npz_path,allow_pickle=False) as d:
  return {k:v.copy() for k,v in d.items()}

def frozen_weight_check(q,df,ids):
 """Independent exact reconstruction of OLC56 63-session covariance, as of k-1."""
 C=q['C'];obs=np.asarray(q.get('observed',np.isfinite(C)&(C>0)),dtype=bool)
 err=[];empty=0
 for j,k in enumerate(ids):
  k=int(k);a,b=int(q['d1'][0,k]),int(q['d2'][0,k]); w=0.5
  if k>=64 and a!=b and min(a,b)>=0:
   c=C[k-64:k][:,[a,b]];o=obs[k-64:k][:,[a,b]]
   v=np.all(o[1:] & o[:-1],axis=1) & np.all(np.isfinite(c[1:]) & np.isfinite(c[:-1]),axis=1) & np.all((c[1:]>0)&(c[:-1]>0),axis=1)
   if v.sum()>=int(np.ceil(.8*63)):
    x=np.log(c[1:][v]/c[:-1][v]);cov=np.cov(x.T,ddof=1)
    v1,v2,c12=float(cov[0,0]),float(cov[1,1]),float(cov[0,1]);den=v1+v2-2*c12
    if den>1e-13 and min(v1,v2)>1e-15:w=float(np.clip((v2-c12)/den,.25,.75))
   else:empty+=1
  else:empty+=1
  target=float(df.iloc[j]['weight__B1_MINVAR63_CAP25']);err.append(abs(target-w))
 assert max(err)<1e-10,('frozen MinVar weight mismatch',max(err))
 return {'events':len(err),'max_abs_error':max(err),'fallback_50_50_count':int((df['weight__B1_MINVAR63_CAP25']==.5).sum()),'missing_lookback_events':empty}

def apply_weights(q,ids,df):
 z={k:v for k,v in q.items()};z['weights']=q['weights'].copy()
 for j,k in enumerate(ids):
  end=int(ids[j+1]) if j+1<len(ids) else len(q['dates'])
  z['weights'][0,k:end]=float(df.iloc[j]['weight__B1_MINVAR63_CAP25'])
 return z

def paired_ci(differences,seed,n_boot=3000):
 """Descriptive historical monthly 6-block circular bootstrap, NOT OOS inference."""
 n=len(differences);x=np.asarray(differences,float);g=np.random.default_rng(seed)
 assert n>=12
 size=6;counts=int(np.ceil(n/size));vals=np.empty(n_boot)
 for j in range(n_boot):
  starts=g.integers(0,n,size=counts)
  ids=np.concatenate([(np.arange(s,s+size)%n) for s in starts])[:n]
  vals[j]=float(x[ids].mean()*12*100)
 return [float(q) for q in np.quantile(vals,[.025,.975])]

def replay(args):
 archive=Path(args.archives)
 computed={}
 for name,expected in EXPECTED.items():
  file=archive/name;assert file.is_file(),('archive missing',str(file))
  actual=sha(file);assert actual==expected,('archive SHA mismatch',name,actual)
  computed[name]=actual
 root=Path(args.root)
 n=root/'native'/'olc19_combined_risk_20261102'
 p=n/'restore'/'olc18_execution_20261102'
 sys.path[:0]=[str(n/'src'),str(p/'parent_archive'/'parent'/'olc16_contextual_rank_20261102'/'src')]
 from combined_engine import _impl
 from portfolio_metrics_parent import metrics
 out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 score=[];dailies=[];monthlies=[];weights=[];parities={};wchecks={}
 refpath=root.parent/'OLC67'/'results'/'OLC67_SCORECARD.csv'
 assert refpath.is_file(),str(refpath)
 refscore=pd.read_csv(refpath)
 # OLC67 previously run same 8-cell factorial. Compare its principal two arms.
 for m in ['EU','USA']:
  raw_context=as_dict(data_path(root,m,'TOP2_CONTEXT_REVALUE'))
  raw_original=as_dict(data_path(root,m,'ORIGINAL'))
  assert np.array_equal(raw_context['events'],raw_original['events'])
  for key in ['dates','tickers','O','L','C','PC','gap','g','gross','UH','SA','ud1','uneg']:
   assert np.array_equal(raw_context[key],raw_original[key]),(m,key)
  ids=np.flatnonzero(raw_context['events']);assert len(ids)==90
  assert str(pd.Timestamp(raw_context['dates'][-1]).date())=='2026-07-01'
  df=pd.read_csv(root.parent/'OLC56_ROBUST_20261106'/'results'/f'{m}_DECISIONS.csv')
  assert len(df)==len(ids) and np.array_equal(df.event_index.to_numpy(),ids)
  assert df.ticker1.tolist()==raw_context['tickers'][raw_context['d1'][0,ids]].tolist()
  assert df.ticker2.tolist()==raw_context['tickers'][raw_context['d2'][0,ids]].tolist()
  assert np.array_equal(raw_context['weights'],np.full(raw_context['weights'].shape,.5))
  wchecks[m]=frozen_weight_check(raw_context,df,ids)
  for j,k in enumerate(ids):
   weights.append({'market':m,'signal_date':df.iloc[j].entry_date,'top1':df.iloc[j].ticker1,'top2':df.iloc[j].ticker2,'w_minvar63':float(df.iloc[j]['weight__B1_MINVAR63_CAP25']),'w_half':0.5})
  for arm,(s,a,t,protect) in ARMS.items():
   qq=raw_original if s=='ORIGINAL' else raw_context
   ev=qq['events'];base={k:v for k,v in qq.items() if k!='events'}
   if a=='MINVAR63':base=apply_weights(base,ids,df)
   for fee in [.001,.003]:
    for friction in [.001,.005]:
     r=_impl(base,ev,policy='IMMEDIATE' if t=='IMMEDIATE' else 'DELAY',
         fraction=1 if t=='IMMEDIATE' else 3,fee=fee,exposure_timing='PREVIOUS',
         stop_timing='NOW',stop_friction=friction,ordinary_alarm=False,
         fast_stop=protect=='FAST_LOCK3',lock_days=3 if protect=='FAST_LOCK3' else 0)
     ratios=r['nav'][:-1]/r['ledger'][:-1,0]
     assert np.isfinite(ratios).all() and (ratios>0).all()
     logr=np.log(ratios)
     assert np.max(np.abs(logr-np.diff(np.log(np.r_[1.,r['nav']]))[:-1]))<1e-10
     dates=pd.to_datetime(base['dates'][1:]);assert len(dates)==len(logr)
     for met in metrics(base,r):
      if met['period'] in ('FULL','ACTIVE2021_2024','2024','2025','2026'):
       score.append({'market':m,'arm':arm,'fee':fee,'stop_friction':friction,**met})
     if fee==.001 and friction==.001:
      dailies.append(pd.DataFrame({'date':dates,'market':m,'arm':arm,'logr':logr}))
      for (year,mon),group in pd.DataFrame({'date':dates,'logr':logr}).groupby([dates.year,dates.month]):
       monthlies.append({'market':m,'arm':arm,'month':f'{year:04d}-{mon:02d}','logr':float(group.logr.sum()),'n_days':len(group)})
      if t=='IMMEDIATE' and a=='HALF' and protect=='FAST_LOCK3':
       ref=n/'results'/'paths'/f'{m}_{"ORIGINAL" if s=="ORIGINAL" else "TOP2_CONTEXT_REVALUE"}_FAST_LOCK3_F10_S10.npz'
       with np.load(ref) as old:
        for col in ACCOUNTING_ARRAYS:assert np.array_equal(r[col],old[col]),(m,arm,col)
       parities[m+'_'+arm]='7/7 exact'
     if friction==.001 and arm in ['B_BASE','C_CANDIDATE','D_TIMING','D_ALLOCATION']:
      old_w='HALF' if a=='HALF' else 'MINVAR63'
      old_sub=refscore[(refscore.market==m)&(refscore.weight==old_w)&(refscore.timing==t)&(refscore.risk==protect)&(np.isclose(refscore.fee,fee))&(refscore.period=='FULL')]
      new_sub=[x for x in metrics(base,r) if x['period']=='FULL']
      assert len(old_sub)==len(new_sub)==1,(m,arm,old_w,t)
      assert abs(float(old_sub.cagr.iloc[0])-float(new_sub[0]['cagr']))<1e-10,(m,arm,'OLC67 CAGR')
      assert abs(float(old_sub.maxdd.iloc[0])-float(new_sub[0]['maxdd']))<1e-10,(m,arm,'OLC67 DD')
  print('HISTORICAL_REPLAYS_PASS',m,flush=True)
 sc=pd.DataFrame(score);dl=pd.concat(dailies,ignore_index=True);mon=pd.DataFrame(monthlies);wt=pd.DataFrame(weights)
 dfpairs=[]
 for m in ['EU','USA']:
  p=mon[mon.market==m].pivot(index='month',columns='arm',values='logr')
  assert len(p)>=85 and p.notna().all().all()
  for contrast,(treat,control) in CONTRASTS.items():
   x=(p[treat]-p[control]).to_numpy()
   ci=paired_ci(x,seed=100112)
   dfpairs.append({'market':m,'contrast':contrast,'months':len(x),
      'annual_log_pp':float(x.mean()*12*100),'bootstrap95_lo_log_pp':ci[0],'bootstrap95_hi_log_pp':ci[1],
      'n_positive_months':int((x>0).sum()),'note':'HISTORICAL_DESCRIPTIVE_NON_OOS'})
 contrasts=pd.DataFrame(dfpairs)
 # Invariant all 24 / all 48 replays of 6 arms x markets x fees x friction are present.
 assert len(sc[(sc.period=='FULL')])==6*2*2*2
 assert len(parities)==4
 qa={'status':'HISTORICAL_REPLAY_PASS_ONLY','forward_outcomes_scored':0,
   'forward_signals_after_2026_07_01':0,'prospective_oos_claim':False,
   'historical_last_open':'2026-07-01','n_full_native_replays':int((sc.period=='FULL').sum()),
   'reference_parity':parities,'olc67_matched_scorecard':'PASS',
   'independent_minvar_reconstruction':wchecks,'archives_sha256_verified':computed,
   'attention':'2019--July 2026 extensively researched: NO OOS inference. USA observed mask missing in native q; EU has 167 price columns including non-eligible auxiliaries. No certified new signals or EU prices.'}
 sc.to_csv(out/'OLC100_HISTORICAL_SCORECARD.csv',index=False)
 dl.to_csv(out/'OLC100_HISTORICAL_DAILY.csv.gz',index=False)
 mon.to_csv(out/'OLC100_HISTORICAL_MONTHLY.csv',index=False)
 wt.to_csv(out/'OLC100_HISTORICAL_WEIGHTS.csv',index=False)
 contrasts.to_csv(out/'OLC100_LAYER_CONTRASTS.csv',index=False)
 (out/'OLC100_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
 print('RUNS',qa['n_full_native_replays'],'PARITY',parities,'MINVAR',wchecks,flush=True)
 print('HISTORICAL_FULL_SCORECARD',flush=True)
 print(sc[(sc.period=='FULL')&(sc.fee==.001)&(sc.stop_friction==.001)][['market','arm','cagr','maxdd']].to_string(index=False),flush=True)
 print('LAYER_CONTRASTS_DESCRIPTIVE',flush=True)
 print(contrasts.to_string(index=False),flush=True)
 return qa

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--archives',default='/mnt/data/frozen_sources')
 ap.add_argument('--root',default='/mnt/data/olc100_workspace/OLC98_Model_Review_20261112')
 ap.add_argument('--out',default='/mnt/data/olc100_package/results')
 args=ap.parse_args();replay(args)
if __name__=='__main__':main()
