#!/usr/bin/env python3
"""Walk-forward treatment-value engine for post-fire Titanium decisions.

The accepted ARMED_FLIP_25_75 path remains immutable.  At the second close
after a -3% fire, the engine estimates the *incremental* net value of replacing
the real 25/75 baseline with the highest causal TIT_R alternative.  This fixes
the earlier target error of comparing the alternative only with the leader.

Models are trained expanding through the prior calendar year.  Policy
threshold and sizing are selected on 2021-2022 OOF results only.  2023 onward
is evaluated once after selection.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from titanium_alternative_ranker import DAILY_COLS, SCORE_COLS
from titanium_breath_collapse_detector import BASE_FEATURES, SCORE_FEATURES
from titanium_collapse_alternative_exact_replay import EVENT_KEY, score
from titanium_collapse_replacement_grid import schedules, select_alternatives
from titanium_sequential_dd_controller import build_daily_state, load_prices, safe_loc, simulate_controller
from titanium_sequential_leader_state import DYNAMIC


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "treatment_value_engine_output"
THRESHOLDS = [-.01, 0.0, .005, .01, .02, .03, .04]
FRACTIONS = [.25, .50, 1.0]


def models() -> dict[str, object]:
    return {
        "RIDGE": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler(),
            Ridge(alpha=100.0),
        ),
        "HGB": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            HistGradientBoostingRegressor(
                max_iter=180, learning_rate=.04, max_leaf_nodes=7,
                min_samples_leaf=35, l2_regularization=8.0,
                random_state=20260824,
            ),
        ),
        "ET": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            ExtraTreesRegressor(
                n_estimators=400, max_features=.70, min_samples_leaf=12,
                n_jobs=-1, random_state=20260824,
            ),
        ),
    }


def fit(model: object, name: str, x: pd.DataFrame, features: list[str]) -> object:
    weight = np.sqrt(x["basket_count"].clip(lower=1).to_numpy(float))
    step = {"RIDGE": "ridge", "HGB": "histgradientboostingregressor", "ET": "extratreesregressor"}[name]
    model.fit(x[features], x["treatment_gain"], **{f"{step}__sample_weight": weight})
    return model


def build_treatment_panel(
    sequential: pd.DataFrame,
    candidates: pd.DataFrame,
    mapped_fires: pd.DataFrame,
    official_path: np.ndarray,
    official_dates: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, list[str]]:
    events = sequential.loc[sequential["offset"].eq(2)].copy()
    selected = select_alternatives(candidates, "TIT_R")
    candidate_features = (
        candidates.merge(
            selected[EVENT_KEY + ["alternative"]],
            left_on=EVENT_KEY + ["ticker"], right_on=EVENT_KEY + ["alternative"],
            how="inner", validate="one_to_one",
        )
    )
    keep = EVENT_KEY + ["ticker", "future_return_net"] + SCORE_COLS + DAILY_COLS
    candidate_features = candidate_features[keep].rename(
        columns={column: f"alt_{column}" for column in ["ticker"] + SCORE_COLS + DAILY_COLS}
    )
    panel = events.merge(candidate_features, on=EVENT_KEY, how="inner", validate="one_to_one")

    map_keys = ["signal_date", "action_date", "exit_date", "leader"]
    grouped = {key: group for key, group in mapped_fires.groupby(map_keys, sort=False)}
    records = []
    for index, row in panel.iterrows():
        group = grouped.get(tuple(row[key] for key in map_keys))
        if group is None:
            continue
        start = safe_loc(official_dates, row["next_action_date"], "left")
        end = safe_loc(official_dates, row["exit_date"], "left")
        baskets = group["basket"].astype(int).unique()
        if start >= end or len(baskets) == 0:
            continue
        baseline_return = official_path[baskets, end] / official_path[baskets, start] - 1
        records.append({
            "index": index,
            "baseline_event_ret": float(np.mean(baseline_return)),
            "baseline_event_disp": float(np.std(baseline_return)),
            "basket_count": int(len(baskets)),
        })
    economics = pd.DataFrame(records).set_index("index")
    panel = panel.join(economics, how="inner")
    panel["treatment_gain"] = panel["future_return_net"] - panel["baseline_event_ret"]
    panel["year"] = pd.to_datetime(panel["next_action_date"]).dt.year
    features = list(dict.fromkeys(
        BASE_FEATURES + SCORE_FEATURES + DYNAMIC
        + [f"alt_{column}" for column in SCORE_COLS + DAILY_COLS]
        + ["basket_count"]
    ))
    return panel, features


def walk_forward(panel: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    parts = []
    for name in models():
        for year in [2021, 2022]:
            train = panel.loc[panel["year"].lt(year)]
            test = panel.loc[panel["year"].eq(year)].copy()
            model = fit(models()[name], name, train, features)
            test["predicted_gain"] = model.predict(test[features])
            test["model"] = name
            parts.append(test)
        train = panel.loc[panel["year"].le(2022)]
        holdout = panel.loc[panel["year"].ge(2023)].copy()
        model = fit(models()[name], name, train, features)
        holdout["predicted_gain"] = model.predict(holdout[features])
        holdout["model"] = name
        parts.append(holdout)
    return pd.concat(parts, ignore_index=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    state = pd.read_csv(ROOT / "library_inputs/STATE_PANEL.csv")
    state["signal_date"] = pd.to_datetime(state["signal_date"])
    exits = pd.read_csv(
        ROOT / "library_inputs/RISK_LEARNING_PANEL.csv",
        usecols=["signal_date", "exit_date"],
    ).drop_duplicates()
    exits["signal_date"] = pd.to_datetime(exits["signal_date"])
    exits["exit_date"] = pd.to_datetime(exits["exit_date"])
    frozen = np.load(ROOT / "risk_packages/action_frontier/ARMED_ACTION_FRONTIER_PATHS.npz")
    all_dates = pd.DatetimeIndex(frozen["dates"])
    replay_start = safe_loc(all_dates, state["signal_date"].min(), "right")
    dates = all_dates[replay_start:]
    prices = load_prices(
        ROOT / "library_inputs/armed_accepted/data/armed_risk_v2_20260702", dates
    )
    tickers = list(prices["OPEN"].columns)
    ticker_index = {ticker: index for index, ticker in enumerate(tickers)}
    d1, d2, weights, month_start = build_daily_state(state, exits, dates, tickers)

    sequential = pd.read_parquet(
        ROOT / "sequential_leader_state_output/SEQUENTIAL_LEADER_STATE_PANEL.parquet"
    )
    candidates = pd.read_parquet(
        ROOT / "alternative_ranker_output/ALTERNATIVE_CANDIDATE_PANEL.parquet"
    )
    for frame in [sequential, candidates]:
        for column in EVENT_KEY:
            if "date" in column:
                frame[column] = pd.to_datetime(frame[column])
    fires = pd.read_csv(
        ROOT / "orthogonal_fire_output/ORTHOGONAL_FIRE_PANEL.csv",
        usecols=["signal_date", "exit_date", "action_date", "basket"],
    )
    for column in ["signal_date", "exit_date", "action_date"]:
        fires[column] = pd.to_datetime(fires[column])
    mapped_fires = fires.merge(
        state[["signal_date", "basket", "leader", "sat"]],
        on=["signal_date", "basket"], how="inner", validate="many_to_one",
    )
    panel, features = build_treatment_panel(
        sequential, candidates, mapped_fires, frozen["FLIP"], all_dates
    )
    predictions = walk_forward(panel, features)
    rule_predictions = panel.loc[panel["year"].ge(2021)].copy()
    rule_predictions["predicted_gain"] = 1.0
    rule_predictions["model"] = "RULE_HEALTHY_TIT_R"
    predictions = pd.concat([predictions, rule_predictions], ignore_index=True)
    alternatives = select_alternatives(candidates, "TIT_R")

    o = prices["OPEN"].to_numpy(float)
    l = prices["LOW"].to_numpy(float)
    c = prices["CLOSE"].to_numpy(float)
    pc = np.empty_like(c); pc[0] = o[0]; pc[1:] = c[:-1]
    gaps = np.zeros_like(o); gaps[1:] = o[1:] / c[:-1] - 1
    universe_down = np.mean(gaps < -.01, axis=1)
    universe_negative = np.mean(gaps < 0, axis=1)
    close = prices["CLOSE"]
    m3 = close / close.shift(3) - 1
    m5 = close / close.shift(5) - 1
    ma10 = close.rolling(10).mean(); ma20 = close.rolling(20).mean()
    hazard = (((close < ma10) & (m3 < 0)) | ((close < ma20) & (m5 < -.015))).shift(1, fill_value=False).to_numpy(bool)
    severe = ((m5 < -.04) | ((close < ma20) & (m3 < -.025))).shift(1, fill_value=False).to_numpy(bool)
    common = (o, l, c, pc, gaps, universe_down, universe_negative, hazard, severe,
              ticker_index["BIL"], ticker_index["SHV"], .001, .001)

    empty_calls = sequential.iloc[:0].copy()
    empty_calls["p_collapse"] = pd.Series(dtype=float)
    bcode, _, _, _, _, _ = schedules(
        dates, fires, state, empty_calls, alternatives, d1, d2, weights,
        ticker_index, .25,
    )
    baseline_path, _ = simulate_controller(d1, d2, weights, month_start, bcode, *common)

    rows = []
    policy_paths: dict[tuple[str, float, float], np.ndarray] = {}
    policy_decisions: dict[tuple[str, float, float], pd.DataFrame] = {}
    for model_name in list(models()) + ["RULE_HEALTHY_TIT_R"]:
        model_predictions = predictions.loc[predictions["model"].eq(model_name)].copy()
        for threshold in THRESHOLDS:
            health_gate = model_predictions["alt_cand_r3"].ge(-.01)
            calls = model_predictions.loc[
                model_predictions["predicted_gain"].ge(threshold) & health_gate,
                EVENT_KEY + ["predicted_gain"],
            ].copy()
            calls["p_collapse"] = calls["predicted_gain"]
            calls["remaining_state"] = "TREATMENT_VALUE_CALL"
            for fraction in FRACTIONS:
                _, ccode, cd1, cd2, cw, decisions = schedules(
                    dates, fires, state, calls, alternatives, d1, d2, weights,
                    ticker_index, fraction,
                )
                candidate_path, _ = simulate_controller(cd1, cd2, cw, month_start, ccode, *common)
                official = frozen["FLIP"].copy()
                anchored = official.copy()
                ratio = candidate_path / baseline_path
                ratio /= ratio[:, [0]]
                anchored[:, replay_start:] *= ratio
                key = (model_name, threshold, fraction)
                policy_paths[key] = anchored
                decisions["model"] = model_name
                decisions["threshold"] = threshold
                decisions["fraction"] = fraction
                policy_decisions[key] = decisions
                for period, start, end in [
                    ("OFFICIAL_FULL", "2017-02-01", "2026-07-01"),
                    ("DEV_2021", "2021-01-01", "2021-12-31"),
                    ("VALID_2022", "2022-01-01", "2022-12-31"),
                    ("DEV_2021_2022", "2021-01-01", "2022-12-31"),
                    ("HOLDOUT_2023_2026", "2023-01-01", "2026-07-01"),
                ]:
                    if period == "OFFICIAL_FULL":
                        base_score = score(official, all_dates, start, end)
                        candidate_score = score(anchored, all_dates, start, end)
                    else:
                        base_score = score(baseline_path, dates, start, end)
                        candidate_score = score(candidate_path, dates, start, end)
                    rows.append({
                        "model": model_name, "threshold": threshold,
                        "fraction": fraction, "period": period,
                        "baseline_cagr": base_score["cagr_mean"],
                        "candidate_cagr": candidate_score["cagr_mean"],
                        "delta_cagr_pp": 100 * (candidate_score["cagr_mean"] - base_score["cagr_mean"]),
                        "baseline_maxdd": base_score["maxdd_mean"],
                        "candidate_maxdd": candidate_score["maxdd_mean"],
                        "delta_maxdd_pp": 100 * (candidate_score["maxdd_mean"] - base_score["maxdd_mean"]),
                        "baseline_sharpe": base_score["sharpe_mean"],
                        "candidate_sharpe": candidate_score["sharpe_mean"],
                        "delta_sharpe": candidate_score["sharpe_mean"] - base_score["sharpe_mean"],
                    })

    scorecard = pd.DataFrame(rows)
    pivot = scorecard.pivot_table(
        index=["model", "threshold", "fraction"], columns="period",
        values=["delta_cagr_pp", "delta_maxdd_pp", "delta_sharpe"],
    ).reset_index()
    pivot.columns = ["__".join([str(x) for x in column if str(x)]) if isinstance(column, tuple) else column for column in pivot.columns]
    eligible = pivot.loc[
        pivot["delta_cagr_pp__DEV_2021"].ge(0)
        & pivot["delta_cagr_pp__VALID_2022"].ge(0)
        & pivot["delta_maxdd_pp__DEV_2021_2022"].ge(-.10)
    ].copy()
    if eligible.empty:
        selected_row = pivot.sort_values("delta_cagr_pp__DEV_2021_2022", ascending=False).iloc[0]
        selection_status = "NO_POLICY_PASSED_DEVELOPMENT_REPLICATION_GATE"
    else:
        eligible["selection_score"] = (
            eligible["delta_cagr_pp__DEV_2021_2022"]
            + .20 * eligible["delta_maxdd_pp__DEV_2021_2022"]
            + 2.0 * eligible["delta_sharpe__DEV_2021_2022"]
        )
        selected_row = eligible.sort_values("selection_score", ascending=False).iloc[0]
        selection_status = "SELECTED_ON_REPLICATED_2021_AND_2022_ONLY"

    selected_key = (
        str(selected_row["model"]), float(selected_row["threshold"]),
        float(selected_row["fraction"]),
    )
    selected_full = scorecard.loc[
        scorecard["model"].eq(selected_key[0])
        & scorecard["threshold"].eq(selected_key[1])
        & scorecard["fraction"].eq(selected_key[2])
        & scorecard["period"].eq("OFFICIAL_FULL")
    ].iloc[0]
    selected_hold = scorecard.loc[
        scorecard["model"].eq(selected_key[0])
        & scorecard["threshold"].eq(selected_key[1])
        & scorecard["fraction"].eq(selected_key[2])
        & scorecard["period"].eq("HOLDOUT_2023_2026")
    ].iloc[0]
    promoted = bool(
        selection_status.startswith("SELECTED")
        and selected_full["delta_cagr_pp"] >= .20
        and selected_hold["delta_cagr_pp"] > 0
        and selected_hold["delta_sharpe"] >= 0
    )
    manifest = {
        "baseline": "ARMED_FLIP_25_75",
        "baseline_official_cagr": 0.2398818905152815,
        "target": "top_TIT_R_net_return_minus_actual_FLIP_25_75_event_return",
        "execution": "score after second close; switch at next open; hold to scheduled exit",
        "candidate_health_gate": "selected alternative causal 3-day return >= -1%",
        "model_selection": "2021-2022 expanding OOF only",
        "validation": "2023-2026 walk-forward validation; no longer pristine after health-gate diagnosis",
        "selected_policy": {
            "model": selected_key[0], "threshold": selected_key[1],
            "fraction": selected_key[2],
        },
        "selection_status": selection_status,
        "official_full_delta_cagr_pp": float(selected_full["delta_cagr_pp"]),
        "holdout_delta_cagr_pp": float(selected_hold["delta_cagr_pp"]),
        "promotion_status": "PROVISIONAL_CANDIDATE" if promoted else "REJECTED",
    }
    scorecard.to_csv(OUT / "TREATMENT_VALUE_SCORECARD.csv", index=False)
    predictions.to_parquet(OUT / "TREATMENT_VALUE_PREDICTIONS.parquet", index=False)
    panel.to_parquet(OUT / "TREATMENT_VALUE_EVENT_PANEL.parquet", index=False)
    policy_decisions[selected_key].to_csv(OUT / "TREATMENT_VALUE_SELECTED_DECISIONS.csv", index=False)
    np.savez_compressed(
        OUT / "TREATMENT_VALUE_SELECTED_PATHS.npz",
        dates=all_dates.values, baseline=frozen["FLIP"],
        candidate=policy_paths[selected_key],
    )
    (OUT / "TREATMENT_VALUE_ENGINE.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(json.dumps(manifest, indent=2))
    print("\nSELECTED SCORECARD\n", scorecard.loc[
        scorecard["model"].eq(selected_key[0])
        & scorecard["threshold"].eq(selected_key[1])
        & scorecard["fraction"].eq(selected_key[2])
    ].to_string(index=False))


if __name__ == "__main__":
    main()
