#!/usr/bin/env python3
"""OLC37: EU-only quality audit + return-based factor style screening.

This script DOES NOT fit a new ETF predictor, run trading, or alter the USA strategy.
It uses frozen OLC19 and OLC32 inputs, and only observed EU proxy Opens.
The 5-factor clone is descriptive, not a certificated factor-neutral alpha test.
"""
from __future__ import annotations
import argparse, hashlib, io, json, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import spearmanr

EXPECTED_19 = '3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540'
EXPECTED_32 = 'aef33c5c1aac60a944f7cf767b7ee637eb4ca254710b431c95b5f13a67fd6b8d'
FACS = [
 ('EXSA.DE','EUROPE_BROAD','EU broad','DE0002635307','https://www.ishares.com/it/investitore-privato/it/prodotti/251931/ishares-stoxx-europe-600-ucits-etf-de-fund','Distributing; Open price not total return'),
 ('SXR8.DE','US_LARGECAP','US broad','IE00B5BMR087','https://www.blackrock.com/us/individual/literature/fact-sheet/cspx-ishares-core-s-p-500-ucits-etf-fund-fact-sheet-en-de.pdf','Accumulating; EUR Xetra price embeds FX'),
 ('SXRV.DE','US_NASDAQ100','Nasdaq 100','IE00B53SZB19','https://live.deutsche-boerse.com/en/etf/ishares-nasdaq-100-ucits-etf-usd-acc','Accumulating; EUR Xetra price embeds FX'),
 ('QDVE.DE','US_IT','US information technology','IE00B3WJKG14','https://www.ishares.com/de/privatanleger/de/produkte/280510','Accumulating; EUR Xetra price embeds FX'),
 ('EXX1.DE','EU_BANKS','Eurozone banks','DE0006289309','https://www.ishares.com/de/privatanleger/de/produkte/251784/EXX1','Distributing; Open price not total return')
]
PFX = 'olc19_combined_risk_20261102/'
STATE_SUFFIX = '/inputs/EU_STATE_HALF.npz'
PATH_SUFFIX = '/results/paths/EU_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz'
EXPECTED_SC = ('EU','TOP2_CONTEXT_REVALUE','FAST_LOCK3',0.001,0.001,False,'ACTIVE2021_2024')


def sha256(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(8*1024*1024),b''):h.update(c)
 return h.hexdigest()

def find_one(names,suffix):
 m=[x for x in names if x.endswith(suffix)]
 if len(m)!=1: raise ValueError(f'Expected exactly one {suffix}, saw {m}')
 return m[0]

def from_zip_npz(z,key):
 a=np.load(io.BytesIO(z.read(key)),allow_pickle=False)
 return {k:a[k] for k in a.files}

def from_zip_csv(z,key):
 return pd.read_csv(io.BytesIO(z.read(key)))


def fit_style(X,y):
 """A strictly historical, no-leverage return-based style projection, not alpha."""
 k=X.shape[1]
 lam=1e-7
 def fun(w):
  q=y-X@w
  return float(np.mean(q*q)+lam*np.dot(w,w))
 def jac(w):
  return -2*(X.T@(y-X@w))/len(y)+2*lam*w
 r=minimize(fun,np.ones(k)/(2*k),jac=jac,method='SLSQP',bounds=[(0.,1.)]*k,
            constraints=[{'type':'ineq','fun':lambda w:1.-np.sum(w),
                          'jac':lambda w:-np.ones_like(w)}],
            options={'ftol':1e-14,'maxiter':5000})
 if not r.success:raise RuntimeError(f'Style optimizer failed: {r.message}')
 w=np.maximum(0.,r.x)
 if np.sum(w)>1+1e-7:raise AssertionError('leverage')
 return w


def metrics(v):
 v=np.asarray(v,float)
 # Equal daily index samples for all compared curves; annualization is a matched 252 session convention.
 if np.any(v<=0):raise AssertionError('nonpositive NAV')
 ret=v[1:]/v[:-1]-1
 peak=np.maximum.accumulate(v)
 return {'start':float(v[0]),'end':float(v[-1]),'total_return_pct':float(100*(v[-1]/v[0]-1)),
         'annualized_252_pct':float(100*((v[-1]/v[0])**(252/len(ret))-1)),
         'max_drawdown_pct':float(100*np.min(v/peak-1)),
         'annual_vol_pct':float(100*np.std(ret,ddof=1)*np.sqrt(252)),
         'sessions':int(len(ret))}


