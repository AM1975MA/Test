#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
os.environ["FROZEN_149_ROOT"] = os.environ["FRESH_149_ROOT"]
os.environ["FROZEN_HOLDOUT70_ROOT"] = os.environ["FRESH_70_ROOT"]

spec = importlib.util.spec_from_file_location(
    "canonical_compare", HERE / "v2_canonical_same_source_compare.py"
)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

c.FROZEN149 = Path(os.environ["FRESH_149_ROOT"]).resolve() / "etf_trader_raw"
c.FROZEN70 = Path(os.environ["FRESH_70_ROOT"]).resolve() / "raw_ticker_csv"
c.OUT = HERE / "fresh_same_source_results"
CHECKPOINT = Path(os.environ["CHECKPOINT_ROOT"]).resolve()
PARTIAL149 = Path(os.environ["PARTIAL149_ROOT"]).resolve()


def restore_holdout_state() -> dict:
    base = c.OUT / "holdout70"
    candidate, titanium_raw, tickers = c.prepare_candidate_and_titanium_raw(
        "holdout70", c.FROZEN70
    )
    src = CHECKPOINT / "holdout70"
    required = [
        "TIT_R_CANDIDATES_ONLY.csv",
        "titanium/TIT_R_SOURCE_ONLY.csv",
        "ma3_panel/RAW_FEATURE_PANEL.pkl",
        "ENSEMBLE_TAIL_OOS.csv",
        "ENSEMBLE_FIT_AUDIT.csv",
    ]
    for rel in required:
        if not (src / rel).exists():
            raise RuntimeError(f"checkpoint missing {rel}")
        dst = base / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src / rel, dst)

    tit = pd.read_csv(
        base / "TIT_R_CANDIDATES_ONLY.csv",
        parse_dates=["signal_date", "entry_date", "exit_date"],
    )
    pred = pd.read_csv(base / "ENSEMBLE_TAIL_OOS.csv")
    if "signal_date" in pred.columns:
        pred["signal_date"] = pd.to_datetime(pred["signal_date"])
    if tit.ticker.nunique() != 70 or pred.ticker.nunique() != 70:
        raise RuntimeError("holdout checkpoint coverage is not exactly 70 candidates")

    return {
        "base": base,
        "candidate_raw": candidate,
        "titanium_raw": titanium_raw,
        "candidate_tickers": tickers,
        "tit": tit,
        "tit_full_path": base / "titanium/TIT_R_SOURCE_ONLY.csv",
        "tit_candidate_path": base / "TIT_R_CANDIDATES_ONLY.csv",
        "pred": pred,
        "pred_path": base / "ENSEMBLE_TAIL_OOS.csv",
        "ma3_panel_path": base / "ma3_panel/RAW_FEATURE_PANEL.pkl",
    }


