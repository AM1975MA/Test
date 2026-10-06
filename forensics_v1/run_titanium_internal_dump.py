#!/usr/bin/env python3
from __future__ import annotations
import argparse,importlib.util,json,os,shutil,sys
from pathlib import Path
import numpy as np
import pandas as pd


def load_compare(path:Path):
    sp=importlib.util.spec_from_file_location('ti_forensic_compare',path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw',required=True);ap.add_argument('--compare-script',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    raw=Path(a.raw).resolve();out=Path(a.out).resolve();cmp=Path(a.compare_script).resolve()
    if out.exists():shutil.rmtree(out)
    out.mkdir(parents=True)
    os.environ['FROZEN_149_ROOT']=str(raw.parent);os.environ['FROZEN_HOLDOUT70_ROOT']=str(raw.parent)
    mod=load_compare(cmp);mod.FROZEN149=raw;mod.FROZEN70=raw;mod.OUT=out/'work'
    state=mod.build_source_only_state('original149',raw)
    # Reconstruct exact Titanium pre-model inputs using canonical source.
    from etf_trader.source_only import kernel as k
    from etf_trader.source_only.features import build as build_extra_features
    mats,cats,_=mod.load_ticker_csv_folder(state['titanium_raw']);cols=list(mats['Close'].columns)
    k.ALL_TICKERS=sorted(cols);k.TICKER_CATEGORY=cats;k.CATEGORY_TICKERS={c:sorted([t for t in cols if cats[t]==c]) for c in sorted(set(cats.values()))}
    dates=k.month_end_dates(mats['Close'].index)
    if len(dates) and dates[-1]==mats['Close'].index[-1]:dates=dates[:-1]
    _,compact,tail,_=k.build_features(mats);compact=compact[compact.signal_date.isin(dates)].copy();tail=tail[tail.signal_date.isin(dates)].copy()
    compact=k.add_labels(compact,mats['Open'],dates);tail=k.add_labels(tail,mats['Open'],dates)
    tail_no_labels=tail.drop(columns=[c for c in tail if c.startswith(('fwd_','target_','exit_')) or c in ['entry_date','y_tailmix']])
    macro,mfeatures=k.build_macro_panel(tail_no_labels,tail)
    extra=build_extra_features(mats,cats,dates)
    compact.to_parquet(out/'TI_COMPACT.parquet',index=False)
    tail.to_parquet(out/'TI_TAIL.parquet',index=False)
    macro.to_parquet(out/'TI_MACRO.parquet',index=False)
    extra.to_parquet(out/'TI_EXTRA.parquet',index=False)
    meta={'F2D_FEATURES':list(k.F2D_FEATURES),'TAIL_FEATURES':list(k.TAIL_FEATURES),'macro_features':list(mfeatures),'compact_columns':list(compact.columns),'tail_columns':list(tail.columns),'macro_columns':list(macro.columns),'extra_columns':list(extra.columns)}
    (out/'TI_INPUT_META.json').write_text(json.dumps(meta,indent=2)+'\n')
    # Annual model raw outputs used to create TIT_R.
    annual=state['base']/'titanium'/'annual_models'
    parts=[]
    for p in sorted(annual.glob('scores_*.csv')):
        q=pd.read_csv(p,parse_dates=['signal_date','entry_date','exit_date']);q['fit_year']=int(p.stem.split('_')[-1]);parts.append(q)
    if not parts:raise RuntimeError(f'no annual score files in {annual}')
    pd.concat(parts,ignore_index=True).to_parquet(out/'TI_MODEL_RAW_SCORES.parquet',index=False)
    state['tit'].to_parquet(out/'TIT_R.parquet',index=False)
    print(json.dumps({'status':'TITANIUM_INTERNAL_DUMP_COMPLETE','f2d':len(k.F2D_FEATURES),'tail':len(k.TAIL_FEATURES),'macro':len(mfeatures),'score_rows':sum(len(x) for x in parts)},indent=2),flush=True)
if __name__=='__main__':main()
