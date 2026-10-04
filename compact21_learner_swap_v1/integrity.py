"""Exact table evidence independent of pandas pickle/block serialization.

NaN payload bits are normalized via a separately hashed missing mask. Signed
zero is preserved. All nonmissing float bits (including infinities and each
ULP) remain material. No rounding/tolerance enters the acceptance gate.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEMANTIC_CONTRACT = {
    "version": 1, "row_and_column_order": "exact", "index": "exact values, type, names, dtype",
    "dtype": "exact including nullable and categorical metadata",
    "missing": "mask exact; NaN payload bits normalized, NaT/NA normalized within dtype",
    "negative_zero": "preserve sign bit", "finite_values": "exact; no rounding or tolerance",
    "infinity": "preserve sign and distinguish from missing",
    "pickle_layout": "ignored; dataframe logical schema and values only",
}


def file_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _scalar(value):
    if value is None or value is pd.NA or value is pd.NaT:
        return ["missing"]
    if isinstance(value, (np.floating, float)):
        if np.isnan(value):
            return ["missing"]
        return ["float", np.float64(value).tobytes().hex()]
    if isinstance(value, (np.bool_, bool)):
        return ["bool", bool(value)]
    if isinstance(value, (np.integer, int)):
        return ["int", str(int(value))]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, bytes):
        return ["bytes", value.hex()]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        value = pd.Timestamp(value)
        return ["timestamp", str(value.value), str(value.tz)]
    if isinstance(value, (pd.Timedelta, np.timedelta64)):
        return ["timedelta_ns", str(pd.Timedelta(value).value)]
    if isinstance(value, tuple):
        return ["tuple", [_scalar(v) for v in value]]
    raise TypeError(f"unsupported semantic scalar type: {type(value).__name__}")


def _dtype_info(dtype) -> dict:
    result = {"name": str(dtype), "type": type(dtype).__name__}
    if isinstance(dtype, pd.CategoricalDtype):
        result.update(ordered=bool(dtype.ordered), categories=[_scalar(x) for x in dtype.categories],
                      categories_dtype=str(dtype.categories.dtype))
    if isinstance(dtype, pd.StringDtype):
        result["storage"] = dtype.storage
    return result


def _series_fingerprint(series: pd.Series) -> dict:
    mask = series.isna().to_numpy(dtype=np.bool_)
    missing_hash = hashlib.sha256(mask.tobytes()).hexdigest()
    dtype = series.dtype
    native = getattr(dtype, "numpy_dtype", dtype)
    try:
        native = np.dtype(native)
    except TypeError:
        native = None
    if native is not None and native.kind in "biufcMm":
        # Nulls are replaced only after their exact mask has been recorded.
        fill = np.datetime64("1970-01-01") if native.kind == "M" else np.timedelta64(0, "ns") if native.kind == "m" else 0
        array = series.to_numpy(dtype=native, na_value=fill).copy()
        array[mask] = fill
        array = np.ascontiguousarray(array.astype(native.newbyteorder("<"), copy=False))
        payload = array.tobytes()
    elif isinstance(dtype, pd.DatetimeTZDtype):
        array = np.asarray(series.array.asi8, dtype="<i8").copy()
        array[mask] = 0
        payload = array.tobytes()
    else:
        h = hashlib.sha256()
        for missing, value in zip(mask, series.array):
            token = _json(["missing"] if missing else _scalar(value))
            h.update(len(token).to_bytes(8, "little"))
            h.update(token)
        payload = None
    return {"dtype": _dtype_info(dtype), "missing_count": int(mask.sum()),
            "missing_sha256": missing_hash,
            "values_sha256": hashlib.sha256(payload).hexdigest() if payload is not None else h.hexdigest()}


def _index_fingerprint(index: pd.Index) -> dict:
    metadata = {"type": type(index).__name__, "names": [_scalar(v) for v in index.names],
                "length": len(index)}
    if isinstance(index, pd.MultiIndex):
        metadata["levels"] = [_series_fingerprint(pd.Series(index.get_level_values(i)))
                              for i in range(index.nlevels)]
    else:
        metadata["values"] = _series_fingerprint(pd.Series(index))
    if isinstance(index, pd.RangeIndex):
        metadata["range"] = [index.start, index.stop, index.step]
    return metadata


def dataframe_fingerprint(frame: pd.DataFrame) -> dict:
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("expected DataFrame")
    if not frame.columns.is_unique:
        raise ValueError("duplicate column names cannot be audited")
    evidence = {"semantic_contract": SEMANTIC_CONTRACT, "shape": list(frame.shape),
                "columns": _index_fingerprint(frame.columns), "index": _index_fingerprint(frame.index),
                "column_values": [{"column": _scalar(column), **_series_fingerprint(frame[column])}
                                  for column in frame.columns]}
    evidence["sha256"] = hashlib.sha256(_json(evidence)).hexdigest()
    return evidence


def compare_panels(reference_panel: pd.DataFrame, own_panel: pd.DataFrame) -> dict:
    reference, own = dataframe_fingerprint(reference_panel), dataframe_fingerprint(own_panel)
    schema_equal = (reference["shape"] == own["shape"] and reference["columns"] == own["columns"]
                    and [c["dtype"] for c in reference["column_values"]] == [c["dtype"] for c in own["column_values"]])
    index_equal = reference["index"] == own["index"]
    keys = [key for key in ("signal_date", "ticker") if key in reference_panel and key in own_panel]
    key_equal = schema_equal and all(_series_fingerprint(reference_panel[k]) == _series_fingerprint(own_panel[k]) for k in keys)
    differences, max_abs = [], 0.0
    if reference["columns"] == own["columns"]:
        for left, right in zip(reference["column_values"], own["column_values"]):
            if left != right:
                differences.append(left["column"])
        if reference_panel.shape == own_panel.shape:
            for col in reference_panel:
                if pd.api.types.is_numeric_dtype(reference_panel[col]) and pd.api.types.is_numeric_dtype(own_panel[col]):
                    a = reference_panel[col].to_numpy(dtype=float, na_value=np.nan)
                    b = own_panel[col].to_numpy(dtype=float, na_value=np.nan)
                    finite = np.isfinite(a) & np.isfinite(b)
                    if finite.any():
                        max_abs = max(max_abs, float(np.max(np.abs(a[finite] - b[finite]))))
    return {"exact_equal": reference["sha256"] == own["sha256"],
            "schema_equal": bool(schema_equal), "key_equal": bool(key_equal), "index_equal": bool(index_equal),
            "reference_sha256": reference["sha256"], "own_sha256": own["sha256"],
            "mismatched_columns": differences, "max_abs_diff": max_abs,
            "diagnostic_tolerance_used_for_gate": False, "semantic_contract": SEMANTIC_CONTRACT}


def write_ma3_evidence(panel_dir: Path) -> dict:
    panel_dir = Path(panel_dir)
    panel_path = panel_dir / "RAW_FEATURE_PANEL.pkl"
    cluster_path = panel_dir / "DYNAMIC_CLUSTER_MEMBERSHIP.csv"
    # CSV parsing is declared identical in reference and replay; original CSV
    # bytes are retained too. Panel dtypes/values are taken directly from pickle.
    evidence = {"panel": dataframe_fingerprint(pd.read_pickle(panel_path)),
                "clusters": dataframe_fingerprint(pd.read_csv(cluster_path)),
                "file_sha256": {p.name: file_hash(p) for p in sorted(panel_dir.iterdir())
                                if p.is_file() and p.name != "SEMANTIC_FINGERPRINT.json"}}
    (panel_dir / "SEMANTIC_FINGERPRINT.json").write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n")
    return evidence
