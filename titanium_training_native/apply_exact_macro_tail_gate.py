#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); a=ap.parse_args()
    p=Path(a.source); s=p.read_text()
    old="(pred.macro_category==pred.top_macro)&(pred.macro_gap_z>=.75)&(pred.titanium_score_pre_macro>=.80)"
    new="(pred.macro_category==pred.top_macro)&(pred.macro_gap_z>=.75)&(pred.tail_rank>=.80)"
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'expected exactly one macro gate site, found {n}')
    s=s.replace(old,new)
    p.write_text(s)
    print('Applied frozen macro gate: top category + gap_z>=0.75 + tail_rank>=0.80')

if __name__=='__main__': main()
