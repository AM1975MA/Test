#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, os, shutil
from pathlib import Path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--raw', required=True)
    ap.add_argument('--compare-script', required=True)
    ap.add_argument('--out', required=True)
    args=ap.parse_args()

    raw=Path(args.raw).resolve()
    compare=Path(args.compare_script).resolve()
    out=Path(args.out).resolve()
    u=raw/'universe.csv'
    if not u.exists():
        raise RuntimeError(f'missing universe: {u}')

    # The imported canonical script reads these at import time.  Both are
    # immediately overridden below; no Holdout70 replay is invoked.
    os.environ['FROZEN_149_ROOT']=str(raw.parent)
    os.environ['FROZEN_HOLDOUT70_ROOT']=str(raw.parent)

    spec=importlib.util.spec_from_file_location('canonical_repeat_compare', compare)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.FROZEN149=raw
    mod.FROZEN70=raw
    mod.OUT=out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    uu=mod.load_universe(raw)
    if len(uu)!=149 or uu.ticker.nunique()!=149:
        raise RuntimeError(f'unexpected universe size: {len(uu)}')

    state=mod.build_source_only_state('original149', raw)
    result=mod.replay_full_universe(state)
    result['repeat_snapshot_raw']=str(raw)
    result['canonical_runner_source']='holdout70/v2_canonical_same_source_compare.py from research/v2-same-source-149-vs-70-20261002'
    p=out/'original149'/'RESULT.json'
    p.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2), flush=True)

if __name__=='__main__':
    main()
