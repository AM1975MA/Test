"""Strict prior-calendar-day Cboe features; no fitting or return simulation."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd


SOURCE_NAMES = ("VIX9D", "VIX", "VIX3M")
MAX_SOURCE_AGE_DAYS = 7
VIX_CHANGE_SOURCE_SESSIONS = 21
SOURCE_URL_BASE = "https://cdn.cboe.com/api/global/us_indices/daily_prices/"


def _read_source(raw_dir, symbol):
    path = Path(raw_dir) / f"{symbol}_History.csv"
    raw = path.read_bytes()
    frame = pd.read_csv(BytesIO(raw))
    if not {"DATE", "CLOSE"}.issubset(frame.columns):
        raise ValueError(f"{path.name} requires DATE and CLOSE columns")
    parsed = pd.to_datetime(frame["DATE"], format="%m/%d/%Y", errors="coerce")
    if parsed.isna().any():
        raise ValueError(f"{path.name} contains an invalid source date")
    dates = parsed.to_numpy(dtype="datetime64[D]")
    if len(dates) > 1 and np.any(dates[1:] <= dates[:-1]):
        raise ValueError(f"{path.name} source dates must be unique and sorted")
    # Keep invalid closes in their original session slots: never fallback or
    # redefine a 21-source-session lag by dropping an invalid observation.
    close = pd.to_numeric(frame["CLOSE"], errors="coerce").to_numpy(dtype=float)
    metadata = {"symbol": symbol, "file": path.name,
                "url": SOURCE_URL_BASE + path.name,
                "sha256": sha256(raw).hexdigest(), "bytes": len(raw),
                "rows": len(dates)}
    return dates, close, metadata


def load_cboe_features(raw_dir, decision_dates):
    """Return causal, unscaled Cboe features for European decision dates.

    ``dates`` has dtype datetime64[D] and retains input order. Source columns
    are VIX9D, VIX, VIX3M. Each latest source date must be strictly earlier
    than the decision calendar date, equal across the three indices, and
    at most seven calendar days old. All current closes and the VIX close
    21 source sessions earlier must be finite and positive. The common
    ``available`` mask gates both two-column feature arrays; invalid rows
    contain NaN. Source dates/ages remain populated for diagnosis.

    ``term`` columns are log(VIX9D/VIX), log(VIX/VIX3M). ``legacy`` columns
    are log(VIX), log(VIX/VIX_21_source_sessions_ago). Metadata hashes are
    computed from raw bytes independently of all feature calculations.
    Dates must be timezone-naive; intraday times are normalized to the same
    calendar date. Duplicate/unsorted/invalid source dates raise ValueError.
    """
    decisions = pd.DatetimeIndex(decision_dates)
    if decisions.tz is not None or decisions.hasnans:
        raise ValueError("Decision dates must be valid, timezone-naive calendar dates")
    dates = decisions.to_numpy(dtype="datetime64[D]")
    n = len(dates)
    source_dates = np.full((n, 3), np.datetime64("NaT", "D"))
    source_age_days = np.full((n, 3), np.nan)
    closes = np.full((n, 3), np.nan)
    lagged_vix = np.full(n, np.nan)
    available = np.ones(n, dtype=bool)
    sources = []

    for column, symbol in enumerate(SOURCE_NAMES):
        observed_dates, observed_close, metadata = _read_source(raw_dir, symbol)
        sources.append(metadata)
        index = np.searchsorted(observed_dates, dates, side="left") - 1
        found = index >= 0
        source_dates[found, column] = observed_dates[index[found]]
        closes[found, column] = observed_close[index[found]]
        source_age_days[found, column] = (
            dates[found] - source_dates[found, column]
        ).astype("timedelta64[D]").astype(float)
        available &= (found & np.isfinite(closes[:, column]) &
                      (closes[:, column] > 0) &
                      (source_age_days[:, column] >= 1) &
                      (source_age_days[:, column] <= MAX_SOURCE_AGE_DAYS))
        if symbol == "VIX":
            mature = index >= VIX_CHANGE_SOURCE_SESSIONS
            lagged_vix[mature] = observed_close[index[mature] - VIX_CHANGE_SOURCE_SESSIONS]
            available &= mature & np.isfinite(lagged_vix) & (lagged_vix > 0)

    # Independent as-of lookup, then a common-date requirement. Do not
    # silently backdate an index to force a matching term structure.
    available &= np.all(source_dates == source_dates[:, :1], axis=1)
    term = np.full((n, 2), np.nan)
    legacy = np.full((n, 2), np.nan)
    log_close = np.log(closes[available])
    term[available, 0] = log_close[:, 0] - log_close[:, 1]
    term[available, 1] = log_close[:, 1] - log_close[:, 2]
    legacy[available, 0] = log_close[:, 1]
    legacy[available, 1] = log_close[:, 1] - np.log(lagged_vix[available])
    return {"dates": dates, "available": available,
            "source_dates": source_dates, "source_age_days": source_age_days,
            "term": term, "legacy": legacy,
            "metadata": {"sources": sources, "source_order": list(SOURCE_NAMES),
                         "term_names": ["log_vix9d_over_vix", "log_vix_over_vix3m"],
                         "legacy_names": ["log_vix", "vix_log_change_21_source_sessions"],
                         "max_source_age_calendar_days": MAX_SOURCE_AGE_DAYS,
                         "vix_change_source_sessions": VIX_CHANGE_SOURCE_SESSIONS,
                         "alignment": "latest_source_date_strictly_before_decision_date",
                         "same_source_date_required": True}}
