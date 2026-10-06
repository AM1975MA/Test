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

ALPHA = 1.0 / 3.0
MIN_MATURED_DATES = 3
NULL_PAIRWISE_ACCURACY = 0.5


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("canonical_nf_compare_c", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pairwise_accuracy(pred: np.ndarray, target: np.ndarray) -> float:
    pred = np.asarray(pred, dtype=float)
    target = np.asarray(target, dtype=float)
    m = np.isfinite(pred) & np.isfinite(target)
    p = pred[m]
    y = target[m]
    n = len(p)
    if n < 2:
        return np.nan
    i, j = np.triu_indices(n, 1)
    dy = y[i] - y[j]
    comparable = dy != 0
    if not comparable.any():
        return np.nan
    dp = p[i] - p[j]
    prod = np.sign(dp[comparable]) * np.sign(dy[comparable])
    return float(((prod > 0).sum() + 0.5 * (prod == 0).sum()) / len(prod))


def build_feedback_gain(mod, state: dict):
    pred = state["pred"].rename(columns={"ET_TAIL": "ET_RANK", "XGB_TAIL": "XGB_RANK"}).copy()
    tickers = list(map(str, state["candidate_tickers"]))
    cal_all = state["tit"][["signal_date", "entry_date", "exit_date"]].drop_duplicates().sort_values("signal_date").reset_index(drop=True)
    for c in ["signal_date", "entry_date", "exit_date"]:
        cal_all[c] = pd.to_datetime(cal_all[c])
    dates_idx = pd.DatetimeIndex(cal_all["signal_date"])
    score = np.asarray(mod.stage19.score_matrix(pred, cal_all, tickers), dtype=float)

    panel = pd.read_pickle(state["ma3_panel_path"]).copy()
    panel["signal_date"] = pd.to_datetime(panel["signal_date"])
    panel["exit_date_63"] = pd.to_datetime(panel["exit_date_63"])
    corrected_target = mod.fit_ensemble_producer.__globals__["fit_hybrid_producer"].__globals__["corrected_target"]
    panel["HYBRID_TARGET"] = corrected_target(panel)
    target = (panel.pivot_table(index="signal_date", columns="ticker", values="HYBRID_TARGET", aggfunc="first")
                  .reindex(index=dates_idx, columns=tickers).to_numpy(float))
    exit_by_date = panel.groupby("signal_date")["exit_date_63"].max().reindex(dates_idx)

    matured_done: set[int] = set()
    q_state = np.nan
    matured_count = 0
    signal_gain = np.ones(len(cal_all), dtype=float)
    audit = []

    for i, d in enumerate(dates_idx):
        newly = []
        for j in range(i):
            if j in matured_done:
                continue
            ex = exit_by_date.iloc[j]
            if pd.notna(ex) and pd.Timestamp(ex) < pd.Timestamp(d):
                acc = pairwise_accuracy(score[j], target[j])
                if np.isfinite(acc):
                    newly.append((j, float(acc)))
                matured_done.add(j)
        for j, acc in sorted(newly):
            if np.isfinite(q_state):
                q_state = (1.0 - ALPHA) * q_state + ALPHA * acc
            else:
                q_state = acc
            matured_count += 1

        active = matured_count >= MIN_MATURED_DATES and np.isfinite(q_state)
        gain = float(np.clip(2.0 * q_state, 0.0, 1.0)) if active else 1.0
        signal_gain[i] = gain
        audit.append({
            "signal_date": str(pd.Timestamp(d).date()),
            "matured_count": matured_count,
            "newly_matured": len(newly),
            "reliability_ewma": None if not np.isfinite(q_state) else float(q_state),
            "gain": gain,
            "active": bool(active),
        })

    cand_mats, _, _ = mod.load_ticker_csv_folder(state["candidate_raw"])
    cutoff = min(cand_mats["Close"][t].last_valid_index() for t in tickers)
    cal = cal_all[cal_all.exit_date.le(cutoff)].copy().reset_index(drop=True)
    Odf = cand_mats["Open"].reindex(columns=tickers).ffill().bfill()
    start, end = pd.Timestamp(cal.entry_date.min()), pd.Timestamp(cal.exit_date.max())
    Odf = Odf.loc[:end]
    st = int(Odf.index.get_loc(start))
    en = int(Odf.index.get_loc(end))
    ds = Odf.index[st:en + 1]

    gain_by_signal = {pd.Timestamp(d): float(g) for d, g in zip(cal_all.signal_date, signal_gain)}
    daily_gain = np.ones(len(ds), dtype=float)
    for row in cal.itertuples(index=False):
        a = int(ds.searchsorted(pd.Timestamp(row.entry_date)))
        e = int(ds.searchsorted(pd.Timestamp(row.exit_date)))
        if a >= len(ds) or e <= a:
            continue
        daily_gain[a:e] = gain_by_signal[pd.Timestamp(row.signal_date)]

    audit_df = pd.DataFrame(audit)
    stats = {
        "active_signal_fraction": float(audit_df.active.mean()),
        "active_daily_fraction": float(np.mean(daily_gain < 1.0 - 1e-15)),
        "mean_daily_gain": float(np.mean(daily_gain)),
        "mean_active_daily_gain": float(np.mean(daily_gain[daily_gain < 1.0 - 1e-15])) if np.any(daily_gain < 1.0 - 1e-15) else 1.0,
        "min_daily_gain": float(np.min(daily_gain)),
        "max_daily_gain": float(np.max(daily_gain)),
        "gain_never_above_one": bool(np.max(daily_gain) <= 1.0 + 1e-15),
    }
    return audit_df, daily_gain, stats


def run_one(raw: Path, compare_script: Path, out: Path):
    os.environ["FROZEN_149_ROOT"] = str(raw.parent)
    os.environ["FROZEN_HOLDOUT70_ROOT"] = str(raw.parent)
    mod = load_module(compare_script)
    mod.FROZEN149 = raw
    mod.FROZEN70 = raw
    mod.OUT = out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    uu = mod.load_universe(raw)
    if len(uu) != 149 or uu.ticker.nunique() != 149:
        raise RuntimeError(f"unexpected universe size: {len(uu)}")

    state = mod.build_source_only_state("original149", raw)
    baseline = mod.replay_full_universe(state)
    base_dir = state["base"]
    for fn in ["RESULT.json", "DAILY_LEADERS.csv", "FULL_UNIVERSE_PATH.npz"]:
        p = base_dir / fn
        if p.exists():
            shutil.copyfile(p, base_dir / ("BASELINE_" + fn))

    audit, daily_gain, feedback_stats = build_feedback_gain(mod, state)
    audit.to_csv(base_dir / "CONFIDENCE_FEEDBACK_STATE_AUDIT.csv", index=False)

    old_risk = mod.stage19.risk_gross_transform
    def feedback_risk(gross):
        base = np.asarray(old_risk(gross), dtype=float)
        if len(base) != len(daily_gain):
            raise RuntimeError(("daily gain shape mismatch", len(base), len(daily_gain)))
        out_g = base * daily_gain
        if np.any(out_g > base + 1e-15):
            raise RuntimeError("feedback increased risk above canonical")
        return out_g

    mod.stage19.risk_gross_transform = feedback_risk
    try:
        feedback = mod.replay_full_universe(state)
    finally:
        mod.stage19.risk_gross_transform = old_risk

    for fn in ["RESULT.json", "DAILY_LEADERS.csv", "FULL_UNIVERSE_PATH.npz"]:
        p = base_dir / fn
        if p.exists():
            shutil.copyfile(p, base_dir / ("FEEDBACK_" + fn))

    b_npz = np.load(base_dir / "BASELINE_FULL_UNIVERSE_PATH.npz")
    f_npz = np.load(base_dir / "FEEDBACK_FULL_UNIVERSE_PATH.npz")
    identity = {
        "d1_exact": bool(np.array_equal(b_npz["d1"], f_npz["d1"])),
        "d2_exact": bool(np.array_equal(b_npz["d2"], f_npz["d2"])),
        "weight1_exact": bool(np.array_equal(b_npz["weight1"], f_npz["weight1"])),
        "margin_exact": bool(np.array_equal(b_npz["margin"], f_npz["margin"])),
    }
    leaders_b = pd.read_csv(base_dir / "BASELINE_DAILY_LEADERS.csv")
    leaders_f = pd.read_csv(base_dir / "FEEDBACK_DAILY_LEADERS.csv")
    identity["top1_exact"] = bool(leaders_b.top1.equals(leaders_f.top1))
    identity["top2_exact"] = bool(leaders_b.top2.equals(leaders_f.top2))
    identity["PASS"] = bool(all(identity.values()))
    if not identity["PASS"]:
        raise RuntimeError(("decision identity failed", identity))

    b = baseline["v2_full_universe"]
    f = feedback["v2_full_universe"]
    summary = {
        "status": "NF_V1_C_COMPLETE",
        "experiment": "NF_V1_C_CONFIDENCE_FEEDBACK",
        "controller": {
            "alpha": ALPHA,
            "min_matured_dates": MIN_MATURED_DATES,
            "null_pairwise_accuracy": NULL_PAIRWISE_ACCURACY,
            "gain_rule": "gain=min(1,max(0,2*q_ewma))",
            "ranking_modified": False,
            "risk_can_only_decrease": True,
        },
        "feedback_state": feedback_stats,
        "decision_identity": identity,
        "baseline": b,
        "feedback": f,
        "economic_delta": {
            "cagr_pp": 100.0 * (f["cagr"] - b["cagr"]),
            "maxdd_pp": 100.0 * (f["maxdd"] - b["maxdd"]),
            "sharpe": f["sharpe"] - b["sharpe"],
            "turnover": f["annualized_turnover"] - b["annualized_turnover"],
        },
    }
    (base_dir / "NF_V1_C_RESULT.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--compare-script", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    run_one(Path(args.raw).resolve(), Path(args.compare_script).resolve(), Path(args.out).resolve())


if __name__ == "__main__":
    main()
