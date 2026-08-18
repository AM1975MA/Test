#!/usr/bin/env python3
"""Reproduce the core score, selection, basket and performance parity checks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def top_two(frame: pd.DataFrame, score: str, prefix: str) -> pd.DataFrame:
    ordered = frame.sort_values(
        ["signal_date", score, "ticker"], ascending=[True, False, True]
    ).copy()
    ordered["rank_number"] = ordered.groupby("signal_date").cumcount() + 1
    result = ordered[ordered.rank_number <= 2].pivot(
        index="signal_date", columns="rank_number", values="ticker"
    )
    return result.rename(columns={1: f"{prefix}1", 2: f"{prefix}2"})


def basket_top_two(expanded: pd.DataFrame, score: str, prefix: str) -> pd.DataFrame:
    ordered = expanded.sort_values(
        ["signal_date", "basket", score, "ticker"],
        ascending=[True, True, False, True],
    ).copy()
    ordered["rank_number"] = ordered.groupby(["signal_date", "basket"]).cumcount() + 1
    result = ordered[ordered.rank_number <= 2].pivot(
        index=["signal_date", "basket"],
        columns="rank_number",
        values=["ticker", score],
    )
    result.columns = [
        f"{prefix}{'ticker' if field == 'ticker' else 'score'}{rank_number}"
        for field, rank_number in result.columns
    ]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authentic-panel", required=True, type=Path)
    parser.add_argument("--live-panel", required=True, type=Path)
    parser.add_argument("--official-membership", required=True, type=Path)
    parser.add_argument("--live-membership", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    authentic = pd.read_pickle(args.authentic_panel)[["signal_date", "ticker", "TIT_R"]]
    live = pd.read_parquet(args.live_panel)[["signal_date", "ticker", "titanium_score"]]
    official_membership = pd.read_csv(args.official_membership)[["basket", "ticker"]]
    live_membership = pd.read_csv(args.live_membership)[["basket", "ticker"]]

    common_dates = sorted(set(authentic.signal_date) & set(live.signal_date))
    authentic = authentic[authentic.signal_date.isin(common_dates)]
    live = live[live.signal_date.isin(common_dates)]
    joined = authentic.merge(live, on=["signal_date", "ticker"], how="inner")

    correlations = joined.groupby("signal_date").apply(
        lambda frame: frame.TIT_R.corr(frame.titanium_score), include_groups=False
    )
    unrestricted = top_two(joined, "TIT_R", "authentic_").join(
        top_two(joined, "titanium_score", "live_")
    )

    expanded = joined.merge(official_membership, on="ticker", how="inner")
    basket = basket_top_two(expanded, "TIT_R", "authentic_").join(
        basket_top_two(expanded, "titanium_score", "live_")
    )
    basket["authentic_margin"] = basket.authentic_score1 - basket.authentic_score2
    basket["live_margin"] = basket.live_score1 - basket.live_score2

    official_set = set(map(tuple, official_membership.to_numpy()))
    live_set = set(map(tuple, live_membership.to_numpy()))
    top1_match = basket.authentic_ticker1 == basket.live_ticker1
    top2_ordered = top1_match & (basket.authentic_ticker2 == basket.live_ticker2)
    top2_set = basket.apply(
        lambda row: {row.authentic_ticker1, row.authentic_ticker2}
        == {row.live_ticker1, row.live_ticker2},
        axis=1,
    )
    concentration_match = (basket.authentic_margin >= 0.12) == (basket.live_margin >= 0.12)

    result = {
        "common_signal_dates": len(common_dates),
        "common_start": str(pd.Timestamp(common_dates[0]).date()),
        "common_end": str(pd.Timestamp(common_dates[-1]).date()),
        "mean_monthly_score_correlation": float(correlations.mean()),
        "unrestricted_top1_agreement": float(
            (unrestricted.authentic_1 == unrestricted.live_1).mean()
        ),
        "basket_decisions": len(basket),
        "basket_top1_matches": int(top1_match.sum()),
        "basket_top1_agreement": float(top1_match.mean()),
        "basket_top2_ordered_matches": int(top2_ordered.sum()),
        "basket_top2_ordered_agreement": float(top2_ordered.mean()),
        "basket_top2_set_matches": int(top2_set.sum()),
        "basket_top2_set_agreement": float(top2_set.mean()),
        "concentration_regime_agreement": float(concentration_match.mean()),
        "membership_rows_common": len(official_set & live_set),
        "membership_rows_official_only": len(official_set - live_set),
        "membership_rows_live_only": len(live_set - official_set),
    }
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
