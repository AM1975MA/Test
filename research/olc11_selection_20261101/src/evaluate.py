"""Evaluate the question answered by each layer; no portfolio or CAGR optimization."""
from pathlib import Path
import json
import numpy as np,pandas as pd
from layer_metrics import ranking_metrics,opportunity_metrics,compose,ndcg,economic_relevance,rank_ic
from objectives import top_event,probability_metrics
from recovery_core import atomic_json
from prepare import readcsv
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'inputs';O=ROOT/'results'
SEEDS=[101,211,307]
VARIANTS=['ARCHIVED_REG','MATCHED_REG','ET_CLASS','XGB_CLASS','BOTH_CLASS','XGB_RANK','RANK_ONLY']

def period_ok(date,exitdate,period):
    if pd.isna(exitdate):return False
    if period=='PRE2025':return pd.Timestamp('2021-01-01')<=date<pd.Timestamp('2025-01-01') and exitdate<pd.Timestamp('2025-01-01')
    if period=='Y2025':return date.year==2025 and exitdate<pd.Timestamp('2026-01-01')
    if period=='Y2026_PARTIAL':return date.year==2026 and exitdate<=pd.Timestamp('2026-07-01')
    if period=='ALL_ACTIVE':return date>=pd.Timestamp('2021-01-01') and exitdate<=pd.Timestamp('2026-07-01')
    raise ValueError(period)

def records(market):
    out={}
    for seed in SEEDS:
        name='R_RSI_DOMAIN' if seed==101 else f'REF42_S{seed}'
        ref=readcsv(I/f'{market}_{name}_FORECASTS.csv.gz')
        new=readcsv(O/f'{market}_S{seed}_PREDICTIONS.csv.gz')
        f=ref.rename(columns={'ET_RAW':'ARCH_ET','XGB_RAW':'ARCH_XGB'}).merge(new,on=['signal_date','ticker'],how='left',validate='one_to_one').sort_values(['signal_date','ticker']).reset_index(drop=True)
        for col in ['ET_REG','XGB_REG','ET_CLASS','XGB_CLASS','XGB_RANK']:
            assert np.array_equal(f[col].isna(),f.ARCH_ET.isna())
        assert (f.source_date.dropna()<=f.loc[f.source_date.notna(),'signal_date']).all()
        out[str(seed)]=f
    mean=out['101'].copy()
    for col in ['ARCH_ET','ARCH_XGB','ET_REG','XGB_REG','ET_CLASS','XGB_CLASS','XGB_RANK']:
        arr=np.stack([out[str(s)][col].to_numpy() for s in SEEDS]);valid=np.isfinite(arr).all(0)
        mean[col]=np.where(valid,np.where(np.isfinite(arr),arr,0).mean(0),np.nan)
    out['MEAN3']=mean
    return out

def score_frame(f,variant):
    pairs={'ARCHIVED_REG':('ARCH_ET','ARCH_XGB'),'MATCHED_REG':('ET_REG','XGB_REG'),
           'ET_CLASS':('ET_CLASS','XGB_REG'),'XGB_CLASS':('ET_REG','XGB_CLASS'),
           'BOTH_CLASS':('ET_CLASS','XGB_CLASS'),'XGB_RANK':('ET_REG','XGB_RANK'),
           'RANK_ONLY':('XGB_RANK','XGB_RANK')}
    a,b=pairs[variant];out=f[['signal_date','ticker','source_date','RETURN',a]].copy() if a!=b else f[['signal_date','ticker','source_date','RETURN']].copy()
    out=f[['signal_date','ticker','source_date','RETURN']].copy()
    out['E']=f.groupby('signal_date')[a].rank(pct=True,method='average')
    out['X']=f.groupby('signal_date')[b].rank(pct=True,method='average')
    dates=pd.DatetimeIndex(sorted(out.signal_date.unique()));tickers=sorted(out.ticker.unique())
    def mat(c):return out.pivot(index='signal_date',columns='ticker',values=c).reindex(index=dates,columns=tickers).to_numpy()
    current,smooth,final=compose(mat('RETURN'),mat('E'),mat('X'))
    for col,arr in [('CURRENT',current),('SMOOTH',smooth),('FUSION',final)]:
        di=dates.get_indexer(out.signal_date);ti=pd.Index(tickers).get_indexer(out.ticker)
        out[col]=arr[di,ti]
    out['EXPECTED_TARGET']=.6*f[a]+.4*f[b] if variant in ['ARCHIVED_REG','MATCHED_REG'] else np.nan
    out['PROBABILITY']=.6*f.ET_CLASS+.4*f.XGB_CLASS if variant=='BOTH_CLASS' else np.nan
    return out

