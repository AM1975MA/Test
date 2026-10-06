#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
import yfinance as yf


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--start", default="2004-01-01")
    ap.add_argument("--end", default="2026-08-01", help="yfinance exclusive end date")
    args = ap.parse_args()

    universe = pd.read_csv(args.universe)[["ticker", "macro_category"]].copy()
    universe["ticker"] = universe.ticker.astype(str).str.upper()
    universe = universe.drop_duplicates("ticker").reset_index(drop=True)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    universe.to_csv(out / "universe.csv", index=False)

    hashes = {}
    coverage = []
    for i, row in enumerate(universe.itertuples(index=False), 1):
        t = row.ticker
        d = yf.download(
            t,
            start=args.start,
            end=args.end,
            auto_adjust=False,
            actions=False,
            progress=False,
            threads=False,
        )
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d = d.reset_index()
        date_col = "Date" if "Date" in d.columns else "Datetime"
        need = [date_col, "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        if d.empty or any(c not in d.columns for c in need):
            raise RuntimeError(f"{t}: incomplete Yahoo response")
        factor = d["Adj Close"] / d["Close"]
        q = pd.DataFrame({
            "date": pd.to_datetime(d[date_col]).dt.tz_localize(None).dt.strftime("%Y-%m-%d"),
            "Open": d["Open"] * factor,
            "High": d["High"] * factor,
            "Low": d["Low"] * factor,
            "Close": d["Adj Close"],
            "Volume": d["Volume"],
        }).dropna()
        if q.date.duplicated().any():
            raise RuntimeError(f"{t}: duplicate dates")
        if (q[["Open", "High", "Low", "Close"]] <= 0).any().any() or (q.Volume < 0).any():
            raise RuntimeError(f"{t}: invalid OHLCV")
        p = out / f"{t}.csv"
        q.to_csv(p, index=False, float_format="%.17g")
        hashes[t] = sha256(p)
        coverage.append({
            "ticker": t,
            "macro_category": row.macro_category,
            "rows": int(len(q)),
            "first": q.date.iloc[0],
            "last": q.date.iloc[-1],
            "pre2017_rows": int((pd.to_datetime(q.date) < pd.Timestamp("2017-01-01")).sum()),
        })
        print(i, len(universe), t, len(q), q.date.iloc[0], q.date.iloc[-1], flush=True)

    pd.DataFrame(coverage).to_csv(out / "coverage.csv", index=False)
    manifest = {
        "status": "UNIFORM_YAHOO_REPEATED_VINTAGE_TEST",
        "provider": "Yahoo Finance via yfinance",
        "requested_start": args.start,
        "requested_end_exclusive": args.end,
        "price_semantics": "same-row Adj Close/raw Close adjustment for OHLC; raw Volume",
        "tickers": int(len(universe)),
        "file_sha256": hashes,
        "package_versions": {
            "yfinance": getattr(yf, "__version__", "unknown"),
            "pandas": pd.__version__,
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
