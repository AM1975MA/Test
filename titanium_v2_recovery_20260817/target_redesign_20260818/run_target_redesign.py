#!/usr/bin/env python3
"""Compare Compact target redesigns with every other Titanium component fixed."""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRanker


SEEDS = (101, 202, 303)


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
    out["target_42"] = out["target_rank_42"]
    out["target_multi_45_35_20"] = (
        0.45 * out["target_rank_21"] + 0.35 * out["target_rank_42"] + 0.20 * out["target_rank_63"]
    )
    out["target_consensus"] = (
        0.35 * out["target_rank_21"]
        + 0.30 * out["target_rank_42"]
        + 0.20 * out["target_rank_63"]
        + 0.15 * ranks.min(axis=1)
    )
    multi_return = 0.45 * out["fwd_ret_21"] + 0.35 * out["fwd_ret_42"] + 0.20 * out["fwd_ret_63"]
    worst_loss = out[["fwd_ret_21", "fwd_ret_42", "fwd_ret_63"]].min(axis=1).clip(upper=0.0)
    out["utility_downside_raw"] = multi_return + 0.50 * worst_loss
    out["target_downside_utility"] = out.groupby("signal_date")["utility_downside_raw"].rank(pct=True)
    return out


def train_variant(
    name: str,
    target: str,
    exit_column: str,
    compact: pd.DataFrame,
    features: list[str],
    params: dict,
) -> tuple[str, pd.DataFrame, pd.DataFrame]:
    rows = []
    audits = []
    cvalid = compact[features].notna().sum(axis=1).ge(30)
    for year in range(2017, 2027):
        cutoff = pd.Timestamp(year, 1, 1)
        train = compact.loc[
            compact["signal_date"].lt(cutoff)
            & compact[exit_column].lt(cutoff)
            & compact[target].notna()
            & cvalid
        ].sort_values(["signal_date", "ticker"])
        test = compact.loc[compact["signal_date"].dt.year.eq(year) & cvalid].sort_values(["signal_date", "ticker"])
        if train["signal_date"].nunique() < 60 or test.empty:
            continue
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
        rows.append(frame)
        audits.append(
            {
                "variant": name,
                "year": year,
                "target": target,
                "label_exit_column": exit_column,
                "train_dates": int(train["signal_date"].nunique()),
                "train_rows": int(len(train)),
                "test_dates": int(test["signal_date"].nunique()),
                "test_rows": int(len(test)),
            }
        )
    prediction = pd.concat(rows, ignore_index=True)
    seed_rank_columns = []
    for seed in SEEDS:
        column = f"rank_seed_{seed}"
        prediction[column] = prediction.groupby("signal_date")[f"raw_seed_{seed}"].rank(pct=True)
        seed_rank_columns.append(column)
    prediction["compact_raw"] = prediction[[f"raw_seed_{seed}" for seed in SEEDS]].mean(axis=1)
    prediction["compact_rank"] = prediction.groupby("signal_date")["compact_raw"].rank(pct=True)
    return name, prediction, pd.DataFrame(audits)


def path_metrics(paths: np.ndarray, dates: pd.DatetimeIndex) -> pd.DataFrame:
    returns = np.zeros_like(paths, dtype=float)
    returns[:, 1:] = paths[:, 1:] / paths[:, :-1] - 1.0
    compounded = np.cumprod(1.0 + returns, axis=1)
    cagr = compounded[:, -1] ** (252.0 / returns.shape[1]) - 1.0
    drawdown = compounded / np.maximum.accumulate(compounded, axis=1) - 1.0
    std = returns.std(axis=1, ddof=1)
    sharpe = np.sqrt(252.0) * returns.mean(axis=1) / np.where(std > 0.0, std, np.nan)
    return pd.DataFrame({"cagr": cagr, "maxdd": drawdown.min(axis=1), "sharpe": sharpe})


def period_scorecard(paths: np.ndarray, dates: pd.DatetimeIndex, variant: str) -> pd.DataFrame:
    periods = {
        "D1_2017_2019": np.asarray(dates < pd.Timestamp("2020-01-01")),
        "D2_2020_2022": np.asarray((dates >= pd.Timestamp("2020-01-01")) & (dates < pd.Timestamp("2023-01-01"))),
        "HOLD_2023_2026": np.asarray(dates >= pd.Timestamp("2023-01-01")),
        "FULL_2017_2026": np.ones(len(dates), dtype=bool),
    }
    rows = []
    for period, mask in periods.items():
        metric = path_metrics(paths[:, mask], dates[mask])
        rows.append(
            {
                "variant": variant,
                "period": period,
                "baskets": int(len(metric)),
                "cagr_mean": float(metric["cagr"].mean()),
                "cagr_median": float(metric["cagr"].median()),
                "cagr_p10": float(metric["cagr"].quantile(0.10)),
                "cagr_p90": float(metric["cagr"].quantile(0.90)),
                "maxdd_mean": float(metric["maxdd"].mean()),
                "sharpe_mean": float(metric["sharpe"].mean()),
            }
        )
    return pd.DataFrame(rows)


