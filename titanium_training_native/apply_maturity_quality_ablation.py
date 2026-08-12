#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

def one(s,o,n,l):
 c=s.count(o)
 if c!=1: raise RuntimeError(f'{l}: {c} sites')
 return s.replace(o,n)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--mode',choices=['MAT21_ONLY','MAT21_QUAL'],required=True);a=ap.parse_args();p=Path(a.source);s=p.read_text()
 old="tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
 if a.mode=='MAT21_ONLY':
  new="tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
 else:
  new="cvalid=compact[base.F2D_FEATURES].notna().sum(axis=1)>=30;tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_pct.notna()&cvalid].sort_values(['signal_date','ticker']);te=compact[(compact.signal_date.dt.year==year)&cvalid].sort_values(['signal_date','ticker'])"
 s=one(s,old,new,'compact maturity')
 if a.mode=='MAT21_QUAL':
  oldt="ttr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()];tte=tail[tail.signal_date.dt.year==year]"
  newt="tvalid=tail[base.TAIL_FEATURES].notna().sum(axis=1)>=12;ttr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()&tvalid];tte=tail[(tail.signal_date.dt.year==year)&tvalid]"
  s=one(s,oldt,newt,'tail quality')
 oldaudit="'compact_max_exit':str(pd.to_datetime(tr.exit_date).max().date()) if len(tr) else None"
 s=one(s,oldaudit,"'compact_max_exit':str(pd.to_datetime(tr.exit_date_21).max().date()) if len(tr) else None",'audit')
 oldpack="for k,x in mats.items(): longs.append(x.stack(dropna=False).rename(k.lower()).reset_index().rename(columns={'level_0':'date','level_1':'ticker'}))"
 newpack="for k,x in mats.items():\n        q=x.stack(dropna=False).rename(k.lower()).reset_index(); q.columns=['date','ticker',k.lower()]; longs.append(q)"
 s=one(s,oldpack,newpack,'package')
 s=s.replace("'compact_historical_params':False", "'compact_historical_params':True").replace("'compact_target':'fwd_ret_monthly'",f"'compact_target':'fwd_ret_monthly__{a.mode}'")
 p.write_text(s);print('patched',a.mode)
if __name__=='__main__':main()
