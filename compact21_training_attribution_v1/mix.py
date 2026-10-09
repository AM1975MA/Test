"""Exact-key training source factorization. Never use mixed data as a deployable model."""
from __future__ import annotations

import pandas as pd

KEYS = ("signal_date", "ticker")
LABELS = ("target_rank_21", "exit_date_21")


def assert_common_training_keys(frames):
    if set(frames) != {1, 2, 3}:
        raise ValueError("Need exactly three frozen training vintages")
    baseline = None
    for vintage in (1, 2, 3):
        frame = frames[vintage]
        if not isinstance(frame, pd.DataFrame) or frame.empty or any(k not in frame for k in KEYS):
            raise ValueError("Invalid/missing training keys")
        if frame[list(KEYS)].isna().any().any() or frame.duplicated(list(KEYS)).any():
            raise ValueError("Null or duplicate training keys")
        key = frame[list(KEYS)].reset_index(drop=True)
        if baseline is None:
            baseline = key
        elif not key.equals(baseline):
            raise ValueError("Training row support/order differs; do not align silently")
    return True


def mixed_training(own, repeat2, *, feature_cols, feature_source, label_source):
    if feature_source not in ("own", "repeat2") or label_source not in ("own", "repeat2"):
        raise ValueError("Unregistered mix treatment")
    if own.empty or repeat2.empty:
        raise ValueError("Empty training vintage")
    if own.duplicated(list(KEYS)).any() or repeat2.duplicated(list(KEYS)).any():
        raise ValueError("Duplicate keys")
    if own[list(KEYS)].isna().any().any() or repeat2[list(KEYS)].isna().any().any():
        raise ValueError("Missing keys")
    if not own[list(KEYS)].reset_index(drop=True).equals(repeat2[list(KEYS)].reset_index(drop=True)):
        raise ValueError("Training cohorts not exactly aligned")
    cols = list(feature_cols)
    if len(cols) != len(set(cols)) or not cols:
        raise ValueError("Invalid feature schema")
    required = set(cols) | set(KEYS) | set(LABELS)
    if not required.issubset(own.columns) or not required.issubset(repeat2.columns):
        raise ValueError("Required original feature/label columns missing")
    if ("fwd_ret_21" in own) != ("fwd_ret_21" in repeat2):
        raise ValueError("Inconsistent optional original forward outcome schema")
    label_cols = list(LABELS) + (["fwd_ret_21"] if "fwd_ret_21" in own else [])
    out = own.copy(deep=True).reset_index(drop=True)
    xsource = own if feature_source == "own" else repeat2
    ysource = own if label_source == "own" else repeat2
    out.loc[:, cols] = xsource[cols].to_numpy(copy=True)
    out.loc[:, label_cols] = ysource[label_cols].to_numpy(copy=True)
    # Reject accidental key movement or side effects to non-factorial fields.
    pd.testing.assert_frame_equal(out[list(KEYS)], own[list(KEYS)].reset_index(drop=True), check_exact=True)
    frozen = [x for x in own.columns if x not in cols and x not in label_cols]
    pd.testing.assert_frame_equal(out[frozen], own.reset_index(drop=True)[frozen], check_exact=True)
    if not out[label_cols[:2]].notna().all().all():
        raise ValueError("Treatment introduced immature/missing label")
    return out
