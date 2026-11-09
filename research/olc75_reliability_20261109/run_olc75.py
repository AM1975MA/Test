#!/usr/bin/env python3
"""OLC75 fixed-protocol, real OLC19 Top2 reliability model and risk accounting."""
from pathlib import Path
import io,zipfile,gzip,hashlib,json,sys,math
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

ROOT=Path(__file__).resolve().parent; OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
SRC=Path('/mnt/data/etf_source')
Z74=Path('/mnt/data/OLC74_Causal_Allocazione_Top2_20261108_VERIFICATO.zip')
Z16=SRC/'OLC16_Input_Code_Checkpoint_20261102.zip';Z14=SRC/'OLC14_Fitting_Risultati_20261101.zip';Z19=SRC/'OLC19_Rischio_Rientro_Checkpoint_20261102.zip'
N=ROOT/'native'; P=N/'restore/olc18_execution_20261102';LIB=N/'restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/src'
sys.path[:0]=[str(N/'src'),str(LIB)];from combined_engine import _impl
from portfolio_metrics_parent import metrics
markets=['EU','USA'];seeds=[101,211,307]
policies=['HALF','H1_CONSENSUS','SCORE_P','RELIABILITY_P','RELIABILITY_SELECTIVE']
features=['d_fusion','vote_sum','unanimity','seed_std','prev_fusion_diff','context_inversion']
intervals={'MAIN':(2021,2024),'2024':(2024,2024),'2025':(2025,2025),'2026_PART':(2026,2026),'FULL':(2019,2026)}

def sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for data in iter(lambda:f.read(1<<22),b''):h.update(data)
 return h.hexdigest()

def read_gz(arc,name):return pd.read_csv(io.BytesIO(gzip.decompress(arc.read(name))))

def wilson(k,n,z=1.95996398454):
 if n==0:return (np.nan,np.nan)
 p=k/n;d=1+z*z/n;ctr=(p+z*z/(2*n))/d
 rad=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 return (ctr-rad,ctr+rad)

