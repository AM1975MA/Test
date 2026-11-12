#!/usr/bin/env python3
"""OLC99: preregistered economic Top10 ranking + matched-state Top2 allocation.
Research only; never trades. All inputs from frozen OLC98 and OLC70 checkpoints.
"""
from __future__ import annotations
import sys, json, hashlib, warnings
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import ndcg_score

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results';OUT.mkdir(parents=True,exist_ok=True)
REF=(ROOT/'source/OLC98_Model_Review_20261112')
if not REF.exists():REF=Path('/mnt/data/olc99_refs/OLC98_Model_Review_20261112')
NATIVE=REF/'native/olc19_combined_risk_20261102'
PARENT=NATIVE/'restore/olc18_execution_20261102'
SCORE_DIR=PARENT/'parent_archive/parent/olc16_contextual_rank_20261102/results'
assert NATIVE.exists(), 'OLC98 source checkpoint unavailable'
sys.path.insert(0,str(NATIVE/'src'))
sys.path.insert(0,str(PARENT/'parent_archive/parent/olc16_contextual_rank_20261102/src'))
OLC70=(ROOT/'source/OLC70')
if not OLC70.exists():OLC70=Path('/mnt/data/olc99_refs/OLC70')
sys.path.insert(0,str(OLC70))
from combined_engine import _impl,_s,_fill
from portfolio_metrics_parent import metrics
from run_olc70 import state_matched_engine

BASE_COLS=['RETURN','ORIGINAL_SMOOTH','ORIGINAL_FUSION','TOP2_CONTEXT_REVALUE_FUSION']
FEATURES=['RETURN','ORIGINAL_SMOOTH','ORIGINAL_FUSION','TOP2_CONTEXT_REVALUE_FUSION',
          'context_minus_fusion','mom5','mom10','mom21','mom63','vol21','vol63','drawdown21']
PAIR_FEATURES=['d_RETURN','d_SMOOTH','d_CTX','d_MOM10','d_MOM21','d_VOL21','pair_corr63']
ARMS=['E0_CONTEXT','E1_ANCHORED_20','E2_ANCHORED_35']
METRICS=['FULL','ACTIVE2021_2024']
SEED=99012

def digest(p:Path):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def safe_log_ratio(a,b):
 return float(np.log(a/b)) if np.isfinite(a) and np.isfinite(b) and a>0 and b>0 else np.nan

def lookback_features(q,k,idx):
 # Day k is the next-month open. Only the completed previous Close is available.
 C=q['C'];O=q['O']
 def mom(n):return safe_log_ratio(C[k-1,idx],C[k-1-n,idx]) if k>n else np.nan
 def vol(n):
  if k<=n:return np.nan
  x=C[k-1-n:k,idx]
  if len(x)<n+1 or np.any(~np.isfinite(x)) or np.any(x<=0):return np.nan
  return float(np.std(np.diff(np.log(x)),ddof=1)*np.sqrt(21))
 def dd(n):
  if k<=n:return np.nan
  x=C[k-1-n:k,idx]
  return float(np.log(x[-1]/np.max(x))) if np.isfinite(x).all() and np.min(x)>0 else np.nan
 return {'mom5':mom(5),'mom10':mom(10),'mom21':mom(21),'mom63':mom(63),
         'vol21':vol(21),'vol63':vol(63),'drawdown21':dd(21)}

def fill_train_predict(train,test,feature_names,target='y_train',alpha=100):
 x=train[feature_names].to_numpy(float);xn=test[feature_names].to_numpy(float)
 med=np.zeros(x.shape[1])
 for j in range(x.shape[1]):
  col=x[:,j];v=col[np.isfinite(col)]
  med[j]=float(np.median(v)) if len(v) else 0.
 x=np.where(np.isfinite(x),x,med);xn=np.where(np.isfinite(xn),xn,med)
 sc=StandardScaler().fit(x)
 x=sc.transform(x);xn=sc.transform(xn)
 y=train[target].to_numpy(float)
 weights=train['sample_weight'].to_numpy(float) if 'sample_weight' in train else None
 mdl=Ridge(alpha=alpha,fit_intercept=True)
 mdl.fit(x,y,sample_weight=weights)
 return mdl.predict(xn)

