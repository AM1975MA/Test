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
from sklearn.metrics import adjusted_rand_score
from xgboost import XGBRanker

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
EVAL_START = pd.Timestamp("2017-01-01")
EVAL_END = pd.Timestamp("2026-07-01")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def monthly_cagr_proxy(values: pd.Series) -> float:
    r = pd.to_numeric(values, errors="coerce").dropna().to_numpy(float)
    if len(r) == 0 or np.any(r <= -1.0):
        return float("nan")
    return float(np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0)


def recompute_candidate_targets(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x["signal_date"] = pd.to_datetime(x.signal_date)
    x["exit_date_63"] = pd.to_datetime(x.exit_date_63)
    for h in (21, 42, 63):
        c = f"fwd_ret_{h}"
        x[f"target_rank_{h}"] = x.groupby("signal_date")[c].rank(
            pct=True, method="average"
        )
    x["target_multi_rank"] = (
        0.45 * x.target_rank_21
        + 0.35 * x.target_rank_42
        + 0.20 * x.target_rank_63
    )
    x["target_relevance"] = np.minimum(
        9, np.floor(x.target_multi_rank * 10)
    ).astype("Int64")
    return x


def assert_same_keys_and_targets(
    reference: pd.DataFrame,
    native: pd.DataFrame,
    name: str,
) -> None:
    cols = ["signal_date", "ticker"]
    a = reference[cols].copy().sort_values(cols).reset_index(drop=True)
    b = native[cols].copy().sort_values(cols).reset_index(drop=True)
    if not a.equals(b):
        ai = pd.MultiIndex.from_frame(a)
        bi = pd.MultiIndex.from_frame(b)
        only_a = ai.difference(bi)
        only_b = bi.difference(ai)
        raise RuntimeError(
            f"{name}: reference/native key mismatch; "
            f"reference_only={len(only_a)} native_only={len(only_b)}"
        )
    ta = reference[cols + ["target_relevance"]].sort_values(cols).reset_index(drop=True)
    tb = native[cols + ["target_relevance"]].sort_values(cols).reset_index(drop=True)
    if not np.array_equal(
        ta.target_relevance.fillna(-1).astype(int).to_numpy(),
        tb.target_relevance.fillna(-1).astype(int).to_numpy(),
    ):
        raise RuntimeError(f"{name}: candidate-relative target mismatch")


def fit_ltr(
    panel: pd.DataFrame,
    feature_cols: list[str],
    prefix: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = panel.copy()
    df["signal_date"] = pd.to_datetime(df.signal_date)
    df["exit_date_63"] = pd.to_datetime(df.exit_date_63)
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise RuntimeError(f"{prefix}: missing features {missing}")

    outs = []
    audits = []
    for year in range(2011, 2027):
        cutoff = pd.Timestamp(f"{year}-01-01")
        next_cutoff = pd.Timestamp(f"{year + 1}-01-01")
        tr = df[
            (df.signal_date < cutoff)
            & (df.exit_date_63 < cutoff)
            & df.target_relevance.notna()
        ].copy()
        pr = df[
            (df.signal_date >= cutoff)
            & (df.signal_date < next_cutoff)
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
        model.fit(
            xtr,
            tr.target_relevance.astype(int).to_numpy(),
            qid=qid,
            verbose=False,
        )
        pr[f"{prefix}_SCORE"] = model.predict(xp)
        pr = pr.sort_values(
            ["signal_date", f"{prefix}_SCORE", "ticker"],
            ascending=[True, False, True],
        ).reset_index(drop=True)
        pr[f"{prefix}_RANK"] = pr.groupby("signal_date").cumcount() + 1
        outs.append(pr[["signal_date", "ticker", f"{prefix}_SCORE", f"{prefix}_RANK"]])
        maturity_ok = bool(
            (tr.signal_date < cutoff).all()
            and (tr.exit_date_63 < cutoff).all()
        )
        audits.append({
            "method": prefix,
            "year": year,
            "cutoff": str(cutoff.date()),
            "n_train": int(len(tr)),
            "n_predict": int(len(pr)),
            "max_train_exit63": str(tr.exit_date_63.max().date()),
            "maturity_ok": maturity_ok,
        })
        if not maturity_ok:
            raise RuntimeError(f"{prefix}: maturity gate failed for {year}")
    if not outs:
        raise RuntimeError(f"{prefix}: no OOS predictions")
    pred = pd.concat(outs, ignore_index=True)
    audit = pd.DataFrame(audits)
    if not bool(audit.maturity_ok.all()):
        raise RuntimeError(f"{prefix}: fit audit failed")
    return pred, audit


def rank_from_fixed_checkpoint(checkpoint: pd.DataFrame, tickers: set[str]) -> pd.DataFrame:
    x = checkpoint[checkpoint.ticker.astype(str).isin(tickers)].copy()
    x["signal_date"] = pd.to_datetime(x.signal_date)
    x = x.sort_values(
        ["signal_date", "LTR_SCORE", "ticker"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    x["FIXED_RANK"] = x.groupby("signal_date").cumcount() + 1
    return x[["signal_date", "ticker", "LTR_SCORE", "FIXED_RANK"]].rename(
        columns={"LTR_SCORE": "FIXED_SCORE"}
    )


def set_jaccard(a: set[str], b: set[str]) -> float:
    u = a | b
    return float(len(a & b) / len(u)) if u else float("nan")


def rank_corr(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2:
        return float("nan")
    if np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a.astype(float), b.astype(float))[0, 1])


def date_stability(
    frame: pd.DataFrame,
    size_name: str,
) -> pd.DataFrame:
    rows = []
    for dt, g in frame.groupby("signal_date", sort=True):
        g = g.dropna(
            subset=["FIXED_RANK", "REF_RANK", "NATIVE_RANK", "fwd_ret_21"]
        ).copy()
        if g.empty:
            continue
        n = len(g)
        fixed = g.sort_values(["FIXED_RANK", "ticker"])
        ref = g.sort_values(["REF_RANK", "ticker"])
        native = g.sort_values(["NATIVE_RANK", "ticker"])
        fixed5 = set(fixed.head(5).ticker.astype(str))
        ref5 = set(ref.head(5).ticker.astype(str))
        native5 = set(native.head(5).ticker.astype(str))
        fixed10 = set(fixed.head(10).ticker.astype(str))
        ref10 = set(ref.head(10).ticker.astype(str))
        native10 = set(native.head(10).ticker.astype(str))
        denom = max(1, n - 1)
        winner = str(g.sort_values("fwd_ret_21", ascending=False).iloc[0].ticker)
        row = {
            "subset": size_name,
            "signal_date": str(pd.Timestamp(dt).date()),
            "n_candidates": int(n),
            "winner": winner,
            "fixed_top1": str(fixed.iloc[0].ticker),
            "ref_top1": str(ref.iloc[0].ticker),
            "native_top1": str(native.iloc[0].ticker),
            "ref_top1_agree_fixed": bool(str(ref.iloc[0].ticker) == str(fixed.iloc[0].ticker)),
            "native_top1_agree_fixed": bool(str(native.iloc[0].ticker) == str(fixed.iloc[0].ticker)),
            "ref_top5_jaccard_fixed": set_jaccard(ref5, fixed5),
            "native_top5_jaccard_fixed": set_jaccard(native5, fixed5),
            "ref_top10_jaccard_fixed": set_jaccard(ref10, fixed10),
            "native_top10_jaccard_fixed": set_jaccard(native10, fixed10),
            "ref_rank_corr_fixed": rank_corr(g.FIXED_RANK.to_numpy(), g.REF_RANK.to_numpy()),
            "native_rank_corr_fixed": rank_corr(g.FIXED_RANK.to_numpy(), g.NATIVE_RANK.to_numpy()),
            "ref_rank_mae_norm_fixed": float(np.mean(np.abs(g.FIXED_RANK - g.REF_RANK)) / denom),
            "native_rank_mae_norm_fixed": float(np.mean(np.abs(g.FIXED_RANK - g.NATIVE_RANK)) / denom),
            "ref_native_top1_agreement": bool(str(ref.iloc[0].ticker) == str(native.iloc[0].ticker)),
            "ref_native_top5_jaccard": set_jaccard(ref5, native5),
            "ref_native_rank_corr": rank_corr(g.REF_RANK.to_numpy(), g.NATIVE_RANK.to_numpy()),
            "ref_native_rank_mae_norm": float(np.mean(np.abs(g.REF_RANK - g.NATIVE_RANK)) / denom),
        }
        for method, ranked in (("fixed", fixed), ("ref", ref), ("native", native)):
            top1 = str(ranked.iloc[0].ticker)
            top5 = set(ranked.head(5).ticker.astype(str))
            top10 = set(ranked.head(10).ticker.astype(str))
            row[f"{method}_top1_is_winner"] = bool(top1 == winner)
            row[f"{method}_top5_contains_winner"] = bool(winner in top5)
            row[f"{method}_top10_contains_winner"] = bool(winner in top10)
            row[f"{method}_top1_ret21"] = float(
                g.loc[g.ticker.astype(str).eq(top1), "fwd_ret_21"].iloc[0]
            )
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_period(per_date: pd.DataFrame, mask: pd.Series) -> dict:
    x = per_date.loc[mask].copy()
    out = {"n_periods": int(len(x))}
    for method in ("ref", "native"):
        out[method] = {
            "top1_agreement_to_fixed": float(x[f"{method}_top1_agree_fixed"].mean()),
            "top5_jaccard_to_fixed": float(x[f"{method}_top5_jaccard_fixed"].mean()),
            "top5_turnover_to_fixed": float(1.0 - x[f"{method}_top5_jaccard_fixed"].mean()),
            "top10_jaccard_to_fixed": float(x[f"{method}_top10_jaccard_fixed"].mean()),
            "rank_corr_to_fixed": float(x[f"{method}_rank_corr_fixed"].mean()),
            "rank_mae_norm_to_fixed": float(x[f"{method}_rank_mae_norm_fixed"].mean()),
        }
    out["ref_vs_native"] = {
        "top1_agreement": float(x.ref_native_top1_agreement.mean()),
        "top5_jaccard": float(x.ref_native_top5_jaccard.mean()),
        "rank_corr": float(x.ref_native_rank_corr.mean()),
        "rank_mae_norm": float(x.ref_native_rank_mae_norm.mean()),
    }
    out["diagnostic_performance"] = {}
    for method in ("fixed", "ref", "native"):
        out["diagnostic_performance"][method] = {
            "top1_exact_winner_rate": float(x[f"{method}_top1_is_winner"].mean()),
            "top5_winner_rate": float(x[f"{method}_top5_contains_winner"].mean()),
            "top10_winner_rate": float(x[f"{method}_top10_contains_winner"].mean()),
            "top1_21d_cagr_proxy": monthly_cagr_proxy(x[f"{method}_top1_ret21"]),
        }
    return out


def feature_drift(
    reference: pd.DataFrame,
    native: pd.DataFrame,
    feature_cols: list[str],
    subset: str,
) -> pd.DataFrame:
    cols = ["signal_date", "ticker"]
    m = reference[cols + feature_cols].merge(
        native[cols + feature_cols], on=cols, suffixes=("_ref", "_native"), validate="one_to_one"
    )
    rows = []
    for c in feature_cols:
        a = pd.to_numeric(m[f"{c}_ref"], errors="coerce").to_numpy(float)
        b = pd.to_numeric(m[f"{c}_native"], errors="coerce").to_numpy(float)
        ok = np.isfinite(a) & np.isfinite(b)
        d = np.abs(a[ok] - b[ok])
        rows.append({
            "subset": subset,
            "feature": c,
            "n": int(ok.sum()),
            "mean_abs_delta": float(np.mean(d)) if len(d) else float("nan"),
            "median_abs_delta": float(np.median(d)) if len(d) else float("nan"),
            "p95_abs_delta": float(np.quantile(d, 0.95)) if len(d) else float("nan"),
        })
    return pd.DataFrame(rows)


def cluster_stability(reference: pd.DataFrame, native: pd.DataFrame, subset: str) -> pd.DataFrame:
    cols = ["signal_date", "ticker"]
    m = reference[cols + ["cluster_id"]].merge(
        native[cols + ["cluster_id"]], on=cols, suffixes=("_ref", "_native"), validate="one_to_one"
    )
    rows = []
    for dt, g in m.groupby("signal_date", sort=True):
        rows.append({
            "subset": subset,
            "signal_date": str(pd.Timestamp(dt).date()),
            "n": int(len(g)),
            "adjusted_rand_index": float(adjusted_rand_score(g.cluster_id_ref, g.cluster_id_native)),
            "reference_cluster_count": int(g.cluster_id_ref.nunique()),
            "native_cluster_count": int(g.cluster_id_native.nunique()),
        })
    return pd.DataFrame(rows)


def directional_decision(full_summary: dict[str, dict]) -> dict:
    by_subset = {}
    all_primary = True
    all_three_of_four = True
    for subset, s in full_summary.items():
        r = s["ref"]
        n = s["native"]
        wins = {
            "top1_agreement": bool(r["top1_agreement_to_fixed"] > n["top1_agreement_to_fixed"]),
            "top5_turnover": bool(r["top5_turnover_to_fixed"] < n["top5_turnover_to_fixed"]),
            "rank_corr": bool(r["rank_corr_to_fixed"] > n["rank_corr_to_fixed"]),
            "rank_mae_norm": bool(r["rank_mae_norm_to_fixed"] < n["rank_mae_norm_to_fixed"]),
        }
        count = int(sum(wins.values()))
        by_subset[subset] = {"wins": wins, "win_count": count}
        all_primary = all_primary and wins["top5_turnover"]
        all_three_of_four = all_three_of_four and count >= 3
    supported = bool(all_primary and all_three_of_four)
    return {
        "rule": (
            "reference-universe stabilization is supported only if reference retraining has lower "
            "Top5 turnover to the frozen full149 anchor for U120/U100/U70 and wins at least 3 of "
            "4 prespecified stability metrics in every subset"
        ),
        "by_subset": by_subset,
        "supported": supported,
        "decision": "SUPPORT_REFERENCE_UNIVERSE" if supported else "DO_NOT_SUPPORT_REFERENCE_UNIVERSE",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full-panel", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--frozen-source", required=True)
    ap.add_argument("--u120", required=True)
    ap.add_argument("--u100", required=True)
    ap.add_argument("--u70", required=True)
    ap.add_argument("--native120", required=True)
    ap.add_argument("--native100", required=True)
    ap.add_argument("--native70", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    frozen_source = Path(args.frozen_source).resolve()
    sys.path.insert(0, str(frozen_source / "src"))
    from etf_trader.ma3.producer import FEATURES_42

    features = list(FEATURES_42)
    full = pd.read_pickle(args.full_panel).copy()
    full["signal_date"] = pd.to_datetime(full.signal_date)
    checkpoint = pd.read_csv(Path(args.checkpoint) / "OOS_PREDICTIONS.csv")
    checkpoint["signal_date"] = pd.to_datetime(checkpoint.signal_date)

    universes = {
        "U120": (args.u120, args.native120),
        "U100": (args.u100, args.native100),
        "U70": (args.u70, args.native70),
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    all_per_date = []
    all_feature_drift = []
    all_cluster = []
    all_audit = []
    full_summary: dict[str, dict] = {}
    split_summary: dict[str, dict] = {}
    coverage = {}

    for subset, (universe_path, native_path) in universes.items():
        u = pd.read_csv(universe_path)
        tickers = set(u.ticker.astype(str).str.upper())
        expected_n = int(subset[1:])
        if len(tickers) != expected_n:
            raise RuntimeError(f"{subset}: expected {expected_n} frozen tickers, got {len(tickers)}")
        if "SPY" not in tickers:
            raise RuntimeError(f"{subset}: SPY anchor missing")

        reference = full[full.ticker.astype(str).isin(tickers)].copy()
        native = pd.read_pickle(native_path).copy()
        native["signal_date"] = pd.to_datetime(native.signal_date)
        if set(native.ticker.astype(str).unique()) - tickers:
            raise RuntimeError(f"{subset}: native panel contains non-candidate ticker")
        reference = recompute_candidate_targets(reference)
        native = recompute_candidate_targets(native)
        assert_same_keys_and_targets(reference, native, subset)

        coverage[subset] = {
            "rows": int(len(reference)),
            "signal_dates": int(reference.signal_date.nunique()),
            "tickers_seen": int(reference.ticker.nunique()),
        }

        ref_pred, ref_audit = fit_ltr(reference, features, "REF")
        native_pred, native_audit = fit_ltr(native, features, "NATIVE")
        ref_audit.insert(0, "subset", subset)
        native_audit.insert(0, "subset", subset)
        all_audit.extend([ref_audit, native_audit])

        fixed = rank_from_fixed_checkpoint(checkpoint, tickers)
        eval_base = reference[
            (reference.signal_date >= EVAL_START)
            & (reference.signal_date < EVAL_END)
        ][["signal_date", "ticker", "fwd_ret_21"]].copy()
        merged = eval_base.merge(fixed, on=["signal_date", "ticker"], how="inner", validate="one_to_one")
        merged = merged.merge(ref_pred, on=["signal_date", "ticker"], how="inner", validate="one_to_one")
        merged = merged.merge(native_pred, on=["signal_date", "ticker"], how="inner", validate="one_to_one")
        expected_eval_rows = len(eval_base.dropna(subset=["fwd_ret_21"]))
        actual_eval_rows = len(merged.dropna(subset=["fwd_ret_21"]))
        if actual_eval_rows != expected_eval_rows:
            raise RuntimeError(
                f"{subset}: evaluation merge lost rows {actual_eval_rows} != {expected_eval_rows}"
            )

        per_date = date_stability(merged, subset)
        if len(per_date) != 114:
            raise RuntimeError(f"{subset}: expected 114 evaluation periods, got {len(per_date)}")
        all_per_date.append(per_date)
        full_mask = pd.Series(True, index=per_date.index)
        old_mask = pd.to_datetime(per_date.signal_date) < pd.Timestamp("2023-01-01")
        new_mask = pd.to_datetime(per_date.signal_date) >= pd.Timestamp("2023-01-01")
        full_summary[subset] = summarize_period(per_date, full_mask)
        split_summary[subset] = {
            "2017_2022": summarize_period(per_date, old_mask),
            "2023_2026": summarize_period(per_date, new_mask),
        }
        all_feature_drift.append(feature_drift(reference, native, features, subset))
        all_cluster.append(cluster_stability(reference, native, subset))

    per_date_all = pd.concat(all_per_date, ignore_index=True)
    feature_all = pd.concat(all_feature_drift, ignore_index=True)
    cluster_all = pd.concat(all_cluster, ignore_index=True)
    audit_all = pd.concat(all_audit, ignore_index=True)

    decision = directional_decision(full_summary)
    cluster_summary = {
        subset: {
            "mean_adjusted_rand_index": float(g.adjusted_rand_index.mean()),
            "median_adjusted_rand_index": float(g.adjusted_rand_index.median()),
            "mean_cluster_change_1_minus_ari": float((1.0 - g.adjusted_rand_index).mean()),
        }
        for subset, g in cluster_all.groupby("subset", sort=True)
    }
    feature_summary = {
        subset: {
            "mean_of_feature_mean_abs_delta": float(g.mean_abs_delta.mean()),
            "max_feature_mean_abs_delta": float(g.mean_abs_delta.max()),
            "most_sensitive_feature": str(g.sort_values("mean_abs_delta", ascending=False).iloc[0].feature),
        }
        for subset, g in feature_all.groupby("subset", sort=True)
    }

    summary = {
        "line": "Evidence V1",
        "test": "universe_sensitivity_v1",
        "status": "DIAGNOSTIC_COMPLETE",
        "universe": "Original149 frozen with preregistered nested U120/U100/U70 candidates",
        "holdout70_used": False,
        "anchor_A": "frozen full149 Retriever LTR v1 OOS scores restricted to candidate universe; no retraining",
        "method_B_reference": "same LTR v1 retrained on candidate rows with FEATURES_42 computed in full149 reference universe; candidate-relative targets recomputed",
        "method_C_native": "same LTR v1 retrained on source-only panel rebuilt natively inside candidate universe; same candidate-relative targets",
        "primary_stability_metrics": [
            "Top1 agreement to A",
            "Top5 turnover to A",
            "rank correlation to A",
            "normalized mean absolute rank displacement to A",
        ],
        "coverage": coverage,
        "full_2017_2026": full_summary,
        "temporal_splits": split_summary,
        "cluster_stability_reference_vs_native": cluster_summary,
        "feature_drift_reference_vs_native": feature_summary,
        "decision": decision,
        "interpretation_rule": (
            "Performance metrics are diagnostic only. This test asks whether stable-reference representation "
            "reduces ranking sensitivity to candidate-universe shrinkage; it is not a promotion test."
        ),
    }

    per_date_all.to_csv(out / "PER_DATE_STABILITY.csv", index=False)
    feature_all.to_csv(out / "FEATURE_DRIFT.csv", index=False)
    cluster_all.to_csv(out / "CLUSTER_STABILITY.csv", index=False)
    audit_all.to_csv(out / "FIT_AUDIT.csv", index=False)
    (out / "CONFIG.json").write_text(json.dumps({
        "ltr_config": LTR_CFG,
        "eval_start": str(EVAL_START.date()),
        "eval_end_exclusive": str(EVAL_END.date()),
        "subsets": [120, 100, 70],
        "decision_rule": decision["rule"],
    }, indent=2) + "\n")
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")

    files = [
        "PER_DATE_STABILITY.csv",
        "FEATURE_DRIFT.csv",
        "CLUSTER_STABILITY.csv",
        "FIT_AUDIT.csv",
        "CONFIG.json",
        "SUMMARY.json",
    ]
    manifest = {
        "test": "universe_sensitivity_v1",
        "files_sha256": {f: sha256_file(out / f) for f in files},
    }
    (out / "RESULT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
