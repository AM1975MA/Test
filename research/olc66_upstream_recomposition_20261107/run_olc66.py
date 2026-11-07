#!/usr/bin/env python3
"""OLC66 upstream Top10 retrieval, economic tail ordering and layer-order ablations.

No trade engine runs in this experiment unless the precommitted gate is passed.
Research only; original OLC19/11/14/16 inputs are immutable and hash checked.

Example:
 python run_olc66.py --olc11 <...> --olc14 <...> --olc16 <...> --olc19 <...> --out results
"""
from __future__ import annotations
import argparse, hashlib, io, json, zipfile, math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from olc63_parent import reconstruct, smooth_matrix, top2_weight

H={
 'olc11':'fc536d786f42f724df8102544c33e3da0e347d216d16b871f805525d9f467b6c',
 'olc14':'4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1',
 'olc16':'ddc79c174afdbacc4060c1dd94b874f745eda3406fbabe6d0b475784322d3df7',
 'olc19':'3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540',
}
METHODS=('B0_FUSION','C1_CLASS','C2_EARLY_BLEND','R1_NATIVE_TOP10','R2_UNION_TOP10','O1_FUSE_THEN_SMOOTH','O2_SMOOTH_BOTH_THEN_FUSE')
FEATS=('rank_FUSION','rank_RETURN','rank_ET','rank_XGB','rank_SMOOTH','rank_CLASS','disagreement')


def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def readgz(z,name):
 return pd.read_csv(io.BytesIO(z.read(name)),compression='gzip')

def bestk_index(x,k=10):
 x=np.asarray(x,float)
 assert np.isfinite(x).all()
 cutoff=np.sort(x)[-k]
 return np.flatnonzero(x>=cutoff)   # include ties at TopK cutoff

def score2(x):
 return top2_weight(x)

def get_rank(x):
 x=np.asarray(x,float)
 assert np.isfinite(x).all()
 return rankdata(x,method='average')/len(x)

