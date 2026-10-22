#!/usr/bin/env python3
"""One-shot XGBoost ranker worker used by source_only.models.

The worker intentionally performs exactly one seed/horizon fit and exits.
This avoids reusing XGBoost/OpenMP state across independent ensemble members.
"""
from __future__ import annotations

import argparse
import json
import os


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",required=True)
    ap.add_argument("--seed",type=int,required=True)
    ap.add_argument("--threads",type=int,required=True)
    ap.add_argument("--rounds",type=int,required=True)
    ap.add_argument("--params-json",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()

    import numpy as np
    import xgboost as xgb

    z=np.load(args.data)
    params=json.loads(args.params_json)
    params["nthread"]=int(args.threads)
    params["seed"]=int(args.seed)

    dtrain=xgb.QuantileDMatrix(z["Xtr"],label=z["y"])
    dtrain.set_group(z["groups"])
    dtest=xgb.QuantileDMatrix(z["Xte"],ref=dtrain)

    model=xgb.train(
        params,
        dtrain,
        num_boost_round=int(args.rounds),
    )
    pred=model.predict(dtest)

    tmp=args.output+".tmp.npy"
    np.save(tmp,pred)
    os.replace(tmp,args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())