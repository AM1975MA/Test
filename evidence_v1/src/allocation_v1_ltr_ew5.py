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


def summarize(monthly: pd.DataFrame) -> dict:
    return {
        "ltr_top1": stats(monthly.ltr_top1_ret21),
        "ltr_ew5": stats(monthly.ltr_ew5_ret21),
        "universe_ew": stats(monthly.universe_ew_ret21),
        "mean_ew5_name_turnover": float(monthly.ew5_name_turnover.dropna().mean()),
        "top5_contains_global_winner_rate": float(monthly.top5_contains_global_winner.mean()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    panel = pd.read_pickle(args.panel).copy()
    panel["signal_date"] = pd.to_datetime(panel.signal_date)
    if "fwd_ret_21" not in panel.columns:
        raise RuntimeError("panel missing fwd_ret_21")

    cp = Path(args.checkpoint)
    top5 = pd.read_csv(cp / "TOP5.csv")
    top5["signal_date"] = pd.to_datetime(top5.signal_date)
    full = pd.read_csv(cp / "OOS_PREDICTIONS.csv")
    full["signal_date"] = pd.to_datetime(full.signal_date)

    if len(top5) != 930 or top5.signal_date.nunique() != 186:
        raise RuntimeError(
            f"frozen Top5 checkpoint mismatch: rows={len(top5)} dates={top5.signal_date.nunique()}"
        )
    sizes = top5.groupby("signal_date").size()
    if sizes.nunique() != 1 or int(sizes.iloc[0]) != 5:
        raise RuntimeError("frozen Top5 checkpoint is not exactly 5 rows per signal date")

    ret = panel[["signal_date", "ticker", "fwd_ret_21"]].copy()
    top5j = top5.merge(ret, on=["signal_date", "ticker"], how="left", validate="one_to_one")
    fullj = full.merge(ret, on=["signal_date", "ticker"], how="left", validate="one_to_one")

    full_by_date = {dt: g.copy() for dt, g in fullj.groupby("signal_date", sort=True)}
    rows = []
    prev_names: set[str] | None = None

    for dt, g in top5j.groupby("signal_date", sort=True):
        if dt < EVAL_START or dt >= EVAL_END:
            continue
        g = g.dropna(subset=["fwd_ret_21"]).copy()
        if len(g) != 5:
            raise RuntimeError(f"{dt}: incomplete mature Top5 returns")
        ranked = g.sort_values(["LTR_SCORE", "ticker"], ascending=[False, True]).reset_index(drop=True)
        names = set(ranked.ticker.astype(str))

        fg = full_by_date.get(dt)
        if fg is None:
            raise RuntimeError(f"{dt}: missing full OOS comparator rows")
        fg = fg.dropna(subset=["fwd_ret_21"]).copy()
        if fg.empty:
            raise RuntimeError(f"{dt}: no full-universe returns")
        actual = fg.sort_values(["fwd_ret_21", "ticker"], ascending=[False, True]).reset_index(drop=True)
        global_winner = str(actual.iloc[0].ticker)

        turnover = np.nan if prev_names is None else 1.0 - len(names & prev_names) / 5.0
        rows.append({
            "signal_date": dt,
            "ltr_top1": str(ranked.iloc[0].ticker),
            "ltr_top1_ret21": float(ranked.iloc[0].fwd_ret_21),
            "ltr_ew5_ret21": float(ranked.fwd_ret_21.mean()),
            "universe_ew_ret21": float(fg.fwd_ret_21.mean()),
            "global_winner": global_winner,
            "top5_contains_global_winner": bool(global_winner in names),
            "ew5_name_turnover": turnover,
            "top5_names": "|".join(ranked.ticker.astype(str).tolist()),
        })
        prev_names = names

    monthly = pd.DataFrame(rows)
    monthly["signal_date"] = pd.to_datetime(monthly.signal_date)
    if len(monthly) != 114 or monthly.signal_date.nunique() != 114:
        raise RuntimeError(
            f"expected 114 evaluation periods, got rows={len(monthly)} dates={monthly.signal_date.nunique()}"
        )

    full_summary = summarize(monthly)
    pre = monthly[monthly.signal_date < pd.Timestamp("2023-01-01")]
    post = monthly[monthly.signal_date >= pd.Timestamp("2023-01-01")]
    pre_summary = summarize(pre)
    post_summary = summarize(post)

    # Fail closed against the certified frozen retriever evidence.
    expected_top1_cagr = 0.220630708412056
    expected_top5_hit = 32 / 114
    if not np.isclose(full_summary["ltr_top1"]["cagr"], expected_top1_cagr, rtol=0, atol=1e-12):
        raise RuntimeError(
            f"frozen LTR Top1 CAGR mismatch: {full_summary['ltr_top1']['cagr']} != {expected_top1_cagr}"
        )
    if not np.isclose(full_summary["top5_contains_global_winner_rate"], expected_top5_hit, rtol=0, atol=1e-12):
        raise RuntimeError(
            "frozen LTR Top5 global-winner containment mismatch: "
            f"{full_summary['top5_contains_global_winner_rate']} != {expected_top5_hit}"
        )

    top1 = full_summary["ltr_top1"]
    ew5 = full_summary["ltr_ew5"]
    uew = full_summary["universe_ew"]
    advance = bool(
        ew5["cagr"] > top1["cagr"]
        and ew5["max_drawdown"] >= top1["max_drawdown"]
        and ew5["cagr"] > uew["cagr"]
    )

    result = {
        "line": "Evidence V1",
        "test": "allocation_v1_ltr_ew5",
        "status": "DEVELOPMENT_EVIDENCE_ADVANCE" if advance else "DEVELOPMENT_EVIDENCE_REJECTED",
        "universe": "Original149 frozen; burned development set only",
        "retriever": "frozen Retriever LTR v1 OOS Top5 checkpoint; no retraining",
        "allocation": "equal weight 20% each across frozen LTR Top5; monthly signal dates; 21d open-to-open forward return proxy",
        "score_use": "LTR score used only to define frozen Top5/Top1; no score-proportional sizing and no margin confidence",
        "comparators": "frozen LTR Top1 and equal-weight eligible OOS candidate universe on same dates/returns",
        "primary_advancement_rule": (
            "EW5 full-window CAGR must strictly exceed frozen LTR Top1 CAGR; "
            "EW5 max drawdown must be no worse than Top1; and EW5 CAGR must exceed universe-EW. "
            "Subperiod and other risk metrics are diagnostic only."
        ),
        "full": full_summary,
        "2017_2022": pre_summary,
        "2023_2026": post_summary,
        "decision": (
            "ADVANCE allocation line; next step may test frozen sizing/risk control without changing K"
            if advance
            else "REJECT simple EW5 allocation; do not sweep K ex post; reassess allocation hypothesis before another configuration"
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(out / "MONTHLY.csv", index=False)
    (out / "SUMMARY.json").write_text(json.dumps(result, indent=2) + "\n")
    manifest = {
        "test": "allocation_v1_ltr_ew5",
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
