#!/usr/bin/env python3
"""P44 preregistered BOCPD local relative-skill router.

Implements the frozen P44 meta-layer only. No producer/portfolio tuning.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import erf, exp, pi, sqrt
import numpy as np
import pandas as pd

SIGMA2 = 1.0 / 3.0
PRIOR_MEAN = 0.0
PRIOR_VAR = SIGMA2
HAZARD = 1.0 / 12.0
MIN_OBS = 5
STATE_WEIGHTS = {
    "Annual": (1.0, 0.0),
    "50-50": (0.5, 0.5),
    "Monthly": (0.0, 1.0),
}


def _norm_pdf(x: float, mean: float, var: float) -> float:
    return exp(-0.5 * (x - mean) ** 2 / var) / sqrt(2.0 * pi * var)


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def _posterior_update(mean: float, var: float, x: float) -> tuple[float, float]:
    precision = 1.0 / var + 1.0 / SIGMA2
    new_var = 1.0 / precision
    new_mean = new_var * (mean / var + x / SIGMA2)
    return float(new_mean), float(new_var)


@dataclass(frozen=True)
class RouterDecision:
    signal_date: pd.Timestamp
    last_matured_outcome_end: pd.Timestamp | None
    observations_seen: int
    p_monthly: float
    p_change_last_update: float
    map_run_length: int
    expected_run_length: float
    state: str
    w_annual: float
    w_monthly: float


class BOCPDLocalSkillRouter:
    def __init__(self) -> None:
        self.prob = np.empty(0, dtype=float)
        self.mean = np.empty(0, dtype=float)
        self.var = np.empty(0, dtype=float)
        self.seen = 0
        self.last_matured_end: pd.Timestamp | None = None
        self.last_cp_prob = float("nan")

    def ingest(self, *, skill: float, outcome_end: pd.Timestamp | str, current_signal_date: pd.Timestamp | str) -> None:
        x = float(skill)
        if not (-1.0 <= x <= 1.0):
            raise ValueError("P44 skill must be in [-1,1]")
        end = pd.Timestamp(outcome_end)
        sd = pd.Timestamp(current_signal_date)
        if not end < sd:
            raise ValueError(f"causality violation: {end=} must be strictly before {sd=}")
        if self.last_matured_end is not None and not end > self.last_matured_end:
            raise ValueError("matured outcomes must be ingested in strictly increasing order")

        fresh_mean, fresh_var = _posterior_update(PRIOR_MEAN, PRIOR_VAR, x)

        if self.seen == 0:
            self.prob = np.asarray([1.0])
            self.mean = np.asarray([fresh_mean])
            self.var = np.asarray([fresh_var])
            self.last_cp_prob = 1.0
        else:
            prior_pred = _norm_pdf(x, PRIOR_MEAN, SIGMA2 + PRIOR_VAR)
            cp_mass = HAZARD * prior_pred
            pred = np.asarray([
                _norm_pdf(x, float(m), SIGMA2 + float(v))
                for m, v in zip(self.mean, self.var)
            ])
            growth_mass = self.prob * (1.0 - HAZARD) * pred
            masses = np.r_[cp_mass, growth_mass]
            total = float(masses.sum())
            if not np.isfinite(total) or total <= 0.0:
                raise RuntimeError("invalid BOCPD normalization mass")
            new_prob = masses / total

            growth_params = [_posterior_update(float(m), float(v), x) for m, v in zip(self.mean, self.var)]
            self.mean = np.asarray([fresh_mean] + [m for m, _ in growth_params], dtype=float)
            self.var = np.asarray([fresh_var] + [v for _, v in growth_params], dtype=float)
            self.prob = new_prob
            self.last_cp_prob = float(new_prob[0])

        self.seen += 1
        self.last_matured_end = end

    def p_monthly(self) -> float:
        if self.seen == 0:
            return 0.5
        p = 0.0
        for q, m, v in zip(self.prob, self.mean, self.var):
            p += float(q) * _norm_cdf(float(m) / sqrt(float(v)))
        return float(np.clip(p, 0.0, 1.0))

    def decision(self, signal_date: pd.Timestamp | str) -> RouterDecision:
        sd = pd.Timestamp(signal_date)
        if self.last_matured_end is not None and not self.last_matured_end < sd:
            raise ValueError("router contains non-mature information at decision time")
        p = self.p_monthly()
        if self.seen < MIN_OBS:
            state = "50-50"
        elif p < 0.25:
            state = "Annual"
        elif p > 0.75:
            state = "Monthly"
        else:
            state = "50-50"
        wa, wm = STATE_WEIGHTS[state]
        if self.seen:
            rl = np.arange(1, self.seen + 1, dtype=float)
            map_rl = int(np.argmax(self.prob)) + 1
            expected_rl = float(np.sum(self.prob * rl))
            cp = float(self.last_cp_prob)
        else:
            map_rl = 0
            expected_rl = 0.0
            cp = float("nan")
        return RouterDecision(
            signal_date=sd,
            last_matured_outcome_end=self.last_matured_end,
            observations_seen=self.seen,
            p_monthly=p,
            p_change_last_update=cp,
            map_run_length=map_rl,
            expected_run_length=expected_rl,
            state=state,
            w_annual=wa,
            w_monthly=wm,
        )


def route_trace(signal_dates, shadow_skill: pd.DataFrame) -> pd.DataFrame:
    req = {"outcome_end", "skill"}
    missing = req.difference(shadow_skill.columns)
    if missing:
        raise KeyError(sorted(missing))
    x = shadow_skill.copy()
    x["outcome_end"] = pd.to_datetime(x["outcome_end"])
    x = x.sort_values("outcome_end").reset_index(drop=True)
    r = BOCPDLocalSkillRouter()
    p = 0
    rows = []
    for sd in pd.DatetimeIndex(signal_dates).sort_values():
        while p < len(x) and pd.Timestamp(x.loc[p, "outcome_end"]) < sd:
            r.ingest(skill=float(x.loc[p, "skill"]), outcome_end=x.loc[p, "outcome_end"], current_signal_date=sd)
            p += 1
        rows.append(asdict(r.decision(sd)))
    return pd.DataFrame(rows)


def _self_test() -> None:
    r = BOCPDLocalSkillRouter()
    assert r.decision("2020-01-31").state == "50-50"
    for i in range(5):
        r.ingest(skill=1.0, outcome_end=pd.Timestamp("2019-01-01") + pd.offsets.MonthEnd(i + 1), current_signal_date="2020-12-31")
    d = r.decision("2020-12-31")
    assert d.state == "Monthly", d
    assert d.p_monthly > 0.75
    try:
        r.ingest(skill=0.0, outcome_end="2020-12-31", current_signal_date="2020-12-31")
    except ValueError:
        pass
    else:
        raise AssertionError("causality guard failed")
    print("P44_BOCPD_SELF_TEST_PASS")


if __name__ == "__main__":
    _self_test()
