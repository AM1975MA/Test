"""Diagnostic of existing layer boundaries, not new strategy selection or tuning."""
from run_experiment import ROOT,I,O,readcsv,prepare_labels,merged,opportunity_rows,in_period
from layer_metrics import compose,ranking_metrics
from recovery_core import atomic_json
import pandas as pd,numpy as np,zipfile
rows=[];rankrows=[];counts=[];parity=[]
for market in ['EU','USA']:
    labels=prepare_labels(market);f=merged(market,'REF_RSI',labels)
    dates=sorted(f.signal_date.unique());names=sorted(f.ticker.unique())
    def matrix(col):return f.pivot(index='signal_date',columns='ticker',values=col).reindex(index=dates,columns=names).to_numpy(float)
    current,smooth,fusion=compose(matrix('RETURN'),matrix('ET'),matrix('XGB'))
    data=f.copy()
    for name,x in [('H_CURRENT',current),('H_SMOOTHED',smooth),('FUSION',fusion)]:
        z=pd.DataFrame(x,index=pd.Index(dates,name='signal_date'),columns=pd.Index(names,name='ticker')).stack(future_stack=True).rename(name).reset_index()
        data=data.merge(z,on=['signal_date','ticker'],validate='one_to_one')
    # Same ex-ante support across every boundary. Return is not measured on a different set here.
    support=np.isfinite(data[['RETURN','H_CURRENT','H_SMOOTHED','FUSION']]).all(axis=1)
    for date,g in data.groupby('signal_date'):
        eligible=g[np.isfinite(g[['RETURN','H_CURRENT','H_SMOOTHED','FUSION']]).all(axis=1)]
        counts.append({'market':market,'date':str(date.date()),'forecast_rows':len(g),'common_predictable':len(eligible),'target_observed':int(np.isfinite(eligible.TARGET).sum()),'target_complete':bool(np.isfinite(eligible.TARGET).all()),'future_label_used_for_selection':False})
    data=data[support]
    for col in ['RETURN','H_CURRENT','H_SMOOTHED','FUSION']:
        rows+=opportunity_rows(market,col,data,col)
        for date,g in data.groupby('signal_date'):
            if len(g)<20 or not np.isfinite(g.TARGET).all() or not g.exit_date_63.notna().all():continue
            metrics=ranking_metrics(g.TARGET.to_numpy(),g[col].to_numpy())
            for period in ['PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE']:
                if in_period(date,g.exit_date_63.max(),period):rankrows.append(dict(market=market,layer=col,period=period,date=str(date.date()),n=len(g),**metrics))
    data.to_csv(O/f'{market}_INTEGRATED_LAYER_OUTPUTS.csv.gz',index=False,compression='gzip')
    archived=pd.read_csv(I/f'{market}_REFERENCE_COMBINED.csv',index_col=0,parse_dates=True,float_precision='round_trip').reindex(index=pd.to_datetime(dates),columns=names)
    np.testing.assert_allclose(fusion,archived.to_numpy(),rtol=0,atol=0,equal_nan=True)
    parity.append(dict(market=market,archived_score_cells=archived.size,exact=True))
pd.DataFrame(rows).to_csv(O/'BOUNDARY_OPPORTUNITY_MONTHS.csv',index=False)
pd.DataFrame(rankrows).to_csv(O/'BOUNDARY_TARGET_RANK_MONTHS.csv',index=False)
pd.DataFrame(counts).to_csv(O/'COVERAGE_EXCLUSIONS.csv',index=False)
atomic_json(O/'COMPOSITION_PARITY.json',parity)
a=pd.DataFrame(rows);metrics=[c for c in a if c not in ['market','variant','period','date','last_exit','horizon','n']]
s=a.groupby(['market','variant','period','horizon'])[metrics].mean().reset_index();s.to_csv(O/'BOUNDARY_OPPORTUNITY_SUMMARY.csv',index=False)
r=pd.DataFrame(rankrows);r.groupby(['market','layer','period']).agg(months=('date','nunique'),ndcg2=('ndcg2','mean'),ndcg5=('ndcg5','mean'),ic=('ic','mean'),top_quintile_precision=('target_top_quintile_precision','mean')).reset_index().to_csv(O/'BOUNDARY_TARGET_SUMMARY.csv',index=False)
print(s[(s.period=='PRE2025')&s.horizon.isin([21,63])].to_string(index=False));print(parity)
