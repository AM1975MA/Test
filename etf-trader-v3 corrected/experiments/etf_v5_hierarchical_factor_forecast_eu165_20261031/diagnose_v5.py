"""Ablation and regime diagnostics: no new fitted policy or parameter search."""
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent
nav=pd.read_csv(R/'PORTFOLIO_NAV.csv',parse_dates=['date']).set_index('date')
ledger=pd.read_csv(R/'PORTFOLIO_TRADES.csv',parse_dates=['date'])
fc=pd.read_csv(R/'PREQUENTIAL_MULTIHORIZON_PREDICTIONS.csv.gz',parse_dates=['signal_date'])
monthly=pd.read_csv(R/'MONTHLY_PREDICTIVE_SKILL.csv',parse_dates=['date'])
comparisons=[('V5_EXPERT_GBM_21','V5_BASIC_GBM_21'),('V5_EXPERT_GBM_21','V5_FACTOR_21'),('V5_EXPERT_GBM_21','REF_V3_PAIR25_HALFMA'),('V5_BASIC_GBM_21','REF_V3_PAIR25_HALFMA')]
rng=np.random.default_rng(20261031)
rows=[]
for title,first,last in [('PRE2025','2021-02-01','2024-12-31'),('EARLY','2021-02-01','2022-12-31'),('LATE','2023-01-01','2024-12-31'),('STRESS_2025','2025-01-01','2025-12-31')]:
 frame=nav.loc[first:last]
 ends=np.log(frame.resample('ME').last()).diff().dropna()
 start=frame.iloc[0];endmonth=frame.resample('ME').last().iloc[0]
 ends=pd.concat([pd.DataFrame([np.log(endmonth/start)],index=[endmonth.name]),ends])
 for a,b in comparisons:
  d=(ends[a]-ends[b]).dropna().to_numpy();n=len(d)
  bt=[]
  for _ in range(4000):
   picks=np.concatenate([np.arange(j,j+6)%n for j in rng.integers(0,n,size=(n+5)//6)])[:n]
   bt.append(float(np.mean(d[picks])))
  rows.append({'period':title,'strategy':a,'reference':b,'n_months':n,
     'annual_log_diff_pp':12*100*d.mean(),'ci95_lo_pp':12*100*np.percentile(bt,2.5),'ci95_hi_pp':12*100*np.percentile(bt,97.5),
     'monthly_win_rate':float(np.mean(d>0))})
pd.DataFrame(rows).to_csv(R/'CLEAN_FACTOR_EXPERT_ABLATION_BLOCK_CI.csv',index=False)
# ETF selected same months for basic & full GBM?
p=fc[(fc.horizon==21)&(fc.signal_date.dt.year.between(2021,2024))]
wide=p.pivot_table(index=['signal_date','ticker'],columns='model',values='mu')
rec=[]
for date,g in wide.groupby(level=0):
 a=g['FACTOR_PLUS_BASIC_GBM'].dropna().sort_values(ascending=False).head(5)
 b=g['V5_FACTOR_PLUS_EXPERT_GBM'].dropna().sort_values(ascending=False).head(5)
 c=g['FACTOR_ONLY'].dropna().sort_values(ascending=False).head(5)
 ix=g[['FACTOR_PLUS_BASIC_GBM','V5_FACTOR_PLUS_EXPERT_GBM']].dropna()
 rec.append({'signal_date':date,'overlap_basic_expert_top5':len(set(a.index).intersection(set(b.index)))/5,
      'overlap_factor_expert_top5':len(set(c.index).intersection(set(b.index)))/5,
      'rank_corr_basic_expert':spearmanr(ix.iloc[:,0],ix.iloc[:,1]).statistic,'n':len(ix)})
pd.DataFrame(rec).to_csv(R/'SCORE_EXPERT_ABLATION_OVERLAP.csv',index=False)
# Forecast error calibration: naive train-month sigma is not an actual conformal/predictive distribution.
r=[]
for (h,m),g in fc[(fc.signal_date.dt.year.between(2021,2024))].groupby(['horizon','model']):
 valid=g.dropna(subset=['true_log','mu','sigma_train'])
 if valid.empty:continue
 err=valid.true_log-valid.mu
 # Normal 80% interval using sigma_train is a provisional scale only.
 hit=float(np.mean(abs(err)<=1.28155*valid.sigma_train))
 r.append({'horizon':h,'model':m,'ticker_months':len(valid),'error_mean':float(err.mean()),'rmse':float(np.sqrt(np.mean(err**2))),
  'mean_predicted_sigma':float(valid.sigma_train.mean()),'nominal80_cover':hit,'expected_coverage':0.8})
pd.DataFrame(r).to_csv(R/'UNCERTAINTY_DIAGNOSTIC.csv',index=False)
# Selected ticker concentration / beta proxy static exposure no full factored attribution.
f=pd.read_pickle(R/'PIT_MONTHLY_ETF_FEATURES.pkl')
f=f.set_index(['signal_date','ticker']);tax=pd.read_csv(R/'EU165_ECONOMIC_TAXONOMY.csv')
print('TAX FIELDS',tax.columns.tolist(),flush=True)
rr=[]
for _,r in ledger[ledger.strategy.isin(['V5_EXPERT_GBM_21','V5_BASIC_GBM_21','V5_FACTOR_21','REF_V3_PAIR25_HALFMA'])].iterrows():
 if pd.isna(r.signal_date):continue
 sd=pd.Timestamp(r.signal_date);tks=str(r.tickers).split(',')
 for t in tks:
  if (sd,t) not in f.index:continue
  z=f.loc[(sd,t)]
  rr.append({'date':r.date,'signal_date':sd,'strategy':r.strategy,'ticker':t,'year':r.date.year,
        'beta_EU':z.beta_EU,'beta_US':z.beta_US,'beta_BANK':z.beta_BANK,'beta_BOND':z.beta_BOND,'macro':z.macro})
pd.DataFrame(rr).to_csv(R/'SLOTS_AND_FACTOR_LOADINGS.csv',index=False)
# One figure, transparent metrics, no specified colors or styles
frame=nav.loc['2021-02-01':'2024-12-31'];fig,ax=plt.subplots(figsize=(11,5.8))
for n in ['REF_V3_PAIR25_HALFMA','V5_FACTOR_21','V5_BASIC_GBM_21','V5_EXPERT_GBM_21','V5_EXPERT_GBM_MULTI_BUFFER']:
 x=frame[n]/frame[n].iloc[0];ax.plot(x.index,100*x,label=n,linewidth=1.5)
ax.set_title('EU165, 2021–2024 · V5 gerarchica vs V3 (NAV normalizzati)');ax.set_ylabel('NAV (inizio=100)')
ax.set_xlabel('Data');ax.grid(alpha=.2);ax.legend(fontsize=8);fig.tight_layout();fig.savefig(R/'NAV_V5_HIERARCHICAL_2021_2024.png',dpi=175);plt.close(fig)
print(pd.read_csv(R/'CLEAN_FACTOR_EXPERT_ABLATION_BLOCK_CI.csv').to_string(index=False,float_format=lambda x:f'{x:.3f}'))
print('OVERLAP',pd.read_csv(R/'SCORE_EXPERT_ABLATION_OVERLAP.csv').mean(numeric_only=True).to_dict())