def build_market(m,z11,z14,z16,z19):
 f,dates,tickers,di,ti,mask,scores,qa=reconstruct(m,z14,z16,z19)
 assert qa['matched_olc19_decisions']==90
 class_df=readgz(z11,f'results/{m}_XGB_CLASS_MEAN3_OUTPUTS.csv.gz')[['signal_date','ticker','FUSION','exit_date_63','fwd_ret_21','fwd_ret_42']].rename(columns={'FUSION':'CLASS_FUSION'})
 assert not class_df.duplicated(['signal_date','ticker']).any()
 x=f.merge(class_df,on=['signal_date','ticker'],how='left',validate='one_to_one',indicator=True)
 assert (x._merge=='both').all() and len(x)==len(f)
 for horizon in ('21','42'):
  a=x['fwd_ret_'+horizon+'_x'].to_numpy(float);b=x['fwd_ret_'+horizon+'_y'].to_numpy(float)
  assert np.array_equal(np.isnan(a),np.isnan(b)) and np.nanmax(np.abs(a-b))<1e-12,(m,'source return mismatch',horizon)
 x=x.rename(columns={'fwd_ret_21_x':'fwd_ret_21','fwd_ret_42_x':'fwd_ret_42'}).drop(columns=['fwd_ret_21_y','fwd_ret_42_y'])
 assert np.array_equal(x.ORIGINAL_FUSION.notna().to_numpy(),x.CLASS_FUSION.notna().to_numpy())
 assert int(x.ORIGINAL_FUSION.notna().sum())==int(mask.sum())
 # Score matrices from EXACT original OLC63 model state, including historical month lags.
 def arr(c):
  return x.pivot(index='signal_date',columns='ticker',values=c).reindex(index=dates,columns=tickers).to_numpy(float)
 r=arr('RETURN');e=arr('ER');xb=arr('XR');cur=.6*e+.4*xb
 class_matrix=arr('CLASS_FUSION')
 assert np.array_equal(np.isfinite(class_matrix),mask)
 originals=scores[15]; assert np.nanmax(np.abs(originals-arr('ORIGINAL_FUSION')))<1e-12
 ordering_1=smooth_matrix(.475*r+.525*cur,True)
 ordering_2=.475*smooth_matrix(r,True)+.525*smooth_matrix(cur,True)
 matrices={
  'B0_FUSION':originals,
  'C1_CLASS':class_matrix,
  'O1_FUSE_THEN_SMOOTH':ordering_1,
  'O2_SMOOTH_BOTH_THEN_FUSE':ordering_2,
 }
 rows=[];audit=[]
 for t,date in enumerate(dates):
  idx=np.flatnonzero(mask[t]);tick=tickers[idx].astype(str)
  df=x[(x.signal_date==date)&(x.ticker.isin(tick))].set_index('ticker').reindex(tick)
  assert len(df)==len(idx) and df.notna().loc[:,['ORIGINAL_FUSION','CLASS_FUSION','RETURN','ER','XR','ORIGINAL_SMOOTH']].all().all()
  val0=matrices['B0_FUSION'][t,idx];val1=matrices['C1_CLASS'][t,idx]
  feature_scores={
   'rank_FUSION':get_rank(val0), 'rank_RETURN':get_rank(df.RETURN.to_numpy(float)),
   'rank_ET':get_rank(df.ER.to_numpy(float)), 'rank_XGB':get_rank(df.XR.to_numpy(float)),
   'rank_SMOOTH':get_rank(df.ORIGINAL_SMOOTH.to_numpy(float)),
   'rank_CLASS':get_rank(val1),
  }
  feature_scores['disagreement']=np.abs(feature_scores['rank_FUSION']-feature_scores['rank_CLASS'])
  pool0=bestk_index(val0);pool1=bestk_index(val1);poolunion=sorted(set(pool0)|set(pool1))
  # This early blend is performed on cross-sectional rankings before selecting any ETF.
  blend=(feature_scores['rank_FUSION']+feature_scores['rank_CLASS'])/2
  scores_date={**{k:v[t,idx] for k,v in matrices.items()},'C2_EARLY_BLEND':blend}
  yr=int(str(date)[:4])
  y21=df.fwd_ret_21.to_numpy(float); y42=df.fwd_ret_42.to_numpy(float)
  valid=np.isfinite(y21).all() and np.isfinite(y42).all() and np.all(y21>-1) and np.all(y42>-1)
  if valid:
   rank21=get_rank(y21);rank42=get_rank(y42)
   target=(rank21>=.8).astype(int)
  else:
   rank21=np.full(len(idx),np.nan);rank42=rank21;target=np.full(len(idx),np.nan)
  for j,tid in enumerate(tick):
   a=df.loc[tid]
   rows.append(dict(market=m,signal_date=str(date),year=yr,ticker=tid,
    valid_label=int(valid),fwd21=float(y21[j]),fwd42=float(y42[j]),target_rank21=float(rank21[j]),target_rank42=float(rank42[j]),
    target21=float(target[j]),exit_date_63=str(a.exit_date_63),
    in_native10=int(j in pool0),in_class10=int(j in pool1),in_union=int(j in poolunion),
    **{k:float(v[j]) for k,v in feature_scores.items()},
    **{k:float(v[j]) for k,v in scores_date.items()}))
  audit.append(dict(market=m,signal_date=str(date),n_eligible=len(idx),native_pool=len(pool0),class_pool=len(pool1),union_pool=len(poolunion),valid_label=int(valid),period=('MAIN' if 2021<=yr<=2024 else 'LATE' if yr==2025 else 'OTHER')))
 return pd.DataFrame(rows),pd.DataFrame(audit),qa

