#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ETF = REPO / "vendor" / "etf_trader_v2"
SRC = ETF / "src"
sys.path.insert(0, str(SRC))

from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.ma3 import producer, ddfirst, v6
from etf_trader.ma3.ensemble import fit_ensemble_producer

sp = importlib.util.spec_from_file_location("stage19", REPO / "vendor" / "p45" / "v2_stage19_kernel.py")
stage19 = importlib.util.module_from_spec(sp)
sp.loader.exec_module(stage19)

FROZEN149 = Path(os.environ["FROZEN_149_ROOT"]).resolve() / "etf_trader_raw"
FROZEN70 = Path(os.environ["FROZEN_HOLDOUT70_ROOT"]).resolve() / "raw_ticker_csv"
OUT = HERE / "canonical_same_source_results"
INFRA = ["SPY", "HYG", "IEF", "BIL", "SHV"]
CANONICAL149 = {
    "cagr": 0.4314595242029944,
    "maxdd": -0.2503576476357465,
    "sharpe": 1.3635086089607882,
    "sessions": 2366,
    "titanium_sha256": "8ec29dd155583b3721fd760fcec9bfbbe43cf96f79e79dd6fd034d478e411dcc",
    "predictions_sha256": "5caf2d1047234e854ff484d5794e421fe1dd6b5283ccde202907a3f0769ab238",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for b in iter(lambda: fp.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def run(cmd: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run(cmd, cwd=ETF, env=env, check=True)


def load_universe(raw: Path) -> pd.DataFrame:
    u = pd.read_csv(raw / "universe.csv")[["ticker", "macro_category"]].copy()
    u["ticker"] = u.ticker.astype(str).str.upper()
    return u.drop_duplicates("ticker").reset_index(drop=True)


def prepare_candidate_and_titanium_raw(name: str, source: Path) -> tuple[Path, Path, list[str]]:
    """Prepare one candidate folder and one Titanium input folder.

    The candidate folder contains only the economic universe.  The Titanium
    input is identical except that missing canonical infrastructure references
    are appended.  Those references are never eligible for top1/top2, MA3
    membership, or V6 alternate selection.  This is the same infrastructure
    contract used by the historical disjoint Holdout100 audit.
    """
    base = OUT / name
    candidate = base / "candidate_raw"
    titanium_raw = base / "titanium_raw"
    candidate.mkdir(parents=True, exist_ok=True)
    titanium_raw.mkdir(parents=True, exist_ok=True)

    u = load_universe(source)
    tickers = u.ticker.tolist()
    u149 = load_universe(FROZEN149).set_index("ticker")

    u.to_csv(candidate / "universe.csv", index=False)
    for t in tickers:
        shutil.copyfile(source / f"{t}.csv", candidate / f"{t}.csv")

    tu = u.copy()
    missing_refs = [t for t in INFRA if t not in set(tickers)]
    if missing_refs:
        refs = u149.loc[missing_refs].reset_index()[["ticker", "macro_category"]]
        tu = pd.concat([tu, refs], ignore_index=True)
    tu = tu.drop_duplicates("ticker").reset_index(drop=True)
    tu.to_csv(titanium_raw / "universe.csv", index=False)
    for t in tu.ticker:
        src = source / f"{t}.csv" if t in set(tickers) else FROZEN149 / f"{t}.csv"
        shutil.copyfile(src, titanium_raw / f"{t}.csv")

    contract = {
        "candidate_count": len(tickers),
        "candidate_tickers": tickers,
        "infrastructure_refs": INFRA,
        "refs_added_for_titanium_only": missing_refs,
        "infrastructure_selectable_top1_top2": False,
        "infrastructure_selectable_v6_alternate": False,
    }
    (base / "INPUT_CONTRACT.json").write_text(json.dumps(contract, indent=2) + "\n")
    return candidate, titanium_raw, tickers


def build_source_only_state(name: str, source: Path):
    base = OUT / name
    candidate, titanium_raw, candidate_tickers = prepare_candidate_and_titanium_raw(name, source)
    tit_out = base / "titanium"
    ma3_out = base / "ma3_panel"

    run([
        sys.executable, str(ETF / "scripts" / "build_tit_r_source_only.py"),
        "--data", str(titanium_raw), "--output", str(tit_out),
        "--xgb-workers", "3", "--xgb-threads-per-worker", "1",
    ])
    tit_full = pd.read_csv(tit_out / "TIT_R_SOURCE_ONLY.csv", parse_dates=["signal_date", "entry_date", "exit_date"])
    tit = tit_full[tit_full.ticker.astype(str).isin(candidate_tickers)].copy()
    if tit.ticker.nunique() != len(candidate_tickers):
        raise RuntimeError(f"{name}: Titanium candidate coverage incomplete")
    tit_path = base / "TIT_R_CANDIDATES_ONLY.csv"
    tit.to_csv(tit_path, index=False)

    # MA3 features, clustering, targets and all investable state are built only
    # on economic candidates; infrastructure references cannot enter selection.
    run([
        sys.executable, str(ETF / "scripts" / "build_ma3_panel_source_only.py"),
        "--data", str(candidate), "--cluster-data", str(candidate),
        "--output", str(ma3_out),
    ])
    panel = pd.read_pickle(ma3_out / "RAW_FEATURE_PANEL.pkl")
    fit = fit_ensemble_producer(panel, tit, candidate_tickers, n_jobs=2)
    if not bool(fit.fit_audit["maturity_ok"].all()):
        raise RuntimeError(f"{name}: hybrid maturity audit failed")
    pred_path = base / "ENSEMBLE_TAIL_OOS.csv"
    fit.predictions.to_csv(pred_path, index=False)
    fit.fit_audit.to_csv(base / "ENSEMBLE_FIT_AUDIT.csv", index=False)

    return {
        "base": base,
        "candidate_raw": candidate,
        "titanium_raw": titanium_raw,
        "candidate_tickers": candidate_tickers,
        "tit": tit,
        "tit_full_path": tit_out / "TIT_R_SOURCE_ONLY.csv",
        "tit_candidate_path": tit_path,
        "pred": fit.predictions,
        "pred_path": pred_path,
        "ma3_panel_path": ma3_out / "RAW_FEATURE_PANEL.pkl",
    }


def append_execution_refs(candidate_mats: dict[str, pd.DataFrame], candidate_tickers: list[str]):
    ref_mats, _, _ = load_ticker_csv_folder(FROZEN149)
    exec_tickers = list(candidate_tickers)
    for t in ("BIL", "SHV"):
        if t not in exec_tickers:
            exec_tickers.append(t)
    mats = {}
    for field in ("Open", "High", "Low", "Close", "Volume"):
        parts = []
        for t in exec_tickers:
            if t in candidate_mats[field].columns:
                parts.append(candidate_mats[field][t].rename(t))
            else:
                parts.append(ref_mats[field][t].rename(t))
        mats[field] = pd.concat(parts, axis=1).sort_index()
    return mats, exec_tickers


def replay_full_universe(state: dict) -> dict:
    candidate, tickers = state["candidate_raw"], state["candidate_tickers"]
    cand_mats, _, _ = load_ticker_csv_folder(candidate)
    exec_mats, exec_tickers = append_execution_refs(cand_mats, tickers)
    ti = {t: i for i, t in enumerate(exec_tickers)}

    tit = state["tit"]
    cal = tit[["signal_date", "entry_date", "exit_date"]].drop_duplicates().sort_values("signal_date").reset_index(drop=True)
    last_raw = {t: cand_mats["Close"][t].last_valid_index() for t in tickers}
    cutoff = min(last_raw.values())
    cal = cal[cal.exit_date.le(cutoff)].copy().reset_index(drop=True)
    if cal.empty:
        raise RuntimeError("no complete holding periods")

    p = state["pred"].rename(columns={"ET_TAIL": "ET_RANK", "XGB_TAIL": "XGB_RANK"}).copy()
    score = stage19.score_matrix(p, cal, tickers)
    pm = stage19.pred_matrices(p, cal, tickers)

    Odf = exec_mats["Open"].reindex(columns=exec_tickers).ffill().bfill()
    Ldf = exec_mats["Low"].reindex(columns=exec_tickers).ffill().bfill().reindex(Odf.index)
    Cdf = exec_mats["Close"].reindex(columns=exec_tickers).ffill().bfill().reindex(Odf.index)
    start, end = pd.Timestamp(cal.entry_date.min()), pd.Timestamp(cal.exit_date.max())
    Odf = Odf.loc[:end]; Ldf = Ldf.reindex(Odf.index); Cdf = Cdf.reindex(Odf.index)
    st, en = int(Odf.index.get_loc(start)), int(Odf.index.get_loc(end))
    ds = Odf.index[st:en + 1]

    # One basket = the complete candidate universe. Infrastructure refs are not
    # included in BM/BOK and therefore cannot become top1/top2.
    BM = np.arange(len(tickers), dtype=np.int32)[None, :]
    BOK = np.ones_like(BM, dtype=bool)
    alloc = producer.allocations_from_score(score, cal, ds, BM, BOK, continuous=True)
    if int(alloc.d1.max()) >= len(tickers) or int(alloc.d2.max()) >= len(tickers):
        raise RuntimeError("infrastructure leaked into top1/top2 allocation")

    cand_close = Cdf[tickers]
    gross = np.asarray(ddfirst.sync_c95_m75_gross(cand_close)[st:en + 1], float)
    g = stage19.risk_gross_transform(gross)
    # Build V6 state strictly from candidates, so its alternate index is also
    # restricted to the economic universe.
    s6 = v6.build_v6_state(cand_close.loc[ds], alloc.d1, alloc.d2, alloc.weight1, gross)
    if np.any((s6.alt_idx >= len(tickers)) & (s6.alt_idx >= 0)):
        raise RuntimeError("infrastructure leaked into V6 alternate selection")

    ex_full = ddfirst.daily_execution_inputs(Odf, Ldf, Cdf)
    ex = {k: v[st:en + 1] for k, v in ex_full.items()}
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
    E, T, _, AW = stage19.simulate_arch(
        alloc.d1, alloc.d2, weights, O, L, C, PC, gap, ud1, uneg, UH, SA,
        ti["BIL"], ti["SHV"], G, g, s6.alt_idx, True, .001
    )
    mask = np.ones(len(ds), dtype=bool)
    met = stage19.metrics(E, mask)

    # Passive benchmark: static equal-weight buy-and-hold of economic candidates.
    bh_close = cand_mats["Close"].reindex(ds)[tickers].ffill().bfill()
    bh = (bh_close / bh_close.iloc[0]).mean(axis=1).to_numpy(float)[None, :]
    bh_met = stage19.metrics(bh, mask)

    np.savez_compressed(state["base"] / "FULL_UNIVERSE_PATH.npz", dates=ds.values,
                        equity=E, turnover=T, d1=alloc.d1, d2=alloc.d2,
                        weight1=weights, margin=alloc.margin, alt_idx=s6.alt_idx)
    top1 = [tickers[int(i)] for i in alloc.d1[0]]
    top2 = [tickers[int(i)] for i in alloc.d2[0]]
    pd.DataFrame({"date": ds, "top1": top1, "top2": top2}).to_csv(state["base"] / "DAILY_LEADERS.csv", index=False)

    result = {
        "candidate_count": len(tickers),
        "sessions": int(len(ds)),
        "start": str(ds.min().date()),
        "end": str(ds.max().date()),
        "completed_signals": int(len(cal)),
        "v2_full_universe": {
            "cagr": float(met["cagr"]),
            "maxdd": float(met["maxdd"]),
            "sharpe": float(met["sharpe"]),
            "terminal_equity": float(E[0, -1]),
            "annualized_turnover": float(T.mean() * 252),
            "mean_risky_gross": float(g.mean()),
        },
        "equal_weight_buy_hold": {
            "cagr": float(bh_met["cagr"]),
            "maxdd": float(bh_met["maxdd"]),
            "sharpe": float(bh_met["sharpe"]),
            "terminal_equity": float(bh[0, -1]),
        },
        "source_only": {
            "titanium_full_sha256": sha256(state["tit_full_path"]),
            "titanium_candidates_sha256": sha256(state["tit_candidate_path"]),
            "predictions_sha256": sha256(state["pred_path"]),
            "ma3_panel_sha256": sha256(state["ma3_panel_path"]),
            "historical_scores_consumed": False,
            "historical_paths_consumed": False,
        },
    }
    (state["base"] / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    u149, u70 = load_universe(FROZEN149), load_universe(FROZEN70)
    if len(u149) != 149 or len(u70) != 70:
        raise RuntimeError("unexpected frozen universe size")
    if set(u149.ticker) & set(u70.ticker):
        raise RuntimeError("holdout70 overlaps original149")

    print("=== ORIGINAL149 CANONICAL SOURCE-ONLY ===", flush=True)
    s149 = build_source_only_state("original149", FROZEN149)
    r149 = replay_full_universe(s149)
    m149 = r149["v2_full_universe"]
    diffs = {k: float(m149[k] - CANONICAL149[k]) for k in ("cagr", "maxdd", "sharpe")}
    gate = {
        "expected": CANONICAL149,
        "got": {
            "cagr": m149["cagr"], "maxdd": m149["maxdd"], "sharpe": m149["sharpe"],
            "sessions": r149["sessions"],
            "titanium_sha256": r149["source_only"]["titanium_full_sha256"],
            "predictions_sha256": r149["source_only"]["predictions_sha256"],
        },
        "metric_differences": diffs,
        "sessions_match": r149["sessions"] == CANONICAL149["sessions"],
        "titanium_hash_match": r149["source_only"]["titanium_full_sha256"] == CANONICAL149["titanium_sha256"],
        "predictions_hash_match": r149["source_only"]["predictions_sha256"] == CANONICAL149["predictions_sha256"],
    }
    gate["pass"] = gate["sessions_match"] and all(abs(v) <= 1e-6 for v in diffs.values())
    (OUT / "PARITY_149.json").write_text(json.dumps(gate, indent=2) + "\n")
    print("PARITY_149", json.dumps(gate, indent=2), flush=True)
    if not gate["pass"]:
        raise RuntimeError("149 canonical parity failed; refusing holdout70 comparison")

    print("=== HOLDOUT70 SAME CANONICAL SOURCE ===", flush=True)
    s70 = build_source_only_state("holdout70", FROZEN70)
    r70 = replay_full_universe(s70)
    m70 = r70["v2_full_universe"]
    comparison = {
        "status": "CANONICAL_SAME_SOURCE_149_VS_70_COMPLETE",
        "period_contract": "completed V2 periods through 2026-07-01",
        "source_contract": "identical canonical Titanium/Hybrid/Stage19 sources; same costs and execution; only economic candidate universe/data differ; missing benchmark/cash references are infrastructure-only and nonselectable",
        "parity_149": gate,
        "original149": r149,
        "holdout70": r70,
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
