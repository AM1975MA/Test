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

EVAL_START = pd.Timestamp("2017-01-01")
EVAL_END = pd.Timestamp("2026-07-01")
MONTH_FEATURES = [f"month_{m:02d}" for m in range(1, 13)]
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
EXPECTED_BASELINE = {
    "n": 114,
    "top1_hits": 10,
    "top5_hits": 32,
    "top10_hits": 47,
    "top1_cagr": 0.220630708412056,
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cagr_proxy(x: pd.Series) -> float:
    r = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    if len(r) == 0 or np.any(r <= -1):
        return float("nan")
    return float(np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0)


def metrics(monthly: pd.DataFrame) -> dict:
    if monthly.empty:
        return {"n": 0}
    return {
        "n": int(len(monthly)),
        "top1_hits": int(monthly.hit1.sum()),
        "top3_hits": int(monthly.hit3.sum()),
        "top5_hits": int(monthly.hit5.sum()),
        "top10_hits": int(monthly.hit10.sum()),
        "top1_hit_rate": float(monthly.hit1.mean()),
        "top5_hit_rate": float(monthly.hit5.mean()),
        "top10_hit_rate": float(monthly.hit10.mean()),
        "winner_rank_mean": float(monthly.winner_rank.mean()),
        "winner_rank_median": float(monthly.winner_rank.median()),
        "mean_ic21": float(monthly.ic21.mean()),
        "positive_ic21": float((monthly.ic21 > 0).mean()),
        "ndcg5_mean": float(monthly.ndcg5.mean()),
        "ndcg10_mean": float(monthly.ndcg10.mean()),
        "top1_cagr_proxy": cagr_proxy(monthly.top1_ret21),
        "top5ew_cagr_proxy": cagr_proxy(monthly.top5ew_ret21),
    }


def evaluate(pred: pd.DataFrame, score_col: str) -> pd.DataFrame:
    rows = []
    for dt, g0 in pred.groupby("signal_date", sort=True):
        if dt < EVAL_START or dt >= EVAL_END:
            continue
        g = g0.dropna(subset=[score_col, "fwd_ret_21"]).copy()
        if len(g) < 10:
            continue
        gp = g.sort_values([score_col, "ticker"], ascending=[False, True]).reset_index(drop=True)
        ga = g.sort_values(["fwd_ret_21", "ticker"], ascending=[False, True]).reset_index(drop=True)
        winner = str(ga.iloc[0].ticker)
        names = gp.ticker.astype(str).tolist()
        rank = names.index(winner) + 1
        ic = spearmanr(g[score_col], g.fwd_ret_21, nan_policy="omit").statistic
        gr = g0.dropna(subset=[score_col, "target_relevance"]).copy()
        if len(gr) >= 2:
            rel = gr.target_relevance.astype(float).to_numpy()[None, :]
            score = gr[score_col].astype(float).to_numpy()[None, :]
            ndcg5 = float(ndcg_score(rel, score, k=5))
            ndcg10 = float(ndcg_score(rel, score, k=10))
        else:
            ndcg5 = float("nan")
            ndcg10 = float("nan")
        rows.append({
            "signal_date": dt,
            "winner": winner,
            "winner_rank": int(rank),
            "hit1": bool(rank <= 1),
            "hit3": bool(rank <= 3),
            "hit5": bool(rank <= 5),
            "hit10": bool(rank <= 10),
            "ic21": float(ic),
            "ndcg5": ndcg5,
            "ndcg10": ndcg10,
            "top1": str(gp.iloc[0].ticker),
            "top1_ret21": float(gp.iloc[0].fwd_ret_21),
            "top5ew_ret21": float(gp.head(5).fwd_ret_21.mean()),
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out["signal_date"] = pd.to_datetime(out.signal_date)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--frozen-source", required=True)
    ap.add_argument("--baseline-checkpoint", required=True)
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
        raise RuntimeError("panel has duplicate signal_date/ticker keys")

    month = panel.signal_date.dt.month.astype(int)
    for m in range(1, 13):
        panel[f"month_{m:02d}"] = (month == m).astype(np.int8)
    if not (panel[MONTH_FEATURES].sum(axis=1) == 1).all():
        raise RuntimeError("calendar one-hot encoding invalid")

    feature_cols = list(FEATURES_42) + MONTH_FEATURES
    predictions = []
    audits = []
    for year in range(2017, 2027):
        cutoff = pd.Timestamp(f"{year}-01-01")
        next_cutoff = pd.Timestamp(f"{year+1}-01-01")
        tr = panel[(panel.signal_date < cutoff) & (panel.exit_date_63 < cutoff) & panel.target_relevance.notna()].copy()
        pr = panel[(panel.signal_date >= cutoff) & (panel.signal_date < next_cutoff)].copy()
        if pr.empty:
            continue
        if tr.empty:
            raise RuntimeError(f"no maturity-safe training rows for {year}")
        tr = tr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        pr = pr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        imp = SimpleImputer(strategy="median")
        xtr = imp.fit_transform(tr[feature_cols])
        xp = imp.transform(pr[feature_cols])
        qid = pd.factorize(tr.signal_date, sort=True)[0]
        model = XGBRanker(**CONFIG)
        model.fit(xtr, tr.target_relevance.astype(int).to_numpy(), qid=qid, verbose=False)
        pr["CALENDAR_LTR_SCORE"] = model.predict(xp)
        predictions.append(pr[[
            "signal_date", "ticker", "CALENDAR_LTR_SCORE",
            "target_relevance", "target_multi_rank", "fwd_ret_21", "fwd_ret_42", "fwd_ret_63",
        ]])
        maturity_ok = bool((tr.signal_date < cutoff).all() and (tr.exit_date_63 < cutoff).all())
        audits.append({
            "year": year,
            "cutoff": str(cutoff.date()),
            "n_train": int(len(tr)),
            "n_predict": int(len(pr)),
            "max_train_signal": str(tr.signal_date.max().date()),
            "max_train_exit63": str(tr.exit_date_63.max().date()),
            "maturity_ok": maturity_ok,
        })
        if not maturity_ok:
            raise RuntimeError(f"maturity failure {year}")

    pred = pd.concat(predictions, ignore_index=True)
    pred["signal_date"] = pd.to_datetime(pred.signal_date)
    calendar_monthly = evaluate(pred, "CALENDAR_LTR_SCORE")
    if len(calendar_monthly) != 114:
        raise RuntimeError(f"expected 114 calendar evaluation dates, got {len(calendar_monthly)}")

    cp = Path(args.baseline_checkpoint)
    base_scores = pd.read_csv(cp / "OOS_PREDICTIONS.csv", parse_dates=["signal_date"])
    evaluation_cols = panel[["signal_date", "ticker", "fwd_ret_21", "target_relevance"]].copy()
    base = base_scores.merge(evaluation_cols, on=["signal_date", "ticker"], how="left", validate="one_to_one")
    base_monthly = evaluate(base, "LTR_SCORE")
    bm = metrics(base_monthly)
    if bm["n"] != EXPECTED_BASELINE["n"]:
        raise RuntimeError(f"baseline n mismatch: {bm['n']}")
    for key in ("top1_hits", "top5_hits", "top10_hits"):
        if bm[key] != EXPECTED_BASELINE[key]:
            raise RuntimeError(f"baseline {key} mismatch: {bm[key]} != {EXPECTED_BASELINE[key]}")
    if not np.isclose(bm["top1_cagr_proxy"], EXPECTED_BASELINE["top1_cagr"], rtol=0, atol=1e-12):
        raise RuntimeError(f"baseline Top1 CAGR mismatch: {bm['top1_cagr_proxy']}")

    cm = metrics(calendar_monthly)
    advance = bool(
        cm["top5_hits"] > EXPECTED_BASELINE["top5_hits"]
        and cm["top10_hits"] > EXPECTED_BASELINE["top10_hits"]
        and cm["top1_hits"] >= EXPECTED_BASELINE["top1_hits"]
        and cm["top1_cagr_proxy"] >= EXPECTED_BASELINE["top1_cagr"]
    )
    pre = calendar_monthly[calendar_monthly.signal_date < pd.Timestamp("2023-01-01")]
    post = calendar_monthly[calendar_monthly.signal_date >= pd.Timestamp("2023-01-01")]
    result = {
        "line": "Evidence V2",
        "test": "retriever_calendar_context_v1",
        "status": "DEVELOPMENT_EVIDENCE_ADVANCE" if advance else "DEVELOPMENT_EVIDENCE_REJECTED",
        "universe": "Original149 frozen; burned development set only",
        "new_information": "twelve fixed one-hot month-of-year indicators derived only from signal_date",
        "calendar_features": MONTH_FEATURES,
        "model_change": "none except appending twelve month-of-year one-hot features to frozen FEATURES_42",
        "config": CONFIG,
        "baseline": bm,
        "calendar_context": cm,
        "2017_2022_calendar_context": metrics(pre),
        "2023_2026_calendar_context": metrics(post),
        "primary_gate": {
            "top5_hits_gt_32": bool(cm["top5_hits"] > 32),
            "top10_hits_gt_47": bool(cm["top10_hits"] > 47),
            "top1_hits_ge_10": bool(cm["top1_hits"] >= 10),
            "top1_cagr_ge_0_220630708412056": bool(cm["top1_cagr_proxy"] >= EXPECTED_BASELINE["top1_cagr"]),
        },
        "decision": (
            "ADVANCE: freeze a new disjoint Holdout-B before any promotion test"
            if advance
            else "REJECT: close Evidence V2 development on Original149; no calendar variants or further information-block tests"
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pred.to_csv(out / "PREDICTIONS.csv", index=False)
    calendar_monthly.to_csv(out / "MONTHLY_CALENDAR.csv", index=False)
    base_monthly.to_csv(out / "MONTHLY_BASELINE.csv", index=False)
    pd.DataFrame(audits).to_csv(out / "FIT_AUDIT.csv", index=False)
    (out / "SUMMARY.json").write_text(json.dumps(result, indent=2) + "\n")
    files = ["PREDICTIONS.csv", "MONTHLY_CALENDAR.csv", "MONTHLY_BASELINE.csv", "FIT_AUDIT.csv", "SUMMARY.json"]
    (out / "RESULT_MANIFEST.json").write_text(json.dumps({
        "test": "retriever_calendar_context_v1",
        "files_sha256": {name: sha256_file(out / name) for name in files},
    }, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
