from pathlib import Path
import sys,json,shutil,time
import numpy as np,pandas as pd
ROOT=Path('/mnt/data/stage19_sourceonly_rebuild');sys.path.insert(0,str(ROOT/'src'))
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder
raw=ROOT/'raw_ticker_csv'; feat=ROOT/'out'/'titanium_features'; out=ROOT/'out'/'titanium'/'xgb_data'; shutil.rmtree(out,ignore_errors=True);out.mkdir(parents=True)
mats,cats,_=load_ticker_csv_folder(raw);cols=list(mats['Close'].columns);k.ALL_TICKERS=sorted(cols);k.TICKER_CATEGORY=cats;k.CATEGORY_TICKERS={c:sorted([t for t in cols if cats[t]==c]) for c in sorted(set(cats.values()))}
compact=pd.read_pickle(feat/'compact.pkl');extra=pd.read_pickle(feat/'extra.pkl');frame=compact.merge(extra,on=['signal_date','ticker'],validate='one_to_one');valid=frame[k.F2D_FEATURES].notna().sum(axis=1)>=30
for year in range(2017,2027):
 cutoff=pd.Timestamp(year,1,1);te=frame[(frame.signal_date.dt.year==year)&valid].sort_values(['signal_date','ticker']);Xte=te[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan).to_numpy();yd=out/str(year);yd.mkdir()
 for h in (21,63):
  tr=frame[(frame.signal_date<cutoff)&(frame[f'exit_date_{h}']<cutoff)&frame[f'target_rank_{h}'].notna()&valid].sort_values(['signal_date','ticker'])
  Xtr=tr[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan).to_numpy();y=(tr[f'target_rank_{h}']*100).round().astype(int).to_numpy();groups=tr.groupby('signal_date',sort=True).size().to_numpy();np.savez(yd/f'data_{h}.npz',Xtr=Xtr,Xte=Xte,y=y,groups=groups)
 print('PREP',year,len(te),flush=True)
