"""Canonical one-seed worker with optional ranking-query objective weights.

Quantile sketch remains canonical (unweighted); weights are attached only after
matrix construction and grouping. Ranking weights are per query, not per row.
https://xgboost.readthedocs.io/en/release_3.1.0/python/python_api.html
"""
from __future__ import annotations
import argparse
import json
import os


def main():
    ap = argparse.ArgumentParser()
    for name in ("data", "params-json", "output"):
        ap.add_argument("--"+name, required=True)
    for name in ("seed", "threads", "rounds"):
        ap.add_argument("--"+name, type=int, required=True)
    args = ap.parse_args()
    import numpy as np
    import xgboost as xgb
    z = np.load(args.data, allow_pickle=False)
    params = json.loads(args.params_json)
    params["nthread"] = int(args.threads)
    params["seed"] = int(args.seed)
    dtrain = xgb.QuantileDMatrix(z["Xtr"], label=z["y"])
    dtrain.set_group(z["groups"])
    if "group_weights" in z:
        weights = z["group_weights"]
        if weights.ndim != 1 or len(weights) != len(z["groups"]) or not np.isfinite(weights).all() or (weights < 0).any() or weights.sum() <= 0:
            raise ValueError("Invalid ranking-query weights")
        dtrain.set_weight(weights)
    dtest = xgb.QuantileDMatrix(z["Xte"], ref=dtrain)
    model = xgb.train(params, dtrain, num_boost_round=int(args.rounds))
    pred = model.predict(dtest)
    tmp = args.output+".tmp.npy"
    np.save(tmp, pred)
    os.replace(tmp, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
