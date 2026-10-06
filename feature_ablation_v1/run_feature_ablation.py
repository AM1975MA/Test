#!/usr/bin/env python3
"""COMPACT21_ORTHOGONAL_FEATURE_ABLATION_V1

Feature discovery only. This script never fits the production XGB/HGB ranker.
Supervised selection evidence is restricted to mature rows strictly before
2017-01-01. Post-2017 data are used only for outcome-free feature stability
audits.

The selector deliberately combines complementary evidence:
  * cross-sectional Information Coefficient (Spearman) with conservative FDR,
  * nonlinear mutual information,
  * Boruta-style shadow-feature confirmation with ExtraTrees,
  * cross-snapshot perturbation stability,
  * semantic-family de-duplication,
  * mRMR-style greedy orthogonalization.

The output is a frozen ladder of nested feature sets for a later, separate
ranker benchmark. No CAGR, strategy return or post-2017 target is read here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ttest_1samp
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_selection import mutual_info_regression

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/etf_trader_v2/src")]

from etf_trader.source_only import kernel as k
from ranker_stability_v1.run_ranker_benchmark_full import load, train_frame, align

KEYS = ["signal_date", "ticker"]
DISCOVERY_CUTOFF = pd.Timestamp("2017-01-01")
AUDIT_END = pd.Timestamp("2026-06-30")
MIN_GROUP = 12
BORUTA_SEEDS = (101, 202, 303)
BORUTA_TREES = 256
BORUTA_SAMPLE_CAP = 30000
MI_SAMPLE_CAP = 30000
SET_SIZES = (8, 12, 16, 24, 32, 40)


def semantic_family(name: str) -> str:
    for suffix in ("_pct", "_dev"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def safe_rank_pct(s: pd.Series) -> pd.Series:
    return s.rank(method="average", pct=True)


def cross_sectional_rank_frame(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    x = frame[KEYS + features].copy()
    for feature in features:
        x[feature] = (
            x.groupby("signal_date", sort=False)[feature]
            .transform(safe_rank_pct)
            .astype(float)
        )
    return x


def finite_corr(a: np.ndarray, b: np.ndarray) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3:
        return float("nan")
    aa = pd.Series(a[m])
    bb = pd.Series(b[m])
    if aa.nunique(dropna=True) < 2 or bb.nunique(dropna=True) < 2:
        return float("nan")
    return float(aa.corr(bb, method="spearman"))


def pair_feature_stability(a: pd.DataFrame, b: pd.DataFrame, feature: str) -> dict:
    av = pd.to_numeric(a[feature], errors="coerce").to_numpy(float)
    bv = pd.to_numeric(b[feature], errors="coerce").to_numpy(float)
    an = ~np.isfinite(av)
    bn = ~np.isfinite(bv)
    both = np.isfinite(av) & np.isfinite(bv)

    exact = (av == bv) | (an & bn)
    raw_spearman = finite_corr(av, bv)

    if both.any():
        q1, q3 = np.nanquantile(
            np.concatenate([av[both], bv[both]]), [0.25, 0.75]
        )
        scale = max(float(q3 - q1), 1e-12)
        scaled_mad = float(np.nanmedian(np.abs(av[both] - bv[both])) / scale)
    else:
        scaled_mad = float("nan")

    ar = (
        pd.DataFrame({"signal_date": a["signal_date"], "v": av})
        .groupby("signal_date", sort=False)["v"]
        .rank(method="average", pct=True)
        .to_numpy(float)
    )
    br = (
        pd.DataFrame({"signal_date": b["signal_date"], "v": bv})
        .groupby("signal_date", sort=False)["v"]
        .rank(method="average", pct=True)
        .to_numpy(float)
    )
    rm = np.isfinite(ar) & np.isfinite(br)
    rank_mad = float(np.mean(np.abs(ar[rm] - br[rm]))) if rm.any() else float("nan")

    return {
        "raw_spearman": raw_spearman,
        "rank_mean_abs": rank_mad,
        "scaled_value_median_abs": scaled_mad,
        "missingness_mismatch": float(np.mean(an != bn)),
        "exact_or_joint_nan_fraction": float(np.mean(exact)),
        "common_finite": int(both.sum()),
    }


def aggregate_stability(frames: dict[int, pd.DataFrame], feature: str) -> dict:
    out = {}
    vals = []
    for i, j in ((1, 2), (1, 3), (2, 3)):
        d = pair_feature_stability(frames[i], frames[j], feature)
        out[f"{i}-{j}"] = d
        vals.append(d)

    def med(field: str, *, invert_nan: float | None = None) -> float:
        arr = np.array([z[field] for z in vals], dtype=float)
        ok = np.isfinite(arr)
        if not ok.any():
            return float("nan") if invert_nan is None else invert_nan
        return float(np.median(arr[ok]))

    return {
        "pairs": out,
        "median_raw_spearman": med("raw_spearman"),
        "median_rank_mean_abs": med("rank_mean_abs"),
        "median_scaled_value_median_abs": med("scaled_value_median_abs"),
        "median_missingness_mismatch": med("missingness_mismatch"),
        "median_exact_or_joint_nan_fraction": med("exact_or_joint_nan_fraction"),
    }


def monthly_ic(frame: pd.DataFrame, feature: str) -> pd.Series:
    rows = []
    for dt, g in frame.groupby("signal_date", sort=True):
        x = pd.to_numeric(g[feature], errors="coerce")
        y = pd.to_numeric(g["target_rank_21"], errors="coerce")
        m = np.isfinite(x.to_numpy(float)) & np.isfinite(y.to_numpy(float))
        if m.sum() < MIN_GROUP:
            continue
        xx = x.to_numpy(float)[m]
        yy = y.to_numpy(float)[m]
        if np.unique(xx).size < 4 or np.unique(yy).size < 4:
            continue
        r = pd.Series(xx).corr(pd.Series(yy), method="spearman")
        if np.isfinite(r):
            rows.append((pd.Timestamp(dt), float(r)))
    if not rows:
        return pd.Series(dtype=float)
    return pd.Series({dt: value for dt, value in rows}).sort_index()


def robust_relevance(frames: dict[int, pd.DataFrame], feature: str) -> dict:
    per_repeat = {}
    means = []
    pvals = []
    sign_rates = []
    for i in (1, 2, 3):
        ic = monthly_ic(frames[i], feature)
        if len(ic):
            mean_ic = float(ic.mean())
            t = ttest_1samp(ic.to_numpy(float), popmean=0.0, nan_policy="omit")
            p = float(t.pvalue) if np.isfinite(t.pvalue) else 1.0
            consensus_sign = np.sign(mean_ic)
            if consensus_sign == 0:
                sign_rate = 0.5
            else:
                sign_rate = float(np.mean(np.sign(ic.to_numpy(float)) == consensus_sign))
        else:
            mean_ic, p, sign_rate = float("nan"), 1.0, 0.0
        per_repeat[str(i)] = {
            "mean_monthly_ic": mean_ic,
            "abs_mean_monthly_ic": abs(mean_ic) if np.isfinite(mean_ic) else float("nan"),
            "months": int(len(ic)),
            "pvalue_vs_zero": p,
            "same_sign_month_fraction": sign_rate,
        }
        means.append(mean_ic)
        pvals.append(p)
        sign_rates.append(sign_rate)

    finite_means = np.array([x for x in means if np.isfinite(x)], dtype=float)
    if len(finite_means):
        median_ic = float(np.median(finite_means))
        median_abs_ic = float(np.median(np.abs(finite_means)))
        same_direction = float(
            max(np.mean(finite_means > 0), np.mean(finite_means < 0))
        )
    else:
        median_ic = median_abs_ic = float("nan")
        same_direction = 0.0

    return {
        "per_repeat": per_repeat,
        "median_mean_ic": median_ic,
        "median_abs_mean_ic": median_abs_ic,
        "worst_repeat_pvalue": float(max(pvals)),
        "median_month_sign_consistency": float(np.median(sign_rates)),
        "repeat_direction_agreement": same_direction,
    }


def deterministic_subsample(frame: pd.DataFrame, cap: int) -> pd.DataFrame:
    if len(frame) <= cap:
        return frame
    idx = np.linspace(0, len(frame) - 1, cap, dtype=int)
    return frame.iloc[idx].copy()


def mi_scores(frames: dict[int, pd.DataFrame], features: list[str]) -> dict[str, dict]:
    per = {feature: [] for feature in features}
    for i in (1, 2, 3):
        z = deterministic_subsample(frames[i].sort_values(KEYS), MI_SAMPLE_CAP)
        y = pd.to_numeric(z["target_rank_21"], errors="coerce").to_numpy(float)
        for feature in features:
            x = pd.to_numeric(z[feature], errors="coerce").to_numpy(float)
            m = np.isfinite(x) & np.isfinite(y)
            if m.sum() < 100 or np.unique(x[m]).size < 4:
                score = 0.0
            else:
                score = float(
                    mutual_info_regression(
                        x[m].reshape(-1, 1),
                        y[m],
                        discrete_features=False,
                        n_neighbors=5,
                        random_state=0,
                    )[0]
                )
            per[feature].append(score)
    return {
        f: {
            "per_repeat": [float(x) for x in values],
            "median_mi": float(np.median(values)),
            "min_mi": float(np.min(values)),
        }
        for f, values in per.items()
    }


def _boruta_matrix(frame: pd.DataFrame, features: list[str]) -> tuple[np.ndarray, np.ndarray]:
    z = deterministic_subsample(frame.sort_values(KEYS), BORUTA_SAMPLE_CAP)
    ranked = cross_sectional_rank_frame(z, features)
    X = ranked[features].to_numpy(float)
    X[~np.isfinite(X)] = 0.5
    y = pd.to_numeric(z["target_rank_21"], errors="coerce").to_numpy(float)
    m = np.isfinite(y)
    return X[m], y[m]


def boruta_shadow_scores(
    frames: dict[int, pd.DataFrame], features: list[str]
) -> dict[str, dict]:
    hits = {feature: 0 for feature in features}
    ratios = {feature: [] for feature in features}
    runs = 0
    for repeat in (1, 2, 3):
        X, y = _boruta_matrix(frames[repeat], features)
        if len(y) < 500:
            raise ValueError("Too few rows for Boruta shadow selector")
        for seed in BORUTA_SEEDS:
            rng = np.random.default_rng(seed + repeat * 1000)
            shadow = np.empty_like(X)
            for j in range(X.shape[1]):
                shadow[:, j] = X[rng.permutation(len(X)), j]
            Xall = np.concatenate([X, shadow], axis=1)
            model = ExtraTreesRegressor(
                n_estimators=BORUTA_TREES,
                max_features="sqrt",
                min_samples_leaf=8,
                random_state=seed,
                n_jobs=1,
            )
            model.fit(Xall, y)
            imp = model.feature_importances_
            real = imp[: len(features)]
            sh = imp[len(features) :]
            threshold = float(np.quantile(sh, 0.95))
            denom = max(threshold, 1e-18)
            for j, feature in enumerate(features):
                hits[feature] += int(real[j] > threshold)
                ratios[feature].append(float(real[j] / denom))
            runs += 1
    return {
        feature: {
            "hit_fraction": float(hits[feature] / runs),
            "median_importance_to_shadow95": float(np.median(ratios[feature])),
            "runs": runs,
        }
        for feature in features
    }


def bh_qvalues(pvalues: dict[str, float]) -> dict[str, float]:
    names = list(pvalues)
    p = np.array([min(max(float(pvalues[n]), 0.0), 1.0) for n in names])
    order = np.argsort(p)
    ranked = p[order]
    qrank = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    qrank = np.minimum.accumulate(qrank[::-1])[::-1]
    qrank = np.clip(qrank, 0.0, 1.0)
    q = np.empty_like(qrank)
    q[order] = qrank
    return {name: float(q[i]) for i, name in enumerate(names)}


def percentile(values: dict[str, float], higher_is_better: bool = True) -> dict[str, float]:
    s = pd.Series(values, dtype=float)
    if not higher_is_better:
        s = -s
    s = s.replace([np.inf, -np.inf], np.nan)
    if s.notna().sum() == 0:
        return {k: 0.0 for k in values}
    r = s.rank(method="average", pct=True).fillna(0.0)
    return {k: float(r[k]) for k in values}


def redundancy_matrix(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    ranked = cross_sectional_rank_frame(frame.sort_values(KEYS), features)
    corr = ranked[features].corr(method="pearson", min_periods=100).abs()
    corr = corr.fillna(0.0)
    np.fill_diagonal(corr.values, 1.0)
    return corr


def orthogonal_greedy(
    features: list[str],
    consensus: dict[str, float],
    corr: pd.DataFrame,
) -> tuple[list[str], list[dict]]:
    remaining = set(features)
    chosen = []
    used_families = set()
    trace = []
    while remaining:
        pool = [f for f in remaining if semantic_family(f) not in used_families]
        if not pool:
            break

        best = None
        best_utility = -np.inf
        best_red = 0.0
        for feature in sorted(pool):
            if chosen:
                red = float(corr.loc[feature, chosen].max())
            else:
                red = 0.0
            utility = float(consensus[feature] * (1.0 - 0.70 * red))
            if utility > best_utility + 1e-15:
                best, best_utility, best_red = feature, utility, red
        if best is None:
            break
        chosen.append(best)
        remaining.remove(best)
        used_families.add(semantic_family(best))
        trace.append(
            {
                "rank": len(chosen),
                "feature": best,
                "family": semantic_family(best),
                "consensus_score": float(consensus[best]),
                "max_abs_rank_corr_to_prior": float(best_red),
                "orthogonal_utility": float(best_utility),
            }
        )
    return chosen, trace


def json_clean(value):
    if isinstance(value, dict):
        return {k: json_clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_clean(v) for v in value]
    if isinstance(value, tuple):
        return [json_clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        x = float(value)
        return x if math.isfinite(x) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    return value


def markdown_table(rows: list[dict]) -> str:
    if not rows:
        return "_No rows_"
    cols = list(rows[0])
    def fmt(v):
        if v is None:
            return ""
        if isinstance(v, float):
            return f"{v:.6g}" if math.isfinite(v) else ""
        return str(v).replace("|", r"\|")
    head = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = [
        "| " + " | ".join(fmt(row.get(c)) for c in cols) + " |"
        for row in rows
    ]
    return "\n".join([head, sep, *body])

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    for i in (1, 2, 3):
        ap.add_argument(f"--r{i}", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary-md", required=True)
    args = ap.parse_args()

    features = list(k.F2D_FEATURES)
    if len(features) != 125:
        raise ValueError(f"Expected frozen 125 Compact21 features, got {len(features)}")
    if len({semantic_family(f) for f in features}) != 46:
        raise ValueError("Expected frozen 46 semantic feature families")

    raw = {i: load(Path(getattr(args, f"r{i}"))) for i in (1, 2, 3)}

    discovery_native = {i: train_frame(raw[i], 2017) for i in (1, 2, 3)}
    d_aligned = align([discovery_native[i] for i in (1, 2, 3)])
    discovery = {i: d_aligned[i - 1] for i in (1, 2, 3)}
    if min(len(x) for x in discovery.values()) < 1000:
        raise ValueError("Insufficient common pre-2017 discovery rows")
    for i in (1, 2, 3):
        if not (discovery[i]["signal_date"] < DISCOVERY_CUTOFF).all():
            raise ValueError("Discovery leakage: signal_date reaches 2017")
        if not (discovery[i]["exit_date_21"] < DISCOVERY_CUTOFF).all():
            raise ValueError("Discovery leakage: immature target reaches 2017")

    audit_native = {}
    for i in (1, 2, 3):
        f = raw[i]
        valid = f[features].notna().sum(axis=1) >= 30
        audit_native[i] = (
            f[
                (f.signal_date >= DISCOVERY_CUTOFF)
                & (f.signal_date <= AUDIT_END)
                & valid
            ]
            .sort_values(KEYS)
            .reset_index(drop=True)
        )
    a_aligned = align([audit_native[i] for i in (1, 2, 3)])
    audit = {i: a_aligned[i - 1][KEYS + features].copy() for i in (1, 2, 3)}

    relevance = {}
    pre_stability = {}
    post_stability = {}
    for idx, feature in enumerate(features, 1):
        relevance[feature] = robust_relevance(discovery, feature)
        pre_stability[feature] = aggregate_stability(discovery, feature)
        post_stability[feature] = aggregate_stability(audit, feature)
        if idx % 10 == 0:
            print(f"FEATURE_DIAGNOSTICS {idx}/{len(features)}", flush=True)

    mi = mi_scores(discovery, features)
    print("MI_COMPLETE", flush=True)
    boruta = boruta_shadow_scores(discovery, features)
    print("BORUTA_COMPLETE", flush=True)

    qvalues = bh_qvalues(
        {f: relevance[f]["worst_repeat_pvalue"] for f in features}
    )

    ic_pct = percentile({f: relevance[f]["median_abs_mean_ic"] for f in features})
    mi_pct = percentile({f: mi[f]["median_mi"] for f in features})
    boruta_pct = percentile({f: boruta[f]["hit_fraction"] for f in features})
    repdir_pct = percentile(
        {f: relevance[f]["repeat_direction_agreement"] for f in features}
    )

    stab_spear_pct = percentile(
        {f: pre_stability[f]["median_raw_spearman"] for f in features}
    )
    stab_rank_pct = percentile(
        {f: pre_stability[f]["median_rank_mean_abs"] for f in features},
        higher_is_better=False,
    )
    missing_pct = percentile(
        {f: pre_stability[f]["median_missingness_mismatch"] for f in features},
        higher_is_better=False,
    )

    scores = {}
    for f in features:
        predictive = (
            0.40 * ic_pct[f]
            + 0.25 * mi_pct[f]
            + 0.25 * boruta_pct[f]
            + 0.10 * repdir_pct[f]
        )
        robustness = (
            0.45 * stab_spear_pct[f]
            + 0.40 * stab_rank_pct[f]
            + 0.15 * missing_pct[f]
        )
        consensus = 0.65 * predictive + 0.35 * robustness
        scores[f] = {
            "predictive_score": float(predictive),
            "robustness_score": float(robustness),
            "consensus_score": float(consensus),
        }

    corr = redundancy_matrix(discovery[2], features)
    chosen, trace = orthogonal_greedy(
        features,
        {f: scores[f]["consensus_score"] for f in features},
        corr,
    )
    if len(chosen) != 46:
        raise ValueError(f"Expected one champion per 46 semantic families, got {len(chosen)}")

    ladders = {f"K{k}": chosen[:k] for k in SET_SIZES}
    ladders["FAMILY46"] = chosen

    by_consensus = sorted(features, key=lambda f: (-scores[f]["consensus_score"], f))
    family_champions = {}
    for f in by_consensus:
        family_champions.setdefault(semantic_family(f), f)
    strong = [
        f
        for f in chosen
        if qvalues[f] <= 0.10
        and boruta[f]["hit_fraction"] >= 0.50
        and pre_stability[f]["median_raw_spearman"] >= 0.995
    ]

    feature_rows = []
    for f in features:
        feature_rows.append(
            {
                "feature": f,
                "family": semantic_family(f),
                "fdr_q_worst_repeat": qvalues[f],
                **scores[f],
                "relevance": relevance[f],
                "mutual_information": mi[f],
                "boruta_shadow": boruta[f],
                "pre2017_stability": pre_stability[f],
                "post2017_outcome_free_stability_audit": post_stability[f],
            }
        )

    result = {
        "schema": "COMPACT21_ORTHOGONAL_FEATURE_ABLATION_V1",
        "status": "FEATURE_SELECTION_COMPLETE_NO_FINAL_RANKER_FIT",
        "frozen_constraints": {
            "features": 125,
            "semantic_families": 46,
            "supervised_discovery_cutoff_exclusive": str(DISCOVERY_CUTOFF.date()),
            "post2017_targets_read": False,
            "strategy_metrics_read": False,
            "production_ranker_fit": False,
            "set_sizes": list(SET_SIZES),
            "boruta_seeds": list(BORUTA_SEEDS),
            "boruta_trees": BORUTA_TREES,
            "boruta_sample_cap": BORUTA_SAMPLE_CAP,
            "mi_sample_cap": MI_SAMPLE_CAP,
        },
        "inputs": {
            str(i): {
                "path": str(Path(getattr(args, f"r{i}")) / "TI_COMPACT.parquet"),
                "sha256": sha256(Path(getattr(args, f"r{i}")) / "TI_COMPACT.parquet"),
                "discovery_rows_common": len(discovery[i]),
                "audit_rows_common": len(audit[i]),
            }
            for i in (1, 2, 3)
        },
        "selection_method": {
            "relevance": "cross-sectional monthly Spearman IC + conservative worst-repeat BH-FDR",
            "nonlinear": "mutual_info_regression, deterministic subsample",
            "all_relevant": "Boruta-style ExtraTrees real-vs-95th-percentile shadow importance",
            "robustness": "three-pair raw Spearman, cross-sectional rank MAD, missingness mismatch",
            "redundancy": "absolute pooled cross-sectional-rank correlation on Repeat2 pre-2017",
            "orthogonalization": "mRMR-style greedy utility with hard one-representation-per-semantic-family",
            "final_model_training": "DEFERRED",
        },
        "ladders": ladders,
        "strong_evidence_features": strong,
        "orthogonal_trace": trace,
        "family_champions": family_champions,
        "features": feature_rows,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    result = json_clean(result)
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")

    rows = []
    lookup = {r["feature"]: r for r in feature_rows}
    for step in trace:
        f = step["feature"]
        r = lookup[f]
        rows.append(
            {
                "rank": step["rank"],
                "feature": f,
                "family": step["family"],
                "consensus": r["consensus_score"],
                "IC": r["relevance"]["median_abs_mean_ic"],
                "FDR_q": r["fdr_q_worst_repeat"],
                "MI": r["mutual_information"]["median_mi"],
                "Boruta": r["boruta_shadow"]["hit_fraction"],
                "pre_spearman": r["pre2017_stability"]["median_raw_spearman"],
                "pre_rank_MAD": r["pre2017_stability"]["median_rank_mean_abs"],
                "post_rank_MAD": r["post2017_outcome_free_stability_audit"]["median_rank_mean_abs"],
                "max_corr_prior": step["max_abs_rank_corr_to_prior"],
            }
        )
    table_rows = rows

    md = [
        "# COMPACT21_ORTHOGONAL_FEATURE_ABLATION_V1",
        "",
        "**Status:** FEATURE_SELECTION_COMPLETE_NO_FINAL_RANKER_FIT",
        "",
        "Supervised feature discovery uses only mature rows before 2017-01-01. "
        "The 2017-2026 interval is used only for outcome-free feature-stability auditing. "
        "No production XGB/HGB ranker and no strategy backtest is fitted or evaluated here.",
        "",
        f"- Frozen candidates: {len(features)} features / {len(set(map(semantic_family, features)))} semantic families",
        f"- Common pre-2017 discovery rows per repeat: {len(discovery[1])}",
        f"- Common 2017-2026 outcome-free audit rows per repeat: {len(audit[1])}",
        f"- Strong-evidence champions: {len(strong)}",
        "",
        "## Frozen nested ladders",
        "",
    ]
    for name, feats in ladders.items():
        md.append(f"- **{name} ({len(feats)}):** " + ", ".join(feats))
    md += [
        "",
        "## Orthogonal family champions",
        "",
        markdown_table(table_rows),
        "",
        "## Interpretation contract",
        "",
        "These sets are candidate inputs for a separate pre-registered training benchmark. "
        "Do not pick a set from CAGR or strategy P&L. The next stage should compare the "
        "nested ladders on the existing three frozen snapshots with the same stability and "
        "predictive-quality endpoints used by the Compact21 stability work.",
        "",
    ]
    Path(args.summary_md).write_text("\n".join(md) + "\n")
    print(json.dumps({
        "status": result["status"],
        "strong_evidence_count": len(strong),
        "K8": ladders["K8"],
        "K16": ladders["K16"],
        "K24": ladders["K24"],
    }, indent=2))


if __name__ == "__main__":
    main()