def per_group_score(g,name):
 return g[name].rank(method='average',pct=True).to_numpy(float)

def source(m):
 with np.load(PARENT/f'inputs/{m}_TOP2_CONTEXT_REVALUE.npz',allow_pickle=False) as z:
  q={k:z[k].copy() for k in z.files}
 with np.load(PARENT/f'inputs/{m}_ORIGINAL.npz',allow_pickle=False) as z:
  qor={k:z[k].copy() for k in z.files}
 dec=pd.read_csv(PARENT/f'inputs/{m}_TOP2_CONTEXT_REVALUE_DECISIONS.csv')
 scores=pd.read_csv(SCORE_DIR/f'{m}_SCORES.csv.gz')
 ids=np.flatnonzero(q['events']);assert len(ids)==len(dec)==90 and ids[-1]==len(q['dates'])-1
 assert np.array_equal(q['events'],qor['events'])
 assert all((q[k]==qor[k]).all() for k in q if k not in {'d1','d2','alt'})
 return q,dec,scores,ids

def prepare_panel(m,q,dec,scores,ids):
 by_date={str(d):g.copy() for d,g in scores.groupby('signal_date',sort=False)}
 mapping={str(x):i for i,x in enumerate(q['tickers'])}
 frame=[];pairs={a:[] for a in ARMS};scorecards=[]
 for j,k in enumerate(ids):
  dt=dec.loc[j,'signal_date']
  g=by_date[dt].dropna(subset=['ORIGINAL_SMOOTH','ORIGINAL_FUSION','TOP2_CONTEXT_REVALUE_FUSION'])
  g=g.sort_values(['ORIGINAL_FUSION','ticker'],ascending=[False,True],kind='mergesort').head(10).copy()
  assert len(g)==10 and g.ticker.is_unique
  assert set(dec.loc[j,['ticker1','ticker2']]).issubset(set(g.ticker)),(m,j,'pair outside Top10')
  features=[]
  for row in g.itertuples(index=False):
   tick=row.ticker;idx=mapping[tick]
   row_dict={'market':m,'event_j':j,'event_k':int(k),'signal_date':dt,'ticker':tick,'ticker_idx':idx}
   for c in BASE_COLS:row_dict[c]=float(getattr(row,c))
   row_dict['context_minus_fusion']=row_dict['TOP2_CONTEXT_REVALUE_FUSION']-row_dict['ORIGINAL_FUSION']
   row_dict.update(lookback_features(q,int(k),idx))
   e=int(ids[j+1]) if j+1<len(ids) else None
   row_dict['future_logr']=safe_log_ratio(q['O'][e,idx],q['O'][k,idx]) if e is not None else np.nan
   features.append(row_dict)
  g=pd.DataFrame(features)
  g['y_unclipped']=g.future_logr-g.future_logr.median()
  g['y_train']=g.y_unclipped.clip(-.25,.25)
  g['sample_weight']=1.0/10.0
  g['economic_pred']=np.nan
  full_groups=pd.concat(frame,ignore_index=True) if frame else pd.DataFrame()
  train=full_groups[(full_groups.event_j<=j-2)&full_groups.y_train.notna()] if len(full_groups) else pd.DataFrame()
  eligible_months=train.event_j.nunique() if len(train) else 0
  if eligible_months>=24:
   pred=fill_train_predict(train,g,FEATURES,'y_train',alpha=100)
   g['economic_pred']=pred
  g['context_rank']=per_group_score(g,'TOP2_CONTEXT_REVALUE_FUSION')
  if np.isfinite(g.economic_pred).all():
   g['econ_rank']=per_group_score(g,'economic_pred')
   g['E1_score']=.8*g.context_rank+.2*g.econ_rank
   g['E2_score']=.65*g.context_rank+.35*g.econ_rank
  else:
   g['econ_rank']=np.nan;g['E1_score']=g.context_rank;g['E2_score']=g.context_rank
  for a,col in [('E0_CONTEXT','TOP2_CONTEXT_REVALUE_FUSION'),('E1_ANCHORED_20','E1_score'),('E2_ANCHORED_35','E2_score')]:
   x=g.sort_values([col,'ticker'],ascending=[False,True],kind='mergesort').head(2)
   pairs[a].append(x.ticker.tolist())
  assert pairs['E0_CONTEXT'][-1]==dec.loc[j,['ticker1','ticker2']].tolist(),(m,j,'not native original')
  for a in ARMS:
   x=g[g.ticker.isin(pairs[a][-1])]
   scorecards.append({'market':m,'j':j,'signal_date':dt,'arm':a,'ticker1':pairs[a][-1][0],
                      'ticker2':pairs[a][-1][1],'train_n_months':int(eligible_months),
                      'static_top2_logr':float(x.future_logr.mean()) if x.future_logr.notna().all() else np.nan,
                      'mean_top10_logr':float(g.future_logr.mean()) if g.future_logr.notna().all() else np.nan,
                      'ndcg10':ndcg_score([g.future_logr.rank(pct=True).to_numpy()],
                        [g[['TOP2_CONTEXT_REVALUE_FUSION','E1_score','E2_score'][ARMS.index(a)]].to_numpy()]) if g.future_logr.notna().all() else np.nan})
  frame.append(g)
 return pd.concat(frame,ignore_index=True),pairs,pd.DataFrame(scorecards)