def prep_panel():
 with zipfile.ZipFile(Z74) as z:
  df=pd.read_csv(z.open('OLC74/results/OLC74_PAIR_PANEL.csv'))
  refdaily=pd.read_csv(io.BytesIO(z.read('OLC74/results/OLC74_DAILY_LOGRET.csv.gz')),compression='gzip')
 df['signal_date']=pd.to_datetime(df.signal_date);df['event_date']=pd.to_datetime(df.event_date);df['exit_date']=pd.to_datetime(df.exit_date)
 assert len(df)==180 and df.groupby('market').size().to_dict()=={'EU':90,'USA':90}
 cohort=[];qa={}
 with zipfile.ZipFile(Z16) as z16,zipfile.ZipFile(Z14) as z14:
  for market in markets:
   b='olc16_contextual_rank_20261102/inputs/'
   src=read_gz(z16,b+market+'_FITTING_FRAME.csv.gz')
   scr=read_gz(z16,b+market+'_MEAN3_SCORES.csv.gz')
   src['signal_date']=pd.to_datetime(src.signal_date);scr['signal_date']=pd.to_datetime(scr.signal_date)
   assert not src.duplicated(['signal_date','ticker']).any()
   src['ER']=src.groupby('signal_date').ORIGINAL_P15_ET.rank(pct=True,method='average')
   src['XR']=src.groupby('signal_date').ORIGINAL_P15_XGB.rank(pct=True,method='average')
   scores=src[['signal_date','ticker','ER','XR']].merge(scr[['signal_date','ticker','RETURN','ORIGINAL_CURRENT','ORIGINAL_SMOOTH','ORIGINAL_FUSION']],on=['signal_date','ticker'],validate='one_to_one')
   valid=scores.ORIGINAL_CURRENT.notna()
   gap=np.max(np.abs(scores.loc[valid,'ORIGINAL_CURRENT']-(.6*scores.loc[valid,'ER']+.4*scores.loc[valid,'XR'])))
   assert gap<1e-12,(market,gap)
   gg=scores.set_index(['signal_date','ticker']);dates=sorted(scores.signal_date.unique())
   seed_frames=[]
   for seed in seeds:
    zname=f'olc14_fitted_ranking_20261101/results/{market}_{seed}_SCORES.csv.gz'
    sd=read_gz(z14,zname);sd.signal_date=pd.to_datetime(sd.signal_date)
    assert not sd.duplicated(['signal_date','ticker']).any()
    seed_frames.append(sd.set_index(['signal_date','ticker'])['ORIGINAL_CURRENT'])
   mg=df[df.market==market].copy()
   q=dict(np.load(P/f'inputs/{market}_TOP2_CONTEXT_REVALUE.npz',allow_pickle=False))
   ids=np.flatnonzero(q['events']); assert len(ids)==len(mg)==90
   for row in mg.itertuples(index=False):
    date=row.signal_date;t1,t2=row.ticker1,row.ticker2
    assert date in dates and date<row.event_date
    k=int(row.event_index);assert int(q['d1'][0,k])>=0
    assert t1==str(q['tickers'][int(q['d1'][0,k])]) and t2==str(q['tickers'][int(q['d2'][0,k])])
    a=gg.loc[(date,t1)];b0=gg.loc[(date,t2)]
    d_return=float(a.RETURN-b0.RETURN);d_fusion=float(a.ORIGINAL_FUSION-b0.ORIGINAL_FUSION)
    assert abs(d_return-row.d_return)<1e-12
    assert abs(d_fusion-row.d_fusion)<1e-12
    assert abs(d_fusion-(.475*d_return+.525*(a.ORIGINAL_SMOOTH-b0.ORIGINAL_SMOOTH)))<1e-11
    d_et=float(a.ER-b0.ER);d_xgb=float(a.XR-b0.XR)
    votes=np.sign([d_return,d_et,d_xgb]).astype(int)
    vote_sum=int(votes.sum());unanimity=int(abs(vote_sum)==3)
    unanimity_dir=int(np.sign(vote_sum)) if unanimity else 0
    sample=[float(s.loc[(date,t1)]-s.loc[(date,t2)]) if (date,t1) in s.index and (date,t2) in s.index else np.nan for s in seed_frames]
    sd=float(np.std(sample)) if np.isfinite(sample).all() else np.nan
    seed_sign_agree=int(np.all(np.sign(sample)==np.sign(d_fusion))) if np.isfinite(sample).all() else 0
    idx=dates.index(date)
    last_date=dates[idx-1] if idx>0 else pd.NaT
    prev_diff=float(gg.loc[(last_date,t1),'ORIGINAL_FUSION']-gg.loc[(last_date,t2),'ORIGINAL_FUSION']) if idx>0 and (last_date,t1) in gg.index and (last_date,t2) in gg.index and np.isfinite(gg.loc[(last_date,t1),'ORIGINAL_FUSION']) and np.isfinite(gg.loc[(last_date,t2),'ORIGINAL_FUSION']) else np.nan
    cohort.append({**row._asdict(),'d_et':d_et,'d_xgb':d_xgb,'vote_sum':vote_sum,'unanimity':unanimity,'unanimity_dir':unanimity_dir,'seed_std':sd,'seed_sign_agree':seed_sign_agree,'prev_fusion_diff':prev_diff,'context_inversion':int(d_fusion<0),'label_win':int(row.diff_month_log>0) if np.isfinite(row.diff_month_log) else np.nan})
   qa[market]={'score_rows':len(scores),'score_last_date':str(scores.signal_date.max().date()),'eligible_rows':int(valid.sum()),'original_current_parity_max':float(gap),'events':len(mg),'asof_pass':True}
 allp=pd.DataFrame(cohort).sort_values(['market','pos']).reset_index(drop=True)
 assert len(allp)==180 and (allp.signal_date<allp.event_date).all()
 assert allp.groupby('market').diff_month_log.apply(lambda x:x.notna().sum()).to_dict()=={'EU':87,'USA':89}
 allp.to_csv(OUT/'OLC75_CONSENSUS_PANEL.csv',index=False)
 return allp,refdaily,qa

def forecast(df):
 pred=[]
 for market,g in df.groupby('market'):
  g=g.sort_values('pos').reset_index(drop=True)
  for row in g.itertuples(index=False):
   tr=g[(g.pos<=row.pos-2)&g.label_win.notna()]
   n=len(tr);pr={'market':market,'pos':row.pos,'event_date':row.event_date,'signal_date':row.signal_date,'n_train':n,'train_max_pos':int(tr.pos.max()) if n else -1,'trainable':False,'p_prior':.5,'p_score':.5,'p_reliability':.5}
   assert n==0 or pr['train_max_pos']<=row.pos-2
   if n>=24:
    y=tr.label_win.astype(int).to_numpy(); p0=float(y.mean());pr['p_prior']=p0
    for cols,key in [(['d_fusion'],'p_score'),(features,'p_reliability')]:
     model=make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),StandardScaler(),LogisticRegression(C=.1,solver='lbfgs',max_iter=1000))
     X=tr[cols].to_numpy(dtype=float);xx=np.array([getattr(row,c) for c in cols],dtype=float).reshape(1,-1)
     if len(np.unique(y))==1:pp=p0
     else:
      model.fit(X,y);pp=float(model.predict_proba(xx)[0,1])
     pr[key]=pp
    pr['trainable']=True
   pred.append(pr)
 pred=pd.DataFrame(pred)
 assert ((pred.train_max_pos==-1)|(pred.train_max_pos<=pred.pos-2)).all() and len(pred)==180
 return pred