def run(archive19:Path,archive32:Path,out:Path):
 out.mkdir(parents=True,exist_ok=True)
 h19=sha256(archive19);h32=sha256(archive32)
 assert h19==EXPECTED_19,(h19,EXPECTED_19)
 assert h32==EXPECTED_32,(h32,EXPECTED_32)
 with zipfile.ZipFile(archive19) as z:
  names=z.namelist()
  state_name=find_one(names,STATE_SUFFIX)
  nav_name=find_one(names,PATH_SUFFIX)
  s=from_zip_npz(z,state_name)
  p=from_zip_npz(z,nav_name)
  dates=pd.DatetimeIndex(s['dates'])
  td=pd.DatetimeIndex(p['dates'])
  names_arr=s['tickers'].astype(str)
  assert np.array_equal(dates,td)
  assert np.array_equal(names_arr,p['tickers'].astype(str))
  assert dates.is_monotonic_increasing and dates.is_unique and pd.Index(names_arr).is_unique
  O=s['O']; observed=s['observed'];nav=p['nav']
  assert O.shape==observed.shape==(len(dates),len(names_arr))
  assert nav.shape==(len(dates),) and np.all(np.isfinite(nav)) and np.all(nav>0)
  ix=np.array([np.where(names_arr==row[0])[0].item() for row in FACS],int)
  fac_obs=observed[:,ix]
  fac_valid=fac_obs.all(axis=1)&np.isfinite(O[:,ix]).all(axis=1)&(O[:,ix]>0).all(axis=1)
  val_ix=np.flatnonzero(fac_valid)
  assert len(val_ix)>1400
  val_dates=dates[val_ix]
  f_price=O[val_ix,:][:,ix]
  # Parent nav row k belongs to valuation at dates[k+1], never dates[k].
  nav_actual=np.r_[1.0,nav[:-1]]
  s_nav=nav_actual[val_ix]
  F=f_price[1:]/f_price[:-1]-1.0
  Y=s_nav[1:]/s_nav[:-1]-1.0
  d_ret=val_dates[1:]
  assert np.isfinite(F).all() and np.isfinite(Y).all()
  # Direct original scores: same strategy, fee and period but official metric window may include non-observed dates.
  scorekey='olc19_combined_risk_20261102/results/SCORECARD.csv'
  assert scorekey in names
  card=from_zip_csv(z,scorekey)
  sel=(card.market==EXPECTED_SC[0])&(card.variant==EXPECTED_SC[1])&(card.contract==EXPECTED_SC[2])&\
      (np.isclose(card.fee,EXPECTED_SC[3]))&(np.isclose(card.stop_friction,EXPECTED_SC[4]))&\
      (~card.stress.astype(bool))&(card.period==EXPECTED_SC[6])
  assert int(sel.sum())==1,('Expected unique baseline scorecard, got',int(sel.sum()))
  base=card[sel].iloc[0]
  assert np.isclose(float(base.cagr),0.232002,atol=3e-4),float(base.cagr)
  # Verify reconstructed scorecard return within its own archival time convention.
  t0=pd.Timestamp(base.first_valuation);t1=pd.Timestamp(base.last_valuation)
  ii0=dates.get_loc(t0);ii1=dates.get_loc(t1)
  official_logs=np.diff(np.log(np.r_[1.,nav]))[:-1]
  actual=dates[1:]
  official_window=(actual>=t0)&(actual<=t1)
  official_growth=np.expm1(official_logs[official_window].sum())
  official_cagr=np.expm1(official_logs[official_window].mean()*252)
  assert official_window.sum()==int(base.n), (official_window.sum(),base.n)
  assert np.isclose(official_growth,float(base.period_return),rtol=1e-10,atol=1e-10), (official_growth,base.period_return)
  assert np.isclose(official_cagr,float(base.cagr),rtol=1e-10,atol=1e-10), (official_cagr,base.cagr)
  # Source matrix checks, including labels corrected on a different artifact only.
  month_june=dates.get_loc('2020-06-01') if '2020-06-01' in dates else None
  june_obs=int(observed[month_june].sum()) if month_june is not None else None
  june2=int(observed[dates.get_loc('2020-06-02')].sum()) if '2020-06-02' in dates else None
  l_index=np.where(names_arr=='LEEU.DE')[0]
  leeu_obs=None
  if len(l_index) and '2024-05-02' in dates:
   leeu_obs=bool(observed[dates.get_loc('2024-05-02'),l_index[0]])
  excluded=dates[~fac_valid&(dates>='2021-01-01')&(dates<='2024-12-31')]
  observed_primary_w=np.maximum(p['primary_units'],0.)*O/nav_actual[:,None]
  exposure=np.sum(observed_primary_w,axis=1)
  primary_on_unobserved=np.sum(observed_primary_w*(~observed),axis=1)
  filt=(dates>='2021-01-01')&(dates<='2024-12-31')
  assert len(dates[filt])>1000
  quality={
    'archive19_sha256':h19,'archive32_sha256':h32,
    'EU_state_dates':len(dates),'EU_state_tickers_including_technical_cash':len(names_arr),
    'EU_dates_min':str(dates.min().date()),'EU_dates_max':str(dates.max().date()),
    'state_dates_duplicated':int(dates.duplicated().sum()),'ticker_duplicates':int(pd.Index(names_arr).duplicated().sum()),
    'EU_positive_NAV':True,'EU_2020_06_01_state_observed_count':june_obs,
    'EU_2020_06_02_state_observed_count':june2,
    'EU_2024_05_02_LEEU_observed':leeu_obs,
    'EU_2021_2024_raw_dates':int(filt.sum()),
    'EU_2021_2024_all_5_proxies_observed_dates':int((fac_valid&filt).sum()),
    'EU_2021_2024_all_5_proxies_missing_dates':list(excluded.strftime('%Y-%m-%d')),
    'EU_portfolio_primary_exposure_mean':float(np.mean(exposure[filt])),
    'EU_portfolio_primary_unobserved_quote_weight_mean':float(np.mean(primary_on_unobserved[filt])),
    'EU_portfolio_primary_unobserved_quote_weight_max':float(np.max(primary_on_unobserved[filt])),
    'EU_original_scorecard':{k:(str(base[k]) if k in ('first_valuation','last_valuation') else float(base[k])) for k in ('first_valuation','last_valuation','cagr','maxdd','period_return','turnover_annual')},
    'EU_scorecard_period_return_recomputed':float(official_growth),
    'EU_scorecard_CAGR_recomputed':float(official_cagr),
    'original_NAV_valuation_shift':'nav_saved[k] = valuation at dates[k+1]; synced nav_actual[0]=1, nav_actual[i]=nav_saved[i-1]',
    'USA_reference_frozen':True,
    'critical_gate_A_pass':False,
    'critical_gate_A_blockers':['ETF constituent/sector/ISIN and share-class exposures not certified PIT for all 165 symbols',
                                'portfolio price data not independently reconciled to raw point-in-time total-return/corporate actions',
                                'true executable auction price, bid/ask and market impact not certified',
                                'USA original observed mask absent (not used in EU clone)'],
    'clone_status':'DESCRIPTIVE_ONLY_NOT_FACTOR_NEUTRAL_ALPHA_OR_DEPLOYABLE'
  }
  (out/'DATA_QUALITY_AUDIT.json').write_text(json.dumps(quality,indent=2,ensure_ascii=False))
  cat=[]
  for (tick,basis,descriptor,isin,url,limit),j in zip(FACS,ix):
   row={'ticker':tick,'proxy_dimension':basis,'economic_index_class':descriptor,'isin':isin,'source_url':url,
        'known_limit':limit,'source_asof_label':'provider description checked in 2026, not historic holdings PIT',
        'observed_2021_2024':int(observed[filt,j].sum()),'raw_rows_2021_2024':int(filt.sum()),
        'first_observed_date':str(dates[np.flatnonzero(observed[:,j])[0]].date())}
   cat.append(row)
  pd.DataFrame(cat).to_csv(out/'FACTOR_PROXY_CATALOG.csv',index=False)
  # Fit only past 252 observed paired intervals, and assign weights after last observed training date.
  weights={};rows=[]
  for year in [2021,2022,2023,2024]:
   fst=np.flatnonzero(val_dates.year==year)[0]
   cutoff=np.datetime64(f'{year}-01-01')
   eligible=np.flatnonzero(d_ret.to_numpy(dtype='datetime64[ns]')<cutoff)
   assert len(eligible)>=252,year
   train=eligible[-252:]
   assert d_ret[train[-1]]<pd.Timestamp(cutoff)
   w=fit_style(F[train,:],Y[train]);weights[year]=w
   pred=F[train,:]@w
   rows.append({'year':year,'first_test_open':str(val_dates[fst].date()),
                'last_fit_return_date':str(d_ret[train[-1]].date()),'n_train':len(train),
                'train_rmse_bp':float(np.sqrt(np.mean((Y[train]-pred)**2))*1e4),
                'train_corr':float(np.corrcoef(Y[train],pred)[0,1]),
                'sum_risky_weight':float(w.sum()),'cash_weight':float(1-w.sum()),
                **{tick:w[j] for j,(tick,*_) in enumerate(FACS)}})
  fit_table=pd.DataFrame(rows)
  fit_table.to_csv(out/'EU_STYLE_TRAIN_BY_YEAR.csv',index=False,float_format='%.12g')
  assert np.all(pd.to_datetime(fit_table.last_fit_return_date)<pd.to_datetime(fit_table.first_test_open))
  # Clone NAV paths, unleveraged and drifted within each year, matching strategy's valid Open endpoints.
  is_eval=(val_dates>=pd.Timestamp('2021-01-04'))&(val_dates<=pd.Timestamp('2024-12-30'))
  indices=np.flatnonzero(is_eval)
  assert len(indices)>980 and indices[0]>0
  first=indices[0]; end=indices[-1]
  cum={};
  wg=weights[int(val_dates[first].year)].copy();wn=wg.copy()
  g=100.;n=100.;strat=100.
  # Entirely consistent cash treatment: cost of initial cash-to-risky annual allocation; no future price in quantities.
  fee0=0.001 * wg.sum()
  n*=1-fee0
  fee_sum=fee0;events=[]
  initial=str(val_dates[first].date())
  for idx in range(first,end+1):
   day=val_dates[idx];year=int(day.year)
   if idx>first:
    rr=f_price[idx]/f_price[idx-1]-1
    gross_period=1+float(np.dot(wg,rr));net_period=1+float(np.dot(wn,rr))
    assert gross_period>0 and net_period>0
    g*=gross_period;n*=net_period
    wg=wg*(1+rr)/gross_period;wn=wn*(1+rr)/net_period
    strat=100*s_nav[idx]/s_nav[first]
   if idx==first:
    events.append({'date':initial,'year':year,'cash_to_factor_turnover':float(wg.sum()),'fee_pct_of_nav':fee0*100})
   elif val_dates[idx-1].year!=year:
    desired=weights[year]
    prev_full=np.r_[wn,1-wn.sum()]
    new_full=np.r_[desired,1-desired.sum()]
    hto=float(0.5*np.sum(np.abs(prev_full-new_full)))
    fee=0.001*hto
    n*=1-fee
    fee_sum+=fee
    wg=desired.copy();wn=desired.copy()
    events.append({'date':str(day.date()),'year':year,'cash_to_factor_turnover':hto,'fee_pct_of_nav':fee*100})
   cum[str(day.date())]={'date':str(day.date()),'year':year,
                         'strategy_OLC19_index':strat,'style_clone_gross_index':g,
                         'style_clone_fee_index':(100.0 if idx==first else n),
                         'EU_broad_EXSA_index':100*f_price[idx,0]/f_price[first,0],
                         'US_broad_SXR8_index':100*f_price[idx,1]/f_price[first,1],
                         'US_IT_QDVE_index':100*f_price[idx,3]/f_price[first,3],
                         'EU_banks_EXX1_index':100*f_price[idx,4]/f_price[first,4],
                         'Nasdaq100_SXRV_index':100*f_price[idx,2]/f_price[first,2]}
  out_daily=pd.DataFrame(cum.values());out_daily.to_csv(out/'EU_FACTOR_CLONE_DAILY.csv',index=False,float_format='%.12g')
  pd.DataFrame(events).to_csv(out/'EU_STYLE_REBALANCES.csv',index=False)
  summary={'eval_first_valid_open':str(val_dates[first].date()),'eval_last_valid_open':str(val_dates[end].date()),
           'n_matched_open_dates':len(out_daily),'style_clone_fit_mode':'as-of 252 prior valid paired returns, annual constrained nonnegative weights',
           'style_clone_initial_fee_frac':float(fee0),'style_clone_sum_nominal_fee_fractions':float(fee_sum),
           'rows':{k:metrics(out_daily[k].to_numpy()) for k in out_daily.columns if k.endswith('_index')},
           'baseline_official_cagr_pct':float(base.cagr)*100,'baseline_official_maxdd_pct':float(base.maxdd)*100,
           'factor_exposure_claim_not_permitted':True}
  summary['strategy_minus_clone_log_pp'] = float(100*np.log(out_daily.strategy_OLC19_index.iloc[-1]/out_daily.style_clone_fee_index.iloc[-1]))
  (out/'EU_STYLE_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
  # One fixed, unoptimized factor-leader persistence diagnostic; not a live strategy.
  with zipfile.ZipFile(archive32) as o32:
   calendar_csv=next(x for x in o32.namelist() if x.endswith('results/REPAIRED_CALENDAR_AUDIT.csv'))
   calendar=from_zip_csv(o32,calendar_csv)
  signal=pd.to_datetime(calendar.loc[(calendar.market=='EU')&(pd.to_datetime(calendar.signal_date)>=pd.Timestamp('2021-01-01'))&(pd.to_datetime(calendar.signal_date)<pd.Timestamp('2025-01-01')),'signal_date'].unique())
  signal=pd.DatetimeIndex(signal).sort_values()
  assert len(signal)==48,len(signal)
  factor_labels=[f[0] for f in FACS]
  leads=[]
  for sgn in signal:
   known=np.flatnonzero(val_dates<=sgn)
   if not len(known):continue
   i=known[-1]
   if i<126 or i+1+126>=len(val_dates):continue
   past=np.log(f_price[i]/f_price[i-126]);future=np.log(f_price[i+1+126]/f_price[i+1]);
   pi=int(np.argmax(past));fi=int(np.argmax(future))
   sp=float(spearmanr(past,future).statistic)
   exp_excess=float(100*(np.expm1(future[pi])-np.mean(np.expm1(future))))
   leads.append({'signal_date':str(sgn.date()),'last_available_open':str(val_dates[i].date()),
                 'forward_entry_open':str(val_dates[i+1].date()),'forward_exit_open':str(val_dates[i+1+126].date()),
                 'past_126_leader':factor_labels[pi],'future_126_leader':factor_labels[fi],
                 'past_leader_future_126_return_pct':float(100*np.expm1(future[pi])),
                 'five_factor_equalweight_future_126_return_pct':float(100*np.mean(np.expm1(future))),
                 'past_leader_minus_ew_pp':exp_excess,'same_leader':bool(pi==fi),
                 'rank_spearman_5_proxy':sp})
  frame=pd.DataFrame(leads)
  frame.to_csv(out/'EU_FACTOR_LEADERSHIP_DIAGNOSTIC.csv',index=False)
  leader_summary={'n_signals_evaluable':int(len(frame)),
                  'same_leader_n':int(frame.same_leader.sum()),
                  'same_leader_pct':float(100*frame.same_leader.mean()),
                  'mean_spearman':float(frame.rank_spearman_5_proxy.mean()),
                  'past_leader_mean_126_return_pct':float(frame.past_leader_future_126_return_pct.mean()),
                  'ew_5factor_mean_126_return_pct':float(frame.five_factor_equalweight_future_126_return_pct.mean()),
                  'mean_past_leader_minus_ew_pp':float(frame.past_leader_minus_ew_pp.mean()),
                  'overlapping_windows_not_independent':True}
  (out/'EU_FACTOR_LEADERSHIP_SUMMARY.json').write_text(json.dumps(leader_summary,ensure_ascii=False,indent=2))
  # Full paths and provenance to reproduce without reading source future labels in any fit.
  (out/'SOURCE_MANIFEST.json').write_text(json.dumps({'protocol_commit':'65cee88b013110a984057314858e34dfbed45e9b',
     'OLC19_zip_SHA256':h19,'OLC32_zip_SHA256':h32,
     'EU_parent_state_member':state_name,'EU_parent_NAV_member':nav_name,
     'source_data':'archived EU Open + observed, original NAV; no downloads/price inventions',
     'factor_source_metadata':'2026 issuer documentation, not historically PIT holdings',
     'script_version':'OLC37_EU_STYLE_CLONE_V1'},indent=2))
  return quality,summary,leader_summary


def main():
 p=argparse.ArgumentParser()
 p.add_argument('--olc19',type=Path,default=Path(__file__).resolve().parents[1]/'input/OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
 p.add_argument('--olc32',type=Path,default=Path(__file__).resolve().parents[1]/'input/OLC32_RESULTS.zip')
 p.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'results')
 a=p.parse_args()
 Q,S,L=run(a.olc19,a.olc32,a.out)
 print(json.dumps({'quality':Q,'styles':S,'leadership':L},indent=2,ensure_ascii=False))
if __name__=='__main__':main()
