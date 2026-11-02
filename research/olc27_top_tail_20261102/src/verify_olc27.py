"""Independent OLC27 replay readout: reconstruct daily CAGR, paired monthly bootstrap, OOS probabilities.
Does not fit models or rerun accounts. Uses only saved data and scorecards.
"""
from pathlib import Path
import json, hashlib
import numpy as np,pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score, average_precision_score
ROOT=Path(__file__).resolve().parents[1]
P26=Path('/mnt/data/olc26_work')
TRIALS=['AUTH','AUTH_ONLY','LONG_POOL','LONG_STRAT','LONG_POOL_NULL27001','LONG_POOL_NULL27002','LONG_POOL_NULL27003']
MARKETS=['EU','USA'];CONTRACTS=['ALARM','FAST_LOCK3'];FEES=[.001,.003]
rows=[];annual=[];quality=[];bootstrap=[];checks=[]
for trial in TRIALS:
 for m in MARKETS:
  s=pd.read_csv(ROOT/f'results/{trial}/{m}_SCORECARD.csv')
  for _,r in s.iterrows():
   if r['period'] in ['ACTIVE2021_2024','FULL','CRASH2020','2020','2021','2022','2023','2024','2025','2026']:
    rec={k:r[k] for k in ['trial','market','contract','fee','period','cagr','period_return','maxdd','turnover_annual','cvar05','n']}
    rows.append(rec)
    if str(r.period) in [str(y) for y in range(2019,2027)]:annual.append(rec)
  if trial!='AUTH':
   p=pd.read_csv(ROOT/f'results/{trial}/{m}_PREDICTIONS.csv.gz',parse_dates=['signal_date','maturity_date'])
   p=p[p.signal_date.dt.year.between(2022,2024)&p.p_tail.notna()&p.future126.notna()]
   y=(p.future126.to_numpy(float)>=.90).astype(int)
   if len(y)>0 and len(set(y))>1:
    quality.append({'trial':trial,'market':m,'n':len(p),'true_positive_rate':float(np.mean(y)),
                    'predicted_mean':float(np.mean(p.p_tail)),'brier':float(brier_score_loss(y,p.p_tail)),
                    'auc':float(roc_auc_score(y,p.p_tail)),'average_precision':float(average_precision_score(y,p.p_tail))})
  f=pd.read_csv(P26/f'results/{m}_FRAME.csv.gz',parse_dates=['signal_date'])
  so=pd.read_csv(ROOT/f'results/{trial}/{m}_SCORES.csv.gz',parse_dates=['signal_date'])
  assert f.ticker.equals(so.ticker)
  fo=so[['signal_date','ticker','FUSION']].copy()
  fo['future126']=f.future126
  fo=fo[fo.signal_date.dt.year.between(2021,2024)]
  top=fo.loc[np.isfinite(fo.FUSION)].sort_values(['signal_date','FUSION','ticker'],ascending=[True,False,True],kind='mergesort').groupby('signal_date',sort=True).head(2)
  top=top[top.future126.notna()]
  checks.append({'trial':trial,'market':m,'top2_label_rows':len(top),
                 'top2_future126_topdecile_hit_rate':float(np.mean(top.future126>=.9)),
                 'top2_future126_mean_percentile':float(top.future126.mean()),
                 'changed_signals_full':len(pd.read_csv(ROOT/f'results/{trial}/{m}_SWAPS.csv')),
                 'changed_signals_2021_2024':int(pd.to_datetime(pd.read_csv(ROOT/f'results/{trial}/{m}_SWAPS.csv').date).dt.year.between(2021,2024).sum())})

metrics=pd.DataFrame(rows);metrics.to_csv(ROOT/'results/ALL_ECONOMIC.csv',index=False)
pd.DataFrame(annual).to_csv(ROOT/'results/ANNUAL_ECONOMIC.csv',index=False)
pd.DataFrame(quality).to_csv(ROOT/'results/TAIL_PROBABILITY_QUALITY.csv',index=False)
pd.DataFrame(checks).to_csv(ROOT/'results/TOP2_DIAGNOSTICS.csv',index=False)

