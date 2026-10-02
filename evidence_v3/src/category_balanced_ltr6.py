#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED = {
    "n": 114,
    "top1_cagr": -0.07567660003526067,
    "top5ew_cagr": 0.034215706909629384,
    "universe_ew_cagr": 0.08524482878917694,
}
CATEGORIES = [
    "C01_US_BROAD_STYLE",
    "C02_US_SECTOR_THEME",
    "C03_DEVELOPED_GLOBAL",
    "C04_EMERGING",
    "C05_BONDS_CASH_CREDIT",
    "C06_REAL_ASSETS",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cagr(x: pd.Series) -> float:
    r = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    if len(r) == 0 or np.any(r <= -1):
        return float("nan")
    return float(np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0)


def max_drawdown(x: pd.Series) -> float:
    r = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    if len(r) == 0:
        return float("nan")
    wealth = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(wealth)
    return float(np.min(wealth / peak - 1.0))


def stats(x: pd.Series) -> dict:
    r = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    if len(r) == 0:
        return {"n": 0}
    vol = float(np.std(r, ddof=1) * np.sqrt(12.0)) if len(r) > 1 else 0.0
    mean_ann = float(np.mean(r) * 12.0)
    return {
        "n": int(len(r)),
        "cagr_proxy": cagr(pd.Series(r)),
        "annual_vol": vol,
        "sharpe_rf0": float(mean_ann / vol) if vol > 0 else float("nan"),
        "max_drawdown": max_drawdown(pd.Series(r)),
        "positive_rate": float(np.mean(r > 0)),
        "mean_period_return": float(np.mean(r)),
        "worst_period": float(np.min(r)),
        "best_period": float(np.max(r)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--universe", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    p = pd.read_csv(args.predictions, parse_dates=["signal_date"])
    u = pd.read_csv(args.universe)
    required_p = {"signal_date", "ticker", "LTR_SCORE", "fwd_ret_21"}
    if not required_p.issubset(p.columns):
        raise RuntimeError(f"predictions missing {sorted(required_p-set(p.columns))}")
    if list(u.columns) != ["ticker", "macro_category"]:
        raise RuntimeError(f"unexpected universe schema {list(u.columns)}")
    if len(u) != 72 or u.ticker.nunique() != 72:
        raise RuntimeError("Dev72 universe is not 72 unique tickers")
    observed = sorted(u.macro_category.astype(str).unique().tolist())
    if observed != CATEGORIES:
        raise RuntimeError(f"category vocabulary mismatch: {observed}")
    counts = u.groupby("macro_category").size().to_dict()
    if any(counts.get(c) != 12 for c in CATEGORIES):
        raise RuntimeError(f"Dev72 is not 12-per-category: {counts}")

    p = p.merge(u, on="ticker", how="left", validate="many_to_one")
    if p.macro_category.isna().any():
        raise RuntimeError("missing category after join")

    rows = []
    selections = []
    for dt, g0 in p.groupby("signal_date", sort=True):
        g = g0.dropna(subset=["LTR_SCORE", "fwd_ret_21"]).copy()
        if len(g) != 72:
            continue
        if set(g.macro_category.astype(str)) != set(CATEGORIES):
            raise RuntimeError(f"missing category on {dt}")

        global_rank = g.sort_values(["LTR_SCORE", "ticker"], ascending=[False, True]).reset_index(drop=True)
        chosen = []
        for c in CATEGORIES:
            gc = g[g.macro_category == c].sort_values(
                ["LTR_SCORE", "ticker"], ascending=[False, True]
            ).reset_index(drop=True)
            if len(gc) != 12:
                raise RuntimeError(f"category {c} count on {dt}: {len(gc)}")
            r = gc.iloc[0]
            chosen.append(r)
            selections.append({
                "signal_date": dt,
                "macro_category": c,
                "ticker": str(r.ticker),
                "LTR_SCORE": float(r.LTR_SCORE),
                "fwd_ret_21": float(r.fwd_ret_21),
            })

        sel = pd.DataFrame(chosen)
        rows.append({
            "signal_date": dt,
            "top1_ret21": float(global_rank.iloc[0].fwd_ret_21),
            "top5ew_ret21": float(global_rank.head(5).fwd_ret_21.mean()),
            "universe_ew_ret21": float(g.fwd_ret_21.mean()),
            "category_ltr6_ret21": float(sel.fwd_ret_21.mean()),
        })

    m = pd.DataFrame(rows)
    if len(m) != EXPECTED["n"]:
        raise RuntimeError(f"baseline period mismatch {len(m)} != {EXPECTED['n']}")
    m["signal_date"] = pd.to_datetime(m.signal_date)

    top1_c = cagr(m.top1_ret21)
    top5_c = cagr(m.top5ew_ret21)
    uni_c = cagr(m.universe_ew_ret21)
    for got, key in ((top1_c, "top1_cagr"), (top5_c, "top5ew_cagr"), (uni_c, "universe_ew_cagr")):
        if not np.isclose(got, EXPECTED[key], rtol=0, atol=1e-12):
            raise RuntimeError(f"fail-closed comparator mismatch {key}: {got} != {EXPECTED[key]}")

    pre = m[m.signal_date < pd.Timestamp("2023-01-01")].copy()
    post = m[m.signal_date >= pd.Timestamp("2023-01-01")].copy()
    if len(pre) != 72 or len(post) != 42:
        raise RuntimeError(f"unexpected subperiod counts pre={len(pre)} post={len(post)}")

    full_cat = stats(m.category_ltr6_ret21)
    full_uni = stats(m.universe_ew_ret21)
    pre_cat = stats(pre.category_ltr6_ret21)
    pre_uni = stats(pre.universe_ew_ret21)
    post_cat = stats(post.category_ltr6_ret21)
    post_uni = stats(post.universe_ew_ret21)

    s = pd.DataFrame(selections)
    s["signal_date"] = pd.to_datetime(s.signal_date)
    turnover = []
    prev = None
    for dt, gd in s.groupby("signal_date", sort=True):
        cur = dict(zip(gd.macro_category, gd.ticker))
        if prev is not None:
            turnover.append(sum(cur[c] != prev[c] for c in CATEGORIES) / len(CATEGORIES))
        prev = cur

    gate = {
        "full_cagr_gt_universe_ew": bool(full_cat["cagr_proxy"] > full_uni["cagr_proxy"]),
        "2017_2022_cagr_gt_universe_ew": bool(pre_cat["cagr_proxy"] > pre_uni["cagr_proxy"]),
        "2023_2026_cagr_gt_universe_ew": bool(post_cat["cagr_proxy"] > post_uni["cagr_proxy"]),
    }
    passed = bool(all(gate.values()))

    summary = {
        "line": "Evidence V3",
        "test": "category_balanced_ltr6",
        "status": "DEVELOPMENT_ADVANCE" if passed else "DEVELOPMENT_REJECTED",
        "architecture": "one highest frozen OOS LTR-score ETF per each of six frozen categories, equal weight 1/6",
        "model_refit": False,
        "baseline_reproduction": {
            "n_periods": int(len(m)),
            "top1_cagr_proxy": top1_c,
            "top5ew_cagr_proxy": top5_c,
            "universe_ew_cagr_proxy": uni_c,
        },
        "full": {
            "category_ltr6": full_cat,
            "universe_ew": full_uni,
            "top1": stats(m.top1_ret21),
            "top5ew": stats(m.top5ew_ret21),
            "cagr_excess_vs_universe_pp": float((full_cat["cagr_proxy"] - full_uni["cagr_proxy"]) * 100.0),
        },
        "2017_2022": {
            "category_ltr6": pre_cat,
            "universe_ew": pre_uni,
            "cagr_excess_vs_universe_pp": float((pre_cat["cagr_proxy"] - pre_uni["cagr_proxy"]) * 100.0),
        },
        "2023_2026": {
            "category_ltr6": post_cat,
            "universe_ew": post_uni,
            "cagr_excess_vs_universe_pp": float((post_cat["cagr_proxy"] - post_uni["cagr_proxy"]) * 100.0),
        },
        "mean_monthly_category_name_turnover": float(np.mean(turnover)) if turnover else 0.0,
        "primary_gate": gate,
        "decision": (
            "PASS: freeze category-balanced LTR6; next step is a new disjoint Holdout-B before one-shot transfer/promotion testing"
            if passed else
            "REJECT: close category-balanced LTR use on Dev72; no category-weight, category-count, TopN-per-category or nearby allocation variants"
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    m.to_csv(out / "MONTHLY.csv", index=False)
    s.to_csv(out / "SELECTIONS.csv", index=False)
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    files = ["MONTHLY.csv", "SELECTIONS.csv", "SUMMARY.json"]
    (out / "RESULT_MANIFEST.json").write_text(json.dumps({
        "test": "category_balanced_ltr6",
        "files_sha256": {name: sha256_file(out / name) for name in files},
    }, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
