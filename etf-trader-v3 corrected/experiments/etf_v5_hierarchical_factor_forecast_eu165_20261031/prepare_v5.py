"""EU165 V5 causal factor & ETF-month feature preparation (source-native forecasts only).
Runs independently of portfolio backtest; annual label-maturity gates enforced at fit.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'source_v4'))
import run_v4_clean as v4
FUND=['EXSA.DE','SXR8.DE','EXX1.DE','LYQ2.DE']; H=[21,42,63]

def go():
 tickers,ix,calendar,oo,cc,cl,events=v4.load()
 labels=pd.read_csv(v4.INPUT/'input/LABELS_ONLY.csv.gz',parse_dates=['signal_date','exit_date_21','exit_date_42','exit_date_63'])
 labels=labels[(labels.signal_date>='2017-12-01')&(labels.signal_date<='2026-05-31')]
 labelby={d:g.set_index('ticker') for d,g in labels.groupby('signal_date')}
 universe=pd.read_csv(v4.INPUT/'input/universe.csv').set_index('ticker').macro_category.to_dict()
 raw=cl.ffill(); rawlog=np.log(raw.where(raw>0))
 dret=rawlog.diff()
 # Source factor innovations: Europe, US over Europe, European banks over Europe, sovereign EUR bonds.
 f=pd.DataFrame(index=raw.index)
 f['EU']=dret['EXSA.DE'];f['US_EU']=dret['SXR8.DE']-dret['EXSA.DE'];f['BANK_EU']=dret['EXX1.DE']-dret['EXSA.DE'];f['BOND']=dret['LYQ2.DE']
 fr=f.fillna(0).to_numpy(float)
 cols=list(f.columns);daily=dret.to_numpy(float)
 prior=rawlog.to_numpy(float)
 # source signals are sometimes on non-trading dates for one venue; only past observations used.
 pct_cols=['MOM252_PCT','V3_PAIR127_PCT','V3_PAIR25_HYBRID_PCT','V2_FULL_HYBRID_PCT','V3_TAIL_RIDGE45_PCT']
 rows=[];frows=[];seen=set()
 for di,(pit,sd,pool,sc,gate) in sorted(events.items()):
  if sd in seen:continue
  seen.add(sd)
  si=raw.index.searchsorted(sd,side='right')-1
  if si<254:continue
  lb=labelby.get(sd)
  if lb is None: continue
  ff={}
  for h in H:
   rr=lb.reindex(FUND)['fwd_ret_'+str(h)]
   if rr.isna().any() or (rr<=-1).any():ff[h]=None;continue
   v=np.log1p(rr.to_numpy(float));ff[h]=np.array([v[0],v[1]-v[0],v[2]-v[0],v[3]])
  # Historical factor trend and volatility, all computed as of sd.
  f_mom={h:np.sum(fr[max(0,si-h+1):si+1],axis=0) for h in [21,63,126,252]}
  fv=np.sqrt(np.sum(fr[max(0,si-62):si+1]**2,axis=0)/63.0)
  exsa_gap=float(np.exp(prior[si,ix['EXSA.DE']]-np.nanmean(prior[si-199:si+1,ix['EXSA.DE']]))-1)
  rf={'signal_date':sd,'market_gap200':exsa_gap}
  for k in range(4):
   rf[f'f{k}_mom21']=f_mom[21][k];rf[f'f{k}_mom63']=f_mom[63][k];rf[f'f{k}_mom126']=f_mom[126][k];rf[f'f{k}_mom252']=f_mom[252][k];rf[f'f{k}_vol63']=fv[k]
   for h in H:rf[f'f{k}_y{h}']=ff[h][k] if ff[h] is not None else np.nan
  for h in H:rf[f'exit_{h}']=lb['exit_date_'+str(h)].max()
  frows.append(rf)
  # Evaluate each ETF's factor loadings using 126 preceding returns with ridge regularization.
  fwindow=fr[si-125:si+1];validF=np.isfinite(fwindow).all(axis=1)
  if validF.sum()<80:continue
  X=fwindow[validF]
  lam=0.20*float(np.trace(X.T@X)/4.0)
  inv=np.linalg.inv(X.T@X+np.eye(4)*max(lam,1e-5))@X.T
  y=daily[si-125:si+1][validF]
  observed=np.isfinite(y)
  y0=np.where(observed,y,0)
  ncounts=observed.sum(axis=0)
  beta=(inv@y0).T;beta=np.clip(beta,-3,3)
  # Scores defined for all tickers, not dynamically backfilled from future.
  mr=sc.reindex(tickers)
  for ticker in pool:
   if ticker not in ix:continue
   j=ix[ticker];b=beta[j]
   if ncounts[j]<70:continue
   pv=prior[si,j]
   if not np.isfinite(pv):continue
   # Require native original source ranks rather than placeholders.
   pcts=mr.loc[ticker,pct_cols]
   if pd.isna(pcts[['V3_PAIR127_PCT','MOM252_PCT']]).any():continue
   out={'signal_date':sd,'ticker':ticker,'macro':universe.get(ticker,'OTHER'),'market_gap200':exsa_gap,'vol63':float(np.nanstd(y[:,j])),
        'm21':pv-prior[si-21,j], 'm63':pv-prior[si-63,j], 'm126':pv-prior[si-126,j], 'm252':pv-prior[si-252,j],
        'beta_EU':b[0], 'beta_US':b[1],'beta_BANK':b[2],'beta_BOND':b[3]}
   for c in pct_cols:out[c]=float(pcts[c]) if pd.notna(pcts[c]) else np.nan
   for k in range(4):
    out[f'f{k}_mom21']=f_mom[21][k];out[f'f{k}_mom63']=f_mom[63][k];out[f'f{k}_mom252']=f_mom[252][k]
   for h in H:
    ytrue=lb.loc[ticker,'fwd_ret_'+str(h)] if ticker in lb.index else np.nan
    logtrue=float(np.log1p(ytrue)) if np.isfinite(ytrue) and ytrue>-1 else np.nan
    out[f'y{h}']=logtrue
    out[f'exit_{h}']=lb.loc[ticker,'exit_date_'+str(h)] if ticker in lb.index else pd.NaT
    out[f'alpha{h}']=logtrue-float(b@ff[h]) if np.isfinite(logtrue) and ff[h] is not None else np.nan
   # past 21/63-day risk-adjusted idiosyncratic trend, from same already estimated beta.
   out['resid_m21']=out['m21']-float(b@f_mom[21]);out['resid_m63']=out['m63']-float(b@f_mom[63])
   rows.append(out)
 df=pd.DataFrame(rows).drop_duplicates(['signal_date','ticker']);fac=pd.DataFrame(frows).drop_duplicates(['signal_date'])
 df.to_pickle(ROOT/'PIT_MONTHLY_ETF_FEATURES.pkl')
 fac.to_pickle(ROOT/'PIT_MONTHLY_FACTOR_FEATURES.pkl')
 print('FEATURES',df.shape,fac.shape,'dates',df.signal_date.nunique(),'t',df.ticker.nunique(),'end',df.signal_date.max(),flush=True)
 print('MISSING LABELS', {h:df[f'y{h}'].notna().mean() for h in H},flush=True)
 print('FIT BASIS',FUND,flush=True)
if __name__=='__main__':go()
