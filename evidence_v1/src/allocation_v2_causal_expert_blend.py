#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

EVAL_START = pd.Timestamp("2017-01-01")
EVAL_END = pd.Timestamp("2026-07-01")
LOOKBACK_MATURE_PERIODS = 12


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stats(r: pd.Series) -> dict:
    x = pd.to_numeric(r, errors="coerce").dropna().to_numpy(float)
    if len(x) == 0 or np.any(x <= -1):
        return {"n": int(len(x))}
    equity = np.cumprod(1.0 + x)
    peak = np.maximum.accumulate(equity)
    dd = equity / peak - 1.0
    cagr = float(equity[-1] ** (12.0 / len(x)) - 1.0)
    vol = float(np.std(x, ddof=1) * np.sqrt(12.0)) if len(x) > 1 else float("nan")
    sharpe = (
        float(np.mean(x) / np.std(x, ddof=1) * np.sqrt(12.0))
        if len(x) > 1 and np.std(x, ddof=1) > 0
        else float("nan")
    )
    mdd = float(np.min(dd))
    calmar = float(cagr / abs(mdd)) if mdd < 0 else float("inf")
    return {
        "n": int(len(x)),
        "cagr": cagr,
        "annualized_vol": vol,
        "sharpe_rf0": sharpe,
        "max_drawdown": mdd,
        "calmar": calmar,
        "positive_period_rate": float(np.mean(x > 0)),
        "worst_period": float(np.min(x)),
        "best_period": float(np.max(x)),
        "mean_period_return": float(np.mean(x)),
    }


