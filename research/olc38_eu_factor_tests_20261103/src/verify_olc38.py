#!/usr/bin/env python3
"""Independent source/decision/return/accounting check for EU-only OLC38."""
import argparse,zipfile,io,hashlib,sys,json
from pathlib import Path
import numpy as np,pandas as pd

REQUIRED={
 'OLC19':'3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540',
 'OLC32':'aef33c5c1aac60a944f7cf767b7ee637eb4ca254710b431c95b5f13a67fd6b8d'}
HMINI='6b4d59814dfeaab8fac415498755cdad664e76b20a424eb0e0aac6568a771f8d'
PROXIES=['EXSA.DE','SXR8.DE','SXRV.DE','QDVE.DE','EXX1.DE','VVSM.DE','EXV5.DE','EXV9.DE']

def filehash(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def extract(z,suffix):
 m=[s for s in z.namelist() if s.endswith(suffix)];assert len(m)==1,(suffix,m)
 return z.read(m[0])
def load(a,b):
 compact=(Path(a).resolve()==Path(b).resolve() and filehash(a)==HMINI)
 if not compact:
  assert filehash(a)==REQUIRED['OLC19']
  assert filehash(b)==REQUIRED['OLC32']
 with zipfile.ZipFile(a) as z:
  x=np.load(io.BytesIO(extract(z,'/inputs/EU_STATE_HALF.npz')),allow_pickle=False)
  dates=pd.DatetimeIndex(x['dates']);names=x['tickers'].astype(str);prices=x['O'];observed=x['observed']
  pf=np.load(io.BytesIO(extract(z,'/results/paths/EU_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz')),allow_pickle=False)
  nav=np.r_[1.,pf['nav'][:-1]]
 with zipfile.ZipFile(b) as z:
  cal=pd.read_csv(io.BytesIO(extract(z,'results/REPAIRED_CALENDAR_AUDIT.csv')))
  lab=pd.read_csv(io.BytesIO(extract(z,'results/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz')),compression='gzip')
 ix={t:int(np.where(names==t)[0][0]) for t in PROXIES}
 return dates,prices,observed,nav,ix,cal[cal.market=='EU'].copy(),lab[lab.market=='EU'].copy()

def independently_rank(d,price,obs,ix,s):
 ans=[]
 for t,j in ix.items():
  k=np.flatnonzero((d<=s)&obs[:,j]&np.isfinite(price[:,j])&(price[:,j]>0))
  if len(k)<127 or (s-d[k[-1]]).days>7:continue
  a,b=k[-1],k[-127]
  ans.append((t,float(np.log(price[a,j]/price[b,j])),str(d[a].date()),str(d[b].date())))
 return sorted(ans,key=lambda x:(-x[1],x[0]))

def verify(A,B,R):
 d,O,obs,nav,ix,cal,labels=load(A,B)
 R=Path(R)
 csv=pd.read_csv(R/'F3_SIGNAL_DECISIONS_AND_PAYOFFS.csv');csv['signal_date']=pd.to_datetime(csv.signal_date)
 f1=pd.read_csv(R/'F1_CLONE_MATCHED_DAILY.csv');wts=pd.read_csv(R/'F1_STYLE_TRAIN_BY_YEAR.csv')
 f2=pd.read_csv(R/'F2_HOLDINGS_COVERAGE_BY_YEAR.csv');hold=pd.read_csv(R/'F2_NAMED_HOLDINGS_BY_YEAR.csv')
 sums=json.loads((R/'OLC38_RESULTS.json').read_text())
 assert csv.signal_date.is_unique and len(csv)==66 and len(csv[(csv.year<=2024)])==48
 cal['signal_date']=pd.to_datetime(cal.signal_date)
 matched=csv[['signal_date','entry_date','exit_date']].merge(cal,on='signal_date',suffixes=('','_src'),validate='one_to_one')
 assert len(matched)==len(csv) and (matched.entry_date==matched.entry_date_src).all() and (matched.exit_date==matched.exit_date_src).all()
 assert set(f1.columns)>={'strategy','F0_FIVE','F1_EIGHT_ASOF'}
 # OLC37 baseline 5-factors is reproduced using matching dates and same fee conventions
 olc37_end=172.67628617245995 # Verified fixed source value; OLC37 report 2026-11-03
 five_end=float(f1.F0_FIVE.iloc[-1]);assert abs(five_end-olc37_end)<1e-9,(olc37_end,five_end)
 assert len(f1)==1021
 # Direct independent F0 and expanded source-date strict cutoff checks; 2021 7 and 2022+ 8 factors
 for _,row in wts.iterrows():
  y=int(row.year);assert pd.Timestamp(row.last_fit_open)<pd.Timestamp(f'{y}-01-01')
  assert int(row.n_train_paired)==252
  assert int(row.n_factor_proxies)==(5 if row.clone=='F0_FIVE' else (7 if y==2021 else 8))
  weights=np.array([row['weight_'+t] for t in PROXIES])
  assert np.all(weights>=-1e-10) and weights.sum()<1+1e-9
 assert np.array_equal(pd.to_datetime(f1.date),d[(d>='2021-01-04')&(d<='2024-12-30')&obs[:,list(ix.values())].all(axis=1)])
 refs=np.asarray([ix[t] for t in PROXIES])
 obsidx=d.get_indexer(pd.to_datetime(f1.date));source_index=100*nav[obsidx]/nav[obsidx[0]]
 assert np.max(np.abs(f1.strategy.to_numpy()-source_index))<1e-8
 # Verify exact O2O economic labels for each factor on source model and standalone OLC32 if valid.
 max_label_diff=0.; verified_labels=0;lag_viol=0;max_proxy_diff=0.
 # Independent economic re-accounting with half L1 against previous holdings and cash, for two strategies.
 prev={'leader':None,'EW':None};wealth={'leader':100.,'EW':100.};max_delta=0.
 for _,row in csv.iterrows():
  s=pd.Timestamp(row.signal_date);start=pd.Timestamp(row.entry_date);end=pd.Timestamp(row.exit_date)
  rank=independently_rank(d,O,obs,ix,s)
  assert row.rank_top1==rank[0][0] and row.rank_top2==rank[1][0]
  assert row.rank_table==';'.join(x[0] for x in rank)
  assert row.source_date_top1==rank[0][2] and row.source_date_top2==rank[1][2]
  assert len(rank)==row.n_asof_factors
  assert pd.Timestamp(row.source_date_top1)<=s
  # Future perturbation for selected timestamps is prohibited from changing any ranking
  if s.year==2023 and s.month in (1,6,12):
   d_mask=d>s
   o2=O.copy();b2=obs.copy();o2[d_mask]*=5.123;b2[d_mask]=False
   alt=independently_rank(d,o2,b2,ix,s)
   assert rank==alt
  if end<=start:
   assert not bool(row.payoff_valid) and row.invalid_reason=='terminal_no_future_label'
  if not bool(row.payoff_valid):
   prev={'leader':None,'EW':None};continue
  ia=d.get_loc(start);ib=d.get_loc(end)
  names=[x[0] for x in rank];returns={t:O[ib,ix[t]]/O[ia,ix[t]]-1 for t in names}
  assert all(obs[ia,ix[t]] and obs[ib,ix[t]] for t in names)
  for t in names:
   key=labels[(labels.signal_date==str(s.date()))&(labels.ticker==t)]
   if len(key)==1 and bool(key.iloc[0].eligible_label):
    label=1e4*np.log(O[ib,ix[t]]/O[ia,ix[t]])
    max_label_diff=max(max_label_diff,abs(label-float(key.iloc[0].r_o2o_bp)));verified_labels+=1
  for label,target in [('leader',{row.rank_top1:.5,row.rank_top2:.5}),('EW',{t:1/len(names) for t in names})]:
   w=np.array([target.get(t,0.) for t in PROXIES]);prior=np.r_[prev[label],1-sum(prev[label])] if prev[label] is not None else np.r_[np.zeros(8),1]
   cost=.001*.5*np.sum(np.abs(np.r_[w,0]-prior));gross=1+sum(w[ix_list]*returns[t] for ix_list,t in enumerate(PROXIES) if t in returns)
   nret=(1-cost)*gross-1
   drift=np.array([w[k]*(1+returns.get(t,0))/gross for k,t in enumerate(PROXIES)])
   prev[label]=drift;wealth[label]*=(1+nret)
   target_value=float(row.leader_month_net_pct if label=='leader' else row.EW_month_net_pct)
   max_proxy_diff=max(max_proxy_diff,abs(nret*100-target_value))
   assert abs(wealth[label]-float(row.leader_NAV_proxy if label=='leader' else row.EW_NAV_proxy))<1e-8
  calc_diff=1e4*(np.log1p(row.leader_month_net_pct/100)-np.log1p(row.EW_month_net_pct/100))
  max_delta=max(max_delta,abs(calc_diff-row.log_delta_bp))
 assert max_label_diff<1e-6,(max_label_diff,verified_labels)
 assert max_proxy_diff<1e-9 and max_delta<1e-9,(max_delta,max_proxy_diff)
 # F2 coverage arithmetic, and no double counting named proxies in held weights
 for _,row in f2.iterrows():
  assert abs(row.mean_primary_NAV_pct-row.mean_eight_direct_NAV_pct-row.mean_unmapped_primary_NAV_pct)<1e-10
  by=hold[hold.year==row.year]
  assert abs(by.mean_NAV_weight_pct.sum()-row.mean_eight_direct_NAV_pct)<1e-8
 assert not sums['USA_changed'] and not sums['production_changed'] and sums['GateA']=='FAIL'
 assert sums['F3_leadership']['main_gate']=='FAIL'
 boot=pd.read_csv(R/'F3_BOOTSTRAP_BLOCK6.csv')
 lo,hi=np.quantile(boot.mean_delta_bp,[.025,.975]);assert len(boot)==4000
 assert np.allclose([lo,hi],sums['F3_leadership']['paired_6month_bootstrap_95pct_mean_bp'],rtol=0,atol=1e-9)
 return {'source_checks':'PASS','clone5_reproduces_OLC37_to_1e-9':True,'max_label_vs_OLC32_bp':max_label_diff,
 'number_factor_month_labels_checked':verified_labels,'max_monthly_simple_return_reconcile_pct':max_proxy_diff,
 'max_monthly_log_delta_reconcile_bp':max_delta,'audit_dates_and_causality':'PASS','cloned_portfolio_NAV':'PASS',
 'independent_F2_coverage':'PASS','F3_bootstrap_draws':len(boot),'olc38_holdings_lookthrough_pit_certified':False,'conclusion':'STOP_NO_PROMOTION'}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--olc19');ap.add_argument('--olc32');ap.add_argument('--compact-source');ap.add_argument('--results',required=True);a=ap.parse_args()
 if a.compact_source:
  assert a.olc19 is None and a.olc32 is None;src19=src32=a.compact_source
 else:
  assert a.olc19 and a.olc32;src19,src32=a.olc19,a.olc32
 v=verify(src19,src32,a.results);Path(a.results,'OLC38_INDEPENDENT_VERIFICATION.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
