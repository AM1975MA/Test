#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.metrics import ndcg_score
from xgboost import XGBRanker


def monthly_cagr_proxy(r: pd.Series) -> float:
    x = pd.to_numeric(r, errors="coerce").dropna().to_numpy(float)
    if len(x) == 0 or np.any(x <= -1):
        return float("nan")
    return float(np.prod(1.0 + x) ** (12.0 / len(x)) - 1.0)


def period_summary(m: pd.DataFrame) -> dict:
    if m.empty:
        return {"n": 0}
    return {
        "n": int(len(m)),
        "mean_ic21": float(m.ic21.mean()),
        "median_ic21": float(m.ic21.median()),
        "positive_ic21": float((m.ic21 > 0).mean()),
        "winner21_rank_mean": float(m.winner21_rank.mean()),
        "winner21_rank_median": float(m.winner21_rank.median()),
        "winner21_hit_at_1": float(m.hit1.mean()),
        "winner21_hit_at_3": float(m.hit3.mean()),
        "winner21_hit_at_5": float(m.hit5.mean()),
        "winner21_hit_at_10": float(m.hit10.mean()),
        "actual_top5_overlap_mean": float(m.actual_top5_overlap.mean()),
        "ndcg_at_5_mean": float(m.ndcg5.mean()),
        "ndcg_at_10_mean": float(m.ndcg10.mean()),
        "ndcg_periods": int(m.ndcg5.notna().sum()),
        "top1_21d_cagr_proxy": monthly_cagr_proxy(m.top1_ret21),
        "top5ew_21d_cagr_proxy": monthly_cagr_proxy(m.top5ew_ret21),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--frozen-source", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    frozen_source = Path(args.frozen_source).resolve()
    sys.path.insert(0, str(frozen_source / "src"))
    from etf_trader.ma3.producer import FEATURES_42  # frozen baseline source

    panel = pd.read_pickle(args.panel).copy()
    panel["signal_date"] = pd.to_datetime(panel["signal_date"])
    panel["exit_date_63"] = pd.to_datetime(panel["exit_date_63"])

    missing = [c for c in FEATURES_42 if c not in panel.columns]
    if missing:
        raise RuntimeError(f"missing frozen Hybrid24 features: {missing}")
    for c in ("target_relevance", "target_multi_rank", "fwd_ret_21"):
        if c not in panel.columns:
            raise RuntimeError(f"missing required target/evaluation column: {c}")

    # Evidence V1 baseline: keep the productive XGB_B hyperparameters unchanged
    # and change only the learning objective to ranking. Pair generation is
    # explicitly top-k focused because this model is a RETRIEVER, not final sizing.
    config = {
        "objective": "rank:ndcg",
        "n_estimators": 400,
        "max_depth": 2,
        "learning_rate": 0.02,
        "subsample": 0.90,
        "colsample_bytree": 0.90,
        "min_child_weight": 12,
        "reg_lambda": 12.0,
        "reg_alpha": 0.2,
        "tree_method": "hist",
        "random_state": 101,
        "n_jobs": 2,
        "lambdarank_pair_method": "topk",
        "lambdarank_num_pair_per_sample": 10,
    }

    predictions = []
    audit = []
    for year in range(2017, 2027):
        cutoff = pd.Timestamp(f"{year}-01-01")
        next_cutoff = pd.Timestamp(f"{year + 1}-01-01")

        tr = panel[
            (panel.signal_date < cutoff)
            & (panel.exit_date_63 < cutoff)
            & panel.target_relevance.notna()
        ].copy()
        pr = panel[
            (panel.signal_date >= cutoff)
            & (panel.signal_date < next_cutoff)
        ].copy()
        if pr.empty:
            continue
        if tr.empty:
            raise RuntimeError(f"no maturity-safe training set for {year}")

        tr = tr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        pr = pr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)

        imp = SimpleImputer(strategy="median")
        xtr = imp.fit_transform(tr[list(FEATURES_42)])
        xp = imp.transform(pr[list(FEATURES_42)])
        y = tr.target_relevance.astype(int).to_numpy()
        qid = pd.factorize(tr.signal_date, sort=True)[0]

        model = XGBRanker(**config)
        model.fit(xtr, y, qid=qid, verbose=False)
        pr["LTR_SCORE"] = model.predict(xp)
        predictions.append(
            pr[[
                "signal_date", "ticker", "LTR_SCORE", "target_relevance",
                "target_multi_rank", "fwd_ret_21", "fwd_ret_42", "fwd_ret_63",
            ]]
        )

        maturity_ok = bool(
            (tr.signal_date < cutoff).all()
            and (tr.exit_date_63 < cutoff).all()
        )
        audit.append({
            "year": year,
            "cutoff": str(cutoff.date()),
            "n_train": int(len(tr)),
            "n_predict": int(len(pr)),
            "train_signal_dates": int(tr.signal_date.nunique()),
            "max_train_signal": str(tr.signal_date.max().date()),
            "max_train_exit63": str(tr.exit_date_63.max().date()),
            "maturity_ok": maturity_ok,
        })
        if not maturity_ok:
            raise RuntimeError(f"label maturity failure for {year}")

    pred = pd.concat(predictions, ignore_index=True)
    monthly = []
    for dt, g0 in pred.groupby("signal_date", sort=True):
        # 21-day trading diagnostics require only the 21-day outcome to be mature.
        # NDCG is evaluated separately and only when the 63-day-derived relevance
        # label is mature. This preserves the full 114-period 21-day comparison.
        g = g0.dropna(subset=["LTR_SCORE", "fwd_ret_21"]).copy()
        if len(g) < 2:
            continue
        gp = g.sort_values("LTR_SCORE", ascending=False).reset_index(drop=True)
        ga = g.sort_values("fwd_ret_21", ascending=False).reset_index(drop=True)
        winner = str(ga.iloc[0].ticker)
        predicted = gp.ticker.astype(str).tolist()
        winner_rank = predicted.index(winner) + 1
        actual_top5 = set(ga.head(5).ticker.astype(str))
        pred_top5 = set(gp.head(5).ticker.astype(str))

        ic = spearmanr(g.LTR_SCORE, g.fwd_ret_21, nan_policy="omit").statistic

        gr = g0.dropna(subset=["LTR_SCORE", "target_relevance"]).copy()
        if len(gr) >= 2:
            rel = gr.target_relevance.astype(float).to_numpy()[None, :]
            score = gr.LTR_SCORE.astype(float).to_numpy()[None, :]
            ndcg5 = float(ndcg_score(rel, score, k=5))
            ndcg10 = float(ndcg_score(rel, score, k=10))
        else:
            ndcg5 = float("nan")
            ndcg10 = float("nan")

        monthly.append({
            "signal_date": dt,
            "n_candidates": int(len(g)),
            "winner21": winner,
            "winner21_rank": int(winner_rank),
            "hit1": bool(winner_rank <= 1),
            "hit3": bool(winner_rank <= 3),
            "hit5": bool(winner_rank <= 5),
            "hit10": bool(winner_rank <= 10),
            "actual_top5_overlap": float(len(actual_top5 & pred_top5) / 5.0),
            "ic21": float(ic),
            "ndcg5": ndcg5,
            "ndcg10": ndcg10,
            "top1": str(gp.iloc[0].ticker),
            "top1_ret21": float(gp.iloc[0].fwd_ret_21),
            "top5ew_ret21": float(gp.head(5).fwd_ret_21.mean()),
        })

    m = pd.DataFrame(monthly)
    m["signal_date"] = pd.to_datetime(m.signal_date)
    m = m[m.signal_date >= pd.Timestamp("2017-01-01")].copy()

    summary = {
        "line": "Evidence V1",
        "test": "retriever_ltr_v1",
        "status": "DEVELOPMENT_EVIDENCE_NOT_PROMOTION",
        "universe": "Original149 frozen",
        "training": "annual expanding walk-forward, 63d-label maturity gate",
        "feature_set": "frozen Hybrid24 FEATURES_42",
        "label": "target_relevance=floor(target_multi_rank*10), clipped 0..9",
        "evaluation": "21d metrics on every mature 21d period; NDCG only where target_relevance is mature",
        "config": config,
        "full": period_summary(m),
        "2017_2022": period_summary(m[m.signal_date < pd.Timestamp("2023-01-01")]),
        "2023_2026": period_summary(m[m.signal_date >= pd.Timestamp("2023-01-01")]),
        "fit_audit_all_maturity_ok": bool(pd.DataFrame(audit).maturity_ok.all()),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pred.to_csv(out / "PREDICTIONS.csv", index=False)
    m.to_csv(out / "MONTHLY.csv", index=False)
    pd.DataFrame(audit).to_csv(out / "FIT_AUDIT.csv", index=False)
    (out / "CONFIG.json").write_text(json.dumps(config, indent=2) + "\n")
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
