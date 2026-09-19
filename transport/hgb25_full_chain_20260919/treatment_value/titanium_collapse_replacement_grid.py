#!/usr/bin/env python3
"""Exact test of replacing only the collapsed sleeve with a live alternative.

The official ARMED_FLIP_25_75 baseline is untouched.  After the frozen
two-close collapse call, the candidate replaces the 25% leader sleeve (or a
larger experimental fraction) with an ex-ante selected alternative.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from titanium_collapse_alternative_exact_replay import EVENT_KEY, causal_calls, score
from titanium_sequential_dd_controller import build_daily_state, load_prices, safe_loc, simulate_controller


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "collapse_replacement_grid_output"


def select_alternatives(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    z = frame.copy()
    for col in EVENT_KEY:
        if "date" in col:
            z[col] = pd.to_datetime(z[col])
    if rule == "TIT_R":
        z["selection_score"] = z["TIT_R"]
    elif rule == "R21":
        z["selection_score"] = z["cand_r21"]
    elif rule == "R3":
        z["selection_score"] = z["cand_r3"]
    elif rule == "ORACLE_RETURN":
        z["selection_score"] = z["future_return_net"]
    elif rule == "ORACLE_ROBUST":
        z["selection_score"] = z["future_return_net"] + .5*z["future_min_net"]
    elif rule in {"TIT_TOP_R21", "TIT_HALF_R21"}:
        z["tit_pct"] = z.groupby(EVENT_KEY, sort=False)["TIT_R"].rank(pct=True)
        cutoff = .75 if rule == "TIT_TOP_R21" else .50
        z = z.loc[z["tit_pct"].ge(cutoff)].copy()
        z["selection_score"] = z["cand_r21"]
    elif rule == "RISK_ADJ":
        grouped = z.groupby(EVENT_KEY, sort=False)
        z["r_tit"] = grouped["TIT_R"].rank(pct=True)
        z["r_r21"] = grouped["cand_r21_cross_pct"].rank(pct=True)
        z["r_vol"] = grouped["cand_vol20"].rank(pct=True)
        z["r_dd"] = grouped["cand_dd21"].rank(pct=True)
        z["selection_score"] = z["r_tit"] + .25*z["r_r21"] - .20*z["r_vol"] + .20*z["r_dd"]
    else:
        raise ValueError(rule)
    return (
        z.sort_values(EVENT_KEY + ["selection_score"])
        .groupby(EVENT_KEY, as_index=False).tail(1)
        [EVENT_KEY + ["ticker", "selection_score", "future_return_net", "future_min_net"]]
        .rename(columns={"ticker": "alternative"})
    )


def schedules(dates, fires, state, calls, selected, d1, d2, weights, ticker_index, fraction):
    baseline_code = np.zeros((500, len(dates)), dtype=np.int8)
    candidate_code = np.zeros_like(baseline_code)
    candidate_d1, candidate_d2, candidate_w = d1.copy(), d2.copy(), weights.copy()
    mapped = fires.merge(state[["signal_date", "basket", "leader", "sat"]],
                         on=["signal_date", "basket"], how="inner", validate="many_to_one")
    for row in mapped.itertuples(index=False):
        start = safe_loc(dates, row.action_date, "left")
        end = safe_loc(dates, row.exit_date, "left")
        if start < end:
            baseline_code[int(row.basket), start:end] = 1
            candidate_code[int(row.basket), start:end] = 1

    decisions = calls.merge(selected, on=EVENT_KEY, how="inner", validate="one_to_one")
    decisions = decisions.merge(
        mapped[["signal_date", "action_date", "exit_date", "leader", "basket"]],
        on=["signal_date", "action_date", "exit_date", "leader"],
        how="inner", validate="one_to_many")
    applied = []
    for row in decisions.itertuples(index=False):
        alt = ticker_index.get(str(row.alternative), -1)
        start = safe_loc(dates, row.next_action_date, "left")
        end = safe_loc(dates, row.exit_date, "left")
        basket = int(row.basket)
        if alt < 0 or start >= end:
            continue
        if fraction < 1.0:
            candidate_d1[basket, start:end] = alt
            candidate_w[basket, start:end] = fraction
            candidate_code[basket, start:end] = 1 if abs(fraction-.25) < 1e-12 else 0
        else:
            candidate_d2[basket, start:end] = alt
            candidate_code[basket, start:end] = 2
        applied.append({
            "basket": basket, "leader": row.leader, "alternative": row.alternative,
            "signal_date": row.signal_date, "switch_action_date": row.next_action_date,
            "exit_date": row.exit_date, "p_collapse": row.p_collapse,
            "remaining_state": row.remaining_state, "selection_score": row.selection_score,
            "future_return_net": row.future_return_net, "future_min_net": row.future_min_net,
            "fraction": fraction,
        })
    return baseline_code, candidate_code, candidate_d1, candidate_d2, candidate_w, pd.DataFrame(applied)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    state = pd.read_csv(ROOT / "library_inputs/STATE_PANEL.csv")
    state["signal_date"] = pd.to_datetime(state["signal_date"])
    exits = pd.read_csv(ROOT / "library_inputs/RISK_LEARNING_PANEL.csv", usecols=["signal_date", "exit_date"]).drop_duplicates()
    exits["signal_date"] = pd.to_datetime(exits["signal_date"]); exits["exit_date"] = pd.to_datetime(exits["exit_date"])
    frozen = np.load(ROOT / "risk_packages/action_frontier/ARMED_ACTION_FRONTIER_PATHS.npz")
    all_dates = pd.DatetimeIndex(frozen["dates"])
    replay_start = safe_loc(all_dates, state.signal_date.min(), "right")
    dates = all_dates[replay_start:]
    data_dir = ROOT / "library_inputs/armed_accepted/data/armed_risk_v2_20260702"
    prices = load_prices(data_dir, dates)
    tickers = list(prices["OPEN"].columns); ti = {t:i for i,t in enumerate(tickers)}
    d1, d2, weights, month_start = build_daily_state(state, exits, dates, tickers)

    sequential = pd.read_parquet(ROOT / "sequential_leader_state_output/SEQUENTIAL_LEADER_STATE_PANEL.parquet")
    for col in EVENT_KEY:
        if "date" in col: sequential[col] = pd.to_datetime(sequential[col])
    calls = causal_calls(sequential)
    candidates = pd.read_parquet(ROOT / "alternative_ranker_output/ALTERNATIVE_CANDIDATE_PANEL.parquet")
    fires = pd.read_csv(ROOT / "orthogonal_fire_output/ORTHOGONAL_FIRE_PANEL.csv",
                        usecols=["signal_date", "exit_date", "action_date", "basket"])
    for col in ["signal_date", "exit_date", "action_date"]: fires[col] = pd.to_datetime(fires[col])

    o=prices["OPEN"].to_numpy(float); l=prices["LOW"].to_numpy(float); c=prices["CLOSE"].to_numpy(float)
    pc=np.empty_like(c); pc[0]=o[0]; pc[1:]=c[:-1]
    gaps=np.zeros_like(o); gaps[1:]=o[1:]/c[:-1]-1
    universe_down=np.mean(gaps<-.01,axis=1); universe_negative=np.mean(gaps<0,axis=1)
    close=prices["CLOSE"]; m3=close/close.shift(3)-1; m5=close/close.shift(5)-1
    ma10=close.rolling(10).mean(); ma20=close.rolling(20).mean()
    hazard=(((close<ma10)&(m3<0))|((close<ma20)&(m5<-.015))).shift(1,fill_value=False).to_numpy(bool)
    severe=((m5<-.04)|((close<ma20)&(m3<-.025))).shift(1,fill_value=False).to_numpy(bool)
    common=(o,l,c,pc,gaps,universe_down,universe_negative,hazard,severe,ti["BIL"],ti["SHV"],.001,.001)

    baseline_path = None
    rows, decision_parts = [], []
    for rule in ["TIT_R", "R3", "R21", "RISK_ADJ", "TIT_TOP_R21", "TIT_HALF_R21", "ORACLE_RETURN", "ORACLE_ROBUST"]:
        selected = select_alternatives(candidates, rule)
        for threshold in [.834412501765974, .875, .90, .925, .95]:
          active_calls = calls.loc[calls.p_collapse.ge(threshold)].copy()
          for fraction in [.25, .50, 1.0]:
            bcode, ccode, cd1, cd2, cw, decisions = schedules(
                dates, fires, state, active_calls, selected, d1, d2, weights, ti, fraction)
            if baseline_path is None:
                baseline_path, _ = simulate_controller(d1,d2,weights,month_start,bcode,*common)
            candidate_path, _ = simulate_controller(cd1,cd2,cw,month_start,ccode,*common)
            official = frozen["FLIP"].copy(); anchored = official.copy()
            ratio = candidate_path / baseline_path; ratio /= ratio[:, [0]]
            anchored[:, replay_start:] *= ratio
            for period, start, end in [
                ("OFFICIAL_FULL", "2017-02-01", "2026-07-01"),
                ("DEV_2021_2022", "2021-01-01", "2022-12-31"),
                ("HOLDOUT_2023_2026", "2023-01-01", "2026-07-01")]:
                if period == "OFFICIAL_FULL":
                    b=score(official,all_dates,start,end); x=score(anchored,all_dates,start,end)
                else:
                    b=score(baseline_path,dates,start,end); x=score(candidate_path,dates,start,end)
                rows.append({"call_mode":"FROZEN_DETECTOR","rule":rule,"threshold":threshold,"fraction":fraction,"period":period,
                             "baseline_cagr":b["cagr_mean"],"candidate_cagr":x["cagr_mean"],
                             "delta_cagr_pp":100*(x["cagr_mean"]-b["cagr_mean"]),
                             "baseline_maxdd":b["maxdd_mean"],"candidate_maxdd":x["maxdd_mean"],
                             "delta_maxdd_pp":100*(x["maxdd_mean"]-b["maxdd_mean"]),
                             "baseline_sharpe":b["sharpe_mean"],"candidate_sharpe":x["sharpe_mean"],
                             "delta_sharpe":x["sharpe_mean"]-b["sharpe_mean"]})
            decisions["rule"] = rule
            decisions["threshold"] = threshold
            decisions["call_mode"] = "FROZEN_DETECTOR"
            decision_parts.append(decisions)

    # Untradable ceiling diagnostic: perfect knowledge of which two-close
    # events will remain collapsed.  This isolates whether the economic
    # bottleneck is detection, candidate selection, or the action horizon.
    true_calls = sequential.loc[
        sequential["offset"].eq(2) & sequential["remaining_state"].eq("COLLAPSE")
    ].copy()
    true_calls["p_collapse"] = 1.0
    for rule in ["TIT_TOP_R21", "ORACLE_RETURN", "ORACLE_ROBUST"]:
        selected = select_alternatives(candidates, rule)
        for fraction in [.25, .50, 1.0]:
            bcode, ccode, cd1, cd2, cw, decisions = schedules(
                dates, fires, state, true_calls, selected, d1, d2, weights, ti, fraction)
            candidate_path, _ = simulate_controller(cd1,cd2,cw,month_start,ccode,*common)
            official = frozen["FLIP"].copy(); anchored = official.copy()
            ratio = candidate_path / baseline_path; ratio /= ratio[:, [0]]
            anchored[:, replay_start:] *= ratio
            for period, start, end in [
                ("OFFICIAL_FULL", "2017-02-01", "2026-07-01"),
                ("DEV_2021_2022", "2021-01-01", "2022-12-31"),
                ("HOLDOUT_2023_2026", "2023-01-01", "2026-07-01")]:
                if period == "OFFICIAL_FULL":
                    b=score(official,all_dates,start,end); x=score(anchored,all_dates,start,end)
                else:
                    b=score(baseline_path,dates,start,end); x=score(candidate_path,dates,start,end)
                rows.append({"call_mode":"PERFECT_COLLAPSE_DETECTOR","rule":rule,"threshold":1.0,"fraction":fraction,"period":period,
                             "baseline_cagr":b["cagr_mean"],"candidate_cagr":x["cagr_mean"],
                             "delta_cagr_pp":100*(x["cagr_mean"]-b["cagr_mean"]),
                             "baseline_maxdd":b["maxdd_mean"],"candidate_maxdd":x["maxdd_mean"],
                             "delta_maxdd_pp":100*(x["maxdd_mean"]-b["maxdd_mean"]),
                             "baseline_sharpe":b["sharpe_mean"],"candidate_sharpe":x["sharpe_mean"],
                             "delta_sharpe":x["sharpe_mean"]-b["sharpe_mean"]})
            decisions["rule"] = rule
            decisions["threshold"] = 1.0
            decisions["call_mode"] = "PERFECT_COLLAPSE_DETECTOR"
            decision_parts.append(decisions)
    result = pd.DataFrame(rows)
    result.to_csv(OUT / "COLLAPSE_REPLACEMENT_GRID_SCORECARD.csv", index=False)
    pd.concat(decision_parts, ignore_index=True).to_csv(OUT / "COLLAPSE_REPLACEMENT_GRID_DECISIONS.csv", index=False)
    manifest = {"baseline":"ARMED_FLIP_25_75","detector":"frozen HGB two-close call",
                "rules":["TIT_R","R3","R21","RISK_ADJ","TIT_TOP_R21","TIT_HALF_R21","ORACLE_RETURN","ORACLE_ROBUST"],"thresholds":[.834412501765974,.875,.9,.925,.95],"fractions":[.25,.5,1.0],
                "status":"DIAGNOSTIC_GRID__SELECT_ON_DEV_ONLY"}
    (OUT / "COLLAPSE_REPLACEMENT_GRID.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(result.pivot_table(index=["call_mode","rule","threshold","fraction"],columns="period",values="delta_cagr_pp").round(4).to_string())


if __name__ == "__main__":
    main()