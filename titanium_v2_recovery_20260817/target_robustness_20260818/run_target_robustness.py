#!/usr/bin/env python3
"""Stress-test Titanium Compact targets under plausible live retraining perturbations.

The target weights and all downstream Titanium components stay frozen.  Only the
training schedule/window/input vintage or ticker availability changes.  Labels
and the daily evaluation path always use the unperturbed source data.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRanker


SEEDS = (101, 202, 303)
VARIANTS = {
    "BASELINE_21": ("target_21", "exit_date_21"),
    "MULTI_45_35_20": ("target_multi_45_35_20", "exit_date_63"),
    "CONSENSUS_MULTI": ("target_consensus", "exit_date_63"),
}


@dataclass(frozen=True)
class Scenario:
    name: str
    family: str
    cadence: str = "annual"
    annual_month: int = 1
    rolling_years: int | None = None
    train_ticker_dropout: float = 0.0
    feature_noise_fraction: float = 0.0
    scenario_seed: int = 260818
    inference_ticker_dropout: float = 0.0


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def add_targets(compact: pd.DataFrame) -> pd.DataFrame:
    out = compact.copy()
    ranks = out[["target_rank_21", "target_rank_42", "target_rank_63"]]
    out["target_21"] = out["target_rank_21"]
    out["target_multi_45_35_20"] = (
        0.45 * out["target_rank_21"] + 0.35 * out["target_rank_42"] + 0.20 * out["target_rank_63"]
    )
    out["target_consensus"] = (
        0.35 * out["target_rank_21"]
        + 0.30 * out["target_rank_42"]
        + 0.20 * out["target_rank_63"]
        + 0.15 * ranks.min(axis=1)
    )
    return out


def stable_ticker_sample(tickers: list[str], fraction: float, seed: int) -> list[str]:
    if fraction <= 0:
        return []
    count = max(1, int(round(len(tickers) * fraction)))
    ordered = sorted(
        tickers,
        key=lambda ticker: hashlib.sha256(f"{seed}|{ticker}".encode("utf-8")).hexdigest(),
    )
    return ordered[:count]


def perturb_features(compact: pd.DataFrame, features: list[str], fraction: float, seed: int) -> pd.DataFrame:
    if fraction <= 0:
        return compact
    out = compact.copy()
    rng = np.random.default_rng(seed)
    for feature in features:
        values = out[feature].to_numpy(float, copy=True)
        finite = np.isfinite(values)
        if not finite.any():
            continue
        q25, q75 = np.nanquantile(values[finite], [0.25, 0.75])
        robust_scale = float((q75 - q25) / 1.349)
        if not np.isfinite(robust_scale) or robust_scale <= 0:
            robust_scale = float(np.nanstd(values[finite]))
        if not np.isfinite(robust_scale) or robust_scale <= 0:
            continue
        values[finite] += rng.normal(0.0, fraction * robust_scale, size=int(finite.sum()))
        if feature.endswith("_pct"):
            values[finite] = np.clip(values[finite], 0.0, 1.0)
        out[feature] = values
    return out


def refit_cutoffs(scenario: Scenario, first_date: pd.Timestamp, last_date: pd.Timestamp) -> list[pd.Timestamp]:
    if scenario.cadence == "quarterly":
        start = pd.Timestamp(first_date.year, 1, 1)
        while start > first_date:
            start -= pd.DateOffset(months=3)
        while start + pd.DateOffset(months=3) <= first_date:
            start += pd.DateOffset(months=3)
        cutoffs = list(pd.date_range(start, last_date + pd.DateOffset(months=3), freq="3MS"))
    else:
        candidates = [pd.Timestamp(year, scenario.annual_month, 1) for year in range(first_date.year - 2, last_date.year + 2)]
        start_candidates = [value for value in candidates if value <= first_date]
        start = max(start_candidates)
        cutoffs = [value for value in candidates if value >= start and value <= last_date + pd.DateOffset(years=1)]
    if cutoffs[-1] <= last_date:
        delta = pd.DateOffset(months=3) if scenario.cadence == "quarterly" else pd.DateOffset(years=1)
        cutoffs.append(cutoffs[-1] + delta)
    return cutoffs


def train_variant(
    variant: str,
    target: str,
    exit_column: str,
    scenario: Scenario,
    compact: pd.DataFrame,
    features: list[str],
    params: dict,
    eval_start: pd.Timestamp,
    eval_end: pd.Timestamp,
) -> tuple[str, pd.DataFrame, pd.DataFrame]:
    feature_frame = perturb_features(compact, features, scenario.feature_noise_fraction, scenario.scenario_seed)
    cvalid = feature_frame[features].notna().sum(axis=1).ge(30)
    tickers = sorted(feature_frame["ticker"].unique())
    dropped = set(stable_ticker_sample(tickers, scenario.train_ticker_dropout, scenario.scenario_seed))
    cutoffs = refit_cutoffs(scenario, eval_start, eval_end)
    prediction_rows: list[pd.DataFrame] = []
    audits: list[dict] = []

    for cutoff, next_cutoff in zip(cutoffs[:-1], cutoffs[1:]):
        test_mask = (
            feature_frame["signal_date"].ge(max(cutoff, eval_start))
            & feature_frame["signal_date"].lt(min(next_cutoff, eval_end + pd.Timedelta(days=1)))
            & cvalid
        )
        test = feature_frame.loc[test_mask].sort_values(["signal_date", "ticker"])
        if test.empty:
            continue
        train_mask = (
            feature_frame["signal_date"].lt(cutoff)
            & feature_frame[exit_column].lt(cutoff)
            & feature_frame[target].notna()
            & cvalid
            & ~feature_frame["ticker"].isin(dropped)
        )
        if scenario.rolling_years is not None:
            train_mask &= feature_frame["signal_date"].ge(cutoff - pd.DateOffset(years=scenario.rolling_years))
        train = feature_frame.loc[train_mask].sort_values(["signal_date", "ticker"])
        minimum_train_dates = 48 if scenario.rolling_years is not None else 60
        if train["signal_date"].nunique() < minimum_train_dates:
            raise RuntimeError(f"{scenario.name}/{variant}: only {train['signal_date'].nunique()} train dates at {cutoff.date()}")
        groups = train.groupby("signal_date", sort=True).size().tolist()
        labels = (100.0 * train[target]).round().astype(int)
        frame = test[["signal_date", "ticker"]].copy()
        for seed in SEEDS:
            model = XGBRanker(**params, random_state=seed)
            model.fit(
                train[features].replace([np.inf, -np.inf], np.nan),
                labels,
                group=groups,
                verbose=False,
            )
            frame[f"raw_seed_{seed}"] = model.predict(test[features].replace([np.inf, -np.inf], np.nan))
        prediction_rows.append(frame)
        audits.append(
            {
                "scenario": scenario.name,
                "variant": variant,
                "cutoff": str(cutoff.date()),
                "next_cutoff": str(next_cutoff.date()),
                "train_dates": int(train["signal_date"].nunique()),
                "train_rows": int(len(train)),
                "train_tickers": int(train["ticker"].nunique()),
                "dropped_train_tickers": int(len(dropped)),
                "test_dates": int(test["signal_date"].nunique()),
                "test_rows": int(len(test)),
            }
        )

    prediction = pd.concat(prediction_rows, ignore_index=True).sort_values(["signal_date", "ticker"])
    if prediction.duplicated(["signal_date", "ticker"]).any():
        raise RuntimeError(f"{scenario.name}/{variant}: duplicate predictions")
    for seed in SEEDS:
        prediction[f"rank_seed_{seed}"] = prediction.groupby("signal_date")[f"raw_seed_{seed}"].rank(pct=True)
    prediction["compact_raw"] = prediction[[f"raw_seed_{seed}" for seed in SEEDS]].mean(axis=1)
    prediction["compact_rank"] = prediction.groupby("signal_date")["compact_raw"].rank(pct=True)
    return variant, prediction, pd.DataFrame(audits)


def build_final_panel(prediction: pd.DataFrame, fixed: pd.DataFrame) -> pd.DataFrame:
    panel = prediction.merge(
        fixed[["signal_date", "ticker", "tail_rank", "macro_category", "top_macro", "macro_gap_z", "macro_bonus"]],
        on=["signal_date", "ticker"], how="inner", validate="one_to_one",
    )
    panel["titanium_score_pre_macro"] = 0.70 * panel["compact_rank"] + 0.30 * panel["tail_rank"]
    panel["titanium_score"] = panel["titanium_score_pre_macro"] + panel["macro_bonus"]
    for seed in SEEDS:
        panel[f"final_seed_{seed}"] = 0.70 * panel[f"rank_seed_{seed}"] + 0.30 * panel["tail_rank"] + panel["macro_bonus"]
    return panel


def path_metrics(paths: np.ndarray) -> pd.DataFrame:
    returns = np.zeros_like(paths, dtype=float)
    returns[:, 1:] = paths[:, 1:] / paths[:, :-1] - 1.0
    compounded = np.cumprod(1.0 + returns, axis=1)
    cagr = compounded[:, -1] ** (252.0 / returns.shape[1]) - 1.0
    drawdown = compounded / np.maximum.accumulate(compounded, axis=1) - 1.0
    std = returns.std(axis=1, ddof=1)
    sharpe = np.sqrt(252.0) * returns.mean(axis=1) / np.where(std > 0.0, std, np.nan)
    return pd.DataFrame({"basket": np.arange(len(paths)), "cagr": cagr, "maxdd": drawdown.min(axis=1), "sharpe": sharpe})


def selection_stability(panel: pd.DataFrame, reference: pd.DataFrame, membership: pd.DataFrame) -> dict[str, float]:
    reference_eval = reference.loc[reference["signal_date"].isin(panel["signal_date"].unique())].copy()
    key_check = reference_eval[["signal_date", "ticker"]].merge(
        panel[["signal_date", "ticker"]], on=["signal_date", "ticker"], how="outer", indicator=True,
        validate="one_to_one",
    )
    joined = reference_eval[["signal_date", "ticker", "titanium_score"]].merge(
        panel[["signal_date", "ticker", "titanium_score"]],
        on=["signal_date", "ticker"], suffixes=("_reference", "_stress"), validate="one_to_one",
    )
    correlations = joined.groupby("signal_date").apply(
        lambda x: x["titanium_score_reference"].corr(x["titanium_score_stress"], method="spearman"),
        include_groups=False,
    )
    unrestricted = reference_eval.sort_values(
        ["signal_date", "titanium_score", "ticker"], ascending=[True, False, True], kind="mergesort"
    ).drop_duplicates("signal_date")[["signal_date", "ticker"]].merge(
        panel.sort_values(
            ["signal_date", "titanium_score", "ticker"], ascending=[True, False, True], kind="mergesort"
        ).drop_duplicates("signal_date")[["signal_date", "ticker"]],
        on="signal_date", suffixes=("_reference", "_stress"), validate="one_to_one",
    )
    reference_expanded = reference_eval[["signal_date", "ticker", "titanium_score"]].merge(
        membership, on="ticker", how="inner", validate="many_to_many"
    )
    stress_expanded = panel[["signal_date", "ticker", "titanium_score"]].merge(
        membership, on="ticker", how="inner", validate="many_to_many"
    )
    reference_top = reference_expanded.sort_values(
        ["signal_date", "basket", "titanium_score", "ticker"],
        ascending=[True, True, False, True], kind="mergesort",
    ).groupby(["signal_date", "basket"], sort=True).head(2)
    stress_top = stress_expanded.sort_values(
        ["signal_date", "basket", "titanium_score", "ticker"],
        ascending=[True, True, False, True], kind="mergesort",
    ).groupby(["signal_date", "basket"], sort=True).head(2)
    reference_top["rank_number"] = reference_top.groupby(["signal_date", "basket"]).cumcount() + 1
    stress_top["rank_number"] = stress_top.groupby(["signal_date", "basket"]).cumcount() + 1
    wide_ref = reference_top.pivot(index=["signal_date", "basket"], columns="rank_number", values=["ticker", "titanium_score"])
    wide_stress = stress_top.pivot(index=["signal_date", "basket"], columns="rank_number", values=["ticker", "titanium_score"])
    wide_ref.columns = [f"{field}{int(rank)}" for field, rank in wide_ref.columns]
    wide_stress.columns = [f"{field}{int(rank)}" for field, rank in wide_stress.columns]
    wide_ref = wide_ref.rename(columns={"ticker1": "ref_ticker1", "ticker2": "ref_ticker2", "titanium_score1": "ref_score1", "titanium_score2": "ref_score2"})
    wide_stress = wide_stress.rename(columns={"ticker1": "stress_ticker1", "ticker2": "stress_ticker2", "titanium_score1": "stress_score1", "titanium_score2": "stress_score2"})
    choices = wide_ref.join(wide_stress, how="inner")
    top1 = choices["ref_ticker1"].eq(choices["stress_ticker1"])
    ordered2 = top1 & choices["ref_ticker2"].eq(choices["stress_ticker2"])
    unordered2 = choices.apply(
        lambda row: {row.ref_ticker1, row.ref_ticker2} == {row.stress_ticker1, row.stress_ticker2}, axis=1
    )
    ref_concentrated = (choices["ref_score1"] - choices["ref_score2"]).ge(0.12)
    stress_concentrated = (choices["stress_score1"] - choices["stress_score2"]).ge(0.12)
    return {
        "score_keys_identical": bool(key_check["_merge"].eq("both").all()),
        "max_abs_score_delta": float(np.max(np.abs(joined["titanium_score_reference"] - joined["titanium_score_stress"]))),
        "monthly_score_rank_correlation": float(correlations.mean()),
        "unrestricted_top1_agreement": float(unrestricted["ticker_reference"].eq(unrestricted["ticker_stress"]).mean()),
        "basket_top1_agreement": float(top1.mean()),
        "basket_top2_ordered_agreement": float(ordered2.mean()),
        "basket_top2_set_agreement": float(unordered2.mean()),
        "concentration_regime_agreement": float(ref_concentrated.eq(stress_concentrated).mean()),
        "decision_count": int(len(choices)),
    }


def evaluate_scenario(
    scenario: Scenario,
    panels: dict[str, pd.DataFrame],
    references: dict[str, pd.DataFrame],
    membership: pd.DataFrame,
    baskets: list[list[str]],
    v6,
    mats: dict,
    opportunity: pd.DataFrame,
    clusters: pd.DataFrame,
    calendar: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries: list[dict] = []
    basket_metrics: list[pd.DataFrame] = []
    dropped = set(stable_ticker_sample(sorted(membership["ticker"].unique()), scenario.inference_ticker_dropout, scenario.scenario_seed))
    evaluation_dates = set(calendar["signal_date"])
    for variant, original_panel in panels.items():
        panel = original_panel.loc[
            original_panel["signal_date"].isin(evaluation_dates) & ~original_panel["ticker"].isin(dropped)
        ].copy()
        idx, paths, _direct, _router, _active, _margin, _condition, selections, weights, *_ = v6.simulate_all(
            baskets, panel, opportunity, clusters, mats, calendar
        )
        metrics = path_metrics(paths)
        metrics.insert(0, "variant", variant)
        metrics.insert(0, "scenario", scenario.name)
        basket_metrics.append(metrics)
        stability = selection_stability(panel, references[variant], membership)
        summaries.append(
            {
                "scenario": scenario.name,
                "family": scenario.family,
                "variant": variant,
                "daily_observations": int(len(idx)),
                "signal_dates": int(calendar["signal_date"].nunique()),
                "available_tickers": int(panel["ticker"].nunique()),
                "inference_dropped_tickers": int(len(dropped)),
                "cagr_mean": float(metrics["cagr"].mean()),
                "cagr_median": float(metrics["cagr"].median()),
                "cagr_p10": float(metrics["cagr"].quantile(0.10)),
                "maxdd_mean": float(metrics["maxdd"].mean()),
                "maxdd_p10": float(metrics["maxdd"].quantile(0.10)),
                "sharpe_mean": float(metrics["sharpe"].mean()),
                "concentrated_100pct_rate": float(np.mean(weights[:, :, 0] >= 0.999999)),
                **stability,
            }
        )
    return pd.DataFrame(summaries), pd.concat(basket_metrics, ignore_index=True)


def scenarios() -> list[Scenario]:
    result = [
        Scenario("CONTROL_ANNUAL_EXPANDING", "control"),
        Scenario("CUTOFF_DECEMBER", "cutoff", annual_month=12),
        Scenario("CUTOFF_FEBRUARY", "cutoff", annual_month=2),
        Scenario("QUARTERLY_REFIT", "cutoff", cadence="quarterly"),
        Scenario("ROLLING_5Y", "window", rolling_years=5),
        Scenario("ROLLING_7Y", "window", rolling_years=7),
        Scenario("ROLLING_10Y", "window", rolling_years=10),
        Scenario("TRAIN_TICKER_DROPOUT_5PCT", "ticker_training", train_ticker_dropout=0.05, scenario_seed=5101),
        Scenario("TRAIN_TICKER_DROPOUT_10PCT", "ticker_training", train_ticker_dropout=0.10, scenario_seed=10101),
        Scenario("FEATURE_NOISE_0_5PCT", "price_vintage", feature_noise_fraction=0.005, scenario_seed=5001),
        Scenario("FEATURE_NOISE_1PCT", "price_vintage", feature_noise_fraction=0.01, scenario_seed=10001),
        Scenario("FEATURE_NOISE_2PCT", "price_vintage", feature_noise_fraction=0.02, scenario_seed=20001),
    ]
    for fraction, prefix in ((0.05, "5PCT"), (0.10, "10PCT")):
        for replicate, seed in enumerate((811, 1613, 3251), start=1):
            result.append(Scenario(f"LIVE_MISSING_{prefix}_R{replicate}", "ticker_live", scenario_seed=seed, inference_ticker_dropout=fraction))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-module", type=Path, required=True)
    parser.add_argument("--v6-module", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--fixed-score-panel", type=Path, required=True)
    parser.add_argument("--opportunity-panel", type=Path, required=True)
    parser.add_argument("--clusters", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--reference-score-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--n-estimators", type=int, default=360)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    base = load_module(args.base_module.resolve(), "robust_base")
    v6 = load_module(args.v6_module.resolve(), "robust_v6")
    base.rolling_downvol = lambda ret, h: ret.clip(upper=0.0).rolling(h, min_periods=h).std(ddof=0) * np.sqrt(252)
    mats = v6.load_mats(args.data_dir.resolve())
    dates, compact, _tail, _dictionary = base.build_features(mats)
    compact = add_targets(base.add_labels(compact, mats["Open"], dates))
    fixed = pd.read_parquet(args.fixed_score_panel)
    opportunity = pd.read_csv(args.opportunity_panel)
    clusters = pd.read_csv(args.clusters)
    calendar = pd.read_csv(args.calendar)
    membership = pd.read_csv(args.membership)[["basket", "ticker"]]
    for frame in (compact, fixed, opportunity, clusters, calendar):
        frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="raise")
    for column in ("entry_date", "exit_date"):
        calendar[column] = pd.to_datetime(calendar[column], errors="raise")
    membership["ticker"] = membership["ticker"].astype(str).str.upper().str.strip()
    calendar = calendar.loc[calendar["exit_date"].le(pd.Timestamp("2026-07-01"))].copy()
    eval_start, eval_end = calendar["signal_date"].min(), calendar["signal_date"].max()
    baskets = [group["ticker"].tolist() for _, group in membership.groupby("basket", sort=True)]
    references = {
        variant: pd.read_parquet(args.reference_score_dir / f"{variant}_SCORE_PANEL.parquet")
        for variant in VARIANTS
    }
    for panel in references.values():
        panel["signal_date"] = pd.to_datetime(panel["signal_date"], errors="raise")
        panel["ticker"] = panel["ticker"].astype(str).str.upper().str.strip()

    selected = [scenario for scenario in scenarios() if not args.only or scenario.name in set(args.only)]
    params = dict(base.COMPACT_PARAMS)
    params.update({"n_estimators": args.n_estimators, "n_jobs": 2})
    completed_summaries: list[pd.DataFrame] = []
    completed_baskets: list[pd.DataFrame] = []
    completed_audits: list[pd.DataFrame] = []

    for scenario in selected:
        scenario_dir = args.output_dir / scenario.name
        scenario_dir.mkdir(parents=True, exist_ok=True)
        summary_path = scenario_dir / "SCENARIO_SUMMARY.csv"
        basket_path = scenario_dir / "BASKET_METRICS.csv.gz"
        audit_path = scenario_dir / "FIT_AUDIT.csv"
        if summary_path.exists() and basket_path.exists():
            completed_summaries.append(pd.read_csv(summary_path))
            completed_baskets.append(pd.read_csv(basket_path))
            if audit_path.exists():
                completed_audits.append(pd.read_csv(audit_path))
            print(f"resumed {scenario.name}", flush=True)
            continue

        scenario_started = time.time()
        if scenario.family == "ticker_live":
            panels = references
            audits = []
        else:
            panels: dict[str, pd.DataFrame] = {}
            audits = []
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = {
                    pool.submit(
                        train_variant,
                        variant, target, exit_column, scenario, compact, list(base.F2D_FEATURES),
                        params, eval_start, eval_end,
                    ): variant
                    for variant, (target, exit_column) in VARIANTS.items()
                }
                for future in as_completed(futures):
                    variant, prediction, audit = future.result()
                    panels[variant] = build_final_panel(prediction, fixed)
                    audits.append(audit)
                    print(f"trained {scenario.name}/{variant}", flush=True)
        summary, basket_metrics = evaluate_scenario(
            scenario, panels, references, membership, baskets, v6, mats, opportunity, clusters, calendar
        )
        base_metrics = basket_metrics.loc[basket_metrics["variant"].eq("BASELINE_21"), ["basket", "cagr"]].rename(columns={"cagr": "baseline_cagr"})
        basket_metrics = basket_metrics.merge(base_metrics, on="basket", how="left", validate="many_to_one")
        basket_metrics["cagr_delta_vs_baseline"] = basket_metrics["cagr"] - basket_metrics["baseline_cagr"]
        baseline_summary = summary.loc[summary["variant"].eq("BASELINE_21")].iloc[0]
        summary["cagr_delta_vs_baseline_pp"] = 100.0 * (summary["cagr_mean"] - baseline_summary["cagr_mean"])
        summary["maxdd_delta_vs_baseline_pp"] = 100.0 * (summary["maxdd_mean"] - baseline_summary["maxdd_mean"])
        summary["sharpe_delta_vs_baseline"] = summary["sharpe_mean"] - baseline_summary["sharpe_mean"]
        improved = basket_metrics.groupby("variant")["cagr_delta_vs_baseline"].apply(lambda values: float(values.gt(0.0).mean()))
        summary["fraction_baskets_beating_baseline"] = summary["variant"].map(improved)
        summary["elapsed_seconds"] = float(time.time() - scenario_started)
        summary.to_csv(summary_path, index=False)
        basket_metrics.to_csv(basket_path, index=False)
        if audits:
            audit = pd.concat(audits, ignore_index=True)
            audit.to_csv(audit_path, index=False)
            completed_audits.append(audit)
        (scenario_dir / "SCENARIO_SPEC.json").write_text(json.dumps(asdict(scenario), indent=2) + "\n", encoding="utf-8")
        completed_summaries.append(summary)
        completed_baskets.append(basket_metrics)
        print(f"completed {scenario.name} in {time.time() - scenario_started:.1f}s", flush=True)

    all_summary = pd.concat(completed_summaries, ignore_index=True)
    all_baskets = pd.concat(completed_baskets, ignore_index=True)
    all_summary.to_csv(args.output_dir / "ROBUSTNESS_SCENARIO_SCORECARD.csv", index=False)
    all_baskets.to_csv(args.output_dir / "ROBUSTNESS_BASKET_METRICS.csv.gz", index=False)
    if completed_audits:
        pd.concat(completed_audits, ignore_index=True).to_csv(args.output_dir / "ROBUSTNESS_FIT_AUDIT.csv", index=False)

    candidates = all_summary.loc[all_summary["variant"].ne("BASELINE_21")].copy()
    aggregate = candidates.groupby("variant").agg(
        scenarios=("scenario", "nunique"),
        mean_cagr=("cagr_mean", "mean"),
        worst_cagr=("cagr_mean", "min"),
        mean_cagr_delta_vs_baseline_pp=("cagr_delta_vs_baseline_pp", "mean"),
        worst_cagr_delta_vs_baseline_pp=("cagr_delta_vs_baseline_pp", "min"),
        scenarios_beating_baseline=("cagr_delta_vs_baseline_pp", lambda x: int((x > 0).sum())),
        mean_maxdd=("maxdd_mean", "mean"),
        worst_maxdd=("maxdd_mean", "min"),
        mean_sharpe=("sharpe_mean", "mean"),
        worst_sharpe=("sharpe_mean", "min"),
        mean_score_correlation=("monthly_score_rank_correlation", "mean"),
        worst_score_correlation=("monthly_score_rank_correlation", "min"),
        mean_basket_top1_agreement=("basket_top1_agreement", "mean"),
        worst_basket_top1_agreement=("basket_top1_agreement", "min"),
        mean_fraction_baskets_beating_baseline=("fraction_baskets_beating_baseline", "mean"),
    ).reset_index()
    aggregate["scenario_win_rate_vs_baseline"] = aggregate["scenarios_beating_baseline"] / aggregate["scenarios"]
    aggregate.to_csv(args.output_dir / "ROBUSTNESS_AGGREGATE.csv", index=False)

    control = all_summary.loc[all_summary["scenario"].eq("CONTROL_ANNUAL_EXPANDING")]
    parity = []
    for variant in VARIANTS:
        row = control.loc[control["variant"].eq(variant)]
        if row.empty:
            continue
        parity.append(
            {
                "variant": variant,
                "monthly_score_rank_correlation": float(row.iloc[0]["monthly_score_rank_correlation"]),
                "basket_top1_agreement": float(row.iloc[0]["basket_top1_agreement"]),
                "cagr_mean": float(row.iloc[0]["cagr_mean"]),
            }
        )
    report = {
        "status": "COMPLETED",
        "elapsed_seconds": float(time.time() - started),
        "scenario_count": int(all_summary["scenario"].nunique()),
        "variants": list(VARIANTS),
        "fixed": [
            "target weights", "feature list", "XGBRanker hyperparameters", "three model seeds",
            "TailMix", "macro layer", "70/30 blend", "official 500 baskets", "governor",
            "costs", "allocation rule", "unperturbed labels", "daily evaluation OHLC", "final date 2026-07-01",
        ],
        "stress_families": sorted(all_summary["family"].unique()),
        "control_parity": parity,
        "aggregate": aggregate.to_dict(orient="records"),
        "caveat": "Price-vintage stress is simulated as deterministic feature noise with labels and evaluation OHLC frozen; it is not a second vendor snapshot.",
    }
    (args.output_dir / "ROBUSTNESS_REPORT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
