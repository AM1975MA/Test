#!/usr/bin/env python3
from __future__ import annotations
import argparse,re
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); a=ap.parse_args()
    p=Path(a.source); s=p.read_text()
    pat=r"m\s*=\s*float\(r1\.TIT_R\s*-\s*r2\.TIT_R\)\s*;\s*margin\[b\s*,\s*k\]\s*=\s*m"
    matches=list(re.finditer(pat,s))
    if len(matches)!=1:
        raise RuntimeError(f'expected exactly one V2 TIT_R margin site, found {len(matches)}')
    repl='m=float(r1.titanium_score-r2.titanium_score);margin[b,k]=m'
    s=re.sub(pat,repl,s,count=1)
    p.write_text(s)
    print('Applied frozen V2 concentration margin = raw titanium_score top1-top2')

if __name__=='__main__': main()
