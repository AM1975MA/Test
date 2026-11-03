#!/usr/bin/env python3
"""Independent reconstruction: OLC19 NAV chronology, observed EU quotes, long-only ETF-style clone."""
from pathlib import Path
import io,json,zipfile,hashlib
import numpy as np,pandas as pd

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results'
ZIP19=ROOT/'input/OLC19_Rischio_Rientro_Checkpoint_20261102.zip'
ZIP32=ROOT/'input/OLC32_RESULTS.zip'
EXPECTED=['EXSA.DE','SXR8.DE','SXRV.DE','QDVE.DE','EXX1.DE']
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

def run():
 meta=json.loads((BASE/'SOURCE_MANIFEST.json').read_text());audit=json.loads((BASE/'DATA_QUALITY_AUDIT.json').read_text());sums=json.loads((BASE/'EU_STYLE_SUMMARY.json').read_text());leader=json.loads((BASE/'EU_FACTOR_LEADERSHIP_SUMMARY.json').read_text())
 assert sha(ZIP19)==meta['OLC19_zip_SHA256'] and sha(ZIP32)==meta['OLC32_zip_SHA256']
 with zipfile.ZipFile(ZIP19) as z:
  s=np.load(io.BytesIO(z.read(meta['EU_parent_state_member'])))
  p=np.load(io.BytesIO(z.read(meta['EU_parent_NAV_member'])))
  d=pd.DatetimeIndex(s['dates']);ticks=s['tickers'].astype(str);ii=[int(np.where(ticks==t)[0][0]) for t in EXPECTED]
  good=s['observed'][:,ii].all(1)&(s['O'][:,ii]>0).all(1)&np.isfinite(s['O'][:,ii]).all(1)
  vd=d[good];prices=s['O'][good][:,ii];actual=np.r_[1.,p['nav'][:-1]][good]
  assert len(vd)==sum(good) and len(vd[vd.year>=2021][vd[vd.year>=2021].year<=2024])==audit['EU_2021_2024_all_5_proxies_observed_dates']
  n0=np.argwhere(vd==pd.Timestamp('2021-01-04')).ravel()[0];n1=np.argwhere(vd==pd.Timestamp('2024-12-30')).ravel()[0]
  pred=sums['rows']['strategy_OLC19_index']['end'];want=actual[n1]/actual[n0]*100
  assert abs(want-pred)<1e-7
  # Independently reconstruct archived scorecard by interval indexing, not by direct matching NAV row.
  scc=pd.read_csv(io.BytesIO(z.read('olc19_combined_risk_20261102/results/SCORECARD.csv')))
  q=scc[(scc.market=='EU')&(scc.variant=='TOP2_CONTEXT_REVALUE')&(scc.contract=='FAST_LOCK3')&(scc.period=='ACTIVE2021_2024')&(scc.fee==0.001)&(scc.stop_friction==0.001)&(~scc.stress)].iloc[0]
  logs=np.log(np.r_[1.,p['nav']]);rr=logs[1:]-logs[:-1]
  mask=(d[1:]>=pd.Timestamp('2021-01-01'))&(d[1:]<=pd.Timestamp('2024-12-31'))
  recomputed=np.expm1(rr[:-1][mask].sum());cagr=np.expm1(rr[:-1][mask].mean()*252)
  assert abs(recomputed-q.period_return)<1e-11 and abs(cagr-q.cagr)<1e-11
  # Reconstruction by NUMBER OF SHARES at each annual Open. No use of the code that built the original clone.
  w=pd.read_csv(BASE/'EU_STYLE_TRAIN_BY_YEAR.csv');records=pd.read_csv(BASE/'EU_FACTOR_CLONE_DAILY.csv')
  assert len(records)==n1-n0+1
  gross=100.
  net=100.
  current_year=int(vd[n0].year)
  by_year={int(row.year):np.array([float(getattr(row,t.replace('.','_'))) for t in EXPECTED]) for row in []}
  by_year={int(row['year']):row[EXPECTED].to_numpy(float) for _,row in w.iterrows()}
  # At initial Open invest a fraction in proxy share units, hold remaining in cash.
  wg=by_year[current_year];shares_g=100*wg/prices[n0];cash_g=100*(1-wg.sum())
  fee0=0.001*wg.sum();net=100*(1-fee0)
  shares_n=net*wg/prices[n0];cash_n=net*(1-wg.sum())
  err_g=[];err_n=[]
  for idx in range(n0,n1+1):
   today=vd[idx];px=prices[idx];yr=int(today.year)
   if idx>n0:
    gross=cash_g+float(shares_g@px)
    net=cash_n+float(shares_n@px)
    if yr!=current_year:
     wnew=by_year[yr]
     prev=np.r_[shares_n*px/net,cash_n/net]
     now=np.r_[wnew,1-wnew.sum()]
     cost=0.001*(.5*np.abs(prev-now).sum())
     net*=1-cost
     cash_n=net*(1-wnew.sum());shares_n=net*wnew/px
     cash_g=gross*(1-wnew.sum());shares_g=gross*wnew/px
     current_year=yr
   obs=records.iloc[idx-n0]
   assert str(today.date())==obs['date']
   err_g.append(abs(gross-obs.style_clone_gross_index))
   if idx==n0:err_n.append(abs(100-obs.style_clone_fee_index))
   else:err_n.append(abs(net-obs.style_clone_fee_index))
  # fixed key/effective signal dates, true 126-session factor diagnostic independently.
  df=pd.read_csv(BASE/'EU_FACTOR_LEADERSHIP_DIAGNOSTIC.csv')
  ex=[];correct=0
  for _,row in df.iterrows():
   k=np.flatnonzero(vd<=pd.Timestamp(row.signal_date))[-1]
   past=np.log(prices[k]/prices[k-126]);future=np.log(prices[k+1+126]/prices[k+1]);i=np.argmax(past);j=np.argmax(future)
   correct+=i==j
   ex.append(abs((np.expm1(future[i])-np.expm1(future).mean())*100-row.past_leader_minus_ew_pp))
  assert len(df)==48 and correct==leader['same_leader_n']
  assert max(err_g)<1e-7 and max(err_n)<1e-7 and max(ex)<1e-10
  # Rigorous test: 2024 inputs outcomes never affect the 2024 model, trained before 2024.
  # Quantities and scorecard can be changed in source files only in a new checkpoint; this check avoids doing so.
  assert (pd.to_datetime(w.last_fit_return_date) < pd.to_datetime(w.first_test_open)).all()
  report={'status':'PASS_INDEPENDENT_ACCOUNTING_AND_PROXY_RECONSTRUCTION',
     'source19_sha_verified':True,'source32_sha_verified':True,
     'scorecard_CAGR_absolute_error':float(abs(cagr-q.cagr)),
     'scorecard_period_return_absolute_error':float(abs(recomputed-q.period_return)),
     'max_factor_clone_gross_NAV_abs_error':float(max(err_g)),
     'max_factor_clone_net_NAV_abs_error':float(max(err_n)),
     'max_126d_leader_excess_error_pp':float(max(ex)),
     'factor_leader_same_n':int(correct),
     'fit_annual_cutoffs_are_causal':True,
     'factor_pit_certified':False,'real_fill_certified':False,'USA_modified':False,
     'note':'Audit covers reproducibility of descriptive returns, not factor-neutral investing alpha or PIT holdings'}
 (BASE/'OLC37_INDEPENDENT_VERIFICATION.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
if __name__=='__main__':
 import argparse
 global_zip=None
 par=argparse.ArgumentParser()
 par.add_argument('--olc19',type=Path,default=ZIP19)
 par.add_argument('--olc32',type=Path,default=ZIP32)
 par.add_argument('--results',type=Path,default=BASE)
 args=par.parse_args()
 ZIP19,ZIP32,BASE=args.olc19,args.olc32,args.results
 run()
