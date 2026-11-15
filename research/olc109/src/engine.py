"""Causal, long-only event/account engine for policy-independent research.

Signals are evaluated at close k and become executable at open k+1+lag.
Instructions are immutable. The latest *matured* instruction supersedes any
partially filled older one; future instructions never affect today's fills.
Economic units and all accounting conventions come from the supplied OLC106
core. No simulator function writes files or mutates the supplied panel.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


def simulate(panel, f, policy, decision_mask, *, legacy, risk_target=None,
             guard_policy=None, guard_mask=None,
             lag=0, ticket=1., impact=.0015, start="2020-03-02",
             end="2026-10-30", initial=10000.):
    """Run close-decision/next-open simulation with optional sell-only controls.

    ``policy(k, current_weights)`` returns weights or ``(weights, metadata)``.
    The initial policy call is always at begin-1. Scheduled decisions take
    precedence over the daily volatility reduction, because their own targets
    are already risk-scaled. Volatility reductions use actual close holdings
    and execute sell-only, even if delayed fills or opening gaps subsequently
    change the account. Their requested signal targets remain in ``alerts``.

    ``guard_policy(k, current_weights)`` returns None, target weights, or
    ``(target_weights, metadata)`` on closes where ``guard_mask[k]`` is true.
    A missing guard mask disables guard evaluation. The callback receives a
    copy of actual close holdings and may only reduce them; additions above
    1e-12 are rejected. Genuine reductions issue forced ``TREND_REDUCE``
    instructions, with execution targets clamped to actual opening weights.
    Scheduled decisions take precedence, followed by an emitted guard, then
    volatility reduction. Guard metadata is accepted but not recorded.
    Guard instructions appear in ``alerts`` and ``instructions``; ``decisions``
    remains the initial/scheduled policy ledger. Guard callbacks cannot reenter.

    ``legacy`` is the immutable core module or its explicit source path.
    ``decisions`` contains copied pre-instruction units, cash, current weights,
    raw policy weights and final target weights, enabling matched-state replay.
    ``alerts``/``instructions`` contain all immutable target instructions.
    ``daily.nav_open`` is the account value before that open's transaction fees.
    ``panel.open_observed``, when supplied, independently gates executable
    opening quotes; close-quality flags must not censor an earlier open.
    Older panels retain their original ``observed`` opening-quote convention.
    """
    if isinstance(legacy, (str, Path)):
        spec = importlib.util.spec_from_file_location("olc106_account_core", legacy)
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
    if (not isinstance(lag, (int, np.integer)) or lag < 0 or
            not np.isfinite(initial) or initial <= 0 or
            not np.isfinite(ticket) or ticket < 0 or
            not np.isfinite(impact) or not 0 <= impact < 1):
        raise ValueError("CONFIG")
    if risk_target is not None and (not np.isfinite(risk_target) or risk_target <= 0):
        raise ValueError("RISK_TARGET")
    dates = pd.DatetimeIndex(panel["dates"])
    names = np.asarray(panel["names"])
    O = np.asarray(panel["O"], float)
    observed = np.asarray(panel["observed"], bool)
    open_observed = np.asarray(panel.get("open_observed", panel["observed"]), bool)
    close_prices = np.asarray(f["C"], float)
    mask = np.asarray(decision_mask, bool)
    n, total = len(names), len(dates)
    guard_schedule = (np.zeros(total, bool) if guard_mask is None
                      else np.asarray(guard_mask, bool))
    if (mask.shape != (total,) or guard_schedule.shape != (total,) or O.shape != (total, n) or
            observed.shape != O.shape or open_observed.shape != O.shape or
            close_prices.shape != O.shape or
            not dates.is_monotonic_increasing or dates.has_duplicates):
        raise ValueError("PANEL_OR_SCHEDULE")
    begin = int(dates.searchsorted(start))
    finish = int(dates.searchsorted(end, side="right"))
    if begin < 253 or finish - begin < 2:
        raise ValueError("WARMUP_OR_WINDOW")

    units = np.zeros(n)
    cash = float(initial)
    queue = deque()
    pending = None
    orders, alerts, daily, decisions = [], [], [], []
    deferred, maxerr = 0, 0.

    def weights_checked(value):
        w = np.array(value, dtype=float, copy=True)
        if (w.shape != (n,) or not np.isfinite(w).all() or
                np.any(w < 0) or w.sum() > 1. + 1e-9):
            raise ValueError("WEIGHTS")
        return w

    def sigma_at(k, w):
        ids = np.flatnonzero(w > 0.)
        if not len(ids):
            return 0.
        cov = legacy.covariance_at(f, k, ids)
        if not np.isfinite(cov).all():
            raise ValueError("NONFINITE_COVARIANCE")
        return float(np.sqrt(max(0., w[ids] @ cov @ w[ids])))

    def issue(k, weights, reason, force=False, raw=None):
        w = weights_checked(weights)
        w.setflags(write=False)
        due = k + 1 + lag
        instruction_id = len(alerts)
        # Tuple and read-only ndarray prohibit later signals rewriting this
        # instruction while retaining its earlier execution eligibility.
        queue.append((instruction_id, k, due, w, reason, bool(force)))
        alerts.append(dict(instruction_id=instruction_id, signal_idx=k,
                           signal_date=str(dates[k].date()), due_idx=due,
                           execution_not_before=(str(dates[due].date()) if due < total else None),
                           reason=reason, force=bool(force), gross_target=float(w.sum()),
                           positions=int((w > 0).sum()), target_weights=tuple(w.tolist()),
                           raw_weights=tuple(np.asarray(w if raw is None else raw).tolist())))
        return instruction_id

    def decide(k, reason, force=False):
        marked = np.where(np.isfinite(close_prices[k]), units * close_prices[k], 0.)
        nav = float(cash + marked.sum())
        current = marked / nav
        answer = policy(k, current.copy())
        if isinstance(answer, tuple) and len(answer) == 2 and isinstance(answer[1], dict):
            raw, metadata = answer
        else:
            raw, metadata = answer, {}
        raw = weights_checked(raw)
        target = raw.copy()
        sig = sigma_at(k, raw) if risk_target is not None else None
        if risk_target is not None:
            target *= min(1., risk_target / max(sig, 1e-12))
        iid = issue(k, target, reason, force, raw)
        decisions.append(dict(k=k, decision_idx=k, signal_idx=k,
                              signal_date=str(dates[k].date()), instruction_id=iid,
                              units=units.copy(), current_units=units.copy(), cash=float(cash),
                              current_weights=current.copy(), raw_weights=raw.copy(),
                              weights=target.copy(), meta=deepcopy(metadata),
                              raw_sigma=sig))

    decide(begin - 1, "INITIAL", True)
    for k in range(begin, finish):
        op = O[k].copy()
        op[~open_observed[k] | ~np.isfinite(op) | (op <= 0)] = np.nan
        mark = np.where(np.isfinite(op), op, close_prices[k - 1])
        if np.any((units > 1e-12) & (~np.isfinite(mark) | (mark <= 0))):
            raise AssertionError("NO_MARK_FOR_HOLDING")
        nav_open = float(cash + np.nansum(units * mark))
        # All new eligible instructions have later signal indices. Select the
        # newest eligible one, retaining future instructions untouched.
        while queue and queue[0][2] <= k:
            pending = queue.popleft()
        if pending is not None:
            iid, signal_idx, due_idx, target, reason, force = pending
            before = float(cash + np.nansum(units * mark))
            execution_target = target
            if reason in ("VOL_REDUCE", "TREND_REDUCE"):
                # Execution information only: a stale reduction must not buy
                # back an earlier sale or add a position after an opening gap.
                # Keep the immutable requested signal target in the queue and
                # alerts; clamp only this attempt's executable target.
                open_weights = np.where(np.isfinite(mark), units * mark, 0.) / before
                execution_target = np.minimum(target, open_weights)
            need = (units > 1e-10) | (execution_target > 0)
            missing = need & ~np.isfinite(op)
            units, cash, trades = legacy.rebalance(
                units, cash, op, execution_target, ticket, impact, .03, force, mark=mark)
            fees = sum(trade["cost"] for trade in trades)
            maxerr = max(maxerr, abs(cash + np.nansum(units * mark) + fees - before))
            for trade in trades:
                orders.append(dict(trade, date=str(dates[k].date()), execution_idx=k,
                                   execution_date=str(dates[k].date()), signal_idx=signal_idx,
                                   signal_date=str(dates[signal_idx].date()), due_idx=due_idx,
                                   ticker=str(names[trade["j"]]), reason=reason,
                                   instruction_id=iid))
            if missing.any():
                deferred += 1
            else:
                pending = None

        close = close_prices[k]
        if np.any((units > 1e-12) & (~np.isfinite(close) | (close <= 0))):
            raise AssertionError("NO_CLOSE_MARK_FOR_HOLDING")
        nav = float(cash + np.nansum(units * close))
        exposure = float(np.nansum(units * close) / nav)
        daily.append(dict(date=str(dates[k].date()), k=k, nav_open=nav_open,
                          nav_close=nav, cash=cash, gross=exposure,
                          positions=int((units > 1e-10).sum())))
        if k + 1 >= finish:
            continue
        if mask[k]:
            decide(k, "SCHEDULED")
        else:
            guard_issued = False
            if guard_policy is not None and guard_schedule[k]:
                holdings = np.where(np.isfinite(close), units * close, 0.) / nav
                answer = guard_policy(k, holdings.copy())
                if answer is not None:
                    if isinstance(answer, tuple) and len(answer) == 2 and isinstance(answer[1], dict):
                        answer = answer[0]
                    target = weights_checked(answer)
                    if np.any(target > holdings + 1e-12):
                        raise ValueError("GUARD_ADDS")
                    # Remove tolerated floating-point additions before storing
                    # the immutable signal target; a no-op emits no instruction.
                    target = np.minimum(target, holdings)
                    if np.any(target < holdings - 1e-12):
                        issue(k, target, "TREND_REDUCE", True, holdings)
                        guard_issued = True
            if not guard_issued and risk_target is not None and exposure > 0:
                holdings = np.where(np.isfinite(close), units * close, 0.) / nav
                sig = sigma_at(k, holdings)
                if sig > 1.25 * risk_target:
                    issue(k, holdings * (risk_target / sig), "VOL_REDUCE", True, holdings)

    order_columns = ["j", "side", "quantity", "price", "notional", "cost", "date",
                     "execution_idx", "execution_date", "signal_idx", "signal_date",
                     "due_idx", "ticker", "reason", "instruction_id"]
    instructions = pd.DataFrame(alerts)
    return dict(daily=pd.DataFrame(daily), orders=pd.DataFrame(orders, columns=order_columns),
                alerts=instructions, instructions=instructions.copy(deep=True), decisions=decisions,
                deferred_sessions=deferred, max_self_financing_error=float(maxerr))
