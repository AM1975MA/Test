"""Causal, date-balanced Ridge heads for native net action advantages.

This module fits one economic action head. It does not generate financial labels,
choose orders, subtract fees, or run a portfolio. Its block-bootstrap lower bound
is a heuristic conditional on a fixed training-only feature representation.
"""
import copy
import hashlib

import numpy as np


HORIZON_SESSIONS = 21
BOOTSTRAP_BLOCK_SESSIONS = 63
LOWER_QUANTILE = 0.10
ARMS = ("MEAN", "PRICE", "VIX", "TERM")


def _integer(value, name, minimum=None):
    if not np.isscalar(value) or not np.isfinite(value) or int(value) != value:
        raise ValueError(f"{name} must be a finite integer")
    value = int(value)
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _matrix(value, name):
    result = np.asarray(value, dtype=float)
    if result.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional array")
    return result


def _vector(value, name, length):
    result = np.asarray(value, dtype=float)
    if result.ndim != 1 or len(result) != length:
        raise ValueError(f"{name} must be one-dimensional with {length} rows")
    return result


def _scaler_fit(values, weights, reference=None):
    mean = weights @ values
    centered = values - mean
    scale = np.sqrt(weights @ (centered * centered))
    if reference is None:
        reference = np.max(np.abs(values), axis=0)
    # Numerical OLS residue must not be amplified into a new unit-variance signal.
    tolerance = 1e-10 * np.maximum(1.0, np.asarray(reference))
    active = scale > tolerance
    safe_scale = np.where(active, scale, 1.0)
    scaled = np.where(active, centered / safe_scale, 0.0)
    if not np.isfinite(scaled).all():
        raise ValueError("Non-finite training representation after scaling")
    return scaled, {"mean": mean, "scale": safe_scale, "active": active}


def _scale(values, scaler):
    return np.where(scaler["active"], (values - scaler["mean"]) / scaler["scale"], 0.0)


def _projection(design, outcomes, weights):
    root_weights = np.sqrt(weights)[:, None]
    return np.linalg.lstsq(design * root_weights, outcomes * root_weights, rcond=None)[0]


def _fit_representation(price, legacy, term, weights):
    zp, price_scaler = _scaler_fit(price, weights)
    p_design = np.column_stack((np.ones(len(price)), zp))
    legacy_projection = _projection(p_design, legacy, weights)
    legacy_residual = legacy - p_design @ legacy_projection
    zl, legacy_scaler = _scaler_fit(legacy_residual, weights, np.max(np.abs(legacy), axis=0))
    pl_design = np.column_stack((p_design, zl))
    term_projection = _projection(pl_design, term, weights)
    term_residual = term - pl_design @ term_projection
    zt, term_scaler = _scaler_fit(term_residual, weights, np.max(np.abs(term), axis=0))
    transforms = {
        "price_scaler": price_scaler,
        "legacy_projection": legacy_projection,
        "legacy_scaler": legacy_scaler,
        "term_projection": term_projection,
        "term_scaler": term_scaler,
    }
    designs = {
        "MEAN": np.ones((len(price), 1)),
        "PRICE": p_design,
        "VIX": pl_design,
        "TERM": np.column_stack((pl_design, zt)),
    }
    return designs, transforms


def _ridge(design, y, weights, penalty):
    weights = weights / weights.sum()
    gram = design.T @ (weights[:, None] * design)
    rhs = design.T @ (weights * y)
    regularizer = np.eye(design.shape[1]) * penalty
    regularizer[0, 0] = 0.0
    if penalty > 0:
        return np.linalg.solve(gram + regularizer, rhs)
    return np.linalg.lstsq(gram, rhs, rcond=None)[0]


def _nonoverlap_count(signals, terminals):
    dates, inverse = np.unique(signals, return_inverse=True)
    ends = dates + HORIZON_SESSIONS
    # Duplicated states share one date; use its latest required outcome endpoint.
    np.maximum.at(ends, inverse, terminals)
    order = np.lexsort((dates, ends))
    previous_end = None
    count = 0
    for i in order:
        if previous_end is None or dates[i] >= previous_end:
            count += 1
            previous_end = ends[i]
    return count


def _jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


class AdvantageModel:
    """One information arm, with fixed transforms and paired bootstrap fits."""

    def __init__(self, name, coefficients, bootstrap_coefficients, transforms, feature_counts, metadata):
        self.name = name
        self.coefficients = np.asarray(coefficients, dtype=float).copy()
        self.bootstrap_coefficients = np.asarray(bootstrap_coefficients, dtype=float).copy()
        self.transforms = copy.deepcopy(transforms)
        self.feature_counts = tuple(feature_counts)
        self.metadata = copy.deepcopy(metadata)

    def _prediction_vector(self, price, legacy, term):
        if self.name == "MEAN":
            return np.ones(1)
        p = _vector(price, "price", self.feature_counts[0])
        if not np.isfinite(p).all():
            raise ValueError("PRICE prediction features must be finite")
        zp = _scale(p, self.transforms["price_scaler"])
        p_design = np.concatenate(([1.0], zp))
        if self.name == "PRICE":
            return p_design
        legacy = _vector(legacy, "legacy", self.feature_counts[1])
        if not np.isfinite(legacy).all():
            raise ValueError("VIX prediction features must be finite")
        residual_legacy = legacy - p_design @ self.transforms["legacy_projection"]
        zl = _scale(residual_legacy, self.transforms["legacy_scaler"])
        pl_design = np.concatenate((p_design, zl))
        if self.name == "VIX":
            return pl_design
        term = _vector(term, "term", self.feature_counts[2])
        if not np.isfinite(term).all():
            raise ValueError("TERM prediction features must be finite")
        residual_term = term - pl_design @ self.transforms["term_projection"]
        zt = _scale(residual_term, self.transforms["term_scaler"])
        return np.concatenate((pl_design, zt))

    def predict(self, price, legacy, term):
        """Return native net mean and the 10th bootstrap conditional-mean quantile."""
        vector = self._prediction_vector(price, legacy, term)
        mean = float(vector @ self.coefficients)
        lower = float(np.quantile(self.bootstrap_coefficients @ vector, LOWER_QUANTILE))
        if not np.isfinite(mean) or not np.isfinite(lower):
            raise ValueError("Non-finite action-advantage prediction")
        return {"mean": mean, "lower": lower}

    def to_dict(self):
        """Export the entire fitted arm without arrays or non-JSON scalar types."""
        return _jsonable({
            "model_name": self.name,
            "coefficients": self.coefficients,
            "bootstrap_coefficients": self.bootstrap_coefficients,
            "feature_counts": self.feature_counts,
            "transforms": self.transforms,
            "metadata": self.metadata,
        })


