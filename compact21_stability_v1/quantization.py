"""Causal, auditable scale-aware feature quantization for Compact21.

Fit a separate instance on each eligible annual training window and snapshot.
The default rule is frozen at 4096 cells: known bounded feature domains use
their domain width; other features use training IQR. The grid is zero-anchored,
its step is rounded upward to a power of two, and ties use NumPy ties-to-even.
This is a scale resolution rule, NOT an estimated measurement noise floor.

Limitations: values around bin boundaries can still disagree; training IQR can
cross a dyadic step boundary between snapshots. Quantization after feature
construction cannot undo raw differences already amplified by cross-sectional
ranks, robust deviations, missingness, or row eligibility. No clipping occurs.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd


SCHEMA_VERSION = "COMPACT21_STABILITY_V1_SCALE_QUANTIZER_1"
DEFAULT_CELLS = 4096


def _domain_width(name: str) -> float | None:
    """Widths from source_only/kernel.py, rather than observed test bounds."""
    if name.endswith("_pct"):
        return 1.0
    if name.endswith("_dev"):
        return 16.0  # cs_robust_dev explicitly clips at [-8, 8].
    if name.startswith(("efficiency", "drawdown", "breakout_pos")):
        return 1.0
    if name == "positive_frac63":
        return 1.0
    if name.startswith("corr_mkt") or name == "autocorr1_63":
        return 2.0
    if name == "rsi14":
        return 100.0
    if name == "sign_entropy63":
        return math.log(2.0)  # Kernel uses natural logarithms.
    return None


def _ceil_power_of_two(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError("A quantization resolution must be finite and positive")
    mantissa, exponent = math.frexp(value)
    exponent = exponent - 1 if mantissa == 0.5 else exponent
    # Finite, normal dyadic steps avoid division by zero/subnormal artifacts.
    return math.ldexp(1.0, min(1023, max(-1022, exponent)))


class ScaleAwareQuantizer:
    """Fit only feature scales, then use identical grids at train/inference.

    DataFrames may contain metadata: only ``feature_names`` are read, and the
    returned DataFrame contains those features in their declared order.
    Arrays must already have the declared order. Inputs are never mutated.
    ``minimum_steps`` are optional externally preregistered resolutions, not
    fitted from targets, outcomes, validation data, or repeat differences.
    """

    def __init__(
        self,
        feature_names: Sequence[str],
        *,
        cells: int = DEFAULT_CELLS,
        minimum_steps: Mapping[str, float] | None = None,
    ) -> None:
        self.feature_names = tuple(feature_names)
        if not self.feature_names or len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("feature_names must be nonempty and unique")
        if not all(isinstance(name, str) and name for name in self.feature_names):
            raise ValueError("feature_names must be nonempty strings")
        if any(name.startswith("target_") for name in self.feature_names):
            raise ValueError("Target columns are not quantizer features")
        if isinstance(cells, bool) or not isinstance(cells, int) or cells < 1:
            raise ValueError("cells must be a positive integer")
        self.cells = cells
        self.minimum_steps = dict(minimum_steps or {})
        if set(self.minimum_steps) - set(self.feature_names):
            raise ValueError("minimum_steps contains undeclared features")
        for value in self.minimum_steps.values():
            if not math.isfinite(value) or value <= 0:
                raise ValueError("minimum_steps must be finite and positive")
        self._audit: dict[str, Any] | None = None
        self.steps_: np.ndarray | None = None

    def _array(self, values: pd.DataFrame | np.ndarray) -> np.ndarray:
        if isinstance(values, pd.DataFrame):
            if not values.columns.is_unique:
                raise ValueError("Input DataFrame columns must be unique")
            missing = set(self.feature_names) - set(values.columns)
            if missing:
                raise ValueError(f"Missing quantizer features: {sorted(missing)}")
            array = values.loc[:, list(self.feature_names)].to_numpy(dtype=np.float64, copy=True)
        else:
            array = np.array(values, dtype=np.float64, copy=True)
        if array.ndim != 2 or array.shape[1] != len(self.feature_names):
            raise ValueError("Input must be a matrix with one column per declared feature")
        return array

    def fit(self, train_features: pd.DataFrame | np.ndarray) -> ScaleAwareQuantizer:
        array = self._array(train_features)
        if len(array) == 0:
            raise ValueError("Cannot fit an empty training window")
        entries = []
        for index, name in enumerate(self.feature_names):
            finite = array[:, index][np.isfinite(array[:, index])]
            q1, median, q3 = (np.quantile(finite, [0.25, 0.5, 0.75]) if len(finite)
                              else (None, None, None))
            width = _domain_width(name)
            if width is not None:
                scale, rule = width, "fixed_kernel_domain"
            elif len(finite) and q3 > q1:
                scale, rule = float(q3 - q1), "training_iqr"
            elif len(finite):
                scale, rule = max(abs(float(median)), 1.0), "zero_iqr_magnitude_fallback"
            else:
                scale, rule = 1.0, "all_nonfinite_unit_fallback"
            resolution = max(scale / self.cells, self.minimum_steps.get(name, 0.0))
            step = _ceil_power_of_two(resolution)
            entries.append({
                "name": name, "rule": rule, "scale": float(scale), "step": step,
                "finite_training_count": int(len(finite)),
                "nonfinite_training_count": int(len(array) - len(finite)),
                "training_q1": None if q1 is None else float(q1),
                "training_median": None if median is None else float(median),
                "training_q3": None if q3 is None else float(q3),
                "preregistered_minimum_step": self.minimum_steps.get(name),
            })
        self.steps_ = np.array([entry["step"] for entry in entries], dtype=np.float64)
        self._audit = {
            "schema_version": SCHEMA_VERSION,
            "feature_names": list(self.feature_names), "cells": self.cells,
            "training_rows": int(len(array)), "anchor": 0.0,
            "rounding": "nearest_ties_to_even", "nonfinite_policy": "nan",
            "minimum_steps": dict(self.minimum_steps), "features": entries,
        }
        return self

    def transform(self, features: pd.DataFrame | np.ndarray) -> pd.DataFrame | np.ndarray:
        if self.steps_ is None:
            raise RuntimeError("Fit the quantizer before transform")
        array = self._array(features)
        array[~np.isfinite(array)] = np.nan
        for index, step in enumerate(self.steps_):
            column = array[:, index]
            # At 2**52 grid units, the float64 spacing is already >= the step.
            # Leave such representable finite numbers alone to avoid overflow.
            with np.errstate(over="ignore"):
                mask = np.isfinite(column) & (np.abs(column) < step * 2.0**52)
            column[mask] = np.rint(column[mask] / step) * step
            column[column == 0] = 0.0  # Canonical positive zero.
        if isinstance(features, pd.DataFrame):
            return pd.DataFrame(array, index=features.index, columns=self.feature_names)
        return array

    def fit_transform(self, train_features: pd.DataFrame | np.ndarray) -> pd.DataFrame | np.ndarray:
        return self.fit(train_features).transform(train_features)

    def to_dict(self) -> dict[str, Any]:
        if self._audit is None:
            raise RuntimeError("Fit the quantizer before exporting its audit")
        # Return an independent JSON-compatible structure, not internal state.
        import copy
        return copy.deepcopy(self._audit)

    @classmethod
    def from_dict(cls, audit: Mapping[str, Any]) -> ScaleAwareQuantizer:
        """Restore the exact fitted grids without re-fitting any input data."""
        if audit.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported quantizer audit schema")
        instance = cls(audit["feature_names"], cells=audit["cells"],
                       minimum_steps=audit.get("minimum_steps"))
        entries = audit["features"]
        if [entry["name"] for entry in entries] != list(instance.feature_names):
            raise ValueError("Audit feature order differs from declared order")
        steps = np.array([entry["step"] for entry in entries], dtype=np.float64)
        if not np.isfinite(steps).all() or np.any(steps <= 0):
            raise ValueError("Audit quantization steps must be finite and positive")
        if any(_ceil_power_of_two(float(step)) != step for step in steps):
            raise ValueError("Audit quantization steps must be powers of two")
        if (audit.get("anchor") != 0.0 or audit.get("rounding") != "nearest_ties_to_even"
                or audit.get("nonfinite_policy") != "nan"):
            raise ValueError("Unsupported quantizer transformation semantics")
        import copy
        instance._audit = copy.deepcopy(dict(audit))
        instance.steps_ = steps
        return instance
