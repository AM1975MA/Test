#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
EU = REPO / "europe120" / "eu120_retrain"

spec = importlib.util.spec_from_file_location("v2runner", EU / "run_eu120_retrain.py")
r = importlib.util.module_from_spec(spec)
sys.modules["v2runner"] = r
spec.loader.exec_module(r)

FROZEN70 = Path(os.environ["FROZEN_HOLDOUT70_ROOT"]).resolve()
FROZEN149 = Path(os.environ["FROZEN_149_ROOT"]).resolve()
OUT = ROOT / "same_source_results"
OUT.mkdir(parents=True, exist_ok=True)

CANONICAL = {
    "cagr": 0.4314595242029944,
    "maxdd": -0.2503576476357465,
    "sharpe": 1.3635086089607882,
}


def _copy_universe(meta: pd.DataFrame, out: Path, source: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    meta = meta[["ticker", "macro_category"]].drop_duplicates().copy()
    meta["ticker"] = meta["ticker"].astype(str).str.upper()
    meta.to_csv(out / "universe.csv", index=False)
    missing = []
    for t in meta.ticker:
        p = source / f"{t}.csv"
        if not p.exists():
            missing.append(t)
        else:
            shutil.copyfile(p, out / p.name)
    if missing:
        raise RuntimeError(f"missing frozen inputs from {source}: {missing}")


def prepare_inputs(target: pd.DataFrame, base: Path, target_source: Path) -> tuple[Path, Path, Path, Path]:
    raw_train = base / "raw_target"
    raw_ref = base / "raw_refs"
    ma3 = base / "ma3"
    models = base / "models"
    for p in (raw_train, raw_ref, ma3, models):
        p.mkdir(parents=True, exist_ok=True)

    _copy_universe(target, raw_train, target_source)
    refs = pd.DataFrame({
        "ticker": r.REF_TICKERS,
        "macro_category": ["REF_US", "REF_CREDIT", "REF_BOND", "REF_CASH", "REF_CASH"],
    })
    _copy_universe(refs, raw_ref, FROZEN149 / "etf_trader_raw")
    return raw_train, raw_ref, ma3, models


def run_one(name: str, target: pd.DataFrame, target_source: Path) -> dict:
    base = OUT / name
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    raw_train, raw_ref, ma3_dir, models = prepare_inputs(target, base, target_source)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(r.ETF / "src")
    subprocess.run([
        sys.executable,
        str(EU / "build_ma3_panel_causal.py"),
        "--data", str(raw_train),
        "--output", str(ma3_dir),
    ], check=True, env=env, cwd=r.ETF)

    panel = pd.read_pickle(ma3_dir / "RAW_FEATURE_PANEL.pkl")
    panel["signal_date"] = pd.to_datetime(panel.signal_date)
    panel["exit_date_63"] = pd.to_datetime(panel.exit_date_63)

    tickers = target.ticker.astype(str).str.upper().tolist()
    cats = dict(zip(target.ticker.astype(str).str.upper(), target.macro_category))

    tmats, _, tdates, tcomp, ttail = r.build_titanium_parts(
        raw_train, market_spy_raw=raw_ref, candidates=tickers
    )
    train_parts = r.add_train_labels(tcomp, ttail, tmats, tdates)
    target_macro, target_mfeatures = r.dummy_macro(ttail.copy(), cats)
    target_parts = (tcomp.copy(), ttail.copy(), target_macro, target_mfeatures)

    signals = pd.DatetimeIndex(sorted(set(tcomp.signal_date)))
    signals = signals[(signals >= r.FIRST_SIGNAL) & (signals <= r.LAST_SIGNAL)]

    base_pred = r.fit_titanium_cross(
        train_parts, target_parts, cats, "annual", signals, models / "annual"
    )
    ma_pred = r.fit_ma3_cross(
        panel, panel, "annual", signals, models / "annual"
    )
    pred = base_pred.merge(ma_pred, on=["signal_date", "ticker"], how="inner")

    cand_mats, _, _ = r.load_ticker_csv_folder(raw_train)
    ref_mats, _, _ = r.load_ticker_csv_folder(raw_ref)
    cal = r.calendar_from_open(cand_mats["Open"], signals).dropna(subset=["exit_date"]).reset_index(drop=True)
    pred = pred[pred.signal_date.isin(cal.signal_date)].copy()
    score, pm = r.score_from_panel(pred, cal, tickers, False)
    metrics, equity, turnover, ds = r.replay(score, pm, cal, cand_mats, ref_mats, tickers)

    close = cand_mats["Close"].reindex(ds).ffill().bfill()
    ew = (close / close.iloc[0]).mean(axis=1).to_numpy(float)
    ew_metrics = r.metrics(ew)

    pred.to_csv(base / "ANNUAL_PREDICTIONS.csv", index=False)
    np.savez_compressed(base / "PATH.npz", dates=ds.values, equity=equity, turnover=turnover)
    result = {
        "name": name,
        "target_count": int(len(target)),
        "period": [str(ds.min().date()), str(ds.max().date())],
        "sessions": int(len(ds)),
        "v2_full_universe": metrics,
        "equal_weight_buy_hold": ew_metrics,
        "prediction_rows": int(len(pred)),
    }
    (base / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    u149 = pd.read_csv(FROZEN149 / "etf_trader_raw" / "universe.csv")
    u70 = pd.read_csv(FROZEN70 / "raw_ticker_csv" / "universe.csv")
    assert len(u149) == 149 and u149.ticker.nunique() == 149
    assert len(u70) == 70 and u70.ticker.nunique() == 70
    assert not (set(u149.ticker.astype(str)) & set(u70.ticker.astype(str)))

    print("RUN_149_SAME_SOURCE", flush=True)
    res149 = run_one("original149", u149, FROZEN149 / "etf_trader_raw")

    got = res149["v2_full_universe"]
    diffs = {k: float(got[k] - CANONICAL[k]) for k in CANONICAL}
    gate = {
        "canonical_reference": CANONICAL,
        "recomputed": {k: float(got[k]) for k in CANONICAL},
        "differences": diffs,
        "tolerance": 1e-6,
        "pass": all(abs(v) <= 1e-6 for v in diffs.values()),
    }
    (OUT / "PARITY_149.json").write_text(json.dumps(gate, indent=2) + "\n")
    print("PARITY_149", json.dumps(gate, indent=2), flush=True)
    if not gate["pass"]:
        raise RuntimeError("149 full-universe parity gate failed; refusing 70 comparison")

    print("RUN_70_SAME_SOURCE", flush=True)
    res70 = run_one("holdout70", u70, FROZEN70 / "raw_ticker_csv")

    m149 = res149["v2_full_universe"]
    m70 = res70["v2_full_universe"]
    comparison = {
        "status": "V2_SAME_SOURCE_149_VS_70_COMPLETE",
        "source_contract": "same imported V2 modeling/replay functions from europe120/eu120_retrain/run_eu120_retrain.py; same execution path; separate model/cache directories; only frozen universe/data differ",
        "parity_149": gate,
        "original149": res149,
        "holdout70": res70,
        "delta_70_minus_149": {
            "cagr_pp": float((m70["cagr"] - m149["cagr"]) * 100),
            "maxdd_pp": float((m70["maxdd"] - m149["maxdd"]) * 100),
            "sharpe": float(m70["sharpe"] - m149["sharpe"]),
        },
    }
    (OUT / "COMPARISON.json").write_text(json.dumps(comparison, indent=2) + "\n")
    print("FINAL_COMPARISON", json.dumps(comparison, indent=2), flush=True)


if __name__ == "__main__":
    main()
