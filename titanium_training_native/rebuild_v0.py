#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Historical F2D recovery runner")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    src = Path(args.input)
    dst = Path(args.output)
    text = src.read_text()

    # Deterministically undo the five forensic substitutions documented by
    # code/patch_historical_f2d.py.  This restores the pre-patch retrainable
    # method; no trained model or prediction file is used as a dependency.
    replacements = [
        (
            "models_dir.mkdir(parents=True,exist_ok=True); params=dict(objective='rank:pairwise',eval_metric='ndcg',n_estimators=60,max_depth=4,learning_rate=0.05,min_child_weight=20,subsample=0.80,colsample_bytree=0.75,reg_lambda=12.0,reg_alpha=0.2,tree_method='hist',n_jobs=2,verbosity=0)",
            "models_dir.mkdir(parents=True,exist_ok=True); params=dict(base.COMPACT_PARAMS);params['n_estimators']=n_estimators;params['n_jobs']=2",
        ),
        (
            "tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_21.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])",
            "tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])",
        ),
        (
            "groups=tr.groupby('signal_date',sort=True).size().tolist();y=np.minimum(4,np.floor(tr.target_rank_21.to_numpy(float)*5.0)).astype(int);seed_parts=[]",
            "groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int);seed_parts=[]",
        ),
        (
            "(pred.macro_category==pred.top_macro)&(pred.macro_gap_z>=.75)&(pred.titanium_score_pre_macro>=.80)",
            "(pred.macro_category==pred.top_macro)&(pred.macro_gap_z>=.75)&(pred.tail_rank>=.80)",
        ),
        (
            "op['opp_raw']=op['target_excess_max_pred'];op['opp_z']=op.groupby('signal_date').opp_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+EPS))",
            "for target,w in OPP_WEIGHTS.items(): op[target+'_pred_rank']=op.groupby('signal_date')[target+'_pred'].rank(pct=True,method='average')\n    op['opp_raw']=sum(w*op[target+'_pred_rank'] for target,w in OPP_WEIGHTS.items());op['opp_z']=op.groupby('signal_date').opp_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+EPS))",
        ),
    ]

    for old, new in replacements:
        count = text.count(old)
        if count != 1:
            raise RuntimeError(f"Expected one patch site, found {count}: {old[:100]}")
        text = text.replace(old, new)

    forensic_manifest = (
        "'compact_trees':60,'compact_historical_params':True,"
        "'compact_target':'fwd_ret_21','compact_relevance_bins':5"
    )
    native_manifest = (
        "'compact_trees':args.n_estimators,'compact_historical_params':False,"
        "'compact_target':'fwd_ret_monthly',"
        "'compact_relevance':'rank_pct_x100_round'"
    )
    if forensic_manifest in text:
        text = text.replace(forensic_manifest, native_manifest)

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text)
    print("source", src)
    print("output", dst)
    print("sha256", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
