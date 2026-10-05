"""Portable Compact21-only semideviation view; no learner or cohort selection."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder

KEYS = ["signal_date", "ticker"]
CHANGED = [f"downvol{h}{suffix}" for h in (21, 63, 126) for suffix in ("", "_pct", "_dev")]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def column_hash(series):
    a = series.to_numpy()
    h = hashlib.sha256(str(series.dtype).encode())
    h.update(str(a.shape).encode())
    h.update(pd.util.hash_pandas_object(series, index=False).to_numpy().tobytes()
             if a.dtype.hasobject else np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def semideviation(log_returns, horizon):
    if horizon not in (21, 63, 126):
        raise ValueError("Unregistered horizon")
    finite = log_returns.where(np.isfinite(log_returns))
    moment = finite.clip(upper=0).pow(2).rolling(
        horizon, min_periods=max(10, horizon // 2)).mean()
    return np.sqrt(moment) * np.sqrt(252)


def build_family(close):
    if not close.index.is_monotonic_increasing or not close.index.is_unique or close.columns.duplicated().any():
        raise ValueError("Invalid source calendar/population")
    if np.isinf(close.to_numpy()).any() or (close <= 0).any().any():
        raise ValueError("Invalid source prices")
    lr = np.log(close.where(close > 0)).diff()
    dates = k.month_end_dates(close.index)
    result = {}
    for horizon in (21, 63, 126):
        base = semideviation(lr, horizon).reindex(dates)
        result[f"downvol{horizon}"] = base
        result[f"downvol{horizon}_pct"] = k.cs_pct(base)
        result[f"downvol{horizon}_dev"] = k.cs_robust_dev(base)
    return result


def align_view(original, close):
    if original.empty or original[KEYS].isna().any().any() or original.duplicated(KEYS).any():
        raise ValueError("Invalid original keys")
    if set(original.ticker) != set(close.columns):
        raise ValueError("TI and raw normalization universe differ")
    if any(feature not in original for feature in k.F2D_FEATURES):
        raise ValueError("Missing canonical feature columns")
    matrices = build_family(close)
    row = matrices[CHANGED[0]].index.get_indexer(pd.to_datetime(original.signal_date))
    col = close.columns.get_indexer(original.ticker)
    if (row < 0).any() or (col < 0).any():
        raise ValueError("Unresolved original keys/calendar")
    view = original.copy(deep=True)
    for feature in CHANGED:
        view[feature] = matrices[feature].to_numpy()[row, col].astype(original[feature].dtype, copy=False)
    preserved = [c for c in original if c not in CHANGED]
    hashes = {}
    for c in preserved:
        pd.testing.assert_series_equal(original[c], view[c], check_exact=True)
        hashes[c] = column_hash(original[c])
        if hashes[c] != column_hash(view[c]):
            raise ValueError("Changed original numeric bits")
    original_valid = original[k.F2D_FEATURES].notna().sum(axis=1).ge(30)
    new_valid = view[k.F2D_FEATURES].notna().sum(axis=1).ge(30)
    audit = {"changed_columns": list(CHANGED), "unchanged_columns_exact": True,
             "preserved_column_sha256": hashes, "preserved_features": 116,
             "population": sorted(close.columns.tolist()), "population_equal_to_original_ti": True,
             "population_count": len(close.columns),
             "normalization": "canonical149_full_date_before_original_eligibility",
             "would_change_original_eligibility_rows": int((original_valid != new_valid).sum()),
             "cohort_selection": "original_TI_only_never_new_view"}
    return view, audit


def original_reconstruction_audit(original, close):
    """Verify original nine downside fields BEFORE constructing the intervention."""
    lr = np.log(close.where(close > 0)).diff()
    dates = k.month_end_dates(close.index)
    row = dates.get_indexer(pd.to_datetime(original.signal_date))
    col = close.columns.get_indexer(original.ticker)
    if (row < 0).any() or (col < 0).any():
        raise ValueError("Original reconstruction keys unresolved")
    checks = {}
    for h in (21, 63, 126):
        base = k.rolling_downvol(lr, h).reindex(dates)
        for suffix, values in (("", base), ("_pct", k.cs_pct(base)), ("_dev", k.cs_robust_dev(base))):
            name = f"downvol{h}{suffix}"
            actual = values.to_numpy()[row, col]
            expected = original[name].to_numpy(float)
            if np.isinf(actual).any() or np.isinf(expected).any() or not np.array_equal(np.isnan(actual), np.isnan(expected)):
                raise ValueError(f"Original downside missingness reconstruction differs {name}")
            finite = np.isfinite(actual) & np.isfinite(expected)
            maximum = float(np.abs(actual[finite]-expected[finite]).max()) if finite.any() else 0.0
            tolerance = 0.0 if suffix == "_pct" else 1e-10 if suffix == "_dev" else 1e-12
            if maximum > tolerance or (suffix == "_pct" and actual[finite].tobytes() != expected[finite].tobytes()):
                raise ValueError(f"Original downside finite reconstruction differs {name}: {maximum}")
            checks[name] = {"missing_mask_exact": True, "max_abs_finite_difference": maximum,
                            "finite_rows": int(finite.sum()), "absolute_tolerance": tolerance,
                            "finite_values_bit_exact_claimed": suffix == "_pct"}
    return {"PASS": True, "checks": checks, "definition": "canonical_conditional_negative_std_ddof0"}


def from_frozen_raw(original, raw_directory, contract_path):
    contract = json.loads(Path(contract_path).read_text())
    expected = contract.get("raw_files_sha256")
    if not expected or len(expected) != 151:
        raise ValueError("Missing or incomplete original149 raw contract")
    actual_names = {p.name for p in Path(raw_directory).glob("*.csv")}
    if actual_names != set(expected):
        raise ValueError("Raw CSV membership differs from retained contract")
    for name, digest in expected.items():
        if sha(Path(raw_directory) / name) != digest:
            raise ValueError(f"Frozen raw hash mismatch {name}")
    mats, _, _ = load_ticker_csv_folder(raw_directory)
    if len(mats["Close"].columns) != 149:
        raise ValueError("Unexpected source normalization population")
    if set(original.ticker) != set(mats["Close"].columns):
        raise ValueError("Original TI/raw population mismatch")
    reconstruction = original_reconstruction_audit(original, mats["Close"])
    view, audit = align_view(original, mats["Close"])
    audit.update(raw_hashes_PASS=True, raw_files_verified=len(expected),
                 raw_contract_sha256=sha(contract_path), raw_file_sha256=dict(expected),
                 original_downvol_reconstruction=reconstruction)
    return view, audit


def transfer_rows(original_rows, view):
    """Transfer only registered columns into already selected/sorted original rows."""
    if original_rows.empty or original_rows.duplicated(KEYS).any() or view.duplicated(KEYS).any():
        raise ValueError("Empty or duplicate transfer keys")
    donor = view.set_index(KEYS)
    keys = pd.MultiIndex.from_frame(original_rows[KEYS])
    positions = donor.index.get_indexer(keys)
    if (positions < 0).any():
        raise ValueError("Missing view donor keys")
    out = original_rows.copy(deep=True)
    for feature in CHANGED:
        out[feature] = donor.iloc[positions][feature].to_numpy()
    for col in original_rows.columns:
        if col not in CHANGED:
            pd.testing.assert_series_equal(original_rows[col], out[col], check_exact=True)
            if column_hash(original_rows[col]) != column_hash(out[col]):
                raise ValueError("Unchanged transfer column altered")
    return out
