#!/usr/bin/env python3
"""Clean source-only rebuild of the MA3 ensemble + High-CAGR24 candidate.

The productive DAG is restricted to raw ETF OHLCV, universe/category metadata,
and repository source. Canonical 500x24 baskets are regenerated deterministically
from universe metadata; historical basket membership, dynamic cluster membership,
scores, paths, models, and checkpoint metrics are not consumed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.source_only.baskets import build_canonical_baskets, BASKET_SEED
from etf_trader.ma3 import producer, ddfirst, v6, highcagr24
from etf_trader.ma3.ensemble import fit_ensemble_producer, ET_KW, XGB_KW, XGB_ALPHA

CANONICAL_BASKET_SHA256 = "36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def aggregate_sha256(paths: list[Path], base: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(paths, key=lambda p: str(p.relative_to(base)).lower()):
        rel = str(path.relative_to(base)).replace("\\", "/")
        h.update(rel.encode("utf-8")); h.update(b"\0")
        h.update(sha256(path).encode("ascii")); h.update(b"\n")
    return h.hexdigest()


def run(cmd: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def environment_identity() -> dict[str, str]:
    packages = {}
    for name in ("numpy", "pandas", "scikit-learn", "xgboost", "numba", "pyarrow"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "NOT_INSTALLED"
    return {"python": platform.python_version(), **packages}


def metrics(equity: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    lr = np.diff(np.log(np.column_stack([np.ones(equity.shape[0]), equity])), axis=1)[:, mask]
    r = np.expm1(lr)
    n = lr.shape[1]
    cagr = np.expm1(lr.sum(axis=1) * 252 / n)
    eq = np.exp(np.cumsum(lr, axis=1))
    peak = np.maximum.accumulate(np.column_stack([np.ones(equity.shape[0]), eq]), axis=1)[:, 1:]
    dd = (eq / peak - 1).min(axis=1)
    sd = r.std(axis=1, ddof=1)
    sharpe = np.divide(r.mean(axis=1) * np.sqrt(252), sd, out=np.zeros_like(sd), where=sd > 0)
    return {
        "cagr": float(cagr.mean()),
        "median_cagr": float(np.median(cagr)),
        "p10_cagr": float(np.quantile(cagr, .10)),
        "p05_cagr": float(np.quantile(cagr, .05)),
        "maxdd": float(dd.mean()),
        "p10dd": float(np.quantile(dd, .10)),
        "p05dd": float(np.quantile(dd, .05)),
        "worst": float(dd.min()),
        "sharpe": float(sharpe.mean()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--raw", help="prepared universe.csv + per-ticker OHLCV CSV directory")
    src.add_argument("--matrix-dir", help="OPEN/HIGH/LOW/CLOSE/VOLUME parquet directory")
    ap.add_argument("--universe", default="data/ETF_UNIVERSE.csv",
                    help="universe/category metadata used with --matrix-dir")
    ap.add_argument("--output", default="artifact/ma3_highcagr24_ensemble_source_only")
    ap.add_argument("--n-jobs", type=int, default=2)
    ap.add_argument("--xgb-workers", type=int, default=3)
    ap.add_argument("--xgb-threads-per-worker", type=int, default=1)
    args = ap.parse_args()

    out = Path(args.output)
    if not out.is_absolute():
        out = ROOT / out
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"output is non-empty: {out}; clean-room run requires an empty directory")
    out.mkdir(parents=True, exist_ok=True)

    if args.matrix_dir:
        raw = out / "raw_ticker_csv"
        universe = Path(args.universe)
        if not universe.is_absolute():
            universe = (ROOT / universe).resolve()
        run([
            sys.executable, str(ROOT / "scripts/prepare_matrix_raw_to_ticker_csv.py"),
            "--matrix-dir", str(Path(args.matrix_dir).resolve()),
            "--universe", str(universe),
            "--output", str(raw),
        ])
        matrix_files = [Path(args.matrix_dir).resolve() / f"{x}.parquet" for x in ("OPEN", "HIGH", "LOW", "CLOSE", "VOLUME")]
        raw_identity = {
            "mode": "matrix_parquet",
            "files": {p.name: sha256(p) for p in matrix_files},
            "universe_sha256": sha256(universe),
        }
    else:
        raw = Path(args.raw).resolve()
        files = sorted(raw.glob("*.csv"))
        raw_identity = {
            "mode": "ticker_csv",
            "file_count": len(files),
            "aggregate_sha256": aggregate_sha256(files, raw),
        }

    mats, cats, raw_manifest = load_ticker_csv_folder(raw)
    tickers = list(map(str, mats["Open"].columns))
    ti = {t: i for i, t in enumerate(tickers)}
    for required in ("SPY", "BIL", "SHV"):
        if required not in ti:
            raise RuntimeError(f"{required} missing from raw universe")

    # Canonical baskets are generated from source logic, not loaded from membership history.
    universe_meta = pd.read_csv(raw / "universe.csv")
    membership = build_canonical_baskets(universe_meta, tickers)
    basket_path = out / "GENERATED_CANONICAL_BASKETS.csv"
    membership.to_csv(basket_path, index=False)
    basket_sha = sha256(basket_path)
    if basket_sha != CANONICAL_BASKET_SHA256:
        raise RuntimeError(f"basket reconstruction parity failed: {basket_sha}")

    # Fresh upstream DAG inside this run.
    tit = out / "titanium"
    panel_dir = out / "ma3_panel"
    run([
        sys.executable, str(ROOT / "scripts/build_tit_r_source_only.py"),
        "--data", str(raw), "--output", str(tit),
        "--xgb-workers", str(args.xgb_workers),
        "--xgb-threads-per-worker", str(args.xgb_threads_per_worker),
    ])
    run([
        sys.executable, str(ROOT / "scripts/build_ma3_panel_source_only.py"),
        "--data", str(raw), "--cluster-data", str(raw), "--output", str(panel_dir),
    ])

    # Explicit causal audits of freshly generated upstream state.
    titanium_audit_records = 0
    titanium_maturity_safe = True
    for path in sorted((tit / "annual_models").glob("fit_audit_*.json")):
        for row in json.loads(path.read_text(encoding="utf-8")):
            titanium_audit_records += 1
            titanium_maturity_safe &= pd.Timestamp(row["max_exit"]) < pd.Timestamp(row["fit_date"])
    cluster_audit = pd.read_csv(panel_dir / "CLUSTER_SOURCE_DATE_AUDIT.csv")
    cluster_source_causal = bool(
        (pd.to_datetime(cluster_audit["window_end"]) <= pd.to_datetime(cluster_audit["signal_date"])).all()
        and cluster_audit["max_source_date_le_signal"].all()
        and cluster_audit["matching_used_only_previous_membership"].all()
    )
    if not titanium_maturity_safe or not cluster_source_causal:
        raise RuntimeError("fresh upstream causal audit failed")

    tit_df = pd.read_csv(tit / "TIT_R_SOURCE_ONLY.csv", parse_dates=["signal_date", "entry_date", "exit_date"])
    panel = pd.read_pickle(panel_dir / "RAW_FEATURE_PANEL.pkl")
    t0 = time.time()
    p = fit_ensemble_producer(panel, tit_df, tickers, n_jobs=args.n_jobs)
    fit_seconds = time.time() - t0
    if not bool(p.fit_audit["maturity_ok"].all()):
        raise RuntimeError("ensemble maturity audit failed")
    p.predictions.to_csv(out / "ENSEMBLE_TAIL_OOS.csv", index=False)
    p.fit_audit.to_csv(out / "ENSEMBLE_FIT_AUDIT.csv", index=False)

    BM, BOK = producer.basket_arrays(membership, tickers, n_baskets=500)
    Odf = mats["Open"].reindex(columns=tickers).ffill().bfill()
    Ldf = mats["Low"].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)
    Cdf = mats["Close"].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)

    end = pd.Timestamp(p.calendar["exit_date"].max())
    start = pd.Timestamp(p.calendar["entry_date"].min())
    Odf = Odf.loc[:end]; Ldf = Ldf.reindex(Odf.index); Cdf = Cdf.reindex(Odf.index)
    st = int(Odf.index.get_loc(start)); en = int(Odf.index.get_loc(end)); ds = Odf.index[st:en + 1]

    gross = np.asarray(ddfirst.sync_c95_m75_gross(Cdf)[st:en + 1], dtype=float)
    ex = ddfirst.daily_execution_inputs(Odf, Ldf, Cdf)
    O, L, C, PC, gap, ud1, uneg, UH, SA = [ex[k][st:en + 1] for k in ("O", "L", "C", "PC", "gap", "ud1", "uneg", "UH", "SA")]
    alloc = producer.allocations_from_score(p.score, p.calendar, ds, BM, BOK, continuous=True)
    noalt = np.full_like(alloc.d1, -1, np.int16)
    ones = np.ones(len(ds), dtype=float)

    Eraw, Traw, _, _ = v6.simulate_with_alt(
        alloc.d1, alloc.d2, alloc.weight1, O, L, C, PC, gap, ud1, uneg, UH, SA,
        ti["BIL"], ti["SHV"], ones, noalt, False, .001,
    )
    s6 = v6.build_v6_state(Cdf.loc[ds, tickers], alloc.d1, alloc.d2, alloc.weight1, gross)
    Edd, Tdd, _, _ = v6.simulate_with_alt(
        alloc.d1, alloc.d2, alloc.weight1, O, L, C, PC, gap, ud1, uneg, UH, SA,
        ti["BIL"], ti["SHV"], gross, noalt, False, .001,
    )
    Ev6, Tv6, _, _ = v6.simulate_with_alt(
        alloc.d1, alloc.d2, alloc.weight1, O, L, C, PC, gap, ud1, uneg, UH, SA,
        ti["BIL"], ti["SHV"], gross, s6.alt_idx, True, .001,
    )
    gross24, weight24 = highcagr24.apply_highcagr24(gross, alloc.weight1, alloc.margin)
    E24, T24, X24, Aw24 = v6.simulate_with_alt(
        alloc.d1, alloc.d2, weight24, O, L, C, PC, gap, ud1, uneg, UH, SA,
        ti["BIL"], ti["SHV"], gross24, s6.alt_idx, True, .001,
    )

    periods = {
        "pre2020": ds < pd.Timestamp("2020-01-01"),
        "2020_2022": (ds >= pd.Timestamp("2020-01-01")) & (ds < pd.Timestamp("2023-01-01")),
        "dev_daily": ds < pd.Timestamp("2023-01-01"),
        "holdout_daily": ds >= pd.Timestamp("2023-01-01"),
        "full": np.ones(len(ds), dtype=bool),
    }
    result = {
        "status": "SOURCE_ONLY_ENSEMBLE_REBUILD_COMPLETE",
        "certification": "CLEAN_CURRENT_RAW_PASS",
        "selection": {
            "extra_trees": "configuration selected on 2011-2016 walk-forward",
            "xgb": "configuration selected on 2011-2016 engine benchmark",
            "alpha_xgb": {"value": XGB_ALPHA, "selected_on": "2017-2022 validation only"},
            "holdout": "2023-2026 not used for parameter selection",
        },
        "producer": {
            "target": "0.45*r21^1.5 + 0.35*r42^1.5 + 0.20*r63^1.5",
            "extra_trees": ET_KW,
            "xgb": XGB_KW,
            "alpha_xgb": XGB_ALPHA,
            "tail_smoothing": [0.40, 0.30, 0.30],
            "tail_power": 1.10,
            "base_tail": [0.475, 0.525],
        },
        "fit_seconds": fit_seconds,
        "calendar": {"start": str(ds.min().date()), "end": str(ds.max().date()), "days": int(len(ds))},
        "metrics": {},
        "turnover_ann": {
            "raw": float(Traw.mean() * 252),
            "ddfirst": float(Tdd.mean() * 252),
            "v6": float(Tv6.mean() * 252),
            "highcagr24": float(T24.mean() * 252),
        },
        "contract": {
            "productive_inputs": ["raw ETF OHLCV", "universe/category metadata", "repository source"],
            "historical_scores_consumed": False,
            "historical_paths_consumed": False,
            "historical_cluster_membership_consumed": False,
            "historical_basket_membership_consumed": False,
            "basket_membership_generated_from_source": True,
            "basket_seed": BASKET_SEED,
            "basket_sha256": basket_sha,
            "cluster_seed": 26072026,
            "titanium_maturity_safe": bool(titanium_maturity_safe),
            "titanium_audit_records": titanium_audit_records,
            "cluster_source_causal": bool(cluster_source_causal),
            "ensemble_maturity_safe": bool(p.fit_audit["maturity_ok"].all()),
        },
        "raw_identity": raw_identity,
        "raw_manifest": raw_manifest,
        "environment": environment_identity(),
    }
    for name, mask in periods.items():
        result["metrics"][name] = {
            "raw": metrics(Eraw, mask),
            "ddfirst": metrics(Edd, mask),
            "v6": metrics(Ev6, mask),
            "highcagr24": metrics(E24, mask),
        }

    (out / "RESULT.json").write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    np.savez_compressed(
        out / "PATH.npz",
        dates=ds.values, equity=E24, turnover=T24, exposure=X24, alt_weight=Aw24,
        d1=alloc.d1, d2=alloc.d2, wg=weight24, margin=alloc.margin,
        global_gross=gross24, alt_idx=s6.alt_idx, tickers=np.asarray(tickers, dtype=object),
    )
    print(json.dumps({
        "status": result["status"],
        "full_highcagr24": result["metrics"]["full"]["highcagr24"],
        "holdout_highcagr24": result["metrics"]["holdout_daily"]["highcagr24"],
        "turnover_ann": result["turnover_ann"]["highcagr24"],
        "contract": result["contract"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
