import zipfile,io,json,hashlib
from pathlib import Path
import pandas as pd,numpy as np
Z0=zipfile.ZipFile('/mnt/data/olc_sources/OLC08_01_Pannelli_Verificati_20261101.zip')
Z1=zipfile.ZipFile('/mnt/data/olc_sources/OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
P0='parents/olc07_calendar_20261101/phases/P0/results/calendar/'
P1='olc19_combined_risk_20261102/restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/inputs/'
report={}
for m in ['EU','USA']:
 original=pd.read_pickle(io.BytesIO(Z0.read(P0+m+'_OPEN.pkl')))
 with np.load(io.BytesIO(Z1.read(P1+m+'_STATE_HALF.npz')),allow_pickle=False) as st:
  dates=pd.DatetimeIndex(st['dates']);ticker=pd.Index(st['tickers'])
  orig=original.reindex(index=dates,columns=ticker).to_numpy(float)
  model=st['O'];mask=np.isfinite(orig)&(orig>0);both=np.isfinite(orig)&np.isfinite(model)&(orig>0)
  assert np.array_equal(orig[both],model[both])
  r=dict(source_dates=len(dates),tickers=len(ticker),exact_matching_valid_prices=int(both.sum()),max_absolute_diff=0.0)
  if 'observed' in st:
   observed=st['observed'];bad=np.where(mask!=observed)
   wrong_tickers=pd.Series(ticker[bad[1]]).value_counts().to_dict()
   assert set(wrong_tickers).issubset({'EUR_CASH_A','EUR_CASH_B'})
   r['original_source_mask_restored_for_ETFs']=True
   r['observed_mask_mismatch_count']=int(len(bad[0]));r['mismatch_tickers']=wrong_tickers
  else:
   r['original_source_mask_restored_for_ETFs']=False
   r['prepared_panel_finite_fraction']=float(np.isfinite(orig).mean())
   r['why_not_certified']='Panel is already complete over modeled dates; original observed/filled distinction absent; equal prices do NOT identify actual quote observations'
  report[m]=r
path=Path('/mnt/data/olc32_work/results/SOURCE_OPEN_MASK_AUDIT.json');path.write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
