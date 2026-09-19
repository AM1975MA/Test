#!/usr/bin/env python3
"""Exact 500-basket replay of the sequential collapse -> TIT_R alternative rule.

Baseline: accepted ARMED_FLIP_25_75 mechanics.  The first -3% fire always moves
to 25% leader / 75% frozen satellite at the next open.  After two post-fire
closes, a frozen HGB detector may move the basket to 100% of the highest
authenticated TIT_R alternative at the following open, held to monthly exit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from titanium_breath_collapse_detector import BASE_FEATURES, SCORE_FEATURES, model_specs
from titanium_sequential_dd_controller import (
    build_daily_state, load_prices, path_statistics, safe_loc, simulate_controller,
)
from titanium_sequential_leader_state import DYNAMIC


THRESHOLD = 0.834412501765974
EVENT_KEY = ["signal_date", "trigger_date", "action_date", "exit_date", "leader", "score_date", "next_action_date"]


def causal_calls(panel: pd.DataFrame) -> pd.DataFrame:
    frame = panel.loc[
        panel["offset"].eq(2) & panel["remaining_state"].isin(["BREATH", "COLLAPSE"])
    ].copy()
    frame["year"] = pd.to_datetime(frame["next_action_date"]).dt.year
    frame["y"] = frame["remaining_state"].eq("COLLAPSE").astype(int)
    features = BASE_FEATURES + SCORE_FEATURES + DYNAMIC
    parts = []
    for year in [2021, 2022]:
        train = frame.loc[frame["year"] < year]
        test = frame.loc[frame["year"].eq(year)].copy()
        model = model_specs(features)["HGB"]
        model.fit(train[features], train["y"])
        test["p_collapse"] = model.predict_proba(test[features])[:, 1]
        parts.append(test)
    train = frame.loc[frame["year"] <= 2022]
    hold = frame.loc[frame["year"] >= 2023].copy()
    model = model_specs(features)["HGB"]
    model.fit(train[features], train["y"])
    hold["p_collapse"] = model.predict_proba(hold[features])[:, 1]
    parts.append(hold)
    pred = pd.concat(parts, ignore_index=True)
    return pred.loc[pred["p_collapse"] >= THRESHOLD].copy()


def top_alternatives(candidate_panel: pd.DataFrame) -> pd.DataFrame:
    frame = candidate_panel.copy()
    for col in EVENT_KEY:
        if "date" in col:
            frame[col] = pd.to_datetime(frame[col])
    # Ascending then tail selects the maximum causal TIT_R in every event.
    return (
        frame.sort_values(EVENT_KEY + ["TIT_R"])
        .groupby(EVENT_KEY, as_index=False)
        .tail(1)[EVENT_KEY + ["ticker", "TIT_R"]]
        .rename(columns={"ticker": "alternative", "TIT_R": "alternative_tit_r"})
    )


def action_schedules(
    dates: pd.DatetimeIndex,
    fires: pd.DataFrame,
    state: pd.DataFrame,
    calls: pd.DataFrame,
    alternatives: pd.DataFrame,
    d2: np.ndarray,
    ticker_index: dict[str, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    baseline = np.zeros((500, len(dates)), dtype=np.int8)
    candidate = np.zeros_like(baseline)
    override_d2 = d2.copy()

    mapped = fires.merge(
        state[["signal_date", "basket", "leader", "sat"]],
        on=["signal_date", "basket"], how="inner", validate="many_to_one",
    )
    for row in mapped.itertuples(index=False):
        start = safe_loc(dates, row.action_date, "left")
        end = safe_loc(dates, row.exit_date, "left")
        if start < end:
            baseline[int(row.basket), start:end] = 1
            candidate[int(row.basket), start:end] = 1

    decisions = calls.merge(alternatives, on=EVENT_KEY, how="inner", validate="one_to_one")
    decisions = decisions.merge(
        mapped[["signal_date", "action_date", "exit_date", "leader", "basket"]],
        on=["signal_date", "action_date", "exit_date", "leader"],
        how="inner", validate="one_to_many",
    )
    applied = []
    for row in decisions.itertuples(index=False):
        alt = ticker_index.get(str(row.alternative), -1)
        start = safe_loc(dates, row.next_action_date, "left")
        end = safe_loc(dates, row.exit_date, "left")
        basket = int(row.basket)
        if alt < 0 or start >= end:
            continue
        candidate[basket, start:end] = 2
        override_d2[basket, start:end] = alt
        applied.append({
            "signal_date": row.signal_date, "trigger_date": row.trigger_date,
            "initial_action_date": row.action_date, "score_date": row.score_date,
            "switch_action_date": row.next_action_date, "exit_date": row.exit_date,
            "basket": basket, "leader": row.leader, "alternative": row.alternative,
            "p_collapse": row.p_collapse, "alternative_tit_r": row.alternative_tit_r,
            "remaining_state": row.remaining_state,
        })
    return baseline, candidate, override_d2, pd.DataFrame(applied)


def score(path: np.ndarray, dates: pd.DatetimeIndex, start: str, end: str) -> dict:
    mask = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
    x = path[:, mask].copy()
    x /= x[:, [0]]
    returns = np.zeros_like(x)
    returns[:, 1:] = x[:, 1:] / x[:, :-1] - 1
    years = max(x.shape[1] / 252, 1 / 252)
    cagr = x[:, -1] ** (1 / years) - 1
    maxdd = (x / np.maximum.accumulate(x, axis=1) - 1).min(axis=1)
    sharpe = np.sqrt(252) * returns.mean(axis=1) / returns.std(axis=1, ddof=1)
    calmar = cagr / np.maximum(-maxdd, 1e-12)
    return {"cagr_mean": float(np.mean(cagr)), "cagr_median": float(np.median(cagr)),
            "maxdd_mean": float(np.mean(maxdd)), "sharpe_mean": float(np.mean(sharpe)),
            "calmar_mean": float(np.mean(calmar))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--output", type=Path, default=Path("collapse_alternative_exact_replay_output"))
    args = ap.parse_args(); root = args.root.resolve(); out = (root / args.output).resolve(); out.mkdir(parents=True, exist_ok=True)

    state = pd.read_csv(root / "library_inputs/STATE_PANEL.csv")
    state["signal_date"] = pd.to_datetime(state["signal_date"])
    exits = pd.read_csv(root / "library_inputs/RISK_LEARNING_PANEL.csv", usecols=["signal_date", "exit_date"]).drop_duplicates()
    exits["signal_date"] = pd.to_datetime(exits["signal_date"]); exits["exit_date"] = pd.to_datetime(exits["exit_date"])
    frozen = np.load(root / "risk_packages/action_frontier/ARMED_ACTION_FRONTIER_PATHS.npz")
    all_dates = pd.DatetimeIndex(frozen["dates"])
    replay_start = safe_loc(all_dates, state.signal_date.min(), "right")
    dates = all_dates[replay_start:]
    data_dir = root / "library_inputs/armed_accepted/data/armed_risk_v2_20260702"
    prices = load_prices(data_dir, dates)
    tickers = list(prices["OPEN"].columns); ti = {t:i for i,t in enumerate(tickers)}
    d1, d2, weights, month_start = build_daily_state(state, exits, dates, tickers)

    sequential = pd.read_parquet(root / "sequential_leader_state_output/SEQUENTIAL_LEADER_STATE_PANEL.parquet")
    for col in EVENT_KEY:
        if "date" in col: sequential[col] = pd.to_datetime(sequential[col])
    calls = causal_calls(sequential)
    alternatives = top_alternatives(pd.read_parquet(root / "alternative_ranker_output/ALTERNATIVE_CANDIDATE_PANEL.parquet"))
    fires = pd.read_csv(root / "orthogonal_fire_output/ORTHOGONAL_FIRE_PANEL.csv", usecols=["signal_date","exit_date","action_date","basket"])
    for col in ["signal_date","exit_date","action_date"]: fires[col] = pd.to_datetime(fires[col])
    baseline_schedule, candidate_schedule, candidate_d2, decisions = action_schedules(
        dates, fires, state, calls, alternatives, d2, ti
    )

    o=prices["OPEN"].to_numpy(float); l=prices["LOW"].to_numpy(float); c=prices["CLOSE"].to_numpy(float)
    pc=np.empty_like(c); pc[0]=o[0]; pc[1:]=c[:-1]
    gaps=np.zeros_like(o); gaps[1:]=o[1:]/c[:-1]-1
    universe_down=np.mean(gaps<-.01,axis=1); universe_negative=np.mean(gaps<0,axis=1)
    close=prices["CLOSE"]; m3=close/close.shift(3)-1; m5=close/close.shift(5)-1; ma10=close.rolling(10).mean(); ma20=close.rolling(20).mean()
    hazard=(((close<ma10)&(m3<0))|((close<ma20)&(m5<-.015))).shift(1,fill_value=False).to_numpy(bool)
    severe=((m5<-.04)|((close<ma20)&(m3<-.025))).shift(1,fill_value=False).to_numpy(bool)
    common=(o,l,c,pc,gaps,universe_down,universe_negative,hazard,severe,ti["BIL"],ti["SHV"],.001,.001)
    baseline, bt = simulate_controller(d1,d2,weights,month_start,baseline_schedule,*common)
    candidate, ct = simulate_controller(d1,candidate_d2,weights,month_start,candidate_schedule,*common)

    if not (np.isfinite(baseline).all() and np.isfinite(candidate).all()):
        raise RuntimeError("Non-finite equity in reconstructed replay")
    reference = frozen["FLIP"][:, replay_start:]
    rebuilt_norm = baseline / baseline[:, [0]]
    reference_norm = reference / reference[:, [0]]
    parity_error = np.abs(rebuilt_norm - reference_norm)
    b_parity = score(rebuilt_norm, dates, "2020-02-03", "2026-07-01")
    r_parity = score(reference_norm, dates, "2020-02-03", "2026-07-01")
    parity = {
        "max_abs_equity_error": float(parity_error.max()),
        "mean_abs_equity_error": float(parity_error.mean()),
        "cagr_gap_pp": float(100 * (b_parity["cagr_mean"] - r_parity["cagr_mean"])),
        "maxdd_gap_pp": float(100 * (b_parity["maxdd_mean"] - r_parity["maxdd_mean"])),
        "sharpe_gap": float(b_parity["sharpe_mean"] - r_parity["sharpe_mean"]),
    }
    parity["status"] = "ACCEPTED_INCREMENTAL_ANCHOR_PARITY" if (
        abs(parity["cagr_gap_pp"]) <= 0.05
        and abs(parity["maxdd_gap_pp"]) <= 0.08
        and abs(parity["sharpe_gap"]) <= 0.002
    ) else "REJECTED_PARITY"
    if parity["status"] != "ACCEPTED_INCREMENTAL_ANCHOR_PARITY":
        raise RuntimeError(f"Rebuilt baseline parity failed: {parity}")

    official_baseline = frozen["FLIP"].copy()
    official_candidate = official_baseline.copy()
    incremental_ratio = (candidate / baseline)
    incremental_ratio /= incremental_ratio[:, [0]]
    official_candidate[:, replay_start:] *= incremental_ratio

    periods={"OFFICIAL_FULL_2017_2026":("2017-02-01","2026-07-01"),"REBUILT_2020_2026":("2020-02-03","2026-07-01"),"DEV_2021_2022":("2021-01-01","2022-12-31"),"HOLDOUT_2023_2026":("2023-01-01","2026-07-01")}
    rows=[]
    for name,(start,end) in periods.items():
        if name.startswith("OFFICIAL_FULL"):
            b=score(official_baseline,all_dates,start,end); x=score(official_candidate,all_dates,start,end)
        else:
            b=score(baseline,dates,start,end); x=score(candidate,dates,start,end)
        rows.append({"period":name,**{f"baseline_{k}":v for k,v in b.items()},**{f"candidate_{k}":v for k,v in x.items()},
                     "delta_cagr_pp":100*(x["cagr_mean"]-b["cagr_mean"]),"delta_maxdd_pp":100*(x["maxdd_mean"]-b["maxdd_mean"]),"delta_sharpe":x["sharpe_mean"]-b["sharpe_mean"]})
    scorecard=pd.DataFrame(rows)
    manifest={"baseline_official_full_cagr":0.2398818905152815,"baseline_official_full_maxdd":-0.3234166169740528,
              "baseline_official_full_sharpe":0.9301567167554667,"detector_threshold":THRESHOLD,
              "leader_calls":int(len(calls)),"basket_switches":int(len(decisions)),"unique_switch_dates":int(decisions.switch_action_date.nunique()),
              "execution":"FLIP at first next open; after two closes, 100% top TIT_R at next open through exit",
              "parity":parity,
              "status":"EXACT_OFFICIAL_PATH_ANCHORED"}
    scorecard.to_csv(out/"COLLAPSE_ALTERNATIVE_EXACT_SCORECARD.csv",index=False); decisions.to_csv(out/"COLLAPSE_ALTERNATIVE_EXACT_DECISIONS.csv",index=False)
    np.savez_compressed(out/"COLLAPSE_ALTERNATIVE_REBUILT_PATHS.npz",dates=dates.values,baseline=baseline,candidate=candidate)
    np.savez_compressed(out/"COLLAPSE_ALTERNATIVE_OFFICIAL_ANCHORED_PATHS.npz",dates=all_dates.values,baseline=official_baseline,candidate=official_candidate)
    (out/"COLLAPSE_ALTERNATIVE_EXACT_REPLAY.json").write_text(json.dumps(manifest,indent=2,default=str)+"\n")
    print(json.dumps(manifest,indent=2)); print("\n",scorecard.to_string(index=False)); print("\nDECISIONS\n",decisions.groupby([decisions.switch_action_date.dt.year,"remaining_state"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__": main()
