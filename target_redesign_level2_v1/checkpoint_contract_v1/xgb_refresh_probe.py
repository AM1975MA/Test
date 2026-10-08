"""Synthetic ONLY XGBoost 3.1.x rank:pairwise leaf-refresh feasibility probe.

No ETF historical rows are loaded, no hyperparameters/CAGR are optimized,
and this does not prove performance or parity of ETF Trader V2.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import numpy as np
import xgboost as xgb


def _splits_and_leaves(booster):
    trees=[]
    leaves=[]
    def walk(n,split_out,leaf_out):
        if "leaf" in n:
            leaf_out.append((n["nodeid"],float(n["leaf"])))
            return
        split_out.append((n["nodeid"],n["split"],float(n["split_condition"]),
                          n["yes"],n["no"],n["missing"]))
        for c in n.get("children",[]):
            walk(c,split_out,leaf_out)
    for tree_text in booster.get_dump(dump_format="json"):
        roots=json.loads(tree_text)
        split_nodes=[];leaf_nodes=[]
        walk(roots,split_nodes,leaf_nodes)
        trees.append(tuple(sorted(split_nodes)))
        leaves.append(tuple(sorted(leaf_nodes)))
    return trees,leaves


def run_synthetic_ranker_refresh_probe() -> dict:
    rng=np.random.default_rng(20261008)
    groups=[10]*8
    n=sum(groups)
    X=rng.normal(size=(n,4)).astype("float32")
    y=np.concatenate([np.linspace(0,100,10).astype("float32") for _ in groups])
    # Produces learnable nonlinear input-target structure within each query.
    X[:,0]=y /100 +rng.normal(0,.2,n)
    dtrain=xgb.QuantileDMatrix(X,label=y)
    dtrain.set_group(groups)
    params={"objective":"rank:pairwise","eval_metric":"ndcg@3",
            "tree_method":"hist","nthread":1,"seed":101,"max_depth":3,
            "subsample":1.0,"colsample_bytree":1.0,"learning_rate":.15}
    base=xgb.train(params,dtrain,num_boost_round=12)
    base_topo,base_leaves=_splits_and_leaves(base)

    X2=X.copy()
    X2[:,0]=0.7*X[:,0]+rng.normal(0,.25,n).astype("float32")
    drefresh=xgb.DMatrix(X2,label=y)
    drefresh.set_group(groups)
    update=xgb.train({**params,"process_type":"update","updater":"refresh",
                      "refresh_leaf":1},drefresh,num_boost_round=12,xgb_model=base)
    new_topo,new_leaves=_splits_and_leaves(update)
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"ranker.ubj"
        update.save_model(path)
        loaded=xgb.Booster()
        loaded.load_model(path)
        p0=update.predict(xgb.DMatrix(X2))
        p1=loaded.predict(xgb.DMatrix(X2))
        error=float(np.max(np.abs(p0-p1)))

    changed=sum(sum(abs(old[1]-new[1])>1e-12 for old,new in zip(oa,na))
                for oa,na in zip(base_leaves,new_leaves))
    return {
        "objective":"rank:pairwise","xgboost":xgb.__version__,
        "n_training_rows":n,"n_refresh_rows":len(X2),
        "original_tree_count":len(base_topo),"updated_tree_count":len(new_topo),
        "identical_split_topology":base_topo==new_topo,
        "changed_leaf_count":changed,
        "reload_max_prediction_error":error,
        "prediction_change_max":float(np.max(np.abs(base.predict(xgb.DMatrix(X2))-p0))),
        "scope":"synthetic API compatibility; NOT ETF strategy validation",
    }

if __name__ == "__main__":
    print(json.dumps(run_synthetic_ranker_refresh_probe(),indent=2))
