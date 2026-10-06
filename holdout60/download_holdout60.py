#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

START = "2004-01-01"
END_EXCLUSIVE = "2026-08-01"  # includes 2026-07-31
PRE2017_CUTOFF = pd.Timestamp("2017-01-31")
LAST_REQUIRED = pd.Timestamp("2026-07-31")

# Intentionally stricter than the EU120 test: ~5 trading years of history
# before evaluation so 252d features and 63d labels still leave a meaningful
# pre-2017 training sample.
MIN_PRE2017_ROWS = 1260
MAX_ABS_ADJ_DAILY_RETURN = 0.25

QUOTAS = {
    "C01_US_BROAD_STYLE": 10,
    "C02_US_SECTOR_THEME": 10,
    "C03_DEVELOPED_GLOBAL": 10,
    "C04_EMERGING": 10,
    "C05_BONDS_CASH_CREDIT": 10,
    "C06_REAL_ASSETS": 10,
}

# Frozen before any holdout performance is calculated. Order is the deterministic
# fallback order. Selection depends ONLY on data existence, history, and coherence.
# This pool is disjoint from the canonical 149 ETF universe.
CANDIDATES = {
    "C01_US_BROAD_STYLE": [
        "VOO","VIG","VYM","SCHG","IUSG","IUSV","USMV","SPHQ","NOBL","SDY",
        "PRF","RWL","VV","MGK","VOE","VOT","VBK","VBR","IJS","IJK","SLYV",
        "SLYG","SCHV","SCHM","SPYG","SPYV","VIOO","VIOV","VIOG","FNDA","QVAL"
    ],
    "C02_US_SECTOR_THEME": [
        "VGT","VFH","VHT","VDC","VCR","VPU","VAW","VOX","XOP","XME","XHB",
        "XSD","KIE","PSI","PBW","QCLN","SKYY","ROBO","CIBR","XAR","PTH","PJP","PBE"
    ],
    "C03_DEVELOPED_GLOBAL": [
        "VPL","SCHF","SPDW","EFV","EFG","SCZ","HEDJ","DXJ","DBEF","EFAV","IDLV",
        "DTH","PID","DWX","IQDF","FNDF","GWX","VSS","SCHC","IDMO"
    ],
    "C04_EMERGING": [
        "FM","EEMS","EWX","EELV","PIE","PXH","FNDE","XSOE","SPEM","EEB","BKF",
        "ILF","EWW","ECH","EPU","GXG","VNM","AFK","NGE","EGPT","EMFM","UAE","QAT","KSA"
    ],
    "C05_BONDS_CASH_CREDIT": [
        "BSV","BIV","BLV","GOVT","SCHR","SCHO","SCHZ","IGSB","IGIB","USIG","FLOT",
        "FLRN","PFF","PGX","CMF","SUB","SHM","TFI","MINT","ICSH","VTIP","STIP","LTPZ","HYD","HYMB"
    ],
    "C06_REAL_ASSETS": [
        "SCHH","USRT","REM","REZ","VNQI","GNR","PICK","COPX","SIL","SILJ","PHO",
        "FIW","CGW","IGF","RJI","DBE","RJA","RJN","PDBC","TOLZ","XLRE","FREL","KBWY"
    ],
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def original_149() -> set[str]:
    src = Path("regeneration/etf_trader_raw.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    cats = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "CATS":
                    cats = ast.literal_eval(node.value)
    if cats is None:
        raise RuntimeError("cannot recover canonical CATS from regeneration/etf_trader_raw.py")
    return {str(t).upper() for xs in cats.values() for t in xs}


def download_one(ticker: str) -> tuple[pd.DataFrame | None, str | None]:
    last_error = None
    d = None
    for attempt in range(5):
        try:
            d = yf.download(
                ticker,
                start=START,
                end=END_EXCLUSIVE,
                auto_adjust=False,
                actions=False,
                progress=False,
                threads=False,
                timeout=45,
            )
            if d is not None and not d.empty:
                break
            last_error = "empty"
        except Exception as e:
            last_error = f"download_error:{type(e).__name__}:{e}"
        time.sleep(min(2 ** attempt, 8))
    if d is None or d.empty:
        return None, last_error or "empty"

    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d.reset_index()
    need = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
    if any(c not in d.columns for c in need):
        return None, "missing_columns"

    raw_close = pd.to_numeric(d["Close"], errors="coerce")
    adj = pd.to_numeric(d["Adj Close"], errors="coerce")
    f = adj / raw_close.replace(0, np.nan)
    q = pd.DataFrame({
        "date": pd.to_datetime(d["Date"]).dt.tz_localize(None),
        "Open": pd.to_numeric(d["Open"], errors="coerce") * f,
        "High": pd.to_numeric(d["High"], errors="coerce") * f,
        "Low": pd.to_numeric(d["Low"], errors="coerce") * f,
        "Close": adj,
        "Volume": pd.to_numeric(d["Volume"], errors="coerce"),
    }).dropna().sort_values("date").drop_duplicates("date", keep="last")

    if q.empty:
        return None, "no_valid_rows"
    if (q[["Open", "High", "Low", "Close"]] <= 0).any().any() or (q["Volume"] < 0).any():
        return None, "invalid_values"

    bad = (
        (q["Low"] > q[["Open", "Close"]].min(axis=1) + 1e-8)
        | (q["High"] < q[["Open", "Close"]].max(axis=1) - 1e-8)
    )
    if bad.any():
        return None, f"ohlc_incoherent:{int(bad.sum())}"

    q = q[q["date"] <= LAST_REQUIRED].copy()
    pre = q[q["date"] <= PRE2017_CUTOFF]
    if len(pre) < MIN_PRE2017_ROWS:
        return None, f"insufficient_pre2017_rows:{len(pre)}"
    if q["date"].max() < LAST_REQUIRED:
        return None, f"ends_early:{q['date'].max().date()}"

    daily = q["Close"].pct_change(fill_method=None).abs()
    max_abs = float(daily.max(skipna=True))
    if not np.isfinite(max_abs) or max_abs > MAX_ABS_ADJ_DAILY_RETURN:
        return None, f"extreme_adjusted_daily_return:{max_abs:.6f}"

    return q, None


def main() -> int:
    out = Path("holdout60/output")
    raw = out / "raw_ticker_csv"
    raw.mkdir(parents=True, exist_ok=True)
    original = original_149()

    candidate_flat = [t for xs in CANDIDATES.values() for t in xs]
    overlap_candidates = sorted(set(candidate_flat) & original)
    if overlap_candidates:
        raise RuntimeError(f"candidate pool overlaps original universe: {overlap_candidates}")

    selected: list[dict] = []
    rejected: list[dict] = []
    data: dict[str, pd.DataFrame] = {}

    for cat, pool in CANDIDATES.items():
        need = QUOTAS[cat]
        chosen = 0
        for ticker in pool:
            q, reason = download_one(ticker)
            if q is None:
                rejected.append({"ticker": ticker, "macro_category": cat, "reason": reason})
                print("REJECT", cat, ticker, reason, flush=True)
                continue

            rec = {
                "ticker": ticker,
                "macro_category": cat,
                "rows": int(len(q)),
                "first": str(q.date.min().date()),
                "last": str(q.date.max().date()),
                "pre2017_rows": int((q.date <= PRE2017_CUTOFF).sum()),
                "max_abs_adj_daily_return": float(q.Close.pct_change(fill_method=None).abs().max()),
            }
            if chosen < need:
                selected.append(rec)
                data[ticker] = q
                chosen += 1
                print("SELECT", cat, ticker, chosen, "/", need, rec, flush=True)
            if chosen >= need:
                break

        if chosen != need:
            raise RuntimeError(f"quota not met for {cat}: selected {chosen}, required {need}")

    if len(selected) != 60:
        raise RuntimeError(f"expected 60 selected ETFs, got {len(selected)}")

    final_tickers = [r["ticker"] for r in selected]
    overlap = sorted(set(final_tickers) & original)
    if overlap:
        raise RuntimeError(f"FINAL HOLDOUT OVERLAP WITH ORIGINAL 149: {overlap}")
    if len(set(final_tickers)) != 60:
        raise RuntimeError("duplicate ticker in selected holdout")

    file_hashes = {}
    for r in selected:
        t = r["ticker"]
        q = data[t].copy()
        q["date"] = q["date"].dt.strftime("%Y-%m-%d")
        p = raw / f"{t}.csv"
        q.to_csv(p, index=False, float_format="%.17g")
        file_hashes[t] = sha256(p)

    universe = pd.DataFrame(selected)[["ticker", "macro_category"]]
    universe.to_csv(raw / "universe.csv", index=False)
    pd.DataFrame(selected).to_csv(out / "coverage.csv", index=False)
    pd.DataFrame(rejected).to_csv(out / "rejected.csv", index=False)

    for fld in ["Open", "High", "Low", "Close", "Volume"]:
        mat = pd.concat(
            [data[t].set_index("date")[[fld]].rename(columns={fld: t}) for t in final_tickers],
            axis=1,
        ).sort_index()
        mat.to_parquet(out / f"{fld.upper()}.parquet")

    frozen_payload = json.dumps({"quotas": QUOTAS, "candidates": CANDIDATES}, sort_keys=True).encode()
    manifest = {
        "status": "HOLDOUT60_FROZEN_QUALITY_GATED",
        "selection_rule": "first coverage-valid ticker in frozen per-cluster candidate order until quota; no return/performance criterion",
        "provider": "Yahoo Finance via yfinance",
        "requested_start": START,
        "last_included": str(LAST_REQUIRED.date()),
        "pre2017_min_rows": MIN_PRE2017_ROWS,
        "max_abs_adjusted_daily_return": MAX_ABS_ADJ_DAILY_RETURN,
        "original_universe_count": len(original),
        "selected_count": len(final_tickers),
        "intersection_with_original149": overlap,
        "quotas": QUOTAS,
        "candidate_spec_sha256": sha256_bytes(frozen_payload),
        "selected_tickers": final_tickers,
        "file_sha256": file_hashes,
        "performance_used_for_selection": False,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print("\nFINAL_MANIFEST")
    print(json.dumps({k: v for k, v in manifest.items() if k != "file_sha256"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
