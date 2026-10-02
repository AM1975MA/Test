#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

START = "2004-01-01"
END_EXCLUSIVE = "2026-08-01"
LAST_REQUIRED = pd.Timestamp("2026-07-31")
PRE2017_CUTOFF = pd.Timestamp("2017-01-31")
MIN_PRE2017_ROWS = 252
QUOTA_PER_CLUSTER = 10


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_v3_candidate_spec(path: Path):
    spec = importlib.util.spec_from_file_location("v3_freezer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen V3 candidate specification")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.CATEGORIES), {k: list(v) for k, v in mod.CANDIDATES.items()}


def load_tickers(path: Path) -> set[str]:
    d = pd.read_csv(path)
    if "ticker" not in d.columns:
        raise RuntimeError(f"reference missing ticker: {path}")
    return set(d.ticker.astype(str).str.upper())


def fetch_one(ticker: str) -> tuple[pd.DataFrame | None, str | None]:
    last_error = None
    for attempt in range(3):
        try:
            d = yf.download(
                ticker,
                start=START,
                end=END_EXCLUSIVE,
                auto_adjust=False,
                actions=False,
                progress=False,
                threads=False,
                timeout=20,
            )
            if d is not None and not d.empty:
                break
            last_error = "empty"
        except Exception as e:
            last_error = f"{type(e).__name__}:{e}"
        time.sleep(1.0 + attempt)
    else:
        return None, f"download_failed:{last_error}"

    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d.reset_index()
    needed = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
    if any(c not in d.columns for c in needed):
        return None, "missing_columns"

    raw_close = pd.to_numeric(d["Close"], errors="coerce")
    adj = pd.to_numeric(d["Adj Close"], errors="coerce")
    factor = adj / raw_close.replace(0, np.nan)
    q = pd.DataFrame({
        "date": pd.to_datetime(d["Date"]),
        "Open": pd.to_numeric(d["Open"], errors="coerce") * factor,
        "High": pd.to_numeric(d["High"], errors="coerce") * factor,
        "Low": pd.to_numeric(d["Low"], errors="coerce") * factor,
        "Close": adj,
        "Volume": pd.to_numeric(d["Volume"], errors="coerce"),
    }).dropna().sort_values("date").drop_duplicates("date", keep="last")

    if q.empty:
        return None, "no_valid_rows"
    if (q[["Open", "High", "Low", "Close"]] <= 0).any().any():
        return None, "nonpositive_ohlc"
    if (q.Volume < 0).any():
        return None, "negative_volume"

    q["High"] = q[["High", "Open", "Close", "Low"]].max(axis=1)
    q["Low"] = q[["Low", "Open", "Close", "High"]].min(axis=1)

    pre = q[q.date <= PRE2017_CUTOFF]
    if len(pre) < MIN_PRE2017_ROWS:
        return None, f"insufficient_pre2017_rows:{len(pre)}"
    if q.date.max() < LAST_REQUIRED:
        return None, f"ends_early:{q.date.max().date()}"
    return q[q.date <= LAST_REQUIRED].copy(), None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v3-freezer", required=True)
    ap.add_argument("--original149", required=True)
    ap.add_argument("--holdout70", required=True)
    ap.add_argument("--eu110", required=True)
    ap.add_argument("--dev72", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    categories, candidates = load_v3_candidate_spec(Path(args.v3_freezer))
    original = load_tickers(Path(args.original149))
    holdout = load_tickers(Path(args.holdout70))
    eu110 = load_tickers(Path(args.eu110))
    dev72 = load_tickers(Path(args.dev72))

    if len(original) != 149 or len(holdout) != 70 or len(eu110) != 110 or len(dev72) != 72:
        raise RuntimeError(
            f"reference sizes unexpected: original={len(original)} holdout={len(holdout)} eu110={len(eu110)} dev72={len(dev72)}"
        )
    burned = original | holdout | eu110 | dev72
    if len(burned) != 400:
        raise RuntimeError(f"expected 400 unique burned/tested tickers, got {len(burned)}")

    flat = [t for c in categories for t in candidates[c]]
    if len(flat) != len(set(flat)):
        raise RuntimeError("frozen V3 candidate order contains duplicate tickers")

    out = Path(args.out)
    raw = out / "raw_ticker_csv"
    raw.mkdir(parents=True, exist_ok=True)
    selected, rejected, data = [], [], {}

    for cat in categories:
        n = 0
        for ticker in candidates[cat]:
            if ticker.upper() in burned:
                rejected.append({"ticker": ticker, "macro_category": cat, "reason": "burned_set_overlap"})
                continue
            q, reason = fetch_one(ticker)
            if q is None:
                rejected.append({"ticker": ticker, "macro_category": cat, "reason": reason})
                print("REJECT", cat, ticker, reason, flush=True)
                continue
            selected.append({
                "ticker": ticker,
                "macro_category": cat,
                "rows": int(len(q)),
                "first": str(q.date.min().date()),
                "last": str(q.date.max().date()),
                "pre2017_rows": int((q.date <= PRE2017_CUTOFF).sum()),
            })
            data[ticker] = q
            n += 1
            print("SELECT", cat, ticker, n, "/", QUOTA_PER_CLUSTER, flush=True)
            if n == QUOTA_PER_CLUSTER:
                break
        if n != QUOTA_PER_CLUSTER:
            raise RuntimeError(f"quota not met for {cat}: {n}/{QUOTA_PER_CLUSTER}")

    tickers = [x["ticker"] for x in selected]
    if len(tickers) != 60 or len(set(tickers)) != 60:
        raise RuntimeError(f"Dev60 selection invalid: total={len(tickers)} unique={len(set(tickers))}")
    overlap = sorted(set(t.upper() for t in tickers) & burned)
    if overlap:
        raise RuntimeError(f"Dev60 overlaps burned/tested universe: {overlap}")

    hashes = {}
    for rec in selected:
        t = rec["ticker"]
        q = data[t].copy()
        q["date"] = q.date.dt.strftime("%Y-%m-%d")
        fp = raw / f"{t}.csv"
        q.to_csv(fp, index=False, float_format="%.17g")
        hashes[t] = sha256(fp)

    u = pd.DataFrame(selected)[["ticker", "macro_category"]]
    u.to_csv(out / "universe.csv", index=False)
    pd.DataFrame(selected).to_csv(out / "coverage.csv", index=False)
    pd.DataFrame(rejected).to_csv(out / "rejected.csv", index=False)

    candidate_payload = json.dumps(
        {"categories": categories, "candidates": candidates}, sort_keys=True
    ).encode()
    manifest = {
        "status": "EVIDENCE_V4_DEV60_FROZEN",
        "provider": "Yahoo Finance via yfinance",
        "selection_rule": "first coverage-valid non-burned ticker in exact pre-V3 frozen candidate order; no performance criterion",
        "requested_start": START,
        "last_included": str(LAST_REQUIRED.date()),
        "pre2017_cutoff": str(PRE2017_CUTOFF.date()),
        "minimum_pre2017_rows": MIN_PRE2017_ROWS,
        "selected_count": 60,
        "per_cluster": QUOTA_PER_CLUSTER,
        "burned_reference_counts": {
            "original149": len(original), "holdout70": len(holdout),
            "eu110_tested": len(eu110), "dev72": len(dev72), "union": len(burned),
        },
        "intersection_with_burned_union": overlap,
        "performance_used_for_selection": False,
        "v3_candidate_order_sha256": hashlib.sha256(candidate_payload).hexdigest(),
        "selected": selected,
        "file_sha256": hashes,
        "universe_sha256": sha256(out / "universe.csv"),
        "coverage_sha256": sha256(out / "coverage.csv"),
        "rejected_sha256": sha256(out / "rejected.csv"),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k not in ("selected", "file_sha256")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
