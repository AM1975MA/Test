#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ensemble", required=True, help="source-only ENSEMBLE_TAIL_OOS.csv")
    ap.add_argument("--fit-audit", required=True, help="source-only ENSEMBLE_FIT_AUDIT.csv")
    ap.add_argument("--tit-r", required=True, help="source-only TIT_R_SOURCE_ONLY.csv")
    ap.add_argument("--baseline-result", required=True, help="source-only RESULT.json from full canonical runner")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ensemble_path = Path(args.ensemble)
    audit_path = Path(args.fit_audit)
    tit_path = Path(args.tit_r)
    baseline_path = Path(args.baseline_result)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    pred = pd.read_csv(ensemble_path)
    pred["signal_date"] = pd.to_datetime(pred.signal_date)
    required_pred = ["signal_date", "ticker", "BASE", "ET_TAIL", "XGB_TAIL", "TAIL_HYBRID"]
    missing = [c for c in required_pred if c not in pred.columns]
    if missing:
        raise RuntimeError(f"ensemble predictions missing columns: {missing}")

    tit = pd.read_csv(tit_path)
    tit["signal_date"] = pd.to_datetime(tit.signal_date)
    for c in ["entry_date", "exit_date"]:
        tit[c] = pd.to_datetime(tit[c])
    cal = (
        tit[["signal_date", "entry_date", "exit_date"]]
        .drop_duplicates()
        .sort_values("signal_date")
        .reset_index(drop=True)
    )
    dates = pd.DatetimeIndex(cal.signal_date)
    tickers = sorted(pred.ticker.astype(str).unique())

    if len(dates) != 114:
        raise RuntimeError(f"expected 114 Hybrid24 OOS signal dates, got {len(dates)}")
    if dates.min() != pd.Timestamp("2017-01-31") or dates.max() != pd.Timestamp("2026-06-30"):
        raise RuntimeError(f"unexpected Hybrid24 calendar: {dates.min()} -> {dates.max()}")

    def pivot(col: str) -> pd.DataFrame:
        return (
            pred.pivot(index="signal_date", columns="ticker", values=col)
            .reindex(index=dates, columns=tickers)
        )

    base = pivot("BASE")
    et = pivot("ET_TAIL")
    xgb = pivot("XGB_TAIL")
    tail = pivot("TAIL_HYBRID")

    # Frozen canonical Hybrid24 post-processing from hybrid_producer.py.
    lag1 = np.vstack([tail.to_numpy()[:1], tail.to_numpy()[:-1]])
    lag2 = np.vstack([tail.to_numpy()[:1], tail.to_numpy()[:1], tail.to_numpy()[:-2]])
    smooth = 0.40 * tail.to_numpy() + 0.30 * lag1 + 0.30 * lag2
    transformed = np.power(np.clip(smooth, 0.0, 1.0), 1.10)
    score = 0.475 * base.to_numpy() + 0.525 * transformed
    score_df = pd.DataFrame(score, index=dates, columns=tickers)

    rows = []
    for dt in dates:
        for ticker in tickers:
            vals = {
                "BASE": base.at[dt, ticker],
                "ET_RANK": et.at[dt, ticker],
                "XGB_RANK": xgb.at[dt, ticker],
                "TAIL_HYBRID": tail.at[dt, ticker],
                "HYBRID24_SCORE": score_df.at[dt, ticker],
            }
            if not np.isfinite(vals["HYBRID24_SCORE"]):
                continue
            rows.append({"signal_date": dt, "ticker": ticker, **vals})

    checkpoint = pd.DataFrame(rows)
    if checkpoint.empty:
        raise RuntimeError("no finite Hybrid24 checkpoint rows")
    checkpoint["HYBRID24_RANK"] = checkpoint.groupby("signal_date").HYBRID24_SCORE.rank(
        ascending=False, method="average"
    )
    n = checkpoint.groupby("signal_date").ticker.transform("count").astype(float)
    checkpoint["HYBRID24_POSITION"] = np.where(
        n > 1, 1.0 - (checkpoint.HYBRID24_RANK - 1.0) / (n - 1.0), 1.0
    )
    checkpoint = checkpoint.sort_values(["signal_date", "HYBRID24_RANK", "ticker"]).reset_index(drop=True)

    if checkpoint.signal_date.nunique() != 114:
        raise RuntimeError("checkpoint lost one or more OOS signal dates")
    if checkpoint.duplicated(["signal_date", "ticker"]).any():
        raise RuntimeError("duplicate checkpoint keys")

    # Cross-check source-only maturity audit.
    audit = pd.read_csv(audit_path)
    if "maturity_ok" not in audit.columns:
        raise RuntimeError("ensemble fit audit missing maturity_ok")
    maturity = audit.maturity_ok.astype(str).str.lower().map({"true": True, "false": False})
    if maturity.isna().any() or not bool(maturity.all()):
        raise RuntimeError("Hybrid24 ensemble maturity audit failed")

    baseline = json.loads(baseline_path.read_text())
    contract = baseline.get("contract", {})
    required_contract = {
        "historical_scores_consumed": False,
        "historical_paths_consumed": False,
        "historical_cluster_membership_consumed": False,
        "historical_basket_membership_consumed": False,
        "basket_membership_generated_from_source": True,
        "titanium_maturity_safe": True,
        "cluster_source_causal": True,
        "ensemble_maturity_safe": True,
    }
    for key, expected in required_contract.items():
        if contract.get(key) is not expected:
            raise RuntimeError(f"canonical source-only contract failed: {key}={contract.get(key)!r}")

    full_h24 = baseline.get("metrics", {}).get("full", {}).get("highcagr24", {})
    if "cagr" not in full_h24:
        raise RuntimeError("canonical baseline RESULT missing full/highcagr24/cagr")
    baseline_cagr = float(full_h24["cagr"])
    # The Evidence V1 source of truth certifies the canonical Original149 baseline
    # at 31.60% CAGR.  This is an engineering parity gate, not a new research metric.
    if round(baseline_cagr, 4) != 0.3160:
        raise RuntimeError(
            f"canonical baseline parity failed: full HighCAGR24 CAGR={baseline_cagr:.12f}, expected rounded 0.3160"
        )

    checkpoint.to_csv(out / "OOS_SCORES.csv", index=False)
    audit.to_csv(out / "FIT_AUDIT.csv", index=False)
    cal.to_csv(out / "CALENDAR.csv", index=False)
    (out / "BASELINE_PARITY.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "full_highcagr24_cagr": baseline_cagr,
                "evidence_v1_certified_rounded_cagr": 0.3160,
                "source_only_contract": {k: contract.get(k) for k in required_contract},
                "signal_dates": int(checkpoint.signal_date.nunique()),
                "rows": int(len(checkpoint)),
                "tickers": int(checkpoint.ticker.nunique()),
                "min_signal_date": str(checkpoint.signal_date.min().date()),
                "max_signal_date": str(checkpoint.signal_date.max().date()),
                "cascade_metrics_observed": False,
            },
            indent=2,
        ) + "\n"
    )

    manifest_files = ["OOS_SCORES.csv", "FIT_AUDIT.csv", "CALENDAR.csv", "BASELINE_PARITY.json"]
    manifest = {
        "checkpoint": "hybrid24_oos_v1",
        "purpose": "materialize canonical source-only Hybrid24 OOS score; no LTR/cascade input consumed",
        "source_inputs_sha256": {
            "ensemble": sha256_file(ensemble_path),
            "fit_audit": sha256_file(audit_path),
            "tit_r": sha256_file(tit_path),
            "canonical_baseline_result": sha256_file(baseline_path),
        },
        "files_sha256": {name: sha256_file(out / name) for name in manifest_files},
    }
    (out / "CHECKPOINT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

    print(json.dumps({"status": "PASS", **json.loads((out / "BASELINE_PARITY.json").read_text())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
