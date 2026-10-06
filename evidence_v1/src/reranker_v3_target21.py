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
from xgboost import XGBRanker

EVAL_START = pd.Timestamp("2017-01-01")
EVAL_END = pd.Timestamp("2026-07-01")

RR3_CFG = {
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
    return {
        "n": int(len(m)),
        "top1_21d_cagr_proxy": monthly_cagr_proxy(m[f"{prefix}_top1_ret21"]),
        "top1_exact_winner_rate": float(m[f"{prefix}_top1_is_winner"].mean()),
        "top2_contains_winner_rate": float(m[f"{prefix}_top2_contains_winner"].mean()),
        "top3_contains_winner_rate": float(m[f"{prefix}_top3_contains_winner"].mean()),
        "margin_vs_top1_minus_top2_ret21_spearman": float(corr),
    }


def make_target21(shortlist: pd.DataFrame) -> pd.DataFrame:
    x = shortlist.copy()
    x["RR3_TARGET21"] = pd.Series(pd.NA, index=x.index, dtype="Int64")
    for dt, idx in x.groupby("signal_date", sort=True).groups.items():
        g = x.loc[idx]
        valid = g.fwd_ret_21.notna()
        if not bool(valid.all()):
            continue
        # Exactly 10 OOS shortlist members: 9=best future 21d return, 0=worst.
        order = g.fwd_ret_21.rank(ascending=False, method="first").astype(int)
        if len(g) != 10 or set(order.tolist()) != set(range(1, 11)):
            raise RuntimeError(f"{dt}: target21 requires an exact 10-name shortlist")
        x.loc[idx, "RR3_TARGET21"] = (10 - order).astype(int).to_numpy()
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
    if top10.groupby("signal_date").size().nunique() != 1 or int(top10.groupby("signal_date").size().iloc[0]) != 10:
        raise RuntimeError("frozen Top10 checkpoint is not exactly 10 rows per signal date")

    feature_cols = list(FEATURES_42)
    join_cols = ["signal_date", "ticker"]
    panel_cols = join_cols + feature_cols + ["exit_date_21", "fwd_ret_21"]
    shortlist = top10.merge(
        panel[panel_cols], on=join_cols, how="left", validate="one_to_one"
    )
    if shortlist[feature_cols].isna().all(axis=1).any():
        raise RuntimeError("checkpoint Top10 contains rows missing entirely from frozen feature panel")
    shortlist = make_target21(shortlist)

    # Full-universe future 21d returns are used only by the evaluator to identify
    # the global winner.  Frozen LTR OOS scores define the comparator ranking.
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
            & shortlist.RR3_TARGET21.notna()
        ].copy()
        pr = shortlist[
            (shortlist.signal_date >= cutoff)
            & (shortlist.signal_date < next_cutoff)
        ].copy()

        if pr.empty:
            continue
        if tr.signal_date.nunique() < 24:
            raise RuntimeError(f"insufficient mature OOS shortlist history for {year}")
        if pr.RR3_TARGET21.isna().any():
            raise RuntimeError(f"evaluation target21 missing in {year}; frozen data horizon insufficient")

        tr = tr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        pr = pr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)

        imp = SimpleImputer(strategy="median")
        xtr = imp.fit_transform(tr[rr_features])
        xp = imp.transform(pr[rr_features])
        qid = pd.factorize(tr.signal_date, sort=True)[0]

        rr = XGBRanker(**RR3_CFG)
        rr.fit(
            xtr,
            tr.RR3_TARGET21.astype(int).to_numpy(),
            qid=qid,
            verbose=False,
        )
        pr["RR3_SCORE"] = rr.predict(xp)

        maturity_ok = bool(
            (tr.signal_date < cutoff).all()
            and (tr.exit_date_21 < cutoff).all()
        )
        audit.append({
            "year": year,
            "cutoff": str(cutoff.date()),
            "n_train_rows": int(len(tr)),
            "train_signal_dates": int(tr.signal_date.nunique()),
            "n_predict_rows": int(len(pr)),
            "max_train_exit21": str(tr.exit_date_21.max().date()),
            "maturity_ok": maturity_ok,
        })
        if not maturity_ok:
            raise RuntimeError(f"reranker v3 maturity gate failed for {year}")

        for dt, g in pr.groupby("signal_date", sort=True):
            if dt < EVAL_START or dt >= EVAL_END:
                continue
            ltr = g.sort_values(
                ["LTR_SCORE", "ticker"], ascending=[False, True]
            ).reset_index(drop=True)
            rr3 = g.sort_values(
                ["RR3_SCORE", "ticker"], ascending=[False, True]
            ).reset_index(drop=True)
            actual = full_by_date[dt].dropna(subset=["fwd_ret_21"]).sort_values(
                ["fwd_ret_21", "ticker"], ascending=[False, True]
            ).reset_index(drop=True)
            if len(actual) < 2 or len(ltr) != 10 or len(rr3) != 10:
                raise RuntimeError(f"{dt}: incomplete evaluation rows")

            winner = str(actual.iloc[0].ticker)
            row = {"signal_date": dt, "winner": winner}
            for name, ranked, score_col in (
                ("ltr", ltr, "LTR_SCORE"),
                ("rr3", rr3, "RR3_SCORE"),
            ):
                top1 = ranked.iloc[0]
                top2 = ranked.iloc[1]
                row.update({
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
        raise RuntimeError("reranker v3 maturity audit failed")

    full_ltr = summarize(monthly, "ltr")
    full_rr3 = summarize(monthly, "rr3")
    pre = monthly[monthly.signal_date < pd.Timestamp("2023-01-01")]
    post = monthly[monthly.signal_date >= pd.Timestamp("2023-01-01")]
    pre_ltr = summarize(pre, "ltr")
    pre_rr3 = summarize(pre, "rr3")
    post_ltr = summarize(post, "ltr")
    post_rr3 = summarize(post, "rr3")

    # Fail closed if the frozen LTR comparator does not reproduce its certified
    # global-winner baseline before judging v3.
    expected_ltr = {
        "n": 114,
        "top1_exact_winner_rate": 10 / 114,
        "top2_contains_winner_rate": 15 / 114,
        "top3_contains_winner_rate": 21 / 114,
    }
    for key, value in expected_ltr.items():
        if not np.isclose(full_ltr[key], value, rtol=0, atol=1e-12):
            raise RuntimeError(
                f"frozen LTR comparator mismatch for {key}: {full_ltr[key]} != {value}"
            )

    advance = bool(
        full_rr3["top2_contains_winner_rate"] > full_ltr["top2_contains_winner_rate"]
        and full_rr3["top1_exact_winner_rate"] >= full_ltr["top1_exact_winner_rate"]
    )

    result = {
        "line": "Evidence V1",
        "test": "reranker_v3_target21",
        "status": "DEVELOPMENT_EVIDENCE_ADVANCE" if advance else "DEVELOPMENT_EVIDENCE_REJECTED",
        "universe": "Original149 frozen",
        "reference_representation": "Original149 stable reference universe",
        "retriever": "frozen Retriever LTR v1 OOS Top10 checkpoint; no retraining",
        "reranker_training_rows": "historical frozen retriever OOS Top10 only",
        "label": "within-shortlist future 21d ordinal relevance: 9=best to 0=worst",
        "maturity_gate": "exit_date_21 < annual cutoff",
        "features": "frozen Hybrid24 FEATURES_42 computed on Original149 reference + frozen LTR_POSITION",
        "model": "same XGBRanker rank:pairwise capacity/config as rejected v2; target changed, no sweep",
        "evaluator": "global full-universe 21d winner; reranker choices restricted to frozen OOS LTR Top10",
        "config": RR3_CFG,
        "primary_advancement_rule": (
            "Top2 global-winner containment must beat frozen LTR v1 and exact Top1 global-winner rate "
            "must not fall below frozen LTR v1; CAGR and margin calibration are diagnostic only"
        ),
        "full": {"ltr": full_ltr, "reranker_v3": full_rr3},
        "2017_2022": {"ltr": pre_ltr, "reranker_v3": pre_rr3},
        "2023_2026": {"ltr": post_ltr, "reranker_v3": post_rr3},
        "maturity_all_ok": bool(audit_df.maturity_ok.all()),
        "decision": (
            "ADVANCE: freeze new disjoint Holdout-B before any promotion test"
            if advance
            else "REJECT: target-aligned v3 does not satisfy the preregistered ranking gate"
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(out / "MONTHLY.csv", index=False)
    audit_df.to_csv(out / "FIT_AUDIT.csv", index=False)
    (out / "CONFIG.json").write_text(json.dumps(RR3_CFG, indent=2) + "\n")
    (out / "SUMMARY.json").write_text(json.dumps(result, indent=2) + "\n")
    manifest = {
        "test": "reranker_v3_target21",
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
