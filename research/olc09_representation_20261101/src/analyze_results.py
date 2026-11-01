"""Matched information/representation/seed contrasts; no selection of best seed."""
from bridge import *
from replay_models import source,ARCHIVE
from train_models import CONFIGS
import importlib.util
_spec=importlib.util.spec_from_file_location('_olc09_parent_evidence',PARENT/'src/evidence_math.py')
_evidence=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_evidence)
daily_log,circular_weights,score_month=_evidence.daily_log,_evidence.circular_weights,_evidence.score_month
import numpy as np,pandas as pd,json
OUT=ROOT/'results';PATHS=OUT/'paths'

def contrast_specs(variants):
    specs=[('versus_reference',v,'REF_RSI') for v in variants if v!='REF_RSI']
    for prefix,core,path,nulls in [('fraction','FRACTION_CORE','FRACTION_PATH',[f'FRACTION_NULL{s}' for s in [7101,7102,7103]]),('fixed','FIXED_CORE_S101','FIXED_PATH_S101',[f'FIXED_NULL{s}_S101' for s in [7101,7102,7103]]),('all','ALL_CORE_S101','ALL_PATH_S101',[f'ALL_NULL{s}_S101' for s in [7101,7102,7103]])]:
        specs.append(('path_vs_core',path,core))
        specs += [(f'path_vs_shuffled_{prefix}',path,n) for n in nulls]
    for pack in ['CORE','PATH']:
        specs.append(('sampling_budget',f'FIXED_{pack}_S101',f'FRACTION_{pack}'))
        specs.append(('sampling_budget',f'ALL_{pack}_S101',f'FIXED_{pack}_S101'))
    for seed in [101,211,307]:specs.append(('seed_matched_path',f'FIXED_PATH_S{seed}',f'FIXED_CORE_S{seed}'))
    specs += [('seed_matched_path','ENSEMBLE_FIXED_PATH','ENSEMBLE_FIXED_CORE'),('ensemble_vs_same_seed_baseline','ENSEMBLE_FIXED_PATH','ENSEMBLE_REF42'),('ensemble_vs_same_seed_baseline','ENSEMBLE_FIXED_CORE','ENSEMBLE_REF42')]
    return specs

