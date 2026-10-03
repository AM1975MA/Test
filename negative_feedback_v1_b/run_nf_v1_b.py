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

MIN_MATURED_DATES = 3


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("canonical_nf_compare_b", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rank_pct(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    out = np.full(x.shape, np.nan, dtype=float)
    m = np.isfinite(x)
    if m.any():
        out[m] = pd.Series(x[m]).rank(pct=True, method="average").to_numpy(float)
    return out


def rank_ic(a: np.ndarray, b: np.ndarray) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3:
        return np.nan
    ra = rank_pct(a[m])
    rb = rank_pct(b[m])
    if np.nanstd(ra) == 0 or np.nanstd(rb) == 0:
        return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])


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
    # A prediction tie receives half credit; realized-target ties are excluded.
    return float(((prod > 0).sum() + 0.5 * (prod == 0).sum()) / len(prod))


def rank_mae(pred: np.ndarray, target: np.ndarray) -> float:
    m = np.isfinite(pred) & np.isfinite(target)
    if m.sum() < 2:
        return np.nan
    rp = rank_pct(pred[m])
    rt = rank_pct(target[m])
    return float(np.mean(np.abs(rp - rt)))


def remap_score_distribution(score: np.ndarray, ordering_rank: np.ndarray) -> np.ndarray:
    """Preserve the exact score multiset while changing only ticker assignment/order."""
    score = np.asarray(score, dtype=float)
    ordering_rank = np.asarray(ordering_rank, dtype=float)
    out = score.copy()
    finite = np.isfinite(score) & np.isfinite(ordering_rank)
    idx = np.flatnonzero(finite)
    if len(idx) <= 1:
        return out
    # Lowest ordering rank receives lowest score; ticker index is deterministic tie-breaker.
    order = idx[np.lexsort((idx, ordering_rank[idx]))]
    values = np.sort(score[idx])
    out[order] = values
    return out


