#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); a=ap.parse_args()
    p=Path(a.source); s=p.read_text()
    old="for year in years:\n        cutoff=pd.Timestamp(year,1,1); ydir=models_dir/str(year);ydir.mkdir(exist_ok=True)\n        tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
    new="for year in years:\n        te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])\n        if te.empty: continue\n        cutoff=pd.Timestamp(te.signal_date.min()); ydir=models_dir/str(year);ydir.mkdir(exist_ok=True)\n        tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker'])"
    if s.count(old)!=1: raise RuntimeError(f'annual refit anchor count={s.count(old)}')
    s=s.replace(old,new)
    s=s.replace("if tr.signal_date.nunique()<60 or te.empty: continue","if tr.signal_date.nunique()<60: continue",1)
    # The same annual model family (Tail/Macro/Opportunity) historically refit on the first actual signal date.
    # They already use the shared cutoff variable, so changing cutoff above applies the same causal fit date.
    s=s.replace("'compact_historical_params':'PUBLISHED_360x3_PLATINUM_COMPACT_PLUS_EXACT_JUL27_TAIL'","'compact_historical_params':'PUBLISHED_360x3_FIRST_SIGNAL_ANNUAL_REFIT_EXACT_TAIL_CVAR'")
    p.write_text(s)
    print('Applied annual cutoff = first actual signal_date of each year')

if __name__=='__main__': main()
