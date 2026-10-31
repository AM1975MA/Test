"""Independent audit of frozen evidence. No model fit or raw-price backtest.
Set AUDIT_EVIDENCE_ROOT to a directory containing evidence/{manifest.json,blobs},
main/ and branch_sources/ reconstructed from the manifest by the audit workflow.
"""
from pathlib import Path
import ast, hashlib, json, math, os
import numpy as np
import pandas as pd
B=Path(os.environ['AUDIT_EVIDENCE_ROOT'])
E=B/'evidence'; O=B/'checks'; O.mkdir(exist_ok=True)
m=json.loads((E/'manifest.json').read_text())
exported=[r for r in m['blobs'] if r['status']=='exported']
integrity=[]
for r in exported:
    data=(E/'blobs'/r['sha']).read_bytes()
    gitsha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    integrity.append({'sha':r['sha'],'size_ok':len(data)==r['size'],'sha256_ok':hashlib.sha256(data).hexdigest()==r['sha256'],'git_blob_sha1_ok':gitsha==r['sha']})
pd.DataFrame(integrity).to_csv(O/'blob_integrity.csv',index=False)
assert all(all(r[k] for k in ('size_ok','sha256_ok','git_blob_sha1_ok')) for r in integrity)
brows=[]
for ref in m['refs']:
    es=ref['entries']
    brows.append({'branch':ref['ref'].removeprefix('refs/remotes/origin/'),'commit':ref['commit'],'files':len(es),'markdown_files':sum(e['path'].endswith('.md') for e in es),'exported_text_files':sum((E/'blobs'/e['sha']).exists() for e in es)})
pd.DataFrame(brows).to_csv(O/'branch_inventory.csv',index=False)
main=next(r for r in m['refs'] if r['ref']=='refs/remotes/origin/main')
paths=[r['path'] for r in main['entries']]
dirs={str(p) for x in paths for p in Path(x).parents if str(p)!='.'}
exp='etf-trader-v3 corrected/experiments/'
v5=next((B/'branch_sources').rglob('PORTFOLIO_SCORECARD.csv')).parent
nav=pd.read_csv(v5/'PORTFOLIO_NAV.csv',index_col=0,parse_dates=True)
score=pd.read_csv(v5/'PORTFOLIO_SCORECARD.csv')
bounds={'2019_2024':('2019-02-01','2024-12-31'),'2019_2020':('2019-02-01','2020-12-31'),'2021_2024':('2021-02-01','2024-12-31'),'2021_2022':('2021-02-01','2022-12-31'),'2023_2024':('2023-01-01','2024-12-31'),'2025':('2025-01-01','2025-12-31'),'2026_partial':('2026-01-01','2026-07-01')}
recon=[]
for r in score.itertuples():
    x=nav.loc[slice(*bounds[r.period]),r.strategy].dropna().to_numpy()
    cagr=math.expm1(math.log(x[-1]/x[0])*252/(len(x)-1))
    maxdd=float(np.min(x/np.maximum.accumulate(x)-1))
    recon.append({'strategy':r.strategy,'period':r.period,'nav_rows':len(x),'reported_days':r.days,'cagr_reported':r.cagr,'cagr_recomputed':cagr,'cagr_abs_error':abs(cagr-r.cagr),'maxdd_reported':r.maxdd,'maxdd_recomputed':maxdd,'maxdd_abs_error':abs(maxdd-r.maxdd)})
pd.DataFrame(recon).to_csv(O/'v5_nav_reconciliation.csv',index=False)
assert max(x['cagr_abs_error'] for x in recon)<1e-12 and max(x['maxdd_abs_error'] for x in recon)<1e-12
assert all(x['nav_rows']==x['reported_days'] for x in recon)
a=pd.read_csv(v5/'ANNUAL_LABEL_MATURITY_AUDIT.csv')
a['cutoff']=pd.to_datetime(a.year.astype(str)+'-01-01')
a['maturity_ok']=pd.to_datetime(a.last_label_exit)<a.cutoff
a.to_csv(O/'v5_label_maturity_checked.csv',index=False)
assert a.maturity_ok.all()
pred=pd.read_csv(v5/'MONTHLY_PREDICTIVE_SKILL.csv',parse_dates=['date'])
pre=pred[pred.year.between(2021,2024)]
ps=pd.read_csv(v5/'PRE2025_PREDICTIVE_SCORECARD.csv')
means=['ic','alpha_ic','top5_excess','top5_avg_ret','rmse','alpha_rmse'];pr=[]
for r in ps.to_dict('records'):
    g=pre[(pre.h==r['h'])&(pre.model==r['model'])]
    for k in means:
        recomputed=float(g[k].mean());reported=float(r[k])
        err=0. if np.isnan(recomputed) and np.isnan(reported) else abs(recomputed-reported)
        pr.append({'h':r['h'],'model':r['model'],'metric':k,'reported':reported,'recomputed':recomputed,'abs_error':err,'month_count_ok':g.date.nunique()==r['months']})
