#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
ETF = REPO / "vendor" / "etf_trader_v2"
SRC = ETF / "src"
sys.path.insert(0, str(SRC))

from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.ma3 import producer, ddfirst, v6
from etf_trader.ma3.ensemble import fit_ensemble_producer

sp = importlib.util.spec_from_file_location("stage19", REPO / "vendor" / "p45" / "v2_stage19_kernel.py")
stage19 = importlib.util.module_from_spec(sp)
sp.loader.exec_module(stage19)

RAW = Path(os.environ["FROZEN_149_ROOT"]).resolve() / "etf_trader_raw"
OUT = ROOT / "canonical149_probe"
TIT_OUT = OUT / "titanium"
MA3_OUT = OUT / "ma3_panel"
EXPECTED = {
    "titanium_sha256": "8ec29dd155583b3721fd760fcec9bfbbe43cf96f79e79dd6fd034d478e411dcc",
    "predictions_sha256": "5caf2d1047234e854ff484d5794e421fe1dd6b5283ccde202907a3f0769ab238",
    "cagr": 0.4314595242029944,
    "maxdd": -0.2503576476357465,
    "sharpe": 1.3635086089607882,
    "sessions": 2366,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run(cmd: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run(cmd, cwd=ETF, env=env, check=True)


def replay_full_universe(pred: pd.DataFrame, tit: pd.DataFrame, mats: dict[str, pd.DataFrame], tickers: list[str]):
    ti = {t: i for i, t in enumerate(tickers)}
    for req in ("BIL", "SHV"):
        if req not in ti:
            raise RuntimeError(f"{req} missing")

    cal = tit[["signal_date", "entry_date", "exit_date"]].drop_duplicates().sort_values("signal_date").reset_index(drop=True)
    last_raw = {t: mats["Close"][t].last_valid_index() for t in tickers}
    cutoff = min(last_raw.values())
    cal = cal[cal.exit_date.le(cutoff)].copy().reset_index(drop=True)
    if cal.empty:
        raise RuntimeError("empty completed calendar")

    p = pred.rename(columns={"ET_TAIL": "ET_RANK", "XGB_TAIL": "XGB_RANK"}).copy()
    score = stage19.score_matrix(p, cal, tickers)
    pm = stage19.pred_matrices(p, cal, tickers)

    Odf = mats["Open"].reindex(columns=tickers).ffill().bfill()
    Ldf = mats["Low"].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)
    Cdf = mats["Close"].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)
    start = pd.Timestamp(cal.entry_date.min())
    end = pd.Timestamp(cal.exit_date.max())
    Odf = Odf.loc[:end]
    Ldf = Ldf.reindex(Odf.index)
    Cdf = Cdf.reindex(Odf.index)
    st, en = int(Odf.index.get_loc(start)), int(Odf.index.get_loc(end))
    ds = Odf.index[st:en + 1]

    BM = np.arange(len(tickers), dtype=np.int32)[None, :]
    BOK = np.ones_like(BM, dtype=bool)
    alloc = producer.allocations_from_score(score, cal, ds, BM, BOK, continuous=True)

    gross = np.asarray(ddfirst.sync_c95_m75_gross(Cdf)[st:en + 1], float)
    full_ex = ddfirst.daily_execution_inputs(Odf, Ldf, Cdf)
    ex = {k: v[st:en + 1] for k, v in full_ex.items()}
    g = stage19.risk_gross_transform(gross)
    s6 = v6.build_v6_state(Cdf.loc[ds, tickers], alloc.d1, alloc.d2, alloc.weight1, gross)

    agreement = np.zeros_like(alloc.d1, bool)
    for m, row in enumerate(cal.itertuples(index=False)):
        a = int(ds.searchsorted(pd.Timestamp(row.entry_date)))
        e = int(ds.searchsorted(pd.Timestamp(row.exit_date)))
        if e <= a or a >= len(ds):
            continue
        x, y = alloc.d1[:, a], alloc.d2[:, a]
        agreement[:, a:e] = ((pm["ET_RANK"][m, x] > pm["ET_RANK"][m, y]) &
                              (pm["XGB_RANK"][m, x] > pm["XGB_RANK"][m, y]))[:, None]

    weights = stage19.confidence_weights(
        alloc, g, agreement, np.zeros_like(agreement), mode="current_plus_models_riskoff"
    )
    G = np.tile(g, (1, 1))
    O, L, C, PC, gap, ud1, uneg, UH, SA = [ex[k] for k in ("O", "L", "C", "PC", "gap", "ud1", "uneg", "UH", "SA")]
    E, T, X, AW = stage19.simulate_arch(
        alloc.d1, alloc.d2, weights, O, L, C, PC, gap, ud1, uneg, UH, SA,
        ti["BIL"], ti["SHV"], G, g, s6.alt_idx, True, .001
    )
    mask = np.ones(len(ds), dtype=bool)
    met = stage19.metrics(E, mask)
    return met, E, T, ds, cal, alloc


