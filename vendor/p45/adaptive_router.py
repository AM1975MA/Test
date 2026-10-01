#!/usr/bin/env python3
"""P43 preregistered adaptive causal cadence router.

This module implements only the frozen meta-layer from PROTOCOL.md.  It does
not modify Annual or Monthly producer logic and does not contain any tuning
loop.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import log, log1p, sqrt
from typing import Iterable

import numpy as np
import pandas as pd

DELTA = 0.002
MIN_SEGMENT = 5
Z95 = 1.96
EPS = 1e-12

STATE_WEIGHTS = {
    "Annual": (1.0, 0.0),
    "50-50": (0.5, 0.5),
    "Monthly": (0.0, 1.0),
}


@dataclass(frozen=True)
class MaturedSkill:
    interval_signal_date: pd.Timestamp
    outcome_end: pd.Timestamp
    annual_return: float
    monthly_return: float
    skill: float
    x: float


@dataclass(frozen=True)
class RouterDecision:
    signal_date: pd.Timestamp
    last_matured_outcome_end: pd.Timestamp | None
    observations_seen: int
    window_length: int
    window_mean_skill: float
    window_sd_skill: float
    ci_low: float
    ci_high: float
    detector_reset: bool
    state: str
    w_annual: float
    w_monthly: float


def relative_skill(annual_return: float, monthly_return: float) -> tuple[float, float]:
    """Return preregistered bounded skill in [-1,1] and detector x in [0,1]."""
    if annual_return <= -1.0 or monthly_return <= -1.0:
        raise ValueError("shadow interval return must be greater than -100%")
    ga = log1p(float(annual_return))
    gm = log1p(float(monthly_return))
    s = (gm - ga) / (abs(gm) + abs(ga) + EPS)
    s = float(np.clip(s, -1.0, 1.0))
    x = 0.5 * (s + 1.0)
    return s, x


class AdaptiveCausalCadenceRouter:
    """One-pass P43 router with an ADWIN-style adaptive skill window."""

    def __init__(self, *, delta: float = DELTA, min_segment: int = MIN_SEGMENT):
        if delta != DELTA or min_segment != MIN_SEGMENT:
            raise ValueError(
                "P43 constants are frozen: delta=0.002 and min_segment=5; "
                "create a new numbered experiment to change them"
            )
        self.delta = float(delta)
        self.min_segment = int(min_segment)
        self._window: list[MaturedSkill] = []
        self._seen = 0
        self._last_matured_end: pd.Timestamp | None = None
        self._reset_since_decision = False

    @property
    def window(self) -> tuple[MaturedSkill, ...]:
        return tuple(self._window)

    @property
    def observations_seen(self) -> int:
        return self._seen

    def _best_cut(self) -> int | None:
        n = len(self._window)
        if n < 2 * self.min_segment:
            return None
        arr = np.asarray([o.x for o in self._window], dtype=float)
        v = float(np.var(arr, ddof=1)) if n > 1 else 0.0
        lterm = log(2.0 / self.delta)
        best_cut = None
        best_excess = 0.0
        for cut in range(self.min_segment, n - self.min_segment + 1):
            a = arr[:cut]
            b = arr[cut:]
            n0, n1 = len(a), len(b)
            m = 1.0 / n0 + 1.0 / n1
            eps = sqrt(max(0.0, 2.0 * v * m * lterm)) + (2.0 / 3.0) * m * lterm
            excess = abs(float(a.mean()) - float(b.mean())) - eps
            if excess > best_excess + 1e-15:
                best_excess = excess
                best_cut = cut
        return best_cut

    def _adapt_window(self) -> bool:
        reset = False
        while True:
            cut = self._best_cut()
            if cut is None:
                break
            self._window = self._window[cut:]
            reset = True
        return reset

    def ingest_matured(
        self,
        *,
        interval_signal_date: pd.Timestamp | str,
        outcome_end: pd.Timestamp | str,
        annual_return: float,
        monthly_return: float,
        current_signal_date: pd.Timestamp | str,
    ) -> MaturedSkill:
        """Ingest one closed shadow interval, enforcing strict causal timing."""
        interval_signal_date = pd.Timestamp(interval_signal_date)
        outcome_end = pd.Timestamp(outcome_end)
        current_signal_date = pd.Timestamp(current_signal_date)
        if not outcome_end < current_signal_date:
            raise ValueError(
                f"causality violation: outcome_end={outcome_end} must be strictly "
                f"before current_signal_date={current_signal_date}"
            )
        if self._last_matured_end is not None and outcome_end <= self._last_matured_end:
            raise ValueError("matured outcomes must be ingested in strictly increasing order")
        s, x = relative_skill(annual_return, monthly_return)
        obs = MaturedSkill(
            interval_signal_date=interval_signal_date,
            outcome_end=outcome_end,
            annual_return=float(annual_return),
            monthly_return=float(monthly_return),
            skill=s,
            x=x,
        )
        self._window.append(obs)
        self._seen += 1
        self._last_matured_end = outcome_end
        self._reset_since_decision |= self._adapt_window()
        return obs

    def decision(self, signal_date: pd.Timestamp | str) -> RouterDecision:
        signal_date = pd.Timestamp(signal_date)
        if self._last_matured_end is not None and not self._last_matured_end < signal_date:
            raise ValueError("router history contains information not mature before signal")

        s = np.asarray([o.skill for o in self._window], dtype=float)
        n = int(len(s))
        if n == 0:
            mean = sd = 0.0
            lo, hi = -np.inf, np.inf
            state = "50-50"
        else:
            mean = float(s.mean())
            sd = float(s.std(ddof=1)) if n > 1 else 0.0
            if n < MIN_SEGMENT:
                lo, hi = -np.inf, np.inf
                state = "50-50"
            else:
                hw = Z95 * sd / sqrt(n)
                lo, hi = mean - hw, mean + hw
                if lo > 0.0:
                    state = "Monthly"
                elif hi < 0.0:
                    state = "Annual"
                else:
                    state = "50-50"

        wa, wm = STATE_WEIGHTS[state]
        out = RouterDecision(
            signal_date=signal_date,
            last_matured_outcome_end=self._last_matured_end,
            observations_seen=self._seen,
            window_length=n,
            window_mean_skill=mean,
            window_sd_skill=sd,
            ci_low=float(lo),
            ci_high=float(hi),
            detector_reset=bool(self._reset_since_decision),
            state=state,
            w_annual=wa,
            w_monthly=wm,
        )
        self._reset_since_decision = False
        return out


def route_trace(
    signal_dates: Iterable[pd.Timestamp],
    matured_intervals: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build a fully causal route trace from completed shadow intervals.

    Required interval columns:
      interval_signal_date, outcome_end, annual_return, monthly_return
    Every interval is ingested only at the first signal strictly after outcome_end.
    """
    req = {
        "interval_signal_date",
        "outcome_end",
        "annual_return",
        "monthly_return",
    }
    missing = req.difference(matured_intervals.columns)
    if missing:
        raise KeyError(f"missing shadow interval columns: {sorted(missing)}")

    ints = matured_intervals.copy()
    ints["interval_signal_date"] = pd.to_datetime(ints["interval_signal_date"])
    ints["outcome_end"] = pd.to_datetime(ints["outcome_end"])
    ints = ints.sort_values(["outcome_end", "interval_signal_date"]).reset_index(drop=True)

    router = AdaptiveCausalCadenceRouter()
    p = 0
    decisions: list[dict] = []
    skills: list[dict] = []
    for sd in pd.DatetimeIndex(signal_dates).sort_values():
        while p < len(ints) and pd.Timestamp(ints.loc[p, "outcome_end"]) < sd:
            r = ints.loc[p]
            obs = router.ingest_matured(
                interval_signal_date=r["interval_signal_date"],
                outcome_end=r["outcome_end"],
                annual_return=float(r["annual_return"]),
                monthly_return=float(r["monthly_return"]),
                current_signal_date=sd,
            )
            skills.append(asdict(obs))
            p += 1
        decisions.append(asdict(router.decision(sd)))

    return pd.DataFrame(decisions), pd.DataFrame(skills)


def _self_test() -> None:
    # Cold start must be neutral.
    r = AdaptiveCausalCadenceRouter()
    assert r.decision("2020-01-31").state == "50-50"

    # A future/unmatured observation must be rejected.
    try:
        r.ingest_matured(
            interval_signal_date="2020-01-31",
            outcome_end="2020-02-28",
            annual_return=0.01,
            monthly_return=0.02,
            current_signal_date="2020-02-28",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("causality guard failed")

    # Five identical positive mature observations create Monthly evidence.
    for i in range(5):
        r.ingest_matured(
            interval_signal_date=pd.Timestamp("2019-01-01") + pd.offsets.MonthEnd(i + 1),
            outcome_end=pd.Timestamp("2019-02-01") + pd.offsets.MonthEnd(i + 1),
            annual_return=0.0,
            monthly_return=0.02,
            current_signal_date="2020-12-31",
        )
    assert r.decision("2020-12-31").state == "Monthly"

    # Frozen constants must fail closed.
    try:
        AdaptiveCausalCadenceRouter(delta=0.01)
    except ValueError:
        pass
    else:
        raise AssertionError("frozen-constant guard failed")

    print("P43_ROUTER_SELF_TEST_PASS")


if __name__ == "__main__":
    _self_test()
