#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

def one(s,old,new,label):
    n=s.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected one site, found {n}')
    return s.replace(old,new)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--mode',choices=['R21_CONT','R21_BIN5','MULTI_CONT'],required=True);a=ap.parse_args()
    p=Path(a.source);s=p.read_text()
    old="tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
    if a.mode.startswith('R21'):
        new="tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_21.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
    else:
        new="tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_63<cutoff)&compact.target_multi_rank.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
    s=one(s,old,new,'train label/maturity')
    oldy="groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int);seed_parts=[]"
    if a.mode=='R21_CONT': newy="groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_21*100).round().astype(int);seed_parts=[]"
    elif a.mode=='R21_BIN5': newy="groups=tr.groupby('signal_date',sort=True).size().tolist();y=np.minimum(4,np.floor(tr.target_rank_21.to_numpy(float)*5.0)).astype(int);seed_parts=[]"
    else: newy="groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_multi_rank*100).round().astype(int);seed_parts=[]"
    s=one(s,oldy,newy,'relevance target')
    # Audit needs the selected maturity column rather than monthly exit_date.
    oldaudit="'compact_max_exit':str(pd.to_datetime(tr.exit_date).max().date()) if len(tr) else None"
    if a.mode.startswith('R21'): newaudit="'compact_max_exit':str(pd.to_datetime(tr.exit_date_21).max().date()) if len(tr) else None"
    else: newaudit="'compact_max_exit':str(pd.to_datetime(tr.exit_date_63).max().date()) if len(tr) else None"
    s=one(s,oldaudit,newaudit,'audit exit')
    # Fix packaging only, no economics.
    oldpack="for k,x in mats.items(): longs.append(x.stack(dropna=False).rename(k.lower()).reset_index().rename(columns={'level_0':'date','level_1':'ticker'}))"
    newpack="for k,x in mats.items():\n        q=x.stack(dropna=False).rename(k.lower()).reset_index(); q.columns=['date','ticker',k.lower()]; longs.append(q)"
    s=one(s,oldpack,newpack,'package')
    s=s.replace("'compact_historical_params':False", "'compact_historical_params':True")
    s=s.replace("'compact_target':'fwd_ret_monthly'", f"'compact_target':'{a.mode}'")
    p.write_text(s);print('patched',a.mode)
if __name__=='__main__':main()
