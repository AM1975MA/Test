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
from xgboost import XGBClassifier

EVAL_START = pd.Timestamp("2017-01-01")
EVAL_END = pd.Timestamp("2026-07-01")

# Single frozen configuration. Capacity/regularization deliberately mirror v2/v3
# where applicable; the scientific change is the binary best-in-shortlist head.
RR4_CFG = {
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
    "scale_pos_weight": 9.0,
    "eval_metric": "logloss",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def monthly_cagr_proxy(x: pd.Series) -> float:
    r = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    if len(r) == 0 or np.any(r <= -1):
        return float("nan")
    return float(np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0)


def summarize(m: pd.DataFrame, prefix: str) -> dict:
    if m.empty:
        return {"n": 0}
    corr = spearmanr(
        m[f"{prefix}_margin"],
        m[f"{prefix}_top1_minus_top2_ret21"],
        nan_policy="omit",
    ).statistic
    retrievable = m[m.global_winner_in_shortlist]
    return {
        "n": int(len(m)),
        "top1_21d_cagr_proxy": monthly_cagr_proxy(m[f"{prefix}_top1_ret21"]),
        "top1_exact_global_winner_rate": float(m[f"{prefix}_top1_is_global_winner"].mean()),
        "top2_contains_global_winner_rate": float(m[f"{prefix}_top2_contains_global_winner"].mean()),
        "top3_contains_global_winner_rate": float(m[f"{prefix}_top3_contains_global_winner"].mean()),
        "top1_exact_shortlist_best_rate": float(m[f"{prefix}_top1_is_shortlist_best"].mean()),
        "top2_contains_shortlist_best_rate": float(m[f"{prefix}_top2_contains_shortlist_best"].mean()),
        "mean_shortlist_best_rank": float(m[f"{prefix}_shortlist_best_rank"].mean()),
        "global_winner_retrievable_n": int(len(retrievable)),
        "conditional_top1_global_winner_rate_when_retrievable": (
            float(retrievable[f"{prefix}_top1_is_global_winner"].mean())
            if len(retrievable) else float("nan")
        ),
        "conditional_top2_global_winner_rate_when_retrievable": (
            float(retrievable[f"{prefix}_top2_contains_global_winner"].mean())
            if len(retrievable) else float("nan")
        ),
        "margin_vs_top1_minus_top2_ret21_spearman": float(corr),
    }


def add_binary_target(shortlist: pd.DataFrame) -> pd.DataFrame:
    x = shortlist.copy()
    x["RR4_BEST21"] = pd.Series(pd.NA, index=x.index, dtype="Int64")
    for dt, idx in x.groupby("signal_date", sort=True).groups.items():
        g = x.loc[idx].copy()
        if len(g) != 10:
            raise RuntimeError(f"{dt}: classifier target requires exactly 10 shortlist rows")
        if g.fwd_ret_21.isna().any():
            continue
        # Exactly one positive. Ties are deterministically broken by ticker.
        ranked = g.sort_values(
            ["fwd_ret_21", "ticker"], ascending=[False, True]
        )
        winner_idx = ranked.index[0]
        x.loc[idx, "RR4_BEST21"] = 0
        x.loc[winner_idx, "RR4_BEST21"] = 1
    return x


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--frozen-source", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    frozen_source = Path(args.frozen_source).resolve()
    sys.path.insert(0, str(frozen_source / "src"))
    from etf_trader.ma3.producer import FEATURES_42

    panel = pd.read_pickle(args.panel).copy()
    panel["signal_date"] = pd.to_datetime(panel.signal_date)
    panel["exit_date_21"] = pd.to_datetime(panel.exit_date_21)

    required = list(FEATURES_42) + [
        "ticker", "signal_date", "exit_date_21", "fwd_ret_21",
    ]
    missing = [c for c in required if c not in panel.columns]
    if missing:
        raise RuntimeError(f"missing required panel columns: {missing}")

    cp = Path(args.checkpoint)
    top10 = pd.read_csv(cp / "TOP10.csv")
    top10["signal_date"] = pd.to_datetime(top10.signal_date)
    full_oos = pd.read_csv(cp / "OOS_PREDICTIONS.csv")
    full_oos["signal_date"] = pd.to_datetime(full_oos.signal_date)

    if len(top10) != 1860 or top10.signal_date.nunique() != 186:
        raise RuntimeError(
            f"frozen Top10 checkpoint mismatch: rows={len(top10)} dates={top10.signal_date.nunique()}"
        )
    sizes = top10.groupby("signal_date").size()
    if sizes.nunique() != 1 or int(sizes.iloc[0]) != 10:
        raise RuntimeError("frozen Top10 checkpoint is not exactly 10 rows per signal date")

    feature_cols = list(FEATURES_42)
    join_cols = ["signal_date", "ticker"]
    panel_cols = join_cols + feature_cols + ["exit_date_21", "fwd_ret_21"]
    shortlist = top10.merge(
        panel[panel_cols], on=join_cols, how="left", validate="one_to_one"
    )
    if shortlist[feature_cols].isna().all(axis=1).any():
        raise RuntimeError("checkpoint Top10 contains rows missing entirely from frozen feature panel")
    shortlist = add_binary_target(shortlist)

    full_eval = full_oos.merge(
        panel[join_cols + ["fwd_ret_21"]],
        on=join_cols,
        how="left",
        validate="one_to_one",
    )
    full_by_date = {
        dt: g.copy() for dt, g in full_eval.groupby("signal_date", sort=True)
    }

    rr_features = feature_cols + ["LTR_POSITION"]
    rows = []
    audit = []

    for year in range(2017, 2027):
        cutoff = pd.Timestamp(f"{year}-01-01")
        next_cutoff = pd.Timestamp(f"{year + 1}-01-01")
        tr = shortlist[
            (shortlist.signal_date < cutoff)
            & (shortlist.exit_date_21 < cutoff)
            & shortlist.RR4_BEST21.notna()
        ].copy()
        pr = shortlist[
            (shortlist.signal_date >= cutoff)
            & (shortlist.signal_date < next_cutoff)
        ].copy()

        if pr.empty:
            continue
        if tr.signal_date.nunique() < 24:
            raise RuntimeError(f"insufficient mature OOS shortlist history for {year}")
        if pr.RR4_BEST21.isna().any():
            raise RuntimeError(f"evaluation target missing in {year}; frozen data horizon insufficient")

        tr = tr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        pr = pr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)

        # Structural audit: each mature historical shortlist contributes exactly
        # one positive and nine negatives, matching the fixed class weight 9.0.
        by_date_pos = tr.groupby("signal_date").RR4_BEST21.sum()
        by_date_n = tr.groupby("signal_date").size()
        if not bool((by_date_pos == 1).all() and (by_date_n == 10).all()):
            raise RuntimeError(f"classifier structural label audit failed for {year}")

        imp = SimpleImputer(strategy="median")
        xtr = imp.fit_transform(tr[rr_features])
        xp = imp.transform(pr[rr_features])

        clf = XGBClassifier(**RR4_CFG)
        clf.fit(xtr, tr.RR4_BEST21.astype(int).to_numpy(), verbose=False)
        pr["RR4_PROB"] = clf.predict_proba(xp)[:, 1]

        maturity_ok = bool(
            (tr.signal_date < cutoff).all()
            and (tr.exit_date_21 < cutoff).all()
        )
        audit.append({
            "year": year,
            "cutoff": str(cutoff.date()),
            "n_train_rows": int(len(tr)),
            "train_signal_dates": int(tr.signal_date.nunique()),
            "n_train_positive": int(tr.RR4_BEST21.sum()),
            "n_train_negative": int(len(tr) - tr.RR4_BEST21.sum()),
            "n_predict_rows": int(len(pr)),
            "max_train_exit21": str(tr.exit_date_21.max().date()),
            "maturity_ok": maturity_ok,
        })
        if not maturity_ok:
            raise RuntimeError(f"reranker v4 maturity gate failed for {year}")

        for dt, g in pr.groupby("signal_date", sort=True):
            if dt < EVAL_START or dt >= EVAL_END:
                continue
            ltr = g.sort_values(
                ["LTR_SCORE", "ticker"], ascending=[False, True]
            ).reset_index(drop=True)
            rr4 = g.sort_values(
                ["RR4_PROB", "ticker"], ascending=[False, True]
            ).reset_index(drop=True)
            actual = full_by_date[dt].dropna(subset=["fwd_ret_21"]).sort_values(
                ["fwd_ret_21", "ticker"], ascending=[False, True]
            ).reset_index(drop=True)
            shortlist_actual = g.sort_values(
                ["fwd_ret_21", "ticker"], ascending=[False, True]
            ).reset_index(drop=True)
            if len(actual) < 2 or len(ltr) != 10 or len(rr4) != 10 or len(shortlist_actual) != 10:
                raise RuntimeError(f"{dt}: incomplete evaluation rows")

            global_winner = str(actual.iloc[0].ticker)
            shortlist_best = str(shortlist_actual.iloc[0].ticker)
            global_in_shortlist = bool(global_winner in set(g.ticker.astype(str)))
            row = {
                "signal_date": dt,
                "global_winner": global_winner,
                "shortlist_best": shortlist_best,
                "global_winner_in_shortlist": global_in_shortlist,
            }
            for name, ranked, score_col in (
                ("ltr", ltr, "LTR_SCORE"),
                ("rr4", rr4, "RR4_PROB"),
            ):
                top1 = ranked.iloc[0]
                top2 = ranked.iloc[1]
                ranks = {str(t): i + 1 for i, t in enumerate(ranked.ticker.astype(str))}
                row.update({
                    f"{name}_top1": str(top1.ticker),
                    f"{name}_top2": str(top2.ticker),
                    f"{name}_top1_ret21": float(top1.fwd_ret_21),
                    f"{name}_top2_ret21": float(top2.fwd_ret_21),
                    f"{name}_top1_is_global_winner": bool(str(top1.ticker) == global_winner),
                    f"{name}_top2_contains_global_winner": bool(
                        global_winner in set(ranked.head(2).ticker.astype(str))
                    ),
                    f"{name}_top3_contains_global_winner": bool(
                        global_winner in set(ranked.head(3).ticker.astype(str))
                    ),
                    f"{name}_top1_is_shortlist_best": bool(str(top1.ticker) == shortlist_best),
                    f"{name}_top2_contains_shortlist_best": bool(
                        shortlist_best in set(ranked.head(2).ticker.astype(str))
                    ),
                    f"{name}_shortlist_best_rank": int(ranks[shortlist_best]),
                    f"{name}_margin": float(
                        ranked.iloc[0][score_col] - ranked.iloc[1][score_col]
                    ),
                    f"{name}_top1_minus_top2_ret21": float(
                        top1.fwd_ret_21 - top2.fwd_ret_21
                    ),
                })
            rows.append(row)

    monthly = pd.DataFrame(rows)
    monthly["signal_date"] = pd.to_datetime(monthly.signal_date)
    audit_df = pd.DataFrame(audit)

    if len(monthly) != 114 or monthly.signal_date.nunique() != 114:
        raise RuntimeError(
            f"expected 114 evaluation periods, got rows={len(monthly)} dates={monthly.signal_date.nunique()}"
        )
    if not bool(audit_df.maturity_ok.all()):
        raise RuntimeError("reranker v4 maturity audit failed")

    full_ltr = summarize(monthly, "ltr")
    full_rr4 = summarize(monthly, "rr4")
    pre = monthly[monthly.signal_date < pd.Timestamp("2023-01-01")]
    post = monthly[monthly.signal_date >= pd.Timestamp("2023-01-01")]
    pre_ltr = summarize(pre, "ltr")
    pre_rr4 = summarize(pre, "rr4")
    post_ltr = summarize(post, "ltr")
    post_rr4 = summarize(post, "rr4")

    # Certified frozen comparator gate before judging v4.
    expected_ltr = {
        "n": 114,
        "top1_exact_global_winner_rate": 10 / 114,
        "top2_contains_global_winner_rate": 15 / 114,
        "top3_contains_global_winner_rate": 21 / 114,
        "global_winner_retrievable_n": 47,
    }
    for key, value in expected_ltr.items():
        if not np.isclose(full_ltr[key], value, rtol=0, atol=1e-12):
            raise RuntimeError(
                f"frozen LTR comparator mismatch for {key}: {full_ltr[key]} != {value}"
            )

    advance = bool(
        full_rr4["top2_contains_global_winner_rate"] > full_ltr["top2_contains_global_winner_rate"]
        and full_rr4["top1_exact_global_winner_rate"] >= full_ltr["top1_exact_global_winner_rate"]
    )

    result = {
        "line": "Evidence V1",
        "test": "reranker_v4_best_classifier",
        "status": "DEVELOPMENT_EVIDENCE_ADVANCE" if advance else "DEVELOPMENT_EVIDENCE_REJECTED",
        "universe": "Original149 frozen; burned development set only",
        "reference_representation": "Original149 stable reference universe",
        "retriever": "frozen Retriever LTR v1 OOS Top10 checkpoint; no retraining",
        "reranker_training_rows": "historical frozen retriever OOS Top10 only",
        "label": "binary best-in-shortlist future 21d: exactly 1 positive + 9 negatives per signal date",
        "maturity_gate": "exit_date_21 < annual cutoff",
        "features": "frozen Hybrid24 FEATURES_42 computed on Original149 reference + frozen LTR_POSITION",
        "model": "XGBClassifier binary:logistic, shallow/regularized, structural class weight 9:1, single preregistered config",
        "evaluator": "primary gate uses global full-universe 21d winner; classifier choices restricted to frozen OOS LTR Top10",
        "config": RR4_CFG,
        "primary_advancement_rule": (
            "Top2 global-winner containment must beat frozen LTR v1 and exact Top1 global-winner rate "
            "must not fall below frozen LTR v1; CAGR and all shortlist-best diagnostics are secondary only"
        ),
        "full": {"ltr": full_ltr, "reranker_v4": full_rr4},
        "2017_2022": {"ltr": pre_ltr, "reranker_v4": pre_rr4},
        "2023_2026": {"ltr": post_ltr, "reranker_v4": post_rr4},
        "maturity_all_ok": bool(audit_df.maturity_ok.all()),
        "decision": (
            "ADVANCE: freeze a new disjoint Holdout-B before any promotion test; no further tuning on Original149"
            if advance
            else "REJECT: close deterministic reranker line on Original149 and move to preregistered top-k allocation/sizing"
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(out / "MONTHLY.csv", index=False)
    audit_df.to_csv(out / "FIT_AUDIT.csv", index=False)
    (out / "CONFIG.json").write_text(json.dumps(RR4_CFG, indent=2) + "\n")
    (out / "SUMMARY.json").write_text(json.dumps(result, indent=2) + "\n")
    manifest = {
        "test": "reranker_v4_best_classifier",
        "files_sha256": {
            name: sha256_file(out / name)
            for name in ["MONTHLY.csv", "FIT_AUDIT.csv", "CONFIG.json", "SUMMARY.json"]
        },
    }
    (out / "RESULT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
