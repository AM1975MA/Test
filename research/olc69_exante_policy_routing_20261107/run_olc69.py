#!/usr/bin/env python3
"""OLC69: prequential policy routing, native adaptive single-account OLC19 replay.

Research-only, historical dates 2019--2026 already mined. Frozen protocol on GitHub.
Inputs: original local OLC67 extracted engine and OLC68 pre-signal diagnostic CSV.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

ROOT=Path(__file__).resolve().parent
SRC=ROOT
OLC67=SRC/'OLC67'
RAW=SRC/'OLC68_PRESIGNAL_EVENT_DIAGNOSTIC.csv'
N=OLC67/'native'/'olc19_combined_risk_20261102'
P=N/'restore'/'olc18_execution_20261102'
sys.path.insert(0,str(OLC67))
import run_olc67 as original
from combined_engine import _s as native_source, _fill, _impl as native_impl
from portfolio_metrics_parent import metrics

SOURCE_HASHES={
 'OLC67_Strategia_ETF_Verificata.zip':'dbfb2cec587fa7b1a118209856d474236707692b6f7ed68fa99c1c27df9661c4',
 'OLC68_PRESIGNAL_EVENT_DIAGNOSTIC.csv':'b7911d1346f6d78a19513547fd4b91b8a68a1806b2332f3a95815fcaf2caf330'}
FEATURES=['universe_breadth_63','pair_avg_mom63','pair_prior_mom_weighted_tilt','pair_corr63']
TARGETS={'B':'weightonly_logbp','C':'timingonly_logbp','D':'paired_logbp'}
LABEL='A'
# Predictions need at least +5 expected log-bp to switch off original OLC19.
EDGE_BP=5.0
ALPHA=25.0
MIN_TRAIN=24

def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for data in iter(lambda:f.read(2**20),b''):h.update(data)
 return h.hexdigest()

def patched_engine():
 s=native_source
 substitutes=[
 ("if policy not in ['IMMEDIATE','PARTIAL','TOP4','COHORT2','PHASE','DELAY']:",
  "if policy not in ['IMMEDIATE','PARTIAL','TOP4','COHORT2','PHASE','DELAY','ADAPTIVE']:") ,
 ("if policy=='IMMEDIATE':tar=p", "if policy=='IMMEDIATE' or (policy=='ADAPTIVE' and int(q['adaptive_lag'][k])==1):\n            tar=p;remaining=0"),
 ("elif policy=='DELAY':", "elif policy=='DELAY' or (policy=='ADAPTIVE' and int(q['adaptive_lag'][k])==3):")]
 for old,new in substitutes:
  if s.count(old)!=1:raise AssertionError('Native contract mismatch: '+old)
  s=s.replace(old,new)
 ns={'_fill':_fill}
 exec(compile(s,'<OLC69_OLC19_ADAPTIVE>','exec'),ns)
 return ns['simulate']

def logret(r):
 # Accounting convention exactly OLC19: next valuation opening.
 return np.log(r['nav'][:-1]/r['ledger'][:-1,0])

def make_decisions(df,market):
 data=df[df.market==market].copy().sort_values('signal_month').reset_index(drop=True)
 assert data.signal_month.is_unique and len(data)==82,(market,len(data))
 assert data[FEATURES+list(TARGETS.values())].notna().all().all()
 data['month_period']=pd.PeriodIndex(data.signal_month,freq='M')
 out=[];skill=[]
 for x in data.itertuples(index=False):
  # Exit maturity: exclude previous event's outcome because its next opening
  # is not necessarily known before current opening trade. Training ends t-2.
  sub=data[data.month_period<=x.month_period-2].copy()
  action='A';forecasts={'A':0.,'B':np.nan,'C':np.nan,'D':np.nan}
  if len(sub)>=MIN_TRAIN:
   X_train=sub[FEATURES].to_numpy(dtype=float)
   X_now=data.loc[data.signal_month==x.signal_month,FEATURES].to_numpy(dtype=float)
   for candidate,col in TARGETS.items():
    learner=make_pipeline(StandardScaler(),Ridge(alpha=ALPHA))
    y=sub[col].to_numpy(float)
    learner.fit(X_train,y)
    forecasts[candidate]=float(learner.predict(X_now)[0])
    skill.append({'market':market,'month':x.signal_month,'candidate':candidate,
                  'pred_bp':forecasts[candidate], 'actual_bp':float(getattr(x,col)),
                  'mean_train_bp':float(y.mean()),'train_n':int(len(sub))})
   winner=max(('A','B','C','D'),key=lambda a:(forecasts[a] if np.isfinite(forecasts[a]) else -float('inf')))
   if winner!='A' and forecasts[winner]>EDGE_BP:action=winner
  out.append({'market':market,'month':x.signal_month,'asof':x.feature_asof_date,'action':action,
              'train_n':int(len(sub)),'predict_B_logbp':forecasts['B'],
              'predict_C_logbp':forecasts['C'],'predict_D_logbp':forecasts['D'],
              'actual_B_logbp':float(x.weightonly_logbp),
              'actual_C_logbp':float(x.timingonly_logbp),
              'actual_D_logbp':float(x.paired_logbp),
              'actual_action_logbp':float({'A':0.,'B':x.weightonly_logbp,'C':x.timingonly_logbp,'D':x.paired_logbp}[action]),
              'feature_coverage':float(x.feature_coverage),
              **{f:float(getattr(x,f)) for f in FEATURES}})
 return pd.DataFrame(out),pd.DataFrame(skill)

def apply_actions(m,route):
 q,ev,ids,dec=original.load(m)
 D=len(ev)
 assert len(ids)==90 and np.array_equal(np.flatnonzero(ev),ids)
 z=dict(q);z['weights']=np.array(q['weights'],copy=True);z['adaptive_lag']=np.ones(D,dtype=int)
 ledger=[]
 per_month={r.month:r for r in route.itertuples(index=False)}
 for j,k in enumerate(ids):
  month=str(pd.to_datetime(q['dates'][k]))[:7]
  f=per_month.get(month)
  action=f.action if f is not None else 'A'
  w=float(dec.loc[j,'weight__B1_MINVAR63_CAP25']) if action in ['B','D'] else .5
  lag=3 if action in ['C','D'] else 1
  e=int(ids[j+1]) if j+1<len(ids) else D
  z['weights'][0,k:e]=w
  z['adaptive_lag'][k:e]=lag
  ledger.append(dict(market=m,month=month,action=action,weight1=w,lag=lag,
                     event_index=int(k),last_index=int(e-1),n=int(e-k)))
 return z,ev,pd.DataFrame(ledger),q

def run():
 out=ROOT/'results';out.mkdir(exist_ok=True)
 source=ROOT/'OLC67_Strategia_ETF_Verificata.zip'
 observed={source.name:digest(source),RAW.name:digest(RAW)}
 assert observed==SOURCE_HASHES,(observed,SOURCE_HASHES)
 df=pd.read_csv(RAW)
 assert len(df)==164 and set(df.market)=={'EU','USA'}
 adaptive=patched_engine()
 score=[];annual=[];daily=[];switches=[];skill=[];qa={'source':observed,'native_contract':{},'train_maturity_verified':True}
 for m in ['EU','USA']:
  route,pred=make_decisions(df,m)
  route.to_csv(out/f'OLC69_{m}_PRESIGNAL_ROUTING.csv',index=False)
  skill.append(pred)
  z,events,decision_map,q=apply_actions(m,route)
  switches.append(decision_map)
  # Contract checks vs original original core: immediate and 3-session delay.
  for label,lag in [('IMMEDIATE',1),('DELAY3',3)]:
   control=dict(q);control['adaptive_lag']=np.full(len(events),lag,dtype=int)
   r_orig=native_impl(q,events,policy=('IMMEDIATE' if lag==1 else 'DELAY'),fraction=lag,
                     fee=.001,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=.001,
                     ordinary_alarm=False,fast_stop=True,lock_days=3)
   r_a=adaptive(control,events,policy='ADAPTIVE',fraction=3,
                fee=.001,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=.001,
                ordinary_alarm=False,fast_stop=True,lock_days=3)
   for key in ['nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace']:
    if not np.array_equal(r_a[key],r_orig[key]):
     raise AssertionError('Parity fail '+m+'/'+label+'/'+key)
   qa['native_contract'][f'{m}_{label}']='BITWISE_SEVEN_ARRAYS'
  for fee in [.001,.003]:
   r=adaptive(z,events,policy='ADAPTIVE',fraction=3,fee=fee,
              exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=.001,
              ordinary_alarm=False,fast_stop=True,lock_days=3)
   lr=logret(r);date=pd.to_datetime(q['dates'][1:]);assert len(lr)==len(date)
   for met in metrics(z,r):
    if met['period'] not in ['ACTIVE2021_2024','FULL','2025','2026','CRASH2020']:continue
    score.append(dict(market=m,fee=fee,**met))
    mask=(date>=met['first_valuation'])&(date<=met['last_valuation'])
    assert int(mask.sum())==met['n']
    reconstructed=float(np.expm1(lr[mask].mean()*252))
    assert abs(reconstructed-met['cagr'])<1e-11
   for year in sorted(date.year.unique()):
    ix=date.year==year
    annual.append(dict(market=m,fee=fee,year=int(year),n=int(ix.sum()),
                       annual_return=float(np.expm1(lr[ix].sum()))))
   daily.append(pd.DataFrame({'market':m,'date':date,'fee':fee,'logr':lr}))
  print('ROUTING',m,route.action.value_counts().to_dict(),'forecast skill months',len(pred)//3,flush=True)
 pd.concat(switches).to_csv(out/'OLC69_EVENT_ACTIONS.csv',index=False)
 pd.concat(skill).to_csv(out/'OLC69_FORECAST_SKILL.csv',index=False)
 pd.DataFrame(score).to_csv(out/'OLC69_SCORECARD.csv',index=False)
 pd.DataFrame(annual).to_csv(out/'OLC69_ANNUAL.csv',index=False)
 pd.concat(daily).to_csv(out/'OLC69_DAILY_LOGRET.csv.gz',index=False)
 # Posthoc estimated shadow policy payoff is NOT the actual native adaptive path.
 qa['action_counts']={f'{m}_{a}':int(v) for (m,a),v in pd.concat(switches).groupby(['market','action']).size().items()}
 (out/'OLC69_QA.json').write_text(json.dumps(qa,indent=2,default=lambda o:str(o)))
 print(pd.DataFrame(score)[['market','fee','period','cagr','maxdd']].to_string(index=False),flush=True)
if __name__=='__main__':run()