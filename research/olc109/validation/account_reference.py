"""OLC109 independent OLC107 account audit; imports neither engine nor strategy code.

Reconstructs cash, units, actual holdings P&L, fees, open/close NAV and metrics
from immutable prices plus saved orders. It also checks instruction chronology
against the newest eligible target, including partial fills. This cannot certify
point-in-time universes, adjusted-price provenance, or economic independence.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd


SCENARIOS = {"BASE": (1., .0015, 0), "ZERO_COST": (0., 0., 0),
             "DOUBLE_COST": (2., .003, 0), "LAG1": (1., .0015, 1),
             "LAG2": (1., .0015, 2)}


def vector(value, n):
    if isinstance(value, str):
        value = ast.literal_eval(value)
    a = np.asarray(value, dtype=float)
    assert a.shape == (n,) and np.isfinite(a).all(), "INVALID_TARGET"
    assert a.min() >= 0 and a.sum() <= 1 + 1e-9, "INVALID_TARGET_WEIGHTS"
    return a


def truth(value):
    if isinstance(value, str):
        assert value.lower() in ("true", "false"), "INVALID_BOOLEAN"
        return value.lower() == "true"
    return bool(value)


def prepare_panel(p):
    dates = pd.DatetimeIndex(p["dates"])
    names = list(map(str, p["names"]))
    assert dates.is_monotonic_increasing and not dates.has_duplicates
    assert len(names) == len(set(names)), "DUPLICATE_INSTRUMENT_ID"
    obs = np.asarray(p["observed"], bool)
    open_obs = np.asarray(p.get("open_observed", p["observed"]), bool)
    raw_o, raw_c = np.asarray(p["O"], float), np.asarray(p["C"], float)
    assert obs.shape == open_obs.shape == raw_o.shape == raw_c.shape == (len(dates), len(names))
    # Opening availability is independent of later close-quality checks.
    # The fallback preserves the convention of legacy frozen panels.
    valid_o = open_obs & np.isfinite(raw_o) & (raw_o > 0)
    valid_c = obs & np.isfinite(raw_c) & (raw_c > 0)
    C = pd.DataFrame(np.where(valid_c, raw_c, np.nan)).ffill().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        returns = np.vstack([np.full((1, len(names)), np.nan),
                             np.log(C[1:] / C[:-1])])
    return dict(dates=dates, names=names, obs=obs, O=raw_o, C=C,
                valid_o=valid_o, returns=returns)


def expected_execution(units, cash, opening, marks, target, ticket, impact, forced):
    """Independent order sizing from the frozen execution contract.

    No production simulator, rebalance function, or selector is imported.
    Budgets use opening pre-fee wealth. Sales free cash first; all eligible buy
    requests share one financing ratio after reserving their fixed tickets.
    """
    held = np.array(units, float, copy=True)
    valuation = np.nan_to_num(marks, nan=0.)
    wealth = float(cash + np.dot(held, valuation))
    budget = wealth * np.asarray(target)
    tolerance = max(1e-8, 0. if forced else .03 * wealth)
    result = []
    available = float(cash)
    quoted = np.isfinite(opening) & (opening > 0)
    for j in range(len(held)):
        excess = held[j] * valuation[j] - budget[j]
        if not quoted[j] or excess <= 1e-8:
            continue
        if excess < tolerance and target[j] != 0:
            continue
        amount = min(held[j], excess / opening[j]) * opening[j]
        charge = ticket + impact * amount
        if amount <= charge and available + amount < charge:
            continue
        quantity = min(held[j], excess / opening[j])
        held[j] -= quantity
        available += amount - charge
        result.append(dict(j=j, side="SELL", quantity=float(quantity),
                           price=float(opening[j]), notional=float(amount), cost=float(charge)))
    requested = budget - held * valuation
    purchases = [j for j in range(len(held)) if quoted[j] and requested[j] > 1e-8
                 and requested[j] >= tolerance and requested[j] > ticket]
    if purchases and available > ticket * len(purchases):
        financing = min(1., (available - ticket * len(purchases)) /
                        ((1. + impact) * sum(requested[j] for j in purchases)))
        for j in purchases:
            amount = float(requested[j] * financing)
            if amount <= 1e-8:
                continue
            result.append(dict(j=j, side="BUY", quantity=float(amount / opening[j]),
                               price=float(opening[j]), notional=amount,
                               cost=float(ticket + impact * amount)))
    return result


def audit_account(p, daily, orders, instructions, metadata, *, initial=10000., state_checker=None):
    """Return independent metrics, attribution and annual returns for one path."""
    dates, names, C = p["dates"], p["names"], p["C"]
    n = len(names)
    lookup = {name: j for j, name in enumerate(names)}
    date_to_k = {str(d.date()): k for k, d in enumerate(dates)}
    begin, finish = dates.searchsorted("2020-03-02"), dates.searchsorted("2026-10-30", side="right")
    expected_dates = [str(d.date()) for d in dates[begin:finish]]
    assert daily.date.tolist() == expected_dates, "INCOMPLETE_OR_REORDERED_DAILY_PATH"
    ticket, impact, lag = SCENARIOS[metadata["scenario"]]
    assert np.isclose(metadata["ticket"], ticket, rtol=0, atol=1e-14)
    assert np.isclose(metadata["impact_bps"], impact * 10000, rtol=0, atol=1e-14)
    assert metadata["lag_extra"] == lag
    assert not instructions.instruction_id.duplicated().any(), "DUPLICATE_INSTRUCTION"
    ins = instructions.sort_values("instruction_id").to_dict("records")
    assert len(ins) and [int(r["instruction_id"]) for r in ins] == list(range(len(ins)))
    previous_signal = -1
    for r in ins:
        k = int(r["signal_idx"])
        assert previous_signal < k < finish - 1, "INVALID_SIGNAL_ORDER"
        assert k >= begin - 1 and r["signal_date"] == str(dates[k].date())
        assert int(r["due_idx"]) == k + 1 + lag, "WRONG_TARGET_DUE_DATE"
        due = int(r["due_idx"])
        if due < len(dates):
            assert r["execution_not_before"] == str(dates[due].date())
        r["target"] = vector(r["target_weights"], n)
        vector(r["raw_weights"], n)
        assert abs(float(r["gross_target"]) - r["target"].sum()) < 1e-10
        assert int(r["positions"]) == int((r["target"] > 0).sum())
        assert truth(r["force"]) == (r["reason"] in ("INITIAL", "VOL_REDUCE", "TREND_REDUCE"))
        previous_signal = k
    assert int(ins[0]["signal_idx"]) == begin - 1 and ins[0]["reason"] == "INITIAL"
    assert orders.empty or set(orders.date) <= set(expected_dates), "ORDER_OUTSIDE_WINDOW"
    grouped = {day: group.to_dict("records") for day, group in orders.groupby("date", sort=False)}

    units, cash = np.zeros(n), float(initial)
    gross_pnl, fees_by_asset = np.zeros(n), np.zeros(n)
    bought, sold = np.zeros(n), np.zeros(n)
    held_sessions = np.zeros(n, dtype=int)
    calc_close, calc_open = [], []
    max_nav_error = max_cost_error = max_attribution_error = 0.
    min_cash, min_units = cash, 0.
    previous_nav, pending, next_instruction, timestamps = initial, None, 0, 0
    deferred = 0
    numerical_only_deferred = 0
    quantity_checks = 0
    if state_checker is not None:
        state_checker(begin - 1, units.copy(), cash)
    for bar in daily.to_dict("records"):
        day = bar["date"]
        k = date_to_k[day]
        assert int(bar["k"]) == k
        op = np.where(p["valid_o"][k], p["O"][k], np.nan)
        mark = np.where(np.isfinite(op), op, C[k - 1])
        assert np.all(np.isfinite(mark[units > 1e-12])), "UNMARKED_OPEN_POSITION"
        old_units = units.copy()
        before = float(cash + np.nansum(units * mark))
        calc_open.append(before)
        max_nav_error = max(max_nav_error, abs(before - bar["nav_open"]))
        overnight = np.where(old_units != 0, old_units * (mark - C[k - 1]), 0.)
        while next_instruction < len(ins) and ins[next_instruction]["due_idx"] <= k:
            pending = ins[next_instruction]
            next_instruction += 1
        trades = grouped.get(day, [])
        assert pending is not None or not trades, "ORDER_WITHOUT_PENDING_TARGET"
        executable_target = None if pending is None else pending["target"]
        if pending is not None and pending["reason"] in ("VOL_REDUCE", "TREND_REDUCE"):
            executable_target = np.minimum(executable_target, np.nan_to_num(units * mark, nan=0.) / before)
        missing = (np.zeros(n, dtype=bool) if pending is None else
                   ((units > 1e-10) | (executable_target > 0)) & ~np.isfinite(op))
        if pending is not None:
            expected = expected_execution(units, cash, op, mark, executable_target,
                                          ticket, impact, truth(pending["force"]))
            assert len(expected) == len(trades), ("ORDER_COUNT_VS_TARGET", day, len(expected), len(trades))
            for actual, wanted in zip(trades, expected):
                assert int(actual["j"]) == wanted["j"] and actual["side"] == wanted["side"], ("ORDER_IDENTITY_VS_TARGET", day)
                for field in ("quantity", "price", "notional", "cost"):
                    assert np.isclose(float(actual[field]), wanted[field], rtol=1e-10, atol=1e-7), ("ORDER_VALUE_VS_TARGET", day, field, actual[field], wanted[field])
                quantity_checks += 1
        daily_cost = 0.
        buy_seen = False
        for trade in trades:
            iid = int(trade["instruction_id"])
            assert iid == pending["instruction_id"], "ORDER_NOT_FROM_LATEST_MATURED_TARGET"
            j = lookup[trade["ticker"]]
            assert int(trade["j"]) == j
            q, price = float(trade["quantity"]), float(trade["price"])
            assert np.isfinite(q) and q > 0 and np.isfinite(price) and price > 0
            assert p["valid_o"][k, j], "FILL_WITHOUT_VALID_OBSERVED_OPEN"
            assert abs(price - op[j]) <= max(1e-9, abs(op[j]) * 1e-12), "WRONG_FILL_PRICE"
            assert int(trade["execution_idx"]) == k and trade["execution_date"] == day
            assert int(trade["signal_idx"]) == pending["signal_idx"]
            assert trade["signal_date"] == pending["signal_date"]
            assert int(trade["due_idx"]) == pending["due_idx"]
            assert trade["reason"] == pending["reason"]
            if pending["reason"] in ("VOL_REDUCE", "TREND_REDUCE"):
                assert trade["side"] == "SELL", "RISK_REDUCTION_MUST_NOT_BUY"
            assert k >= pending["signal_idx"] + 1 + lag, "SAME_DATE_OR_EARLY_EXECUTION"
            notional = q * price
            assert abs(notional - trade["notional"]) <= max(1e-7, abs(notional) * 1e-12)
            cost = ticket + impact * notional
            max_cost_error = max(max_cost_error, abs(cost - trade["cost"]))
            if trade["side"] == "BUY":
                buy_seen = True
                units[j] += q
                cash -= notional + cost
                bought[j] += notional
            else:
                assert trade["side"] == "SELL", "INVALID_SIDE"
                assert not buy_seen, "SALES_MUST_PRECEDE_PURCHASES"
                units[j] -= q
                cash += notional - cost
                sold[j] += notional
            min_cash, min_units = min(min_cash, cash), min(min_units, float(units.min()))
            assert cash >= -1e-6 and units.min() >= -1e-8, "LEVERAGE_OR_SHORTS"
            fees_by_asset[j] += cost
            daily_cost += cost
            timestamps += 1
        if pending is not None:
            if missing.any():
                deferred += 1
                if np.all(units[missing] <= 1e-10) and np.all(executable_target[missing] <= 1e-10):
                    numerical_only_deferred += 1
            else:
                pending = None
        assert np.all(np.isfinite(C[k, units > 1e-12])), "UNMARKED_CLOSE_POSITION"
        intraday = np.where(units != 0, units * (C[k] - mark), 0.)
        contribution = np.nan_to_num(overnight, nan=0.) + np.nan_to_num(intraday, nan=0.)
        gross_pnl += contribution
        held_sessions += ((old_units > 1e-10) | (units > 1e-10)).astype(int)
        assets = float(np.nansum(units * C[k]))
        nav = cash + assets
        assert nav > 0 and assets / nav <= 1 + 1e-9
        max_nav_error = max(max_nav_error, abs(nav - bar["nav_close"]), abs(cash - bar["cash"]))
        assert abs(assets / nav - bar["gross"]) < 1e-9
        assert int((units > 1e-10).sum()) == int(bar["positions"])
        attribution_error = abs(nav - previous_nav - contribution.sum() + daily_cost)
        max_attribution_error = max(max_attribution_error, float(attribution_error))
        calc_close.append(nav)
        previous_nav = nav
        if state_checker is not None and k + 1 < finish:
            state_checker(k, units.copy(), cash)

    a, opens = np.asarray(calc_close), np.asarray(calc_open)
    days = (dates[finish - 1] - dates[begin]).days + 1
    cagr = float(np.expm1(np.log(a[-1] / initial) * 365.2425 / days))
    close_chain = np.r_[initial, a]
    sampled_chain = np.r_[initial, np.column_stack([opens, a]).ravel()]
    dd = float(np.min(sampled_chain / np.maximum.accumulate(sampled_chain) - 1))
    dd_close = float(np.min(close_chain / np.maximum.accumulate(close_chain) - 1))
    calmar = cagr / abs(dd) if dd < 0 else float("nan")
    lr = np.diff(np.log(close_chain))
    independent = dict(cagr=cagr, cumulative=float(a[-1] / initial - 1),
                       maxdd_close=dd_close, maxdd_sampled=dd, calmar=calmar,
                       volatility=float(lr.std(ddof=1) * np.sqrt(252)),
                       worst_21_sessions=float(np.expm1(pd.Series(lr).rolling(min(21, len(a))).sum().min())),
                       end_equity=float(a[-1]), days=int(days),
                       costs=float(fees_by_asset.sum()), orders=len(orders))
    for key, value in independent.items():
        if key not in metadata:
            continue
        actual = float(metadata[key])
        assert np.isclose(value, actual, rtol=1e-10, atol=1e-8, equal_nan=True), ("METRIC", key, value, actual)
    assert max_nav_error < 1e-5 and max_cost_error < 1e-7 and max_attribution_error < 1e-7
    assert abs(gross_pnl.sum() - fees_by_asset.sum() - (a[-1] - initial)) < 1e-5
    if metadata["arm"] == "PASSIVE":
        assert len(orders) == 1 and orders.iloc[0]["side"] == "BUY"
        trade = orders.iloc[0]
        j = lookup[trade.ticker]
        passive_expected = (initial - ticket) / (1 + impact) / trade.price * C[finish - 1, j]
        assert abs(passive_expected - a[-1]) < 1e-5, "PASSIVE_RATIO"
    independent.update(max_nav_cash_error=float(max_nav_error),
                       max_per_order_cost_error=float(max_cost_error),
                       max_daily_pnl_attribution_error=float(max_attribution_error),
                       min_cash=float(min_cash), min_units=float(min_units),
                       order_timestamps_checked=int(timestamps),
                       order_quantities_independently_checked=int(quantity_checks),
                       deferred_sessions_reconstructed=int(deferred),
                       numerical_residue_only_deferred_sessions=int(numerical_only_deferred),
                       trading_days=int(orders.date.nunique()),
                       trading_days_per_year=float(orders.date.nunique() / (days / 365.2425)),
                       average_gross=float(daily.gross.mean()))
    attribution = [dict(ticker=names[j], gross_pnl=float(gross_pnl[j]),
                        costs=float(fees_by_asset[j]), net_pnl=float(gross_pnl[j] - fees_by_asset[j]),
                        buy_notional=float(bought[j]), sell_notional=float(sold[j]),
                        held_sessions=int(held_sessions[j])) for j in range(n)
                   if held_sessions[j] or fees_by_asset[j]]
    years = dates[begin:finish].year
    annual, previous = [], initial
    for year in sorted(set(years)):
        ids = np.flatnonzero(years == year)
        annual.append(dict(year=int(year), annual_return=float(a[ids[-1]] / previous - 1),
                           period_start=str(dates[begin + ids[0]].date()),
                           period_end=str(dates[begin + ids[-1]].date()),
                           partial_year=year in (2020, 2026)))
        previous = a[ids[-1]]
    return independent, attribution, annual