pd.DataFrame(pr).to_csv(O/'v5_predictive_means_reconciliation.csv',index=False)
assert max(x['abs_error'] for x in pr)<1e-12 and all(x['month_count_ok'] for x in pr)
frame=nav.loc['2021-02-01':'2024-12-31']
monthly=frame.groupby(frame.index.to_period('M')).last()
returns=np.log(monthly).diff();returns.iloc[0]=np.log(monthly.iloc[0]/frame.iloc[0])
rng=np.random.default_rng(10312026);bootstrap=[]
for ctrl in ['V5_BASIC_GBM_21','V5_FACTOR_21','REF_V3_PAIR25_HALFMA']:
    d=(returns['V5_EXPERT_GBM_21']-returns[ctrl]).dropna().to_numpy();n=len(d)
    starts=rng.integers(0,n,size=(10000,(n+5)//6))
    ix=((starts[:,:,None]+np.arange(6))%n).reshape(10000,-1)[:,:n]
    draw=d[ix].mean(axis=1)*1200
    bootstrap.append({'comparison':'V5_EXPERT_GBM_21 minus '+ctrl,'months':n,'annual_log_difference_pp':float(d.mean()*1200),'block_months':6,'resamples':10000,'seed':10312026,'ci95_low_pp':float(np.quantile(draw,.025)),'ci95_high_pp':float(np.quantile(draw,.975)),'status':'exploratory_reused_history_not_independent_market_validation'})
pd.DataFrame(bootstrap).to_csv(O/'v5_independent_block_bootstrap.csv',index=False)
rp=B/'main/etf-trader-v3 corrected/experiments/etf149_rank_to_pnl_20261030'
r=pd.read_csv(rp/'equal_k_same_months.csv',dtype={'cap':str})
s=pd.read_csv(rp/'equal_k_summary.csv',dtype={'cap':str});eq=[]
for z in s.itertuples():
    g=r[(r.k==z.k)&(r.cap==z.cap)].pivot(index='signal_date',columns='model',values=z.comparison).dropna()
    delta=float((g.RIDGE-g.V2).mean());err=abs(delta-z.mean_difference)
    eq.append({'k':z.k,'cap':z.cap,'metric':z.comparison,'months':len(g),'ridge_mean_recomputed':g.RIDGE.mean(),'v2_mean_recomputed':g.V2.mean(),'difference_recomputed':delta,'difference_reported':z.mean_difference,'abs_error':err,'reported_ci_contains_zero':z.ci95_low<=0<=z.ci95_high})
pd.DataFrame(eq).to_csv(O/'equal_k_reconciliation.csv',index=False)
assert max(x['abs_error'] for x in eq)<1e-12 and all(x['months']==42 for x in eq)
source=next((B/'branch_sources').rglob('replay_v5.py')).read_text()
func=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='score_by_source')
ns={'np':np,'plan_to_model':{'V5_TEST':('MODEL','21')},'by':{},'orig':lambda sc,indices,scheme: np.full(len(indices),0.123)}
exec(compile(ast.Module(body=[func],type_ignores=[]),'<isolated archived adapter>','exec'),ns)
sc=pd.DataFrame(index=['ETF_A','ETF_B']);sc.attrs['signal_date']=pd.Timestamp('2024-06-28')
fallback=ns['score_by_source'](sc,np.arange(2),'V5_TEST')
ns['by']={('MODEL',sc.attrs['signal_date']):pd.DataFrame({'score21':[np.nan,0.02]},index=sc.index)}
missing=ns['score_by_source'](sc,np.arange(2),'V5_TEST')
adapter={'post2020_missing_date_returns_legacy_stub':bool(np.all(fallback==0.123)),'missing_score_returned':float(missing[0]),'missing_score_is_finite':bool(np.isfinite(missing[0])),'scope':'Verified adapter behavior only; missing parent replay prevents assertion that an invalid ETF was actually bought. No claim of measured PnL impact.'}
(O/'v5_adapter_probe.json').write_text(json.dumps(adapter,indent=2))
summary={'frozen_main':m['frozen_main'],'branches':len(m['refs']),'unique_blobs':len(m['blobs']),'exported_verified_blobs':len(integrity),'unexported_blobs':len(m['blobs'])-len(integrity),'main_files':len(paths),'main_directories':len(dirs),'main_tree_elements':len(paths)+len(dirs),'main_experiment_files':sum(p.startswith(exp) for p in paths),'main_experiment_subdirectories':sum(d.startswith(exp) for d in dirs),'unique_markdown_blobs':sum(r['example_path'].endswith('.md') for r in m['blobs']),'v5_nav_rows_verified':len(recon),'v5_metric_values_verified':2*len(recon),'max_cagr_abs_error':max(r['cagr_abs_error'] for r in recon),'max_dd_abs_error':max(r['maxdd_abs_error'] for r in recon),'v5_maturity_records_checked':len(a),'v5_predictive_mean_checks':len(pr),'equal_k_summary_rows_checked':len(eq),'full_raw_data_backtests_rerun':0,'trained_models':0,'scope':'All remote branch tips inventoried; deleted historical revisions and nonexported binary evidence not exhaustively inspected. Critical manual review is a subset, distinct from indexing.'}
(O/'SUMMARY.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2));print(pd.DataFrame(bootstrap).to_string(index=False))
