#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, sys
from pathlib import Path
import numpy as np


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--v5', required=True)
    ap.add_argument('--base', required=True)
    ap.add_argument('--data-dir', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--mode', choices=['original','zero_std','downside_rms','negative_std_full'], required=True)
    ap.add_argument('--fast', action='store_true')
    args=ap.parse_args()
    v5=load_module(Path(args.v5),'titanium_v5')
    original_loader=v5.load_base
    def patched_loader(path):
        base=original_loader(path)
        if args.mode=='zero_std':
            def rolling_downvol(ret,h):
                neg=ret.clip(upper=0.0)
                return neg.rolling(h,min_periods=h).std(ddof=0)*np.sqrt(252)
            base.rolling_downvol=rolling_downvol
        elif args.mode=='downside_rms':
            def rolling_downvol(ret,h):
                neg=ret.clip(upper=0.0)
                return np.sqrt(neg.pow(2).rolling(h,min_periods=h).mean())*np.sqrt(252)
            base.rolling_downvol=rolling_downvol
        elif args.mode=='negative_std_full':
            def rolling_downvol(ret,h):
                neg=ret.where(ret<0)
                return neg.rolling(h,min_periods=1).std(ddof=0)*np.sqrt(252)
            base.rolling_downvol=rolling_downvol
        return base
    v5.load_base=patched_loader
    sys.argv=[Path(args.v5).name,'--base-module',args.base,'--data-dir',args.data_dir,'--output',args.output]
    if args.fast: sys.argv.append('--fast')
    v5.main()

if __name__=='__main__':
    main()
