#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os
from pathlib import Path
import pandas as pd
from etf_trader.source_only import kernel as k
from etf_trader.source_only.features import build as build_extra_features
from etf_trader.source_only.models import fit_predict, variants
from etf_trader.source_only.raw_io import load_ticker_csv_folder

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data',required=True)
    ap.add_argument('--output',required=True)
    ap.add_argument('--xgb-workers',type=int,default=3)
    ap.add_argument('--xgb-threads-per-worker',type=int,default=1)
    ap.add_argument('--start-year',type=int,default=2017)
    ap.add_argument('--end-year',type=int,default=2026)
    ap.add_argument('--min-signal-date',default='2017-01-31')
    ap.add_argument(
        '--max-signal-date',
        default='2026-06-30',
        help="historical parity default; use 'auto' only for the frozen prospective extension",
    )
    a=ap.parse_args()
    if a.end_year<a.start_year:
        raise ValueError('--end-year must be >= --start-year')
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    os.environ['ETF_TRADER_XGB_WORKERS']=str(a.xgb_workers);os.environ['ETF_TRADER_XGB_THREADS_PER_WORKER']=str(a.xgb_threads_per_worker)
    mats,cats,raw_manifest=load_ticker_csv_folder(a.data)
    cols=list(mats['Close'].columns);k.ALL_TICKERS=sorted(cols);k.TICKER_CATEGORY=cats;k.CATEGORY_TICKERS={c:sorted([t for t in cols if cats[t]==c]) for c in sorted(set(cats.values()))}
    dates=k.month_end_dates(mats['Close'].index)
    if len(dates) and dates[-1]==mats['Close'].index[-1]:dates=dates[:-1]
    _,compact,tail,_=k.build_features(mats)
    compact=compact[compact.signal_date.isin(dates)].copy();tail=tail[tail.signal_date.isin(dates)].copy()
    compact=k.add_labels(compact,mats['Open'],dates);tail=k.add_labels(tail,mats['Open'],dates)
    tail_no_labels=tail.drop(columns=[c for c in tail if c.startswith(('fwd_','target_','exit_')) or c in ['entry_date','y_tailmix']])
    macro,mfeatures=k.build_macro_panel(tail_no_labels,tail);extra=build_extra_features(mats,cats,dates)
    pred=fit_predict(
        k,compact,tail,macro,mfeatures,extra,out/'annual_models',
        years=range(a.start_year,a.end_year+1),
    )
    pred=pred[pred.signal_date>=pd.Timestamp(a.min_signal_date)].copy()
    if str(a.max_signal_date).lower() not in {'auto','none'}:
        pred=pred[pred.signal_date<=pd.Timestamp(a.max_signal_date)].copy()
    # Only completed monthly holding periods are valid inputs to path evaluation.
    # Historical parity defaults are unaffected because all <=2026-06-30 rows
    # already have an exit date in the frozen 2026-07-31 feed.
    pred=pred[pred['entry_date'].notna()&pred['exit_date'].notna()].copy()
    if pred.empty:
        raise RuntimeError('no completed monthly prediction periods after date filtering')
    baseline=variants(pred)['baseline'].rename(columns={'score':'TIT_R'})
    calendar=pred[['signal_date','ticker','entry_date','exit_date']].drop_duplicates(['signal_date','ticker'])
    panel=baseline.merge(calendar,on=['signal_date','ticker'],how='inner',validate='one_to_one')
    panel=panel[['signal_date','entry_date','exit_date','ticker','TIT_R']].sort_values(['signal_date','ticker'])
    panel.to_csv(out/'TIT_R_SOURCE_ONLY.csv',index=False)
    print(json.dumps({'status':'SOURCE_ONLY_TIT_R_REBUILT','rows':len(panel),'signal_dates':panel.signal_date.nunique(),'tickers':panel.ticker.nunique()},indent=2))
if __name__=='__main__':main()
