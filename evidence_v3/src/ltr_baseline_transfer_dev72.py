#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.metrics import ndcg_score
from xgboost import XGBRanker

CONFIG = {
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
EVAL_START = pd.Timestamp("2017-01-01")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cagr_proxy(x: pd.Series) -> float:
    r = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    if len(r) == 0 or np.any(r <= -1):
        return float("nan")
    return float(np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--frozen-source", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    frozen_source = Path(args.frozen_source).resolve()
    sys.path.insert(0, str(frozen_source / "src"))
    from etf_trader.ma3.producer import FEATURES_42

    panel = pd.read_pickle(args.panel).copy()
    panel["signal_date"] = pd.to_datetime(panel.signal_date)
    panel["exit_date_63"] = pd.to_datetime(panel.exit_date_63)

    required = list(FEATURES_42) + [
        "signal_date", "ticker", "exit_date_63", "target_relevance",
        "target_multi_rank", "fwd_ret_21", "fwd_ret_42", "fwd_ret_63",
    ]
    missing = [c for c in required if c not in panel.columns]
    if missing:
        raise RuntimeError(f"panel missing required columns: {missing}")
    if panel.duplicated(["signal_date", "ticker"]).any():
        raise RuntimeError("duplicate signal_date/ticker keys")

    pred_parts = []
    audits = []
    for year in range(2017, 2027):
        cutoff = pd.Timestamp(f"{year}-01-01")
        next_cutoff = pd.Timestamp(f"{year+1}-01-01")
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
            raise RuntimeError(f"no maturity-safe training data for {year}")

        tr = tr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        pr = pr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        imp = SimpleImputer(strategy="median")
        xtr = imp.fit_transform(tr[list(FEATURES_42)])
        xp = imp.transform(pr[list(FEATURES_42)])
        qid = pd.factorize(tr.signal_date, sort=True)[0]
        model = XGBRanker(**CONFIG)
        model.fit(
            xtr,
            tr.target_relevance.astype(int).to_numpy(),
            qid=qid,
            verbose=False,
        )
        pr["LTR_SCORE"] = model.predict(xp)
        pred_parts.append(pr[[
            "signal_date", "ticker", "LTR_SCORE", "target_relevance",
            "target_multi_rank", "fwd_ret_21", "fwd_ret_42", "fwd_ret_63",
        ]])

        maturity_ok = bool(
            (tr.signal_date < cutoff).all() and (tr.exit_date_63 < cutoff).all()
        )
        audits.append({
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
            raise RuntimeError(f"maturity gate failed for {year}")

    if not pred_parts:
        raise RuntimeError("no OOS predictions")
    pred = pd.concat(pred_parts, ignore_index=True)
    pred["signal_date"] = pd.to_datetime(pred.signal_date)

    monthly = []
    for dt, g0 in pred.groupby("signal_date", sort=True):
        if dt < EVAL_START:
            continue
        g = g0.dropna(subset=["LTR_SCORE", "fwd_ret_21"]).copy()
        if len(g) < 10:
            continue
        gp = g.sort_values(["LTR_SCORE", "ticker"], ascending=[False, True]).reset_index(drop=True)
        ga = g.sort_values(["fwd_ret_21", "ticker"], ascending=[False, True]).reset_index(drop=True)
        winner = str(ga.iloc[0].ticker)
        predicted = gp.ticker.astype(str).tolist()
        winner_rank = predicted.index(winner) + 1
        n = int(len(g))
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
            "n_candidates": n,
            "winner": winner,
            "winner_rank": int(winner_rank),
            "winner_rank_normalized": float((winner_rank - 1) / max(1, n - 1)),
            "hit1": bool(winner_rank <= 1),
            "hit3": bool(winner_rank <= 3),
            "hit5": bool(winner_rank <= 5),
            "hit10": bool(winner_rank <= 10),
            "random_p1": 1.0 / n,
            "random_p5": min(5, n) / n,
            "random_p10": min(10, n) / n,
            "ic21": float(ic),
            "ndcg5": ndcg5,
            "ndcg10": ndcg10,
            "top1": str(gp.iloc[0].ticker),
            "top1_ret21": float(gp.iloc[0].fwd_ret_21),
            "top5ew_ret21": float(gp.head(5).fwd_ret_21.mean()),
            "universe_ew_ret21": float(g.fwd_ret_21.mean()),
        })

    m = pd.DataFrame(monthly)
    if m.empty:
        raise RuntimeError("no evaluation periods")
    m["signal_date"] = pd.to_datetime(m.signal_date)

    exp1 = float(m.random_p1.sum())
    exp5 = float(m.random_p5.sum())
    exp10 = float(m.random_p10.sum())
    obs1 = int(m.hit1.sum())
    obs5 = int(m.hit5.sum())
    obs10 = int(m.hit10.sum())
    top1_cagr = cagr_proxy(m.top1_ret21)
    top5_cagr = cagr_proxy(m.top5ew_ret21)
    universe_cagr = cagr_proxy(m.universe_ew_ret21)
    enrich5 = float(obs5 / exp5) if exp5 > 0 else float("nan")
    enrich10 = float(obs10 / exp10) if exp10 > 0 else float("nan")

    gate = {
        "top5_enrichment_ge_2x": bool(enrich5 >= 2.0),
        "top10_enrichment_ge_1_5x": bool(enrich10 >= 1.5),
        "top1_cagr_gt_universe_ew": bool(top1_cagr > universe_cagr),
        "top5ew_cagr_gt_universe_ew": bool(top5_cagr > universe_cagr),
    }
    passed = bool(all(gate.values()))

    summary = {
        "line": "Evidence V3",
        "test": "ltr_baseline_transfer_dev72",
        "status": "DEVELOPMENT_TRANSFER_PASS" if passed else "DEVELOPMENT_TRANSFER_FAIL",
        "universe": "Dev72 frozen; disjoint new development universe",
        "model": "exact Evidence V1 Retriever LTR v1 architecture retrained causally on Dev72",
        "config": CONFIG,
        "evaluation": {
            "n_periods": int(len(m)),
            "first_signal": str(m.signal_date.min().date()),
            "last_signal": str(m.signal_date.max().date()),
            "mean_candidates": float(m.n_candidates.mean()),
            "min_candidates": int(m.n_candidates.min()),
            "max_candidates": int(m.n_candidates.max()),
        },
        "retrieval": {
            "top1_hits": obs1,
            "top3_hits": int(m.hit3.sum()),
            "top5_hits": obs5,
            "top10_hits": obs10,
            "random_expected_top1_hits": exp1,
            "random_expected_top5_hits": exp5,
            "random_expected_top10_hits": exp10,
            "top1_enrichment": float(obs1 / exp1) if exp1 > 0 else float("nan"),
            "top5_enrichment": enrich5,
            "top10_enrichment": enrich10,
            "winner_rank_mean": float(m.winner_rank.mean()),
            "winner_rank_median": float(m.winner_rank.median()),
            "winner_rank_normalized_mean": float(m.winner_rank_normalized.mean()),
            "mean_ic21": float(m.ic21.mean()),
            "positive_ic21": float((m.ic21 > 0).mean()),
            "ndcg5_mean": float(m.ndcg5.mean()),
            "ndcg10_mean": float(m.ndcg10.mean()),
        },
        "economics": {
            "top1_cagr_proxy": top1_cagr,
            "top5ew_cagr_proxy": top5_cagr,
            "universe_ew_cagr_proxy": universe_cagr,
            "top1_minus_universe_cagr_pp": float((top1_cagr - universe_cagr) * 100.0),
            "top5ew_minus_universe_cagr_pp": float((top5_cagr - universe_cagr) * 100.0),
        },
        "primary_gate": gate,
        "decision": (
            "PASS: frozen LTR retrieval transfers to Dev72; preregister exactly one new V3 decision-layer hypothesis"
            if passed else
            "FAIL: do not tune LTR target/hyperparameters/features/K on Dev72; reassess V3 architecture before any additional model run"
        ),
        "fit_audit_all_maturity_ok": bool(pd.DataFrame(audits).maturity_ok.all()),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pred.to_csv(out / "PREDICTIONS.csv", index=False)
    m.to_csv(out / "MONTHLY.csv", index=False)
    pd.DataFrame(audits).to_csv(out / "FIT_AUDIT.csv", index=False)
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    files = ["PREDICTIONS.csv", "MONTHLY.csv", "FIT_AUDIT.csv", "SUMMARY.json"]
    (out / "RESULT_MANIFEST.json").write_text(json.dumps({
        "test": "ltr_baseline_transfer_dev72",
        "files_sha256": {name: sha256_file(out / name) for name in files},
    }, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
