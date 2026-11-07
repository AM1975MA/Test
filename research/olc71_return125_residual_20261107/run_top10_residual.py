#!/usr/bin/env python3
"""OLC71C: Return125 conditional information INSIDE native FUSION Top10. Diagnostic only."""
from run_olc71 import *
from scipy.stats import spearmanr

METHODS=['ORIG_FUSION_TOP2','TOP10_SCORE_RIDGE','TOP10_PCT46_RIDGE','TOP10_FULL125_RIDGE']

def month_metrics(d,method):
  ok=d[d[method].notna() & d.fwd_ret_21.notna() & d.fwd_ret_42.notna() & d.target10_bp.notna()].copy()
  if len(ok)!=10:return None
  values=ok[method].to_numpy(float);truth=ok.target10_bp.to_numpy(float)
  rank=ok.sort_values([method,'ticker'],ascending=[False,True]).head(2)
  return dict(market=ok.market.iloc[0],year=int(ok.signal_date.iloc[0].year),month=ok.signal_date.iloc[0].strftime('%Y-%m'),method=method,n=10,
              rmse_bp=float(np.sqrt(np.mean((values-truth)**2))) if method!='ORIG_FUSION_TOP2' else np.nan,
              mse_bp2=float(np.mean((values-truth)**2)) if method!='ORIG_FUSION_TOP2' else np.nan,
              ic10=float(spearmanr(values,truth).statistic),top2_21=float(rank.fwd_ret_21.mean()),
              top2_42=float(rank.fwd_ret_42.mean()),top2_top20=float((rank.target_bp>=rank.q80).mean()),
              negative=float((rank.fwd_ret_21<0).mean()),tickers=';'.join(rank.ticker.astype(str)))

def main():
  for name,sha in SOURCE.items():assert sha256(INPUT/name)==sha
  z8=ZipFile(INPUT/'OLC08F_01_FeaturePack_20261101.zip');z14=ZipFile(INPUT/'OLC14_Fitting_Risultati_20261101.zip');z19=ZipFile(INPUT/'OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
  allpred=[];aud=[]
  for market in ('EU','USA'):
   q,feats=get_data(market,z8,z14,z19)
   q=q.loc[q.ORIGINAL_FUSION.notna()].copy()
   q=q.sort_values(['signal_date','ORIGINAL_FUSION','ticker'],ascending=[True,False,True]).groupby('signal_date',sort=True).head(10).copy()
   assert q.groupby('signal_date').size().eq(10).all()
   q['target10_bp']=1e4*(q.retlog21-q.groupby('signal_date').retlog21.transform('median'))
   # Top quintile on complete original peer universe: use target_bp threshold from ORIGINAL full eligible panel, not top10.
   # Original per-date target_21 rank is available in q, but compute percentile after full panel in separate load.
   full,_=get_data(market,z8,z14,z19)
   quant=full.groupby('signal_date').target_bp.quantile(.8)
   q['q80']=q.signal_date.map(quant)
   q.insert(0,'market',market)
   for year in range(2021,2026):
    cutoff=pd.Timestamp(year,1,1)
    tr=q.loc[q.signal_date.lt(cutoff) & q.fully_mature_label & q.train_group_exit63.lt(cutoff) & q.group_valid21 & q[BASE].notna().all(axis=1)]
    te=q.loc[q.signal_date.dt.year.eq(year)&q[BASE].notna().all(axis=1)].copy()
    assert tr.groupby('signal_date').size().eq(10).all()
    assert te.groupby('signal_date').size().eq(10).all()
    pct=[c for c in feats if c.endswith('_pct')]
    spec={'TOP10_SCORE_RIDGE':BASE,'TOP10_PCT46_RIDGE':BASE+pct,'TOP10_FULL125_RIDGE':BASE+feats}
    for method,cols in spec.items():
     te[method]=model_fit_predict(ridge_model(),tr[cols].to_numpy(float),tr.target10_bp.to_numpy(float),te[cols].to_numpy(float))
    te['ORIG_FUSION_TOP2']=te.ORIGINAL_FUSION
    allpred.append(te[['market']+KEY+['fwd_ret_21','fwd_ret_42','target_bp','target10_bp','q80']+METHODS].copy())
    aud.append(dict(market=market,year=year,ntrain=len(tr),test=len(te),train_months=tr.signal_date.nunique(),cutoff=cutoff.date().isoformat(),features=125))
    print('TOP10 fit',market,year,len(tr),len(te),flush=True)
  d=pd.concat(allpred,ignore_index=True)
  rows=[]
  for (market,date),frame in d.groupby(['market','signal_date']):
   for method in METHODS:
    r=month_metrics(frame,method)
    if r:rows.append(r)
  mo=pd.DataFrame(rows)
  sums=[]
  for (market,period,method),frame in mo.assign(period=np.where(mo.year.between(2021,2024),'MAIN_2021_2024','LATE_2025')).groupby(['market','period','method']):
   sums.append(dict(market=market,period=period,method=method,months=len(frame),rmse_bp=float(np.sqrt(frame.mse_bp2.mean())),ic10=frame.ic10.mean(),payoff21=frame.top2_21.mean(),payoff42=frame.top2_42.mean(),top20=frame.top2_top20.mean(),negative=frame.negative.mean()))
  d.to_csv(OUT/'OLC71C_TOP10_OOF.csv.gz',index=False,compression='gzip')
  mo.to_csv(OUT/'OLC71C_TOP10_MONTHLY.csv',index=False)
  pd.DataFrame(sums).to_csv(OUT/'OLC71C_TOP10_SUMMARY.csv',index=False)
  pd.DataFrame(aud).to_csv(OUT/'OLC71C_FIT_AUDIT.csv',index=False)
  (OUT/'OLC71C_QA.json').write_text(json.dumps({'train_filters':'fully_mature entire 63d group and 21d labels','months_per_year':12,'n_top10':10,'families':['scores3','scores3+pct46','scores3+full125'],'fixed_alpha':100,'no_new_untouched_OOS':True,'scores_asof':True,'top10_selections':'before future label'},indent=2))
  print(pd.DataFrame(sums).to_string(index=False,float_format=lambda x:f'{x:.5f}'))

if __name__=='__main__':main()