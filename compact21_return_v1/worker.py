#!/usr/bin/env python3
"""One canonical, isolated XGBoost process per seed; economic objectives only."""
from __future__ import annotations
import argparse,json,os
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",required=True);ap.add_argument("--params",required=True)
    ap.add_argument("--seed",required=True,type=int);ap.add_argument("--rounds",required=True,type=int)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    import numpy as np
    import xgboost as xgb
    with np.load(a.data,allow_pickle=False) as f:
        tr=f["xtrain"];te=f["xtest"];y=f["labels"];groups=f["groups"]
    p=json.loads(a.params);p.update(nthread=1,seed=a.seed)
    if p["objective"] not in ("rank:ndcg","reg:pseudohubererror") or a.rounds!=360:
        raise ValueError("Non registered worker objective")
    dtrain=xgb.QuantileDMatrix(tr,label=y)
    if p["objective"]=="rank:ndcg":
        dtrain.set_group(groups)
    dtest=xgb.QuantileDMatrix(te,ref=dtrain)
    model=xgb.train(p,dtrain,num_boost_round=a.rounds,verbose_eval=False)
    prediction=model.predict(dtest)
    if not np.isfinite(prediction).all() or len(prediction)!=len(te):
        raise ValueError("Invalid worker predictions")
    tmp=a.output+".tmp.npy"
    np.save(tmp,prediction);os.replace(tmp,a.output)
if __name__=="__main__":main()