def forecast_metrics(df):
 result=[]
 for market,g in df.groupby('market'):
  for per,(lo,hi) in intervals.items():
   ss=g[(g.event_date.dt.year>=lo)&(g.event_date.dt.year<=hi)&g.label_win.notna()&g.trainable].copy()
   if len(ss)==0:continue
   y=ss.label_win.to_numpy(dtype=float)
   for key in ['p_prior','p_score','p_reliability']:
    p=np.clip(ss[key].to_numpy(float),1e-9,1-1e-9)
    result.append({'market':market,'period':per,'model':key,'n':len(ss),'brier':np.mean((y-p)**2),'logloss':-np.mean(y*np.log(p)+(1-y)*np.log(1-p)),'accuracy':np.mean((p>.5)==(y>.5)),'win_rate_first':np.mean(y),'mean_probability':np.mean(p)})
 return pd.DataFrame(result)

def diagnostics(df):
 rows=[]
 for market,g in df.groupby('market'):
  for per,(lo,hi) in intervals.items():
   s=g[(g.event_date.dt.year>=lo)&(g.event_date.dt.year<=hi)&g.label_win.notna()].copy()
   if not len(s):continue
   for typ,seg in [('all',s),('unanimous',s[s.unanimity==1]),('split_votes',s[s.unanimity==0]),('unanimous_etf1',s[s.unanimity_dir==1]),('unanimous_etf2',s[s.unanimity_dir==-1]),('context_inversion',s[s.context_inversion==1]),('context_agree',s[s.context_inversion==0]),('prev_available',s[s.prev_fusion_diff.notna()])]:
    if len(seg)==0:continue
    win=int(seg.label_win.sum());n=len(seg)
    votes=seg.unanimity_dir.to_numpy(float);actual=seg.label_win.to_numpy(float)
    nonzero=(votes!=0)
    accuracy=float(np.mean(((votes[nonzero]>0)==(actual[nonzero]>0.5)))) if nonzero.any() else np.nan
    low,high=wilson(win,n)
    rows.append({'market':market,'period':per,'group':typ,'n':n,'first_win_rate':win/n,'win_wilson_low':low,'win_wilson_high':high,'unanimous_direction_accuracy':accuracy,'mean_future_spread_pct':float(100*seg.diff_month_log.mean()),'mean_fusion_gap':float(seg.d_fusion.mean()),'mean_seed_std':float(seg.seed_std.mean()),'prior_coverage':float(seg.prev_fusion_diff.notna().mean())})
 return pd.DataFrame(rows)

def block_bootstrap(df, niter=4000, block=6, seed=75009):
 rng=np.random.default_rng(seed);rows=[]
 for market,g in df.groupby('market'):
  s=g[(g.event_date.dt.year>=2021)&(g.event_date.dt.year<=2024)&g.trainable&g.label_win.notna()].sort_values('pos')
  y=s.label_win.to_numpy(float);n=len(s)
  b0=(y-s.p_prior.to_numpy(float))**2;b1=(y-s.p_score.to_numpy(float))**2;b2=(y-s.p_reliability.to_numpy(float))**2
  for name,ref in [('REL_MINUS_PRIOR',b0),('REL_MINUS_SCOREONLY',b1)]:
   d=b2-ref
   stats=np.empty(niter)
   for i in range(niter):
    ix=[]
    while len(ix)<n:
     start=int(rng.integers(n));ix.extend(((start+np.arange(block))%n).tolist())
    stats[i]=np.mean(d[np.array(ix[:n])])
   rows.append({'market':market,'comparison':name,'n':n,'brier_diff_reliability_minus_reference':float(d.mean()),'ci95_low':float(np.quantile(stats,.025)),'ci95_high':float(np.quantile(stats,.975)),'block_months':block,'bootstrap_repeats':niter})
 return pd.DataFrame(rows)

