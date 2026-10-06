#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRanker


def monthly_cagr_proxy(x: pd.Series) -> float:
    r = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    if len(r) == 0 or np.any(r <= -1):
        return float("nan")
    return float(np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0)


def summary(m: pd.DataFrame) -> dict:
    if m.empty:
        return {"n": 0}
    corr = spearmanr(m.pair_margin, m.pair_top1_minus_top2_ret21, nan_policy="omit").statistic
    return {
        "n": int(len(m)),
        "pair_top1_21d_cagr_proxy": monthly_cagr_proxy(m.pair_top1_ret21),
        "ltr_top1_21d_cagr_proxy": monthly_cagr_proxy(m.ltr_top1_ret21),
        "pair_top1_exact_winner_rate": float(m.pair_top1_is_winner.mean()),
        "ltr_top1_exact_winner_rate": float(m.ltr_top1_is_winner.mean()),
        "pair_top2_contains_winner_rate": float(m.pair_top2_contains_winner.mean()),
        "ltr_top2_contains_winner_rate": float(m.ltr_top2_contains_winner.mean()),
        "ltr_top10_contains_winner_rate": float(m.winner_in_ltr_top10.mean()),
        "pair_margin_vs_top1_minus_top2_ret21_spearman": float(corr),
    }


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

    # Same retriever configuration as validated retriever_ltr_v1.
    ltr_cfg = {
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

    # Build strictly OOS retriever predictions from 2011 onward.  Earlier OOS
    # predictions provide mature pairwise history before the 2017 evaluation.
    pred_parts = []
    ltr_audit = []
    for year in range(2011, 2027):
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
        if tr.empty or pr.empty:
            continue
        tr = tr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        pr = pr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        imp = SimpleImputer(strategy="median")
        xtr = imp.fit_transform(tr[list(FEATURES_42)])
        xp = imp.transform(pr[list(FEATURES_42)])
        qid = pd.factorize(tr.signal_date, sort=True)[0]
        model = XGBRanker(**ltr_cfg)
        model.fit(xtr, tr.target_relevance.astype(int).to_numpy(), qid=qid, verbose=False)
        pr["LTR_SCORE"] = model.predict(xp)
        pr["LTR_RANK_PCT"] = pr.groupby("signal_date").LTR_SCORE.rank(pct=True, method="average")
        pred_parts.append(pr)
        ok = bool((tr.signal_date < cutoff).all() and (tr.exit_date_63 < cutoff).all())
        ltr_audit.append({
            "year": year,
            "n_train": int(len(tr)),
            "n_predict": int(len(pr)),
            "max_train_exit63": str(tr.exit_date_63.max().date()),
            "cutoff": str(cutoff.date()),
            "maturity_ok": ok,
        })
        if not ok:
            raise RuntimeError(f"LTR maturity gate failed for {year}")

    oos = pd.concat(pred_parts, ignore_index=True)

    # Historical OOS shortlist pairs.  Each unordered pair is emitted in both
    # directions to enforce an antisymmetric pairwise learning problem.
    feature_names = [f"d_{c}" for c in FEATURES_42] + ["d_ltr_rank"]
    pair_rows = []
    for dt, g in oos.groupby("signal_date", sort=True):
        s = g.sort_values("LTR_SCORE", ascending=False).head(10).reset_index(drop=True)
        for i, j in combinations(range(len(s)), 2):
            a, b = s.iloc[i], s.iloc[j]
            if pd.isna(a.target_multi_rank) or pd.isna(b.target_multi_rank):
                continue
            va = a[list(FEATURES_42)].astype(float).to_numpy()
            vb = b[list(FEATURES_42)].astype(float).to_numpy()
            diff = np.r_[va - vb, float(a.LTR_RANK_PCT - b.LTR_RANK_PCT)]
            y = int(a.target_multi_rank > b.target_multi_rank)
            exit63 = max(pd.Timestamp(a.exit_date_63), pd.Timestamp(b.exit_date_63))
            base = {"signal_date": dt, "exit_date_63": exit63}
            pair_rows.append({**base, "y": y, **dict(zip(feature_names, diff))})
            pair_rows.append({**base, "y": 1 - y, **dict(zip(feature_names, -diff))})
    pairs = pd.DataFrame(pair_rows)

    rows = []
    rerank_audit = []
    for year in range(2017, 2027):
        cutoff = pd.Timestamp(f"{year}-01-01")
        next_cutoff = pd.Timestamp(f"{year + 1}-01-01")
        train_pairs = pairs[pairs.exit_date_63 < cutoff].copy()
        current = oos[(oos.signal_date >= cutoff) & (oos.signal_date < next_cutoff)].copy()
        if current.empty:
            continue
        if len(train_pairs) < 500:
            raise RuntimeError(f"insufficient mature OOS pair history for {year}")

        model = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(C=1.0, max_iter=500, solver="liblinear", random_state=101),
        )
        model.fit(train_pairs[feature_names], train_pairs.y.astype(int))
        rerank_audit.append({
            "year": year,
            "cutoff": str(cutoff.date()),
            "n_train_pairs": int(len(train_pairs)),
            "max_train_pair_exit63": str(pd.to_datetime(train_pairs.exit_date_63).max().date()),
            "maturity_ok": bool((pd.to_datetime(train_pairs.exit_date_63) < cutoff).all()),
        })

        for dt, g in current.groupby("signal_date", sort=True):
            shortlist = g.sort_values("LTR_SCORE", ascending=False).head(10).reset_index(drop=True)
            if shortlist.fwd_ret_21.notna().sum() < 2:
                continue

            pair_features = []
            pair_indices = []
            for i, j in combinations(range(len(shortlist)), 2):
                a, b = shortlist.iloc[i], shortlist.iloc[j]
                va = a[list(FEATURES_42)].astype(float).to_numpy()
                vb = b[list(FEATURES_42)].astype(float).to_numpy()
                pair_features.append(np.r_[va - vb, float(a.LTR_RANK_PCT - b.LTR_RANK_PCT)])
                pair_indices.append((i, j))
            probs = model.predict_proba(pd.DataFrame(pair_features, columns=feature_names))[:, 1]

            score = np.zeros(len(shortlist), float)
            count = np.zeros(len(shortlist), float)
            for (i, j), p in zip(pair_indices, probs):
                score[i] += p; count[i] += 1
                score[j] += 1.0 - p; count[j] += 1
            rr = shortlist.copy()
            rr["PAIR_SCORE"] = score / count
            rr = rr.sort_values("PAIR_SCORE", ascending=False).reset_index(drop=True)

            actual = g.dropna(subset=["fwd_ret_21"]).sort_values("fwd_ret_21", ascending=False).reset_index(drop=True)
            winner = str(actual.iloc[0].ticker)
            rows.append({
                "signal_date": dt,
                "pair_top1": str(rr.iloc[0].ticker),
                "pair_top2": str(rr.iloc[1].ticker),
                "ltr_top1": str(shortlist.iloc[0].ticker),
                "ltr_top2": str(shortlist.iloc[1].ticker),
                "pair_top1_ret21": float(rr.iloc[0].fwd_ret_21),
                "pair_top2_ret21": float(rr.iloc[1].fwd_ret_21),
                "ltr_top1_ret21": float(shortlist.iloc[0].fwd_ret_21),
                "pair_top1_is_winner": bool(str(rr.iloc[0].ticker) == winner),
                "ltr_top1_is_winner": bool(str(shortlist.iloc[0].ticker) == winner),
                "pair_top2_contains_winner": bool(winner in set(rr.head(2).ticker.astype(str))),
                "ltr_top2_contains_winner": bool(winner in set(shortlist.head(2).ticker.astype(str))),
                "winner_in_ltr_top10": bool(winner in set(shortlist.ticker.astype(str))),
                "pair_margin": float(rr.iloc[0].PAIR_SCORE - rr.iloc[1].PAIR_SCORE),
                "pair_top1_minus_top2_ret21": float(rr.iloc[0].fwd_ret_21 - rr.iloc[1].fwd_ret_21),
            })

    monthly = pd.DataFrame(rows)
    monthly["signal_date"] = pd.to_datetime(monthly.signal_date)
    rerank_audit_df = pd.DataFrame(rerank_audit)
    if not bool(rerank_audit_df.maturity_ok.all()):
        raise RuntimeError("pairwise maturity gate failed")

    result = {
        "line": "Evidence V1",
        "test": "pairwise_reranker_v1",
        "status": "DEVELOPMENT_EVIDENCE_NOT_PROMOTION",
        "universe": "Original149 frozen",
        "retriever": "LTR v1 top10, OOS annual expanding from 2011",
        "pair_label": "candidate A target_multi_rank > candidate B target_multi_rank",
        "pair_features": "differences of frozen Hybrid24 FEATURES_42 + LTR percentile-rank difference",
        "reranker": "L2 logistic regression C=1.0, annual expanding",
        "full": summary(monthly),
        "2017_2022": summary(monthly[monthly.signal_date < pd.Timestamp("2023-01-01")]),
        "2023_2026": summary(monthly[monthly.signal_date >= pd.Timestamp("2023-01-01")]),
        "ltr_maturity_all_ok": bool(pd.DataFrame(ltr_audit).maturity_ok.all()),
        "pairwise_maturity_all_ok": bool(rerank_audit_df.maturity_ok.all()),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(out / "MONTHLY.csv", index=False)
    pd.DataFrame(ltr_audit).to_csv(out / "LTR_FIT_AUDIT.csv", index=False)
    rerank_audit_df.to_csv(out / "PAIRWISE_FIT_AUDIT.csv", index=False)
    (out / "SUMMARY.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