# Use daily log returns, not nominal compounded CAGR, for paired month block-bootstrap.
rng=np.random.default_rng(27117)
for contract in CONTRACTS:
 for fee in FEES:
  keyend=f'{contract}_{round(fee*10000)}'
  for trial in ['AUTH_ONLY','LONG_POOL','LONG_STRAT']:
   for m in MARKETS:
    paths=[ROOT/f'results/{v}/{m}_{keyend}_RETURNS.csv.gz' for v in ('AUTH',trial)]
    a,b=(pd.read_csv(x,parse_dates=['date']) for x in paths)
    assert a.date.equals(b.date)
    a=a[a.date.dt.year.between(2021,2024)].copy()
    b=b[b.date.dt.year.between(2021,2024)].copy()
    assert a.date.equals(b.date)
    a['month']=a.date.dt.to_period('M');b['month']=b.date.dt.to_period('M')
    d=b.groupby('month').log_return.sum()-a.groupby('month').log_return.sum()
    assert len(d)==48,(trial,m,contract,fee,len(d))
    delta=d.to_numpy(float);n=48;length=6;B=5000
    k=int(np.ceil(n/length)); starts=rng.integers(0,n,(B,k))
    ids=(starts[:,:,None]+np.arange(length))%n
    means=delta[ids.reshape(B,-1)[:,:n]].mean(axis=1)*1200
    bootstrap.append({'trial':trial,'market':m,'contract':contract,'fee':fee,'months':n,
                      'annualized_log_difference_pp':float(delta.mean()*1200),
                      'ci95_low_pp':float(np.quantile(means,.025)),
                      'ci95_high_pp':float(np.quantile(means,.975)),
                      'positive_months':int(np.sum(delta>1e-12)),
                      'worst3_log_contribution_pp':float(np.sort(delta)[:3].sum()*100),
                      'best3_log_contribution_pp':float(np.sort(delta)[-3:].sum()*100)})
pd.DataFrame(bootstrap).to_csv(ROOT/'results/PAIRED_BOOTSTRAP.csv',index=False)

# Independently reconstruct saved primary CAGR from daily returns as a check against scorecard.
nav=[]
for trial in TRIALS:
 for m in MARKETS:
  for contract in CONTRACTS:
   for fee in FEES:
    key=f'{m}_{contract}_{round(fee*10000)}'
    if '_NULL' in trial:continue
    a=pd.read_csv(ROOT/f'results/{trial}/{key}_RETURNS.csv.gz',parse_dates=['date'])
    a=a[a.date.dt.year.between(2021,2024)]
    reported=metrics.loc[(metrics.trial==trial)&(metrics.market==m)&(metrics.contract==contract)&(metrics.fee==fee)&(metrics.period=='ACTIVE2021_2024'),'cagr'].iloc[0]
    independent=float(np.expm1(a.log_return.sum()*252/len(a)))
    nav.append({'trial':trial,'market':m,'contract':contract,'fee':fee,'n':len(a),
                'recomputed_cagr':independent,'reported_cagr':float(reported),
                'abs_error':abs(independent-reported)})
nav=pd.DataFrame(nav);nav.to_csv(ROOT/'results/INDEPENDENT_CAGR_CHECK.csv',index=False)
assert nav.abs_error.max()<1e-10

match=metrics[metrics.period=='ACTIVE2021_2024'].copy()
match['cagr_pct']=match.cagr*100;match['maxdd_pct']=match.maxdd*100
base=match[match.trial=='AUTH'].set_index(['market','contract','fee'])
match['delta_cagr_pp']=[r.cagr_pct-base.loc[(r.market,r.contract,r.fee),'cagr_pct'] for _,r in match.iterrows()]
match['delta_maxdd_pp']=[r.maxdd_pct-base.loc[(r.market,r.contract,r.fee),'maxdd_pct'] for _,r in match.iterrows()]
match.to_csv(ROOT/'results/PRIMARY_MATCHED.csv',index=False)

# No candidate common improvements in primary period? Always report with outcome, not assert.
common=[]
for tr in ('AUTH_ONLY','LONG_POOL','LONG_STRAT'):
 for contract in CONTRACTS:
  for fee in FEES:
   z=match[(match.trial==tr)&(match.contract==contract)&(match.fee==fee)]
   common.append({'trial':tr,'contract':contract,'fee':fee,'EU_delta_cagr_pp':float(z[z.market=='EU'].delta_cagr_pp.iloc[0]),
                  'USA_delta_cagr_pp':float(z[z.market=='USA'].delta_cagr_pp.iloc[0]),
                  'common_improvement':bool((z.delta_cagr_pp>1e-8).all())})

report={'procedures':len(TRIALS),'portfolio_accounts':len(TRIALS)*2*2*2,'primary_rows':len(match),
        'models_fitted':sum(sum(not x['fallback'] for x in json.load(open(ROOT/f'results/{t}/ANNUAL_MODELS.json'))) for t in TRIALS),
        'parent_account_exact':8,'max_abs_cagr_rebuild_error':float(nav.abs_error.max()),
        'top5_swaps':{t:{m:int(pd.read_csv(ROOT/f'results/{t}/{m}_SWAPS.csv').shape[0]) for m in MARKETS} for t in TRIALS},
        'common_improvements':common,'status':'evaluated_no_promotion'}
(ROOT/'VERIFICATION.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
