#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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
QUOTA_PER_CLUSTER = 12

CATEGORIES = [
    "C01_US_BROAD_STYLE",
    "C02_US_SECTOR_THEME",
    "C03_DEVELOPED_GLOBAL",
    "C04_EMERGING",
    "C05_BONDS_CASH_CREDIT",
    "C06_REAL_ASSETS",
]

# Ordered pools frozen before any V3 performance calculation.
# They intentionally contain only unlevered ETFs/ETPs with plausible pre-2017 history;
# final inclusion depends solely on burned-set exclusion and data coverage/coherence.
CANDIDATES = {
    "C01_US_BROAD_STYLE": [
        "IWB","IWR","IWS","IWP","IWO","IWC","IJJ","IJK","IJS","IJT",
        "VBR","VBK","VOE","VOT","SCHV","SCHM","MGK","MGV","SPYG","SPYV",
        "VIOO","VIOV","VIOG","FNDA","SLYV","SLYG","MDYG","MDYV","VLUE","FNDX",
        "QVAL","RPG","RPV","RFG","RFV","PWV","PWB","PXLG","PXLV"
    ],
    "C02_US_SECTOR_THEME": [
        "XOP","PSI","PBW","QCLN","SKYY","CIBR","XAR","PTH","PJP","PBE",
        "PPH","IHF","IHE","IYG","IAI","IAT","IAK","IEO","IEZ","IYE",
        "IYM","IYK","IYC","IYZ","IYH","IYF","IYW","XTL","XHS","XHE",
        "XSW","XTN","XPH","KCE","FXH","FXL","FXN","FXU","FXD","FXG","FXR"
    ],
    "C03_DEVELOPED_GLOBAL": [
        "PID","DWX","IQDF","FNDF","GWX","VSS","SCHC","IDMO","ACWX","VXUS",
        "IXUS","GWL","DWM","DNL","DOL","DLS","SCJ","DFJ","DXJS","EWUS",
        "EWGS","JPXN","IDV","DBJP","HEWJ","HEWG","HEWI","HEWL","PDN","DIM",
        "AUSE","HFXI","DBAW","DWMF","DOO"
    ],
    "C04_EMERGING": [
        "FM","FNDE","XSOE","EEB","ILF","GXG","NGE","EGPT","EMFM","UAE",
        "QAT","KSA","EMQQ","ECNS","CQQQ","KBA","PGJ","GXC","CHIQ","CHIX",
        "CHIS","CHIM","CHIE","CHII","BRF","EWZS","IDX","ECON","EMGF","AFTY",
        "EEMA","EEMV","EEMO","HEEM","ADRE","FEM","FEMB"
    ],
    "C05_BONDS_CASH_CREDIT": [
        "GOVT","FLRN","PFF","PGX","CMF","SUB","SHM","TFI","MINT","ICSH",
        "VTIP","STIP","LTPZ","HYD","HYMB","SPSB","SPTS","SPTI","SPTL","SPIP",
        "SPAB","VTEB","TOTL","BOND","NEAR","SHYG","SJNK","HYLS","HYLB","EMHY",
        "PCY","VWOB","ELD","LEMB","IGOV","BWX","BWZ","WIP","FLTR","BAB"
    ],
    "C06_REAL_ASSETS": [
        "USRT","PICK","SILJ","RJI","RJA","RJN","PDBC","TOLZ","XLRE","FREL",
        "KBWY","REET","ICF","RWR","PSR","FRI","WPS","IFGL","DRW","DJP",
        "GCC","SLX","LIT","REMX","NLR","FAN","PIO","PBD","CUT","MOO",
        "XES","OIH","AMLP","MLPA","ENFR","GRID","RWO","RWX","PPA"
    ],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_burned(path: Path) -> set[str]:
    d = pd.read_csv(path)
    if "ticker" not in d.columns:
        raise RuntimeError(f"burned reference missing ticker column: {path}")
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
    })
    q = q.dropna().sort_values("date").drop_duplicates("date", keep="last")
    if q.empty:
        return None, "no_valid_rows"
    if (q[["Open", "High", "Low", "Close"]] <= 0).any().any():
        return None, "nonpositive_ohlc"
    if (q["Volume"] < 0).any():
        return None, "negative_volume"

    q["High"] = q[["High", "Open", "Close", "Low"]].max(axis=1)
    q["Low"] = q[["Low", "Open", "Close", "High"]].min(axis=1)

    pre = q[q.date <= PRE2017_CUTOFF]
    if len(pre) < MIN_PRE2017_ROWS:
        return None, f"insufficient_pre2017_rows:{len(pre)}"
    if q.date.max() < LAST_REQUIRED:
        return None, f"ends_early:{q.date.max().date()}"
    q = q[q.date <= LAST_REQUIRED].copy()
    return q, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--original149", required=True)
    ap.add_argument("--holdout70", required=True)
    ap.add_argument("--eu110", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    original = load_burned(Path(args.original149))
    holdout = load_burned(Path(args.holdout70))
    eu110 = load_burned(Path(args.eu110))
    burned = original | holdout | eu110

    if len(original) != 149:
        raise RuntimeError(f"expected Original149 size 149, got {len(original)}")
    if len(holdout) != 70:
        raise RuntimeError(f"expected Holdout70 size 70, got {len(holdout)}")
    if len(eu110) != 110:
        raise RuntimeError(f"expected EU110 exclusion size 110, got {len(eu110)}")

    flat = [t for c in CATEGORIES for t in CANDIDATES[c]]
    if len(flat) != len(set(flat)):
        s = pd.Series(flat)
        dup = sorted(s[s.duplicated()].unique().tolist())
        raise RuntimeError(f"duplicate candidate ticker across pools: {dup}")

    out = Path(args.out)
    raw = out / "raw_ticker_csv"
    raw.mkdir(parents=True, exist_ok=True)
    selected: list[dict] = []
    rejected: list[dict] = []
    data: dict[str, pd.DataFrame] = {}

    for cat in CATEGORIES:
        n = 0
        for ticker in CANDIDATES[cat]:
            if ticker.upper() in burned:
                rejected.append({"ticker": ticker, "macro_category": cat, "reason": "burned_set_overlap"})
                continue
            q, reason = fetch_one(ticker)
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
            selected.append(rec)
            data[ticker] = q
            n += 1
            print("SELECT", cat, ticker, n, "/", QUOTA_PER_CLUSTER, flush=True)
            if n == QUOTA_PER_CLUSTER:
                break
        if n != QUOTA_PER_CLUSTER:
            raise RuntimeError(f"quota not met for {cat}: {n}/{QUOTA_PER_CLUSTER}")

    if len(selected) != 72:
        raise RuntimeError(f"expected 72 selected, got {len(selected)}")
    tickers = [r["ticker"] for r in selected]
    if len(set(tickers)) != 72:
        raise RuntimeError("duplicate selected ticker")
    overlap = sorted(set(t.upper() for t in tickers) & burned)
    if overlap:
        raise RuntimeError(f"selected universe overlaps burned sets: {overlap}")

    file_hashes = {}
    for r in selected:
        t = r["ticker"]
        q = data[t].copy()
        q["date"] = q.date.dt.strftime("%Y-%m-%d")
        p = raw / f"{t}.csv"
        q.to_csv(p, index=False, float_format="%.17g")
        file_hashes[t] = sha256(p)

    universe = pd.DataFrame(selected)[["ticker", "macro_category"]]
    universe.to_csv(out / "universe.csv", index=False)
    pd.DataFrame(selected).to_csv(out / "coverage.csv", index=False)
    pd.DataFrame(rejected).to_csv(out / "rejected.csv", index=False)

    spec_payload = json.dumps({
        "quota_per_cluster": QUOTA_PER_CLUSTER,
        "categories": CATEGORIES,
        "candidates": CANDIDATES,
        "start": START,
        "last_required": str(LAST_REQUIRED.date()),
        "min_pre2017_rows": MIN_PRE2017_ROWS,
    }, sort_keys=True).encode()

    manifest = {
        "status": "EVIDENCE_V3_DEV72_FROZEN",
        "provider": "Yahoo Finance via yfinance",
        "selection_rule": "first non-burned coverage-valid ticker in frozen category order; no performance criterion",
        "requested_start": START,
        "last_included": str(LAST_REQUIRED.date()),
        "pre2017_cutoff": str(PRE2017_CUTOFF.date()),
        "minimum_pre2017_rows": MIN_PRE2017_ROWS,
        "selected_count": len(tickers),
        "per_cluster": QUOTA_PER_CLUSTER,
        "unique_tickers": len(set(tickers)),
        "burned_reference_counts": {
            "original149": len(original),
            "holdout70": len(holdout),
            "eu110_tested": len(eu110),
            "union": len(burned),
        },
        "intersection_with_burned_union": overlap,
        "performance_used_for_selection": False,
        "candidate_spec_sha256": hashlib.sha256(spec_payload).hexdigest(),
        "selected": selected,
        "file_sha256": file_hashes,
        "universe_sha256": sha256(out / "universe.csv"),
        "coverage_sha256": sha256(out / "coverage.csv"),
        "rejected_sha256": sha256(out / "rejected.csv"),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k not in ("selected", "file_sha256")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
