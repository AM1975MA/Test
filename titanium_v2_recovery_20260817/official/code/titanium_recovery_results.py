#!/usr/bin/env python3
"""Produce recovered Titanium V2 500-basket distribution and unrestricted-universe test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from titanium_exact_daily_replay import simulate


def path_metrics(equity: np.ndarray, mask: np.ndarray) -> pd.DataFrame:
    returns = np.zeros_like(equity)
    returns[:, 1:] = equity[:, 1:] / equity[:, :-1] - 1.0
    selected = returns[:, mask]
    compounded = np.cumprod(1.0 + selected, axis=1)
    cagr = compounded[:, -1] ** (252.0 / selected.shape[1]) - 1.0
    drawdown = compounded / np.maximum.accumulate(compounded, axis=1) - 1.0
    maxdd = drawdown.min(axis=1)
    std = selected.std(axis=1, ddof=1)
    sharpe = np.sqrt(252.0) * selected.mean(axis=1) / np.where(std > 0.0, std, np.nan)
    calmar = cagr / np.maximum(-maxdd, 1e-12)
    return pd.DataFrame({"cagr": cagr, "maxdd": maxdd, "sharpe": sharpe, "calmar": calmar})


def period_masks(dates: pd.DatetimeIndex) -> dict[str, np.ndarray]:
    return {
        "D1_2017_2019": np.asarray(dates < pd.Timestamp("2020-01-01")),
        "D2_2020_2022": np.asarray((dates >= pd.Timestamp("2020-01-01")) & (dates < pd.Timestamp("2023-01-01"))),
        "DEV_2017_2022": np.asarray(dates < pd.Timestamp("2023-01-01")),
        "HOLD_2023_2026": np.asarray(dates >= pd.Timestamp("2023-01-01")),
        "FULL_2017_2026": np.ones(len(dates), dtype=bool),
    }


def summarize_distribution(per_basket: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (strategy, period), group in per_basket.groupby(["strategy", "period"], sort=False):
        row: dict[str, object] = {
            "strategy": strategy,
            "period": period,
            "baskets": int(group["basket"].nunique()),
        }
        for metric in ("cagr", "maxdd", "sharpe", "calmar"):
            values = group[metric].to_numpy(float)
            row.update(
                {
                    f"{metric}_mean": float(np.mean(values)),
                    f"{metric}_std": float(np.std(values, ddof=1)),
                    f"{metric}_min": float(np.min(values)),
                    f"{metric}_p05": float(np.quantile(values, 0.05)),
                    f"{metric}_p10": float(np.quantile(values, 0.10)),
                    f"{metric}_p25": float(np.quantile(values, 0.25)),
                    f"{metric}_median": float(np.quantile(values, 0.50)),
                    f"{metric}_p75": float(np.quantile(values, 0.75)),
                    f"{metric}_p90": float(np.quantile(values, 0.90)),
                    f"{metric}_p95": float(np.quantile(values, 0.95)),
                    f"{metric}_max": float(np.max(values)),
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def build_market_arrays(daily_path: Path, dates: pd.DatetimeIndex) -> tuple[list[str], tuple[np.ndarray, ...]]:
    daily = pd.read_parquet(daily_path)
    daily["date"] = pd.to_datetime(daily["date"], errors="raise")
    daily["ticker"] = daily["ticker"].astype(str).str.upper().str.strip()

    def pivot(column: str) -> pd.DataFrame:
        return (
            daily.pivot(index="date", columns="ticker", values=column)
            .sort_index()
            .sort_index(axis=1)
            .reindex(dates)
            .ffill()
            .bfill()
        )

    open_prices = pivot("adj_open_calc")
    low_prices = pivot("adj_low_calc")
    close_prices = pivot("adj_close_calc")
    tickers = list(open_prices.columns)
    open_values = open_prices.to_numpy(float)
    low_values = low_prices.to_numpy(float)
    close_values = close_prices.to_numpy(float)
    gaps = np.zeros_like(open_values)
    gaps[1:] = open_values[1:] / close_values[:-1] - 1.0
    universe_down_1pct = np.mean(gaps < -0.01, axis=1)
    universe_negative = np.mean(gaps < 0.0, axis=1)
    momentum3 = close_prices / close_prices.shift(3) - 1.0
    momentum5 = close_prices / close_prices.shift(5) - 1.0
    sma10 = close_prices.rolling(10).mean()
    sma20 = close_prices.rolling(20).mean()
    hazard = (
        ((close_prices < sma10) & (momentum3 < 0.0))
        | ((close_prices < sma20) & (momentum5 < -0.015))
    ).shift(1).fillna(False).to_numpy(bool)
    severe = ((momentum5 < -0.04) | ((close_prices < sma20) & (momentum3 < -0.025))).shift(1).fillna(False).to_numpy(bool)
    previous_close = np.empty_like(close_values)
    previous_close[0] = open_values[0]
    previous_close[1:] = close_values[:-1]
    return tickers, (
        open_values,
        low_values,
        close_values,
        previous_close,
        gaps,
        universe_down_1pct,
        universe_negative,
        hazard,
        severe,
    )


def unrestricted_paths(
    panel: pd.DataFrame, daily_path: Path, dates: pd.DatetimeIndex
) -> tuple[np.ndarray, pd.DataFrame, list[str]]:
    tickers, arrays = build_market_arrays(daily_path, dates)
    ticker_to_index = {ticker: index for index, ticker in enumerate(tickers)}
    calendar = (
        panel[["signal_date", "entry_date", "exit_date"]]
        .drop_duplicates()
        .sort_values("signal_date")
        .query("signal_date >= '2017-01-01'")
        .reset_index(drop=True)
    )
    scores = (
        panel.pivot(index="signal_date", columns="ticker", values="TIT_R")
        .reindex(index=calendar["signal_date"], columns=tickers)
        .to_numpy(float)
    )
    top1 = np.zeros(len(calendar), dtype=np.int16)
    top2 = np.zeros(len(calendar), dtype=np.int16)
    margin = np.zeros(len(calendar), dtype=float)
    rows: list[dict[str, object]] = []
    for month, score_row in enumerate(scores):
        order = np.argsort(np.where(np.isfinite(score_row), score_row, -np.inf))[::-1]
        first, second = int(order[0]), int(order[1])
        top1[month] = first
        top2[month] = second
        margin[month] = float(score_row[first] - score_row[second])
        rows.append(
            {
                "signal_date": calendar.loc[month, "signal_date"],
                "entry_date": calendar.loc[month, "entry_date"],
                "exit_date": calendar.loc[month, "exit_date"],
                "top1": tickers[first],
                "top2": tickers[second],
                "margin": margin[month],
                "top1_weight_v2": 1.0 if margin[month] >= 0.12 else 0.75,
                "top2_weight_v2": 0.0 if margin[month] >= 0.12 else 0.25,
            }
        )

    daily_top1 = np.full((1, len(dates)), -1, dtype=np.int16)
    daily_top2 = np.full((1, len(dates)), -1, dtype=np.int16)
    daily_margin = np.ones((1, len(dates)), dtype=float)
    for month, row in calendar.iterrows():
        entry = dates.get_loc(pd.Timestamp(row["entry_date"]))
        exit_ = dates.get_loc(pd.Timestamp(row["exit_date"]))
        daily_top1[:, entry:exit_] = top1[month]
        daily_top2[:, entry:exit_] = top2[month]
        daily_margin[:, entry:exit_] = margin[month]

    (
        open_values,
        low_values,
        close_values,
        previous_close,
        gaps,
        universe_down_1pct,
        universe_negative,
        hazard,
        severe,
    ) = arrays
    params = np.array([[-9.0, 1.0], [0.12, 0.75]], dtype=float)
    equity = simulate(
        params,
        daily_top1,
        daily_top2,
        daily_margin,
        open_values,
        low_values,
        close_values,
        previous_close,
        gaps,
        universe_down_1pct,
        universe_negative,
        hazard,
        severe,
        ticker_to_index["BIL"],
        ticker_to_index["SHV"],
    )[:, 0, :]
    return equity, pd.DataFrame(rows), tickers


def save_histogram(per_basket: pd.DataFrame, output_path: Path) -> None:
    import matplotlib.pyplot as plt

    full = per_basket[per_basket["period"].eq("FULL_2017_2026")]
    fig, ax = plt.subplots(figsize=(10, 6))
    for strategy, color in (("Titanium_V1", "#7f8c8d"), ("Titanium_V2", "#1f77b4")):
        values = 100.0 * full.loc[full["strategy"].eq(strategy), "cagr"].to_numpy(float)
        ax.hist(values, bins=24, alpha=0.48, label=strategy, color=color, edgecolor="white")
        ax.axvline(values.mean(), color=color, linewidth=2)
    ax.set_title("Meteor Titanium — distribuzione CAGR sui 500 panieri")
    ax.set_xlabel("CAGR annuo (%) · 1 feb 2017–1 lug 2026")
    ax.set_ylabel("Numero di panieri")
    ax.grid(axis="y", alpha=0.2)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def selection_parity(
    panel: pd.DataFrame, membership_path: Path, reg_paths: Path, output_dir: Path
) -> dict[str, object]:
    membership = pd.read_csv(membership_path)
    official = np.load(reg_paths)["BASE_SELECTED"].astype(np.int16)
    dates = np.sort(panel["signal_date"].unique())
    expanded = (
        membership.merge(panel[["signal_date", "ticker", "TIT_R"]], on="ticker", how="inner")
        .sort_values(
            ["signal_date", "basket", "TIT_R", "ticker"],
            ascending=[True, True, False, True],
            kind="mergesort",
        )
    )
    recovered_top1 = (
        expanded.drop_duplicates(["signal_date", "basket"])
        .pivot(index="basket", columns="signal_date", values="ticker")
        .reindex(index=range(500), columns=dates)
    )
    pairs = pd.DataFrame(
        {"ticker_index": official.ravel(), "recovered_ticker": recovered_top1.to_numpy().ravel()}
    ).dropna()
    counts = (
        pairs.groupby(["ticker_index", "recovered_ticker"])
        .size()
        .rename("observations")
        .reset_index()
    )
    best = (
        counts.sort_values(["ticker_index", "observations"], ascending=[True, False])
        .drop_duplicates("ticker_index")
        .sort_values("ticker_index")
    )
    matches = pairs.merge(
        best[["ticker_index", "recovered_ticker"]],
        on=["ticker_index", "recovered_ticker"],
        how="inner",
    )
    best.to_csv(output_dir / "TITANIUM_AUTHENTIC_TICKER_INDEX_MAP_OBSERVED.csv", index=False)
    full_ticker_map = pd.DataFrame(
        {"ticker_index": np.arange(150, dtype=int), "ticker": sorted(panel["ticker"].unique().tolist() + ["PIN"])}
    )
    full_ticker_map.to_csv(output_dir / "TITANIUM_TICKER_INDEX_MAP_150.csv", index=False)
    result = {
        "official_selection_shape": [int(value) for value in official.shape],
        "decision_pairs": int(len(pairs)),
        "matched_pairs": int(len(matches)),
        "agreement": float(len(matches) / len(pairs)),
        "observed_selected_indices": int(pairs["ticker_index"].nunique()),
        "observed_selected_tickers": int(pairs["recovered_ticker"].nunique()),
        "ambiguous_index_mappings": int(counts.groupby("ticker_index").size().gt(1).sum()),
    }
    (output_dir / "TITANIUM_SELECTION_PARITY.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-paths", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--reg-paths", type=Path, required=True)
    parser.add_argument("--daily", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    frozen = np.load(args.frozen_paths)
    dates = pd.DatetimeIndex(frozen["dates"])
    masks = period_masks(dates)
    basket_rows: list[pd.DataFrame] = []
    for strategy, key in (("Titanium_V1", "BASE"), ("Titanium_V2", "BALANCED")):
        for period, mask in masks.items():
            frame = path_metrics(frozen[key], mask)
            frame.insert(0, "basket", np.arange(len(frame), dtype=int))
            frame.insert(0, "period", period)
            frame.insert(0, "strategy", strategy)
            basket_rows.append(frame)
    per_basket = pd.concat(basket_rows, ignore_index=True)
    distribution = summarize_distribution(per_basket)
    per_basket.to_csv(args.output_dir / "TITANIUM_500_BASKET_METRICS.csv", index=False)
    distribution.to_csv(args.output_dir / "TITANIUM_500_BASKET_DISTRIBUTION_SUMMARY.csv", index=False)
    save_histogram(per_basket, args.output_dir / "TITANIUM_500_BASKET_CAGR_DISTRIBUTION.png")

    panel = pd.read_pickle(args.panel)
    panel["signal_date"] = pd.to_datetime(panel["signal_date"], errors="raise")
    parity = selection_parity(panel, args.membership, args.reg_paths, args.output_dir)
    unrestricted, selections, tickers = unrestricted_paths(panel, args.daily, dates)
    selections.to_csv(args.output_dir / "TITANIUM_UNRESTRICTED_150_SELECTIONS.csv", index=False)
    np.savez_compressed(
        args.output_dir / "TITANIUM_UNRESTRICTED_150_PATHS.npz",
        dates=dates.values,
        Titanium_V1=unrestricted[0],
        Titanium_V2=unrestricted[1],
        tickers=np.asarray(tickers),
    )
    global_rows: list[dict[str, object]] = []
    for strategy, values in (("Titanium_V1", unrestricted[0]), ("Titanium_V2", unrestricted[1])):
        for period, mask in masks.items():
            metric = path_metrics(values[None, :], mask).iloc[0].to_dict()
            global_rows.append({"strategy": strategy, "period": period, **metric})
    global_scorecard = pd.DataFrame(global_rows)
    global_scorecard.to_csv(args.output_dir / "TITANIUM_UNRESTRICTED_150_SCORECARD.csv", index=False)

    fingerprint = {
        "frozen_path_start": str(dates.min().date()),
        "frozen_path_end": str(dates.max().date()),
        "daily_rows": int(len(dates)),
        "basket_count": 500,
        "score_panel_rows": int(len(panel)),
        "score_panel_dates": int(panel["signal_date"].nunique()),
        "score_panel_tickers": int(panel["ticker"].nunique()),
        "unrestricted_universe_price_columns": int(len(tickers)),
        "unrestricted_universe_scored_tickers": int(panel["ticker"].nunique()),
        "unrestricted_last_signal": str(selections["signal_date"].max().date()),
        "unrestricted_last_top1": str(selections.iloc[-1]["top1"]),
        "unrestricted_last_top2": str(selections.iloc[-1]["top2"]),
    }
    (args.output_dir / "TITANIUM_RECOVERY_RESULTS_FINGERPRINT.json").write_text(
        json.dumps(fingerprint, indent=2), encoding="utf-8"
    )
    print(distribution.loc[distribution["period"].eq("FULL_2017_2026")].to_string(index=False))
    print(global_scorecard.to_string(index=False))
    print(json.dumps(parity, indent=2))
    print(json.dumps(fingerprint, indent=2))


if __name__ == "__main__":
    main()
