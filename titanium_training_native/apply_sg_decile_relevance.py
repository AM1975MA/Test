#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); a=ap.parse_args()
    p=Path(a.source); s=p.read_text()
    old="groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int);seed_parts=[]"
    new="groups=tr.groupby('signal_date',sort=True).size().tolist();y=np.minimum(9,np.floor(tr.target_rank_pct.to_numpy(float)*10.0-1e-12)).astype(np.int32);seed_parts=[]"
    if s.count(old)!=1:
        raise RuntimeError(f'expected one Compact relevance site, found {s.count(old)}')
    s=s.replace(old,new)
    s=s.replace("'compact_historical_params':'PUBLISHED_360x3_PLATINUM_COMPACT_PLUS_EXACT_JUL27_TAIL'","'compact_historical_params':'JUL24_SG_DECILE_RELEVANCE_PLATINUM_COMPACT_EXACT_TAIL'")
    p.write_text(s)
    print('Applied Jul24 Super Gold relevance = floor(rank*10) clipped 0..9')

if __name__=='__main__': main()