def fit_reranker(panel):
 pred=[];fitlog=[]
 for market,p in panel.groupby('market',sort=True):
  p=p.copy()
  for year in range(2021,2026):
   cutoff=pd.Timestamp(year,1,1)
   tmp=p[(p.valid_label==1)&(p.in_union==1)&(pd.to_datetime(p.exit_date_63)<cutoff)].copy()
   # Whole-month maturity, not just per-ticker maturity: reject partial groups.
   whole=p.groupby('signal_date').agg(n=('ticker','size'),complete=('valid_label','min'),all_mature=('exit_date_63',lambda v:pd.to_datetime(v).max()<cutoff))
   good_dates=whole[(whole.complete==1)&(whole.all_mature)].index
   tmp=tmp[tmp.signal_date.isin(good_dates)]
   assert len(tmp)>=200 and tmp.signal_date.nunique()>=12,(market,year,'training underflow',len(tmp),tmp.signal_date.nunique())
   assert tmp.target21.notna().all() and tmp.target21.nunique()==2
   assert pd.to_datetime(tmp.exit_date_63).max()<cutoff
   nn=tmp.groupby('signal_date').ticker.transform('size').to_numpy(float)
   sw=len(tmp)/(tmp.signal_date.nunique()*nn)
   mdl=make_pipeline(StandardScaler(),LogisticRegression(C=.1,solver='lbfgs',max_iter=2000))
   mdl.fit(tmp[list(FEATS)].to_numpy(float),tmp.target21.astype(int),logisticregression__sample_weight=sw)
   # Predict each current-year ETF prior to seeing ANY of its 21d outcomes.
   curr=p[(p.year==year)&(p.in_union==1)].copy()
   if len(curr)==0:continue
   score=mdl.predict_proba(curr[list(FEATS)].to_numpy(float))[:,1]
   curr['score_rerank']=score
   pred.append(curr[['market','signal_date','ticker','score_rerank']])
   fitlog.append(dict(market=market,year=year,n_train=len(tmp),n_groups=tmp.signal_date.nunique(),n_predict=len(curr),first_train=str(tmp.signal_date.min()),last_train=str(tmp.signal_date.max()),train_pos_rate=float(tmp.target21.mean()),standardized=True,lambda_l2=False,coef=np.round(mdl[-1].coef_[0],6).tolist(),fit_intercept=float(mdl[-1].intercept_[0])))
  # No prediction for older years because only needed as causal training; reference models historical from OLC11.
 preds=pd.concat(pred,ignore_index=True)
 assert not preds.duplicated(['market','signal_date','ticker']).any()
 panel=panel.merge(preds,on=['market','signal_date','ticker'],how='left',validate='one_to_one')
 assert panel[(panel.year.between(2021,2025))&(panel.in_union==1)].score_rerank.notna().all()
 return panel,pd.DataFrame(fitlog)

def weights_for(g,method):
 if method in ('R1_NATIVE_TOP10','R2_UNION_TOP10'):
  part=g[g['in_native10']==1] if method=='R1_NATIVE_TOP10' else g[g['in_union']==1]
  if part.score_rerank.isna().any():raise ValueError('missing rerank prediction')
  ww=score2(part.score_rerank.to_numpy(float))
 else:
  part=g
  ww=score2(part[method].to_numpy(float))
 assert np.isclose(ww.sum(),1)
 return part,ww

