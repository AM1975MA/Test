#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

def one(s,old,new,label):
    n=s.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected one site, found {n}')
    return s.replace(old,new)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);a=ap.parse_args();p=Path(a.source);s=p.read_text()
    old="cutoff=pd.Timestamp(year,1,1); ydir=models_dir/str(year);ydir.mkdir(exist_ok=True)\n        tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
    new="cutoff=pd.Timestamp(year,1,1); ydir=models_dir/str(year);ydir.mkdir(exist_ok=True)\n        cvalid=compact[base.F2D_FEATURES].notna().sum(axis=1)>=30\n        tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()&cvalid].sort_values(['signal_date','ticker']);te=compact[(compact.signal_date.dt.year==year)&cvalid].sort_values(['signal_date','ticker'])"
    s=one(s,old,new,'compact validity')
    oldpack="for k,x in mats.items(): longs.append(x.stack(dropna=False).rename(k.lower()).reset_index().rename(columns={'level_0':'date','level_1':'ticker'}))"
    newpack="for k,x in mats.items():\n        q=x.stack(dropna=False).rename(k.lower()).reset_index(); q.columns=['date','ticker',k.lower()]; longs.append(q)"
    if oldpack in s:s=one(s,oldpack,newpack,'package')
    s=s.replace("'compact_historical_params':False","'compact_historical_params':'V1_PLUS_CVALID30_ONLY'")
    p.write_text(s);print('Applied Compact cvalid>=30 only')
if __name__=='__main__':main()