def weight_of(row,name):
 if name=='HALF':return .5
 if name=='H1_CONSENSUS':return .65 if row.unanimity_dir==1 else (.35 if row.unanimity_dir==-1 else .5)
 if not row.trainable:return .5
 if name=='SCORE_P':return float(.25+.5*row.p_score)
 if name=='RELIABILITY_P':return float(.25+.5*row.p_reliability)
 if name=='RELIABILITY_SELECTIVE':return float(.5 if abs(row.p_reliability-.5)<=.1 else (.25+.5*row.p_reliability))
 raise ValueError(name)

def independent_cagr_maxdd(lr):
 arr=np.asarray(lr,float);c=float(np.expm1(arr.mean()*252))
 nav=np.exp(np.cumsum(arr));dd=float(np.min(nav/np.maximum.accumulate(np.r_[1.,nav])[1:]-1))
 return c,dd

def replay(df, refdaily):
 cards=[];daily=[];annual=[];weights=[];qa={}
 for market,g in df.groupby('market'):
  g=g.sort_values('pos').reset_index(drop=True)
  with np.load(P/f'inputs/{market}_TOP2_CONTEXT_REVALUE.npz',allow_pickle=False) as zz:q={k:np.array(v) for k,v in zz.items()}
  ix=np.flatnonzero(q['events']);assert len(ix)==90
  ds=pd.DatetimeIndex(q['dates'][1:])
  assert np.array_equal(ix,g.event_index.to_numpy())
  for policy in policies:
   w=np.array([weight_of(row,policy) for row in g.itertuples(index=False)],float)
   assert ((w>=.25)&(w<=.75)).all() and np.isfinite(w).all()
   for row,wi in zip(g.itertuples(index=False),w):weights.append({'market':market,'pos':row.pos,'event_date':row.event_date,'ticker1':row.ticker1,'ticker2':row.ticker2,'policy':policy,'w1':wi,'w2':1-wi})
   qq={k:v.copy() for k,v in q.items()}
   for j,k in enumerate(ix):
    end=int(ix[j+1]) if j+1<len(ix) else qq['weights'].shape[1]
    qq['weights'][0,int(k):end]=w[j]
   for timing in ['IMMEDIATE','DELAY3']:
    for fee in [.001,.003]:
     key=f'{market}_{policy}_{timing}_{int(fee*10000)}'
     r=_impl(qq,qq['events'],policy='IMMEDIATE' if timing=='IMMEDIATE' else 'DELAY',fraction=1 if timing=='IMMEDIATE' else 3,fee=fee,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=.001,ordinary_alarm=False,fast_stop=True,lock_days=3)
     # Exact original internal ledger's daily log NAV accounting.
     lr=np.log(r['nav'][:-1]/r['ledger'][:-1,0])
     assert len(lr)==len(ds)
     ref=refdaily[(refdaily.market==market)&(refdaily.policy=='HALF')&(refdaily.timing==timing)&(np.isclose(refdaily.fee,fee))].sort_values('date')
     if policy=='HALF':
      assert len(ref)==len(lr)
      err=float(np.max(abs(lr-ref.logr.to_numpy(float))))
      assert err<1e-12,(key,err)
      qa[key]={'reference_OLC74_half_logr_max':err}
     if policy=='HALF' and timing=='IMMEDIATE' and fee==.001:
      with np.load(N/f'results/paths/{market}_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz',allow_pickle=False) as frozen:
       for col in ['nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace']:
        assert np.array_equal(r[col],frozen[col]),(key,col)
      qa[key]['reference_OLC19_bitwise_arrays']=7
     meta=metrics(qq,r)
     for item in meta:
      if item['period'] in ('FULL','ACTIVE2021_2024','2024','2025','2026','CRASH2020','2021','2022','2023'):
       mask=(ds>=pd.Timestamp(item['first_valuation']))&(ds<=pd.Timestamp(item['last_valuation']))
       c,d=independent_cagr_maxdd(lr[mask])
       assert abs(c-item['cagr'])<1e-10 and abs(d-item['maxdd'])<1e-10
       cards.append({'key':key,'market':market,'policy':policy,'timing':timing,'fee':fee,**item})
     for year in np.unique(ds.year):
      ar=lr[ds.year==year];annual.append({'market':market,'policy':policy,'timing':timing,'fee':fee,'year':int(year),'return':float(np.expm1(ar.sum())),'n':len(ar)})
     daily.append(pd.DataFrame({'date':ds,'market':market,'policy':policy,'timing':timing,'fee':fee,'key':key,'logr':lr}))
     print('REPLAY',key,'FULL',round(100*next(a['cagr'] for a in meta if a['period']=='FULL'),3),flush=True)
 cards=pd.DataFrame(cards);daily=pd.concat(daily,ignore_index=True);annual=pd.DataFrame(annual);weights=pd.DataFrame(weights)
 cards.to_csv(OUT/'OLC75_SCORECARD.csv',index=False);daily.to_csv(OUT/'OLC75_DAILY_LOGRET.csv.gz',index=False);annual.to_csv(OUT/'OLC75_ANNUAL.csv',index=False);weights.to_csv(OUT/'OLC75_EVENT_WEIGHTS.csv',index=False)
 return cards,qa

