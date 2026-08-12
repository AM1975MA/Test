#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
F={'D1':.15022713687299,'D2':.2264479079604543,'DEV':.1861726630584223,'HOLD':.2760542274772661,'FULL':.2165406437471759};P={'D1':(2017,2019),'D2':(2020,2022),'DEV':(2017,2022),'HOLD':(2023,9999),'FULL':(2017,9999)}
def mod(path):
 s=importlib.util.spec_from_file_location('x',str(path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def mats(r):
 o={}
 for k in ['Open','High','Low','Close','Volume']:
  x=pd.read_parquet(r/f'{k.upper()}.parquet');x.index=pd.to_datetime(x.index).tz_localize(None);x.columns=x.columns.astype(str).str.upper();o[k]=x.apply(pd.to_numeric,errors='coerce')
 c=sorted(set.intersection(*[set(x.columns) for x in o.values()]));return {k:v.reindex(columns=c) for k,v in o.items()}
def baskets(p):
 d=pd.read_csv(p);return [tuple(g.sort_values('ticker').ticker.astype(str)) for _,g in d.groupby('basket',sort=True)]
def score(EB,idx,e):
 y=pd.DatetimeIndex(idx).year;rows=[]
 for p,(lo,hi) in P.items():
  pos=np.flatnonzero((y>=lo)&(y<=hi));sl=slice(pos[0],pos[-1]+1);ix=pd.DatetimeIndex(idx)[sl];vals=[]
  for q in EB:
   z=np.asarray(q[sl],float);z=z/z[0];vals.append(e.metrics(z,ix)[0])
  g=float(np.mean(vals));rows.append({'period':p,'cagr':g,'gap_pp':100*(g-F[p])})
 return rows
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.root);r=root/'results';out=Path(a.output);out.mkdir(parents=True,exist_ok=True);e=mod(root/'source'/'exact_execution_v1.py');M=mats(r);pred0=pd.read_parquet(r/'OOS_TICKER_SCORES.parquet');pred0.signal_date=pd.to_datetime(pred0.signal_date);opp=pd.read_parquet(r/'OOS_OPPORTUNITY_SCORES.parquet');opp.signal_date=pd.to_datetime(opp.signal_date);cl=pd.read_csv(r/'DYNAMIC_CLUSTER_MEMBERSHIP.csv',parse_dates=['signal_date']);cal=pd.read_csv(r/'MONTHLY_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date']);bs=baskets(r/'BASKET_MEMBERSHIP_500.csv');allrows=[];checks={}
 for gate in ['TAIL30','TAIL_R']:
  for margin in ['TIT_R','RAW_SCORE']:
   p=pred0.copy();cond=(p.macro_category==p.top_macro)&(p.macro_gap_z>=.75)&((p.titanium_score_pre_macro>=.80) if gate=='TAIL30' else (p.tail_rank>=.80));p['macro_bonus']=np.where(cond,.15,0.);p['titanium_score']=p.titanium_score_pre_macro+p.macro_bonus;p['TIT_R_TRUE']=p.groupby('signal_date').titanium_score.rank(pct=True,method='average');p['TIT_R']=p.TIT_R_TRUE if margin=='TIT_R' else p.titanium_score
   idx,EB,ED,ER,*_=e.simulate_all(bs,p,opp,cl,M,cal);name=f'{gate}__{margin}';rr=score(EB,idx,e)
   for x in rr:x['variant']=name
   allrows+=rr
   g=p[p.signal_date.eq(pd.Timestamp('2026-06-30'))].sort_values(['TIT_R','ticker'],ascending=[False,True]).head(5);checks[name]=g[['ticker','titanium_score_pre_macro','tail_rank','macro_bonus','titanium_score','TIT_R_TRUE','TIT_R']].to_dict(orient='records')
 d=pd.DataFrame(allrows);d.to_csv(out/'COMPOSITION_ABLATION.csv',index=False);j={'scorecards':allrows,'checkpoints':checks};(out/'COMPOSITION_ABLATION.json').write_text(json.dumps(j,indent=2));print(json.dumps(j,indent=2))
if __name__=='__main__':main()