def main() -> None:
    import shutil
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    run([
        sys.executable, str(ETF / "scripts" / "build_tit_r_source_only.py"),
        "--data", str(RAW), "--output", str(TIT_OUT),
        "--xgb-workers", "3", "--xgb-threads-per-worker", "1",
    ])
    tit_path = TIT_OUT / "TIT_R_SOURCE_ONLY.csv"
    tit_hash = sha256(tit_path)
    print("TITANIUM_SHA256", tit_hash, flush=True)

    run([
        sys.executable, str(ETF / "scripts" / "build_ma3_panel_source_only.py"),
        "--data", str(RAW), "--cluster-data", str(RAW), "--output", str(MA3_OUT),
    ])

    mats, cats, _ = load_ticker_csv_folder(RAW)
    tickers = list(map(str, mats["Open"].columns))
    tit = pd.read_csv(tit_path, parse_dates=["signal_date", "entry_date", "exit_date"])
    panel = pd.read_pickle(MA3_OUT / "RAW_FEATURE_PANEL.pkl")
    fit = fit_ensemble_producer(panel, tit, tickers, n_jobs=2)
    pred_path = OUT / "ENSEMBLE_TAIL_OOS.csv"
    fit.predictions.to_csv(pred_path, index=False)
    fit.fit_audit.to_csv(OUT / "ENSEMBLE_FIT_AUDIT.csv", index=False)
    pred_hash = sha256(pred_path)
    print("PREDICTIONS_SHA256", pred_hash, flush=True)

    met, E, T, ds, cal, alloc = replay_full_universe(fit.predictions, tit, mats, tickers)
    np.savez_compressed(OUT / "FULL_UNIVERSE_PATH.npz", dates=ds.values, equity=E, turnover=T,
                        d1=alloc.d1, d2=alloc.d2, weight1=alloc.weight1, margin=alloc.margin)

    got = {
        "titanium_sha256": tit_hash,
        "predictions_sha256": pred_hash,
        "sessions": int(len(ds)),
        "start": str(ds.min().date()),
        "end": str(ds.max().date()),
        "cagr": float(met["cagr"]),
        "maxdd": float(met["maxdd"]),
        "sharpe": float(met["sharpe"]),
        "annualized_turnover": float(T.mean() * 252),
        "completed_signals": int(len(cal)),
    }
    parity = {
        "expected": EXPECTED,
        "got": got,
        "hash_titanium_match": tit_hash == EXPECTED["titanium_sha256"],
        "hash_predictions_match": pred_hash == EXPECTED["predictions_sha256"],
        "metric_differences": {k: got[k] - EXPECTED[k] for k in ("cagr", "maxdd", "sharpe")},
        "sessions_match": got["sessions"] == EXPECTED["sessions"],
    }
    parity["pass_metrics"] = parity["sessions_match"] and all(abs(v) <= 1e-6 for v in parity["metric_differences"].values())
    parity["pass_strict"] = parity["pass_metrics"] and parity["hash_titanium_match"] and parity["hash_predictions_match"]
    (OUT / "PARITY.json").write_text(json.dumps(parity, indent=2) + "\n")
    print(json.dumps(parity, indent=2), flush=True)
    if not parity["pass_metrics"]:
        raise RuntimeError("canonical 149 metric parity failed")


if __name__ == "__main__":
    main()