def evaluate(p):
 monthly=[];selections=[];opportunity=[]
 for (m,date),g in p[p.year.between(2021,2025)].groupby(['market','signal_date'],sort=True):
  g=g.sort_values('ticker').reset_index(drop=True)
  # label coverage is identical across methods; missing month excluded from all comparison.
  if not g.valid_label.all():
   opportunity.append(dict(market=m,signal_date=date,year=int(date[:4]),n=len(g),status='SKIP_MISSING_LABEL'))
   continue
  y21=g.fwd21.to_numpy(float);y42=g.fwd42.to_numpy(float)
  rank21=g.target_rank21.to_numpy(float);rank42=g.target_rank42.to_numpy(float)
  assert np.isfinite(y21).all() and np.isfinite(y42).all()
  for method in METHODS:
   v,ww=weights_for(g,method)
   ids=np.flatnonzero(ww>0)
   if len(ids)<2: raise ValueError('Too few Top2')
   mu21=float(np.dot(ww,v.fwd21.to_numpy(float)))
   mu42=float(np.dot(ww,v.fwd42.to_numpy(float)))
   persist=float(np.dot(ww,((v.target_rank21>=.8)&(v.target_rank42>=.8)).astype(float)))
   lead21=float(np.dot(ww,(v.target_rank21>=.8).astype(float)))
   neg21=float(np.dot(ww,(v.fwd21<0).astype(float)))
   oracle=set(g.sort_values('fwd21',ascending=False).head(2).ticker)
   for j in ids:
    a=v.iloc[j];selections.append(dict(market=m,signal_date=date,year=int(date[:4]),method=method,ticker=a.ticker,weight=float(ww[j]),fwd21=float(a.fwd21),fwd42=float(a.fwd42),score=float(a.get('score_rerank') if method.startswith('R') else a[method])))
   pool10=g[g.in_native10==1];union=g[g.in_union==1]
   monthly.append(dict(market=m,signal_date=date,year=int(date[:4]),method=method,n_eligible=len(g),
    mean21=mu21,mean42=mu42,persistent=persist,lead21=lead21,negative21=neg21,
    overlap_future_top2=float(sum(ww[j]*(v.iloc[j].ticker in oracle) for j in ids)),
    oracle21=float(np.sort(y21)[-2:].mean()),native_pool_oracle21=float(np.sort(pool10.fwd21.to_numpy())[-2:].mean()),union_pool_oracle21=float(np.sort(union.fwd21.to_numpy())[-2:].mean())))
 return pd.DataFrame(monthly),pd.DataFrame(selections),pd.DataFrame(opportunity)

def summarize(monthly):
 out=[]
 for (m,method),g in monthly.groupby(['market','method']):
  for period,yr in [('MAIN',(2021,2022,2023,2024)),('LATE',(2025,)),('FULL',(2021,2022,2023,2024,2025))]:
   v=g[g.year.isin(yr)]
   out.append(dict(market=m,method=method,period=period,nmonths=len(v),**{c:float(v[c].mean()) for c in ('mean21','mean42','persistent','lead21','negative21','overlap_future_top2','oracle21','native_pool_oracle21','union_pool_oracle21')}))
 return pd.DataFrame(out)

def bootstrap(monthly,rep=2000,seed=66007):
 rng=np.random.default_rng(seed);out=[]
 for m in ('EU','USA'):
  v=monthly[(monthly.market==m)&(monthly.year.between(2021,2024))]
  for metric in ('mean21','mean42','persistent'):
   wide=v.pivot(index='signal_date',columns='method',values=metric).sort_index()
   assert len(wide)==48 and wide.notna().all().all()
   ix=np.empty((rep,48),dtype=int)
   for j in range(rep):
    starts=rng.integers(0,48,size=8)
    ix[j]=np.concatenate([np.arange(s,s+6)%48 for s in starts])[:48]
   for method in METHODS[1:]:
    a=(wide[method]-wide['B0_FUSION']).to_numpy()
    z=a[ix].mean(axis=1)
    out.append(dict(market=m,metric=metric,method=method,delta_mean=float(a.mean()),ci_lower=float(np.quantile(z,.025)),ci_upper=float(np.quantile(z,.975)),n_positive=int((a>0).sum()),nmonths=len(a)))
 return pd.DataFrame(out)

def lo_yo(monthly):
 z=[]
 for m in ('EU','USA'):
  v=monthly[(monthly.market==m)&monthly.year.between(2021,2024)]
  for year in (2021,2022,2023,2024):
   w=v[v.year!=year].pivot(index='signal_date',columns='method',values='mean21')
   for method in METHODS[1:]:z.append(dict(market=m,year_excluded=year,method=method,delta_mean21=float((w[method]-w.B0_FUSION).mean())))
 return pd.DataFrame(z)

