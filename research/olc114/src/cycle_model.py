"""Portable, date-balanced value heads for fixed 42-session complete plans.

Only mature rows are inspected numerically. There is no market-data loading or
fitting at import time. Model inference needs NumPy, never sklearn or pickle;
sklearn is imported locally only when fitting the prescribed small tree.
"""
from __future__ import annotations

import copy
import hashlib
import json

import numpy as np

HORIZON = 42
BLOCK_LENGTH = 63
MODEL_NAMES = ("MEAN", "RIDGE", "TREE")
TREE_PARAMETERS = {"ccp_alpha": 0.0, "criterion": "squared_error", "max_depth": 2,
                   "max_features": None, "max_leaf_nodes": None,
                   "min_impurity_decrease": 0.0, "min_samples_leaf": 1,
                   "min_samples_split": 2, "min_weight_fraction_leaf": .20,
                   "monotonic_cst": None, "random_state": 114, "splitter": "best"}


def canonical_hash(value) -> str:
    """SHA256 of finite sorted, compact ASCII JSON encoded as UTF-8."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode("utf-8")).hexdigest()


def model_hash(value_model: "ValueModel") -> str:
    return canonical_hash(value_model.to_dict())


def _predict_fitted(kind, fitted, x, scaler):
    if kind == "MEAN":
        return float(fitted["value"])
    if kind == "RIDGE":
        z = (x - np.asarray(scaler["mean"])) / np.asarray(scaler["scale"])
        return float(fitted["intercept"] + z @ np.asarray(fitted["coef"]))
    # sklearn's tree prediction converts the feature vector to float32 before
    # comparing against double precision thresholds. Keeping x in float64 here
    # would silently send sufficiently close boundary values to a different leaf.
    features = x.astype(np.float32)
    node = 0
    while fitted["children_left"][node] != -1:
        feature = fitted["feature"][node]
        node = (fitted["children_left"][node] if features[feature] <= fitted["threshold"][node]
                else fitted["children_right"][node])
    return float(fitted["value"][node])


class ValueModel:
    """One full-training estimator and all paired bootstrap estimators.

    ``scaler`` is the full-training representation, retained for every model
    for state-support diagnostics. Only RIDGE applies it during inference.
    The lower statistic uses NumPy's linear-interpolated 10th percentile.
    """

    def __init__(self, payload):
        # JSON round-trip both rejects nonfinite values and prevents caller
        # mutation of arrays shared by fitted models or provenance.
        self._payload = json.loads(json.dumps(payload, allow_nan=False))
        if self._payload.get("schema_version") != 1:
            raise ValueError("unsupported value-model schema")
        if self._payload.get("kind") not in MODEL_NAMES:
            raise ValueError("unknown model kind")
        if not self._payload.get("bootstraps"):
            raise ValueError("bootstrap estimators are required")

    @property
    def training_scaler(self):
        return copy.deepcopy(self._payload["scaler"])

    def predict(self, x):
        x = np.asarray(x, dtype=float)
        if x.shape != (self._payload["n_features"],) or not np.all(np.isfinite(x)):
            raise ValueError("prediction requires one finite feature vector")
        kind, scaler = self._payload["kind"], self._payload["scaler"]
        mean = _predict_fitted(kind, self._payload["fitted"], x, scaler)
        values = [_predict_fitted(kind, fitted, x, scaler)
                  for fitted in self._payload["bootstraps"]]
        lower = float(np.quantile(values, .10, method="linear"))
        if not np.isfinite(mean) or not np.isfinite(lower):
            raise ValueError("prediction is nonfinite")
        return {"mean": mean, "lower": lower}

    def to_dict(self):
        return copy.deepcopy(self._payload)

    @classmethod
    def from_dict(cls, payload):
        return cls(payload)


def _fit_ridge(z, y, weights, penalty):
    w = weights / weights.sum()
    zm = w @ z
    ym = float(w @ y)
    centered = z - zm
    matrix = centered.T @ (w[:, None] * centered) + penalty * np.eye(z.shape[1])
    rhs = centered.T @ (w * (y - ym))
    coef = np.linalg.solve(matrix, rhs) if penalty > 0 else np.linalg.lstsq(matrix, rhs, rcond=None)[0]
    return {"intercept": float(ym - zm @ coef), "coef": coef.tolist()}


def _fit_tree(X, y, weights):
    from sklearn.tree import DecisionTreeRegressor
    estimator = DecisionTreeRegressor(**TREE_PARAMETERS)
    estimator.fit(X, y, sample_weight=weights)
    tree = estimator.tree_
    return {"children_left": tree.children_left.tolist(),
            "children_right": tree.children_right.tolist(),
            "feature": tree.feature.tolist(), "threshold": tree.threshold.tolist(),
            "value": tree.value[:, 0, 0].tolist()}


def _integer_vector(values, name):
    values = np.asarray(values)
    if values.ndim != 1 or not np.issubdtype(values.dtype, np.integer):
        raise ValueError(f"{name} must be a one-dimensional integer array")
    return values.astype(np.int64, copy=False)


def fit_head(X, y, signal_idx, terminal_idx, cutoff, dates, *, min_dates=504,
             min_months=24, min_blocks=12, n_boot=32, seed=114, penalty=1.):
    """Fit matched MEAN/RIDGE/TREE heads, or return None before readiness.

    Fixed blocks are the occupied absolute panel-index blocks ``signal//63``.
    Each replicate draws as many blocks as are occupied, with replacement.
    Every leg on each sampled date receives that date's multiplicity divided by
    its leg count. Thus rows never create independent-date support, and pooled
    date weight remains one before bootstrap multiplicities. Bootstrap Ridge
    fits use the original full-training scaler without re-estimating it.

    The readiness count greedily selects [signal, signal+42) return intervals;
    a signal at the previous terminal shares no return increment and is legal.
    """
    signal = _integer_vector(signal_idx, "signal_idx")
    terminal = _integer_vector(terminal_idx, "terminal_idx")
    X, y = np.asarray(X), np.asarray(y)
    if X.ndim != 2 or X.shape[1] < 1 or y.ndim != 1 or not (len(X) == len(y) == len(signal) == len(terminal)):
        raise ValueError("X/y/index dimensions do not agree")
    if not isinstance(cutoff, (int, np.integer)) or cutoff < 0:
        raise ValueError("cutoff must be a nonnegative integer panel index")
    if any(not isinstance(v, (int, np.integer)) or v < 1
           for v in (min_dates, min_months, min_blocks, n_boot)):
        raise ValueError("readiness counts and bootstrap count must be positive integers")
    if not np.isfinite(penalty) or penalty < 0:
        raise ValueError("penalty must be finite and nonnegative")
    mature = terminal < cutoff
    if not np.any(mature):
        return None
    # Never validate the content of immature features or labels: future NaNs or
    # extreme outcomes must not alter an earlier fit or its numerical identity.
    X, y = np.asarray(X[mature], dtype=float), np.asarray(y[mature], dtype=float)
    signal, terminal = signal[mature], terminal[mature]
    if not np.all(np.isfinite(X)) or not np.all(np.isfinite(y)):
        raise ValueError("mature training values must be finite")
    if np.any(signal < 0) or np.any(terminal != signal + HORIZON):
        raise ValueError("mature outcomes must have exactly 42-session horizon")
    dates = np.asarray(dates, dtype="datetime64[D]")
    if dates.ndim != 1 or np.any(signal >= len(dates)) or np.any(terminal >= len(dates)):
        raise ValueError("mature indices exceed panel date support")
    distinct, inverse, date_counts = np.unique(signal, return_inverse=True, return_counts=True)
    signal_dates = dates[distinct]
    if np.any(np.isnat(signal_dates)):
        raise ValueError("mature signal dates must be valid")
    months = np.unique(signal_dates.astype("datetime64[M]"))
    nonoverlap = []
    for k in distinct:
        if not nonoverlap or k >= nonoverlap[-1] + HORIZON:
            nonoverlap.append(int(k))
    if len(distinct) < min_dates or len(months) < min_months or len(nonoverlap) < min_blocks:
        return None
    weights = 1. / date_counts[inverse]
    normalized = weights / weights.sum()
    mean = normalized @ X
    scale = np.sqrt(normalized @ ((X - mean) ** 2))
    scale[scale == 0] = 1.
    scaler = {"mean": mean.tolist(), "scale": scale.tolist()}
    z = (X - mean) / scale
    support = np.unique(distinct // BLOCK_LENGTH)
    draws = np.random.default_rng(seed).choice(support, size=(n_boot, len(support)), replace=True)
    bootstrap_spec = {"seed": int(seed), "block_length": BLOCK_LENGTH,
                      "block_origin": 0, "support": support.tolist(), "draws": draws.tolist()}
    draw_hash = canonical_hash(bootstrap_spec)
    provenance = {"cutoff": int(cutoff), "horizon": HORIZON,
                  "draw_hash": draw_hash, "bootstrap": bootstrap_spec,
                  "training_hash": canonical_hash({"X": X.tolist(), "y": y.tolist(),
                      "signal_idx": signal.tolist(), "terminal_idx": terminal.tolist(),
                      "signal_dates": signal_dates.astype(str).tolist(), "weights": weights.tolist()})}
    parameters = {"MEAN": {}, "RIDGE": {"penalty": float(penalty), "loss": "weighted_mean_squared_error",
                                        "penalize_intercept": False},
                  "TREE": dict(TREE_PARAMETERS)}
    fitted = {name: [] for name in MODEL_NAMES}
    row_blocks = np.searchsorted(support, signal // BLOCK_LENGTH)
    for replicate in range(n_boot + 1):
        if replicate == 0:
            current_weights = weights
        else:
            multiplicity = np.bincount(np.searchsorted(support, draws[replicate - 1]), minlength=len(support))
            current_weights = weights * multiplicity[row_blocks]
        fitted["MEAN"].append({"value": float(np.average(y, weights=current_weights))})
        fitted["RIDGE"].append(_fit_ridge(z, y, current_weights, penalty))
        fitted["TREE"].append(_fit_tree(X, y, current_weights))
    models = {name: ValueModel({"schema_version": 1, "kind": name, "n_features": X.shape[1],
                               "scaler": scaler, "parameters": parameters[name],
                               "fitted": fitted[name][0], "bootstraps": fitted[name][1:],
                               "provenance": provenance}) for name in MODEL_NAMES}
    meta = {"ready": True, "cutoff": int(cutoff), "mature_rows": len(y),
            "mature_dates": len(distinct), "mature_months": len(months),
            "nonoverlap_42": len(nonoverlap), "nonoverlap_signal_idx": nonoverlap,
            "signal_idx": signal.tolist(), "terminal_idx": terminal.tolist(),
            "distinct_signal_idx": distinct.tolist(), "training_weights": weights.tolist(),
            "scaler": scaler, "feature_scaler": scaler,
            "feature_min": X.min(axis=0).tolist(), "feature_max": X.max(axis=0).tolist(),
            "mature_first_signal_idx": int(distinct[0]), "mature_last_signal_idx": int(distinct[-1]),
            "max_terminal_idx": int(terminal.max()), "training_hash": provenance["training_hash"],
            "block_support": support.tolist(), "bootstrap_draws": draws.tolist(),
            "bootstrap_spec": bootstrap_spec, "draw_hash": draw_hash,
            "readiness": {"min_dates": int(min_dates), "min_months": int(min_months),
                          "min_blocks": int(min_blocks)}, "horizon": HORIZON}
    return {"models": models, "hashes": {name: model_hash(value) for name, value in models.items()}, "meta": meta}
