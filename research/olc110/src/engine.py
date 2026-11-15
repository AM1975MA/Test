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
from types import MappingProxyType

import numpy as np
import pandas as pd


def simulate(panel, f, policy, decision_mask, *, legacy, risk_target=None,
             guard_policy=None, guard_mask=None, account_policy=None,
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

    ``account_policy(k, current_weights, context)`` optionally replaces the
    initial/scheduled selector and is also called on every nonterminal Close.
    It must return a dict on initial/scheduled calls, and may return None on
    other calls. The dict contains ``weights`` and optionally ``action_mask``
    (a boolean vector, None means all assets), ``sell_only``, ``force``,
    ``reason``, and ``meta``. Initial/scheduled instructions must be full.
    Context contains detached account arrays, cash/nav, initial/scheduled
    flags, immutable pending/queued instruction summaries, and last actual
    buy/sell indices (-1 before any fill). No callback receives future data.

    Targeted instructions preserve quantities outside their immutable mask.
    Unaffected accepted Opens still mark NAV but are never executable quotes.
    Signal targets preserve unaffected exposure and cap the involved budget;
    the core then limits buys to actual cash after selling involved assets.
    Sell-only instructions reject signal additions within their action mask
    and clamp stale targets to actual opening exposure. All emitted account
    decisions and metadata are recorded. When ``account_policy`` is None,
    original outputs are unchanged.

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
    if account_policy is not None and not callable(account_policy):
        raise ValueError("ACCOUNT_POLICY")
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
    last_buy_idx = np.full(n, -1, dtype=int)
    last_sell_idx = np.full(n, -1, dtype=int)
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

    def issue(k, weights, reason, force=False, raw=None, *, action_mask=None,
              sell_only=False, meta=None):
        w = weights_checked(weights)
        w.setflags(write=False)
        if action_mask is not None:
            action_mask = np.array(action_mask, dtype=bool, copy=True)
            action_mask.setflags(write=False)
        due = k + 1 + lag
        instruction_id = len(alerts)
        # Tuple and read-only ndarray prohibit later signals rewriting this
        # instruction while retaining its earlier execution eligibility.
        queue.append((instruction_id, k, due, w, reason, bool(force),
                      action_mask, bool(sell_only)))
        alerts.append(dict(instruction_id=instruction_id, signal_idx=k,
                           signal_date=str(dates[k].date()), due_idx=due,
                           execution_not_before=(str(dates[due].date()) if due < total else None),
                           reason=reason, force=bool(force), gross_target=float(w.sum()),
                           positions=int((w > 0).sum()), target_weights=tuple(w.tolist()),
                           raw_weights=tuple(np.asarray(w if raw is None else raw).tolist())))
        if account_policy is not None:
            alerts[-1].update(action_indices=(None if action_mask is None else
                                             np.flatnonzero(action_mask).tolist()),
                              sell_only=bool(sell_only or reason in ("VOL_REDUCE", "TREND_REDUCE")),
                              meta=deepcopy({} if meta is None else meta))
        return instruction_id

    def instruction_summary(instruction):
        if instruction is None:
            return None
        iid, signal_idx, due_idx, target, reason, force, action_mask, sell_only = instruction
        # Only immutable scalars/tuples are exposed. The mapping has no links
        # back to either mutable ledger rows or the executable instruction.
        return MappingProxyType(dict(instruction_id=iid, signal_idx=signal_idx,
                                     due_idx=due_idx, target_weights=tuple(target.tolist()),
                                     reason=reason, force=force, sell_only=sell_only,
                                     action_indices=(None if action_mask is None else
                                                     tuple(np.flatnonzero(action_mask).tolist()))))

    def readonly_copy(values):
        copied = values.copy()
        copied.setflags(write=False)
        return copied

    def account_decide(k, *, initial_call=False, scheduled=False):
        marked = np.where(np.isfinite(close_prices[k]), units * close_prices[k], 0.)
        nav = float(cash + marked.sum())
        current = marked / nav
        context = dict(initial=bool(initial_call), scheduled=bool(scheduled),
                       units=readonly_copy(units), cash=float(cash), nav=nav,
                       pending=instruction_summary(pending),
                       queued=tuple(instruction_summary(item) for item in queue),
                       last_buy_idx=readonly_copy(last_buy_idx),
                       last_sell_idx=readonly_copy(last_sell_idx))
        answer = account_policy(k, current.copy(), context)
        full_decision = initial_call or scheduled
        if answer is None:
            if full_decision:
                raise ValueError("ACCOUNT_POLICY_REQUIRED")
            return False
        if (not isinstance(answer, dict) or "weights" not in answer or
                not isinstance(answer.get("meta", {}), dict)):
            raise ValueError("ACCOUNT_POLICY_RESULT")
        raw = weights_checked(answer["weights"])
        target = raw.copy()
        action_mask = answer.get("action_mask")
        if action_mask is not None:
            action_mask = np.asarray(action_mask)
            if action_mask.shape != (n,) or action_mask.dtype.kind != "b":
                raise ValueError("ACTION_MASK")
            action_mask = action_mask.copy()
            if full_decision:
                if not action_mask.all():
                    raise ValueError("ACCOUNT_SCHEDULED_MASK")
                action_mask = None
        sell_only = bool(answer.get("sell_only", False))
        if sell_only:
            additions = raw > current + 1e-12
            if action_mask is not None:
                additions &= action_mask
            if np.any(additions):
                raise ValueError("ACCOUNT_ADDS")
            target = np.minimum(target, current)
        if action_mask is not None:
            # The callback may supply a sparse target. Restore the accounting
            # budget of frozen holdings before allocating the involved slice.
            target[~action_mask] = current[~action_mask]
            budget = max(0., 1. - float(current[~action_mask].sum()))
            requested = float(target[action_mask].sum())
            if requested > budget:
                target[action_mask] *= budget / requested
        sig = sigma_at(k, raw) if risk_target is not None and full_decision else None
        if sig is not None:
            target *= min(1., risk_target / max(sig, 1e-12))
        reason = answer.get("reason", "INITIAL" if initial_call else
                            "SCHEDULED" if scheduled else "ACCOUNT_POLICY")
        if not isinstance(reason, str):
            raise ValueError("ACCOUNT_POLICY_RESULT")
        force = bool(answer.get("force", initial_call))
        metadata = deepcopy(answer.get("meta", {}))
        iid = issue(k, target, reason, force, raw, action_mask=action_mask,
                    sell_only=sell_only, meta=metadata)
        decisions.append(dict(k=k, decision_idx=k, signal_idx=k,
                              signal_date=str(dates[k].date()), instruction_id=iid,
                              units=units.copy(), current_units=units.copy(), cash=float(cash),
                              current_weights=current.copy(), raw_weights=raw.copy(),
                              weights=target.copy(), meta=metadata, raw_sigma=sig,
                              initial=bool(initial_call), scheduled=bool(scheduled),
                              reason=reason, force=force, sell_only=sell_only,
                              action_indices=(None if action_mask is None else
                                              np.flatnonzero(action_mask).tolist())))
        return True

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

    if account_policy is None:
        decide(begin - 1, "INITIAL", True)
    else:
        account_decide(begin - 1, initial_call=True)
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
            iid, signal_idx, due_idx, target, reason, force, action_mask, sell_only = pending
            before = float(cash + np.nansum(units * mark))
            execution_target = target
            if sell_only or reason in ("VOL_REDUCE", "TREND_REDUCE"):
                # Execution information only: a stale reduction must not buy
                # back an earlier sale or add a position after an opening gap.
                # Keep the immutable requested signal target in the queue and
                # alerts; clamp only this attempt's executable target.
                open_weights = np.where(np.isfinite(mark), units * mark, 0.) / before
                execution_target = np.minimum(target, open_weights)
            need = (units > 1e-10) | (execution_target > 0)
            execution_prices = op
            if action_mask is not None:
                # Preserve full-account marks while removing all execution
                # eligibility outside this instruction's immutable mask.
                execution_prices = op.copy()
                execution_prices[~action_mask] = np.nan
                need &= action_mask
            missing = need & ~np.isfinite(execution_prices)
            units, cash, trades = legacy.rebalance(
                units, cash, execution_prices, execution_target, ticket, impact, .03, force, mark=mark)
            fees = sum(trade["cost"] for trade in trades)
            maxerr = max(maxerr, abs(cash + np.nansum(units * mark) + fees - before))
            for trade in trades:
                if trade["side"] == "BUY":
                    last_buy_idx[trade["j"]] = k
                elif trade["side"] == "SELL":
                    last_sell_idx[trade["j"]] = k
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
        if account_policy is not None:
            account_issued = account_decide(k, scheduled=bool(mask[k]))
            if mask[k] or account_issued:
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
