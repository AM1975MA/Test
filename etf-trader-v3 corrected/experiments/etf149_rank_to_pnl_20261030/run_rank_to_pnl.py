#!/usr/bin/env python3
"""Frozen ETF149 V2/Ridge score-to-realized-return diagnostic.
Inputs: archived 149-price snapshot, V2 OOS scores, Ridge forward scores, frozen portfolio weights.
No fitting, feature selection, or model changes. Results are historical diagnostics, NOT fresh OOS.
Dependencies: numpy, pandas, scipy.
"""
from pathlib import Path
import io, zipfile, json, hashlib, os
from math import ceil
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, pearsonr

BASE=Path(os.environ.get('ETF149_DATA_ROOT', '/mnt/data'))
OUT=Path(os.environ.get('ETF149_OUTPUT_DIR', str(BASE/'ETF149_Rank_to_PnL_20261030')))
OUT.mkdir(parents=True,exist_ok=True)
PZIP=BASE/'etf149_forward_20261023.zip'
VZIP=BASE/'v2_deep_leaf_complete_results.zip'
RZIP=BASE/'ETF149_Predictive_Research_2020_2026.zip'
WFILE=BASE/'ETF149_Investment_System_Research/strategy_target_weights.npz'
assert all(p.exists() for p in [PZIP,VZIP,RZIP,WFILE])
z=zipfile.ZipFile(PZIP)
u=pd.read_csv(io.BytesIO(z.read('universe.csv')))
tick=u.ticker.astype(str).tolist()
assert len(tick)==149
cat=u.macro_category.astype(str).to_numpy()
position={t:i for i,t in enumerate(tick)}
D=pd.DatetimeIndex(pd.read_csv(io.BytesIO(z.read('SPY.csv')),usecols=['date'],parse_dates=['date']).date)
P=np.full((len(D),len(tick)),np.nan)
for i,t in enumerate(tick):
    d=pd.read_csv(io.BytesIO(z.read(t+'.csv')),usecols=['date','Open'],parse_dates=['date']).set_index('date').sort_index()
    P[:,i]=d.Open.reindex(D).to_numpy(float)
last=pd.Series(np.arange(len(D)),index=D).groupby(D.to_period('M')).last().to_numpy()
blocks=[]
for j in range(len(last)-1):
    s=int(last[j]);e=s+1;x=int(last[j+1])+1
    if x+5>=len(D) or D[e]<pd.Timestamp('2013-01-01') or D[e]>pd.Timestamp('2026-09-01'):continue
    blocks.append((D[s].strftime('%Y-%m-%d'),e,x))
by_date={s:(e,x) for s,e,x in blocks}
weights=np.load(WFILE)
wr=weights['RIDGE_top15_none_capNone']
assert wr.shape[0]==len(blocks)
V=pd.read_csv(io.BytesIO(zipfile.ZipFile(VZIP).read('runs/v2_large_leaf_complete/OOS_SCORES.csv')),
              usecols=['variant','signal_date','ticker','score'])
V=V[V.variant=='leaves_255'].copy()
V['signal_date']=pd.to_datetime(V.signal_date).dt.strftime('%Y-%m-%d')
V=V.rename(columns={'signal_date':'date'})
R=pd.read_csv(io.BytesIO(zipfile.ZipFile(RZIP).read('ETF149_predictive_research/forward_2026/monthly_predictions.csv.gz')),
              compression='gzip',usecols=['date','ticker','ridge_nokalman'])
R=R.rename(columns={'ridge_nokalman':'score'})
V['model']='V2_255';R['model']='RIDGE_2026'
scores=pd.concat([V[['date','ticker','score','model']],R[['date','ticker','score','model']]],ignore_index=True)
months=[];age=[];bins=[];bad=[]
for (model,date),g in scores.groupby(['model','date'],sort=True):
    if date not in by_date:continue
    e,x=by_date[date]
    if x>=len(D):continue
    gg=g.set_index('ticker').reindex(tick)
    scr=gg.score.to_numpy(float)
    valid=np.isfinite(scr)&np.isfinite(P[e])&np.isfinite(P[x])&(P[e]>0)&(P[x]>0)
    if valid.sum()!=149:
        bad.append((model,date,int(valid.sum())))
        continue
    actual=P[x]/P[e]-1.
    ic=float(spearmanr(scr,actual).statistic)
    bycat=[]
    for c in np.unique(cat):
        mk=(cat==c)&valid
        if mk.sum()>=5:
            bycat.append((int(mk.sum()),float(spearmanr(scr[mk],actual[mk]).statistic)))
    cat_ic=float(np.average([v for _,v in bycat],weights=[w for w,_ in bycat]))
    order=np.argsort(-scr,kind='stable')
    k=10 if model=='V2_255' else 15
    chosen=order[:k]
    if model=='RIDGE_2026':
        bi=[i for i,(d,_,__) in enumerate(blocks) if d==date][0]
        held=np.flatnonzero(wr[bi,:149]>0)
        if set(held)!=set(chosen):bad.append((model,date,'portfolio mismatch'))
        assert set(held)==set(chosen),'Archived Ridge scores mismatch frozen portfolio'
    top=float(np.mean(actual[chosen]))
    market=float(np.mean(actual))
    spy=float(actual[position['SPY']])
    residual=np.zeros(len(tick))
    for c in np.unique(cat):
        residual[cat==c]=actual[cat==c]-np.mean(actual[cat==c])
    cat_residual=float(np.mean(residual[chosen]))
    quint=pd.qcut(pd.Series(scr).rank(method='first'),5,labels=False).to_numpy()
    for q in range(5):
        mem=(quint==q)
        bins.append(dict(model=model,signal_date=date,bin_low_to_high=q+1,member_count=int(mem.sum()),
                         forward_return_mean=float(actual[mem].mean()),
                         forward_category_residual_mean=float(residual[mem].mean())))
    months.append(dict(model=model,signal_date=date,entry=str(D[e].date()),exit=str(D[x].date()),sessions=x-e,
        spearman_all=ic,spearman_within_category=cat_ic,
        top_k=k,top_gross=top,universe_gross=market,spy_gross=spy,
        top_minus_universe=top-market,top_minus_spy=top-spy,top_minus_category=cat_residual,
        top_positive_fraction=float(np.mean(actual[chosen]>0)),
        universe_positive_fraction=float(np.mean(actual>0))))
    for h in [1,3,5,10,15,20]:
        if e+h>x:continue
        if not (np.isfinite(P[e+h]).all() and (P[e+h]>0).all()):continue
        hr=P[e+h]/P[e]-1.
        age.append(dict(model=model,signal_date=date,horizon_sessions=h,
            top_k_vs_spy=float(hr[chosen].mean()-hr[position['SPY']]),
            top_k_vs_universe=float(hr[chosen].mean()-hr.mean()),
            score_ic=float(spearmanr(scr,hr).statistic)))
