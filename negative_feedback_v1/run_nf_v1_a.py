#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

ALPHA = 0.20
LAMBDA = 0.50
CAP = 0.20
MIN_OBS = 3


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("canonical_nf_compare", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cross_section_rank_corr(a: pd.Series, b: pd.Series) -> float:
    aa = a.rank(pct=True, method="average")
    bb = b.rank(pct=True, method="average")
    if aa.nunique() < 2 or bb.nunique() < 2:
        return np.nan
    return float(aa.corr(bb))


def build_feedback(mod, state: dict):
    pred = state["pred"].copy()
    panel = pd.read_pickle(state["ma3_panel_path"]).copy()
    panel["signal_date"] = pd.to_datetime(panel["signal_date"])
    panel["exit_date_63"] = pd.to_datetime(panel["exit_date_63"])
    panel["HYBRID_TARGET"] = mod.fit_ensemble_producer.__globals__["fit_hybrid_producer"].__globals__["corrected_target"](panel)

    cols = ["signal_date", "ticker", "exit_date_63", "HYBRID_TARGET"]
    ev = pred.merge(panel[cols], on=["signal_date", "ticker"], how="left", validate="one_to_one")
    ev["signal_date"] = pd.to_datetime(ev["signal_date"])
    ev["exit_date_63"] = pd.to_datetime(ev["exit_date_63"])
    ev["TAIL_BASE"] = 0.60 * ev["ET_TAIL"].astype(float) + 0.40 * ev["XGB_TAIL"].astype(float)

    dates = sorted(ev["signal_date"].dropna().unique())
    tickers = list(map(str, state["candidate_tickers"]))
    bias = {t: 0.0 for t in tickers}
    nobs = {t: 0 for t in tickers}
    used = set()
    out = []

    # At each signal date, first ingest only targets that fully matured before this signal.
    for d in dates:
        matured = ev[(ev["exit_date_63"] < d) & ev["HYBRID_TARGET"].notna()]
        for idx, r in matured.iterrows():
            key = (pd.Timestamp(r.signal_date), str(r.ticker))
            if key in used:
                continue
            t = str(r.ticker)
            residual = float(r.TAIL_BASE - r.HYBRID_TARGET)  # + means model over-estimated
            bias[t] = (1.0 - ALPHA) * bias[t] + ALPHA * residual
            nobs[t] += 1
            used.add(key)

        day = ev[ev["signal_date"] == d].copy()
        day["BIAS"] = day["ticker"].map(lambda t: bias[str(t)] if nobs[str(t)] >= MIN_OBS else 0.0)
        day["NOBS"] = day["ticker"].map(lambda t: nobs[str(t)])
        day["TAIL_CORR"] = np.clip(day["TAIL_BASE"] - LAMBDA * day["BIAS"].clip(-CAP, CAP), 0.0, 1.0)
        out.append(day)

    evc = pd.concat(out, ignore_index=True)

    cal = state["tit"][["signal_date", "entry_date", "exit_date"]].drop_duplicates().sort_values("signal_date").reset_index(drop=True)
    cal["signal_date"] = pd.to_datetime(cal["signal_date"])
    dates_idx = pd.DatetimeIndex(cal["signal_date"])

    def pivot(col):
        return (evc.pivot(index="signal_date", columns="ticker", values=col)
                   .reindex(index=dates_idx, columns=tickers).to_numpy(float))

    base = (evc.pivot(index="signal_date", columns="ticker", values="BASE")
               .reindex(index=dates_idx, columns=tickers).to_numpy(float))
    tail_corr = pivot("TAIL_CORR")
    lag1 = np.vstack([tail_corr[:1], tail_corr[:-1]])
    lag2 = np.vstack([tail_corr[:1], tail_corr[:1], tail_corr[:-2]])
    smooth = 0.40 * tail_corr + 0.30 * lag1 + 0.30 * lag2
    score_corr = 0.475 * base + 0.525 * np.power(np.clip(smooth, 0.0, 1.0), 1.10)

    # Direct ex-post diagnostics. These are evaluation metrics only; they never feed earlier dates.
    valid = evc[evc["HYBRID_TARGET"].notna()].copy()
    valid["ERR_BASE"] = valid["TAIL_BASE"] - valid["HYBRID_TARGET"]
    valid["ERR_CORR"] = valid["TAIL_CORR"] - valid["HYBRID_TARGET"]
    ic_base, ic_corr = [], []
    for _, g in valid.groupby("signal_date"):
        ic_base.append(cross_section_rank_corr(g["TAIL_BASE"], g["HYBRID_TARGET"]))
        ic_corr.append(cross_section_rank_corr(g["TAIL_CORR"], g["HYBRID_TARGET"]))

    metrics = {
        "mae_base": float(valid["ERR_BASE"].abs().mean()),
        "mae_feedback": float(valid["ERR_CORR"].abs().mean()),
        "rmse_base": float(np.sqrt(np.mean(np.square(valid["ERR_BASE"])))),
        "rmse_feedback": float(np.sqrt(np.mean(np.square(valid["ERR_CORR"])))),
        "mean_error_base": float(valid["ERR_BASE"].mean()),
        "mean_error_feedback": float(valid["ERR_CORR"].mean()),
        "mean_rank_ic_base": float(np.nanmean(ic_base)),
        "mean_rank_ic_feedback": float(np.nanmean(ic_corr)),
        "rows_evaluated": int(len(valid)),
        "dates_evaluated": int(valid["signal_date"].nunique()),
        "correction_active_fraction": float((evc["NOBS"] >= MIN_OBS).mean()),
    }
    return evc, score_corr, metrics


def run_one(raw: Path, compare_script: Path, out: Path):
    os.environ["FROZEN_149_ROOT"] = str(raw.parent)
    os.environ["FROZEN_HOLDOUT70_ROOT"] = str(raw.parent)
    mod = load_module(compare_script)
    mod.FROZEN149 = raw
    mod.FROZEN70 = raw
    mod.OUT = out
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)

    uu = mod.load_universe(raw)
    if len(uu) != 149 or uu.ticker.nunique() != 149:
        raise RuntimeError(f"unexpected universe size: {len(uu)}")

    state = mod.build_source_only_state("original149", raw)

    # Untouched canonical baseline.
    baseline = mod.replay_full_universe(state)
    base_dir = state["base"]
    for fn in ["RESULT.json", "DAILY_LEADERS.csv", "FULL_UNIVERSE_PATH.npz"]:
        p = base_dir / fn
        if p.exists(): shutil.copyfile(p, base_dir / ("BASELINE_" + fn))

    evc, score_corr, direct = build_feedback(mod, state)
    evc.to_csv(base_dir / "FEEDBACK_STATE_AUDIT.csv", index=False)

    # Reuse the exact canonical execution path; replace only the score matrix.
    old_score_matrix = mod.stage19.score_matrix
    mod.stage19.score_matrix = lambda pred, cal, tickers: score_corr
    try:
        feedback = mod.replay_full_universe(state)
    finally:
        mod.stage19.score_matrix = old_score_matrix

    for fn in ["RESULT.json", "DAILY_LEADERS.csv", "FULL_UNIVERSE_PATH.npz"]:
        p = base_dir / fn
        if p.exists(): shutil.copyfile(p, base_dir / ("FEEDBACK_" + fn))

    b = baseline["v2_full_universe"]
    f = feedback["v2_full_universe"]
    summary = {
        "status": "NF_V1_A_COMPLETE",
        "controller": {"alpha": ALPHA, "lambda": LAMBDA, "cap": CAP, "min_obs": MIN_OBS},
        "causality": "Only residuals whose exit_date_63 is strictly earlier than current signal_date enter state.",
        "direct_error_metrics": direct,
        "baseline": b,
        "feedback": f,
        "economic_delta": {
            "cagr_pp": 100.0 * (f["cagr"] - b["cagr"]),
            "maxdd_pp": 100.0 * (f["maxdd"] - b["maxdd"]),
            "sharpe": f["sharpe"] - b["sharpe"],
            "turnover": f["annualized_turnover"] - b["annualized_turnover"],
        },
    }
    (base_dir / "NF_V1_A_RESULT.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--compare-script", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    run_one(Path(args.raw).resolve(), Path(args.compare_script).resolve(), Path(args.out).resolve())

if __name__ == "__main__":
    main()
