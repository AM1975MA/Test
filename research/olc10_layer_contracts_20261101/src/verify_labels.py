"""Reconcile all saved forward labels to authenticated observed Open endpoints."""
from pathlib import Path
import pandas as pd,numpy as np
from recovery_core import atomic_json
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'inputs';rows=[]
for m in ['EU','USA']:
    csv=I/f'{m}_OPEN_OBSERVED.csv.gz'
    if csv.exists():o=pd.read_csv(csv,index_col=0,parse_dates=True,float_precision='round_trip')
    else:
        o=pd.read_pickle(I/f'{m}_OPEN.pkl');o.to_csv(csv,compression='gzip')
    for kind in ['LAYER','RETURN']:
        labels=pd.read_csv(I/f'{m}_{kind}_LABELS.csv.gz',float_precision='round_trip',parse_dates=['signal_date','entry_date','exit_date_21','exit_date_42','exit_date_63'])
        for h in [21,42,63]:
            f=labels[np.isfinite(labels[f'fwd_ret_{h}'])].copy()
            er=o.index.get_indexer(f.entry_date);xr=o.index.get_indexer(f[f'exit_date_{h}']);tc=o.columns.get_indexer(f.ticker)
            assert (er>=0).all() and (xr>=0).all() and (tc>=0).all()
            ov=o.to_numpy();entry=ov[er,tc];exit=ov[xr,tc]
            assert np.isfinite(entry).all() and np.isfinite(exit).all() and (entry>0).all()
            diff=np.max(abs(exit/entry-1-f[f'fwd_ret_{h}'].to_numpy()));assert diff<1e-12
            assert (f.entry_date>f.signal_date).all() and (f[f'exit_date_{h}']>f.entry_date).all()
            rows.append({'market':m,'panel':kind,'horizon':h,'labels_checked':len(f),'max_error':float(diff),'observed_finite_endpoints':True})
    
atomic_json(ROOT/'results/LABEL_ENDPOINT_VERIFICATION.json',{'rows':rows,'labels_checked':sum(r['labels_checked'] for r in rows),'scope':'Checks against saved filtered observed Opens; not external price/total-return certification.'})
print(sum(r['labels_checked'] for r in rows),'labels checked',max(r['max_error'] for r in rows))