def summarize(x: pd.DataFrame) -> dict:
    return {
        "ltr_top1": stats(x.top1_ret21),
        "ltr_ew5": stats(x.ew5_ret21),
        "causal_blend": stats(x.meta_ret21),
        "universe_ew": stats(x.universe_ew_ret21),
        "mean_top1_weight": float(x.weight_top1.mean()),
        "median_top1_weight": float(x.weight_top1.median()),
        "min_top1_weight": float(x.weight_top1.min()),
        "max_top1_weight": float(x.weight_top1.max()),
        "mean_abs_weight_change": float(x.weight_top1.diff().abs().dropna().mean()),
        "bootstrap_50_50_periods": int(x.bootstrap_50_50.sum()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    panel = pd.read_pickle(args.panel).copy()
    panel["signal_date"] = pd.to_datetime(panel.signal_date)
    panel["exit_date_21"] = pd.to_datetime(panel.exit_date_21)
    required = ["signal_date", "ticker", "exit_date_21", "fwd_ret_21"]
    missing = [c for c in required if c not in panel.columns]
    if missing:
        raise RuntimeError(f"panel missing required columns: {missing}")

    cp = Path(args.checkpoint)
    top5 = pd.read_csv(cp / "TOP5.csv")
    top5["signal_date"] = pd.to_datetime(top5.signal_date)
    full = pd.read_csv(cp / "OOS_PREDICTIONS.csv")
    full["signal_date"] = pd.to_datetime(full.signal_date)

    if len(top5) != 930 or top5.signal_date.nunique() != 186:
        raise RuntimeError("frozen Top5 checkpoint shape mismatch")
    sizes = top5.groupby("signal_date").size()
    if sizes.nunique() != 1 or int(sizes.iloc[0]) != 5:
        raise RuntimeError("frozen Top5 checkpoint is not exactly 5 rows per signal date")

    ret = panel[required].copy()
    top5j = top5.merge(ret, on=["signal_date", "ticker"], how="left", validate="one_to_one")
    fullj = full.merge(
        panel[["signal_date", "ticker", "fwd_ret_21"]],
        on=["signal_date", "ticker"], how="left", validate="one_to_one"
    )
    full_by_date = {dt: g.copy() for dt, g in fullj.groupby("signal_date", sort=True)}

    # Build the two frozen expert return streams for the whole OOS checkpoint,
    # including pre-2017 history. These rows are not evaluation results; they are
    # available only after their 21d exits have matured.
    expert_rows = []
    for dt, g in top5j.groupby("signal_date", sort=True):
        g = g.copy()
        if len(g) != 5:
            raise RuntimeError(f"{dt}: expected exactly five frozen Top5 rows")
        valid = g.fwd_ret_21.notna() & g.exit_date_21.notna()
        if not bool(valid.all()):
            continue
        exits = pd.DatetimeIndex(g.exit_date_21.unique())
        if len(exits) != 1:
            raise RuntimeError(f"{dt}: inconsistent exit_date_21 within Top5")
        ranked = g.sort_values(["LTR_SCORE", "ticker"], ascending=[False, True]).reset_index(drop=True)
        fg = full_by_date.get(dt)
        if fg is None:
            raise RuntimeError(f"{dt}: missing full OOS rows")
        fg = fg.dropna(subset=["fwd_ret_21"])
        if fg.empty:
            continue
        expert_rows.append({
            "signal_date": dt,
            "exit_date_21": exits[0],
            "top1_ret21": float(ranked.iloc[0].fwd_ret_21),
            "ew5_ret21": float(ranked.fwd_ret_21.mean()),
            "universe_ew_ret21": float(fg.fwd_ret_21.mean()),
        })

    experts = pd.DataFrame(expert_rows).sort_values("signal_date").reset_index(drop=True)
    if experts.empty:
        raise RuntimeError("no mature frozen expert returns")

    eval_rows = []
    for _, cur in experts.iterrows():
        dt = pd.Timestamp(cur.signal_date)
        if dt < EVAL_START or dt >= EVAL_END:
            continue

        # Strict causal maturity gate. A prior signal is usable only if its 21d
        # realized return was already fully known before the current signal date.
        hist = experts[
            (experts.signal_date < dt) & (experts.exit_date_21 < dt)
        ].sort_values("signal_date")
        hist12 = hist.tail(LOOKBACK_MATURE_PERIODS)

        bootstrap = len(hist12) < LOOKBACK_MATURE_PERIODS
        if bootstrap:
            w_top1 = 0.5
            w_ew5 = 0.5
            wealth_top1 = float("nan")
            wealth_ew5 = float("nan")
        else:
            wealth_top1 = float(np.prod(1.0 + hist12.top1_ret21.to_numpy(float)))
            wealth_ew5 = float(np.prod(1.0 + hist12.ew5_ret21.to_numpy(float)))
            if wealth_top1 <= 0 or wealth_ew5 <= 0:
                raise RuntimeError(f"{dt}: non-positive trailing expert wealth")
            denom = wealth_top1 + wealth_ew5
            w_top1 = wealth_top1 / denom
            w_ew5 = wealth_ew5 / denom

        if not np.isclose(w_top1 + w_ew5, 1.0, atol=1e-12):
            raise RuntimeError(f"{dt}: expert weights do not sum to one")
        meta_ret = w_top1 * float(cur.top1_ret21) + w_ew5 * float(cur.ew5_ret21)
        eval_rows.append({
            "signal_date": dt,
            "exit_date_21": pd.Timestamp(cur.exit_date_21),
            "top1_ret21": float(cur.top1_ret21),
            "ew5_ret21": float(cur.ew5_ret21),
            "universe_ew_ret21": float(cur.universe_ew_ret21),
            "weight_top1": float(w_top1),
            "weight_ew5": float(w_ew5),
            "trailing_wealth_top1": wealth_top1,
            "trailing_wealth_ew5": wealth_ew5,
            "n_mature_history_used": int(len(hist12)),
            "bootstrap_50_50": bool(bootstrap),
            "meta_ret21": float(meta_ret),
        })

    monthly = pd.DataFrame(eval_rows)
    monthly["signal_date"] = pd.to_datetime(monthly.signal_date)
    if len(monthly) != 114 or monthly.signal_date.nunique() != 114:
        raise RuntimeError(
            f"expected 114 evaluation periods, got rows={len(monthly)} dates={monthly.signal_date.nunique()}"
        )

    # Because OOS history starts in 2011, all 2017+ evaluation dates should have
    # 12 mature observations. Fail closed if the bootstrap path was actually used.
    if bool(monthly.bootstrap_50_50.any()):
        raise RuntimeError("unexpected 50/50 bootstrap inside 2017-2026 evaluation window")

    full_summary = summarize(monthly)
    pre_summary = summarize(monthly[monthly.signal_date < pd.Timestamp("2023-01-01")])
    post_summary = summarize(monthly[monthly.signal_date >= pd.Timestamp("2023-01-01")])

    # Reproduce the already-certified comparator streams before judging the meta rule.
    expected_top1_cagr = 0.220630708412056
    expected_ew5_cagr = 0.20360068077564386
    expected_top1_mdd = -0.5147222930936663
    if not np.isclose(full_summary["ltr_top1"]["cagr"], expected_top1_cagr, rtol=0, atol=1e-12):
        raise RuntimeError("frozen Top1 CAGR comparator mismatch")
    if not np.isclose(full_summary["ltr_ew5"]["cagr"], expected_ew5_cagr, rtol=0, atol=1e-12):
        raise RuntimeError("frozen EW5 CAGR comparator mismatch")
    if not np.isclose(full_summary["ltr_top1"]["max_drawdown"], expected_top1_mdd, rtol=0, atol=1e-12):
        raise RuntimeError("frozen Top1 max-drawdown comparator mismatch")

    meta = full_summary["causal_blend"]
    top1 = full_summary["ltr_top1"]
    advance = bool(
        meta["cagr"] > top1["cagr"]
        and meta["max_drawdown"] >= top1["max_drawdown"]
    )

    result = {
        "line": "Evidence V1",
        "test": "allocation_v2_causal_expert_blend",
        "status": "DEVELOPMENT_EVIDENCE_ADVANCE" if advance else "DEVELOPMENT_EVIDENCE_REJECTED",
        "universe": "Original149 frozen; burned development set only",
        "experts": ["frozen LTR Top1", "frozen LTR-EW5"],
        "meta_rule": (
            "At each signal date use the 12 most recent expert periods whose exit_date_21 is strictly before the current signal; "
            "compute each expert trailing compounded wealth and allocate weight = own wealth / sum of the two wealth values."
        ),
        "lookback_mature_periods": LOOKBACK_MATURE_PERIODS,
        "bootstrap_rule": "50/50 only if fewer than 12 mature periods; not used in 2017-2026 evaluation",
        "leverage": "none; weights non-negative and sum to 1",
        "market_regime_inputs": "none",
        "ltr_margin_or_score_sizing": "none",
        "primary_advancement_rule": (
            "Full-window causal-blend CAGR must strictly exceed frozen LTR Top1 CAGR and causal-blend max drawdown must be no worse than Top1. "
            "Subperiods and all other metrics are diagnostic only."
        ),
        "full": full_summary,
        "2017_2022": pre_summary,
        "2023_2026": post_summary,
        "decision": (
            "ADVANCE: freeze new disjoint Holdout-B before any promotion test; no tuning on Original149"
            if advance
            else "REJECT: do not sweep lookback/temperature/switch rules ex post; stop adaptive-allocation tuning on Original149"
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(out / "MONTHLY.csv", index=False)
    (out / "SUMMARY.json").write_text(json.dumps(result, indent=2) + "\n")
    manifest = {
        "test": "allocation_v2_causal_expert_blend",
        "files_sha256": {
            name: sha256_file(out / name)
            for name in ["MONTHLY.csv", "SUMMARY.json"]
        },
    }
    (out / "RESULT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
