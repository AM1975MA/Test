#!/usr/bin/env python3
"""Retrain Titanium once while holding official baskets and evaluation dates fixed."""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def top_two(frame: pd.DataFrame, score: str, group: list[str], prefix: str) -> pd.DataFrame:
    ordered = frame.sort_values(
        group + [score, "ticker"],
        ascending=[True] * len(group) + [False, True],
        kind="mergesort",
    ).copy()
    ordered["rank_number"] = ordered.groupby(group).cumcount() + 1
    wide = ordered.loc[ordered["rank_number"].le(2)].pivot(
        index=group, columns="rank_number", values=["ticker", score]
    )
    wide.columns = [f"{prefix}{'ticker' if field == 'ticker' else 'score'}{rank_}" for field, rank_ in wide.columns]
    return wide


def parity(authentic: pd.DataFrame, retrained: pd.DataFrame, membership: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    common_dates = sorted(set(authentic["signal_date"]) & set(retrained["signal_date"]))
    auth = authentic.loc[authentic["signal_date"].isin(common_dates), ["signal_date", "ticker", "TIT_R"]]
    new = retrained.loc[retrained["signal_date"].isin(common_dates), ["signal_date", "ticker", "titanium_score"]]
    joined = auth.merge(new, on=["signal_date", "ticker"], how="inner", validate="one_to_one")
    correlations = joined.groupby("signal_date").apply(
        lambda x: x["TIT_R"].corr(x["titanium_score"]), include_groups=False
    )

    unrestricted = top_two(joined, "TIT_R", ["signal_date"], "auth_").join(
        top_two(joined, "titanium_score", ["signal_date"], "new_")
    )
    expanded = joined.merge(membership, on="ticker", how="inner", validate="many_to_many")
    basket = top_two(expanded, "TIT_R", ["signal_date", "basket"], "auth_").join(
        top_two(expanded, "titanium_score", ["signal_date", "basket"], "new_")
    )
    basket["auth_margin"] = basket["auth_score1"] - basket["auth_score2"]
    basket["new_margin"] = basket["new_score1"] - basket["new_score2"]
    top1 = basket["auth_ticker1"].eq(basket["new_ticker1"])
    ordered2 = top1 & basket["auth_ticker2"].eq(basket["new_ticker2"])
    set2 = basket.apply(
        lambda x: {x["auth_ticker1"], x["auth_ticker2"]} == {x["new_ticker1"], x["new_ticker2"]}, axis=1
    )
    regime = basket["auth_margin"].ge(0.12).eq(basket["new_margin"].ge(0.12))
    result = {
        "common_signal_dates": len(common_dates),
        "common_start": str(pd.Timestamp(common_dates[0]).date()),
        "common_end": str(pd.Timestamp(common_dates[-1]).date()),
        "common_tickers": int(joined["ticker"].nunique()),
        "mean_monthly_score_correlation": float(correlations.mean()),
        "unrestricted_top1_matches": int(unrestricted["auth_ticker1"].eq(unrestricted["new_ticker1"]).sum()),
        "unrestricted_top1_agreement": float(unrestricted["auth_ticker1"].eq(unrestricted["new_ticker1"]).mean()),
        "basket_decisions": int(len(basket)),
        "basket_top1_matches": int(top1.sum()),
        "basket_top1_agreement": float(top1.mean()),
        "basket_top2_ordered_matches": int(ordered2.sum()),
        "basket_top2_ordered_agreement": float(ordered2.mean()),
        "basket_top2_set_matches": int(set2.sum()),
        "basket_top2_set_agreement": float(set2.mean()),
        "concentration_regime_matches": int(regime.sum()),
        "concentration_regime_agreement": float(regime.mean()),
    }
    return result, basket.reset_index()


def replay(panel: pd.DataFrame, membership: pd.DataFrame, score: str, cost: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    columns = ["signal_date", "ticker", score, "fwd_ret_21"]
    expanded = membership.merge(panel[columns], on="ticker", how="inner", validate="many_to_many")
    ordered = expanded.sort_values(
        ["basket", "signal_date", score, "ticker"],
        ascending=[True, True, False, True],
        kind="mergesort",
    ).copy()
    ordered["rank_number"] = ordered.groupby(["basket", "signal_date"]).cumcount() + 1
    top = ordered.loc[ordered["rank_number"].le(2)].pivot(
        index=["basket", "signal_date"], columns="rank_number", values=["ticker", score, "fwd_ret_21"]
    )
    top.columns = [f"{field}{int(rank_)}" for field, rank_ in top.columns]
    top = top.dropna().reset_index().sort_values(["basket", "signal_date"])
    top["margin"] = top[f"{score}1"] - top[f"{score}2"]
    top["weight1"] = np.where(top["margin"].ge(0.12), 1.0, 0.75)
    top["weight2"] = 1.0 - top["weight1"]
    top["gross_return"] = top["weight1"] * top["fwd_ret_211"] + top["weight2"] * top["fwd_ret_212"]

    net_returns = []
    turnovers = []
    previous: dict[int, dict[str, float]] = {}
    for row in top.itertuples(index=False):
        basket = int(row.basket)
        current = {str(row.ticker1): float(row.weight1)}
        if float(row.weight2) > 0:
            current[str(row.ticker2)] = float(row.weight2)
        prior = previous.get(basket, {})
        names = set(current) | set(prior)
        turn = 0.5 * sum(abs(current.get(t, 0.0) - prior.get(t, 0.0)) for t in names)
        turnovers.append(turn)
        net_returns.append(float(row.gross_return) - cost * turn)
        previous[basket] = current
    top["turnover"] = turnovers
    top["net_return"] = net_returns

    rows = []
    for basket, group in top.groupby("basket", sort=True):
        values = group["net_return"].to_numpy(float)
        equity = np.cumprod(1.0 + values)
        drawdown = equity / np.maximum.accumulate(equity) - 1.0
        std = values.std(ddof=1)
        rows.append(
            {
                "basket": int(basket),
                "months": int(len(values)),
                "cagr": float(equity[-1] ** (12.0 / len(values)) - 1.0),
                "maxdd": float(drawdown.min()),
                "sharpe": float(np.sqrt(12.0) * values.mean() / std) if std > 0 else np.nan,
                "final_equity": float(equity[-1]),
            }
        )
    metrics = pd.DataFrame(rows)
    summary = pd.DataFrame(
        [{
            "baskets": int(metrics["basket"].nunique()),
            "mean_months": float(metrics["months"].mean()),
            "mean_cagr": float(metrics["cagr"].mean()),
            "median_cagr": float(metrics["cagr"].median()),
            "mean_maxdd": float(metrics["maxdd"].mean()),
            "mean_sharpe": float(metrics["sharpe"].mean()),
        }]
    )
    return top, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-module", type=Path, required=True)
    parser.add_argument("--v6-module", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--authentic-panel", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--existing-live-panel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--n-estimators", type=int, default=360)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    base = load_module(args.base_module.resolve(), "retrain_base")
    v6 = load_module(args.v6_module.resolve(), "retrain_v6")
    base.rolling_downvol = lambda ret, h: ret.clip(upper=0.0).rolling(h, min_periods=h).std(ddof=0) * np.sqrt(252)

    mats = v6.load_mats(args.data_dir.resolve())
    dates, compact, _tail0, dictionary = base.build_features(mats)
    dictionary = v6.enhance_feature_dictionary(base, mats, dates, dictionary)
    tail = v6.rebuild_tail_long(base, dictionary, dates, mats["Close"].columns)
    compact = base.add_labels(compact, mats["Open"], dates)
    tail = base.add_labels(tail, mats["Open"], dates)
    clusters, _balance, _ari = v6.build_s3b_clusters(mats, dates, base.TICKER_CATEGORY)
    macro, macro_features = v6.build_macro_panel(base, dictionary, compact, base.TICKER_CATEGORY)
    opportunity = v6.build_opportunity_panel(base, dictionary, clusters, compact)
    retrained, _opp, fit_audit, _macro_pred = v6.fit_predict(
        base, compact, tail, macro, macro_features, opportunity, range(2017, 2027), args.n_estimators
    )
    retrained = retrained.loc[retrained["signal_date"].ge(v6.BACKTEST_START)].copy()

    authentic = pd.read_pickle(args.authentic_panel)
    membership = pd.read_csv(args.membership)[["basket", "ticker"]]
    existing = pd.read_parquet(args.existing_live_panel)
    for frame in (retrained, authentic, existing):
        frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="raise")
        frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    membership["ticker"] = membership["ticker"].astype(str).str.upper().str.strip()

    compare_columns = ["compact_rank", "tail_rank", "macro_bonus", "titanium_score"]
    deterministic = existing[["signal_date", "ticker"] + compare_columns].merge(
        retrained[["signal_date", "ticker"] + compare_columns],
        on=["signal_date", "ticker"], suffixes=("_existing", "_fresh"), how="outer", indicator=True,
        validate="one_to_one",
    )
    det = {"key_rows": int(len(deterministic)), "keys_identical": bool(deterministic["_merge"].eq("both").all())}
    for column in compare_columns:
        left = deterministic[f"{column}_existing"].to_numpy(float)
        right = deterministic[f"{column}_fresh"].to_numpy(float)
        delta = np.abs(left - right)
        det[f"{column}_max_abs_delta"] = float(np.nanmax(delta))
        det[f"{column}_allclose_1e_12"] = bool(np.allclose(left, right, atol=1e-12, rtol=0.0, equal_nan=True))

    common_dates = sorted(set(authentic["signal_date"]) & set(retrained["signal_date"]))
    authentic_eval = authentic.loc[authentic["signal_date"].isin(common_dates)].copy()
    retrained_eval = retrained.loc[retrained["signal_date"].isin(common_dates)].merge(
        authentic[["signal_date", "ticker", "fwd_ret_21"]], on=["signal_date", "ticker"], how="left", validate="one_to_one"
    )
    parity_result, basket_choices = parity(authentic_eval, retrained_eval, membership)
    auth_replay, auth_summary = replay(authentic_eval, membership, "TIT_R", 0.001)
    new_replay, new_summary = replay(retrained_eval, membership, "titanium_score", 0.001)
    auth_summary.insert(0, "strategy", "authenticated_TIT_R")
    new_summary.insert(0, "strategy", "fresh_retrained")
    replay_summary = pd.concat([auth_summary, new_summary], ignore_index=True)

    retrained.to_parquet(args.output_dir / "FRESH_RETRAINED_SCORE_PANEL.parquet", index=False, compression="zstd")
    fit_audit.to_csv(args.output_dir / "FIT_AUDIT.csv", index=False)
    basket_choices.to_csv(args.output_dir / "OFFICIAL_BASKET_SELECTION_COMPARISON.csv.gz", index=False)
    auth_replay.to_csv(args.output_dir / "AUTHENTIC_MONTHLY_REPLAY.csv.gz", index=False)
    new_replay.to_csv(args.output_dir / "RETRAINED_MONTHLY_REPLAY.csv.gz", index=False)
    replay_summary.to_csv(args.output_dir / "ISOLATED_MONTHLY_REPLAY_SUMMARY.csv", index=False)

    result = {
        "status": "PASS" if det["titanium_score_allclose_1e_12"] else "NONDETERMINISTIC_RETRAIN",
        "experiment": "fresh retraining only; official baskets, common dates, architecture and threshold fixed",
        "elapsed_seconds": float(time.time() - started),
        "data": {
            "price_tickers": int(len(mats["Close"].columns)),
            "price_start": str(pd.Timestamp(mats["Close"].index.min()).date()),
            "price_end": str(pd.Timestamp(mats["Close"].index.max()).date()),
            "retrained_rows": int(len(retrained)),
            "retrained_tickers": int(retrained["ticker"].nunique()),
            "retrained_signal_dates": int(retrained["signal_date"].nunique()),
            "official_baskets": int(membership["basket"].nunique()),
        },
        "fresh_vs_existing_live_determinism": det,
        "fresh_retrained_vs_authenticated": parity_result,
        "isolated_monthly_replay": replay_summary.to_dict(orient="records"),
        "interpretation_guardrails": [
            "The selection comparison isolates retraining because official basket membership and common dates are fixed.",
            "The monthly replay uses authenticated fwd_ret_21 labels and identical cost logic for both score panels.",
            "The monthly replay is an attribution diagnostic and is not the official daily governor path scorecard.",
        ],
    }
    (args.output_dir / "RETRAIN_ONLY_REPORT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