def build_rank_feedback(mod, state: dict):
    pred = state["pred"].copy()
    tickers = list(map(str, state["candidate_tickers"]))
    cal = state["tit"][["signal_date", "entry_date", "exit_date"]].drop_duplicates().sort_values("signal_date").reset_index(drop=True)
    cal["signal_date"] = pd.to_datetime(cal["signal_date"])
    dates_idx = pd.DatetimeIndex(cal["signal_date"])

    # Untouched canonical Stage19 score matrix before monkey-patching.
    score_base = np.asarray(mod.stage19.score_matrix(pred, cal, tickers), dtype=float)
    if score_base.shape != (len(dates_idx), len(tickers)):
        raise RuntimeError(("unexpected score shape", score_base.shape, len(dates_idx), len(tickers)))

    panel = pd.read_pickle(state["ma3_panel_path"]).copy()
    panel["signal_date"] = pd.to_datetime(panel["signal_date"])
    panel["exit_date_63"] = pd.to_datetime(panel["exit_date_63"])
    panel["HYBRID_TARGET"] = mod.fit_ensemble_producer.__globals__["fit_hybrid_producer"].__globals__["corrected_target"](panel)

    target = (panel.pivot_table(index="signal_date", columns="ticker", values="HYBRID_TARGET", aggfunc="first")
                  .reindex(index=dates_idx, columns=tickers).to_numpy(float))
    exit_by_date = panel.groupby("signal_date")["exit_date_63"].max().reindex(dates_idx)

    score_corr = np.array(score_base, copy=True)
    prev_corr_rank = None
    matured_done: set[int] = set()
    matured_acc: list[float] = []
    audit_rows = []
    reliability_by_date = []
    active_by_date = []
    dist_gate_max = 0.0

    for i, d in enumerate(dates_idx):
        # Ingest each historical ranking outcome only after its 63d target has fully matured.
        for j in range(i):
            if j in matured_done:
                continue
            ex = exit_by_date.iloc[j]
            if pd.notna(ex) and pd.Timestamp(ex) < pd.Timestamp(d):
                acc = pairwise_accuracy(score_base[j], target[j])
                if np.isfinite(acc):
                    matured_acc.append(float(acc))
                matured_done.add(j)

        current_rank = rank_pct(score_base[i])
        active = len(matured_acc) >= MIN_MATURED_DATES and prev_corr_rank is not None
        reliability = float(np.mean(matured_acc)) if matured_acc else np.nan

        if active:
            q = float(np.clip(reliability, 0.0, 1.0))
            corr_rank = q * current_rank + (1.0 - q) * prev_corr_rank
        else:
            corr_rank = current_rank.copy()

        corrected = remap_score_distribution(score_base[i], corr_rank)
        score_corr[i] = corrected

        b = np.sort(score_base[i][np.isfinite(score_base[i])])
        c = np.sort(corrected[np.isfinite(corrected)])
        if len(b) != len(c):
            raise RuntimeError("score distribution finite-count mismatch")
        if len(b):
            dist_err = float(np.max(np.abs(b - c)))
            dist_gate_max = max(dist_gate_max, dist_err)
            if not np.array_equal(b, c):
                raise RuntimeError(("score distribution preservation failure", str(d), dist_err))

        feedback_rank = rank_pct(corrected)
        for k, ticker in enumerate(tickers):
            audit_rows.append({
                "signal_date": pd.Timestamp(d),
                "ticker": ticker,
                "exit_date_63": exit_by_date.iloc[i],
                "HYBRID_TARGET": target[i, k],
                "SCORE_BASE": score_base[i, k],
                "RANK_BASE": current_rank[k],
                "RANK_BLEND": corr_rank[k],
                "SCORE_FEEDBACK": corrected[k],
                "RANK_FEEDBACK": feedback_rank[k],
                "RELIABILITY": reliability,
                "MATURED_DATES": len(matured_acc),
                "ACTIVE": int(active),
            })

        reliability_by_date.append(reliability)
        active_by_date.append(active)
        prev_corr_rank = corr_rank.copy()

    rank_mae_base = []
    rank_mae_fb = []
    ic_base = []
    ic_fb = []
    pair_base = []
    pair_fb = []
    eval_dates = 0
    for i in range(len(dates_idx)):
        if np.isfinite(target[i]).sum() < 2:
            continue
        eval_dates += 1
        rank_mae_base.append(rank_mae(score_base[i], target[i]))
        rank_mae_fb.append(rank_mae(score_corr[i], target[i]))
        ic_base.append(rank_ic(score_base[i], target[i]))
        ic_fb.append(rank_ic(score_corr[i], target[i]))
        pair_base.append(pairwise_accuracy(score_base[i], target[i]))
        pair_fb.append(pairwise_accuracy(score_corr[i], target[i]))

    active_reliability = [q for q, a in zip(reliability_by_date, active_by_date) if a and np.isfinite(q)]
    metrics = {
        "rank_mae_base": float(np.nanmean(rank_mae_base)),
        "rank_mae_feedback": float(np.nanmean(rank_mae_fb)),
        "mean_rank_ic_base": float(np.nanmean(ic_base)),
        "mean_rank_ic_feedback": float(np.nanmean(ic_fb)),
        "mean_pairwise_accuracy_base": float(np.nanmean(pair_base)),
        "mean_pairwise_accuracy_feedback": float(np.nanmean(pair_fb)),
        "dates_evaluated": int(eval_dates),
        "correction_active_fraction": float(np.mean(active_by_date)),
        "mean_reliability_when_active": float(np.mean(active_reliability)) if active_reliability else np.nan,
        "score_distribution_max_abs_error": float(dist_gate_max),
    }
    return pd.DataFrame(audit_rows), score_base, score_corr, metrics


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

    # Untouched canonical baseline.
    baseline = mod.replay_full_universe(state)
    base_dir = state["base"]
    for fn in ["RESULT.json", "DAILY_LEADERS.csv", "FULL_UNIVERSE_PATH.npz"]:
        p = base_dir / fn
        if p.exists():
            shutil.copyfile(p, base_dir / ("BASELINE_" + fn))

    audit, score_base, score_corr, direct = build_rank_feedback(mod, state)
    audit.to_csv(base_dir / "RANK_FEEDBACK_STATE_AUDIT.csv", index=False)

    # Exact distribution gate: V1_B may reassign scores to tickers, never alter the score multiset.
    for i in range(score_base.shape[0]):
        b = np.sort(score_base[i][np.isfinite(score_base[i])])
        c = np.sort(score_corr[i][np.isfinite(score_corr[i])])
        if not np.array_equal(b, c):
            raise RuntimeError(("score distribution gate failed", i))

    old_score_matrix = mod.stage19.score_matrix
    mod.stage19.score_matrix = lambda pred, cal, tickers: score_corr
    try:
        feedback = mod.replay_full_universe(state)
    finally:
        mod.stage19.score_matrix = old_score_matrix

    for fn in ["RESULT.json", "DAILY_LEADERS.csv", "FULL_UNIVERSE_PATH.npz"]:
        p = base_dir / fn
        if p.exists():
            shutil.copyfile(p, base_dir / ("FEEDBACK_" + fn))

    b = baseline["v2_full_universe"]
    f = feedback["v2_full_universe"]
    summary = {
        "status": "NF_V1_B_COMPLETE",
        "controller": {
            "type": "causal_expanding_pairwise_rank_reliability_with_temporal_inertia",
            "min_matured_dates": MIN_MATURED_DATES,
            "score_distribution_preserved_exactly": True,
            "free_gain_parameters": 0,
        },
        "causality": "Only ranking outcomes whose exit_date_63 is strictly earlier than current signal_date enter reliability state.",
        "direct_rank_metrics": direct,
        "baseline": b,
        "feedback": f,
        "economic_delta": {
            "cagr_pp": 100.0 * (f["cagr"] - b["cagr"]),
            "maxdd_pp": 100.0 * (f["maxdd"] - b["maxdd"]),
            "sharpe": f["sharpe"] - b["sharpe"],
            "turnover": f["annualized_turnover"] - b["annualized_turnover"],
        },
    }
    (base_dir / "NF_V1_B_RESULT.json").write_text(json.dumps(summary, indent=2) + "\n")
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
