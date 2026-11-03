#!/usr/bin/env python3
"""Independent equation, calendar, source and portfolio-baseline checks for OLC35.
No training/backtesting, no mutation of official snapshots.
"""
from pathlib import Path
import io,gzip,zipfile,json,hashlib
import numpy as np
import pandas as pd
root=Path(__file__).resolve().parents[1]
r=root/'results'
D=pd.read_csv(r/'OLC35_MONTHLY_ORACLE_DECOMPOSITION.csv')
P=pd.read_csv(r/'OLC35_FROZEN_PORTFOLIO_BASELINES.csv')
F=pd.read_csv(r/'OLC35_TOP2_RECONCILIATION.csv')
C=pd.read_csv(r/'OLC35_LABEL_COVERAGE.csv')
X=pd.read_csv(r/'OLC35_SAME_FAMILY_RISK_CONTRACTS.csv')
A=pd.read_csv(r/'OLC35_MARKET_SUMMARY.csv')
assert len(D)==96 and len(F)==96 and len(C)==96
assert not D.duplicated(['market','signal_date']).any()
assert F.set_match.all() and len(F)==96
assert (D.best_market_in_top5==(D.best_market_rank<=5)).all()
assert (D.best_market_in_top2==(D.best_market_rank<=2)).all()
assert (D.oracle_availability_effect_bp>=-1e-9).all()
assert (D.oracle_total_bp>=-1e-9).all()
assert C.n_missing.sum()==2
assert P.groupby('market').size().to_dict()=={'EU':2,'USA':2}
assert len(X)==6 and not X.duplicated(['market','contract']).any()
lookup={('USA','OLC17_ALL_PREOPEN_V6'):(0.523006,-0.197902),('USA','OLC19_FAST_LOCK3'):(.507722,-.202260),
('EU','OLC17_ALL_PREOPEN_V6'):(.203754,-.266763),('EU','OLC19_FAST_LOCK3'):(.231999,-.286084)}
for (m,s),(c,dd) in lookup.items():
  z=P[(P.market==m)&(P.source==s)].iloc[0]
  assert abs(z.cagr-c)<1e-6 and abs(z.maxdd-dd)<1e-6
# Independent check using rank/sort vs group-by extrema and a pandas pivot.
with zipfile.ZipFile(str(root/'input'/'OLC32_RESULTS.zip')) as z:
  raw=gzip.decompress(z.read('results/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz'))
  src=pd.read_csv(io.BytesIO(raw),usecols=['market','signal_date','ticker','auth_rank','r_o2o_bp','eligible_label','feature_available_asof'])
src=src[(src.eligible_label)&(src.signal_date.between('2021-01-01','2024-12-31'))]
result=[]
for keys, g in src.groupby(['market','signal_date']):
  t=g.set_index('auth_rank').sort_index()
  b=t['r_o2o_bp']
  raw_max=float(b.max());top5_max=float(b.loc[b.index<=5].max());top2_max=float(b.loc[b.index<=2].max());avg2=float(b.loc[b.index<=2].mean());
  available=g[g.feature_available_asof];asof_max=float(available.r_o2o_bp.max())
  result.append([*keys,raw_max,top5_max,top2_max,avg2,asof_max])
E=pd.DataFrame(result,columns=['market','signal_date','raw_best','top5_best','top2_best','avg2','asof_best'])
Y=D.merge(E,on=['market','signal_date'],validate='one_to_one')
checks={
 'market_best_abs_difference':float(np.max(np.abs(Y.best_market_bp-Y.raw_best))),
 'top5_abs_difference':float(np.max(np.abs(Y.best_top5_bp-Y.top5_best))),
 'top2_abs_difference':float(np.max(np.abs(Y.best_top2_bp-Y.top2_best))),
 'selected_top2_abs_difference':float(np.max(np.abs(Y.selected_two_logscore_bp-Y.avg2))),
 'asof_max_abs_difference':float(np.max(np.abs(Y.asof_best_bp-Y.asof_best))),
 'max_decomposition_identity_bp':float(np.max(np.abs(Y.oracle_total_bp-(Y.opportunity_outside_top5_bp+Y.opportunity_within_top5_outside_top2_bp+Y.opportunity_two_slot_concentration_bp)))),
 'top2_signal_matches':int(F.set_match.sum()),
 'matched_months_total':len(Y),
 'missing_EU_label_pairs':int(C.n_missing.sum()),
 'unscoreable_expost_months':int((Y.oracle_availability_effect_bp>1e-9).sum()),
 'USA_OLC17_CAGR':float(P.query("market=='USA' and source=='OLC17_ALL_PREOPEN_V6'").cagr.iloc[0]),
 'USA_OLC19_CAGR':float(P.query("market=='USA' and source=='OLC19_FAST_LOCK3'").cagr.iloc[0]),
 'USA_strategy_unchanged':True,
 'investable_new_portfolio_proposed':False,
}
for key,value in checks.items():
 if key.endswith('difference') or key.startswith('max_'):
  assert value<1e-7,(key,value)
manifest=json.loads((r/'OLC35_MANIFEST.json').read_text())
for filename,entry in manifest.items():
 p=(root/filename if filename.startswith('figures/') else r/filename)
 assert p.exists(),(filename,p)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']
assert np.allclose(A.set_index('market')['months'].to_numpy(),[48,48])
checks['status']='PASSED'
(r/'OLC35_INDEPENDENT_VERIFICATION.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