def rerank_q(q,ids,ticker_idx,pairs):
 z={k:v.copy() for k,v in q.items()}
 for j,k in enumerate(ids):
  e=int(ids[j+1]) if j+1<len(ids) else len(z['dates'])
  z['d1'][0,k:e]=ticker_idx[pairs[j][0]];z['d2'][0,k:e]=ticker_idx[pairs[j][1]]
 return z

def daily_logr(r):
 values=r['nav'][:-1]/r['ledger'][:-1,0]
 assert np.isfinite(values).all() and np.min(values)>0
 return np.log(values)

def simulate_native(q,fee=.001,timing='IMMEDIATE'):
 return _impl(q,q['events'],policy='DELAY' if timing=='DELAY3' else 'IMMEDIATE',fraction=3 if timing=='DELAY3' else 1,
   fee=fee,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=.001,
   ordinary_alarm=False,fast_stop=True,lock_days=3)

def pair_features(panel,pa,j,q,k):
 # Features are calculated at t. Pair ordering is explicitly Top1,Top2.
 u=panel[panel.event_j==j].set_index('ticker');t1,t2=pa[j]
 a,b=u.loc[t1],u.loc[t2]
 r={'market':str(a.market),'event_j':j,'signal_date':str(a.signal_date),'ticker1':t1,'ticker2':t2,
    'd_RETURN':float(a.RETURN-b.RETURN),
    'd_SMOOTH':float(a.ORIGINAL_SMOOTH-b.ORIGINAL_SMOOTH),
    'd_CTX':float(a.TOP2_CONTEXT_REVALUE_FUSION-b.TOP2_CONTEXT_REVALUE_FUSION),
    'd_MOM10':float(a.mom10-b.mom10),'d_MOM21':float(a.mom21-b.mom21),
    'd_VOL21':float(a.vol21-b.vol21)}
 idx1=int(a.ticker_idx);idx2=int(b.ticker_idx);C=q['C'];w=63
 if k>w+1:
  x=C[k-w-1:k,idx1];y=C[k-w-1:k,idx2]
  if min(np.min(x),np.min(y))>0 and np.isfinite(x).all() and np.isfinite(y).all():
   r['pair_corr63']=float(np.corrcoef(np.diff(np.log(x)),np.diff(np.log(y)))[0,1])
  else:r['pair_corr63']=np.nan
 else:r['pair_corr63']=np.nan
 return r

def _weight(mu,sigma):
 assert sigma>0
 return float(np.clip(.5+.5*np.tanh(mu/sigma),0,1))

