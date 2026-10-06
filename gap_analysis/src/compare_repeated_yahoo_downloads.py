#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

OHLC = ["Open", "High", "Low", "Close"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_csv(path: Path) -> pd.DataFrame:
    q = pd.read_csv(path)
    q["date"] = pd.to_datetime(q["date"])
    return q.set_index("date").sort_index()


def compare_pair(a_root: Path, b_root: Path, label: str) -> tuple[dict, pd.DataFrame]:
    ua = pd.read_csv(a_root / "universe.csv")
    ub = pd.read_csv(b_root / "universe.csv")
    ta = list(ua.ticker.astype(str))
    tb = list(ub.ticker.astype(str))
    if ta != tb:
        raise RuntimeError(f"{label}: universe/order mismatch")

    rows = []
    for t in ta:
        pa, pb = a_root / f"{t}.csv", b_root / f"{t}.csv"
        A, B = load_csv(pa), load_csv(pb)
        date_equal = A.index.equals(B.index)
        common = A.index.intersection(B.index)
        Ac, Bc = A.loc[common], B.loc[common]
        denom = np.maximum(np.abs(Ac[OHLC].to_numpy(float)), 1e-12)
        rel = np.abs(Bc[OHLC].to_numpy(float) - Ac[OHLC].to_numpy(float)) / denom
        max_rel = float(np.nanmax(rel)) if rel.size else float("nan")

        ra = Ac["Close"].pct_change()
        rb = Bc["Close"].pct_change()
        rdelta = (rb - ra).abs()
        max_ret_delta = float(rdelta.max(skipna=True)) if len(rdelta) else float("nan")

        vol_diff = int((Ac["Volume"].to_numpy() != Bc["Volume"].to_numpy()).sum())
        ratio = Bc[OHLC].to_numpy(float) / Ac[OHLC].to_numpy(float)
        finite = ratio[np.isfinite(ratio)]
        ratio_span = float(finite.max() - finite.min()) if finite.size else float("nan")
        ratio_median = float(np.median(finite)) if finite.size else float("nan")
        constant_scale = bool(finite.size and ratio_span <= 1e-10)

        rows.append({
            "pair": label,
            "ticker": t,
            "sha_equal": sha256(pa) == sha256(pb),
            "rows_a": len(A),
            "rows_b": len(B),
            "date_equal": date_equal,
            "common_rows": len(common),
            "volume_diff_cells": vol_diff,
            "max_abs_relative_ohlc_diff": max_rel,
            "max_abs_close_return_diff": max_ret_delta,
            "ohlc_ratio_median_b_over_a": ratio_median,
            "ohlc_ratio_span": ratio_span,
            "constant_multiplicative_rescale_1e10": constant_scale,
        })

    df = pd.DataFrame(rows)
    summary = {
        "pair": label,
        "tickers": int(len(df)),
        "different_csv_sha256": int((~df.sha_equal).sum()),
        "ticker_date_or_row_mismatch": int(((~df.date_equal) | (df.rows_a != df.rows_b)).sum()),
        "tickers_with_volume_difference": int((df.volume_diff_cells > 0).sum()),
        "tickers_with_ohlc_diff_gt_1e12": int((df.max_abs_relative_ohlc_diff > 1e-12).sum()),
        "tickers_with_ohlc_diff_gt_1e8": int((df.max_abs_relative_ohlc_diff > 1e-8).sum()),
        "tickers_with_return_diff_gt_1e12": int((df.max_abs_close_return_diff > 1e-12).sum()),
        "tickers_with_return_diff_gt_1e8": int((df.max_abs_close_return_diff > 1e-8).sum()),
        "max_abs_relative_ohlc_diff": float(df.max_abs_relative_ohlc_diff.max()),
        "max_abs_close_return_diff": float(df.max_abs_close_return_diff.max()),
        "changed_tickers_constant_rescale": int(((df.max_abs_relative_ohlc_diff > 1e-12) & df.constant_multiplicative_rescale_1e10).sum()),
    }
    return summary, df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root1", required=True)
    ap.add_argument("--root2", required=True)
    ap.add_argument("--root3", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    roots = [Path(args.root1), Path(args.root2), Path(args.root3)]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    manifests = [json.loads((r / "manifest.json").read_text()) for r in roots]
    for m in manifests:
        if int(m["tickers"]) != 149:
            raise RuntimeError("not Original149")
        if m["package_versions"]["yfinance"] != "0.2.66":
            raise RuntimeError("unexpected yfinance version")
        if m["requested_end_exclusive"] != "2026-08-01":
            raise RuntimeError("unexpected end date")

    all_rows = []
    summaries = []
    for i, j, label in [(0, 1, "1_vs_2"), (0, 2, "1_vs_3"), (1, 2, "2_vs_3")]:
        s, d = compare_pair(roots[i], roots[j], label)
        summaries.append(s)
        all_rows.append(d)

    detail = pd.concat(all_rows, ignore_index=True)
    detail.to_csv(out / "REPEATABILITY_PER_TICKER.csv", index=False)
    result = {
        "status": "YFINANCE_REPEATABILITY_V1_COMPLETE",
        "contract": {
            "universe": "Original149",
            "downloads": 3,
            "start": "2004-01-01",
            "end_exclusive": "2026-08-01",
            "yfinance": "0.2.66",
            "pandas": manifests[0]["package_versions"]["pandas"],
            "price_semantics": manifests[0]["price_semantics"],
        },
        "pairs": summaries,
        "global": {
            "any_date_or_row_mismatch": bool(any(s["ticker_date_or_row_mismatch"] for s in summaries)),
            "any_volume_difference": bool(any(s["tickers_with_volume_difference"] for s in summaries)),
            "max_abs_relative_ohlc_diff": float(max(s["max_abs_relative_ohlc_diff"] for s in summaries)),
            "max_abs_close_return_diff": float(max(s["max_abs_close_return_diff"] for s in summaries)),
        },
    }
    (out / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