def main():
 hashes={x:sha256(p) for x,p in [('OLC74',Z74),('OLC16',Z16),('OLC14_RESULTS',Z14),('OLC19',Z19)]}
 assert hashes['OLC19']=='3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540'
 assert hashes['OLC16']=='ddc79c174afdbacc4060c1dd94b874f745eda3406fbabe6d0b475784322d3df7'
 assert hashes['OLC14_RESULTS']=='4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1'
 x,ref,qa=prep_panel();p=forecast(x)
 merged=x.merge(p.drop(columns=['event_date','signal_date']),on=['market','pos'],validate='one_to_one')
 merged.to_csv(OUT/'OLC75_EVENT_FORECASTS.csv',index=False)
 skill=forecast_metrics(merged);diags=diagnostics(merged);ci=block_bootstrap(merged)
 skill.to_csv(OUT/'OLC75_FORECAST_SKILL.csv',index=False);diags.to_csv(OUT/'OLC75_CONSENSUS_DIAGNOSTIC.csv',index=False);ci.to_csv(OUT/'OLC75_PAIRED_BRIER_CI.csv',index=False)
 print('PREDICTIVE SKILL MAIN',skill[skill.period=='MAIN'].to_string(index=False),flush=True)
 print('CONSENSUS H1 MAIN',diags[(diags.period=='MAIN')&(diags.group.isin(['all','unanimous','split_votes']))].to_string(index=False),flush=True)
 cards,parity=replay(merged,ref)
 best=cards[(cards.period.isin(['FULL','ACTIVE2021_2024'])) & (cards.fee==.001)&(cards.timing=='IMMEDIATE')]
 print('REPLAY SUMMARY',best[['market','policy','period','cagr','maxdd']].to_string(index=False),flush=True)
 qa.update(source_sha256=hashes,main_training_lag_months=2,source_holdout_end='2026-07-01',new_aug_oct_2026_data=False,full_replays=int(cards.key.nunique()),replay_parity=parity,score_reconstruction_pass=True,n_predictions=len(merged),no_new_feature_sources=True,nonindependent_historical_research=True)
 # Frozen gate: probabilistic skill must beat both references MAIN EU+USA, and FULL/MAIN returns plus DD guardrail.
 gate={}
 for m in markets:
  f=skill[(skill.market==m)&(skill.period=='MAIN')].set_index('model').brier
  gate[m]={'reliability_brier_better_prior':bool(f['p_reliability']<f['p_prior']),'reliability_brier_better_scoreonly':bool(f['p_reliability']<f['p_score'])}
  h=cards[(cards.market==m)&(cards.timing=='IMMEDIATE')&(cards.fee==.001)].set_index(['policy','period'])
  ctrl=h.loc[('HALF','FULL')];r=h.loc[('RELIABILITY_P','FULL')]
  gate[m].update(full_cagr_gte_half=bool(r.cagr>=ctrl.cagr),full_dd_degradation_le_3pp=bool(r.maxdd>=ctrl.maxdd-.03),main_cagr_gte_half=bool(h.loc[('RELIABILITY_P','ACTIVE2021_2024')].cagr>=h.loc[('HALF','ACTIVE2021_2024')].cagr))
 qa['gate']=gate;qa['gate_paper_pass']=bool(all(all(v.values()) for v in gate.values()))
 (OUT/'OLC75_QA.json').write_text(json.dumps(qa,indent=2,default=str))
 print('COMPLETE 40 paths',len(cards),'PAPER GATE',qa['gate_paper_pass'],flush=True)
if __name__=='__main__':main()