def on_policy_allocation(m,base,panel,pairs,ids,policy,eng):
 """Actual selected paths define the unique evolving book. Every weight fork shares identical pre-event state."""
 assert policy in ('PRIOR','ML')
 q={k:v.copy() for k,v in base.items()};q['weights']=q['weights'].copy()
 features=pd.DataFrame([pair_features(panel,pairs,j,q,int(k)) for j,k in enumerate(ids)])
 state=None;train_labels=[];weights=[];cf=[]
 stitched={s:np.zeros_like(x) for s,x in [
    ('nav',np.ones(len(q['dates']))),('ledger',np.zeros((len(q['dates']),26))),
    ('primary_units',np.zeros_like(q['O'])),('defensive_units',np.zeros_like(q['O'])),
    ('free_cash',np.zeros(len(q['dates']))),('targets',np.zeros_like(q['O'])),
    ('risk_trace',np.zeros((len(q['dates']),8))) ]}
 fees={'fee':.001,'exposure_timing':'PREVIOUS','stop_timing':'NOW','stop_friction':.001,
       'ordinary_alarm':False,'fast_stop':True,'lock_days':3}
 for j,k0 in enumerate(ids[:-1]):
  k,e=int(k0),int(ids[j+1]);xnow=features.iloc[j];mature=[r for r in train_labels if r['event_j']<=j-2]
  mu=0.;sigma=np.nan;ww=.5
  if len(mature)>=24:
   yy=np.array([r['spread_100_vs_0_logbp'] for r in mature],float)
   sigma=max(100.,float(np.std(yy,ddof=1)))
   if policy=='PRIOR':mu=float(np.mean(yy))
   else:
    tr=features.iloc[[r['event_j'] for r in mature]].copy()
    tr['y_train']=np.clip(yy,-3500,3500)
    tr['sample_weight']=1.
    mu=float(fill_train_predict(tr,features.iloc[[j]],PAIR_FEATURES,'y_train',alpha=100)[0])
   ww=_weight(mu,sigma)
  weights.append({'market':m,'policy':policy,'event_j':j,'signal_date':str(xnow.signal_date),
           'ticker1':xnow.ticker1,'ticker2':xnow.ticker2,'weight_top1':ww,
           'pred_spread_logbp':mu,'sigma_logbp':sigma,'n_mature':len(mature)})
  versions={}
  for w in (0.,.25,.5,.75,1.,ww):
   if w in versions:continue
   qq={k2:v for k2,v in q.items()};qq['weights']=q['weights'].copy()
   qq['weights'][0,k:e]=w
   r=eng(qq,q['events'],policy='DELAY',fraction=3,start_index=k,end_index=e,
           initial_state=state,**fees)
   v=float(r['nav'][e-1]);s=float(r['ledger'][k,0]);assert np.isfinite(s) and s>0 and v>0
   versions[w]=(r,10000*np.log(v/s),s)
  assert max(v[2] for v in versions.values())-min(v[2] for v in versions.values())<1e-8
  outcomes={w:versions[w][1] for w in (0.,.25,.5,.75,1.)}
  row={'market':m,'policy':policy,'event_j':j,'signal_date':str(xnow.signal_date),
        **{f'w{int(round(w*100))}_logbp':outcomes[w] for w in outcomes},
        'spread_100_vs_0_logbp':outcomes[1.]-outcomes[0.],
        'optimal_weight_expost':float(max(outcomes,key=outcomes.get)),
        'actual_weight':ww,'actual_logbp':versions[ww][1]}
  cf.append(row)
  train_labels.append(row)
  r=versions[ww][0];state=r['state_out']
  for key in stitched:stitched[key][k:e]=r[key][k:e]
  q['weights'][0,k:e]=ww
 # Complete native simulation should equal the state-by-state run exactly.
 rwhole=simulate_native(q,timing='DELAY3')
 maxerr={key:float(np.max(np.abs(rwhole[key][:-1]-stitched[key][:-1]))) for key in stitched}
 for key in stitched:
  assert np.array_equal(rwhole[key][:-1],stitched[key][:-1]),(m,policy,key,maxerr[key])
 weights.append({'market':m,'policy':policy,'event_j':len(ids)-1,
           'signal_date':str(features.iloc[-1].signal_date),'ticker1':features.iloc[-1].ticker1,
           'ticker2':features.iloc[-1].ticker2,'weight_top1':ww,'n_mature':len(mature),'terminal_no_label':True})
 return q,rwhole,pd.DataFrame(weights),pd.DataFrame(cf),{'state_path_parity':'7 arrays bitwise', 'max_abs_diff':maxerr}