def mean_turnover(selections: np.ndarray, weights: np.ndarray) -> float:
    values = []
    for basket in range(selections.shape[0]):
        previous: dict[int, float] = {}
        for month in range(selections.shape[1]):
            current = {
                int(ticker): float(weight)
                for ticker, weight in zip(selections[basket, month], weights[basket, month])
                if ticker >= 0 and weight > 0
            }
            names = set(previous) | set(current)
            values.append(0.5 * sum(abs(current.get(t, 0.0) - previous.get(t, 0.0)) for t in names))
            previous = current
    return float(np.mean(values))


def seed_stability(panel: pd.DataFrame, membership: pd.DataFrame) -> dict[str, float]:
    pairs = [(101, 202), (101, 303), (202, 303)]
    monthly_corr = []
    unrestricted = []
    expanded = panel.merge(membership, on="ticker", how="inner", validate="many_to_many")
    basket_hits = []
    for left, right in pairs:
        lc, rc = f"final_seed_{left}", f"final_seed_{right}"
        correlations = panel.groupby("signal_date").apply(
            lambda x: x[lc].corr(x[rc], method="spearman"), include_groups=False
        )
        monthly_corr.extend(correlations.tolist())
        lt = panel.sort_values(["signal_date", lc, "ticker"], ascending=[True, False, True], kind="mergesort").drop_duplicates("signal_date")
        rt = panel.sort_values(["signal_date", rc, "ticker"], ascending=[True, False, True], kind="mergesort").drop_duplicates("signal_date")
        unrestricted.extend(lt[["signal_date", "ticker"]].merge(rt[["signal_date", "ticker"]], on="signal_date", suffixes=("_l", "_r")).eval("ticker_l == ticker_r").tolist())
        lb = expanded.sort_values(["signal_date", "basket", lc, "ticker"], ascending=[True, True, False, True], kind="mergesort").drop_duplicates(["signal_date", "basket"])
        rb = expanded.sort_values(["signal_date", "basket", rc, "ticker"], ascending=[True, True, False, True], kind="mergesort").drop_duplicates(["signal_date", "basket"])
        joined = lb[["signal_date", "basket", "ticker"]].merge(rb[["signal_date", "basket", "ticker"]], on=["signal_date", "basket"], suffixes=("_l", "_r"))
        basket_hits.extend(joined["ticker_l"].eq(joined["ticker_r"]).tolist())
    return {
        "mean_pairwise_monthly_rank_correlation": float(np.mean(monthly_corr)),
        "pairwise_unrestricted_top1_agreement": float(np.mean(unrestricted)),
        "pairwise_basket_top1_agreement": float(np.mean(basket_hits)),
    }