def main(args):
 for k,h in H.items():
  d=sha(getattr(args,k))
  assert d==h,(k,'immutable input SHA mismatch',d,h)
 out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 panels=[];poolinfo=[];qa0=[]
 with zipfile.ZipFile(args.olc11) as z11,zipfile.ZipFile(args.olc14) as z14,zipfile.ZipFile(args.olc16) as z16,zipfile.ZipFile(args.olc19) as z19:
  for m in ('EU','USA'):
   p,a,q=build_market(m,z11,z14,z16,z19)
   panels.append(p);poolinfo.append(a);qa0.append(q)
   print('build market',m,len(p),'selection parity',q['matched_olc19_decisions'],flush=True)
 panel=pd.concat(panels,ignore_index=True)
 panel,fits=fit_reranker(panel)
 monthly,sel,skips=evaluate(panel)
 assert not monthly.empty
 summary=summarize(monthly);boot=bootstrap(monthly);loyo=lo_yo(monthly)
 # Independent same-population/label controls: benchmark frozen OLC63 Top2 mean21/42.
 expected={'EU':(.0213087107986867,.0375386073901987),'USA':(.035010,.0)}
 for m in ('EU','USA'):
  ref=summary[(summary.market==m)&(summary.period=='MAIN')&(summary.method=='B0_FUSION')].iloc[0]
  assert len(monthly[(monthly.market==m)&(monthly.method=='B0_FUSION')&(monthly.year.between(2021,2024))])==48
  assert abs(ref.mean21-expected[m][0])<3e-5,(m,'baseline static mismatch',ref.mean21)
 # Entire 2021-25 panel as a controlled sample: no row dropout for method.
 pivot=monthly.pivot(index=['market','signal_date'],columns='method',values='mean21')
 assert set(pivot.columns)==set(METHODS) and not pivot.isna().any().any()
 for m in ('EU','USA'):
  assert len(pivot.loc[m])>=58
 # Independent arithmetic: aggregate selected ticker weighted returns from detail rows.
 check=sel.groupby(['market','signal_date','method']).apply(lambda g:np.dot(g.weight,g.fwd21),include_groups=False).rename('recalc')
 comp=monthly.set_index(['market','signal_date','method']).join(check)
 merr=float((comp.recalc-comp.mean21).abs().max());assert merr<1e-12
 qa=dict(source_sha256=H,markets=qa0,total_original_decisions=sum(q['matched_olc19_decisions'] for q in qa0),
      n_raw_rows=len(panel),n_monthly_rows=len(monthly),number_fits=len(fits),model_train_only_before_cutoff=True,
      same_support=True,max_static_return_tieout_error=merr,main_modified=False,trading_engine_rerun=False,
      protocol='research/olc66_upstream_recomposition_20261107/PROTOCOL_PRE_RESULTS.md')
 for file,df in [('OLC66_PANEL.csv.gz',panel),('OLC66_FITS.csv',fits),('OLC66_POOL_SUPPORT.csv',pd.concat(poolinfo)),('OLC66_MONTHLY.csv',monthly),('OLC66_SELECTED.csv',sel),('OLC66_SUMMARY.csv',summary),('OLC66_BLOCK6_BOOTSTRAP.csv',boot),('OLC66_LOYO.csv',loyo),('OLC66_SKIPPED.csv',skips)]:
  df.to_csv(out/file,index=False,compression='gzip' if file.endswith('.gz') else None)
 (out/'OLC66_QA.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False))
 print('SUM MAIN:')
 print(summary[summary.period=='MAIN'][['market','method','nmonths','mean21','mean42','persistent','negative21']].to_string(index=False,float_format=lambda x:f'{x:.5f}'),flush=True)
 print('LATE:')
 print(summary[summary.period=='LATE'][['market','method','nmonths','mean21','mean42','persistent']].to_string(index=False,float_format=lambda x:f'{x:.5f}'),flush=True)
 print('QA:',qa,flush=True)

if __name__=='__main__':
 a=argparse.ArgumentParser()
 for k in H:a.add_argument('--'+k,required=True)
 a.add_argument('--out',required=True)
 main(a.parse_args())