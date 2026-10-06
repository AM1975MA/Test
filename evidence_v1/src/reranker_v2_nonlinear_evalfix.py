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
from xgboost import XGBRanker


def monthly_cagr_proxy(x: pd.Series) -> float:
    r = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    if len(r) == 0 or np.any(r <= -1):
        return float("nan")
    return float(np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0)


def summarize(m: pd.DataFrame, prefix: str) -> dict:
    if m.empty:
        return {"n": 0}
    margin_corr = spearmanr(
        m[f"{prefix}_margin"],
        m[f"{prefix}_top1_minus_top2_ret21"],
        nan_policy="omit",
    ).statistic
    return {
        "n": int(len(m)),
        "top1_21d_cagr_proxy": monthly_cagr_proxy(m[f"{prefix}_top1_ret21"]),
        "top1_exact_winner_rate": float(m[f"{prefix}_top1_is_winner"].mean()),
        "top2_contains_winner_rate": float(m[f"{prefix}_top2_contains_winner"].mean()),
        "top3_contains_winner_rate": float(m[f"{prefix}_top3_contains_winner"].mean()),
        "margin_vs_top1_minus_top2_ret21_spearman": float(margin_corr),
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

    required = list(FEATURES_42) + [
        "ticker", "signal_date", "exit_date_63", "target_relevance",
        "target_multi_rank", "fwd_ret_21",
    ]
    missing = [c for c in required if c not in panel.columns]
    if missing:
        raise RuntimeError(f"missing required panel columns: {missing}")

    # Frozen retriever LTR v1 configuration.  We regenerate historical OOS
    # predictions from 2011 onward so the reranker is trained only on shortlists
    # that a causal retriever could actually have emitted at each historical date.
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
        model.fit(
            xtr,
            tr.target_relevance.astype(int).to_numpy(),
            qid=qid,
            verbose=False,
        )
        pr["LTR_SCORE"] = model.predict(xp)
        # Rank=1 means best.  Convert to 0..1 position where larger is better
        # and scale is comparable across different universe sizes.
        rank = pr.groupby("signal_date").LTR_SCORE.rank(
            ascending=False, method="average"
        )
        n = pr.groupby("signal_date").ticker.transform("count").astype(float)
        pr["LTR_POSITION"] = np.where(n > 1, 1.0 - (rank - 1.0) / (n - 1.0), 1.0)
        pred_parts.append(pr)

        ok = bool((tr.signal_date < cutoff).all() and (tr.exit_date_63 < cutoff).all())
        ltr_audit.append({
            "year": year,
            "cutoff": str(cutoff.date()),
            "n_train": int(len(tr)),
            "n_predict": int(len(pr)),
            "max_train_exit63": str(tr.exit_date_63.max().date()),
            "maturity_ok": ok,
        })
        if not ok:
            raise RuntimeError(f"LTR maturity gate failed for {year}")

    if not pred_parts:
        raise RuntimeError("no OOS retriever predictions generated")
    oos = pd.concat(pred_parts, ignore_index=True)

    # Materialize OOS top10 shortlists.  This is the ONLY row universe visible
    # to the reranker.  No full-universe in-sample retriever rows are admitted.
    shortlist_parts = []
    for dt, g in oos.groupby("signal_date", sort=True):
        s = g.sort_values("LTR_SCORE", ascending=False).head(10).copy()
        s["SHORTLIST_RANK"] = np.arange(1, len(s) + 1)
        shortlist_parts.append(s)
    shortlist = pd.concat(shortlist_parts, ignore_index=True)
    full_by_date = {
        dt: g.copy()
        for dt, g in oos.groupby("signal_date", sort=True)
    }

    # Reranker v2 pre-registered configuration: nonlinear, shallow and strongly
    # regularized.  No sweep.  The target and maturity horizon are unchanged
    # from v1 so the main experiment isolates model/representation capacity.
    rr_features = list(FEATURES_42) + ["LTR_POSITION"]
    rr_cfg = {
        "objective": "rank:pairwise",
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
        "lambdarank_pair_method": "topk",
        "lambdarank_num_pair_per_sample": 8,
    }

    rows = []
    rr_audit = []
    for year in range(2017, 2027):
        cutoff = pd.Timestamp(f"{year}-01-01")
        next_cutoff = pd.Timestamp(f"{year + 1}-01-01")

        tr = shortlist[
            (shortlist.signal_date < cutoff)
            & (shortlist.exit_date_63 < cutoff)
            & shortlist.target_relevance.notna()
        ].copy()
        pr = shortlist[
            (shortlist.signal_date >= cutoff)
            & (shortlist.signal_date < next_cutoff)
        ].copy()

        if pr.empty:
            continue
        if tr.signal_date.nunique() < 24:
            raise RuntimeError(f"insufficient mature OOS shortlist history for {year}")

        tr = tr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        pr = pr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)

        imp = SimpleImputer(strategy="median")
        xtr = imp.fit_transform(tr[rr_features])
        xp = imp.transform(pr[rr_features])
        qid = pd.factorize(tr.signal_date, sort=True)[0]

        rr = XGBRanker(**rr_cfg)
        rr.fit(
            xtr,
            tr.target_relevance.astype(int).to_numpy(),
            qid=qid,
            verbose=False,
        )
        pr["RR2_SCORE"] = rr.predict(xp)

        maturity_ok = bool(
            (tr.signal_date < cutoff).all()
            and (tr.exit_date_63 < cutoff).all()
        )
        rr_audit.append({
            "year": year,
            "cutoff": str(cutoff.date()),
            "n_train_rows": int(len(tr)),
            "train_signal_dates": int(tr.signal_date.nunique()),
            "n_predict_rows": int(len(pr)),
            "max_train_exit63": str(tr.exit_date_63.max().date()),
            "maturity_ok": maturity_ok,
        })
        if not maturity_ok:
            raise RuntimeError(f"reranker maturity gate failed for {year}")

        for dt, g in pr.groupby("signal_date", sort=True):
            ltr = g.sort_values("LTR_SCORE", ascending=False).reset_index(drop=True)
            r2 = g.sort_values("RR2_SCORE", ascending=False).reset_index(drop=True)
            # Evaluation uses the GLOBAL 21d winner from the full Original149
            # OOS candidate set, not the best asset inside the retriever shortlist.
            # This matches the canonical retriever/pairwise diagnostics.
            actual = full_by_date[dt].dropna(subset=["fwd_ret_21"]).sort_values(
                "fwd_ret_21", ascending=False
            ).reset_index(drop=True)
            if len(actual) < 2 or len(ltr) < 3 or len(r2) < 3:
                continue

            winner = str(actual.iloc[0].ticker)
            for name, ranked, score_col in (
                ("ltr", ltr, "LTR_SCORE"),
                ("rr2", r2, "RR2_SCORE"),
            ):
                top1 = ranked.iloc[0]
                top2 = ranked.iloc[1]
                rowspec = {
                    f"{name}_top1": str(top1.ticker),
                    f"{name}_top2": str(top2.ticker),
                    f"{name}_top1_ret21": float(top1.fwd_ret_21),
                    f"{name}_top2_ret21": float(top2.fwd_ret_21),
                    f"{name}_top1_is_winner": bool(str(top1.ticker) == winner),
                    f"{name}_top2_contains_winner": bool(
                        winner in set(ranked.head(2).ticker.astype(str))
                    ),
                    f"{name}_top3_contains_winner": bool(
                        winner in set(ranked.head(3).ticker.astype(str))
                    ),
                    f"{name}_margin": float(
                        ranked.iloc[0][score_col] - ranked.iloc[1][score_col]
                    ),
                    f"{name}_top1_minus_top2_ret21": float(
                        top1.fwd_ret_21 - top2.fwd_ret_21
                    ),
                }
                if name == "ltr":
                    row = {"signal_date": dt, "winner": winner, **rowspec}
                else:
                    row.update(rowspec)
            rows.append(row)

    monthly = pd.DataFrame(rows)
    monthly["signal_date"] = pd.to_datetime(monthly.signal_date)
    ltr_audit_df = pd.DataFrame(ltr_audit)
    rr_audit_df = pd.DataFrame(rr_audit)

    if not bool(ltr_audit_df.maturity_ok.all()):
        raise RuntimeError("LTR maturity audit failed")
    if not bool(rr_audit_df.maturity_ok.all()):
        raise RuntimeError("reranker v2 maturity audit failed")

    full_ltr = summarize(monthly, "ltr")
    full_rr2 = summarize(monthly, "rr2")
    pre_ltr = summarize(monthly[monthly.signal_date < pd.Timestamp("2023-01-01")], "ltr")
    pre_rr2 = summarize(monthly[monthly.signal_date < pd.Timestamp("2023-01-01")], "rr2")
    post_ltr = summarize(monthly[monthly.signal_date >= pd.Timestamp("2023-01-01")], "ltr")
    post_rr2 = summarize(monthly[monthly.signal_date >= pd.Timestamp("2023-01-01")], "rr2")

    # Pre-registered advancement rule is ranking-first, not CAGR-first.
    # Require improvement in top2 winner containment and no loss in exact top1
    # over the same 114-period evaluation.  CAGR remains diagnostic only.
    advance = bool(
        full_rr2.get("n", 0) == full_ltr.get("n", -1)
        and full_rr2["top2_contains_winner_rate"] > full_ltr["top2_contains_winner_rate"]
        and full_rr2["top1_exact_winner_rate"] >= full_ltr["top1_exact_winner_rate"]
    )

    result = {
        "line": "Evidence V1",
        "test": "reranker_v2_nonlinear_evalfix",
        "status": "DEVELOPMENT_EVIDENCE_ADVANCE" if advance else "DEVELOPMENT_EVIDENCE_REJECTED",
        "universe": "Original149 frozen",
        "retriever": "LTR v1 top10, OOS annual expanding from 2011",
        "reranker_training_rows": "historical retriever OOS top10 only",
        "label": "target_relevance from frozen multi-horizon target; 63d maturity gate",
        "features": "frozen Hybrid24 FEATURES_42 + normalized LTR position",
        "model": "XGBRanker rank:pairwise, single pre-registered configuration, annual expanding",
        "evaluator": "global full-universe 21d winner; reranker choices restricted to OOS LTR Top10",
        "config": rr_cfg,
        "primary_advancement_rule": (
            "top2 winner containment must beat LTR v1 and exact top1 winner rate "
            "must not fall below LTR v1 on the full evaluation; CAGR is diagnostic only"
        ),
        "full": {"ltr": full_ltr, "reranker_v2": full_rr2},
        "2017_2022": {"ltr": pre_ltr, "reranker_v2": pre_rr2},
        "2023_2026": {"ltr": post_ltr, "reranker_v2": post_rr2},
        "ltr_maturity_all_ok": bool(ltr_audit_df.maturity_ok.all()),
        "reranker_maturity_all_ok": bool(rr_audit_df.maturity_ok.all()),
        "decision": (
            "ADVANCE to confidence calibration diagnostics"
            if advance
            else "REJECT as final reranker candidate; retain only diagnostic evidence"
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(out / "MONTHLY.csv", index=False)
    ltr_audit_df.to_csv(out / "LTR_FIT_AUDIT.csv", index=False)
    rr_audit_df.to_csv(out / "RERANKER_FIT_AUDIT.csv", index=False)
    (out / "CONFIG.json").write_text(json.dumps(rr_cfg, indent=2) + "\n")
    (out / "SUMMARY.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
