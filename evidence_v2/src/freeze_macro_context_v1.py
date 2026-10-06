#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

START = pd.Timestamp("2005-01-01")
END = pd.Timestamp("2026-06-30")
SERIES = {
    "VIXCLS": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS&cosd=2005-01-01&coed=2026-06-30",
    "DGS2": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2&cosd=2005-01-01&coed=2026-06-30",
    "DGS10": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=2005-01-01&coed=2026-06-30",
    "BAA10Y": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAA10Y&cosd=2005-01-01&coed=2026-06-30",
    "DTWEXBGS": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS&cosd=2005-01-01&coed=2026-06-30",
}
FEATURES = [
    "vix_z252",
    "dgs2_delta21",
    "dgs10_delta21",
    "curve_10y2y_z252",
    "baa10y_z252",
    "usd_ret21",
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def zscore(s: pd.Series, window: int = 252, minp: int = 126) -> pd.Series:
    mu = s.rolling(window, min_periods=minp).mean()
    sd = s.rolling(window, min_periods=minp).std(ddof=0)
    return (s - mu) / sd.replace(0, np.nan)


def fetch(url: str) -> bytes:
    last: Exception | None = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "EvidenceV2/1.0",
                    "Accept": "text/csv,*/*;q=0.8",
                    "Connection": "close",
                },
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if len(data) < 100:
                raise RuntimeError(f"unexpectedly short FRED response: {len(data)} bytes")
            return data
        except Exception as exc:
            last = exc
            if attempt == 4:
                break
            time.sleep(2 ** attempt)
    raise RuntimeError(f"FRED download failed after retries for {url}: {last!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    rawdir = out / "raw"
    rawdir.mkdir(parents=True, exist_ok=True)

    raw_hashes: dict[str, str] = {}
    frames = []
    source_meta = {}
    for sid, url in SERIES.items():
        data = fetch(url)
        raw = rawdir / f"{sid}.csv"
        raw.write_bytes(data)
        raw_hashes[sid] = sha256_bytes(data)
        x = pd.read_csv(io.BytesIO(data))
        date_col = "DATE" if "DATE" in x.columns else x.columns[0]
        if sid not in x.columns:
            value_cols = [c for c in x.columns if c != date_col]
            if len(value_cols) != 1:
                raise RuntimeError(f"{sid}: unexpected FRED columns {list(x.columns)}")
            x = x.rename(columns={value_cols[0]: sid})
        x[date_col] = pd.to_datetime(x[date_col], errors="coerce")
        x[sid] = pd.to_numeric(x[sid], errors="coerce")
        x = x.dropna(subset=[date_col]).set_index(date_col)[[sid]].sort_index()
        x = x[(x.index >= START) & (x.index <= END)]
        if x.empty:
            raise RuntimeError(f"{sid}: no observations in freeze range")
        source_meta[sid] = {
            "url": url,
            "raw_sha256": raw_hashes[sid],
            "first_observation": str(x.index.min().date()),
            "last_observation": str(x.dropna().index.max().date()),
            "non_null": int(x[sid].notna().sum()),
        }
        frames.append(x)

    idx = pd.bdate_range(START, END)
    raw = pd.concat(frames, axis=1).reindex(idx).ffill(limit=5)
    raw.index.name = "date"

    curve = raw["DGS10"] - raw["DGS2"]
    feat = pd.DataFrame(index=raw.index)
    feat["vix_z252"] = zscore(np.log(raw["VIXCLS"].where(raw["VIXCLS"] > 0)))
    feat["dgs2_delta21"] = raw["DGS2"] - raw["DGS2"].shift(21)
    feat["dgs10_delta21"] = raw["DGS10"] - raw["DGS10"].shift(21)
    feat["curve_10y2y_z252"] = zscore(curve)
    feat["baa10y_z252"] = zscore(raw["BAA10Y"])
    feat["usd_ret21"] = np.log(raw["DTWEXBGS"] / raw["DTWEXBGS"].shift(21))

    daily = pd.concat([raw, feat], axis=1)
    if daily.index.max() > END:
        raise RuntimeError("freeze contains observations after 2026-06-30")
    quality_start = pd.Timestamp("2007-01-01")
    q = daily.loc[quality_start:, FEATURES].notna().mean()
    if (q < 0.97).any():
        raise RuntimeError(f"macro feature coverage below 97%: {q.to_dict()}")
    for c in FEATURES:
        if not np.isfinite(daily[c].dropna().to_numpy(float)).all():
            raise RuntimeError(f"non-finite values in {c}")

    daily_path = out / "MACRO_DAILY.csv"
    daily.reset_index().to_csv(daily_path, index=False)
    manifest = {
        "dataset": "evidence_v2_macro_context_v1",
        "status": "FROZEN",
        "freeze_range": {"start": str(START.date()), "end": str(END.date())},
        "source": "FRED market series; downloaded once and frozen before model test",
        "point_in_time_note": "FRED current historical market series are frozen as retrieved; no later network fetch is permitted in the model test. These market series are expected to have low revision risk, but this is not an ALFRED vintage reconstruction.",
        "series": source_meta,
        "features": FEATURES,
        "transformations": {
            "vix_z252": "rolling 252-business-day z-score of log(VIXCLS), min 126",
            "dgs2_delta21": "DGS2 minus 21-business-day lag",
            "dgs10_delta21": "DGS10 minus 21-business-day lag",
            "curve_10y2y_z252": "rolling 252-business-day z-score of DGS10-DGS2, min 126",
            "baa10y_z252": "rolling 252-business-day z-score of BAA10Y, min 126",
            "usd_ret21": "log(DTWEXBGS / 21-business-day lag)",
        },
        "alignment_rule_for_tests": "as-of join using only macro date strictly less than signal_date",
        "coverage_from_2007": {k: float(v) for k, v in q.items()},
        "files_sha256": {
            "MACRO_DAILY.csv": sha256_file(daily_path),
            **{f"raw/{sid}.csv": sha256_file(rawdir / f"{sid}.csv") for sid in SERIES},
        },
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