if bad:
    pd.DataFrame(bad).to_csv(OUT/'invalid_or_mismatched_months.csv',index=False)
assert not bad,f'Missing series or mismatch for {len(bad)} months, first {bad[:3]}'
m=pd.DataFrame(months).sort_values(['model','signal_date'])
a=pd.DataFrame(age)
q=pd.DataFrame(bins)
m.to_csv(OUT/'monthly_rank_and_pnl.csv',index=False)
a.to_csv(OUT/'signal_age_horizons.csv',index=False)
q.to_csv(OUT/'score_quintiles_monthly.csv',index=False)
rng=np.random.default_rng(20261030)
def ci_block(data,size=6,B=5000):
    vals=np.array(data,float);N=len(vals)
    ix=((rng.integers(0,N,size=(B,ceil(N/size),1))+np.arange(size))%N).reshape(B,-1)[:,:N]
    return np.quantile(vals[ix].mean(axis=1),[.025,.975]).tolist()
summary=[];QA=[]
for model,g in m.groupby('model'):
    for label,sub in [('all',g),('2018-2022',g[g.signal_date<'2023-01-01']),
                      ('2023-2024',g[(g.signal_date>='2023-01-01')&(g.signal_date<'2025-01-01')]),
                      ('2025-2026',g[g.signal_date>='2025-01-01'])]:
        if len(sub)<3:continue
        for metric in ['spearman_all','spearman_within_category','top_minus_universe','top_minus_spy','top_minus_category']:
            ci=ci_block(sub[metric])
            summary.append(dict(model=model,period=label,months=len(sub),metric=metric,
              mean=float(sub[metric].mean()),ci95_low=float(ci[0]),ci95_high=float(ci[1]),
              positive_month_fraction=float(np.mean(sub[metric]>0))))
    qa=float(pearsonr(g.spearman_all,g.top_minus_spy).statistic)
    qar=float(pearsonr(g.spearman_within_category,g.top_minus_category).statistic)
    QA.append(dict(model=model,n_months=len(g),corr_crosssection_IC_vs_portfolio_active=qa,
        corr_category_IC_vs_top_category_residual=qar,
        ic_positive_and_active_negative=int(((g.spearman_all>0)&(g.top_minus_spy<=0)).sum()),
        ic_negative_and_active_positive=int(((g.spearman_all<=0)&(g.top_minus_spy>0)).sum()),
        both_positive=int(((g.spearman_all>0)&(g.top_minus_spy>0)).sum()),
        both_negative=int(((g.spearman_all<=0)&(g.top_minus_spy<=0)).sum())))
pd.DataFrame(summary).to_csv(OUT/'block_bootstrap_summary.csv',index=False)
common=m.pivot(index='signal_date',columns='model',
               values=['spearman_all','top_minus_spy','top_minus_category']).dropna()
for met in ['spearman_all','top_minus_spy','top_minus_category']:
    diff=common[met]['RIDGE_2026']-common[met]['V2_255']
    ci=ci_block(diff)
    QA.append(dict(model='RIDGE_MINUS_V2',n_months=len(diff),metric=met,
                   difference=float(diff.mean()),ci95_low=ci[0],ci95_high=ci[1]))
pd.DataFrame(QA).to_csv(OUT/'ic_vs_realized_pnl.csv',index=False)
qu=q.groupby(['model','bin_low_to_high']).agg(n_months=('signal_date','nunique'),
    mean_return=('forward_return_mean','mean'),mean_category_excess=('forward_category_residual_mean','mean')).reset_index()
qu.to_csv(OUT/'score_quintile_summary.csv',index=False)
ages=a.groupby(['model','horizon_sessions']).agg(months=('signal_date','size'),
    avg_top_vs_spy=('top_k_vs_spy','mean'),
    avg_top_vs_universe=('top_k_vs_universe','mean'),avg_ic=('score_ic','mean')).reset_index()
ages.to_csv(OUT/'signal_age_horizon_summary.csv',index=False)
files={'prices':PZIP,'v2_scores':VZIP,'ridge_scores':RZIP,'frozen_weights':WFILE}
manifest={'analysis_date':'2026-10-30',
    'inputs_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()},
    'n_etfs':149,'models':{model:int(len(g)) for model,g in m.groupby('model')},
    'common_months':len(common),'no_training_or_parameter_search':True,
    'prices_last_date':str(D[-1].date()),
    'research_contamination':'Historical data reused in prior model search; descriptive audit, NOT independent OOS.'}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
print(pd.DataFrame(summary).query('period=="all"').round(4).to_string(index=False))
print(pd.DataFrame(QA).round(4).to_string(index=False))
