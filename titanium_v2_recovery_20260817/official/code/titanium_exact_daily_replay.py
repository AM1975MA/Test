#!/usr/bin/env python3
"""Rebuild frozen Titanium daily paths from authenticated score state and prices."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit, prange


@njit(parallel=True, cache=True)
def simulate(
    params: np.ndarray,
    daily_top1: np.ndarray,
    daily_top2: np.ndarray,
    daily_margin: np.ndarray,
    open_values: np.ndarray,
    low_values: np.ndarray,
    close_values: np.ndarray,
    previous_close: np.ndarray,
    gaps: np.ndarray,
    universe_down_1pct: np.ndarray,
    universe_negative: np.ndarray,
    hazard: np.ndarray,
    severe: np.ndarray,
    bil_index: int,
    shv_index: int,
    cost: float = 0.001,
    slippage: float = 0.001,
) -> np.ndarray:
    n_policies = params.shape[0]
    baskets, days = daily_top1.shape
    equity = np.ones((n_policies, baskets, days))
    for policy in prange(n_policies):
        threshold = params[policy, 0]
        low_confidence_top1_weight = params[policy, 1]
        for basket in range(baskets):
            ticker1 = -1
            ticker2 = -1
            units1 = 0.0
            units2 = 0.0
            bil_units = 0.0
            shv_units = 0.0
            cash = 0.0
            previous_weight1 = -1.0
            previous_fraction = -1.0
            cooldown = 0
            for day in range(days):
                value = cash
                if ticker1 >= 0 and units1 != 0.0:
                    value += units1 * open_values[day, ticker1]
                if ticker2 >= 0 and units2 != 0.0:
                    value += units2 * open_values[day, ticker2]
                if bil_units != 0.0:
                    value += bil_units * open_values[day, bil_index]
                if shv_units != 0.0:
                    value += shv_units * open_values[day, shv_index]
                if day == 0 and value == 0.0:
                    value = 1.0
                if day == days - 1:
                    equity[policy, basket, day] = value
                    break

                new_ticker1 = daily_top1[basket, day]
                new_ticker2 = daily_top2[basket, day]
                weight1 = (
                    1.0
                    if threshold < 0.0 or daily_margin[basket, day] >= threshold
                    else low_confidence_top1_weight
                )
                if new_ticker2 == new_ticker1:
                    weight1 = 1.0

                prior_hazard1 = False
                prior_hazard2 = False
                systemic = False
                risky_fraction = 1.0
                if new_ticker1 < 0:
                    risky_fraction = 0.0
                else:
                    prior_hazard1 = hazard[day, new_ticker1] or severe[day, new_ticker1]
                    prior_hazard2 = hazard[day, new_ticker2] or severe[day, new_ticker2]
                    portfolio_gap = (
                        weight1 * gaps[day, new_ticker1]
                        + (1.0 - weight1) * gaps[day, new_ticker2]
                    )
                    systemic = (
                        (portfolio_gap <= -0.032 and universe_down_1pct[day] >= 0.70)
                        or (portfolio_gap <= -0.044 and universe_negative[day] >= 0.75)
                    )
                    if systemic:
                        risky_fraction = 0.25
                        cooldown = 3
                    elif cooldown > 0:
                        risky_fraction = 0.25
                        cooldown -= 1

                risky_weight1 = risky_fraction * weight1
                risky_weight2 = risky_fraction * (1.0 - weight1)
                defensive_weight = 1.0 - risky_fraction
                rebalance = (
                    ticker1 != new_ticker1
                    or ticker2 != new_ticker2
                    or abs(previous_weight1 - weight1) > 1e-12
                    or abs(previous_fraction - risky_fraction) > 1e-12
                    or cash > 1e-14
                    or day == 0
                )
                if rebalance:
                    current1 = (
                        units1 * open_values[day, ticker1] / value
                        if ticker1 >= 0 and units1 != 0.0
                        else 0.0
                    )
                    current2 = (
                        units2 * open_values[day, ticker2] / value
                        if ticker2 >= 0 and units2 != 0.0
                        else 0.0
                    )
                    current_bil = bil_units * open_values[day, bil_index] / value if bil_units != 0.0 else 0.0
                    current_shv = shv_units * open_values[day, shv_index] / value if shv_units != 0.0 else 0.0
                    current_cash = cash / value if value > 0.0 else 0.0
                    tv = 0.5 * (
                        abs(current_cash)
                        + abs(current_bil - defensive_weight * 0.5)
                        + abs(current_shv - defensive_weight * 0.5)
                    )
                    if ticker1 != new_ticker1:
                        tv += 0.5 * (abs(current1) + risky_weight1)
                    else:
                        tv += 0.5 * abs(current1 - risky_weight1)
                    if ticker2 != new_ticker2:
                        tv += 0.5 * (abs(current2) + risky_weight2)
                    else:
                        tv += 0.5 * abs(current2 - risky_weight2)
                    value *= 1.0 - cost * tv
                    ticker1 = new_ticker1
                    ticker2 = new_ticker2
                    units1 = (
                        risky_weight1 * value / open_values[day, ticker1]
                        if ticker1 >= 0 and risky_weight1 > 0.0
                        else 0.0
                    )
                    units2 = (
                        risky_weight2 * value / open_values[day, ticker2]
                        if ticker2 >= 0 and risky_weight2 > 0.0
                        else 0.0
                    )
                    bil_units = defensive_weight * 0.5 * value / open_values[day, bil_index]
                    shv_units = defensive_weight * 0.5 * value / open_values[day, shv_index]
                    cash = 0.0
                    previous_weight1 = weight1
                    previous_fraction = risky_fraction

                if ticker1 >= 0 and units1 > 0.0 and prior_hazard1 and (systemic or universe_down_1pct[day] >= 0.55):
                    stop_price = previous_close[day, ticker1] * (1.0 - 0.055)
                    fill = (
                        open_values[day, ticker1]
                        if open_values[day, ticker1] <= stop_price
                        else stop_price * (1.0 - slippage)
                        if low_values[day, ticker1] <= stop_price
                        else 0.0
                    )
                    if fill > 0.0:
                        cash += units1 * fill * (1.0 - cost)
                        units1 = 0.0
                        cooldown = max(cooldown, 3)
                if ticker2 >= 0 and units2 > 0.0 and prior_hazard2 and (systemic or universe_down_1pct[day] >= 0.55):
                    stop_price = previous_close[day, ticker2] * (1.0 - 0.055)
                    fill = (
                        open_values[day, ticker2]
                        if open_values[day, ticker2] <= stop_price
                        else stop_price * (1.0 - slippage)
                        if low_values[day, ticker2] <= stop_price
                        else 0.0
                    )
                    if fill > 0.0:
                        cash += units2 * fill * (1.0 - cost)
                        units2 = 0.0
                        cooldown = max(cooldown, 3)

                next_value = cash
                if ticker1 >= 0 and units1 != 0.0:
                    next_value += units1 * open_values[day + 1, ticker1]
                if ticker2 >= 0 and units2 != 0.0:
                    next_value += units2 * open_values[day + 1, ticker2]
                if bil_units != 0.0:
                    next_value += bil_units * open_values[day + 1, bil_index]
                if shv_units != 0.0:
                    next_value += shv_units * open_values[day + 1, shv_index]
                equity[policy, basket, day] = next_value
    return equity


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--reg-paths", type=Path, required=True)
    parser.add_argument("--daily", type=Path)
    parser.add_argument("--open", dest="open_path", type=Path)
    parser.add_argument("--low", type=Path)
    parser.add_argument("--close", type=Path)
    parser.add_argument("--frozen-paths", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    panel = pd.read_pickle(args.panel)
    panel["signal_date"] = pd.to_datetime(panel["signal_date"])
    membership = pd.read_csv(args.membership)
    reg = np.load(args.reg_paths)
    dates = pd.DatetimeIndex(reg["dates"])
    top1 = reg["BASE_SELECTED"].astype(np.int16)

    if args.daily is not None:
        daily = pd.read_parquet(args.daily)
        daily["date"] = pd.to_datetime(daily["date"], errors="raise")
        daily["ticker"] = daily["ticker"].astype(str).str.upper().str.strip()

        def pivot(column: str) -> pd.DataFrame:
            return daily.pivot(index="date", columns="ticker", values=column).sort_index().sort_index(axis=1)

        open_prices = pivot("adj_open_calc").reindex(dates).ffill().bfill()
        low_prices = pivot("adj_low_calc").reindex(dates).ffill().bfill()
        close_prices = pivot("adj_close_calc").reindex(dates).ffill().bfill()
    else:
        if args.open_path is None or args.low is None or args.close is None:
            parser.error("Provide --daily or all of --open, --low, and --close")
        open_prices = pd.read_parquet(args.open_path).reindex(dates).ffill().bfill()
        low_prices = pd.read_parquet(args.low).reindex(dates).ffill().bfill()
        close_prices = pd.read_parquet(args.close).reindex(dates).ffill().bfill()
    tickers = list(open_prices.columns)
    ticker_to_index = {ticker: index for index, ticker in enumerate(tickers)}
    low_prices = low_prices[tickers]
    close_prices = close_prices[tickers]

    calendar = (
        panel[["signal_date", "entry_date", "exit_date"]]
        .drop_duplicates()
        .sort_values("signal_date")
        .query("signal_date >= '2017-01-01'")
        .reset_index(drop=True)
    )
    entry_indices = np.array([dates.get_loc(pd.Timestamp(date)) for date in calendar["entry_date"]])
    exit_indices = np.array([dates.get_loc(pd.Timestamp(date)) for date in calendar["exit_date"]])
    score_matrix = (
        panel.pivot(index="signal_date", columns="ticker", values="TIT_R")
        .reindex(index=calendar["signal_date"], columns=tickers)
        .to_numpy(float)
    )
    member_indices = np.array(
        [
            [ticker_to_index[ticker] for ticker in membership.loc[membership["basket"].eq(basket), "ticker"]]
            for basket in range(500)
        ],
        dtype=np.int16,
    )
    top2 = np.zeros_like(top1)
    margin = np.zeros(top1.shape, dtype=float)
    for month in range(len(calendar)):
        for basket in range(500):
            selected = top1[basket, month]
            members = member_indices[basket]
            scores = np.where(np.isfinite(score_matrix[month, members]), score_matrix[month, members], -np.inf)
            order = members[np.argsort(scores)[::-1]]
            alternatives = order[order != selected]
            second = alternatives[0] if len(alternatives) else selected
            top2[basket, month] = second
            margin[basket, month] = np.nan_to_num(score_matrix[month, selected], nan=-1.0) - np.nan_to_num(
                score_matrix[month, second], nan=-1.0
            )

    baskets, days = top1.shape[0], len(dates)
    daily_top1 = np.full((baskets, days), -1, dtype=np.int16)
    daily_top2 = np.full((baskets, days), -1, dtype=np.int16)
    daily_margin = np.ones((baskets, days), dtype=float)
    for month, (entry, exit_) in enumerate(zip(entry_indices, exit_indices)):
        daily_top1[:, entry:exit_] = top1[:, month, None]
        daily_top2[:, entry:exit_] = top2[:, month, None]
        daily_margin[:, entry:exit_] = margin[:, month, None]

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

    params = np.array([[-9.0, 1.0], [0.12, 0.75]], dtype=float)
    rebuilt = simulate(
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
    )
    frozen = np.load(args.frozen_paths)
    comparisons = {}
    for label, candidate, reference in (
        ("BASE", rebuilt[0], frozen["BASE"]),
        ("BALANCED", rebuilt[1], frozen["BALANCED"]),
    ):
        absolute = np.abs(candidate - reference)
        relative = absolute / np.maximum(np.abs(reference), 1e-12)
        before_cutoff = dates < pd.Timestamp("2026-02-01")
        comparisons[label] = {
            "max_abs_error": float(absolute.max()),
            "max_rel_error": float(relative.max()),
            "pre_2026_02_max_abs_error": float(absolute[:, before_cutoff].max()),
            "pre_2026_02_max_rel_error": float(relative[:, before_cutoff].max()),
            "final_mean_rebuilt": float(candidate[:, -1].mean()),
            "final_mean_frozen": float(reference[:, -1].mean()),
        }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output_dir / "TITANIUM_EXACT_DAILY_REPLAY.npz",
        dates=dates.values,
        BASE=rebuilt[0],
        BALANCED=rebuilt[1],
        BASE_SELECTED=top1,
        SECOND_SELECTED=top2,
        SCORE_MARGIN=margin,
        tickers=np.asarray(tickers),
    )
    (args.output_dir / "TITANIUM_EXACT_DAILY_PARITY.json").write_text(
        json.dumps(comparisons, indent=2), encoding="utf-8"
    )
    print(json.dumps(comparisons, indent=2))


if __name__ == "__main__":
    main()