def bootstrap_month_ci(daily,m,a,b,timing='DELAY3',fee=.001,n=3000):
 d=daily[(daily.market==m)&(daily.timing==timing)&(daily.fee==fee)]
 aa=d[d.arm==a].copy();bb=d[d.arm==b].copy()
 x=aa[['date','logr']].merge(bb[['date','logr']],on='date',suffixes=('_a','_b'),validate='one_to_one')
 assert len(x)==len(aa)==len(bb)
 x['month']=pd.PeriodIndex(pd.to_datetime(x.date),freq='M').astype(str)
 grouped=x.assign(diff=x.logr_a-x.logr_b).groupby('month').agg(total=('diff','sum'),n=('diff','size'))
 vals=grouped.total.to_numpy(float);days=grouped.n.to_numpy(int);T=len(vals)
 rng=np.random.default_rng(SEED)
 stats=[]
 for z in range(n):
  groups=[]
  while len(groups)<T:
   j=int(rng.integers(T));groups.extend((j+np.arange(6))%T)
  idx=np.array(groups[:T],dtype=int)
  stats.append(252.*vals[idx].sum()/days[idx].sum())
 dlt=252.*vals.sum()/days.sum()
 return {'market':m,'arm':a,'benchmark':b,'fee':fee,'delta_annual_log_pp':100*dlt,
         'lower95':100*float(np.quantile(stats,.025)),'upper95':100*float(np.quantile(stats,.975)),
         'n_months':T,'bootstraps':n,'interpretation':'descriptive_not_OOS_not_multiple_test_adjusted'}