def replay_holdout70(state: dict) -> dict:
    candidate, tickers = state["candidate_raw"], state["candidate_tickers"]
    cand_mats, _, _ = c.load_ticker_csv_folder(candidate)
    ref_mats, _, _ = c.load_ticker_csv_folder(c.FROZEN149)

    # Execution keeps the 70 candidates first so all candidate indices remain
    # 0..69. BIL/SHV are appended only as cash sleeves.
    exec_tickers = list(tickers) + [t for t in ("BIL", "SHV") if t not in tickers]
    exec_mats = {}
    for field in ("Open", "High", "Low", "Close", "Volume"):
        parts = []
        for t in exec_tickers:
            s = cand_mats[field][t] if t in cand_mats[field].columns else ref_mats[field][t]
            parts.append(s.rename(t))
        exec_mats[field] = pd.concat(parts, axis=1).sort_index()
    ti = {t: i for i, t in enumerate(exec_tickers)}

    tit = state["tit"]
    cal = tit[["signal_date", "entry_date", "exit_date"]].drop_duplicates().sort_values("signal_date").reset_index(drop=True)
    last_raw = {t: cand_mats["Close"][t].last_valid_index() for t in tickers}
    cutoff = min(last_raw.values())
    cal = cal[cal.exit_date.le(cutoff)].copy().reset_index(drop=True)
    if cal.empty:
        raise RuntimeError("no complete holding periods")

    p = state["pred"].rename(columns={"ET_TAIL": "ET_RANK", "XGB_TAIL": "XGB_RANK"}).copy()
    score = c.stage19.score_matrix(p, cal, tickers)
    pm = c.stage19.pred_matrices(p, cal, tickers)

    Odf = exec_mats["Open"].reindex(columns=exec_tickers).ffill().bfill()
    Ldf = exec_mats["Low"].reindex(columns=exec_tickers).ffill().bfill().reindex(Odf.index)
    Cdf = exec_mats["Close"].reindex(columns=exec_tickers).ffill().bfill().reindex(Odf.index)
    start, end = pd.Timestamp(cal.entry_date.min()), pd.Timestamp(cal.exit_date.max())
    Odf = Odf.loc[:end]
    Ldf = Ldf.reindex(Odf.index)
    Cdf = Cdf.reindex(Odf.index)
    st, en = int(Odf.index.get_loc(start)), int(Odf.index.get_loc(end))
    ds = Odf.index[st:en + 1]

    BM = np.arange(len(tickers), dtype=np.int32)[None, :]
    BOK = np.ones_like(BM, dtype=bool)
    alloc = c.producer.allocations_from_score(score, cal, ds, BM, BOK, continuous=True)
    if int(alloc.d1.max()) >= 70 or int(alloc.d2.max()) >= 70:
        raise RuntimeError("non-candidate leaked into top1/top2")

    cand_close = Cdf[tickers]

    # DD-first source is unchanged. Add the three canonical systemic references
    # required by market_state(); they are never candidate indices.
    risk_refs = ref_mats["Close"][["SPY", "HYG", "IEF"]].reindex(Cdf.index).ffill().bfill()
    risk_close = pd.concat([cand_close, risk_refs], axis=1)
    gross = np.asarray(c.ddfirst.sync_c95_m75_gross(risk_close)[st:en + 1], float)
    g = c.stage19.risk_gross_transform(gross)

    # V6 source is also unchanged. It requires SPY plus two excluded tickers.
    # Build [70 candidates, SPY, BIL] and use its existing bil_ticker/shv_ticker
    # parameters to exclude both infrastructure columns from ALT eligibility.
    v6_refs = ref_mats["Close"][["SPY", "BIL"]].reindex(ds).ffill().bfill()
    v6_close = pd.concat([cand_close.loc[ds], v6_refs], axis=1)
    s6 = c.v6.build_v6_state(
        v6_close, alloc.d1, alloc.d2, alloc.weight1, gross,
        bil_ticker="SPY", shv_ticker="BIL",
    )
    if np.any((s6.alt_idx >= 70) & (s6.alt_idx >= 0)):
        raise RuntimeError("infrastructure leaked into V6 alternate selection")

    ex_full = c.ddfirst.daily_execution_inputs(Odf, Ldf, Cdf)
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
    weights = c.stage19.confidence_weights(
        alloc, g, agreement, np.zeros_like(agreement), mode="current_plus_models_riskoff"
    )
    G = np.tile(g, (1, 1))
    O, L, C, PC, gap, ud1, uneg, UH, SA = [
        ex[k] for k in ("O", "L", "C", "PC", "gap", "ud1", "uneg", "UH", "SA")
    ]
    E, T, _, AW = c.stage19.simulate_arch(
        alloc.d1, alloc.d2, weights, O, L, C, PC, gap, ud1, uneg, UH, SA,
        ti["BIL"], ti["SHV"], G, g, s6.alt_idx, True, .001
    )
    mask = np.ones(len(ds), dtype=bool)
    met = c.stage19.metrics(E, mask)

    bh_close = cand_mats["Close"].reindex(ds)[tickers].ffill().bfill()
    bh = (bh_close / bh_close.iloc[0]).mean(axis=1).to_numpy(float)[None, :]
    bh_met = c.stage19.metrics(bh, mask)

    np.savez_compressed(
        state["base"] / "FULL_UNIVERSE_PATH.npz",
        dates=ds.values, equity=E, turnover=T, d1=alloc.d1, d2=alloc.d2,
        weight1=weights, margin=alloc.margin, alt_idx=s6.alt_idx,
    )
    pd.DataFrame({
        "date": ds,
        "top1": [tickers[int(i)] for i in alloc.d1[0]],
        "top2": [tickers[int(i)] for i in alloc.d2[0]],
    }).to_csv(state["base"] / "DAILY_LEADERS.csv", index=False)

    result = {
        "candidate_count": 70,
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
            "titanium_full_sha256": c.sha256(state["tit_full_path"]),
            "titanium_candidates_sha256": c.sha256(state["tit_candidate_path"]),
            "predictions_sha256": c.sha256(state["pred_path"]),
            "ma3_panel_sha256": c.sha256(state["ma3_panel_path"]),
            "historical_scores_consumed": False,
            "historical_paths_consumed": False,
            "replayed_from_saved_source_only_checkpoint": True,
        },
        "infrastructure_contract": {
            "economic_candidates": 70,
            "ddfirst_market_refs_nonselectable": ["SPY", "HYG", "IEF"],
            "v6_recovery_refs_nonselectable": ["SPY", "BIL"],
            "execution_cash_refs_nonselectable": ["BIL", "SHV"],
            "top1_top2_candidate_only": True,
            "v6_alt_candidate_only": True,
        },
    }
    (state["base"] / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    if c.OUT.exists():
        shutil.rmtree(c.OUT)
    c.OUT.mkdir(parents=True)

    src149 = PARTIAL149 / "original149"
    if not (src149 / "RESULT.json").exists():
        raise RuntimeError("original149 checkpoint missing")
    shutil.copytree(src149, c.OUT / "original149")
    r149 = json.loads((c.OUT / "original149" / "RESULT.json").read_text())

    state70 = restore_holdout_state()
    r70 = replay_holdout70(state70)
    m149 = r149["v2_full_universe"]
    m70 = r70["v2_full_universe"]
    hist = c.CANONICAL149
    comparison = {
        "status": "REPLAY_ONLY_CHECKPOINTED_SAME_SOURCE_149_VS_70_COMPLETE",
        "resume_contract": {
            "raw_from_run": 37017429560,
            "original149_result_from_run": 37017928047,
            "holdout70_training_checkpoint_from_run": 37019935712,
            "holdout70_training_recomputed_this_run": False,
            "replay_only": True,
        },
        "historical_canonical149_reference": hist,
        "fresh149_minus_historical_reference": {
            "cagr_pp": float((m149["cagr"] - hist["cagr"]) * 100),
            "maxdd_pp": float((m149["maxdd"] - hist["maxdd"]) * 100),
            "sharpe": float(m149["sharpe"] - hist["sharpe"]),
        },
        "original149": r149,
        "holdout70": r70,
        "delta_70_minus_149": {
            "cagr_pp": float((m70["cagr"] - m149["cagr"]) * 100),
            "maxdd_pp": float((m70["maxdd"] - m149["maxdd"]) * 100),
            "sharpe": float(m70["sharpe"] - m149["sharpe"]),
        },
    }
    (c.OUT / "COMPARISON.json").write_text(json.dumps(comparison, indent=2) + "\n")
    print("FINAL_REPLAY_ONLY_COMPARISON", json.dumps(comparison, indent=2), flush=True)


if __name__ == "__main__":
    main()
