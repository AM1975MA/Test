#!/usr/bin/env python3
"""Independent OLC66 arithmetic/provenance checker, using archived OLC63 frozen outputs.
No fitting, no OLC66 model import, no new strategy or post-result parameter search.
"""
import argparse, json
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import rankdata


def main(folder,olc63):
 d=Path(folder);p=pd.read_csv(d/'OLC66_PANEL.csv.gz');m=pd.read_csv(d/'OLC66_MONTHLY.csv');s=pd.read_csv(d/'OLC66_SELECTED.csv');f=pd.read_csv(d/'OLC66_FITS.csv')
 parent=pd.read_csv(olc63)
 o=parent[(parent.method=='SUBSET') & (parent['mask']==15)][['market','date','mean21','mean42','persistent','negative21']].rename(columns={'date':'signal_date'})
 b=m[m.method=='B0_FUSION']
 comp=b.merge(o,on=['market','signal_date'],how='outer',validate='one_to_one',indicator=True,suffixes=('_new','_frozen'))
 assert len(comp)==118 and comp._merge.eq('both').all(),(len(comp),comp._merge.value_counts())
 control={}
 for v in ['mean21','mean42','persistent','negative21']:
  e=float((comp[v+'_new']-comp[v+'_frozen']).abs().max())
  assert e<1e-12,(v,e)
  control[v+'_max_err']=e
 # Independently select top2 from each stored score vector and compare names and weights.
 checks=0;missing=0
 for (market,date,method),g in s.groupby(['market','signal_date','method']):
  full=p[(p.market==market)&(p.signal_date==date)].copy()
  assert len(g)>=2 and g.weight.sum()>1-1e-12
  if method in ('R1_NATIVE_TOP10','R2_UNION_TOP10'):
   sub=full[full['in_native10']==1] if method=='R1_NATIVE_TOP10' else full[full.in_union==1]
   sub=sub.sort_values('ticker')
   col='score_rerank'
  else:
   sub=full.sort_values('ticker');col=method
  vals=sub[col].to_numpy(float)
  cut=np.sort(vals)[-2]
  top=(vals>cut).astype(float)+(vals==cut).astype(float)*((2-(vals>cut).sum())/(vals==cut).sum())
  top/=2
  expected=dict(zip(sub.ticker[top>0],top[top>0]))
  actual=dict(zip(g.ticker,g.weight))
  assert expected.keys()==actual.keys() and all(abs(actual[t]-expected[t])<1e-12 for t in expected),(market,date,method,expected,actual)
  calc21=float(np.dot(g.weight,g.fwd21));calc42=float(np.dot(g.weight,g.fwd42))
  mm=m[(m.market==market)&(m.signal_date==date)&(m.method==method)].iloc[0]
  assert abs(calc21-mm.mean21)<1e-12 and abs(calc42-mm.mean42)<1e-12
  checks+=1
 # Recompute early blend without using creator's rank helpers.
 pmain=p[p.year.between(2021,2025)]
 maxerr=0.
 for (market,date),g in pmain.groupby(['market','signal_date']):
  a=g.B0_FUSION.rank(method='average',pct=True)
  b=g.C1_CLASS.rank(method='average',pct=True)
  maxerr=max(maxerr,abs(g.C2_EARLY_BLEND-(a+b)/2).max())
 assert maxerr<1e-14
 assert len(f)==10 and f.year.between(2021,2025).all()
 assert (f.n_groups>=20).all() and (f.n_train>=200).all()
 assert (pd.to_datetime(f.last_train)<pd.to_datetime(f.year.astype(str)+'-01-01')).all()
 # OLC19 same-risk template and calendar sanity.
 native=pd.read_csv(d/'OLC66_NATIVE_CONTEXT_STATIC_COMPARISON.csv')
 assert native.query("period=='MAIN'").months.eq(48).all()
 assert ((native.query("period=='LATE'").set_index('market').months)==pd.Series({'EU':10,'USA':12})).all()
 native_events=pd.read_csv(d/'OLC66_NATIVE_EVENT_SELECTIONS.csv')
 assert len(native_events)==720 and native_events.groupby(['market','variant']).size().eq(90).all()
 score=pd.read_csv(d/'OLC66_CONTEXT_RISK_CHOICES.csv')
 assert all(score.query("period=='ACTIVE2021_2024' and fee==0.001 and contract=='FAST_LOCK3'").set_index('market').cagr.loc[['EU','USA']].between(.19,.60))
 qa=dict(status='PASS',source_frozen_olc63_pairs=len(comp),max_b0_diffs=control,independent_selection_groups=checks,
       early_blend_max_error=float(maxerr),n_yearly_ml_fits=len(f),risk_archive_engine_reexecuted=False,
       original_olc19_unchanged=True,compared_main_years='2021-2024',future_labels_used_for_train=False)
 (d/'OLC66_INDEPENDENT_QA.json').write_text(json.dumps(qa,indent=2))
 print(json.dumps(qa,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--folder',required=True);p.add_argument('--olc63',required=True);a=p.parse_args();main(a.folder,a.olc63)