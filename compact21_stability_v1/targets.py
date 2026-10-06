"""Preregistered compact21 relevance targets; never fit on outcome data.

The economic target quantizes next-open/21-session-open simple returns to a
fixed 1 bp grid, then densely ranks the grid coordinates within each signal
date. Economic ties remain ties; tickers never break them. The ordinal control
densely ranks the existing percentile target without multiplying/rounding it.

The 1 bp grid is an economic resolution choice, not an estimate of vendor data
error. Small changes can still cross fixed grid edges. Invariance applies only
inside the same grid cell; this module makes no stronger stability claim.
"""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

RETURN_QUANTUM = 0.0001  # One absolute basis point of simple return.
TargetMode = Literal["legacy", "ordinal", "economic"]


def _numeric(frame: pd.DataFrame, column: str) -> np.ndarray:
    if column not in frame:
        raise ValueError(f"Missing target column: {column}")
    try:
        return pd.to_numeric(frame[column], errors="raise").to_numpy(
            dtype=float, na_value=np.nan
        )
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Target column must be numeric: {column}") from exc


def _validate_frame(frame: pd.DataFrame) -> pd.Series:
    for column in ("signal_date", "ticker"):
        if column not in frame:
            raise ValueError(f"Missing key column: {column}")
        if frame[column].isna().any():
            raise ValueError(f"Missing key values: {column}")
    if frame.duplicated(["signal_date", "ticker"]).any():
        raise ValueError("Duplicate signal_date/ticker target keys")
    dates = pd.to_datetime(frame["signal_date"], errors="raise")
    # Avoid pandas index alignment changing results when the caller has a
    # repeated or shuffled index. Keys, rather than index labels, identify rows.
    return pd.Series(dates.to_numpy(), index=pd.RangeIndex(len(frame)))


def quantize_returns(values: np.ndarray) -> np.ndarray:
    """Return fixed grid coordinates, retaining nonfinite inputs as NaN.

    Nearest-grid rounding uses NumPy's deterministic nearest-even convention.
    The grid is anchored at zero and is never calibrated from observed data.
    Coordinates are bounded to exactly represented float integers.
    """
    values = np.asarray(values, dtype=float)
    result = np.full(values.shape, np.nan, dtype=float)
    finite = np.isfinite(values)
    coordinates = values[finite] / RETURN_QUANTUM
    if not np.isfinite(coordinates).all() or (np.abs(coordinates) > 2**52).any():
        raise ValueError("Forward return exceeds exact grid coordinate range")
    result[finite] = np.rint(coordinates)
    return result


def build_labels(
    frame: pd.DataFrame,
    mode: TargetMode = "economic",
    *,
    cutoff: pd.Timestamp | str | None = None,
) -> pd.Series:
    """Build aligned labels, preserving invalid source values as NaN.

    Use ``cutoff`` for every training call: finite labels must have both signal
    and exit dates strictly before that cutoff. Omit only for target diagnostics
    which do not fit a model. This function does not silently drop/reorder rows.
    Dense labels start at zero, are integral where valid, and require no
    relevance-magnitude interpretation under rank:pairwise.
    """
    if mode not in ("legacy", "ordinal", "economic"):
        raise ValueError(f"Unknown target mode: {mode}")
    dates = _validate_frame(frame)
    rank = None
    if mode in ("legacy", "ordinal") or "target_rank_21" in frame:
        rank = _numeric(frame, "target_rank_21")
        valid_rank = np.isfinite(rank)
        if ((rank[valid_rank] <= 0) | (rank[valid_rank] > 1)).any():
            raise ValueError("Finite target_rank_21 must lie in (0, 1]")
    if mode == "economic":
        outcome = _numeric(frame, "fwd_ret_21")
        values = quantize_returns(outcome)
        if rank is not None:
            if not np.array_equal(np.isfinite(outcome), np.isfinite(rank)):
                raise ValueError("Forward-return/rank validity mismatch")
            # Original ranks can come from a larger feature-validity universe;
            # compare ordering/ties, not percentile magnitudes or denominators.
            raw_dense = pd.Series(outcome).where(np.isfinite(outcome)).groupby(
                dates, sort=False
            ).rank(method="dense")
            rank_dense = pd.Series(rank).where(np.isfinite(rank)).groupby(
                dates, sort=False
            ).rank(method="dense")
            if not np.array_equal(
                raw_dense.to_numpy(), rank_dense.to_numpy(), equal_nan=True
            ):
                raise ValueError("Forward-return/rank ordering or tie mismatch")
    else:
        values = rank.copy()
        values[~np.isfinite(values)] = np.nan

    valid = np.isfinite(values)
    if cutoff is not None:
        if "exit_date_21" not in frame:
            raise ValueError("Training targets require exit_date_21")
        exits = pd.to_datetime(frame["exit_date_21"], errors="raise")
        cutoff = pd.Timestamp(cutoff)
        matured = (dates < cutoff).to_numpy() & (exits < cutoff).to_numpy()
        if (valid & ~matured).any():
            raise ValueError("Immature compact21 target at training cutoff")

    if mode == "legacy":
        labels = np.full(len(frame), np.nan)
        labels[valid] = np.rint(values[valid] * 100)
    else:
        labels = (
            pd.Series(values).groupby(dates, sort=False).rank(method="dense") - 1
        ).to_numpy()
    return pd.Series(labels, index=frame.index, name=f"label_{mode}_21")


def training_labels(
    frame: pd.DataFrame,
    cutoff: pd.Timestamp | str,
    mode: TargetMode = "economic",
) -> np.ndarray:
    """Worker-ready int64 labels; reject invalid or immature training rows."""
    labels = build_labels(frame, mode=mode, cutoff=cutoff).to_numpy()
    if not np.isfinite(labels).all():
        raise ValueError("Invalid compact21 training labels; filter before fit")
    return labels.astype(np.int64)