def fit_head(Xprice, Xlegacy, Xterm, y, signal_idx, terminal_idx, cutoff, *,
             min_dates=504, min_blocks=24, n_boot=100, seed=111, penalty=1.0):
    """Fit four nested arms on one common, strictly matured sample.

    Input feature matrices are (rows, features); labels/session indices are1-D.
    Date weights sum to one per distinct signal date before normalization. Every
    bootstrap samples fixed63-session blocks with replacement, using the same
    draws for all arms and retaining all rows/states attached to selected dates.
    Full-training transforms stay fixed within that coefficient bootstrap.
    """
    cutoff = _integer(cutoff, "cutoff")
    min_dates = _integer(min_dates, "min_dates", 1)
    min_blocks = _integer(min_blocks, "min_blocks", 0)
    n_boot = _integer(n_boot, "n_boot", 1)
    seed = _integer(seed, "seed", 0)
    if not np.isscalar(penalty) or not np.isfinite(penalty) or penalty < 0:
        raise ValueError("penalty must be finite and nonnegative")
    penalty = float(penalty)
    price, legacy, term = (_matrix(value, name) for value, name in
                           ((Xprice, "Xprice"), (Xlegacy, "Xlegacy"), (Xterm, "Xterm")))
    n = len(price)
    if len(legacy) != n or len(term) != n:
        raise ValueError("All feature blocks must have identical row counts")
    y = _vector(y, "y", n)
    signals = _vector(signal_idx, "signal_idx", n)
    terminals = _vector(terminal_idx, "terminal_idx", n)
    mask = (np.isfinite(y) & np.isfinite(signals) & np.isfinite(terminals)
            & (signals == np.floor(signals)) & (terminals == np.floor(terminals))
            & (terminals >= signals + HORIZON_SESSIONS) & (terminals < cutoff)
            & np.isfinite(price).all(axis=1) & np.isfinite(legacy).all(axis=1)
            & np.isfinite(term).all(axis=1))
    if not mask.any():
        return None
    price, legacy, term, y = (array[mask] for array in (price, legacy, term, y))
    signals, terminals = signals[mask].astype(np.int64), terminals[mask].astype(np.int64)
    order = np.argsort(signals, kind="stable")
    price, legacy, term, y, signals, terminals = (
        array[order] for array in (price, legacy, term, y, signals, terminals))
    dates, inverse, date_counts = np.unique(signals, return_inverse=True, return_counts=True)
    n_nonoverlap = _nonoverlap_count(signals, terminals)
    if len(dates) < min_dates or n_nonoverlap < min_blocks:
        return None
    weights = 1.0 / date_counts[inverse]
    weights /= weights.sum()
    designs, transforms = _fit_representation(price, legacy, term, weights)
    block_ids, row_blocks = np.unique(signals // BOOTSTRAP_BLOCK_SESSIONS, return_inverse=True)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(block_ids), size=(n_boot, len(block_ids)))
    counts = np.stack([np.bincount(row, minlength=len(block_ids)) for row in draws])
    counts_hash = hashlib.sha256(np.asarray(counts, dtype="<i8").tobytes()).hexdigest()
    metadata = {
        "cutoff": cutoff,
        "n_rows": len(y),
        "n_dates": len(dates),
        "n_nonoverlap_blocks": n_nonoverlap,
        "min_signal_idx": int(signals.min()),
        "max_signal_idx": int(signals.max()),
        "max_terminal_idx": int(terminals.max()),
        "n_bootstrap_blocks": len(block_ids),
        "bootstrap_block_ids": block_ids.tolist(),
        "bootstrap_block_sessions": BOOTSTRAP_BLOCK_SESSIONS,
        "bootstrap_counts_sha256": counts_hash,
        "n_boot": n_boot,
        "seed": seed,
        "penalty_mean_loss_scale": penalty,
        "lower_quantile": LOWER_QUANTILE,
        "bootstrap_representation": "fixed_full_mature_training_transform",
        "bootstrap_interpretation": "paired_coefficient_heuristic_not_calibrated_confidence",
        "target": "native_net_log_wealth_advantage_no_extra_fee_offset",
    }
    feature_counts = (price.shape[1], legacy.shape[1], term.shape[1])
    models = {}
    for name in ARMS:
        design = designs[name]
        coefficients = _ridge(design, y, weights, penalty)
        bootstrap = np.stack([
            _ridge(design, y, weights * counts[b, row_blocks], penalty)
            for b in range(n_boot)
        ])
        models[name] = AdvantageModel(name, coefficients, bootstrap, transforms, feature_counts, metadata)
    return {"models": models, "meta": copy.deepcopy(metadata)}
