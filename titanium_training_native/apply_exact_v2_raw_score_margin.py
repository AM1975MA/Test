#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); a=ap.parse_args()
    p=Path(a.source); s=p.read_text()
    old='m=float(r1.TIT_R-r2.TIT_R); margin[b,k]=m'
    new='m=float(r1.titanium_score-r2.titanium_score); margin[b,k]=m'
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'expected exactly one V2 margin site, found {n}')
    s=s.replace(old,new)
    p.write_text(s)
    print('Applied frozen V2 concentration margin = raw titanium_score top1-top2')

if __name__=='__main__': main()
