#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

F={'D1':.15022713687299,'D2':.2264479079604543,'DEV':.1861726630584223,'HOLD':.2760542274772661,'FULL':.2165406437471759}
P={'D1':(2017,2019),'D2':(2020,2022),'DEV':(2017,2022),'HOLD':(2023,9999),'FULL':(2017,9999)}

def mod(path,name='x'):
 s=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def mats(r):
 o={}
 for k in ['Open','High','Low','Close','Volume']:
  x=pd.read_parquet(r/f'{k.upper()}.parquet');x.index=pd.to_datetime(x.index).tz_localize(None);x.columns=x.columns.astype(str).str.upper();o[k]=x.apply(pd.to_numeric,errors='coerce')
 c=sorted(set.intersection(*[set(x.columns) for x in o.values()]));return {k:v.reindex(columns=c) for k,v in o.items()}

def baskets(p):
 d=pd.read_csv(p);return [tuple(g.sort_values('ticker').ticker.astype(str)) for _,g in d.groupby('basket',sort=True)]

def period_score(EB,idx,e):
 y=pd.DatetimeIndex(idx).year; rows=[]
 for p,(lo,hi) in P.items():
  pos=np.flatnonzero((y>=lo)&(y<=hi)); sl=slice(pos[0],pos[-1]+1); ix=pd.DatetimeIndex(idx)[sl]; vals=[]
  for q in EB:
   z=np.asarray(q[sl],float); z=z/z[0]; vals.append(e.metrics(z,ix)[0])
  c=float(np.mean(vals)); rows.append({'period':p,'cagr':c,'gap_pp':100*(c-F[p])})
 return rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--v1-root',required=True);ap.add_argument('--fixture-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
 vr=Path(a.v1_root); rr=vr/'results'; fr=Path(a.fixture_root); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
 e=mod(vr/'source'/'exact_execution_v1.py','execv1'); base=mod(fr/'code'/'source_feature_engine.py','base')
 feats=list(base.TAIL_FEATURES); tail=pd.read_parquet(rr/'TAILMIX_LABELED.parquet');tail.signal_date=pd.to_datetime(tail.signal_date);tail.exit_date_63=pd.to_datetime(tail.exit_date_63)
 pred0=pd.read_parquet(rr/'OOS_TICKER_SCORES.parquet');pred0.signal_date=pd.to_datetime(pred0.signal_date)
 years=sorted(pred0.signal_date.dt.year.unique());parts=[]; audits=[]
 for year in years:
  cutoff=pd.Timestamp(year,1,1); valid=tail[feats].notna().sum(axis=1)>=12
  tr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()&valid]
  te=tail[(tail.signal_date.dt.year==year)&valid]
  if tr.empty or te.empty: continue
  m=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.0));m.fit(tr[feats],tr.y_tailmix)
  q=te[['signal_date','ticker']].copy();q['tail_raw_valid']=m.predict(te[feats]);q['tail_rank_valid']=q.groupby('signal_date').tail_raw_valid.rank(pct=True,method='average');parts.append(q)
  audits.append({'year':year,'train_rows':len(tr),'test_rows':len(te),'valid_train_frac':float(valid[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()].mean()),'valid_test_frac':float(valid[tail.signal_date.dt.year==year].mean())})
 tv=pd.concat(parts,ignore_index=True);p=pred0.merge(tv,on=['signal_date','ticker'],how='left');p['tail_raw']=p.tail_raw_valid;p['tail_rank']=p.tail_rank_valid
 p['titanium_score_pre_macro']=.70*p.compact_rank+.30*p.tail_rank
 cond=(p.macro_category==p.top_macro)&(p.macro_gap_z>=.75)&(p.titanium_score_pre_macro>=.80);p['macro_bonus']=np.where(cond,.15,0.);p['titanium_score']=p.titanium_score_pre_macro+p.macro_bonus;p['TIT_R']=p.groupby('signal_date').titanium_score.rank(pct=True,method='average')
 opp=pd.read_parquet(rr/'OOS_OPPORTUNITY_SCORES.parquet');opp.signal_date=pd.to_datetime(opp.signal_date);cl=pd.read_csv(rr/'DYNAMIC_CLUSTER_MEMBERSHIP.csv',parse_dates=['signal_date']);cal=pd.read_csv(rr/'MONTHLY_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date']);M=mats(rr);bs=baskets(rr/'BASKET_MEMBERSHIP_500.csv')
 idx,EB,*_=e.simulate_all(bs,p,opp,cl,M,cal);scores=period_score(EB,idx,e)
 ck=p[p.signal_date.eq(pd.Timestamp('2026-06-30'))].sort_values(['TIT_R','titanium_score'],ascending=False).head(10)[['ticker','compact_rank','tail_rank','titanium_score_pre_macro','TIT_R']].to_dict(orient='records')
 pd.DataFrame(audits).to_csv(out/'TAIL_VALIDITY_AUDIT.csv',index=False);pd.DataFrame(scores).to_csv(out/'TAIL_VALIDITY_SCORECARD.csv',index=False);p.to_parquet(out/'OOS_TICKER_SCORES_TAIL_VALIDITY.parquet',index=False)
 j={'scores':scores,'checkpoint':ck,'target_checkpoint':['USO','PALL']};(out/'TAIL_VALIDITY_DIAGNOSTIC.json').write_text(json.dumps(j,indent=2));print(json.dumps(j,indent=2))
if __name__=='__main__':main()
