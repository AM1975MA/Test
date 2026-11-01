"""Independent paired portfolio and predictor summaries; no training or rule selection."""
from bootstrap import *
from evidence_math import *
from replay_pack import forecast_path
from train_pack import VARS
import numpy as np,pandas as pd,json
OUT=ROOT/'results';PATHS=OUT/'paths'

def analyze(variants):
    sc=pd.read_csv(OUT/'SCORECARD.csv');dec=pd.read_csv(OUT/'DECISIONS.csv')
    monthly={};metrics=[];yearly=[]
    for row in pd.read_csv(OUT/'REPLAY_CHECKS.csv').itertuples():
        z=np.load(PATHS/f'{row.config}.npz',allow_pickle=False)
        dates=pd.DatetimeIndex(z['dates'])[1:];logs=daily_log(z['nav'])[:-1]
        month=pd.Series(logs,index=dates).groupby(dates.to_period('M')).sum()
        monthly[row.config]=month
        for period,part in pd.Series(logs,index=dates).groupby(dates.year):yearly.append({'config':row.config,'year':int(period),'period_return':float(np.expm1(part.sum())),'intervals':len(part)})
    pd.DataFrame(monthly).to_csv(OUT/'MONTHLY_LOG_RETURNS.csv',index_label='month')
    pd.DataFrame(yearly).to_csv(OUT/'ANNUAL_RETURNS.csv',index=False)
    confidence=[]
    for fee in [.001,.003]:
      for policy in ['IMMEDIATE','DELAY3','PHASE5']:
        series=[];labels=[]
        contrasts=[(v,'REF_RSI') for v in variants if v not in ['LEGACY','REF_RSI']]
        if 'H_PATH' in variants and 'H_UNIQUE' in variants:contrasts.append(('H_PATH','H_UNIQUE'))
        if 'H_SESSION' in variants and 'H_UNIQUE' in variants:contrasts.append(('H_SESSION','H_UNIQUE'))
        for v,base in contrasts:
          for market in ['EU','USA']:
            k=f'{market}_{v}_{policy}_C{round(fee*10000)}';b=f'{market}_{base}_{policy}_C{round(fee*10000)}'
            series.append((monthly[k]-monthly[b]).loc['2021-01':'2024-12']);labels.append((market,v,base))
        if not series:continue
        x=pd.concat(series,axis=1,join='inner').dropna().to_numpy();assert len(x)==48
        for block in [3,6]:
            weights=circular_weights(len(x),block,6000,20261101)
            draws=(weights@x)*1200;point=x.mean(0)*1200;sd=draws.std(0,ddof=1)
            active=sd>1e-12;critical=np.quantile(np.max(np.abs((draws[:,active]-point[active])/sd[active]),axis=1),.95) if active.any() else 0
            for j,(market,v,base) in enumerate(labels):
                low,high=np.quantile(draws[:,j],[.025,.975])
                confidence.append(dict(market=market,variant=v,comparator=base,policy=policy,fee=fee,block_months=block,months=len(x),resamples=6000,annual_log_pp=point[j],ci95_low_pp=low,ci95_high_pp=high,simultaneous_family_low_pp=point[j]-critical*sd[j],simultaneous_family_high_pp=point[j]+critical*sd[j],resampling_positive_fraction=float((draws[:,j]>0).mean()),family_contrasts=len(labels)))
    pd.DataFrame(confidence).to_csv(OUT/'PAIRED_UNCERTAINTY.csv',index=False)
    # Predictive scoring is at original monthly signal dates with only completed forward labels.
    predrows=[]
    for market in ['EU','USA']:
        cp=pd.read_pickle(CAL/f'{market}_COMPACT.pkl')
        labels=cp[['signal_date','ticker','exit_date_21','fwd_ret_21','exit_date_63','fwd_ret_63']]
        for variant in variants:
            p=pd.read_csv(forecast_path(market,variant),parse_dates=['signal_date'],float_precision='round_trip')
            p['HYBRID_CURRENT']=.6*p.ET+.4*p.XGB
            c=pd.read_csv(OUT/f'{market}_{variant}_COMBINED.csv',index_col=0,parse_dates=True,float_precision='round_trip')
            c.index.name='signal_date';c.columns.name='ticker'
            co=c.stack(future_stack=True).rename('COMBINED').reset_index()
            p=p.merge(co,on=['signal_date','ticker'],validate='one_to_one').merge(labels,on=['signal_date','ticker'],validate='one_to_one')
            for h in [21,63]:
                # Evaluation conditioning identical across variants, not a rule for current selection.
                a=p[(p.signal_date>='2021-01-01')&(p[f'exit_date_{h}']<'2025-01-01')].copy()
                a=a[a[['RETURN','HYBRID_CURRENT','COMBINED',f'fwd_ret_{h}']].notna().all(axis=1)]
                for date,g in a.groupby('signal_date'):
                    for score in ['RETURN','HYBRID_CURRENT','COMBINED']:
                        predrows.append(dict(market=market,variant=variant,signal_date=str(date.date()),horizon=h,score=score,**score_month(g,score,f'fwd_ret_{h}')))
    pred=pd.DataFrame(predrows);pred.to_csv(OUT/'PREDICTIVE_MONTHS.csv',index=False)
    pred.groupby(['market','variant','horizon','score']).agg(months=('signal_date','nunique'),mean_candidates=('n','mean'),rank_ic=('rank_ic','mean'),top2_return=('top2_return','mean'),top2_excess=('top2_excess','mean'),top5_overlap=('top5_overlap','mean')).reset_index().to_csv(OUT/'PREDICTIVE_SUMMARY.csv',index=False)
    # Decision changes relative to RSI reference, not to an accidental renamed baseline.
    changes=[]
    for market in ['EU','USA']:
        ref=dec[(dec.market==market)&(dec.variant=='REF_RSI')].set_index('signal_date')
        for v in variants:
            cur=dec[(dec.market==market)&(dec.variant==v)].set_index('signal_date').reindex(ref.index)
            first=(ref['first']!=cur['first']);pair=[set(a)!=set(b) for a,b in zip(ref[['first','second']].values,cur[['first','second']].values)]
            changes.append({'market':market,'variant':v,'months':len(ref),'first_changed':int(first.sum()),'pair_changed':int(sum(pair))})
    pd.DataFrame(changes).to_csv(OUT/'DECISION_CHANGES.csv',index=False)
    audits=[];pruned=[]
    for p in (ROOT/'models').glob('*/*/*/audit.json'):
        a=json.loads(p.read_text());audits.append({k:a[k] for k in ['market','variant','year','n_return_train','n_hybrid_train','last_exit_return','last_exit_hybrid']}|{'return_features':len(a['return_columns']),'hybrid_features':len(a['hybrid_columns']),'new_models':len(a['trained_models'])})
        for r in a['pruning']:pruned.append({'market':a['market'],'variant':a['variant'],'year':a['year'],**r})
    pd.DataFrame(audits).to_csv(OUT/'ANNUAL_FIT_AUDIT.csv',index=False);pd.DataFrame(pruned).to_csv(OUT/'TRAIN_ONLY_PRUNING.csv',index=False)
    for period in ['ACTIVE2021_2024','FULL','2025','2026']:
        sc[(sc.period==period)&sc.policy.eq('DELAY3')].to_csv(OUT/f'COMPARISON_{period}_DELAY3.csv',index=False)
    summary=json.loads((OUT/'REPLAY_SUMMARY.json').read_text())
    summary.update(new_models=sum(a['new_models'] for a in audits),annual_fit_batches=len(audits),variants=variants,predictive_month_rows=len(pred),uncertainty='Exploratory paired common-month bootstrap, not posterior and not correction for all previous studies.',new_information='New representations of existing observed prices/ranks, not new external sources.')
    atomic_json(OUT/'VERIFIED_SUMMARY.json',summary)
    print(json.dumps(summary,indent=2))
    print(sc.query("period=='ACTIVE2021_2024' and policy=='DELAY3' and fee==.001").pivot(index='variant',columns='market',values=['cagr','maxdd']).to_string())
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--variants',default='LEGACY,REF_RSI,'+','.join(VARS));a=ap.parse_args();analyze(a.variants.split(','))
