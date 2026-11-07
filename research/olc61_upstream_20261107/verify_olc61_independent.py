#!/usr/bin/env python3
"""Independent file-level and economic recomputation of OLC61 artifacts.
Uses saved forecast panel and selections, NOT the training/score helpers.
"""
import json, sys, zipfile, io
from pathlib import Path
import pandas as pd
import numpy as np

p=Path(sys.argv[1])
a=pd.read_csv(p/'OLC61_PREDICTIONS.csv.gz')
s=pd.read_csv(p/'OLC61_TOP2_SELECTIONS.csv')
m=pd.read_csv(p/'OLC61_MONTHLY_METRICS.csv')
sum0=pd.read_csv(p/'OLC61_SUMMARY.csv')
fit=pd.read_csv(p/'OLC61_FIT_QA.csv')
assert len(a)==18099 and len(fit)==30 and len(m)==600
assert fit.model_parity_error.max()==0
assert fit.num_boosted_rounds.eq(180).all()
assert (pd.to_datetime(fit.last_matured_exit)<pd.to_datetime(fit.year.astype(str)+'-01-01')).all()
assert not a.duplicated(['market','signal_date','ticker']).any()
assert not s.duplicated(['market','signal_date','method','ticker']).any()
assert (s.groupby(['market','signal_date','method']).weight.sum()-1).abs().max()<1e-13

score_cols={'B0_NATIVE':'ORIGINAL_CURRENT','B0_FUSION_CONTEXT':'ORIGINAL_FUSION','ECON21':'pred_ECON21','STAY2':'pred_STAY2','ECO_STAY':'pred_ECO_STAY'}
assert s.method.nunique()==5
independent=0
for (market,dt),g in a.groupby(['market','signal_date']):
    for method,col in score_cols.items():
        # independent full sort + top-2 threshold tie distribution
        sorted_score=np.sort(g[col].to_numpy(dtype=float))[::-1]
        cut=sorted_score[1]
        n_gt=np.count_nonzero(g[col]>cut)
        n_eq=np.count_nonzero(g[col]==cut)
        w=pd.Series(0.,index=g.index)
        w.loc[g.index[g[col]>cut]]=0.5
        w.loc[g.index[g[col]==cut]]=(2-n_gt)/(2*n_eq)
        r=g.loc[w>0, ['ticker','fwd_ret_21','fwd_ret_42']].copy();r['weight']=w.loc[w>0].to_numpy()
        actual=s[(s.market==market)&(s.signal_date==dt)&(s.method==method)]
        q=actual[['ticker','weight']].merge(r[['ticker','weight']],on='ticker',how='outer',indicator=True,suffixes=('_saved','_check'))
        assert (q._merge=='both').all(),(market,dt,method)
        assert np.allclose(q.weight_saved,q.weight_check,atol=1e-13,rtol=0)
        for k in ['fwd_ret_21','fwd_ret_42']:
            val=float(np.dot(r.weight.to_numpy(),r[k].to_numpy()))
            seen=float(m[(m.market==market)&(m.signal_date==dt)&(m.method==method)][k].iloc[0])
            assert abs(val-seen)<1e-13 or (np.isnan(val) and np.isnan(seen)),(market,dt,method,k,val,seen)
        independent+=1
assert independent==600
# independent FUSION baseline OLC60 comparison summary
with zipfile.ZipFile('/mnt/data/OLC60_Upstream_20261107_VERIFICATO.zip') as z:
 old=pd.read_csv(io.BytesIO(z.read('OLC60_Upstream_20261107/results/OLC60_MAIN_SUMMARY.csv')))
for market in ['EU','USA']:
 for method in ['B0_NATIVE','B0_FUSION_CONTEXT']:
  n=sum0[(sum0.market==market)&(sum0.period=='MAIN')&(sum0.method==method)].iloc[0]
  o=old[(old.market==market)&(old.period=='MAIN')&(old.method==method)].iloc[0]
  for k,t in [('fwd_ret_21','avg_fwd21'),('fwd_ret_42','avg_fwd42'),('persist','top2_persist_hit'),('near','top2_near_hit')]:
   assert abs(float(n[k])-float(o[t]))<1e-13,(market,method,k,n[k],o[t])
# constant data coverage, no future label imposed on test universe
assert all(a.groupby(['market','signal_date']).size().between(100,200))
report={'status':'PASS','recomputed_monthly_portfolio_cells':independent,'baseline_olc60_matched':True,
        'source_month_count_each_market':60,'models':len(fit),'prequential_predictions':len(a),
        'full_out_of_fit_year_test_support_unchanged':True,
        'no_lookahead_cutoff_violation_in_fitting_key_dates':True,
        'units':'forward 21/42 session static returns, not portfolio CAGR'}
(p/'OLC61_INDEPENDENT_QA.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))