from pathlib import Path
import sys,time,json
import pandas as pd
ROOT=Path('/mnt/data/stage19_sourceonly_rebuild'); sys.path.insert(0,str(ROOT/'src'))
from etf_trader.source_only import kernel as k
from etf_trader.source_only.features import build as build_extra_features
from etf_trader.source_only.raw_io import load_ticker_csv_folder
raw=ROOT/'raw_ticker_csv'; out=ROOT/'out'/'titanium_features'; out.mkdir(parents=True,exist_ok=True)
t=time.time(); mats,cats,man=load_ticker_csv_folder(raw); print('LOAD',time.time()-t,flush=True)
cols=list(mats['Close'].columns);k.ALL_TICKERS=sorted(cols);k.TICKER_CATEGORY=cats;k.CATEGORY_TICKERS={c:sorted([t for t in cols if cats[t]==c]) for c in sorted(set(cats.values()))}
dates=k.month_end_dates(mats['Close'].index)
if len(dates) and dates[-1]==mats['Close'].index[-1]: dates=dates[:-1]
t=time.time(); _,compact,tail,_=k.build_features(mats); print('BUILD_FEATURES',time.time()-t,compact.shape,tail.shape,flush=True)
compact=compact[compact.signal_date.isin(dates)].copy();tail=tail[tail.signal_date.isin(dates)].copy()
t=time.time();compact=k.add_labels(compact,mats['Open'],dates);tail=k.add_labels(tail,mats['Open'],dates); print('LABELS',time.time()-t,flush=True)
t=time.time();tail_no_labels=tail.drop(columns=[c for c in tail if c.startswith(('fwd_','target_','exit_')) or c in ['entry_date','y_tailmix']]);macro,mfeatures=k.build_macro_panel(tail_no_labels,tail);extra=build_extra_features(mats,cats,dates); print('MACRO_EXTRA',time.time()-t,macro.shape,extra.shape,flush=True)
compact.to_pickle(out/'compact.pkl');tail.to_pickle(out/'tail.pkl');macro.to_pickle(out/'macro.pkl');extra.to_pickle(out/'extra.pkl');(out/'mfeatures.json').write_text(json.dumps(mfeatures));(out/'meta.json').write_text(json.dumps({'dates':len(dates),'tickers':len(cols),'raw_manifest':man},indent=2));print('SAVED',out,flush=True)
