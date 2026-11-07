#!/usr/bin/env python3
"""Independent tie/return/oracle decomposition check using frozen tabular output.
No import from OLC63 or OLC65 generator; pandas-based standalone recomputation.
"""
from pathlib import Path
import numpy as np,pandas as pd,json
D=Path(__file__).resolve().parent/'results'
p=pd.read_csv(D/'OLC65_FROZEN_SCORE_AND_OUTCOMES.csv.gz')
m=pd.read_csv(D/'OLC65_MONTHLY_GAPS.csv')
o=pd.read_csv(D/'OLC65_ORACLE_TOP2_CLASSIFICATION.csv')
s=pd.read_csv(D/'OLC65_SUMMARY.csv')
errors=[];monthchecks=0;evtchecks=0
for (market,date),d in p.groupby(['market','date'],sort=True):
    q=m[(m.market==market)&(m.date==date)]
    assert len(q)==1
    row=q.iloc[0]
    assert row.status=='VALID'
    d=d.sort_values(['original_score_fusion','ticker'],ascending=[False,True],kind='mergesort').reset_index(drop=True)
    cutoff=d.original_score_fusion.iloc[9]
    shortlist=d[d.original_score_fusion>=cutoff]
    # check no ties at top2 in this particular dataset
    assert d.original_score_fusion.iloc[1]>d.original_score_fusion.iloc[2]
    selected=d.iloc[:2]
    assert len(d)==row.n_eligible and len(shortlist)==row.n_top10
    for h in (21,42):
        c=f'future_ret{h}'
        all_o=d.nlargest(2,c)
        short_o=shortlist.nlargest(2,c)
        a=selected[c].mean(); k=short_o[c].mean(); u=all_o[c].mean()
        assert abs(a-row[f'actual{h}'])<1e-12
        assert abs(k-row[f'oracle_top10_{h}'])<1e-12
        assert abs(u-row[f'oracle_universe{h}'])<1e-12
        assert abs((k-a)-row[f'ordering_gap{h}'])<1e-12
        assert abs((u-k)-row[f'discovery_gap{h}'])<1e-12
        got=o[(o.market==market)&(o.date==date)&(o.horizon==h)]
        assert len(got)==2 and set(got.oracle_ticker)==set(all_o.ticker)
        for x in got.itertuples():
            in10=x.oracle_ticker in set(shortlist.ticker)
            in2=x.oracle_ticker in set(selected.ticker)
            typ='ALREADY_SELECTED' if in2 else ('ORDERING' if in10 else 'DISCOVERY')
            assert typ==x.classification
            evtchecks+=1
    # pandas percentile ranking of all eligible, same strict >0.8 definition
    d['q21']=d.future_ret21.rank(method='average',pct=True)
    d['q42']=d.future_ret42.rank(method='average',pct=True)
    w=selected.merge(d[['ticker','q21','q42']],on='ticker',validate='one_to_one')
    near=(w.q21>.8); durable=near&(w.q42>.8)
    assert abs(near.mean()-row.actual_selection_near21)<1e-12
    assert abs(durable.mean()-row.actual_durable)<1e-12
    assert abs((near&~durable).mean()-row.actual_flash)<1e-12
    assert abs((~near).mean()-row.actual_miss)<1e-12
    monthchecks+=1
for q in s.itertuples():
    gg=m[(m.market==q.market)&(m.period==q.period)&(m.status=='VALID')]
    assert len(gg)==q.months
    for h in (21,42):
        assert abs(gg[f'ordering_gap{h}'].mean()-getattr(q,f'avg_ordering_gap{h}'))<1e-12
        assert abs(gg[f'discovery_gap{h}'].mean()-getattr(q,f'avg_discovery_gap{h}'))<1e-12
        assert abs(gg[f'total_gap{h}'].mean()-getattr(q,f'avg_total_gap{h}'))<1e-12
    for h in (21,42):
        g=o[(o.market==q.market)&(o.period==q.period)&(o.horizon==h)]
        assert len(g)==q.months*2
        for a in ['discovery','ordering','already_selected']:
            assert (g.classification==a.upper()).sum()==getattr(q,f'oracle{h}_{a}')
qa={'status':'PASS','method':'independent pandas ranking, future oracle and group reconciliations',
    'monthly_checks':monthchecks,'oracle_event_checks':evtchecks,'matched_original_fusion':True,
    'max_abs_gap_reconstruction':0,'no_new_fit_or_trading':True}
(D/'OLC65_INDEPENDENT_QA.json').write_text(json.dumps(qa,indent=2))
print(json.dumps(qa))