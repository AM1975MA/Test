"""Immutable recipes and causal training-only return targets for two Compact21 challengers."""
from __future__ import annotations
import hashlib
import numpy as np
import pandas as pd
from etf_trader.source_only import kernel as k

VARIANTS=("RETURN_RANK_NDCG","RETURN_REG_PSEUDOHUBER")
KEYS=("signal_date","ticker")
TARGETS=dict(
    RETURN_RANK_NDCG=dict(objective="rank:ndcg",ndcg_exp_gain=False,
                          lambdarank_pair_method="topk",lambdarank_num_pair_per_sample=5,
                          eval_metric="ndcg@5"),
    RETURN_REG_PSEUDOHUBER=dict(objective="reg:pseudohubererror",huber_slope=0.10,
                               eval_metric="mae"))
RETURN_REG_CLIP=0.25
RET_GRADE_MAX=15

def sha_array(a):
    b=np.ascontiguousarray(a)
    h=hashlib.sha256()
    h.update(str(b.dtype).encode());h.update(str(b.shape).encode());h.update(b.tobytes())
    return h.hexdigest()

def native_x(frame):
    result=frame[k.F2D_FEATURES].to_numpy(dtype=np.float64,copy=True)
    result[~np.isfinite(result)]=np.nan
    if result.shape[1]!=125:raise ValueError("Canonical features changed")
    return result

def prepare_targets(train, variant):
    """Only training rows; query-local future returns never enter inference features."""
    if variant not in VARIANTS:raise ValueError(variant)
    if not {"signal_date","fwd_ret_21","target_rank_21","exit_date_21"}.issubset(train):
        raise ValueError("Missing true 21-session forward return training labels")
    ordered=train.sort_values(list(KEYS)).reset_index(drop=True)
    if train.duplicated(list(KEYS)).any() or not train[list(KEYS)].reset_index(drop=True).equals(ordered[list(KEYS)]):
        raise ValueError("Queries must be ordered")
    r=train.fwd_ret_21.to_numpy(float)
    if not np.isfinite(r).all():raise ValueError("Nonfinite mature future return")
    groups=train.groupby("signal_date",sort=True).size().to_numpy(np.int64)
    if groups.sum()!=len(r) or np.any(groups<2):raise ValueError("Invalid group")
    labels=np.zeros(len(r),float)
    cursor=0
    dates=[]
    for group in groups:
        a=slice(cursor,cursor+group); u=r[a]
        med=np.median(u)
        if variant=="RETURN_RANK_NDCG":
            # Query-specific cross-sectional robust spread; NDCG gain differences now
            # encode return-gap magnitude, not just ordinal realized percentile.
            spread=max(float(np.quantile(u,.90)-np.quantile(u,.10)),1e-6)
            scaled=np.clip((u-med)/spread,-1.,1.)
            labels[a]=np.rint(.5*RET_GRADE_MAX*(1.+scaled))
        else:
            # Huber robust regression on return premium over the same date's median;
            # centering removes common market return, and clipping limits outlier leverage.
            labels[a]=np.clip(u-med,-RETURN_REG_CLIP,RETURN_REG_CLIP)
        dates.append(str(train.signal_date.iloc[cursor]))
        cursor+=group
    if variant=="RETURN_RANK_NDCG":
        y=labels.astype(np.int32)
        if (y<0).any() or (y>RET_GRADE_MAX).any():raise ValueError("Bad graded relevance")
    else:y=labels.astype(np.float32)
    meta=dict(variant=variant,target="21_session_next_open_forward_return",
        robust_grading="round(7.5+7.5*clip((ret-date_median)/max(q90-q10,1e-6),-1,1))" if variant=="RETURN_RANK_NDCG" else "clip(ret-date_median,-.25,+.25)",
        training_target_sha256=sha_array(y),
        group_sha256=sha_array(groups),training_groups=len(groups),
        minimum_label=float(np.min(y)),maximum_label=float(np.max(y)),
        finite_future_returns=True,date_centered=True)
    return y,groups,meta

def recipe(variant):
    if variant not in VARIANTS:raise ValueError("Unknown recipe")
    expected={"objective":"rank:pairwise","n_estimators":360,"max_depth":4,
              "learning_rate":.035,"subsample":.85,"colsample_bytree":.8,
              "min_child_weight":8.,"reg_lambda":8.,"reg_alpha":.1,
              "tree_method":"hist"}
    if any(k.COMPACT_PARAMS.get(name)!=value for name,value in expected.items()):
        raise ValueError("Frozen original learner parameters changed")
    if list(k.COMPACT_SEEDS)!=[101,202,303]:raise ValueError("Frozen seeds changed")
    params=dict(k.COMPACT_PARAMS)
    rounds=int(params.pop("n_estimators"));params.pop("n_jobs",None)
    params.update(TARGETS[variant])
    return params,rounds,list(k.COMPACT_SEEDS)
