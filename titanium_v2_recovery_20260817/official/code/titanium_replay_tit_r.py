#!/usr/bin/env python3
"""Replay frozen Titanium V2 concentration directly from authenticated TIT_R."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


FROZEN_CAGR = {
    "D1": 0.15022713687299,
    "D2": 0.2264479079604543,
    "DEV": 0.1861726630584223,
    "HOLD": 0.2760542274772661,
    "FULL": 0.2165406437471759,
}


def turnover(current: dict[str, float], previous: dict[str, float]) -> float:
    names = set(current) | set(previous)
    current_cash = 1.0 - sum(current.values())
    previous_cash = 1.0 - sum(previous.values())
    return 0.5 * (
        sum(abs(current.get(name, 0.0) - previous.get(name, 0.0)) for name in names)
        + abs(current_cash - previous_cash)
    )


def metrics(group: pd.DataFrame) -> dict[str, float]:
    returns = group["net_return"].to_numpy(float)
    equity = np.cumprod(1.0 + returns)
    drawdown = equity / np.maximum.accumulate(equity) - 1.0
    std = returns.std(ddof=1) if len(returns) > 1 else np.nan
    return {
        "cagr": float(equity[-1] ** (12.0 / len(returns)) - 1.0),
        "maxdd": float(drawdown.min()),
        "sharpe": float(np.sqrt(12.0) * returns.mean() / std) if std > 0 else np.nan,
        "months": int(len(returns)),
    }


def replay(panel: pd.DataFrame, membership: pd.DataFrame, cost: float) -> pd.DataFrame:
    baskets = {
        int(basket): group["ticker"].astype(str).tolist()
        for basket, group in membership.groupby("basket", sort=True)
    }
    rows: list[dict[str, object]] = []
    for signal_date, date_frame in panel.groupby("signal_date", sort=True):
        indexed = date_frame.set_index("ticker")
        for basket, members in baskets.items():
            available = indexed.reindex(members).dropna(subset=["TIT_R", "fwd_ret_21"])
            if len(available) < 2:
                continue
            order = available["TIT_R"].sort_values(ascending=False, kind="mergesort").index
            top1, top2 = str(order[0]), str(order[1])
            margin = float(available.loc[top1, "TIT_R"] - available.loc[top2, "TIT_R"])
            weights = {top1: 1.0} if margin >= 0.12 else {top1: 0.75, top2: 0.25}
            gross = sum(
                weight * float(available.loc[ticker, "fwd_ret_21"])
                for ticker, weight in weights.items()
            )
            rows.append(
                {
                    "signal_date": signal_date,
                    "basket": basket,
                    "top1": top1,
                    "top2": top2,
                    "margin": margin,
                    "weights": json.dumps(weights, sort_keys=True),
                    "gross_return": gross,
                }
            )
    result = pd.DataFrame(rows).sort_values(["basket", "signal_date"]).reset_index(drop=True)
    previous: dict[int, dict[str, float]] = {}
    turnover_values: list[float] = []
    for row in result.itertuples(index=False):
        current = json.loads(row.weights)
        turnover_values.append(turnover(current, previous.get(int(row.basket), {})))
        previous[int(row.basket)] = current
    result["turnover"] = turnover_values
    result["net_return"] = result["gross_return"] - cost * result["turnover"]
    return result


def scorecard(replay_frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    years = replay_frame["signal_date"].dt.year
    periods = {
        "D1": years.between(2020, 2021),
        "D2": years.eq(2022),
        "DEV": years.between(2020, 2022),
        "HOLD": years.ge(2023),
        "FULL": years.ge(2020),
        "ALL_2017": years.ge(2017),
    }
    basket_rows: list[dict[str, object]] = []
    score_rows: list[dict[str, object]] = []
    for period, mask in periods.items():
        current_rows: list[dict[str, object]] = []
        for basket, group in replay_frame.loc[mask].groupby("basket", sort=True):
            row = {"period": period, "basket": int(basket), **metrics(group)}
            basket_rows.append(row)
            current_rows.append(row)
        frame = pd.DataFrame(current_rows)
        mean_cagr = float(frame["cagr"].mean())
        frozen = FROZEN_CAGR.get(period)
        score_rows.append(
            {
                "period": period,
                "mean_cagr": mean_cagr,
                "frozen_cagr": frozen,
                "gap_pp": None if frozen is None else 100.0 * (mean_cagr - frozen),
                "mean_maxdd": float(frame["maxdd"].mean()),
                "mean_sharpe": float(frame["sharpe"].mean()),
                "mean_months": float(frame["months"].mean()),
                "baskets": int(frame["basket"].nunique()),
            }
        )
    return pd.DataFrame(score_rows), pd.DataFrame(basket_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cost-bps", type=float, default=10.0)
    args = parser.parse_args()

    panel = pd.read_pickle(args.panel)
    membership = pd.read_csv(args.membership)
    panel["signal_date"] = pd.to_datetime(panel["signal_date"], errors="raise")
    panel["ticker"] = panel["ticker"].astype(str).str.upper().str.strip()
    membership["ticker"] = membership["ticker"].astype(str).str.upper().str.strip()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    replay_frame = replay(panel, membership, args.cost_bps / 10_000.0)
    score, baskets = scorecard(replay_frame)
    replay_frame.to_csv(args.output_dir / "TIT_R_V2_MONTHLY_REPLAY.csv.gz", index=False)
    score.to_csv(args.output_dir / "TIT_R_V2_SCORECARD.csv", index=False)
    baskets.to_csv(args.output_dir / "TIT_R_V2_PER_BASKET.csv", index=False)
    fingerprint = {
        "panel_rows": int(len(panel)),
        "panel_dates": int(panel["signal_date"].nunique()),
        "panel_tickers": int(panel["ticker"].nunique()),
        "membership_rows": int(len(membership)),
        "membership_baskets": int(membership["basket"].nunique()),
        "membership_tickers": int(membership["ticker"].nunique()),
        "replay_rows": int(len(replay_frame)),
        "last_signal_date": str(replay_frame["signal_date"].max().date()),
        "full_pct_100_top1": float((replay_frame.loc[replay_frame["signal_date"].dt.year >= 2020, "margin"] >= 0.12).mean()),
    }
    (args.output_dir / "TIT_R_V2_FINGERPRINT.json").write_text(
        json.dumps(fingerprint, indent=2), encoding="utf-8"
    )
    print(score.to_string(index=False))
    print(json.dumps(fingerprint, indent=2))


if __name__ == "__main__":
    main()
