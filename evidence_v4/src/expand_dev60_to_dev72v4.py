#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
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
OLD_QUOTA = 10
NEW_QUOTA = 12


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
    ap.add_argument("--dev72-v3", required=True)
    ap.add_argument("--dev60-root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    categories, candidates = load_v3_candidate_spec(Path(args.v3_freezer))
    original = load_tickers(Path(args.original149))
    holdout = load_tickers(Path(args.holdout70))
    eu110 = load_tickers(Path(args.eu110))
    dev72v3 = load_tickers(Path(args.dev72_v3))
    burned = original | holdout | eu110 | dev72v3
    if (len(original), len(holdout), len(eu110), len(dev72v3), len(burned)) != (149, 70, 110, 72, 400):
        raise RuntimeError(
            f"reference sizes unexpected: original={len(original)} holdout={len(holdout)} "
            f"eu110={len(eu110)} dev72v3={len(dev72v3)} union={len(burned)}"
        )

    dev60_root = Path(args.dev60_root)
    dev60_u = pd.read_csv(dev60_root / "universe.csv")
    dev60_cov = pd.read_csv(dev60_root / "coverage.csv")
    dev60_manifest = json.loads((dev60_root / "manifest.json").read_text())
    if len(dev60_u) != 60 or dev60_u.ticker.nunique() != 60:
        raise RuntimeError("frozen Dev60 is not 60 unique tickers")
    if dev60_manifest["performance_used_for_selection"] is not False:
        raise RuntimeError("Dev60 provenance is not clean")

    counts = dev60_u.groupby("macro_category").size().to_dict()
    if any(counts.get(c) != OLD_QUOTA for c in categories):
        raise RuntimeError(f"Dev60 is not 10 per category: {counts}")

    out = Path(args.out)
    raw_out = out / "raw_ticker_csv"
    raw_out.mkdir(parents=True, exist_ok=True)

    selected: list[dict] = []
    rejected: list[dict] = []
    add_hashes: dict[str, str] = {}

    # Preserve all 60 frozen constituents and bytes exactly.
    cov_by_ticker = dev60_cov.set_index("ticker")
    for cat in categories:
        prefix = dev60_u.loc[dev60_u.macro_category == cat, "ticker"].astype(str).tolist()
        if len(prefix) != OLD_QUOTA:
            raise RuntimeError(f"bad Dev60 prefix count for {cat}")
        positions = [candidates[cat].index(t) if t in candidates[cat] else -1 for t in prefix]
        if any(i < 0 for i in positions) or positions != sorted(positions):
            raise RuntimeError(f"Dev60 prefix not ordered by frozen candidate list for {cat}: {prefix}")
        for t in prefix:
            src = dev60_root / "raw_ticker_csv" / f"{t}.csv"
            want = dev60_manifest["file_sha256"].get(t)
            got = sha256(src)
            if want != got:
                raise RuntimeError(f"Dev60 raw hash mismatch {t}: {got} != {want}")
            shutil.copy2(src, raw_out / f"{t}.csv")
            row = cov_by_ticker.loc[t]
            selected.append({
                "ticker": t,
                "macro_category": cat,
                "rows": int(row["rows"]),
                "first": str(row["first"]),
                "last": str(row["last"]),
                "pre2017_rows": int(row["pre2017_rows"]),
                "source": "frozen_dev60_prefix",
            })

        last_pos = positions[-1]
        n_added = 0
        for ticker in candidates[cat][last_pos + 1:]:
            if ticker.upper() in burned or ticker in prefix:
                rejected.append({"ticker": ticker, "macro_category": cat, "reason": "burned_or_already_selected"})
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
                "source": "engineering_expansion_after_dev60",
            }
            selected.append(rec)
            q2 = q.copy()
            q2["date"] = q2.date.dt.strftime("%Y-%m-%d")
            fp = raw_out / f"{ticker}.csv"
            q2.to_csv(fp, index=False, float_format="%.17g")
            add_hashes[ticker] = sha256(fp)
            n_added += 1
            print("ADD", cat, ticker, n_added, "/", NEW_QUOTA - OLD_QUOTA, flush=True)
            if n_added == NEW_QUOTA - OLD_QUOTA:
                break
        if n_added != NEW_QUOTA - OLD_QUOTA:
            raise RuntimeError(f"could not add two valid names for {cat}: added {n_added}")

    u = pd.DataFrame(selected)[["ticker", "macro_category"]]
    if len(u) != 72 or u.ticker.nunique() != 72:
        raise RuntimeError(f"Dev72V4 invalid total={len(u)} unique={u.ticker.nunique()}")
    per_cat = u.groupby("macro_category").size().to_dict()
    if any(per_cat.get(c) != NEW_QUOTA for c in categories):
        raise RuntimeError(f"Dev72V4 is not 12 per category: {per_cat}")
    overlap = sorted(set(u.ticker.astype(str).str.upper()) & burned)
    if overlap:
        raise RuntimeError(f"Dev72V4 overlaps burned/tested sets: {overlap}")

    # Explicit prefix-preservation gate after expansion.
    for cat in categories:
        old = dev60_u.loc[dev60_u.macro_category == cat, "ticker"].astype(str).tolist()
        new = u.loc[u.macro_category == cat, "ticker"].astype(str).tolist()
        if new[:OLD_QUOTA] != old:
            raise RuntimeError(f"Dev60 prefix changed for {cat}: {new[:OLD_QUOTA]} != {old}")

    coverage = pd.DataFrame(selected)
    u.to_csv(out / "universe.csv", index=False)
    coverage.to_csv(out / "coverage.csv", index=False)
    pd.DataFrame(rejected).to_csv(out / "rejected_expansion.csv", index=False)

    all_hashes = {t: sha256(raw_out / f"{t}.csv") for t in u.ticker.astype(str)}
    manifest = {
        "status": "EVIDENCE_V4_DEV72_ENGINEERING_FIX_FROZEN",
        "reason": "canonical MA3 requires >=56 dynamic + >=8 defensive eligible names; Dev60 has only 50 dynamic",
        "invalid_preperformance_run": "37075621569",
        "provider": "Yahoo Finance via yfinance for 12 added names only; original 60 copied byte-for-byte from frozen Dev60",
        "selection_rule": "preserve frozen Dev60 10/category prefix and append next two coverage-valid non-burned names from exact pre-V3 candidate order",
        "requested_start": START,
        "last_included": str(LAST_REQUIRED.date()),
        "pre2017_cutoff": str(PRE2017_CUTOFF.date()),
        "minimum_pre2017_rows": MIN_PRE2017_ROWS,
        "selected_count": 72,
        "per_cluster": NEW_QUOTA,
        "dev60_prefix_preserved": True,
        "burned_reference_counts": {
            "original149": len(original), "holdout70": len(holdout),
            "eu110_tested": len(eu110), "dev72_v3": len(dev72v3), "union": len(burned),
        },
        "intersection_with_burned_union": overlap,
        "performance_used_for_selection": False,
        "dev60_manifest_sha256": sha256(dev60_root / "manifest.json"),
        "dev60_universe_sha256": sha256(dev60_root / "universe.csv"),
        "selected": selected,
        "added_ticker_sha256": add_hashes,
        "file_sha256": all_hashes,
        "universe_sha256": sha256(out / "universe.csv"),
        "coverage_sha256": sha256(out / "coverage.csv"),
        "rejected_expansion_sha256": sha256(out / "rejected_expansion.csv"),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k not in ("selected", "file_sha256", "added_ticker_sha256")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
