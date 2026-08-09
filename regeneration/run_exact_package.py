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
    ap.add_argument('--generator',required=True)
    ap.add_argument('--base-module',required=True)
    ap.add_argument('--v5-module',required=True)
    ap.add_argument('--data-dir',required=True)
    ap.add_argument('--output-parent',default='.')
    ap.add_argument('--n-estimators',type=int,default=360)
    ap.add_argument('--n-baskets',type=int,default=500)
    args=ap.parse_args()

    gen=load_module(Path(args.generator),'titanium_package_generator')

    # Canonical frozen downside-volatility definition recovered from source:
    # positive returns are zeroed, ddof=0, and 75% valid observations are enough.
    def canonical_corrected_downvol(mode: str):
        if mode == 'original':
            return None
        if mode == 'zero_std':
            def f(ret,h):
                neg=ret.where(ret < 0.0, 0.0)
                minp=max(10,int(h*0.75))
                return neg.rolling(h,min_periods=minp).std(ddof=0)*np.sqrt(252)
            return f
        return gen.corrected_downvol(mode)
    gen.corrected_downvol=canonical_corrected_downvol

    # Keep the generated live inference script feature-identical to training.
    original_live_script_text=gen.live_script_text
    def canonical_live_script_text():
        txt=original_live_script_text()
        txt=txt.replace("ret.clip(upper=0.0).rolling(h,min_periods=h).std(ddof=0)*np.sqrt(252)",
                        "ret.where(ret < 0.0, 0.0).rolling(h,min_periods=max(10,int(h*0.75))).std(ddof=0)*np.sqrt(252)")
        return txt
    gen.live_script_text=canonical_live_script_text

    sys.argv=[Path(args.generator).name,
              '--base-module',args.base_module,
              '--v5-module',args.v5_module,
              '--data-dir',args.data_dir,
              '--output-parent',args.output_parent,
              '--downvol-mode','zero_std',
              '--n-estimators',str(args.n_estimators),
              '--n-baskets',str(args.n_baskets)]
    gen.main()

if __name__=='__main__':
    main()
