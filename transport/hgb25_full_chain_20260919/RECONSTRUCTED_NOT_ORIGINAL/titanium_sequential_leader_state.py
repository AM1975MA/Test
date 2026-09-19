#!/usr/bin/env python3
"""RECONSTRUCTED — NOT ORIGINAL HISTORICAL SOURCE.

Clean-room reconstruction of the missing sequential leader-state producer used
by the 2026-08-24 Titanium collapse/treatment chain.

Causality contract:
- trigger is the already observed -3% close fire;
- offsets 0/1/2 use information through that close only;
- offset 2 means two closes after the trigger and acts at the next open;
- remaining_state is a FUTURE LABEL used only for supervised training/audit;
- no future value is used in any feature.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from titanium_breath_collapse_detector import BASE_FEATURES, SCORE_FEATURES

SOURCE_STATUS = "RECONSTRUCTED_NOT_ORIGINAL"
RECONSTRUCTION_DATE = "2026-09-19"

DYNAMIC = [
    "score_offset",
    "score_leader_from_trigger",
    "score_leader_from_entry",
    "score_rebound_from_post_trigger_low",
    "score_drawdown_from_post_trigger_high",
    "score_spy_from_trigger",
    "score_sat_from_trigger",
    "score_rel_sat_from_trigger",
    "score_breadth_delta",
    "days_remaining",
]


def _ret(close: pd.DataFrame, ticker: str, pos: int, lag: int) -> float:
    if ticker not in close.columns or pos - lag < 0:
        return np.nan
    a = float(close.iloc[pos][ticker])
    b = float(close.iloc[pos - lag][ticker])
    return a / b - 1 if np.isfinite(a) and np.isfinite(b) and b > 0 else np.nan


def _dd(close: pd.DataFrame, ticker: str, pos: int, window: int) -> float:
    if ticker not in close.columns:
        return np.nan
    s = close[ticker].iloc[max(0, pos - window + 1): pos + 1]
    return float(s.iloc[-1] / s.max() - 1) if len(s) and s.max() > 0 else np.nan


def _vol(close: pd.DataFrame, ticker: str, pos: int, window: int) -> float:
    if ticker not in close.columns:
        return np.nan
    s = close[ticker].iloc[max(0, pos - window): pos + 1].pct_change().dropna()
    return float(s.std(ddof=1) * np.sqrt(252)) if len(s) >= 3 else np.nan


def _ma(close: pd.DataFrame, ticker: str, pos: int, window: int) -> float:
    if ticker not in close.columns:
        return np.nan
    s = close[ticker].iloc[max(0, pos - window + 1): pos + 1]
    return float(s.iloc[-1] / s.mean() - 1) if len(s) >= max(3, window // 2) else np.nan


def _label_remaining(close: pd.DataFrame, open_: pd.DataFrame, leader: str,
                     next_pos: int, exit_pos: int) -> tuple[str, float, float, float]:
    """Leader-only historical semantics, evaluated from next executable open."""
    if leader not in close.columns or next_pos >= exit_pos:
        return "DETERIORATION", np.nan, np.nan, np.nan
    entry = float(open_.iloc[next_pos][leader])
    terminal = float(open_.iloc[exit_pos][leader]) / entry - 1
    path = close[leader].iloc[next_pos:exit_pos].to_numpy(float) / entry - 1
    mn = float(np.nanmin(path)) if len(path) else terminal
    mx = float(np.nanmax(path)) if len(path) else terminal
    if mn <= -0.05 or terminal <= -0.04:
        state = "COLLAPSE"
    elif mn > -0.03 and (mx >= 0.02 or terminal >= 0.0):
        state = "BREATH"
    else:
        state = "DETERIORATION"
    return state, terminal, mn, mx


def build_sequential_panel(events: pd.DataFrame, open_: pd.DataFrame,
                           close: pd.DataFrame) -> pd.DataFrame:
    open_ = open_.sort_index()
    close = close.sort_index()
    dates = pd.DatetimeIndex(close.index)
    x = events.copy()
    for c in ["signal_date", "exit_date", "trigger_date", "action_date"]:
        x[c] = pd.to_datetime(x[c])

    sort_cols = [c for c in ["signal_date", "trigger_date", "leader", "sat"] if c in x.columns]
    x = x.sort_values(sort_cols).drop_duplicates(["signal_date", "trigger_date", "leader"])

    rows: list[dict] = []
    for r in x.itertuples(index=False):
        leader = str(r.leader)
        sat = str(getattr(r, "sat", ""))
        if leader not in close.columns:
            continue
        trig = int(dates.searchsorted(pd.Timestamp(r.trigger_date), side="left"))
        exit_pos = int(dates.searchsorted(pd.Timestamp(r.exit_date), side="left"))
        if trig >= len(dates) or exit_pos >= len(dates):
            continue

        for offset in (0, 1, 2):
            pos = trig + offset
            next_pos = pos + 1
            if next_pos >= exit_pos or next_pos >= len(dates):
                continue

            rec = {c: getattr(r, c) for c in BASE_FEATURES if hasattr(r, c)}
            rec.update({
                "signal_date": pd.Timestamp(r.signal_date),
                "trigger_date": pd.Timestamp(r.trigger_date),
                "action_date": pd.Timestamp(r.action_date),
                "exit_date": pd.Timestamp(r.exit_date),
                "leader": leader,
                "sat": sat,
                "score_date": dates[pos],
                "next_action_date": dates[next_pos],
                "offset": offset,
            })
            for c in BASE_FEATURES:
                rec.setdefault(c, np.nan)

            vals = {
                "score_leader_r1": _ret(close, leader, pos, 1),
                "score_leader_r3": _ret(close, leader, pos, 3),
                "score_leader_r5": _ret(close, leader, pos, 5),
                "score_leader_r10": _ret(close, leader, pos, 10),
                "score_leader_r21": _ret(close, leader, pos, 21),
                "score_leader_dd21": _dd(close, leader, pos, 21),
                "score_leader_dd63": _dd(close, leader, pos, 63),
                "score_leader_vol5": _vol(close, leader, pos, 5),
                "score_leader_vol20": _vol(close, leader, pos, 20),
                "score_leader_vs_ma20": _ma(close, leader, pos, 20),
                "score_leader_vs_ma50": _ma(close, leader, pos, 50),
                "score_spy_r5": _ret(close, "SPY", pos, 5),
                "score_spy_r21": _ret(close, "SPY", pos, 21),
                "score_spy_dd63": _dd(close, "SPY", pos, 63),
                "score_spy_vs_ma200": _ma(close, "SPY", pos, 200),
                "score_hyg_ief_r10": _ret(close, "HYG", pos, 10) - _ret(close, "IEF", pos, 10),
            }
            cur = close.iloc[pos]
            vals["score_breadth5"] = float((cur / close.iloc[pos - 5] - 1 > 0).mean()) if pos >= 5 else np.nan
            vals["score_breadth21"] = float((cur / close.iloc[pos - 21] - 1 > 0).mean()) if pos >= 21 else np.nan
            vals["score_cross_down1"] = float((cur / close.iloc[pos - 1] - 1 < 0).mean()) if pos >= 1 else np.nan
            rec.update(vals)

            trigger_close = float(close.iloc[trig][leader])
            entry_pos = int(dates.searchsorted(pd.Timestamp(r.signal_date), side="right"))
            entry_open = float(open_.iloc[entry_pos][leader]) if entry_pos < len(open_) else np.nan
            post = close[leader].iloc[trig:pos + 1].to_numpy(float)
            spy_trigger = float(close.iloc[trig]["SPY"]) if "SPY" in close.columns else np.nan
            sat_trigger = float(close.iloc[trig][sat]) if sat in close.columns else np.nan
            sat_now = float(close.iloc[pos][sat]) if sat in close.columns else np.nan

            rec.update({
                "score_offset": float(offset),
                "score_leader_from_trigger": float(close.iloc[pos][leader] / trigger_close - 1),
                "score_leader_from_entry": float(close.iloc[pos][leader] / entry_open - 1)
                    if np.isfinite(entry_open) and entry_open > 0 else np.nan,
                "score_rebound_from_post_trigger_low": float(close.iloc[pos][leader] / np.nanmin(post) - 1),
                "score_drawdown_from_post_trigger_high": float(close.iloc[pos][leader] / np.nanmax(post) - 1),
                "score_spy_from_trigger": float(close.iloc[pos]["SPY"] / spy_trigger - 1)
                    if "SPY" in close.columns and np.isfinite(spy_trigger) else np.nan,
                "score_sat_from_trigger": float(sat_now / sat_trigger - 1)
                    if np.isfinite(sat_now) and np.isfinite(sat_trigger) and sat_trigger > 0 else np.nan,
                "score_breadth_delta": vals["score_breadth21"] - rec.get("breadth21", np.nan),
                "days_remaining": float(exit_pos - next_pos),
            })
            rec["score_rel_sat_from_trigger"] = rec["score_leader_from_trigger"] - rec["score_sat_from_trigger"]

            state, terminal, mn, mx = _label_remaining(close, open_, leader, next_pos, exit_pos)
            rec.update({
                "remaining_state": state,
                "remaining_terminal": terminal,
                "remaining_min": mn,
                "remaining_max": mx,
            })
            rows.append(rec)

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["signal_date", "leader", "trigger_date", "offset"]).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=Path, required=True)
    ap.add_argument("--open", dest="open_path", type=Path, required=True)
    ap.add_argument("--close", dest="close_path", type=Path, required=True)
    ap.add_argument("--output", type=Path,
                    default=Path("sequential_leader_state_output/SEQUENTIAL_LEADER_STATE_PANEL.parquet"))
    a = ap.parse_args()
    ev = pd.read_csv(a.events)
    op = pd.read_parquet(a.open_path)
    cl = pd.read_parquet(a.close_path)
    out = build_sequential_panel(ev, op, cl)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(a.output, index=False)
    print({"status": SOURCE_STATUS, "rows": len(out), "output": str(a.output)})


if __name__ == "__main__":
    main()
