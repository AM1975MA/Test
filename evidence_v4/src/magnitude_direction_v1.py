#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from xgboost import XGBClassifier, XGBRanker

LTR_CFG = {
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
DIR_CFG = {
    "objective": "binary:logistic",
    "n_estimators": 300,
    "max_depth": 2,
    "learning_rate": 0.02,
    "subsample": 0.85,
    "colsample_bytree": 0.75,
    "min_child_weight": 20,
    "reg_lambda": 20.0,
    "reg_alpha": 1.0,
    "tree_method": "hist",
    "random_state": 211,
    "n_jobs": 2,
    "scale_pos_weight": 1.0,
    "eval_metric": "logloss",
}
EVAL_START = pd.Timestamp("2017-01-01")
K = 10


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
    ann_mean = float(np.mean(r) * 12.0)
    return {
        "n": int(len(r)),
        "cagr_proxy": cagr(pd.Series(r)),
        "annual_vol": vol,
        "sharpe_rf0": float(ann_mean / vol) if vol > 0 else float("nan"),
        "max_drawdown": max_drawdown(pd.Series(r)),
        "positive_period_rate": float(np.mean(r > 0)),
        "mean_period_return": float(np.mean(r)),
        "worst_period": float(np.min(r)),
        "best_period": float(np.max(r)),
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
    panel["exit_date_21"] = pd.to_datetime(panel.exit_date_21)
    panel["exit_date_63"] = pd.to_datetime(panel.exit_date_63)
    required = list(FEATURES_42) + [
        "signal_date", "ticker", "target_relevance", "fwd_ret_21",
        "exit_date_21", "exit_date_63",
    ]
    missing = [c for c in required if c not in panel.columns]
    if missing:
        raise RuntimeError(f"panel missing required columns: {missing}")
    if panel.duplicated(["signal_date", "ticker"]).any():
        raise RuntimeError("duplicate panel signal_date/ticker")

    feature_cols = list(FEATURES_42)

    # Stage 1: exact frozen LTR architecture, fully OOS by calendar year.
    s1_parts = []
    s1_audit = []
    for year in range(2011, 2027):
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
        if tr.empty or pr.empty:
            continue
        tr = tr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        pr = pr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        imp = SimpleImputer(strategy="median")
        xtr = imp.fit_transform(tr[feature_cols])
        xp = imp.transform(pr[feature_cols])
        qid = pd.factorize(tr.signal_date, sort=True)[0]
        model = XGBRanker(**LTR_CFG)
        model.fit(xtr, tr.target_relevance.astype(int).to_numpy(), qid=qid, verbose=False)
        pr["LTR_SCORE"] = model.predict(xp)
        pr = pr.sort_values(["signal_date", "LTR_SCORE", "ticker"], ascending=[True, False, True])
        pr["LTR_RANK"] = pr.groupby("signal_date").cumcount() + 1
        n = pr.groupby("signal_date").ticker.transform("count").astype(float)
        pr["LTR_POSITION"] = np.where(n > 1, 1.0 - (pr.LTR_RANK.astype(float)-1.0)/(n-1.0), 1.0)
        s1_parts.append(pr[[
            "signal_date", "ticker", "LTR_SCORE", "LTR_RANK", "LTR_POSITION",
            "fwd_ret_21", "exit_date_21", "target_relevance", *feature_cols,
        ]])
        maturity_ok = bool((tr.signal_date < cutoff).all() and (tr.exit_date_63 < cutoff).all())
        s1_audit.append({
            "year": year, "cutoff": str(cutoff.date()),
            "n_train": int(len(tr)), "n_predict": int(len(pr)),
            "train_dates": int(tr.signal_date.nunique()),
            "max_train_exit63": str(tr.exit_date_63.max().date()),
            "maturity_ok": maturity_ok,
        })
        if not maturity_ok:
            raise RuntimeError(f"Stage1 maturity failure in {year}")

    if not s1_parts:
        raise RuntimeError("no Stage1 OOS predictions")
    s1 = pd.concat(s1_parts, ignore_index=True)
    s1["signal_date"] = pd.to_datetime(s1.signal_date)
    s1["exit_date_21"] = pd.to_datetime(s1.exit_date_21)
    s1_top10 = s1[s1.LTR_RANK <= K].copy()
    sizes = s1_top10.groupby("signal_date").size()
    if (sizes > K).any():
        raise RuntimeError("Stage1 Top10 size exceeds K")

    # Stage 2: sign model trained only on historical OOS Stage1 Top10 rows.
    dir_features = feature_cols + ["LTR_POSITION"]
    s2_parts = []
    s2_audit = []
    for year in range(2017, 2027):
        cutoff = pd.Timestamp(f"{year}-01-01")
        next_cutoff = pd.Timestamp(f"{year+1}-01-01")
        tr = s1_top10[
            (s1_top10.signal_date < cutoff)
            & (s1_top10.exit_date_21 < cutoff)
            & s1_top10.fwd_ret_21.notna()
        ].copy()
        pr = s1_top10[
            (s1_top10.signal_date >= cutoff)
            & (s1_top10.signal_date < next_cutoff)
        ].copy()
        if pr.empty:
            continue
        if tr.empty:
            raise RuntimeError(f"no causal Stage2 training data for {year}")
        tr["SIGN21"] = (tr.fwd_ret_21 > 0).astype(int)
        if tr.SIGN21.nunique() != 2:
            raise RuntimeError(f"Stage2 training has only one class in {year}")
        imp = SimpleImputer(strategy="median")
        xtr = imp.fit_transform(tr[dir_features])
        xp = imp.transform(pr[dir_features])
        clf = XGBClassifier(**DIR_CFG)
        clf.fit(xtr, tr.SIGN21.to_numpy(), verbose=False)
        pr["P_POS21"] = clf.predict_proba(xp)[:, 1]
        s2_parts.append(pr[[
            "signal_date", "ticker", "LTR_SCORE", "LTR_RANK", "LTR_POSITION",
            "P_POS21", "fwd_ret_21",
        ]])
        causal_ok = bool((tr.signal_date < cutoff).all() and (tr.exit_date_21 < cutoff).all())
        s2_audit.append({
            "year": year, "cutoff": str(cutoff.date()),
            "n_train_rows": int(len(tr)),
            "train_signal_dates": int(tr.signal_date.nunique()),
            "positive_class_rate": float(tr.SIGN21.mean()),
            "n_predict_rows": int(len(pr)),
            "max_train_exit21": str(tr.exit_date_21.max().date()),
            "causal_ok": causal_ok,
        })
        if not causal_ok:
            raise RuntimeError(f"Stage2 causality failure in {year}")

    if not s2_parts:
        raise RuntimeError("no Stage2 predictions")
    s2 = pd.concat(s2_parts, ignore_index=True)
    s2["signal_date"] = pd.to_datetime(s2.signal_date)

    # Full Stage1 rows for universe/global comparators on exactly Stage2 evaluation dates.
    monthly = []
    for dt, cand0 in s2.groupby("signal_date", sort=True):
        if dt < EVAL_START:
            continue
        cand = cand0.dropna(subset=["P_POS21", "fwd_ret_21"]).copy()
        full = s1[(s1.signal_date == dt) & s1.fwd_ret_21.notna()].copy()
        if len(cand) != K or len(full) < K:
            continue
        cand_ltr = cand.sort_values(["LTR_SCORE", "ticker"], ascending=[False, True]).reset_index(drop=True)
        cand_dir = cand.sort_values(["P_POS21", "ticker"], ascending=[False, True]).reset_index(drop=True)
        full_ltr = full.sort_values(["LTR_SCORE", "ticker"], ascending=[False, True]).reset_index(drop=True)
        actual = full.sort_values(["fwd_ret_21", "ticker"], ascending=[False, True]).reset_index(drop=True)
        winner = str(actual.iloc[0].ticker)
        loser = str(actual.iloc[-1].ticker)
        top10_names = set(cand.ticker.astype(str))
        selected = cand_dir.iloc[0]
        monthly.append({
            "signal_date": dt,
            "n_candidates": int(len(full)),
            "winner": winner,
            "loser": loser,
            "stage1_top10_contains_winner": winner in top10_names,
            "stage1_top10_contains_loser": loser in top10_names,
            "stage1_top1": str(full_ltr.iloc[0].ticker),
            "stage1_top1_ret21": float(full_ltr.iloc[0].fwd_ret_21),
            "stage1_top10ew_ret21": float(cand_ltr.head(K).fwd_ret_21.mean()),
            "universe_ew_ret21": float(full.fwd_ret_21.mean()),
            "oracle_top10_best_ret21": float(cand.fwd_ret_21.max()),
            "direction_top1": str(selected.ticker),
            "direction_p_pos21": float(selected.P_POS21),
            "direction_top1_ret21": float(selected.fwd_ret_21),
            "direction_top1_positive": bool(selected.fwd_ret_21 > 0),
            "direction_top1_is_global_winner": bool(str(selected.ticker) == winner),
        })

    m = pd.DataFrame(monthly)
    if m.empty:
        raise RuntimeError("no evaluation months")
    m["signal_date"] = pd.to_datetime(m.signal_date)
    pre = m[m.signal_date < pd.Timestamp("2023-01-01")].copy()
    post = m[m.signal_date >= pd.Timestamp("2023-01-01")].copy()
    if pre.empty or post.empty:
        raise RuntimeError("fixed subperiod missing")

    exp_top10_winner = float((K / m.n_candidates).sum())
    exp_top10_loser = float((K / m.n_candidates).sum())
    winner_hits = int(m.stage1_top10_contains_winner.sum())
    loser_hits = int(m.stage1_top10_contains_loser.sum())
    winner_enrichment = float(winner_hits / exp_top10_winner)
    loser_enrichment = float(loser_hits / exp_top10_loser)

    full_dir = stats(m.direction_top1_ret21)
    full_uni = stats(m.universe_ew_ret21)
    pre_dir = stats(pre.direction_top1_ret21)
    pre_uni = stats(pre.universe_ew_ret21)
    post_dir = stats(post.direction_top1_ret21)
    post_uni = stats(post.universe_ew_ret21)

    gate = {
        "stage1_top10_winner_enrichment_ge_2x": bool(winner_enrichment >= 2.0),
        "direction_full_cagr_gt_universe_ew": bool(full_dir["cagr_proxy"] > full_uni["cagr_proxy"]),
        "direction_2017_2022_cagr_gt_universe_ew": bool(pre_dir["cagr_proxy"] > pre_uni["cagr_proxy"]),
        "direction_2023_2026_cagr_gt_universe_ew": bool(post_dir["cagr_proxy"] > post_uni["cagr_proxy"]),
    }
    passed = bool(all(gate.values()))

    summary = {
        "line": "Evidence V4",
        "test": "magnitude_direction_v1",
        "status": "DEVELOPMENT_ADVANCE" if passed else "DEVELOPMENT_REJECTED",
        "architecture": "frozen LTR Top10 magnitude retrieval -> causal binary 21d sign classifier -> max P(positive) Top1",
        "stage1_config": LTR_CFG,
        "direction_config": DIR_CFG,
        "evaluation": {
            "n_periods": int(len(m)),
            "first_signal": str(m.signal_date.min().date()),
            "last_signal": str(m.signal_date.max().date()),
            "mean_candidates": float(m.n_candidates.mean()),
            "min_candidates": int(m.n_candidates.min()),
            "max_candidates": int(m.n_candidates.max()),
            "n_2017_2022": int(len(pre)),
            "n_2023_2026": int(len(post)),
        },
        "stage1_tail_retrieval": {
            "top10_winner_hits": winner_hits,
            "top10_loser_hits": loser_hits,
            "random_expected_hits": exp_top10_winner,
            "winner_enrichment": winner_enrichment,
            "loser_enrichment": loser_enrichment,
        },
        "full": {
            "direction_top1": full_dir,
            "stage1_top1": stats(m.stage1_top1_ret21),
            "stage1_top10ew": stats(m.stage1_top10ew_ret21),
            "universe_ew": full_uni,
            "oracle_top10_best": stats(m.oracle_top10_best_ret21),
            "direction_selected_positive_rate": float(m.direction_top1_positive.mean()),
            "direction_exact_global_winner_count": int(m.direction_top1_is_global_winner.sum()),
            "direction_mean_selected_probability": float(m.direction_p_pos21.mean()),
            "direction_cagr_excess_vs_universe_pp": float((full_dir["cagr_proxy"] - full_uni["cagr_proxy"]) * 100.0),
        },
        "2017_2022": {
            "direction_top1": pre_dir,
            "universe_ew": pre_uni,
            "direction_cagr_excess_vs_universe_pp": float((pre_dir["cagr_proxy"] - pre_uni["cagr_proxy"]) * 100.0),
        },
        "2023_2026": {
            "direction_top1": post_dir,
            "universe_ew": post_uni,
            "direction_cagr_excess_vs_universe_pp": float((post_dir["cagr_proxy"] - post_uni["cagr_proxy"]) * 100.0),
        },
        "primary_gate": gate,
        "decision": (
            "PASS: freeze exact two-stage magnitude-direction architecture; next step new disjoint Holdout-B one-shot transfer/promotion test"
            if passed else
            "REJECT: do not vary K, sign threshold, direction target, class weight, classifier hyperparameters, feature subset, blending, cash rule or horizon on Dev60"
        ),
        "stage1_fit_audit_all_maturity_ok": bool(pd.DataFrame(s1_audit).maturity_ok.all()),
        "direction_fit_audit_all_causal_ok": bool(pd.DataFrame(s2_audit).causal_ok.all()),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # Compact Stage1 output without copying 42 features into durable CSV.
    s1[["signal_date", "ticker", "LTR_SCORE", "LTR_RANK", "LTR_POSITION", "fwd_ret_21"]].to_csv(out / "STAGE1_OOS.csv", index=False)
    s2.to_csv(out / "STAGE2_TOP10_OOS.csv", index=False)
    m.to_csv(out / "MONTHLY.csv", index=False)
    pd.DataFrame(s1_audit).to_csv(out / "STAGE1_FIT_AUDIT.csv", index=False)
    pd.DataFrame(s2_audit).to_csv(out / "DIRECTION_FIT_AUDIT.csv", index=False)
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    files = [
        "STAGE1_OOS.csv", "STAGE2_TOP10_OOS.csv", "MONTHLY.csv",
        "STAGE1_FIT_AUDIT.csv", "DIRECTION_FIT_AUDIT.csv", "SUMMARY.json",
    ]
    (out / "RESULT_MANIFEST.json").write_text(json.dumps({
        "test": "magnitude_direction_v1",
        "files_sha256": {name: sha256_file(out / name) for name in files},
    }, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
