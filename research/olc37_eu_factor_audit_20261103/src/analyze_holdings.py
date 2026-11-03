#!/usr/bin/env python3
"""Supplementary, outcome-free holdings diagnostic: EU primary portfolio weights only."""
from pathlib import Path
import io,zipfile,numpy as np,pandas as pd,json
import argparse
cli=argparse.ArgumentParser()
cli.add_argument('--olc19',type=Path,default=Path(__file__).resolve().parents[1]/'input/OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
cli.add_argument('--results',type=Path,default=Path(__file__).resolve().parents[1]/'results')
a=cli.parse_args()
src=a.olc19;out=a.results
with zipfile.ZipFile(src) as z:
 s=np.load(io.BytesIO(z.read(next(x for x in z.namelist() if x.endswith('/EU_STATE_HALF.npz')))))
 p=np.load(io.BytesIO(z.read('olc19_combined_risk_20261102/results/paths/EU_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz')))
 dates=pd.DatetimeIndex(s['dates']);t=s['tickers'].astype(str);O=s['O'];mask=s['observed']
 nav_actual=np.r_[1.0,p['nav'][:-1]]
 weights=np.where(np.isfinite(O),np.maximum(p['primary_units'],0.)*O/nav_actual[:,None],0.)
 common=[int(np.where(t==x)[0][0]) for x in ('EXSA.DE','SXR8.DE','SXRV.DE','QDVE.DE','EXX1.DE')]
 valid=mask[:,common].all(axis=1)
 rows=[]
 for year in [2021,2022,2023,2024]:
  k=(dates.year==year)&valid
  w=weights[k].mean(axis=0)
  for j in np.argsort(-w)[:20]:
   rows.append({'year':year,'ticker':t[j],'rank_by_mean_open_weight':int(1+sum(w>w[j])),
                'mean_portfolio_weight_pct':100*float(w[j]),
                'invested_days_pct':100*float(np.mean(weights[k,j]>1e-6)),
                'observed_quote_fraction_when_positive':float(np.mean(mask[k,j][weights[k,j]>1e-6])) if np.any(weights[k,j]>1e-6) else None,
                'primary_only':'yes; defensive excluded'})
 df=pd.DataFrame(rows).sort_values(['year','rank_by_mean_open_weight','ticker']);df.to_csv(out/'EU_ACTUAL_PRIMARY_HOLDINGS_BY_YEAR.csv',index=False)
 summary=[]
 for year in [2021,2022,2023,2024]:
  k=(dates.year==year)&valid
  w=weights[k].mean(axis=0)
  get=lambda tk:float(100*w[np.where(t==tk)[0][0]])
  summary.append({'year':year,'days_common_open':int(k.sum()),
     'mean_VVSM_semiconductor_portfolio_weight_pct':get('VVSM.DE'),
     'mean_QDVE_US_IT_portfolio_weight_pct':get('QDVE.DE'),
     'sum_VVSM_QDVE_pct':get('VVSM.DE')+get('QDVE.DE'),
     'mean_total_primary_pct':float(100*w.sum()),
     'avg_weight_top3_tickers_pct':float(100*np.sort(w)[-3:].sum()),
     'unknown_lookthrough_share_class_pct':'NOT_CERTIFIED_PIT'})
 pd.DataFrame(summary).to_csv(out/'EU_SEMICONDUCTOR_TECH_EXPOSURE_DIAGNOSTIC.csv',index=False)
 print(pd.DataFrame(summary).to_string(index=False))
