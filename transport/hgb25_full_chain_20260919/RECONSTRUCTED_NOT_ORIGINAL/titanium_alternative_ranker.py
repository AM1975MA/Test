#!/usr/bin/env python3
"""RECONSTRUCTED — NOT ORIGINAL HISTORICAL SOURCE.

Clean-room reconstruction of the missing Titanium alternative-candidate
producer. It preserves the documented idea: after a confirmed leader shock,
evaluate the whole causal TIT_R universe (excluding leader/BIL/SHV), attach
causal health/momentum/drawdown/volatility/correlation information, and retain
future returns only as labels for research. The downstream historical selector
chooses max TIT_R; future labels are never used for live selection.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

SOURCE_STATUS = "RECONSTRUCTED_NOT_ORIGINAL"
RECONSTRUCTION_DATE = "2026-09-19"
EPS = 1e-12

EVENT_KEY = [
    "signal_date", "trigger_date", "action_date", "exit_date",
    "leader", "score_date", "next_action_date",
]

SCORE_COLS = [
    "TIT_R", "cand_r3", "cand_r5", "cand_r10", "cand_r21", "cand_r63",
    "cand_r21_cross_pct", "cand_dd21", "cand_dd63", "cand_vol5",
    "cand_vol20", "cand_vs_ma20", "cand_vs_ma50",
    "cand_corr_leader20", "cand_corr_spy20",
]
DAILY_COLS = [
    "cand_gap", "cand_downfrac5", "cand_atr20", "cand_volume_z20",
    "spy_r5", "spy_r21", "spy_dd63", "spy_vs_ma200",
    "hyg_ief_r10", "breadth5", "breadth21", "cross_down1",
]


def _ret(close: pd.DataFrame, ticker: str, pos: int, lag: int) -> float:
    if ticker not in close.columns or pos - lag < 0:
        return np.nan
    a = float(close.iloc[pos][ticker])
    b = float(close.iloc[pos - lag][ticker])
    return a / b - 1 if np.isfinite(a) and np.isfinite(b) and b > 0 else np.nan


def _dd(close: pd.DataFrame, ticker: str, pos: int, window: int) -> float:
    s = close[ticker].iloc[max(0, pos - window + 1): pos + 1]
    return float(s.iloc[-1] / s.max() - 1) if len(s) and s.max() > 0 else np.nan


def _vol(close: pd.DataFrame, ticker: str, pos: int, window: int) -> float:
    s = close[ticker].iloc[max(0, pos - window): pos + 1].pct_change().dropna()
    return float(s.std(ddof=1) * np.sqrt(252)) if len(s) >= 3 else np.nan


def _ma(close: pd.DataFrame, ticker: str, pos: int, window: int) -> float:
    s = close[ticker].iloc[max(0, pos - window + 1): pos + 1]
    return float(s.iloc[-1] / s.mean() - 1) if len(s) >= max(3, window // 2) else np.nan


def _corr(close: pd.DataFrame, a: str, b: str, pos: int, window: int = 20) -> float:
    if a not in close.columns or b not in close.columns:
        return np.nan
    ra = close[a].iloc[max(0, pos - window): pos + 1].pct_change()
    rb = close[b].iloc[max(0, pos - window): pos + 1].pct_change()
    return float(ra.corr(rb))


def _normalize_scores(scores: pd.DataFrame) -> pd.DataFrame:
    z = scores.copy()
    date_col = "score_date" if "score_date" in z.columns else (
        "date" if "date" in z.columns else "signal_date"
    )
    z[date_col] = pd.to_datetime(z[date_col])
    # Historical TIT_R is a monthly signal-date score carried forward to the\n    # post-fire decision date.  Do NOT require a daily TIT_R row on score_date.\n    z = z.rename(columns={date_col: "_score_signal_date"})
    if "TIT_R" not in z.columns:
        for c in ["tit_r", "score", "titanium_score"]:
            if c in z.columns:
                z = z.rename(columns={c: "TIT_R"})
                break
    if "ticker" not in z.columns or "TIT_R" not in z.columns:
        raise ValueError("score panel must contain ticker and TIT_R")
    return z[["_score_signal_date", "ticker", "TIT_R"]].dropna().sort_values(
        ["_score_signal_date", "ticker"]
    )


def build_candidate_panel(events: pd.DataFrame, scores: pd.DataFrame,
                          open_: pd.DataFrame, high: pd.DataFrame,
                          low: pd.DataFrame, close: pd.DataFrame,
                          volume: pd.DataFrame, cost: float = 0.001) -> pd.DataFrame:
    open_ = open_.sort_index()
    high = high.sort_index()
    low = low.sort_index()
    close = close.sort_index()
    volume = volume.sort_index()
    dates = pd.DatetimeIndex(close.index)
    score = _normalize_scores(scores)
    ev = events.copy()
    for c in EVENT_KEY:
        if "date" in c:
            ev[c] = pd.to_datetime(ev[c])
    if "offset" in ev.columns:
        ev = ev.loc[ev["offset"].eq(2)].copy()

    rows = []
    for e in ev.itertuples(index=False):
        score_date = pd.Timestamp(e.score_date)
        next_action = pd.Timestamp(e.next_action_date)
        exit_date = pd.Timestamp(e.exit_date)
        pos = int(dates.searchsorted(score_date, side="left"))
        start = int(dates.searchsorted(next_action, side="left"))
        end = int(dates.searchsorted(exit_date, side="left"))
        if pos >= len(dates) or start >= end or end >= len(dates):
            continue

        # TIT_R belongs to the basket's monthly signal_date; score_date is the\n        # later, causal second-close decision date used for market features.\n        signal_date = pd.Timestamp(e.signal_date)\n        s = score.loc[score["_score_signal_date"].eq(signal_date)]
        if s.empty:
            continue
        candidates = s.loc[
            ~s["ticker"].isin([str(e.leader), "BIL", "SHV"])
        ].copy()

        r21 = {
            t: _ret(close, t, pos, 21)
            for t in candidates["ticker"] if t in close.columns
        }
        valid_r21 = pd.Series(r21, dtype=float)
        pct = valid_r21.rank(pct=True) if len(valid_r21) else pd.Series(dtype=float)

        spy_r5 = _ret(close, "SPY", pos, 5)
        spy_r21 = _ret(close, "SPY", pos, 21)
        spy_dd63 = _dd(close, "SPY", pos, 63)
        spy_ma200 = _ma(close, "SPY", pos, 200)
        hyg_ief = _ret(close, "HYG", pos, 10) - _ret(close, "IEF", pos, 10)
        cur = close.iloc[pos]
        breadth5 = float((cur / close.iloc[pos - 5] - 1 > 0).mean()) if pos >= 5 else np.nan
        breadth21 = float((cur / close.iloc[pos - 21] - 1 > 0).mean()) if pos >= 21 else np.nan
        cross_down1 = float((cur / close.iloc[pos - 1] - 1 < 0).mean()) if pos >= 1 else np.nan

        for rr in candidates.itertuples(index=False):
            t = str(rr.ticker)
            if t not in close.columns or t not in open_.columns:
                continue
            c0 = float(open_.iloc[start][t])
            ce = float(open_.iloc[end][t])
            if not (np.isfinite(c0) and np.isfinite(ce) and c0 > 0):
                continue
            future = ce / c0 - 1 - cost
            path = close[t].iloc[start:end].to_numpy(float) / c0 - 1 - cost
            ret5 = close[t].iloc[max(0, pos - 20): pos + 1].pct_change().dropna()
            atr = ((high[t] - low[t]) / close[t].shift(1)).iloc[max(0, pos - 19): pos + 1]
            vs = volume[t].iloc[max(0, pos - 19): pos + 1]
            vz = (
                (np.log1p(vs.iloc[-1]) - np.log1p(vs).mean())
                / (np.log1p(vs).std(ddof=1) + EPS)
                if len(vs) >= 5 else np.nan
            )

            rec = {k: getattr(e, k) for k in EVENT_KEY}
            rec.update({
                "ticker": t,
                "TIT_R": float(rr.TIT_R),
                "cand_r3": _ret(close, t, pos, 3),
                "cand_r5": _ret(close, t, pos, 5),
                "cand_r10": _ret(close, t, pos, 10),
                "cand_r21": _ret(close, t, pos, 21),
                "cand_r63": _ret(close, t, pos, 63),
                "cand_r21_cross_pct": float(pct.get(t, np.nan)),
                "cand_dd21": _dd(close, t, pos, 21),
                "cand_dd63": _dd(close, t, pos, 63),
                "cand_vol5": _vol(close, t, pos, 5),
                "cand_vol20": _vol(close, t, pos, 20),
                "cand_vs_ma20": _ma(close, t, pos, 20),
                "cand_vs_ma50": _ma(close, t, pos, 50),
                "cand_corr_leader20": _corr(close, t, str(e.leader), pos, 20),
                "cand_corr_spy20": _corr(close, t, "SPY", pos, 20),
                "cand_gap": float(open_.iloc[pos][t] / close.iloc[pos - 1][t] - 1)
                    if pos >= 1 else np.nan,
                "cand_downfrac5": float((ret5.tail(5) < 0).mean()) if len(ret5) else np.nan,
                "cand_atr20": float(atr.mean()),
                "cand_volume_z20": float(vz),
                "spy_r5": spy_r5,
                "spy_r21": spy_r21,
                "spy_dd63": spy_dd63,
                "spy_vs_ma200": spy_ma200,
                "hyg_ief_r10": hyg_ief,
                "breadth5": breadth5,
                "breadth21": breadth21,
                "cross_down1": cross_down1,
                "future_return_net": float(future),
                "future_min_net": float(np.nanmin(path)) if len(path) else float(future),
            })
            rows.append(rec)

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(EVENT_KEY + ["TIT_R", "ticker"]).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=Path, required=True)
    ap.add_argument("--scores", type=Path, required=True)
    ap.add_argument("--open", dest="open_path", type=Path, required=True)
    ap.add_argument("--high", type=Path, required=True)
    ap.add_argument("--low", type=Path, required=True)
    ap.add_argument("--close", type=Path, required=True)
    ap.add_argument("--volume", type=Path, required=True)
    ap.add_argument(
        "--output", type=Path,
        default=Path("alternative_ranker_output/ALTERNATIVE_CANDIDATE_PANEL.parquet"),
    )
    a = ap.parse_args()
    ev = pd.read_parquet(a.events) if a.events.suffix == ".parquet" else pd.read_csv(a.events)
    sc = pd.read_parquet(a.scores) if a.scores.suffix == ".parquet" else pd.read_csv(a.scores)
    panel = build_candidate_panel(
        ev, sc,
        pd.read_parquet(a.open_path),
        pd.read_parquet(a.high),
        pd.read_parquet(a.low),
        pd.read_parquet(a.close),
        pd.read_parquet(a.volume),
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(a.output, index=False)
    print({"status": SOURCE_STATUS, "rows": len(panel), "output": str(a.output)})


if __name__ == "__main__":
    main()
