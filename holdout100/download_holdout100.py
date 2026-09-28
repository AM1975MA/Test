#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

START = "2004-01-01"
END_EXCLUSIVE = "2026-08-01"  # includes 2026-07-31
MIN_PRE2017_ROWS = 252
LAST_REQUIRED = pd.Timestamp("2026-07-31")
PRE2017_CUTOFF = pd.Timestamp("2017-01-31")

QUOTAS = {
    "C01_US_BROAD_STYLE": 17,
    "C02_US_SECTOR_THEME": 17,
    "C03_DEVELOPED_GLOBAL": 17,
    "C04_EMERGING": 17,
    "C05_BONDS_CASH_CREDIT": 16,
    "C06_REAL_ASSETS": 16,
}

# Frozen before any holdout performance is calculated. Order is the deterministic
# fallback order. Selection depends only on data existence/coverage/coherence.
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
    try:
        d = yf.download(
            ticker,
            start=START,
            end=END_EXCLUSIVE,
            auto_adjust=False,
            actions=False,
            progress=False,
            threads=False,
        )
    except Exception as e:
        return None, f"download_error:{type(e).__name__}:{e}"
    if d is None or d.empty:
        return None, "empty"
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
        "date": pd.to_datetime(d["Date"]),
        "Open": pd.to_numeric(d["Open"], errors="coerce") * f,
        "High": pd.to_numeric(d["High"], errors="coerce") * f,
        "Low": pd.to_numeric(d["Low"], errors="coerce") * f,
        "Close": adj,
        "Volume": pd.to_numeric(d["Volume"], errors="coerce"),
    }).dropna().sort_values("date").drop_duplicates("date", keep="last")
    if q.empty:
        return None, "no_valid_rows"
    if (q[["Open","High","Low","Close"]] <= 0).any().any() or (q["Volume"] < 0).any():
        return None, "invalid_values"
    bad = (q["Low"] > q[["Open","Close"]].min(axis=1) + 1e-8) | (q["High"] < q[["Open","Close"]].max(axis=1) - 1e-8)
    if bad.any():
        return None, f"ohlc_incoherent:{int(bad.sum())}"
    pre = q[q["date"] <= PRE2017_CUTOFF]
    if len(pre) < MIN_PRE2017_ROWS:
        return None, f"insufficient_pre2017_rows:{len(pre)}"
    if q["date"].max() < LAST_REQUIRED:
        return None, f"ends_early:{q['date'].max().date()}"
    q = q[q["date"] <= LAST_REQUIRED].copy()
    return q, None


def main() -> int:
    out = Path("holdout100/output")
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
            }
            if chosen < need:
                selected.append(rec)
                data[ticker] = q
                chosen += 1
                print("SELECT", cat, ticker, chosen, "/", need, flush=True)
            else:
                # Coverage-valid reserve; recorded but not selected.
                rejected.append({"ticker": ticker, "macro_category": cat, "reason": "valid_reserve_not_needed"})
            if chosen >= need:
                break
        if chosen != need:
            raise RuntimeError(f"quota not met for {cat}: selected {chosen}, required {need}")

    if len(selected) != 100:
        raise RuntimeError(f"expected 100 selected ETFs, got {len(selected)}")
    final_tickers = [r["ticker"] for r in selected]
    overlap = sorted(set(final_tickers) & original)
    if overlap:
        raise RuntimeError(f"FINAL HOLDOUT OVERLAP WITH ORIGINAL 149: {overlap}")
    if len(set(final_tickers)) != 100:
        raise RuntimeError("duplicate ticker in selected holdout")

    # Persist per-ticker CSVs with the same adjusted-OHLC convention as canonical raw.
    file_hashes = {}
    for r in selected:
        t = r["ticker"]
        q = data[t].copy()
        q["date"] = q["date"].dt.strftime("%Y-%m-%d")
        p = raw / f"{t}.csv"
        q.to_csv(p, index=False, float_format="%.17g")
        file_hashes[t] = sha256(p)

    universe = pd.DataFrame(selected)[["ticker","macro_category"]]
    universe.to_csv(raw / "universe.csv", index=False)
    pd.DataFrame(selected).to_csv(out / "coverage.csv", index=False)
    pd.DataFrame(rejected).to_csv(out / "rejected.csv", index=False)

    # Wide matrices are transport copies only; per-ticker CSV is the productive source.
    fields = ["Open","High","Low","Close","Volume"]
    for fld in fields:
        mat = pd.concat(
            [data[t].set_index("date")[[fld]].rename(columns={fld: t}) for t in final_tickers],
            axis=1,
        ).sort_index()
        mat.to_parquet(out / f"{fld.upper()}.parquet")

    frozen_payload = json.dumps({"quotas": QUOTAS, "candidates": CANDIDATES}, sort_keys=True).encode()
    manifest = {
        "status": "HOLDOUT100_DOWNLOADED",
        "selection_rule": "first coverage-valid ticker in frozen per-cluster candidate order until quota; no return/performance criterion",
        "provider": "Yahoo Finance via yfinance",
        "requested_start": START,
        "last_included": str(LAST_REQUIRED.date()),
        "pre2017_min_rows": MIN_PRE2017_ROWS,
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
    print(json.dumps({k:v for k,v in manifest.items() if k != "file_sha256"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
