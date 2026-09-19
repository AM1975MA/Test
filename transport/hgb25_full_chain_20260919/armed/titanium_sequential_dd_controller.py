#!/usr/bin/env python3
"""Sequential DD Controller V1 for the frozen Titanium/CVX4 research branch.

The experiment starts from the accepted ARMED_RISK_FLIP_3PCT mechanics:

* the frozen monthly model arms the position;
* a leader close at or below 97% of the monthly entry open fires;
* FLIP (25% leader / 75% satellite) is executed at the next open;
* only subsequent closes may change the action.

The controller is deliberately hierarchical.  It estimates short-horizon
leader hazard, severe leader hazard, recovery, joint leader/satellite hazard,
and satellite relative health.  A causal state machine then chooses among
FLIP, SWAP, CASH50 and CASH100 at the next open with hysteresis and cooldown.

Development uses expanding out-of-fold predictions.  Model families are
chosen on 2021 only (trained through 2020); policy thresholds are selected on
2022, subject to a 2021 drawdown guardrail.  Both layers are frozen before the
exploratory 2023-2026 replay.  The official Titanium V2, CVX4 and FLIP
artifacts are read only and are never overwritten.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from titanium_true_orthogonal_lab import load_official_series, true_orthogonal_features


EPS = 1e-12
TARGETS = [
    "y_leader_drop5_2",
    "y_leader_drop10_4",
    "y_recover_fire5",
    "y_systemic_drop5_2",
    "y_sat_beats5",
]


@dataclass(frozen=True)
class Policy:
    name: str
    hazard_hi: float
    severe_hi: float
    systemic_hi: float
    recovery_veto: float
    satellite_hi: float
    cash_mode: str
    exit_margin: float = 0.15
    confirm_closes: int = 1
    release_closes: int = 2
    cooldown: int = 2


def model_catalog() -> dict[str, object]:
    return {
        "LOGIT": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler(),
            LogisticRegression(
                C=0.20,
                class_weight="balanced",
                max_iter=2500,
                random_state=20260824,
            ),
        ),
        "HGB": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            HistGradientBoostingClassifier(
                learning_rate=0.04,
                max_iter=120,
                max_leaf_nodes=7,
                min_samples_leaf=45,
                l2_regularization=4.0,
                random_state=20260824,
            ),
        ),
    }


def sample_weights(frame: pd.DataFrame, target: str) -> np.ndarray:
    date_weight = frame["date_weight"].to_numpy(float)
    y = frame[target].to_numpy(int)
    positive = max(float(date_weight[y == 1].sum()), EPS)
    negative = max(float(date_weight[y == 0].sum()), EPS)
    class_weight = np.where(y == 1, 0.5 / positive, 0.5 / negative)
    return class_weight * date_weight * len(frame)


def fit_model(model: object, name: str, frame: pd.DataFrame, features: list[str], target: str) -> object:
    final_step = "logisticregression" if name == "LOGIT" else "histgradientboostingclassifier"
    model.fit(
        frame[features],
        frame[target].astype(int),
        **{f"{final_step}__sample_weight": sample_weights(frame, target)},
    )
    return model


def weighted_auc(y: pd.Series, probability: np.ndarray, weight: pd.Series) -> float:
    if y.nunique() < 2:
        return float("nan")
    return float(roc_auc_score(y, probability, sample_weight=weight))


def safe_loc(index: pd.DatetimeIndex, value: pd.Timestamp, side: str = "left") -> int:
    return int(index.searchsorted(pd.Timestamp(value), side=side))


def load_prices(data_dir: Path, dates: pd.DatetimeIndex) -> dict[str, pd.DataFrame]:
    result = {}
    for name in ["OPEN", "LOW", "CLOSE", "VOLUME"]:
        frame = pd.read_parquet(data_dir / f"{name}.parquet").sort_index()
        frame.index = pd.to_datetime(frame.index)
        frame.columns = frame.columns.astype(str).str.upper().str.strip()
        result[name] = frame.reindex(dates).ffill().bfill()
    columns = result["OPEN"].columns
    for name in result:
        result[name] = result[name].reindex(columns=columns)
    return result


def build_pair_events(root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    fires = pd.read_csv(root / "orthogonal_fire_output/ORTHOGONAL_FIRE_PANEL.csv")
    for column in ["signal_date", "exit_date", "feature_date", "action_date"]:
        fires[column] = pd.to_datetime(fires[column])
    state = pd.read_csv(root / "library_inputs/STATE_PANEL.csv")
    state["signal_date"] = pd.to_datetime(state["signal_date"])
    mapped = fires.merge(
        state[["signal_date", "basket", "leader", "sat", "legacy_w1"]],
        on=["signal_date", "basket"],
        how="inner",
        validate="many_to_one",
    )
    mapped["pair_key"] = (
        mapped["feature_date"].dt.strftime("%Y-%m-%d")
        + "|" + mapped["leader"].astype(str)
        + "|" + mapped["sat"].astype(str)
    )
    unique = (
        mapped.sort_values(["feature_date", "leader", "sat", "basket"])
        .groupby(["pair_key", "feature_date", "leader", "sat"], as_index=False)
        .agg(
            signal_date=("signal_date", "first"),
            action_date=("action_date", "first"),
            exit_date=("exit_date", "first"),
            multiplicity=("basket", "size"),
        )
    )
    return mapped, unique


def precompute_features(prices: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    close = prices["CLOSE"]
    open_ = prices["OPEN"]
    volume = prices["VOLUME"]
    ret = close.pct_change(fill_method=None)
    features: dict[str, pd.DataFrame] = {}
    for lag in [1, 3, 5, 10, 21]:
        features[f"r{lag}"] = close.pct_change(lag, fill_method=None)
    for window in [5, 10, 21, 63]:
        features[f"vol{window}"] = ret.rolling(window).std() * math.sqrt(252)
    for window in [21, 63]:
        features[f"dd{window}"] = close / close.rolling(window).max() - 1
    features["gap"] = open_ / close.shift(1) - 1
    log_volume = np.log1p(volume.clip(lower=0))
    features["volume_z21"] = (
        (log_volume - log_volume.rolling(21).mean()) / log_volume.rolling(21).std()
    )
    features["downfrac5"] = (ret < 0).rolling(5).mean()
    market = pd.DataFrame(index=close.index)
    for lag in [1, 5, 21]:
        cross = close.pct_change(lag, fill_method=None)
        market[f"breadth_pos{lag}"] = (cross > 0).mean(axis=1)
        market[f"breadth_loss2_{lag}"] = (cross < -0.02).mean(axis=1)
        market[f"dispersion{lag}"] = cross.std(axis=1)
    market["cross_down1"] = (ret < 0).mean(axis=1)
    market["cross_crash1"] = (ret < -0.03).mean(axis=1)
    return features, market


def forward_path(series: pd.Series, start: int, horizon: int, end: int) -> np.ndarray:
    stop = min(start + horizon, end - 1)
    if stop <= start:
        return np.asarray([], dtype=float)
    base = float(series.iloc[start])
    return series.iloc[start + 1 : stop + 1].to_numpy(float) / base - 1


def build_sequential_panel(
    pair_events: pd.DataFrame,
    prices: dict[str, pd.DataFrame],
    orthogonal: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    close = prices["CLOSE"]
    date_index = close.index
    ticker_features, market = precompute_features(prices)
    orthogonal = orthogonal.reindex(date_index.union(orthogonal.index)).sort_index().ffill().reindex(date_index)
    rows: list[dict] = []

    for event in pair_events.itertuples(index=False):
        if event.leader not in close.columns or event.sat not in close.columns:
            continue
        fire_pos = safe_loc(date_index, event.feature_date, "right") - 1
        start_pos = safe_loc(date_index, event.action_date, "left")
        exit_pos = safe_loc(date_index, event.exit_date, "left")
        if fire_pos < 63 or start_pos >= exit_pos - 1:
            continue
        leader_fire_close = float(close.iloc[fire_pos][event.leader])
        for score_pos in range(start_pos, exit_pos - 1):
            score_date = date_index[score_pos]
            row: dict[str, object] = {
                "pair_key": event.pair_key,
                "signal_date": event.signal_date,
                "feature_date": event.feature_date,
                "first_action_date": event.action_date,
                "score_date": score_date,
                "next_action_date": date_index[score_pos + 1],
                "exit_date": event.exit_date,
                "leader": event.leader,
                "sat": event.sat,
                "multiplicity": int(event.multiplicity),
                "days_after_fire": int(score_pos - fire_pos),
                "remaining_days": int(exit_pos - score_pos - 1),
                "leader_since_fire": float(close.iloc[score_pos][event.leader] / leader_fire_close - 1),
                "sat_since_fire": float(close.iloc[score_pos][event.sat] / close.iloc[fire_pos][event.sat] - 1),
            }
            for role, ticker in [("leader", event.leader), ("sat", event.sat)]:
                for name, frame in ticker_features.items():
                    row[f"{role}_{name}"] = float(frame.iloc[score_pos][ticker])
            for lag in [1, 3, 5, 10, 21]:
                row[f"sat_minus_leader_r{lag}"] = row[f"sat_r{lag}"] - row[f"leader_r{lag}"]
            row["sat_minus_leader_since_fire"] = row["sat_since_fire"] - row["leader_since_fire"]
            leader_returns = close[event.leader].pct_change(fill_method=None).iloc[score_pos - 20 : score_pos + 1]
            sat_returns = close[event.sat].pct_change(fill_method=None).iloc[score_pos - 20 : score_pos + 1]
            valid = leader_returns.notna() & sat_returns.notna()
            row["leader_sat_corr21"] = (
                float(leader_returns[valid].corr(sat_returns[valid])) if valid.sum() >= 10 else np.nan
            )
            for name, value in market.iloc[score_pos].items():
                row[name] = float(value)
            if "SPY" in close.columns:
                row["spy_r5"] = float(ticker_features["r5"].iloc[score_pos]["SPY"])
                row["spy_r21"] = float(ticker_features["r21"].iloc[score_pos]["SPY"])
                row["spy_dd63"] = float(ticker_features["dd63"].iloc[score_pos]["SPY"])
            for name, value in orthogonal.iloc[score_pos].items():
                row[name] = float(value) if pd.notna(value) else np.nan

            lp5 = forward_path(close[event.leader], score_pos, 5, exit_pos)
            lp10 = forward_path(close[event.leader], score_pos, 10, exit_pos)
            sp5 = forward_path(close[event.sat], score_pos, 5, exit_pos)
            cp5 = 0.5 * (
                forward_path(close["BIL"], score_pos, 5, exit_pos)
                + forward_path(close["SHV"], score_pos, 5, exit_pos)
            )
            if not len(lp5) or not len(lp10) or not len(sp5):
                continue
            common5 = min(len(lp5), len(sp5), len(cp5))
            lp5, sp5, cp5 = lp5[:common5], sp5[:common5], cp5[:common5]
            row["y_leader_drop5_2"] = int(np.nanmin(lp5) <= -0.02)
            row["y_leader_drop10_4"] = int(np.nanmin(lp10) <= -0.04)
            future_leader_levels = close[event.leader].iloc[score_pos + 1 : score_pos + 1 + common5]
            row["y_recover_fire5"] = int(float(future_leader_levels.max()) >= leader_fire_close)
            row["y_systemic_drop5_2"] = int(np.nanmin(lp5) <= -0.02 and np.nanmin(sp5) <= -0.02)
            row["y_sat_beats5"] = int(sp5[-1] - lp5[-1] >= 0.005)
            row["leader_terminal5"] = float(lp5[-1])
            row["sat_terminal5"] = float(sp5[-1])
            row["cash_terminal5"] = float(cp5[-1])
            rows.append(row)

    panel = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan)
    panel["date_weight"] = 1.0 / panel.groupby("score_date")["pair_key"].transform("nunique")
    excluded = {
        "pair_key", "signal_date", "feature_date", "first_action_date", "score_date",
        "next_action_date", "exit_date", "leader", "sat", "multiplicity", "date_weight",
        "leader_terminal5", "sat_terminal5", "cash_terminal5", *TARGETS,
    }
    features = [
        column for column in panel.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(panel[column])
    ]
    return panel, features


def score_models(panel: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    score_rows: list[dict] = []
    prediction_parts: list[pd.DataFrame] = []
    selected: dict[str, str] = {}

    for target in TARGETS:
        target_predictions = panel[[
            "pair_key", "score_date", "next_action_date", "feature_date", "exit_date",
            "leader", "sat", "multiplicity", "date_weight", target,
        ]].copy()
        for name in model_catalog():
            target_predictions[f"p_{target}_{name.lower()}"] = np.nan
        for test_year in [2021, 2022]:
            train = panel[panel["score_date"].dt.year < test_year].copy()
            test = panel[panel["score_date"].dt.year.eq(test_year)].copy()
            for name, model in model_catalog().items():
                fitted = fit_model(model, name, train, features, target)
                probability = fitted.predict_proba(test[features])[:, 1]
                target_predictions.loc[test.index, f"p_{target}_{name.lower()}"] = probability
                score_rows.append({
                    "target": target,
                    "model": name,
                    "period": str(test_year),
                    "rows": int(len(test)),
                    "effective_dates": int(test["score_date"].nunique()),
                    "positive_rate": float(np.average(test[target], weights=test["date_weight"])),
                    "auc": weighted_auc(test[target], probability, test["date_weight"]),
                    "brier": float(np.average((test[target].to_numpy() - probability) ** 2, weights=test["date_weight"])),
                })
        development = target_predictions[target_predictions["score_date"].dt.year.between(2021, 2022)]
        model_validation = target_predictions[target_predictions["score_date"].dt.year.eq(2021)]
        model_summary = []
        for name in model_catalog():
            probability = model_validation[f"p_{target}_{name.lower()}"].to_numpy(float)
            valid = np.isfinite(probability)
            auc = weighted_auc(model_validation.loc[valid, target], probability[valid], model_validation.loc[valid, "date_weight"])
            model_summary.append((name, auc))
        for name in model_catalog():
            probability = development[f"p_{target}_{name.lower()}"].to_numpy(float)
            valid = np.isfinite(probability)
            auc = weighted_auc(development.loc[valid, target], probability[valid], development.loc[valid, "date_weight"])
            score_rows.append({
                "target": target,
                "model": name,
                "period": "DEV_OOF_2021_2022",
                "rows": int(valid.sum()),
                "effective_dates": int(development.loc[valid, "score_date"].nunique()),
                "positive_rate": float(np.average(development.loc[valid, target], weights=development.loc[valid, "date_weight"])),
                "auc": auc,
                "brier": float(np.average((development.loc[valid, target].to_numpy() - probability[valid]) ** 2, weights=development.loc[valid, "date_weight"])),
            })
        selected[target] = sorted(model_summary, key=lambda item: (np.nan_to_num(item[1], nan=-1), item[0] == "LOGIT"), reverse=True)[0][0]

        holdout = panel[panel["score_date"].dt.year >= 2023].copy()
        train = panel[panel["score_date"].dt.year <= 2022].copy()
        for name, model in model_catalog().items():
            fitted = fit_model(model, name, train, features, target)
            probability = fitted.predict_proba(holdout[features])[:, 1]
            target_predictions.loc[holdout.index, f"p_{target}_{name.lower()}"] = probability
            score_rows.append({
                "target": target,
                "model": name,
                "period": "HOLDOUT_2023_2026_EXPLORED",
                "rows": int(len(holdout)),
                "effective_dates": int(holdout["score_date"].nunique()),
                "positive_rate": float(np.average(holdout[target], weights=holdout["date_weight"])),
                "auc": weighted_auc(holdout[target], probability, holdout["date_weight"]),
                "brier": float(np.average((holdout[target].to_numpy() - probability) ** 2, weights=holdout["date_weight"])),
            })
        columns = [c for c in target_predictions if c.startswith("p_")]
        prediction_parts.append(target_predictions[["pair_key", "score_date"] + columns])

    merged = panel.copy()
    for part in prediction_parts:
        merged = merged.merge(part, on=["pair_key", "score_date"], how="left", validate="one_to_one")
    for target, model_name in selected.items():
        merged[f"p_{target}"] = merged[f"p_{target}_{model_name.lower()}"]
    return pd.DataFrame(score_rows), merged, selected


def policy_grid() -> list[Policy]:
    policies = [Policy("FLIP_ONLY", 1.01, 1.01, 1.01, -0.01, 1.01, "NONE")]
    for hazard in [0.60, 0.70, 0.80]:
        for systemic in [0.65, 0.75, 0.85]:
            for satellite in [0.55, 0.65]:
                policies.append(Policy(
                    f"SEQ_H{hazard:.2f}_Y{systemic:.2f}_S{satellite:.2f}_NOCASH",
                    hazard, 0.75, systemic, 0.55, satellite, "NONE",
                ))
                policies.append(Policy(
                    f"SEQ_H{hazard:.2f}_Y{systemic:.2f}_S{satellite:.2f}_C50",
                    hazard, 0.75, systemic, 0.55, satellite, "C50",
                ))
                policies.append(Policy(
                    f"SEQ_H{hazard:.2f}_Y{systemic:.2f}_S{satellite:.2f}_C100",
                    hazard, 0.75, systemic, 0.55, satellite, "C100",
                ))
    return policies


def event_actions(rows: pd.DataFrame, policy: Policy) -> pd.DataFrame:
    rows = rows.sort_values("score_date").copy()
    current = "FLIP"
    candidate = "FLIP"
    candidate_count = 0
    release_count = 0
    cooldown = 0
    actions = []
    for row in rows.itertuples(index=False):
        hazard = float(row.p_y_leader_drop5_2)
        severe = float(row.p_y_leader_drop10_4)
        recovery = float(row.p_y_recover_fire5)
        systemic = float(row.p_y_systemic_drop5_2)
        satellite = float(row.p_y_sat_beats5)
        desired = "FLIP"
        if policy.cash_mode != "NONE" and systemic >= policy.systemic_hi and severe >= policy.severe_hi:
            desired = "CASH100" if policy.cash_mode == "C100" else "CASH50"
        elif hazard >= policy.hazard_hi and recovery <= policy.recovery_veto and satellite >= policy.satellite_hi:
            desired = "SWAP"
        if desired != current:
            if desired == candidate:
                candidate_count += 1
            else:
                candidate = desired
                candidate_count = 1
            if candidate_count >= policy.confirm_closes and cooldown <= 0:
                current = desired
                cooldown = policy.cooldown
                candidate_count = 0
                release_count = 0
        else:
            candidate = current
            candidate_count = 0
        if current in {"CASH50", "CASH100", "SWAP"}:
            safe = (
                hazard < max(0.0, policy.hazard_hi - policy.exit_margin)
                and systemic < max(0.0, policy.systemic_hi - policy.exit_margin)
            )
            release_count = release_count + 1 if safe else 0
            if release_count >= policy.release_closes and cooldown <= 0:
                current = "FLIP"
                release_count = 0
                cooldown = policy.cooldown
        actions.append(current)
        cooldown = max(0, cooldown - 1)
    result = rows[["pair_key", "score_date", "next_action_date"]].copy()
    result["action"] = actions
    return result


def all_event_actions(predictions: pd.DataFrame, policy: Policy) -> pd.DataFrame:
    """Run the state machine once across a pair-key-sorted array.

    This is equivalent to calling ``event_actions`` for every pair, but avoids
    thousands of tiny DataFrame copies for each policy in the threshold grid.
    """
    ordered = predictions.sort_values(["pair_key", "score_date"]).reset_index(drop=True)
    pair_keys = ordered["pair_key"].to_numpy(str)
    hazard_values = ordered["p_y_leader_drop5_2"].to_numpy(float)
    severe_values = ordered["p_y_leader_drop10_4"].to_numpy(float)
    recovery_values = ordered["p_y_recover_fire5"].to_numpy(float)
    systemic_values = ordered["p_y_systemic_drop5_2"].to_numpy(float)
    satellite_values = ordered["p_y_sat_beats5"].to_numpy(float)
    actions: list[str] = []
    previous_key = ""
    current = "FLIP"
    candidate = "FLIP"
    candidate_count = 0
    release_count = 0
    cooldown = 0
    for index, pair_key in enumerate(pair_keys):
        if pair_key != previous_key:
            previous_key = pair_key
            current = "FLIP"
            candidate = "FLIP"
            candidate_count = 0
            release_count = 0
            cooldown = 0
        hazard_value = hazard_values[index]
        severe_value = severe_values[index]
        recovery_value = recovery_values[index]
        systemic_value = systemic_values[index]
        satellite_value = satellite_values[index]
        desired = "FLIP"
        if (
            policy.cash_mode != "NONE"
            and systemic_value >= policy.systemic_hi
            and severe_value >= policy.severe_hi
        ):
            desired = "CASH100" if policy.cash_mode == "C100" else "CASH50"
        elif (
            hazard_value >= policy.hazard_hi
            and recovery_value <= policy.recovery_veto
            and satellite_value >= policy.satellite_hi
        ):
            desired = "SWAP"
        if desired != current:
            if desired == candidate:
                candidate_count += 1
            else:
                candidate = desired
                candidate_count = 1
            if candidate_count >= policy.confirm_closes and cooldown <= 0:
                current = desired
                cooldown = policy.cooldown
                candidate_count = 0
                release_count = 0
        else:
            candidate = current
            candidate_count = 0
        if current in {"CASH50", "CASH100", "SWAP"}:
            safe = (
                hazard_value < max(0.0, policy.hazard_hi - policy.exit_margin)
                and systemic_value < max(0.0, policy.systemic_hi - policy.exit_margin)
            )
            release_count = release_count + 1 if safe else 0
            if release_count >= policy.release_closes and cooldown <= 0:
                current = "FLIP"
                release_count = 0
                cooldown = policy.cooldown
        actions.append(current)
        cooldown = max(0, cooldown - 1)
    result = ordered[["pair_key", "score_date", "next_action_date"]].copy()
    result["action"] = actions
    return result


def make_action_schedule(
    mapped_events: pd.DataFrame,
    predictions: pd.DataFrame,
    policy: Policy,
    dates: pd.DatetimeIndex,
) -> tuple[np.ndarray, pd.DataFrame]:
    schedule = np.zeros((500, len(dates)), dtype=np.int8)
    action_map = {"FLIP": 1, "SWAP": 2, "CASH50": 3, "CASH100": 4}
    decisions = []
    all_actions = all_event_actions(predictions, policy)
    pair_action_cache = {key: frame for key, frame in all_actions.groupby("pair_key", sort=False)}
    for event in mapped_events.itertuples(index=False):
        basket = int(event.basket)
        start = safe_loc(dates, event.action_date, "left")
        exit_pos = safe_loc(dates, event.exit_date, "left")
        if start >= len(dates) or start >= exit_pos:
            continue
        schedule[basket, start:exit_pos] = 1
        selected = pair_action_cache.get(event.pair_key)
        if selected is None:
            continue
        for row in selected.itertuples(index=False):
            action_pos = safe_loc(dates, row.next_action_date, "left")
            if action_pos >= exit_pos:
                continue
            schedule[basket, action_pos:exit_pos] = action_map[row.action]
            decisions.append({
                "pair_key": event.pair_key,
                "basket": basket,
                "score_date": row.score_date,
                "action_date": row.next_action_date,
                "action": row.action,
                "policy": policy.name,
            })
    return schedule, pd.DataFrame(decisions)


def build_daily_state(
    state: pd.DataFrame,
    exits: pd.DataFrame,
    dates: pd.DatetimeIndex,
    tickers: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    ticker_index = {ticker: index for index, ticker in enumerate(tickers)}
    d1 = np.full((500, len(dates)), -1, dtype=np.int16)
    d2 = np.full((500, len(dates)), -1, dtype=np.int16)
    base_weight = np.ones((500, len(dates)), dtype=float)
    month_start = np.zeros(len(dates), dtype=np.uint8)
    exit_map = exits.set_index("signal_date")["exit_date"].to_dict()
    for signal_date, month in state.groupby("signal_date", sort=True):
        if signal_date not in exit_map:
            continue
        entry = safe_loc(dates, signal_date, "right")
        exit_pos = safe_loc(dates, exit_map[signal_date], "left")
        if entry >= len(dates) or entry >= exit_pos:
            continue
        month_start[entry] = 1
        for row in month.itertuples(index=False):
            basket = int(row.basket)
            d1[basket, entry:exit_pos] = ticker_index.get(str(row.leader), -1)
            d2[basket, entry:exit_pos] = ticker_index.get(str(row.sat), -1)
            base_weight[basket, entry:exit_pos] = float(row.legacy_w1)
    return d1, d2, base_weight, month_start


def simulate_controller(
    daily_top1: np.ndarray,
    daily_top2: np.ndarray,
    daily_weight: np.ndarray,
    month_start: np.ndarray,
    action_code: np.ndarray,
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
    cost: float,
    slippage: float,
) -> tuple[np.ndarray, np.ndarray]:
    baskets, days = daily_top1.shape
    equity = np.ones((baskets, days))
    turnover = np.zeros((baskets, days))
    ticker1 = np.full(baskets, -1, dtype=np.int16)
    ticker2 = np.full(baskets, -1, dtype=np.int16)
    units1 = np.zeros(baskets)
    units2 = np.zeros(baskets)
    bil_units = np.zeros(baskets)
    shv_units = np.zeros(baskets)
    cash = np.zeros(baskets)
    previous_weight1 = np.full(baskets, -1.0)
    previous_fraction = np.full(baskets, -1.0)
    cooldown = np.zeros(baskets, dtype=np.int16)
    rows = np.arange(baskets)

    def held_price(values: np.ndarray, day: int, ticker: np.ndarray) -> np.ndarray:
        valid = ticker >= 0
        out = np.zeros(baskets)
        out[valid] = values[day, ticker[valid]]
        return out

    for day in range(days):
        current_open1 = held_price(open_values, day, ticker1)
        current_open2 = held_price(open_values, day, ticker2)
        value = (
            cash
            + units1 * current_open1
            + units2 * current_open2
            + bil_units * open_values[day, bil_index]
            + shv_units * open_values[day, shv_index]
        )
        if day == 0:
            value = np.where(value == 0, 1.0, value)
        if day == days - 1:
            equity[:, day] = value
            break

        new_ticker1 = daily_top1[:, day]
        new_ticker2 = daily_top2[:, day]
        base_w1 = daily_weight[:, day]
        code = action_code[:, day]
        weight1 = base_w1.copy()
        controller_fraction = np.ones(baskets)
        weight1[np.isin(code, [1, 3, 4])] = 0.25
        weight1[code == 2] = 0.0
        controller_fraction[code == 3] = 0.50
        controller_fraction[code == 4] = 0.0
        weight1[new_ticker2 == new_ticker1] = 1.0

        valid1 = new_ticker1 >= 0
        valid2 = new_ticker2 >= 0
        safe1 = np.where(valid1, new_ticker1, 0)
        safe2 = np.where(valid2, new_ticker2, 0)
        prior_hazard1 = valid1 & (hazard[day, safe1] | severe[day, safe1])
        prior_hazard2 = valid2 & (hazard[day, safe2] | severe[day, safe2])
        portfolio_gap = weight1 * gaps[day, safe1] + (1.0 - weight1) * gaps[day, safe2]
        systemic = valid1 & (
            ((portfolio_gap <= -0.032) & (universe_down_1pct[day] >= 0.70))
            | ((portfolio_gap <= -0.044) & (universe_negative[day] >= 0.75))
        )
        governor_fraction = np.ones(baskets)
        governor_fraction[~valid1] = 0.0
        governor_fraction[systemic] = 0.25
        cooldown[systemic] = 3
        active_cooldown = (~systemic) & (cooldown > 0)
        governor_fraction[active_cooldown] = 0.25
        cooldown[active_cooldown] -= 1
        risky_fraction = np.minimum(governor_fraction, controller_fraction)
        risky_weight1 = risky_fraction * weight1
        risky_weight2 = risky_fraction * (1.0 - weight1)
        defensive_weight = 1.0 - risky_fraction

        rebalance = (
            (ticker1 != new_ticker1)
            | (ticker2 != new_ticker2)
            | (np.abs(previous_weight1 - weight1) > 1e-12)
            | (np.abs(previous_fraction - risky_fraction) > 1e-12)
            | (cash > 1e-14)
            | (day == 0)
            | (month_start[day] > 0)
        )
        if rebalance.any():
            safe_value = np.maximum(value, EPS)
            current1 = units1 * current_open1 / safe_value
            current2 = units2 * current_open2 / safe_value
            current_bil = bil_units * open_values[day, bil_index] / safe_value
            current_shv = shv_units * open_values[day, shv_index] / safe_value
            current_cash = cash / safe_value
            tv = 0.5 * (
                np.abs(current_cash)
                + np.abs(current_bil - defensive_weight * 0.5)
                + np.abs(current_shv - defensive_weight * 0.5)
            )
            tv += 0.5 * np.where(
                ticker1 != new_ticker1,
                np.abs(current1) + risky_weight1,
                np.abs(current1 - risky_weight1),
            )
            tv += 0.5 * np.where(
                ticker2 != new_ticker2,
                np.abs(current2) + risky_weight2,
                np.abs(current2 - risky_weight2),
            )
            value[rebalance] *= 1.0 - cost * tv[rebalance]
            turnover[rebalance, day] = tv[rebalance]
            ticker1[rebalance] = new_ticker1[rebalance]
            ticker2[rebalance] = new_ticker2[rebalance]
            new_open1 = held_price(open_values, day, ticker1)
            new_open2 = held_price(open_values, day, ticker2)
            units1[rebalance] = np.where(
                (ticker1[rebalance] >= 0) & (risky_weight1[rebalance] > 0),
                risky_weight1[rebalance] * value[rebalance] / np.maximum(new_open1[rebalance], EPS),
                0.0,
            )
            units2[rebalance] = np.where(
                (ticker2[rebalance] >= 0) & (risky_weight2[rebalance] > 0),
                risky_weight2[rebalance] * value[rebalance] / np.maximum(new_open2[rebalance], EPS),
                0.0,
            )
            bil_units[rebalance] = defensive_weight[rebalance] * 0.5 * value[rebalance] / open_values[day, bil_index]
            shv_units[rebalance] = defensive_weight[rebalance] * 0.5 * value[rebalance] / open_values[day, shv_index]
            cash[rebalance] = 0.0
            previous_weight1[rebalance] = weight1[rebalance]
            previous_fraction[rebalance] = risky_fraction[rebalance]

        safe_ticker1 = np.where(ticker1 >= 0, ticker1, 0)
        safe_ticker2 = np.where(ticker2 >= 0, ticker2, 0)
        stop_permission = systemic | (universe_down_1pct[day] >= 0.55)
        stop_price1 = previous_close[day, safe_ticker1] * (1.0 - 0.055)
        fill1 = np.where(
            open_values[day, safe_ticker1] <= stop_price1,
            open_values[day, safe_ticker1],
            np.where(low_values[day, safe_ticker1] <= stop_price1, stop_price1 * (1.0 - slippage), 0.0),
        )
        hit1 = (ticker1 >= 0) & (units1 > 0) & prior_hazard1 & stop_permission & (fill1 > 0)
        cash[hit1] += units1[hit1] * fill1[hit1] * (1.0 - cost)
        units1[hit1] = 0.0
        cooldown[hit1] = np.maximum(cooldown[hit1], 3)
        stop_price2 = previous_close[day, safe_ticker2] * (1.0 - 0.055)
        fill2 = np.where(
            open_values[day, safe_ticker2] <= stop_price2,
            open_values[day, safe_ticker2],
            np.where(low_values[day, safe_ticker2] <= stop_price2, stop_price2 * (1.0 - slippage), 0.0),
        )
        hit2 = (ticker2 >= 0) & (units2 > 0) & prior_hazard2 & stop_permission & (fill2 > 0)
        cash[hit2] += units2[hit2] * fill2[hit2] * (1.0 - cost)
        units2[hit2] = 0.0
        cooldown[hit2] = np.maximum(cooldown[hit2], 3)

        next_open1 = held_price(open_values, day + 1, ticker1)
        next_open2 = held_price(open_values, day + 1, ticker2)
        equity[:, day] = (
            cash
            + units1 * next_open1
            + units2 * next_open2
            + bil_units * open_values[day + 1, bil_index]
            + shv_units * open_values[day + 1, shv_index]
        )
    return equity, turnover


def path_statistics(path: np.ndarray, dates: pd.DatetimeIndex, start: str, end: str) -> dict[str, np.ndarray]:
    mask = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
    x = path[:, mask].copy()
    x /= x[:, [0]]
    gross = x[:, 1:] / x[:, :-1]
    years = max(gross.shape[1] / 252, 1 / 252)
    cagr = np.exp(np.log(gross).sum(axis=1) / years) - 1
    wealth = np.cumprod(gross, axis=1)
    maxdd = (wealth / np.maximum.accumulate(wealth, axis=1) - 1).min(axis=1)
    returns = gross - 1
    sharpe = np.sqrt(252) * returns.mean(axis=1) / returns.std(axis=1, ddof=1)
    calmar = cagr / np.maximum(-maxdd, EPS)
    return {"cagr": cagr, "maxdd": maxdd, "sharpe": sharpe, "calmar": calmar}


def comparison_rows(
    reference: np.ndarray,
    candidate: np.ndarray,
    dates: pd.DatetimeIndex,
    strategy: str,
) -> list[dict]:
    periods = {
        "DEV_2021_2022": ("2021-01-01", "2022-12-31"),
        "2021": ("2021-01-01", "2021-12-31"),
        "2022": ("2022-01-01", "2022-12-31"),
        "HOLDOUT_2023_2026_EXPLORED": ("2023-01-01", "2026-07-01"),
        "2023": ("2023-01-01", "2023-12-31"),
        "2024": ("2024-01-01", "2024-12-31"),
        "2025": ("2025-01-01", "2025-12-31"),
        "2026": ("2026-01-01", "2026-07-01"),
    }
    rows = []
    for period, (start, end) in periods.items():
        base = path_statistics(reference, dates, start, end)
        cand = path_statistics(candidate, dates, start, end)
        rows.append({
            "strategy": strategy,
            "period": period,
            "cagr_mean": float(np.nanmean(cand["cagr"])),
            "maxdd_mean": float(np.nanmean(cand["maxdd"])),
            "sharpe_mean": float(np.nanmean(cand["sharpe"])),
            "calmar_mean": float(np.nanmean(cand["calmar"])),
            "delta_cagr_pp_vs_flip": float(100 * np.nanmean(cand["cagr"] - base["cagr"])),
            "delta_maxdd_pp_vs_flip": float(100 * np.nanmean(cand["maxdd"] - base["maxdd"])),
            "delta_sharpe_vs_flip": float(np.nanmean(cand["sharpe"] - base["sharpe"])),
            "delta_calmar_vs_flip": float(np.nanmean(cand["calmar"] - base["calmar"])),
            "cagr_win_rate": float(np.nanmean(cand["cagr"] > base["cagr"])),
            "maxdd_win_rate": float(np.nanmean(cand["maxdd"] > base["maxdd"])),
        })
    return rows


def bootstrap_paths(
    reference: np.ndarray,
    candidate: np.ndarray,
    dates: pd.DatetimeIndex,
    reps: int = 4000,
) -> pd.DataFrame:
    mask = (dates >= pd.Timestamp("2023-01-01")) & (dates <= pd.Timestamp("2026-07-01"))
    date_slice = dates[mask]
    base_gross = reference[:, mask][:, 1:] / reference[:, mask][:, :-1]
    cand_gross = candidate[:, mask][:, 1:] / candidate[:, mask][:, :-1]
    rng = np.random.default_rng(20260824)
    base = path_statistics(reference, dates, "2023-01-01", "2026-07-01")
    cand = path_statistics(candidate, dates, "2023-01-01", "2026-07-01")
    metrics = {
        "delta_cagr_pp": 100 * (cand["cagr"] - base["cagr"]),
        "delta_maxdd_pp": 100 * (cand["maxdd"] - base["maxdd"]),
        "delta_sharpe": cand["sharpe"] - base["sharpe"],
        "delta_calmar": cand["calmar"] - base["calmar"],
    }
    rows = []
    indices = rng.integers(0, reference.shape[0], size=(reps, reference.shape[0]))
    for name, values in metrics.items():
        draws = values[indices].mean(axis=1)
        rows.append({
            "test": "paired_basket_bootstrap", "metric": name, "reps": reps,
            "mean": float(draws.mean()), "ci95_low": float(np.quantile(draws, 0.025)),
            "ci95_high": float(np.quantile(draws, 0.975)), "prob_gt_zero": float((draws > 0).mean()),
        })
    return_dates = date_slice[1:]
    month_labels = return_dates.to_period("M")
    month_blocks = [np.where(month_labels == month)[0] for month in pd.Index(month_labels.unique())]
    base_portfolio = (base_gross - 1).mean(axis=0)
    cand_portfolio = (cand_gross - 1).mean(axis=0)

    def scalar(returns: np.ndarray) -> tuple[float, float, float, float]:
        gross = 1 + returns
        years = max(len(gross) / 252, 1 / 252)
        cagr = float(np.exp(np.log(gross).sum() / years) - 1)
        wealth = np.cumprod(gross)
        maxdd = float((wealth / np.maximum.accumulate(wealth) - 1).min())
        sharpe = float(np.sqrt(252) * returns.mean() / returns.std(ddof=1))
        return cagr, maxdd, sharpe, cagr / max(-maxdd, EPS)

    draws = np.empty((reps, 4))
    for iteration in range(reps):
        sampled = rng.integers(0, len(month_blocks), size=len(month_blocks))
        idx = np.concatenate([month_blocks[i] for i in sampled])
        b = scalar(base_portfolio[idx])
        c = scalar(cand_portfolio[idx])
        draws[iteration] = [100 * (c[0] - b[0]), 100 * (c[1] - b[1]), c[2] - b[2], c[3] - b[3]]
    for column, name in enumerate(["delta_cagr_pp", "delta_maxdd_pp", "delta_sharpe", "delta_calmar"]):
        values = draws[:, column]
        rows.append({
            "test": "calendar_month_block_bootstrap", "metric": name, "reps": reps,
            "mean": float(values.mean()), "ci95_low": float(np.quantile(values, 0.025)),
            "ci95_high": float(np.quantile(values, 0.975)), "prob_gt_zero": float((values > 0).mean()),
        })
    return pd.DataFrame(rows)


def audit_data(
    mapped: pd.DataFrame,
    pair_events: pd.DataFrame,
    panel: pd.DataFrame,
    features: list[str],
) -> dict:
    return {
        "mapped_fire_events": int(len(mapped)),
        "unique_pair_events": int(len(pair_events)),
        "sequential_rows": int(len(panel)),
        "sequential_unique_score_dates": int(panel["score_date"].nunique()),
        "feature_count": int(len(features)),
        "mapping_coverage_since_2020": float(len(mapped) / max(1, (pd.read_csv(Path("orthogonal_fire_output/ORTHOGONAL_FIRE_PANEL.csv"))["signal_date"].str[:4].astype(int) >= 2020).sum())),
        "duplicate_pair_score_rows": int(panel.duplicated(["pair_key", "score_date"]).sum()),
        "next_open_causality_share": float((panel["next_action_date"] > panel["score_date"]).mean()),
        "outcome_before_exit_share": float((panel["next_action_date"] < panel["exit_date"]).mean()),
        "feature_missing_share": float(panel[features].isna().mean().mean()),
        "development_rows": int(panel["score_date"].dt.year.between(2020, 2022).sum()),
        "explored_holdout_rows": int((panel["score_date"].dt.year >= 2023).sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("sequential_dd_output"))
    parser.add_argument("--bootstrap-reps", type=int, default=4000)
    parser.add_argument("--policy-limit", type=int, default=0, help="Optional smoke-test limit; 0 runs the full grid")
    args = parser.parse_args()
    root = args.root.resolve()
    output = (root / args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    frozen = np.load(root / "risk_packages/action_frontier/ARMED_ACTION_FRONTIER_PATHS.npz")
    all_dates = pd.DatetimeIndex(frozen["dates"])
    state = pd.read_csv(root / "library_inputs/STATE_PANEL.csv")
    state["signal_date"] = pd.to_datetime(state["signal_date"])
    first_signal = state["signal_date"].min()
    start = safe_loc(all_dates, first_signal, "right")
    dates = all_dates[start:]
    prices = load_prices(root / "library_inputs/armed/data/armed_risk_v2_20260702", dates)
    mapped, pair_events = build_pair_events(root)
    mapped = mapped[mapped["signal_date"] >= first_signal].copy()
    pair_events = pair_events[pair_events["signal_date"] >= first_signal].copy()

    raw_orthogonal, source_manifest = load_official_series(output / "raw")
    orthogonal = true_orthogonal_features(raw_orthogonal)
    panel_path = output / "SEQUENTIAL_EVENT_DAY_PANEL.parquet"
    prediction_path = output / "SEQUENTIAL_PREDICTIONS.parquet"
    scorecard_path = output / "SEQUENTIAL_MODEL_SCORECARD.csv"
    if panel_path.exists() and prediction_path.exists() and scorecard_path.exists():
        panel = pd.read_parquet(panel_path)
        predictions = pd.read_parquet(prediction_path)
        model_scorecard = pd.read_csv(scorecard_path)
        excluded = {
            "pair_key", "signal_date", "feature_date", "first_action_date", "score_date",
            "next_action_date", "exit_date", "leader", "sat", "multiplicity", "date_weight",
            "leader_terminal5", "sat_terminal5", "cash_terminal5", *TARGETS,
        }
        features = [
            column for column in panel.columns
            if column not in excluded and pd.api.types.is_numeric_dtype(panel[column])
        ]
        selected_models = {}
        for target in TARGETS:
            selected_models[target] = str(
                model_scorecard[
                    model_scorecard["period"].eq("2021")
                    & model_scorecard["target"].eq(target)
                ]
                .sort_values(["auc", "model"], ascending=[False, False])
                .iloc[0]["model"]
            )
    else:
        panel, features = build_sequential_panel(pair_events, prices, orthogonal)
        panel.to_parquet(panel_path, index=False)
        panel.head(250).to_csv(output / "SEQUENTIAL_EVENT_DAY_PANEL_PREVIEW.csv", index=False)
        model_scorecard, predictions, selected_models = score_models(panel, features)
        model_scorecard.to_csv(scorecard_path, index=False)
        predictions.to_parquet(prediction_path, index=False)
    for target, model_name in selected_models.items():
        predictions[f"p_{target}"] = predictions[f"p_{target}_{model_name.lower()}"]

    exit_calendar = pd.read_csv(root / "library_inputs/RISK_LEARNING_PANEL.csv", usecols=["signal_date", "exit_date"])
    exit_calendar["signal_date"] = pd.to_datetime(exit_calendar["signal_date"])
    exit_calendar["exit_date"] = pd.to_datetime(exit_calendar["exit_date"])
    exit_calendar = exit_calendar.drop_duplicates()
    tickers = list(prices["OPEN"].columns)
    d1, d2, daily_weight, month_start = build_daily_state(state, exit_calendar, dates, tickers)
    open_values = prices["OPEN"].to_numpy(float)
    low_values = prices["LOW"].to_numpy(float)
    close_values = prices["CLOSE"].to_numpy(float)
    previous_close = np.empty_like(close_values)
    previous_close[0] = open_values[0]
    previous_close[1:] = close_values[:-1]
    gaps = np.zeros_like(open_values)
    gaps[1:] = open_values[1:] / close_values[:-1] - 1
    universe_down = np.mean(gaps < -0.01, axis=1)
    universe_negative = np.mean(gaps < 0, axis=1)
    close_frame = prices["CLOSE"]
    momentum3 = close_frame / close_frame.shift(3) - 1
    momentum5 = close_frame / close_frame.shift(5) - 1
    sma10 = close_frame.rolling(10).mean()
    sma20 = close_frame.rolling(20).mean()
    hazard = (((close_frame < sma10) & (momentum3 < 0)) | ((close_frame < sma20) & (momentum5 < -0.015))).shift(1, fill_value=False).to_numpy(bool)
    severe = ((momentum5 < -0.04) | ((close_frame < sma20) & (momentum3 < -0.025))).shift(1, fill_value=False).to_numpy(bool)
    ticker_index = {ticker: index for index, ticker in enumerate(tickers)}

    baseline_policy = Policy("FLIP_ONLY", 1.01, 1.01, 1.01, -0.01, 1.01, "NONE")
    baseline_schedule, baseline_decisions = make_action_schedule(mapped, predictions, baseline_policy, dates)
    baseline_path, baseline_turnover = simulate_controller(
        d1, d2, daily_weight, month_start, baseline_schedule,
        open_values, low_values, close_values, previous_close, gaps,
        universe_down, universe_negative, hazard, severe,
        ticker_index["BIL"], ticker_index["SHV"], 0.001, 0.001,
    )
    reference_flip = frozen["FLIP"][:, start:]
    normalized_rebuilt = baseline_path / baseline_path[:, [0]]
    normalized_reference = reference_flip / reference_flip[:, [0]]
    parity_error = np.abs(normalized_rebuilt - normalized_reference)
    parity = {
        "start_date": str(dates.min().date()),
        "max_abs_equity_error": float(parity_error.max()),
        "mean_abs_equity_error": float(parity_error.mean()),
        "final_mean_rebuilt": float(normalized_rebuilt[:, -1].mean()),
        "final_mean_reference": float(normalized_reference[:, -1].mean()),
    }
    ref_stats = path_statistics(normalized_reference, dates, "2020-02-01", "2026-07-01")
    rebuilt_stats = path_statistics(normalized_rebuilt, dates, "2020-02-01", "2026-07-01")
    parity.update({
        "cagr_gap_pp": float(100 * np.nanmean(rebuilt_stats["cagr"] - ref_stats["cagr"])),
        "maxdd_gap_pp": float(100 * np.nanmean(rebuilt_stats["maxdd"] - ref_stats["maxdd"])),
        "sharpe_gap": float(np.nanmean(rebuilt_stats["sharpe"] - ref_stats["sharpe"])),
    })
    parity["status"] = "ACCEPTED_INCREMENTAL_ANCHOR_PARITY" if (
        abs(parity["cagr_gap_pp"]) <= 0.05
        and abs(parity["maxdd_gap_pp"]) <= 0.08
        and abs(parity["sharpe_gap"]) <= 0.002
    ) else "REJECTED_PARITY"
    parity["official_anchor_rule"] = "official FLIP * (candidate rebuilt / FLIP rebuilt)"
    parity["official_flip_only_anchor_max_abs_error"] = 0.0
    (output / "SEQUENTIAL_ENGINE_PARITY.json").write_text(json.dumps(parity, indent=2) + "\n", encoding="utf-8")
    if parity["status"] != "ACCEPTED_INCREMENTAL_ANCHOR_PARITY":
        raise RuntimeError(f"Sequential engine parity failed: {parity}")

    policies = policy_grid()
    if args.policy_limit > 0:
        policies = policies[: args.policy_limit]
    grid_rows = []
    paths: dict[str, np.ndarray] = {"FLIP_REBUILT": baseline_path}
    decision_cache: dict[str, pd.DataFrame] = {"FLIP_ONLY": baseline_decisions}
    payloads = []
    for number, policy in enumerate(policies, start=1):
        print(f"schedule {number}/{len(policies)} {policy.name}", flush=True)
        schedule, decisions = make_action_schedule(mapped, predictions, policy, dates)
        payloads.append((policy, schedule, decisions))
    batch_size = 8
    for batch_start in range(0, len(payloads), batch_size):
        batch = payloads[batch_start : batch_start + batch_size]
        print(f"simulate policies {batch_start + 1}-{batch_start + len(batch)}/{len(payloads)}", flush=True)
        stacked_schedule = np.vstack([item[1] for item in batch])
        repeats = len(batch)
        candidate_stack, turnover_stack = simulate_controller(
            np.tile(d1, (repeats, 1)),
            np.tile(d2, (repeats, 1)),
            np.tile(daily_weight, (repeats, 1)),
            month_start,
            stacked_schedule,
            open_values, low_values, close_values, previous_close, gaps,
            universe_down, universe_negative, hazard, severe,
            ticker_index["BIL"], ticker_index["SHV"], 0.001, 0.001,
        )
        candidate_stack = candidate_stack.reshape(repeats, 500, len(dates))
        turnover_stack = turnover_stack.reshape(repeats, 500, len(dates))
        for offset, (policy, _schedule, decisions) in enumerate(batch):
            candidate = candidate_stack[offset]
            turnover = turnover_stack[offset]
            anchored_candidate = reference_flip * (candidate / np.maximum(baseline_path, EPS))
            rows = comparison_rows(reference_flip, anchored_candidate, dates, policy.name)
            for row in rows:
                if len(decisions):
                    if row["period"] == "DEV_2021_2022":
                        action_sample = decisions[decisions["score_date"].dt.year.between(2021, 2022)]
                    elif row["period"] == "HOLDOUT_2023_2026_EXPLORED":
                        action_sample = decisions[decisions["score_date"].dt.year >= 2023]
                    else:
                        action_sample = decisions[decisions["score_date"].dt.year.eq(int(row["period"]))]
                    action_counts = action_sample["action"].value_counts(normalize=True).to_dict()
                else:
                    action_counts = {}
                row.update({
                    "hazard_hi": policy.hazard_hi,
                    "severe_hi": policy.severe_hi,
                    "systemic_hi": policy.systemic_hi,
                    "recovery_veto": policy.recovery_veto,
                    "satellite_hi": policy.satellite_hi,
                    "cash_mode": policy.cash_mode,
                    "cash_decision_rate": float(action_counts.get("CASH50", 0) + action_counts.get("CASH100", 0)),
                    "swap_decision_rate": float(action_counts.get("SWAP", 0)),
                    "mean_daily_turnover": float(turnover.mean()),
                })
            grid_rows.extend(rows)
            if policy.name == "FLIP_ONLY":
                paths[policy.name] = candidate
                decision_cache[policy.name] = decisions
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(output / "SEQUENTIAL_POLICY_GRID.csv", index=False)

    development = grid[grid["period"].isin(["DEV_2021_2022", "2021", "2022"])].copy()
    wide = development.pivot(index="strategy", columns="period")
    candidates = []
    for policy in policies:
        q = development[development["strategy"].eq(policy.name)].set_index("period")
        if not {"DEV_2021_2022", "2021", "2022"}.issubset(q.index):
            continue
        eligible = (
            q.loc["2022", "delta_cagr_pp_vs_flip"] >= -0.25
            and q.loc["2022", "cash_decision_rate"] <= 0.10
            and min(q.loc["2021", "delta_maxdd_pp_vs_flip"], q.loc["2022", "delta_maxdd_pp_vs_flip"]) >= -0.05
        )
        score = (
            q.loc["2022", "delta_calmar_vs_flip"]
            + 0.25 * q.loc["2022", "delta_sharpe_vs_flip"]
            + 0.02 * min(q.loc["2021", "delta_maxdd_pp_vs_flip"], q.loc["2022", "delta_maxdd_pp_vs_flip"])
            + 0.10 * q.loc["2021", "delta_calmar_vs_flip"]
        )
        candidates.append({
            "strategy": policy.name,
            "eligible": bool(eligible),
            "selection_score": float(score),
            "dev_delta_cagr_pp": float(q.loc["DEV_2021_2022", "delta_cagr_pp_vs_flip"]),
            "dev_delta_maxdd_pp": float(q.loc["DEV_2021_2022", "delta_maxdd_pp_vs_flip"]),
            "dev_delta_sharpe": float(q.loc["DEV_2021_2022", "delta_sharpe_vs_flip"]),
            "dev_delta_calmar": float(q.loc["DEV_2021_2022", "delta_calmar_vs_flip"]),
            "worst_year_delta_maxdd_pp": float(min(q.loc["2021", "delta_maxdd_pp_vs_flip"], q.loc["2022", "delta_maxdd_pp_vs_flip"])),
            "cash_decision_rate": float(q.loc["DEV_2021_2022", "cash_decision_rate"]),
            "delta_cagr_pp_2021": float(q.loc["2021", "delta_cagr_pp_vs_flip"]),
            "delta_maxdd_pp_2021": float(q.loc["2021", "delta_maxdd_pp_vs_flip"]),
            "delta_calmar_2021": float(q.loc["2021", "delta_calmar_vs_flip"]),
            "delta_cagr_pp_2022": float(q.loc["2022", "delta_cagr_pp_vs_flip"]),
            "delta_maxdd_pp_2022": float(q.loc["2022", "delta_maxdd_pp_vs_flip"]),
            "delta_calmar_2022": float(q.loc["2022", "delta_calmar_vs_flip"]),
            "cash_decision_rate_2022": float(q.loc["2022", "cash_decision_rate"]),
        })
    selection = pd.DataFrame(candidates).sort_values(["eligible", "selection_score"], ascending=False)
    selection.to_csv(output / "SEQUENTIAL_POLICY_SELECTION.csv", index=False)
    best_name = str(selection.iloc[0]["strategy"])
    best_policy = next(policy for policy in policies if policy.name == best_name)
    best_schedule, best_decisions = make_action_schedule(mapped, predictions, best_policy, dates)
    best_path, best_turnover = simulate_controller(
        d1, d2, daily_weight, month_start, best_schedule,
        open_values, low_values, close_values, previous_close, gaps,
        universe_down, universe_negative, hazard, severe,
        ticker_index["BIL"], ticker_index["SHV"], 0.001, 0.001,
    )
    best_path_anchored = reference_flip * (best_path / np.maximum(baseline_path, EPS))
    scorecard = pd.DataFrame(comparison_rows(reference_flip, best_path_anchored, dates, best_name))
    scorecard.to_csv(output / "SEQUENTIAL_FINAL_SCORECARD.csv", index=False)
    best_decisions.to_csv(output / "SEQUENTIAL_FINAL_DECISIONS.csv", index=False)
    bootstrap = bootstrap_paths(reference_flip, best_path_anchored, dates, reps=args.bootstrap_reps)
    bootstrap.to_csv(output / "SEQUENTIAL_BOOTSTRAP.csv", index=False)

    cost_rows = []
    for cost in [0.0010, 0.0015, 0.0020]:
        stressed, _ = simulate_controller(
            d1, d2, daily_weight, month_start, best_schedule,
            open_values, low_values, close_values, previous_close, gaps,
            universe_down, universe_negative, hazard, severe,
            ticker_index["BIL"], ticker_index["SHV"], cost, 0.001,
        )
        stressed_base, _ = simulate_controller(
            d1, d2, daily_weight, month_start, baseline_schedule,
            open_values, low_values, close_values, previous_close, gaps,
            universe_down, universe_negative, hazard, severe,
            ticker_index["BIL"], ticker_index["SHV"], cost, 0.001,
        )
        q = comparison_rows(stressed_base, stressed, dates, best_name)
        for row in q:
            if row["period"] == "HOLDOUT_2023_2026_EXPLORED":
                row["one_way_cost"] = cost
                cost_rows.append(row)
    pd.DataFrame(cost_rows).to_csv(output / "SEQUENTIAL_COST_STRESS.csv", index=False)

    np.savez_compressed(
        output / "SEQUENTIAL_DD_PATHS.npz",
        dates=dates.values,
        FLIP_REBUILT=baseline_path,
        SEQUENTIAL_DD_CONTROLLER_REBUILT=best_path,
        SEQUENTIAL_DD_CONTROLLER=best_path_anchored,
        OFFICIAL_FLIP_REFERENCE=reference_flip,
    )
    data_audit = audit_data(mapped, pair_events, panel, features)
    data_audit["status"] = "PASS" if (
        data_audit["duplicate_pair_score_rows"] == 0
        and data_audit["next_open_causality_share"] == 1.0
        and data_audit["mapping_coverage_since_2020"] >= 0.999
    ) else "FAIL"
    (output / "SEQUENTIAL_DATA_QUALITY.json").write_text(json.dumps(data_audit, indent=2) + "\n", encoding="utf-8")
    source_manifest["local_sources"] = [
        "risk_packages/action_frontier/ARMED_ACTION_FRONTIER_PATHS.npz",
        "orthogonal_fire_output/ORTHOGONAL_FIRE_PANEL.csv",
        "library_inputs/STATE_PANEL.csv",
        "library_inputs/armed/data/armed_risk_v2_20260702/{OPEN,LOW,CLOSE,VOLUME}.parquet",
    ]
    (output / "SEQUENTIAL_SOURCE_MANIFEST.json").write_text(json.dumps(source_manifest, indent=2) + "\n", encoding="utf-8")

    holdout = scorecard[scorecard["period"].eq("HOLDOUT_2023_2026_EXPLORED")].iloc[0].to_dict()
    temporal_cagr = bootstrap[(bootstrap["test"].eq("calendar_month_block_bootstrap")) & (bootstrap["metric"].eq("delta_cagr_pp"))].iloc[0].to_dict()
    temporal_dd = bootstrap[(bootstrap["test"].eq("calendar_month_block_bootstrap")) & (bootstrap["metric"].eq("delta_maxdd_pp"))].iloc[0].to_dict()
    promote = bool(
        holdout["delta_maxdd_pp_vs_flip"] > 0
        and holdout["delta_cagr_pp_vs_flip"] >= -0.25
        and holdout["delta_sharpe_vs_flip"] >= 0
        and temporal_dd["ci95_low"] >= -0.05
        and temporal_cagr["ci95_low"] >= -0.25
    )
    report = {
        "experiment": "Sequential DD Controller V1",
        "as_of": "2026-08-24",
        "baseline_status": "Titanium V2, CVX4 and FLIP remain frozen and unmodified",
        "development": "models selected on OOF 2021 (train through 2020); policy thresholds selected on OOF 2022 with a 2021 drawdown guardrail",
        "historical_holdout": "2023-2026 (explicitly explored in prior research; not pristine)",
        "selected_models": selected_models,
        "selected_policy": asdict(best_policy),
        "engine_parity": parity,
        "data_quality": data_audit,
        "holdout_scorecard": holdout,
        "bootstrap_temporal_cagr": temporal_cagr,
        "bootstrap_temporal_maxdd": temporal_dd,
        "promotion_gate_passed": promote,
        "decision": "PROMOTE_CHALLENGER" if promote else "RESEARCH_ONLY_DO_NOT_PROMOTE",
        "sources": source_manifest,
    }
    (output / "SEQUENTIAL_DD_REPORT.json").write_text(json.dumps(report, indent=2, default=float) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, default=float), flush=True)


if __name__ == "__main__":
    main()
