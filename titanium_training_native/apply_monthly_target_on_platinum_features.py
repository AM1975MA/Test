#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def one(s, old, new, label):
    n=s.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: expected one site, found {n}')
    return s.replace(old,new)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); a=ap.parse_args()
    p=Path(a.source); s=p.read_text()
    # Keep Platinum feature formulas and PIT eligibility; only change the Compact target/maturity.
    old="out=out[(out.past_close_obs>=126)&entry_ok].copy()\n    return out"
    new="out=out[(out.past_close_obs>=126)&entry_ok].copy()\n        out['target_rank_pct']=out.groupby('signal_date')['fwd_ret_monthly'].rank(pct=True,method='average')\n        out['target_top25']=(out.target_rank_pct>=.75).astype('Int64')\n    return out"
    s=one(s,old,new,'eligible monthly target')
    old="tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
    new="tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
    s=one(s,old,new,'monthly maturity')
    s=s.replace("'compact_target':'fwd_ret_21_PLATINUM_LINEAGE'","'compact_target':'fwd_ret_monthly_ON_PLATINUM_FEATURES'")
    s=s.replace("'compact_max_exit':str(pd.to_datetime(tr.exit_date_21).max().date()) if len(tr) else None","'compact_max_exit':str(pd.to_datetime(tr.exit_date).max().date()) if len(tr) else None")
    p.write_text(s)
    print('Applied monthly target/maturity on Platinum feature+PIT parity')

if __name__=='__main__': main()