def run():
 qa={'source_sha256':{'protocol':digest(ROOT/'PROTOCOL_PRE_RESULTS.md')},'markets':{},'model_hyperparams':
     {'stage1_alpha':100,'warmup_months':24,'maturity_lag':2,'stage1_anchor':[.8,.65],
      'stage2_alpha':100,'risk_sigma_floor_logbp':100}}
 for m in ['EU','USA']:
  qa['source_sha256'][f'{m}_scores']=digest(SCORE_DIR/f'{m}_SCORES.csv.gz')
  qa['source_sha256'][f'{m}_Q']=digest(PARENT/f'inputs/{m}_TOP2_CONTEXT_REVALUE.npz')
 eng,s=state_matched_engine(_s,_fill)
 decisions=[];candidate=[];st=[];fullsc=[];daily=[];annual=[];weights=[];counter=[]
 for m in ['EU','USA']:
  q,dec,scores,ids=source(m)
  panel,pairs,st_rows=prepare_panel(m,q,dec,scores,ids)
  candidate.append(panel);st.append(st_rows)
  ticker_idx={str(t):i for i,t in enumerate(q['tickers'])}
  arm_q={a:rerank_q(q,ids,ticker_idx,pairs[a]) for a in ARMS}
  qa['markets'][m]={'n_events':len(ids),'n_candidate_rows':len(panel),
                   'changes_e1_vs_context':int(sum(pairs[ARMS[1]][j]!=pairs[ARMS[0]][j] for j in range(90))),
                   'changes_e2_vs_context':int(sum(pairs[ARMS[2]][j]!=pairs[ARMS[0]][j] for j in range(90)))}
  for arm in ARMS:
   for j,k in enumerate(ids):
    decisions.append({'market':m,'arm':arm,'event_j':j,'signal_date':str(dec.loc[j,'signal_date']),
          'ticker1':pairs[arm][j][0],'ticker2':pairs[arm][j][1]})
  # fixed-selection native control
  for arm in ARMS:
   for timing in ('IMMEDIATE','DELAY3'):
    for fee in (.001,.003):
     r=simulate_native(arm_q[arm],fee,timing)
     if arm=='E0_CONTEXT' and timing=='IMMEDIATE' and fee==.001:
      refpath=NATIVE/f'results/paths/{m}_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz'
      with np.load(refpath,allow_pickle=False) as orig:
       assert all(np.array_equal(orig[key],r[key]) for key in ('nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace'))
      qa['markets'][m]['original_native_parity']='7/7 bitwise'
     add_result(m,arm,timing,fee,arm_q[arm],r,fullsc,daily,annual)
  for policy in ('PRIOR','ML'):
   name='E1_ALLOC_'+policy
   qsel=arm_q['E1_ANCHORED_20']
   qout,r,w,c,qaq=on_policy_allocation(m,qsel,panel,pairs['E1_ANCHORED_20'],ids,policy,eng)
   qa['markets'][m][policy+'_onpolicy']=qaq
   weights.append(w);counter.append(c)
   for fee in (.001,.003):
    rout=r if fee==.001 else simulate_native(qout,fee,'DELAY3')
    add_result(m,name,'DELAY3',fee,qout,rout,fullsc,daily,annual)
   print('ALLOC COMPLETED',m,name,'last weight',w.weight_top1.iloc[-2],flush=True)
  score=pd.DataFrame(fullsc)
  for a in ['E0_CONTEXT','E1_ANCHORED_20','E2_ANCHORED_35','E1_ALLOC_PRIOR','E1_ALLOC_ML']:
   if len(score[(score.market==m)&(score.arm==a)&(score.period=='FULL')]):
    sub=score[(score.market==m)&(score.arm==a)&(score.period=='FULL')&(score.fee==.001)]
    print('NATIVE',m,a,[(d['timing'],round(float(d['cagr'])*100,3),round(float(d['maxdd'])*100,2)) for d in sub.to_dict('records')],flush=True)
  print('STAGE',m,'changed E1/E2',qa['markets'][m]['changes_e1_vs_context'],qa['markets'][m]['changes_e2_vs_context'],flush=True)
 pd.concat(candidate).to_csv(OUT/'OLC99_TOP10_ECONOMIC_PANEL.csv.gz',index=False,compression={'method':'gzip','mtime':0})
 pd.concat(st).to_csv(OUT/'OLC99_STATIC_TOP2_OUTCOMES.csv',index=False)
 pd.DataFrame(decisions).to_csv(OUT/'OLC99_SELECTIONS.csv',index=False)
 sc=pd.DataFrame(fullsc);sc.to_csv(OUT/'OLC99_NATIVE_SCORECARD.csv',index=False)
 d=pd.concat(daily);d.to_csv(OUT/'OLC99_DAILY_LOGRET.csv.gz',index=False,compression={'method':'gzip','mtime':0})
 pd.DataFrame(annual).to_csv(OUT/'OLC99_ANNUAL.csv',index=False)
 pd.concat(weights).to_csv(OUT/'OLC99_ALLOCATOR_WEIGHTS.csv',index=False)
 pd.concat(counter).to_csv(OUT/'OLC99_MATCHED_STATE_COUNTERFACTUALS.csv',index=False)
 ci=[]
 for m in ['EU','USA']:
  for a,b,t in [('E1_ANCHORED_20','E0_CONTEXT','DELAY3'),
                ('E2_ANCHORED_35','E0_CONTEXT','DELAY3'),
                ('E1_ALLOC_ML','E1_ANCHORED_20','DELAY3'),
                ('E1_ALLOC_ML','E1_ALLOC_PRIOR','DELAY3')]:
   ci.append(bootstrap_month_ci(d,m,a,b,t))
 pd.DataFrame(ci).to_csv(OUT/'OLC99_DESCRIPTIVE_BLOCK6_CI.csv',index=False)
 qa['n_native_paths']=len(set(zip(d.market,d.arm,d.timing,d.fee)))
 qa['n_scorecard_rows']=len(sc)
 qa['n_counterfactual_months']=len(pd.concat(counter))
 qa['n_selections']=len(decisions)
 (OUT/'OLC99_QA.json').write_text(json.dumps(qa,indent=2),encoding='utf-8')
 print('DONE',json.dumps(qa['markets'],indent=2))

def add_result(m,arm,timing,fee,q,r,sc,daily,annual):
 dt=pd.DatetimeIndex(q['dates'])[1:]
 logr=daily_logr(r)
 assert len(dt)==len(logr)
 for record in metrics(q,r): sc.append({'market':m,'arm':arm,'timing':timing,'fee':fee,**record})
 daily.append(pd.DataFrame({'market':m,'arm':arm,'timing':timing,'fee':fee,'date':dt,'logr':logr}))
 for year in sorted(set(dt.year)):
  yy=logr[dt.year==year]
  annual.append({'market':m,'arm':arm,'timing':timing,'fee':fee,'year':year,'return':float(np.expm1(yy.sum())),'n_days':len(yy)})

if __name__=='__main__':run()