def predictive_diagnostics(panel: pd.DataFrame, labels: pd.DataFrame) -> dict[str, float]:
    joined = panel[["signal_date", "ticker", "compact_rank"]].merge(
        labels[["signal_date", "ticker", "target_rank_21", "target_rank_42", "target_rank_63"]],
        on=["signal_date", "ticker"], how="inner", validate="one_to_one"
    )
    result = {}
    for horizon in (21, 42, 63):
        correlations = joined.groupby("signal_date").apply(
            lambda x: x["compact_rank"].corr(x[f"target_rank_{horizon}"], method="spearman"), include_groups=False
        )
        result[f"mean_monthly_rank_ic_{horizon}"] = float(correlations.mean())
        result[f"median_monthly_rank_ic_{horizon}"] = float(correlations.median())
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
    parser.add_argument("--frozen-paths", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--n-estimators", type=int, default=360)
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    base = load_module(args.base_module.resolve(), "target_base")
    v6 = load_module(args.v6_module.resolve(), "target_v6")
    base.rolling_downvol = lambda ret, h: ret.clip(upper=0.0).rolling(h, min_periods=h).std(ddof=0) * np.sqrt(252)
    mats = v6.load_mats(args.data_dir.resolve())
    dates, compact, _tail, _dictionary = base.build_features(mats)
    compact = add_targets(base.add_labels(compact, mats["Open"], dates))

    variants = {
        "BASELINE_21": ("target_21", "exit_date_21"),
        "TARGET_42": ("target_42", "exit_date_42"),
        "MULTI_45_35_20": ("target_multi_45_35_20", "exit_date_63"),
        "CONSENSUS_MULTI": ("target_consensus", "exit_date_63"),
        "DOWNSIDE_UTILITY": ("target_downside_utility", "exit_date_63"),
    }
    params = dict(base.COMPACT_PARAMS)
    params.update({"n_estimators": args.n_estimators, "n_jobs": 2})
    trained = {}
    audits = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(train_variant, name, target, exit_column, compact, list(base.F2D_FEATURES), params): name
            for name, (target, exit_column) in variants.items()
        }
        for future in as_completed(futures):
            name, prediction, audit = future.result()
            trained[name] = prediction
            audits.append(audit)
            print(f"trained {name}: {len(prediction)} rows", flush=True)

    fixed = pd.read_parquet(args.fixed_score_panel)
    opp = pd.read_csv(args.opportunity_panel)
    clusters = pd.read_csv(args.clusters)
    calendar = pd.read_csv(args.calendar)
    membership = pd.read_csv(args.membership)[["basket", "ticker"]]
    for frame in (fixed, opp, clusters, calendar, compact):
        frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="raise")
    for column in ("entry_date", "exit_date"):
        calendar[column] = pd.to_datetime(calendar[column], errors="raise")
    membership["ticker"] = membership["ticker"].astype(str).str.upper().str.strip()
    baskets = [g["ticker"].tolist() for _, g in membership.groupby("basket", sort=True)]
    calendar = calendar.loc[calendar["exit_date"].le(pd.Timestamp("2026-07-01"))].copy()

    scorecards = []
    diagnostics = []
    target_arrays = {}
    for name in variants:
        compact_pred = trained[name]
        panel = compact_pred.merge(
            fixed[["signal_date", "ticker", "tail_rank", "macro_category", "top_macro", "macro_gap_z", "macro_bonus"]],
            on=["signal_date", "ticker"], how="inner", validate="one_to_one"
        )
        panel["titanium_score_pre_macro"] = 0.70 * panel["compact_rank"] + 0.30 * panel["tail_rank"]
        panel["titanium_score"] = panel["titanium_score_pre_macro"] + panel["macro_bonus"]
        for seed in SEEDS:
            panel[f"final_seed_{seed}"] = 0.70 * panel[f"rank_seed_{seed}"] + 0.30 * panel["tail_rank"] + panel["macro_bonus"]

        idx, base_paths, _direct, _router, _active, _margin, _condition, base_sel, base_weights, *_ = v6.simulate_all(
            baskets, panel, opp, clusters, mats, calendar
        )
        scorecards.append(period_scorecard(base_paths, idx, name))
        stability = seed_stability(panel.loc[panel["signal_date"].isin(calendar["signal_date"])], membership)
        predictive = predictive_diagnostics(panel, compact)
        diagnostics.append(
            {
                "variant": name,
                **predictive,
                **stability,
                "mean_monthly_turnover": mean_turnover(base_sel, base_weights),
                "concentrated_100pct_rate": float(np.mean(base_weights[:, :, 0] >= 0.999999)),
            }
        )
        target_arrays[name] = {"paths": base_paths, "selections": base_sel, "weights": base_weights}
        panel.to_parquet(args.output_dir / f"{name}_SCORE_PANEL.parquet", index=False, compression="zstd")
        print(f"evaluated {name}", flush=True)

    scorecard = pd.concat(scorecards, ignore_index=True)
    diagnostic = pd.DataFrame(diagnostics)
    fit_audit = pd.concat(audits, ignore_index=True)
    scorecard.to_csv(args.output_dir / "TARGET_SCORECARD.csv", index=False)
    diagnostic.to_csv(args.output_dir / "TARGET_DIAGNOSTICS.csv", index=False)
    fit_audit.to_csv(args.output_dir / "TARGET_FIT_AUDIT.csv", index=False)

    full = scorecard.loc[scorecard["period"].eq("FULL_2017_2026")].set_index("variant")
    baseline = full.loc["BASELINE_21"]
    comparison = full.reset_index().copy()
    comparison["cagr_delta_vs_baseline_pp"] = 100.0 * (comparison["cagr_mean"] - baseline["cagr_mean"])
    comparison["maxdd_delta_vs_baseline_pp"] = 100.0 * (comparison["maxdd_mean"] - baseline["maxdd_mean"])
    comparison["sharpe_delta_vs_baseline"] = comparison["sharpe_mean"] - baseline["sharpe_mean"]
    comparison = comparison.merge(diagnostic, on="variant", validate="one_to_one")
    comparison.to_csv(args.output_dir / "TARGET_COMPARISON_FULL.csv", index=False)

    frozen = np.load(args.frozen_paths)
    frozen_dates = pd.DatetimeIndex(frozen["dates"])
    official = path_metrics(frozen["BALANCED"], frozen_dates)
    report = {
        "status": "COMPLETED",
        "experiment": "Compact target redesign with every other Titanium component fixed",
        "elapsed_seconds": float(time.time() - started),
        "evaluation": {
            "path_start": str(idx.min().date()),
            "path_end": str(idx.max().date()),
            "daily_observations": int(len(idx)),
            "official_baskets": int(len(baskets)),
            "signal_dates": int(len(calendar)),
        },
        "official_frozen_reference": {
            "cagr_mean": float(official["cagr"].mean()),
            "maxdd_mean": float(official["maxdd"].mean()),
            "sharpe_mean": float(official["sharpe"].mean()),
        },
        "variants": comparison.to_dict(orient="records"),
        "methodology": {
            "changed": "Compact training target only",
            "fixed": ["features", "XGBRanker parameters", "three seeds", "TailMix", "macro layer", "70/30 blend", "official baskets", "governor", "costs", "allocation rule"],
            "multi_horizon_label_maturity": "exit_date_63 strictly before annual cutoff",
            "baseline_label_maturity": "exit_date_21 strictly before annual cutoff",
        },
    }
    (args.output_dir / "TARGET_EXPERIMENT_REPORT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
