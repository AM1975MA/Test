"""Economic second-stage ridge: train ONLY on genuine annual OOS BASE predictions."""
from __future__ import annotations
import hashlib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

VARIANT="ECON_LAYER_OOS30"
AUX_FEATURES=("mom21_pct","mom63_pct","mom126_ex21_pct","vol21_pct",
              "downvol63_pct","drawdown63_pct","efficiency63_pct","rsi14_pct")
FEATURES=("base_rank",*AUX_FEATURES)
ALPHA=200.
BASE_FRACTION=.70
MIN_DATES=20
MAX_RETURN=.25
KEYS=("signal_date","ticker")

def array_hash(a):
    x=np.ascontiguousarray(a)
    h=hashlib.sha256()
    h.update(str(x.dtype).encode());h.update(str(x.shape).encode());h.update(x.tobytes())
    return h.hexdigest()

def prepare(frame):
    """Within-query BASE percentile and eight pre-existing observable Compact features."""
    if frame.empty or frame.duplicated(list(KEYS)).any():raise ValueError("Empty/duplicate query rows")
    if not frame[list(KEYS)].reset_index(drop=True).equals(frame.sort_values(list(KEYS))[list(KEYS)].reset_index(drop=True)):
        raise ValueError("Unsorted query rows")
    if frame["_base_pred"].isna().any() or not np.isfinite(frame["_base_pred"].to_numpy(float)).all():
        raise ValueError("BASE scores invalid")
    if any(name not in frame for name in AUX_FEATURES):raise ValueError("Missing frozen Compact feature")
    rank=frame.groupby("signal_date",sort=True)["_base_pred"].rank(method="average",pct=True)
    z=np.column_stack((rank.to_numpy(float),frame[list(AUX_FEATURES)].to_numpy(dtype=float)))
    z[~np.isfinite(z)]=np.nan
    if not np.isfinite(z[:,0]).all() or z.shape[1]!=len(FEATURES):
        raise ValueError("Meta features malformed")
    return z,rank.to_numpy(float)

def learn(history,cutoff):
    cutoff=pd.Timestamp(cutoff)
    if not ((history.signal_date<cutoff)&(history.exit_date_21<cutoff)).all():
        raise ValueError("Layer includes not-yet-mature label")
    if history.duplicated(list(KEYS)).any():raise ValueError("Duplicate historical OOS keys")
    num_dates=int(history.signal_date.nunique())
    if num_dates<MIN_DATES:
        return None,dict(fallback=True,training_dates=num_dates,train_rows=len(history),
                         meta_source="prior_annual_oos_compact_base")
    if "fwd_ret_21" not in history or not np.isfinite(history.fwd_ret_21.to_numpy(float)).all():
        raise ValueError("Historical economic target missing or nonfinite")
    x, _=prepare(history)
    median=np.array([float(np.median(c[np.isfinite(c)])) if np.isfinite(c).any() else 0. for c in x.T])
    zz=np.where(np.isfinite(x),x,median)
    mean=zz.mean(axis=0);sd=zz.std(axis=0)
    sd=np.where(sd>0,sd,1.)
    transformed=(zz-mean)/sd
    actual=history.fwd_ret_21.to_numpy(float)
    date_med=history.groupby("signal_date").fwd_ret_21.transform("median").to_numpy(float)
    y=np.clip(actual-date_med,-MAX_RETURN,MAX_RETURN)
    if not np.isfinite(transformed).all() or not np.isfinite(y).all():
        raise ValueError("Invalid standardized OOS economic history")
    m=Ridge(alpha=ALPHA,fit_intercept=True,solver="svd")
    m.fit(transformed,y)
    model=dict(median=median,mean=mean,scale=sd,coef=m.coef_.copy(),
               intercept=float(m.intercept_))
    audit=dict(fallback=False,training_dates=num_dates,train_rows=len(history),
        earliest_train_date=str(history.signal_date.min().date()),
        latest_train_date=str(history.signal_date.max().date()),
        latest_mature_label_exit=str(history.exit_date_21.max().date()),
        layer_target="clip(fwd_ret_21-date_median,-0.25,+0.25)",
        meta_source="prior_annual_oos_compact_base",
        feature_names=list(FEATURES),ridge_alpha=ALPHA,
        train_features_hash=array_hash(transformed),train_target_hash=array_hash(y),
        transform_state_hash={k:array_hash(model[k]) for k in ("median","mean","scale","coef")},
        trained_intercept=model["intercept"],training_only_statistics=True)
    return model,audit

def predict(frame,model):
    x,rank=prepare(frame)
    if model is None:return frame["_base_pred"].to_numpy(float).copy()
    imputed=np.where(np.isfinite(x),x,model["median"])
    z=(imputed-model["mean"])/model["scale"]
    expected=z@model["coef"]+model["intercept"]
    if not np.isfinite(expected).all():raise ValueError("Nonfinite economic predictions")
    tab=frame[list(KEYS)].copy();tab["economics"]=expected
    economic_rank=tab.groupby("signal_date",sort=True).economics.rank(method="average",pct=True).to_numpy(float)
    scores=BASE_FRACTION*rank+(1.-BASE_FRACTION)*economic_rank
    if not np.isfinite(scores).all() or scores.min()<0 or scores.max()>1:
        raise ValueError("Combined score invalid")
    return scores
