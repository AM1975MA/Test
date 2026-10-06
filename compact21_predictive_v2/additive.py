"""Frozen smooth-additive ablation of continuous-target Ridge.

Every learned transform sees only the supplied, strictly mature training frame.
This module does not select cohorts, tune parameters, or change strategy logic.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler

from etf_trader.source_only import kernel as k

KEYS = ["signal_date", "ticker"]
PARAMS = {
    "imputer_strategy": "median",
    "input_scaler": "StandardScaler",
    "n_knots": 4,
    "degree": 3,
    "knots": "quantile",
    "extrapolation": "linear",
    "include_bias": False,
    "design_scaler": "StandardScaler",
    "alpha": 30.0,
}


def array_hash(value):
    a = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode())
    h.update(str(a.shape).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def _matrix(frame):
    if any(name not in frame for name in k.F2D_FEATURES):
        raise ValueError("Missing canonical feature columns")
    try:
        x = frame[k.F2D_FEATURES].replace([np.inf, -np.inf], np.nan).to_numpy(dtype=float)
    except (ValueError, TypeError) as exc:
        raise ValueError("Features must be numeric") from exc
    return x


def validate(train, tests, year):
    cutoff = pd.Timestamp(year=int(year), month=1, day=1)
    if train.empty or not tests or any(frame.empty for frame in tests):
        raise ValueError("Empty training or inference frame")
    if len(k.F2D_FEATURES) != 125 or len(set(k.F2D_FEATURES)) != 125:
        raise ValueError("Unexpected canonical feature contract")
    for frame in [train, *tests]:
        if any(name not in frame for name in KEYS):
            raise ValueError("Missing prediction keys")
        if frame[KEYS].isna().any().any() or frame.duplicated(KEYS).any():
            raise ValueError("Invalid or duplicate prediction keys")
    if not train[KEYS].reset_index(drop=True).equals(
            train.sort_values(KEYS)[KEYS].reset_index(drop=True)):
        raise ValueError("Training rows must be key-sorted")
    if "exit_date_21" not in train or "target_rank_21" not in train:
        raise ValueError("Missing training maturity or target")
    signal = pd.to_datetime(train.signal_date, errors="coerce")
    exit_date = pd.to_datetime(train.exit_date_21, errors="coerce")
    if not (signal.notna().all() and exit_date.notna().all()
            and (signal < cutoff).all() and (exit_date < cutoff).all()):
        raise ValueError("Immature training rows")
    y = train.target_rank_21.to_numpy(dtype=float)
    if not np.isfinite(y).all() or ((y < 0) | (y > 1)).any():
        raise ValueError("Invalid continuous percentile target")
    x = _matrix(train)
    if np.isnan(x).all(axis=0).any():
        raise ValueError("Entirely missing training feature")
    test_x = [_matrix(frame) for frame in tests]
    return cutoff, x, test_x, y


def fit_additive(train, tests, year, tmp=None, tag="fit"):
    """Return predictions, provenance audit, continuous labels and fit seconds."""
    cutoff, x, test_x, y = validate(train, tests, year)
    start = time.perf_counter()
    model = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(),
        SplineTransformer(n_knots=4, degree=3, knots="quantile",
                          extrapolation="linear", include_bias=False),
        StandardScaler(),
        Ridge(alpha=30.0),
    )
    model.fit(x, y)
    predictions = [np.asarray(model.predict(t), dtype=float) for t in test_x]
    if any(len(p) != len(frame) or not np.isfinite(p).all()
           for p, frame in zip(predictions, tests)):
        raise ValueError("Nonfinite or invalid predictions")
    imputer, input_scale, spline, design_scale, ridge = [s[1] for s in model.steps]
    if imputer.n_features_in_ != 125 or len(imputer.statistics_) != 125:
        raise ValueError("Imputer changed canonical feature dimensions")
    design = model[:-1].transform(x)
    test_design = [model[:-1].transform(t) for t in test_x]
    if not np.isfinite(design).all() or any(not np.isfinite(t).all() for t in test_design):
        raise ValueError("Nonfinite transformed design")
    states = {
        "imputer_statistics": imputer.statistics_,
        "input_scaler_mean": input_scale.mean_,
        "input_scaler_scale": input_scale.scale_,
        "input_scaler_variance": input_scale.var_,
        "design_scaler_mean": design_scale.mean_,
        "design_scaler_scale": design_scale.scale_,
        "design_scaler_variance": design_scale.var_,
        "ridge_coef": ridge.coef_,
        "ridge_intercept": ridge.intercept_,
    }
    for i, basis in enumerate(spline.bsplines_):
        states[f"spline_{i}_knots"] = basis.t
        states[f"spline_{i}_coefficients"] = basis.c
    meta = {
        "kind": "ADDITIVE_RIDGE",
        "feature_transform": "median_imputer_standard_scaler_quantile_cubic_splines_design_scaler",
        "target": "continuous_percentile",
        "model_params": dict(PARAMS),
        "feature_names": list(k.F2D_FEATURES),
        "input_features": 125,
        "all_missing_features": [],
        "constant_features": [name for i, name in enumerate(k.F2D_FEATURES)
                              if np.nanmin(x[:, i]) == np.nanmax(x[:, i])],
        "features_with_repeated_spline_knots": [name for name, basis in zip(k.F2D_FEATURES, spline.bsplines_)
                                               if len(np.unique(basis.t)) < len(basis.t)],
        "design_features": int(design.shape[1]),
        "train_rows": len(train),
        "test_rows": [len(frame) for frame in tests],
        "cutoff": cutoff.isoformat(),
        "max_signal_date": pd.to_datetime(train.signal_date).max().isoformat(),
        "max_exit_date_21": pd.to_datetime(train.exit_date_21).max().isoformat(),
        "maturity_PASS": True,
        "train_matrix_sha256": array_hash(x),
        "train_labels_sha256": array_hash(y),
        "train_groups_sha256": array_hash(train.groupby("signal_date", sort=True).size().to_numpy()),
        "fit_matrix_sha256": array_hash(design),
        "test_matrix_sha256": [array_hash(t) for t in test_x],
        "test_fit_matrix_sha256": [array_hash(t) for t in test_design],
        "prediction_sha256": [array_hash(p) for p in predictions],
        "learned_state_hashes": {name: array_hash(value) for name, value in states.items()},
        "imputer_statistics": imputer.statistics_.tolist(),
        "scaler_mean": input_scale.mean_.tolist(),
        "scaler_scale": input_scale.scale_.tolist(),
        "spline_knots": [basis.t.tolist() for basis in spline.bsplines_],
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "environment": {name: importlib.metadata.version(name)
                        for name in ("numpy", "pandas", "scipy", "scikit-learn")},
    }
    if tmp is not None:
        import joblib
        destination = Path(tmp)
        destination.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, destination / f"{tag}_additive.joblib")
    return predictions, meta, y, time.perf_counter() - start


fit = fit_additive
