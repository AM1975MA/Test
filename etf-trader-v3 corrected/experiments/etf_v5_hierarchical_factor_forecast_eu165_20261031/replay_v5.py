"""EU165 V5 hierarchical prequential forecast to self-financing portfolio diagnostic.
V3 reference original replay unchanged. 2019/20 warmup equal across policies.
No hyperparameter selection from performance; all output variants reported.
"""
from pathlib import Path
import sys,os
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'source_v4'))
import run_v4_clean as v4
OUT=ROOT if v4.COST==0.001 else ROOT/"cost_stress_30bps"
OUT.mkdir(exist_ok=True)
v4.OUT=OUT
forecast=pd.read_csv(ROOT/'PREQUENTIAL_MULTIHORIZON_PREDICTIONS.csv.gz',usecols=['signal_date','ticker','model','horizon','mu','mu_alpha','sigma_train'],parse_dates=['signal_date'])
mu=forecast.pivot_table(index=['signal_date','ticker','model'],columns='horizon',values='mu').reset_index()
mu.columns=['signal_date','ticker','model','h21','h42','h63']
mu['score21']=mu['h21']
mu['scoremulti']=0.5*mu['h21']+0.3*(mu['h42']/2)+0.2*(mu['h63']/3)
# Stable per model/date prediction. Missing later-horizon: fall back to a fully available short horizon, no future-filled labels.
mu['scoremulti']=mu.scoremulti.fillna(mu.h21)
by={(model,date):g.set_index('ticker') for (model,date),g in mu.groupby(['model','signal_date'])}
orig=v4.score_vals

def score_by_source(sc,indices,scheme):
 if scheme.startswith('V5_'):
  model,stat=plan_to_model[scheme]
  date=sc.attrs.get('signal_date')
  if date is not None:
   gg=by.get((model,date))
   if gg is not None:
    name='scoremulti' if stat=='multi' else 'score21'
    s=gg[name].reindex(sc.index).to_numpy(float)[indices]
    # Invalid expected return missing: cannot buy without a prediction.
    return np.where(np.isfinite(s),s,-1e6)
  # Warmup same V3 original source, enables true matched beginning of 2021
  return orig(sc,indices,'PAIR25')
 return orig(sc,indices,scheme)

plan_to_model={
 'V5_FACTOR_21':('FACTOR_ONLY','21'),
 'V5_BASIC_21':('FACTOR_PLUS_BASIC_RIDGE','21'),
 'V5_BASIC_GBM_21':('FACTOR_PLUS_BASIC_GBM','21'),
 'V5_EXPERT_RIDGE_21':('V5_FACTOR_PLUS_EXPERT_RIDGE','21'),
 'V5_EXPERT_GBM_21':('V5_FACTOR_PLUS_EXPERT_GBM','21'),
 'V5_EXPERT_GBM_MULTI':('V5_FACTOR_PLUS_EXPERT_GBM','multi'),
 'V5_EXPERT_GBM_MULTI_BUFFER':('V5_FACTOR_PLUS_EXPERT_GBM','multi'),
 'V5_EXPERT_GBM_MULTI_RISK':('V5_FACTOR_PLUS_EXPERT_GBM','multi'),
}

v4.PLANS={
 'REF_V3_PAIR127_TOP5':dict(score='PAIR127',ma=False,invvol=False,buffer=False),
 'REF_V3_PAIR25_TOP5':dict(score='PAIR25',ma=False,invvol=False,buffer=False),
 'REF_V3_PAIR25_HALFMA':dict(score='PAIR25',ma=True,invvol=False,buffer=False),
 'CLEAN_V4':dict(score='CLEAN',ma=True,invvol=True,buffer=True),
 **{name:dict(score=name,ma=True,invvol=('RISK' in name),buffer=('BUFFER' in name or 'RISK' in name)) for name in plan_to_model}
}
v4.score_vals=score_by_source

def main():
 tickers,ix,calendar,oo,cc,cl,events=v4.load()
 for di,(pit,sd,pool,sc,gate) in events.items():sc.attrs['signal_date']=sd
 nav,ledger,skips=v4.replay(tickers,ix,calendar,oo,cc,cl,events)
 # Confirm frozen V3 controls exactly, even though V5 variants are added.
 parity=v4.check_parity(nav) if v4.COST==0.001 else {'ref_parity':'skipped because cost differs from frozen 10bp source'}
 stats=v4.summarize(nav,ledger)
 stats.to_csv(OUT/'PORTFOLIO_SCORECARD.csv',index=False)
 nav.to_csv(OUT/'PORTFOLIO_NAV.csv')
 ledger.to_csv(OUT/'PORTFOLIO_TRADES.csv',index=False)
 skips.to_csv(OUT/'PORTFOLIO_SKIP_AUDIT.csv',index=False)
 ci=v4.paired_bootstrap(nav,first='2021-02-01',last='2024-12-31',iters=3000)
 ci.to_csv(OUT/'PORTFOLIO_PAIRED_CI_2021_2024.csv',index=False)
 print('REPLAY REF PARITY',parity)
 print('REPLAY 2021–2024',stats[stats.period=='2021_2024'][['strategy','cagr','maxdd','sharpe','ann_turnover','n_rebalances']].to_string(index=False,float_format=lambda x:f'{x:.4f}'))
 print('REPLAY 2025',stats[stats.period=='2025'][['strategy','cagr','maxdd']].to_string(index=False,float_format=lambda x:f'{x:.4f}'))
 print('PAIRED CIs',ci[['strategy','annual_log_diff_pp','ci95_lower_pp','ci95_upper_pp']].to_string(index=False,float_format=lambda x:f'{x:.3f}'))
if __name__=='__main__':main()