def main():
    sc=pd.read_csv(OUT/'SCORECARD.csv');variants=list(sc.variant.unique());dec=pd.read_csv(OUT/'DECISIONS.csv')
    monthly={};yearly=[]
    for row in pd.read_csv(OUT/'REPLAY_CHECKS.csv').itertuples():
        z=np.load(PATHS/f'{row.config}.npz',allow_pickle=False);dates=pd.DatetimeIndex(z['dates'])[1:];logs=daily_log(z['nav'])[:-1]
        monthly[row.config]=pd.Series(logs,index=dates).groupby(dates.to_period('M')).sum()
        for y,part in pd.Series(logs,index=dates).groupby(dates.year):yearly.append({'config':row.config,'year':int(y),'period_return':float(np.expm1(part.sum())),'intervals':len(part)})
    pd.DataFrame(monthly).to_csv(OUT/'MONTHLY_LOG_RETURNS.csv',index_label='month');pd.DataFrame(yearly).to_csv(OUT/'ANNUAL_RETURNS.csv',index=False)
    specs=contrast_specs(variants);confidence=[];concentration=[]
    for fee in [.001,.003]:
        for policy in ['IMMEDIATE','DELAY3','PHASE5']:
            xs=[];ls=[]
            for family,v,b in specs:
                for m in ['EU','USA']:
                    a=f'{m}_{v}_{policy}_C{round(fee*10000)}';bb=f'{m}_{b}_{policy}_C{round(fee*10000)}'
                    x=(monthly[a]-monthly[bb]).loc['2021-01':'2024-12'];assert len(x)==48
                    xs.append(x);ls.append((family,m,v,b))
                    if family=='path_vs_core':
                        excluded=x.nlargest(3).index;remaining=x.drop(excluded)
                        concentration.append(dict(market=m,variant=v,comparator=b,policy=policy,fee=fee,annual_log_pp=x.mean()*1200,without_best3_annual_log_pp=remaining.mean()*1200,excluded_months=';'.join(map(str,excluded)),status='post-outcome_concentration_diagnostic_not_trading_rule'))
            X=pd.concat(xs,axis=1).to_numpy();assert np.isfinite(X).all()
            for block in [3,6]:
                w=circular_weights(48,block,6000,20261101);draws=w@X*1200;point=X.mean(0)*1200;sd=draws.std(0,ddof=1)
                families=sorted(set(x[0] for x in ls));crit={}
                for fam in families:
                    idx=[j for j,l in enumerate(ls) if l[0]==fam and sd[j]>1e-12]
                    crit[fam]=float(np.quantile(np.max(abs((draws[:,idx]-point[idx])/sd[idx]),axis=1),.95)) if idx else 0.
                for j,(fam,m,v,b) in enumerate(ls):
                    lo,hi=np.quantile(draws[:,j],[.025,.975])
                    confidence.append(dict(family=fam,market=m,variant=v,comparator=b,policy=policy,fee=fee,block_months=block,months=48,resamples=6000,annual_log_pp=point[j],ci95_low_pp=lo,ci95_high_pp=hi,simultaneous_low_pp=point[j]-crit[fam]*sd[j],simultaneous_high_pp=point[j]+crit[fam]*sd[j],resampling_positive_fraction=float((draws[:,j]>0).mean()),family_contrasts=sum(x[0]==fam for x in ls)))
    pd.DataFrame(confidence).to_csv(OUT/'PAIRED_UNCERTAINTY.csv',index=False);pd.DataFrame(concentration).to_csv(OUT/'CONCENTRATION.csv',index=False)
    predrows=[]
    for m in ['EU','USA']:
        cp=pd.read_pickle(parent_bootstrap.CAL/f'{m}_COMPACT.pkl')
        labels=cp[['signal_date','ticker','exit_date_21','fwd_ret_21','exit_date_63','fwd_ret_63']]
        supports={}
        for v in variants:
            p=pd.read_csv(source(m,v),parse_dates=['signal_date'],float_precision='round_trip');p['HYBRID_CURRENT']=.6*p.ET+.4*p.XGB
            c=pd.read_csv(OUT/f'{m}_{v}_COMBINED.csv',index_col=0,parse_dates=True,float_precision='round_trip');c.index.name='signal_date';c.columns.name='ticker'
            p=p.merge(c.stack(future_stack=True).rename('COMBINED').reset_index(),on=['signal_date','ticker'],validate='one_to_one').merge(labels,on=['signal_date','ticker'],validate='one_to_one')
            for h in [21,63]:
                a=p[(p.signal_date>='2021-01-01')&(p[f'exit_date_{h}']<'2025-01-01')].copy()
                a=a[a[['RETURN','HYBRID_CURRENT','COMBINED',f'fwd_ret_{h}']].notna().all(axis=1)]
                keys=key_hash(a.sort_values(['signal_date','ticker']))
                if h not in supports:supports[h]=keys
                else:assert keys==supports[h]
                for date,g in a.groupby('signal_date'):
                    for s in ['HYBRID_CURRENT','COMBINED']:
                        predrows.append(dict(market=m,variant=v,signal_date=str(date.date()),horizon=h,score=s,**score_month(g,s,f'fwd_ret_{h}')))
    p=pd.DataFrame(predrows);p.to_csv(OUT/'PREDICTIVE_MONTHS.csv',index=False)
    p.groupby(['market','variant','horizon','score']).agg(months=('signal_date','nunique'),mean_candidates=('n','mean'),rank_ic=('rank_ic','mean'),top2_return=('top2_return','mean'),top2_excess=('top2_excess','mean'),top5_overlap=('top5_overlap','mean')).reset_index().to_csv(OUT/'PREDICTIVE_SUMMARY.csv',index=False)
    change=[]
    for m in ['EU','USA']:
        for v,b in [('REVERSE42_S101','REF_RSI')]+[(x,'REF_RSI') for x in variants if x not in ['REF_RSI','REVERSE42_S101']]+[(f'FIXED_PATH_S{s}',f'FIXED_CORE_S{s}') for s in [101,211,307]]:
            ref=dec[(dec.market==m)&(dec.variant==b)].set_index('signal_date');cur=dec[(dec.market==m)&(dec.variant==v)].set_index('signal_date').reindex(ref.index)
            pairs=[set(a)!=set(b) for a,b in zip(cur[['first','second']].to_numpy(),ref[['first','second']].to_numpy())]
            change.append(dict(market=m,variant=v,comparator=b,months=len(ref),first_changed=int((cur['first']!=ref['first']).sum()),pair_changed=int(sum(pairs))))
    pd.DataFrame(change).to_csv(OUT/'DECISION_CHANGES.csv',index=False)
    seedrows=[]
    for family,patterns in [('REF42',['REF_RSI','REF42_S211','REF42_S307']),('FIXED_CORE',[f'FIXED_CORE_S{s}' for s in [101,211,307]]),('FIXED_PATH',[f'FIXED_PATH_S{s}' for s in [101,211,307]])]:
        z=sc[sc.variant.isin(patterns)]
        for keys,g in z.groupby(['market','policy','fee','period']):
            seedrows.append(dict(family=family,market=keys[0],policy=keys[1],fee=keys[2],period=keys[3],seeds=len(g),cagr_min=g.cagr.min(),cagr_max=g.cagr.max(),cagr_mean=g.cagr.mean(),cagr_std=g.cagr.std(),dd_min=g.maxdd.min(),dd_max=g.maxdd.max()))
    pd.DataFrame(seedrows).to_csv(OUT/'SEED_SPREAD.csv',index=False)
    for period in ['ACTIVE2021_2024','FULL','2025','2026']:
        sc[sc.period.eq(period)].to_csv(OUT/f'COMPARISON_{period}.csv',index=False)
    summary=json.loads((OUT/'REPLAY_SUMMARY.json').read_text());summary.update(configurations=len(variants),new_trained_models=544,reference_refits=4,unchanged_Return=True,primary_months=48,scope='Self review, reused history, fixed metadata; no all-data/all-market/live certification.')
    atomic_json(OUT/'SUMMARY.json',summary)
    print(json.dumps(summary,indent=2))
    print(sc.query("period=='ACTIVE2021_2024' and policy=='IMMEDIATE' and fee==.001").pivot(index='variant',columns='market',values=['cagr','maxdd']).to_string())
if __name__=='__main__':main()