def main():
    assert json.loads((O/'TRAINING_COMPLETE.json').read_text())['new_models']==240
    tm=[];om=[];pm=[];ex=[];decision=[];saved=[]
    audit=json.loads((O/'INPUT_AUDIT.json').read_text());priors={(r['market'],r['year']):r['prior_event_rate'] for r in audit}
    for market in ['EU','USA']:
        label=readcsv(I/f'{market}_LAYER_LABELS.csv.gz').drop(columns=['source_date'])
        for seed,f in records(market).items():
            native=f[np.isfinite(f.ARCH_ET)&np.isfinite(f.ARCH_XGB)].copy()
            cls=native.merge(label,on=['signal_date','ticker'],validate='one_to_one')
            for date,g in cls.groupby('signal_date'):
                if not np.isfinite(g.TARGET).all() or g.exit_date_63.isna().any():continue
                z=top_event(g.TARGET.to_numpy());prior=priors[(market,date.year)]
                for pred in ['ET_CLASS','XGB_CLASS','MEAN_PROB']:
                    p=(.6*g.ET_CLASS+.4*g.XGB_CLASS).to_numpy() if pred=='MEAN_PROB' else g[pred].to_numpy()
                    for period in ['PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE']:
                        if period_ok(date,g.exit_date_63.max(),period):pm.append(dict(market=market,seed=seed,predictor=pred,date=date,period=period,n=len(g),**probability_metrics(z,p,prior)))
            for variant in VARIANTS:
                s=score_frame(f,variant);s=s.merge(label,on=['signal_date','ticker'],how='left',validate='one_to_one')
                if seed=='MEAN3':
                    s.to_csv(O/f'{market}_{variant}_MEAN3_OUTPUTS.csv.gz',index=False,compression='gzip');saved.append((market,variant,len(s)))
                for date,g0 in s.groupby('signal_date'):
                    # Same real-time support for all compared stages and candidates.
                    g=g0[np.isfinite(g0.CURRENT)&np.isfinite(g0.RETURN)].copy()
                    if len(g)<20:continue
                    ok_target=np.isfinite(g.TARGET).all() and g.exit_date_63.notna().all()
                    if not ok_target and seed=='MEAN3' and variant=='MATCHED_REG':ex.append(dict(market=market,date=date,reason='incomplete_target_outcomes',candidates=len(g),missing=int(g.TARGET.isna().sum())))
                    for stage in ['CURRENT','SMOOTH','FUSION']:
                        score=g[stage].to_numpy()
                        if not np.isfinite(score).all():raise AssertionError('Mismatched stage support')
                        if ok_target:
                            stats=ranking_metrics(g.TARGET.to_numpy(),score)
                            mse=float(np.mean((g.EXPECTED_TARGET-g.TARGET)**2)) if variant in ['ARCHIVED_REG','MATCHED_REG'] and stage=='CURRENT' else np.nan
                            for period in ['PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE']:
                                if period_ok(date,g.exit_date_63.max(),period):tm.append(dict(market=market,variant=variant,seed=seed,stage=stage,period=period,date=date,n=len(g),last_exit=g.exit_date_63.max(),mse=mse,**stats))
                        for h in [21,42,63]:
                            ret=g[f'fwd_ret_{h}'];exitdate=g[f'exit_date_{h}']
                            if not np.isfinite(ret).all() or exitdate.isna().any():continue
                            stats=opportunity_metrics(ret.to_numpy(),score)
                            stats['economic_ndcg2']=ndcg(economic_relevance(ret.to_numpy()),score,2)
                            for period in ['PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE']:
                                if period_ok(date,exitdate.max(),period):om.append(dict(market=market,variant=variant,seed=seed,stage=stage,period=period,date=date,horizon=h,n=len(g),last_exit=exitdate.max(),**stats))
                        if seed=='MEAN3':
                            # Inspectable deterministic display only; summary metrics handle ties by expectation.
                            top=g.assign(score=score).sort_values(['score','ticker'],ascending=[False,True]).head(2)
                            for order,row in enumerate(top.itertuples(),1):decision.append(dict(market=market,variant=variant,stage=stage,date=date,position=order,ticker=row.ticker,score=row.score,n=len(g),TARGET=row.TARGET,fwd21=row.fwd_ret_21,fwd63=row.fwd_ret_63))
            print('EVALUATED',market,seed,'target_rows',len(tm),'opportunity_rows',len(om),flush=True)
    t=pd.DataFrame(tm);o=pd.DataFrame(om);p=pd.DataFrame(pm)
    t.to_csv(O/'TARGET_MONTHS.csv',index=False);o.to_csv(O/'OPPORTUNITY_MONTHS.csv',index=False);p.to_csv(O/'PROBABILITY_MONTHS.csv',index=False)
    pd.DataFrame(ex).to_csv(O/'EXCLUDED_MONTHS.csv',index=False);pd.DataFrame(decision).to_csv(O/'TOP2_DECISIONS.csv',index=False)
    group=['market','variant','seed','stage','period'];metrics=['ndcg2','ndcg5','ic','target_regret','selected_target','target_top_quintile_precision','target_bottom_quintile_fraction','mse']
    t.groupby(group).agg(months=('date','nunique'),**{m:(m,'mean') for m in metrics}).reset_index().to_csv(O/'TARGET_SUMMARY.csv',index=False)
    metrics=['top2_return','top2_excess','top2_regret','selected_negative_return','bottom_quintile_fraction','top5_capture','economic_ndcg2']
    o.groupby(group+['horizon']).agg(months=('date','nunique'),**{m:(m,'mean') for m in metrics}).reset_index().to_csv(O/'OPPORTUNITY_SUMMARY.csv',index=False)
    p.groupby(['market','seed','predictor','period']).agg(months=('date','nunique'),**{m:(m,'mean') for m in ['brier','logloss','prior_brier','prior_logloss','mean_probability','event_rate']}).reset_index().to_csv(O/'PROBABILITY_SUMMARY.csv',index=False)
    atomic_json(O/'EVALUATION_COMPLETE.json',{'target_month_rows':len(t),'opportunity_month_rows':len(o),'probability_month_rows':len(p),'mean_ensemble_outputs':saved,'new_portfolios':0,'primary':'CURRENT, MEAN3, PRE2025; paired with MATCHED_REG','note':'Static forward excess payoffs are not compounded returns or CAGR; rank outputs are not probabilities.'})
    print('EVALUATION_DONE',len(t),len(o),len(p),flush=True)
if __name__=='__main__':main()
