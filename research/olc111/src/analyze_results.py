"""Independent, deterministic diagnostics for the completed OLC111 matrix.

No model is fitted or selected here. Account metrics are reproduced from ledgers;
actual-held quote support is audited without changing any recorded performance.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ARMS = ("BASE", "STATIC_75", "MEAN", "PRICE", "VIX", "TERM")
SCENARIOS = ("NEXT_CLOSE", "DOUBLE_COST", "NEXT_OPEN")
ACTIONS = ("CASH", "FRESH", "ENTRY")
YEAR_DAYS = 365.2425
INITIAL_CAPITAL = 10000.0


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _validate_daily(daily):
    needed = {"k", "date", "nav_open", "nav_close", "cash", "gross", "positions"}
    if not needed.issubset(daily.columns) or not len(daily):
        raise ValueError("DAILY_SCHEMA_OR_EMPTY")
    dates = pd.DatetimeIndex(daily.date)
    k = daily.k.to_numpy(float)
    values = daily[["nav_open", "nav_close", "cash", "gross", "positions"]].to_numpy(float)
    if (dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing
            or not np.isfinite(k).all() or np.any(k != np.floor(k))
            or np.any(np.diff(k) <= 0) or not np.isfinite(values).all()
            or np.any(values[:, :2] <= 0)):
        raise ValueError("INVALID_DAILY_NAV_OR_CALENDAR")
    return dates, k.astype(int)


def _window(daily, start_idx=None, end_idx=None, initial_nav=INITIAL_CAPITAL):
    dates, k = _validate_daily(daily)
    keep = np.ones(len(daily), bool)
    if start_idx is not None:
        keep &= k >= int(start_idx)
    if end_idx is not None:
        keep &= k <= int(end_idx)
    positions = np.flatnonzero(keep)
    if not len(positions):
        return None
    first = int(positions[0])
    anchor = float(initial_nav if first == 0 else daily.nav_close.iloc[first-1])
    if not np.isfinite(anchor) or anchor <= 0:
        raise ValueError("INVALID_WINDOW_ANCHOR")
    return (daily.iloc[positions].reset_index(drop=True), anchor,
            None if first == 0 else str(dates[first-1].date()),
            int(k[first]-1 if first == 0 else k[first-1]))


def _sample_chain(frame, anchor, anchor_date, anchor_idx):
    wealth = np.r_[anchor, frame[["nav_open", "nav_close"]].to_numpy(float).ravel()]
    dates = [anchor_date] + [str(d) for d in frame.date for _ in range(2)]
    indices = np.r_[anchor_idx, np.repeat(frame.k.to_numpy(int), 2)]
    kinds = ["INITIAL_OR_ANCHOR"] + [kind for _ in range(len(frame)) for kind in ("PRE_FEES", "CLOSE")]
    return wealth, dates, indices, kinds


def _worst_drawdown(frame, anchor, anchor_date, anchor_idx):
    wealth, dates, indices, kinds = _sample_chain(frame, anchor, anchor_date, anchor_idx)
    high = np.maximum.accumulate(wealth)
    dd = wealth/high - 1.0
    trough = int(np.argmin(dd))
    depth = float(dd[trough])
    if depth >= 0:
        return dict(depth=0.0, peak_date=None, trough_date=None, recovery_date=None,
                    peak_idx=None, trough_idx=None, recovery_idx=None,
                    peak_sample=None, trough_sample=None, recovery_sample=None,
                    recovered=True, sessions_peak_to_trough=0, sessions_peak_to_recovery=0)
    peak = int(np.flatnonzero(wealth[:trough+1] == high[trough])[-1])
    recoveries = np.flatnonzero(wealth[trough+1:] >= high[trough])
    recovery = None if not len(recoveries) else int(trough+1+recoveries[0])
    return dict(depth=depth, peak_date=dates[peak], trough_date=dates[trough],
                recovery_date=None if recovery is None else dates[recovery],
                peak_idx=int(indices[peak]), trough_idx=int(indices[trough]),
                recovery_idx=None if recovery is None else int(indices[recovery]),
                peak_sample=kinds[peak], trough_sample=kinds[trough],
                recovery_sample=None if recovery is None else kinds[recovery],
                peak_nav=float(wealth[peak]), trough_nav=float(wealth[trough]),
                recovered=recovery is not None,
                sessions_peak_to_trough=int(indices[trough]-indices[peak]),
                sessions_peak_to_recovery=None if recovery is None else int(indices[recovery]-indices[peak]))


def performance_window(daily, *, start_idx=None, end_idx=None, initial_nav=INITIAL_CAPITAL):
    """Reproduce native calendar CAGR and preserve the actual preceding NAV."""
    selected = _window(daily, start_idx, end_idx, initial_nav)
    if selected is None:
        return None
    frame, anchor, anchor_date, anchor_idx = selected
    dates = pd.DatetimeIndex(frame.date)
    close = frame.nav_close.to_numpy(float)
    chain = np.r_[anchor, close]
    log_returns = np.diff(np.log(chain))
    days = max(1, int((dates[-1]-dates[0]).days)+1)
    log_growth = float(np.log(close[-1]/anchor))
    cagr = float(np.expm1(log_growth * YEAR_DAYS/days))
    close_dd = float(np.min(chain/np.maximum.accumulate(chain)-1))
    episode = _worst_drawdown(frame, anchor, anchor_date, anchor_idx)
    n = min(21, len(frame))
    worst21 = float(np.expm1(pd.Series(log_returns).rolling(n).sum().min()))
    gross = frame.gross.to_numpy(float)
    return dict(initial_nav=anchor, anchor_date=anchor_date, anchor_idx=anchor_idx,
        start_idx=int(frame.k.iloc[0]), end_idx=int(frame.k.iloc[-1]),
        start_date=str(dates[0].date()), end_date=str(dates[-1].date()),
        sessions=len(frame), days=days, calendar_convention="inclusive_first_to_last_observation_dates",
        cumulative=float(close[-1]/anchor-1), log_growth=log_growth, cagr=cagr,
        maxdd_close=close_dd, maxdd_sampled=episode["depth"], worst_drawdown=episode,
        calmar=None if episode["depth"] == 0 else cagr/abs(episode["depth"]),
        volatility=float(log_returns.std(ddof=1)*np.sqrt(252)) if len(log_returns)>1 else 0.0,
        worst_21_sessions=worst21, end_equity=float(close[-1]),
        mean_exposure=float(gross.mean()), min_exposure=float(gross.min()), max_exposure=float(gross.max()),
        exposure_q05=float(np.quantile(gross, .05)), exposure_median=float(np.median(gross)),
        exposure_q95=float(np.quantile(gross, .95)), mean_cash_share=float((1-gross).mean()),
        full_cash_days=int((gross <= 1e-8).sum()), mean_positions=float(frame.positions.mean()),
        end_cash=float(frame.cash.iloc[-1]))


def cash_spells(daily):
    """Observed-close cash spells, including calendar gaps and boundary censoring."""
    dates, _ = _validate_daily(daily)
    cash = daily.gross.to_numpy(float) <= 1e-8
    spells = []
    start = None
    for i, is_cash in enumerate(np.r_[cash, False]):
        if is_cash and start is None:
            start = i
        if not is_cash and start is not None:
            end = i-1
            right = i == len(daily)
            spells.append(dict(start_idx=int(daily.k.iloc[start]), end_idx=int(daily.k.iloc[end]),
                start_date=str(dates[start].date()), last_cash_close_date=str(dates[end].date()),
                cash_sessions=end-start+1, left_censored=start == 0, right_censored=right,
                next_invested_close_date=None if right else str(dates[i].date()),
                observed_close_calendar_span_days=int((dates[end]-dates[start]).days),
                calendar_days_until_next_invested_close=None if right else int((dates[i]-dates[start]).days)))
            start = None
    return spells


def intervention_summary(trace, orders, *, last_idx):
    """Count filled instructions, with completed21-session spacing by signal date."""
    episodes = []
    if len(orders):
        required = {"reason", "instruction_id", "signal_idx", "execution_idx", "notional"}
        if not required.issubset(orders.columns):
            raise ValueError("ORDER_ACTION_SCHEMA")
        for (action, iid), group in orders.loc[orders.reason.isin(ACTIONS)].groupby(["reason", "instruction_id"]):
            if group.signal_idx.nunique() != 1:
                raise ValueError("INSTRUCTION_MULTIPLE_SIGNAL_DATES")
            signal = int(group.signal_idx.iloc[0])
            episodes.append(dict(action=action, instruction_id=int(iid), signal_idx=signal,
                first_execution_idx=int(group.execution_idx.min()), last_execution_idx=int(group.execution_idx.max()),
                orders=len(group), notional=float(group.notional.sum()),
                completed21=signal+21 <= int(last_idx), selected_nonoverlap=False))
    columns = ["action", "instruction_id", "signal_idx", "first_execution_idx", "last_execution_idx",
               "orders", "notional", "completed21", "selected_nonoverlap"]
    frame = pd.DataFrame(episodes, columns=columns)
    summary = {}
    for action in ACTIONS:
        selected = frame.loc[(frame.action == action) & frame.completed21].sort_values(["signal_idx", "instruction_id"])
        previous = None
        for row in selected.itertuples():
            if previous is None or row.signal_idx >= previous+21:
                frame.loc[row.Index, "selected_nonoverlap"] = True
                previous = int(row.signal_idx)
        action_frame = frame.loc[frame.action == action]
        intended = (int(trace.loc[trace.action == action, "k"].nunique())
                    if {"action", "k"}.issubset(trace.columns) else 0)
        separated = int(action_frame.selected_nonoverlap.sum())
        summary[action] = dict(intended_signals=intended, realized_instructions=len(action_frame),
            completed21_instructions=int(action_frame.completed21.sum()),
            separated_completed21_episodes=separated,
            at_least12_separated_completed21=separated >= 12,
            temporal_completion_only=True)
    return summary, frame


def warmup_replication(base, candidate, *, ready_idx):
    """Exact account-state equality through the readiness decision Close."""
    _validate_daily(base)
    _validate_daily(candidate)
    last = int(base.k.iloc[-1]) if ready_idx is None else int(ready_idx)
    a = base.loc[base.k <= last].reset_index(drop=True)
    b = candidate.loc[candidate.k <= last].reset_index(drop=True)
    calendar = a[["k", "date"]].equals(b[["k", "date"]])
    fields = ("nav_open", "nav_close", "cash", "gross", "positions")
    differences = {}
    for field in fields:
        if not calendar or len(a) != len(b):
            differences[field] = None
        else:
            differences[field] = float(np.max(np.abs(a[field].to_numpy(float)-b[field].to_numpy(float)))) if len(a) else 0.0
    exact = calendar and all(value == 0.0 for value in differences.values())
    return dict(exact_match=bool(exact), calendar_match=bool(calendar), sessions=len(a),
                through_idx=last, maximum_absolute_differences=differences)


def term_vix_comparison(term, vix, *, start_idx=None, initial_nav=INITIAL_CAPITAL):
    """Paired arithmetic and additive log-growth attribution; no significance claim."""
    if not term[["k", "date"]].equals(vix[["k", "date"]]):
        raise ValueError("TERM_VIX_CALENDAR_MISMATCH")
    tm = performance_window(term, start_idx=start_idx, initial_nav=initial_nav)
    vm = performance_window(vix, start_idx=start_idx, initial_nav=initial_nav)
    if tm is None or vm is None:
        return None, pd.DataFrame()
    rows = term.loc[term.k >= tm["start_idx"]]
    years = pd.to_datetime(rows.date).dt.year
    annual = []
    for year in sorted(years.unique()):
        indices = rows.loc[years == year, "k"]
        left, right = int(indices.min()), int(indices.max())
        ta = performance_window(term, start_idx=left, end_idx=right, initial_nav=initial_nav)
        va = performance_window(vix, start_idx=left, end_idx=right, initial_nav=initial_nav)
        annual.append(dict(year=int(year), start_date=ta["start_date"], end_date=ta["end_date"],
            term_return=ta["cumulative"], vix_return=va["cumulative"],
            simple_return_difference=ta["cumulative"]-va["cumulative"],
            log_increment_term_minus_vix=ta["log_growth"]-va["log_growth"]))
    annual = pd.DataFrame(annual)
    deltas = annual.log_increment_term_minus_vix.to_numpy(float)
    positive = np.maximum(deltas, 0)
    total = tm["log_growth"]-vm["log_growth"]
    summary = dict(start_date=tm["start_date"], end_date=tm["end_date"],
        cagr_term=tm["cagr"], cagr_vix=vm["cagr"], cagr_difference=tm["cagr"]-vm["cagr"],
        total_log_increment=total, annualized_log_increment=total*YEAR_DAYS/tm["days"],
        ending_relative_wealth_ratio=float(np.exp(total)),
        maxdd_difference=tm["maxdd_sampled"]-vm["maxdd_sampled"],
        mean_exposure_difference=tm["mean_exposure"]-vm["mean_exposure"],
        positive_years=int((deltas>0).sum()), negative_years=int((deltas<0).sum()),
        positive_year_share_of_positive_increment_max=None if positive.sum()==0 else float(positive.max()/positive.sum()),
        largest_year_share_of_absolute_increment=None if np.abs(deltas).sum()==0 else float(np.abs(deltas).max()/np.abs(deltas).sum()),
        total_log_increment_without_largest_positive_year=float(total-positive.max()),
        attribution_ties=bool(np.isclose(deltas.sum(), total, rtol=0, atol=1e-12)),
        inference="exploratory_historical_comparison_not_independent_validation")
    return summary, annual


def held_mark_audit(daily, orders, panel, *, initial_cash=INITIAL_CAPITAL, max_age_days=5):
    """Reconstruct filled holdings/cash and audit accepted-source ages at every Close."""
    dates, indices = _validate_daily(daily)
    source_dates = np.asarray(panel["dates"], dtype="datetime64[D]")
    raw = np.asarray(panel["C"], float)
    observed = np.asarray(panel["observed"], bool)
    names = np.asarray(panel["names"])
    if (raw.shape != observed.shape or raw.shape != (len(source_dates), len(names))
            or np.any(indices<0) or np.any(indices>=len(source_dates))
            or not np.array_equal(source_dates[indices], dates.values.astype("datetime64[D]"))):
        raise ValueError("RAW_PANEL_DATE_OR_SHAPE_MISMATCH")
    if len(orders):
        required = {"j", "side", "quantity", "notional", "cost", "execution_idx"}
        if not required.issubset(orders.columns):
            raise ValueError("ORDER_LEDGER_SCHEMA")
        ids = np.unique(orders.j.to_numpy(int))
        if np.any(ids<0) or np.any(ids>=len(names)) or not set(orders.execution_idx).issubset(set(indices)):
            raise ValueError("ORDER_LEDGER_INDEX")
    else:
        ids = np.array([], int)
    raw = raw[:, ids]
    valid = observed[:, ids] & np.isfinite(raw) & (raw > 0)
    last = np.maximum.accumulate(np.where(valid, np.arange(len(raw))[:, None], -1), axis=0)
    local = {int(j): i for i, j in enumerate(ids)}
    units = np.zeros(len(ids))
    first_buy = np.full(len(ids), -1, int)
    cash = float(initial_cash)
    grouped = {int(k): group for k, group in orders.groupby("execution_idx")} if len(orders) else {}
    violations = []
    stale_days, no_mark_days, missing_current_days, old_holding_days = set(), set(), set(), set()
    stale_count = no_mark_count = missing_current_count = held_count = 0
    max_age = None
    max_hold_age = 0
    max_cash_error = max_nav_error = 0.0
    positions_mismatches = negative_unit_closes = 0
    unreconciled_no_mark_days = 0
    for day in daily.itertuples():
        k = int(day.k)
        if k in grouped:
            for order in grouped[k].itertuples():
                i = local[int(order.j)]
                qty, notional, fee = float(order.quantity), float(order.notional), float(order.cost)
                if not np.isfinite([qty, notional, fee]).all() or qty < 0 or notional < 0 or fee < 0:
                    raise ValueError("INVALID_ORDER_AMOUNTS")
                if hasattr(order, "ticker") and str(order.ticker) != str(names[int(order.j)]):
                    raise ValueError("ORDER_TICKER_INDEX_MISMATCH")
                if order.side == "BUY":
                    if units[i] <= 1e-12 and qty > 1e-12:
                        first_buy[i] = k
                    units[i] += qty
                    cash -= notional+fee
                elif order.side == "SELL":
                    units[i] -= qty
                    cash += notional-fee
                    if abs(units[i]) <= 1e-12:
                        units[i] = 0.0
                        first_buy[i] = -1
                else:
                    raise ValueError("ORDER_SIDE")
        negative_unit_closes += int(np.any(units < -1e-8))
        positions_mismatches += int(int((units>1e-10).sum()) != int(day.positions))
        held = np.flatnonzero(units > 1e-12)
        held_count += len(held)
        market_value = 0.0
        missing_mark = False
        for i in held:
            seen = int(last[k, i])
            age = None if seen < 0 else int((source_dates[k]-source_dates[seen]).astype(int))
            mark = None if seen < 0 else float(raw[seen, i])
            hold_age = k-int(first_buy[i])
            max_hold_age = max(max_hold_age, hold_age)
            if hold_age > 63:
                old_holding_days.add(k)
            if not valid[k, i]:
                missing_current_count += 1
                missing_current_days.add(k)
            if age is not None:
                max_age = age if max_age is None else max(max_age, age)
            issue = None
            if mark is None or not np.isfinite(mark) or mark <= 0:
                no_mark_count += 1
                no_mark_days.add(k)
                missing_mark = True
                issue = "NO_VALID_SOURCE_MARK"
            else:
                market_value += units[i]*mark
                if age > max_age_days:
                    stale_count += 1
                    stale_days.add(k)
                    issue = "STALE_SOURCE_MARK"
            if issue:
                violations.append(dict(k=k, date=str(day.date), ticker=str(names[ids[i]]),
                    instrument_idx=int(ids[i]), units=float(units[i]), issue=issue,
                    source_date=None if seen<0 else str(source_dates[seen]), source_age_calendar_days=age,
                    source_mark=mark, value_at_source_mark=None if mark is None else float(units[i]*mark),
                    nav=float(day.nav_close), exposure_at_source_mark=None if mark is None else float(units[i]*mark/day.nav_close),
                    continuous_holding_age_sessions=hold_age))
        max_cash_error = max(max_cash_error, abs(cash-float(day.cash)))
        if missing_mark:
            unreconciled_no_mark_days += 1
        else:
            max_nav_error = max(max_nav_error, abs(cash+market_value-float(day.nav_close)))
    tolerance = max(1e-6, float(daily.nav_close.max())*1e-10)
    ledger_pass = (max_cash_error <= tolerance and max_nav_error <= tolerance
                   and not positions_mismatches and not negative_unit_closes and not unreconciled_no_mark_days)
    valuation_pass = stale_count == 0 and no_mark_count == 0
    summary = dict(held_asset_closes=held_count, stale_held_asset_closes=stale_count,
        stale_held_days=len(stale_days), held_asset_closes_without_valid_mark=no_mark_count,
        days_without_valid_held_mark=len(no_mark_days), max_source_age_calendar_days=max_age,
        missing_or_unobserved_current_raw_asset_closes=missing_current_count,
        days_with_missing_or_unobserved_current_raw_close=len(missing_current_days),
        max_continuous_holding_age_sessions=max_hold_age,
        days_with_continuous_holding_age_over63=len(old_holding_days),
        max_cash_reconstruction_error=max_cash_error, max_nav_reconstruction_error=max_nav_error,
        reconciliation_tolerance=tolerance, position_count_mismatch_days=positions_mismatches,
        negative_unit_days=negative_unit_closes, unreconciled_no_mark_days=unreconciled_no_mark_days,
        ledger_reconciliation_pass=bool(ledger_pass), valuation_support_pass=valuation_pass,
        promotion_blocked_by_held_mark_support=not valuation_pass,
        age_limit_calendar_days=int(max_age_days), performance_modified=False)
    columns = ["k", "date", "ticker", "instrument_idx", "units", "issue", "source_date",
               "source_age_calendar_days", "source_mark", "value_at_source_mark", "nav",
               "exposure_at_source_mark", "continuous_holding_age_sessions"]
    return summary, pd.DataFrame(violations, columns=columns)


def validate_result_calendar(daily, panel_dates, *, start_idx, end_idx):
    """Reject a dropped session even when all retained daily rows are valid."""
    dates, indices = _validate_daily(daily)
    expected = np.arange(int(start_idx), int(end_idx)+1)
    panel_dates = np.asarray(panel_dates, dtype="datetime64[D]")
    if (not np.array_equal(indices, expected) or start_idx < 0 or end_idx >= len(panel_dates)
            or not np.array_equal(dates.values.astype("datetime64[D]"), panel_dates[expected])):
        raise ValueError("INCOMPLETE_OR_MISMATCHED_RESULT_CALENDAR")


def metric_parity(actual, recorded, *, prefix=""):
    """Compare every independently available native field, including boundaries."""
    checks = {}
    for key, value in actual.items():
        native_key = prefix+key
        if native_key not in recorded or isinstance(value, (dict, list)):
            continue
        expected = recorded[native_key]
        if value is None or pd.isna(expected):
            equal = value is None and (expected is None or pd.isna(expected))
            difference = None
        elif isinstance(value, (int, float, np.number)):
            difference = float(value)-float(expected)
            equal = bool(np.isclose(float(value), float(expected), rtol=1e-11, atol=1e-12))
        else:
            equal, difference = str(value) == str(expected), None
        checks[key] = dict(matches=equal, difference=difference)
    if not checks:
        raise ValueError("NO_METRIC_FIELDS_TO_COMPARE")
    numeric = [abs(row["difference"]) for row in checks.values() if row["difference"] is not None]
    return dict(pass_all=all(row["matches"] for row in checks.values()),
                compared_fields=len(checks), maximum_absolute_difference=max(numeric, default=0.0),
                mismatches={key: row for key, row in checks.items() if not row["matches"]})


def trace_diagnostics(trace, *, ready_idx):
    """Summarize recorded state drift; standardized extremes are not formal OOD tests."""
    active = trace.loc[trace.k >= ready_idx]
    maxima = {}
    for column in ("max_holding_age_sessions", "mean_holding_age_sessions",
                   "cash_max_abs_standardized_price", "fresh_max_abs_standardized_price",
                   "entry_max_abs_standardized_price"):
        values = pd.to_numeric(active[column], errors="coerce")
        finite = values[np.isfinite(values)]
        if len(finite):
            row = active.loc[finite.idxmax()]
            maxima[column] = dict(maximum=float(finite.max()), k=int(row.k), date=str(row.date),
                action=str(row.action), n_recorded=len(finite),
                q95=float(finite.quantile(.95)), q99=float(finite.quantile(.99)))
        else:
            maxima[column] = None
    return dict(decision_rows=len(trace), post_readiness_decision_rows=len(active),
        first_decision_date=str(trace.date.iloc[0]), last_decision_date=str(trace.date.iloc[-1]),
        post_readiness_status_counts={str(k): int(v) for k, v in active.status.value_counts().items()},
        post_readiness_fallback_price_rows=int(active.fallback_price.sum()),
        post_readiness_unknown_age_positions_max=int(active.unknown_age_positions.max()) if len(active) else 0,
        maxima=maxima, standardized_extremes_are_formal_ood_test=False,
        holding_age_note="Trace age follows last-buy state; order reconstruction separately measures continuous ownership.")


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_csv(path):
    return pd.read_csv(path, float_precision="round_trip")


def forecast_audit(results):
    """Independently reproduce date-balanced all-head-ready forecast diagnostics."""
    ledger = _read_csv(results / "PREQUENTIAL_FORECASTS.csv.gz")
    saved = _read_csv(results / "FORECAST_SCORES.csv")
    selected = ledger.loc[ledger.all_heads_ready & np.isfinite(ledger.prediction)].copy()
    maturity = bool(((selected.max_training_terminal_idx < selected.fit_cutoff_idx)
                     & (selected.fit_cutoff_idx <= selected.signal_idx)
                     & (selected.terminal_idx < selected.reporting_cutoff_idx)).all())
    rows, parity = [], []
    for (head, arm), group in selected.groupby(["head", "arm"], sort=True):
        counts = group.groupby("signal_idx").signal_idx.transform("size").to_numpy(float)
        weights = 1/counts
        weights /= weights.sum()
        error = group.prediction.to_numpy(float)-group.outcome.to_numpy(float)
        positive = group.loc[(group.prediction > 0) & (group.lower > 0)]
        positive_means = positive.groupby("signal_idx").outcome.mean()
        signals = sorted(positive.signal_idx.unique())
        separated, previous = 0, None
        for signal in signals:
            if previous is None or signal >= previous+21:
                separated, previous = separated+1, signal
        row = dict(head=head, arm=arm, n_rows=len(group), n_dates=int(group.signal_idx.nunique()),
            mse=float(weights @ (error*error)), bias=float(weights @ error),
            positive_buffer_dates=len(signals), positive_buffer_episodes=separated,
            positive_buffer_realized_mean=None if not len(positive) else float(positive_means.mean()))
        native = saved.loc[(saved.support == "ALL_HEADS_READY") & (saved["head"] == head) & (saved.arm == arm)]
        if len(native) != 1:
            raise ValueError("FORECAST_SCORE_MATRIX")
        parity.append(dict(head=head, arm=arm, **metric_parity(row, native.iloc[0].to_dict())))
        rows.append(row)
    if len(rows) != 12:
        raise ValueError("INCOMPLETE_FORECAST_MATRIX")
    paired = []
    for head in ACTIONS:
        term = next(row for row in rows if row["head"] == head and row["arm"] == "TERM")
        vix = next(row for row in rows if row["head"] == head and row["arm"] == "VIX")
        paired.append(dict(head=head, term_mse=term["mse"], vix_mse=vix["mse"],
            term_minus_vix_mse=term["mse"]-vix["mse"],
            term_relative_mse_change=term["mse"]/vix["mse"]-1,
            term_improves_mse=term["mse"] < vix["mse"],
            term_positive_buffer_realized_mean=term["positive_buffer_realized_mean"],
            term_positive_buffer_episodes=term["positive_buffer_episodes"]))
    return dict(support="ALL_HEADS_READY", rows=rows, metric_parity=parity,
        maturity_and_reporting_cutoff_pass=maturity,
        term_vs_vix=paired, term_improves_all_three_heads=all(row["term_improves_mse"] for row in paired),
        outcomes_independently_rebuilt=False,
        note="Audit reproduces forecasts from the saved prequential ledger; it does not rebuild counterfactual labels.")


def plot_primary(paths, readiness, destination, *, postwarmup, arms=ARMS, study="OLC111", locale="en"):
    """Publication-style two-panel figure with explicit, unbroken wealth anchors."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    colors = dict(BASE="#20252d", STATIC_75="#8b929a", MEAN="#a05a9d",
                  PRICE="#286ca3", VIX="#c3811a", TERM="#008276")
    styles = dict(BASE="-", STATIC_75="--", MEAN=":", PRICE="-", VIX="-.", TERM="-")
    fig, (nav_ax, dd_ax) = plt.subplots(2, 1, figsize=(12.4, 8.0), sharex=True,
        gridspec_kw=dict(height_ratios=[1.7, 1], hspace=.12))
    for arm in arms:
        daily = paths[f"{arm}__NEXT_CLOSE"]["daily"]
        chosen = _window(daily, readiness["postwarmup_start_idx"] if postwarmup else None)
        frame, anchor, anchor_date, anchor_idx = chosen
        if anchor_date is None:
            anchor_date = paths[f"{arm}__NEXT_CLOSE"]["trace"].date.iloc[0]
        x = pd.to_datetime([anchor_date]+frame.date.tolist())
        nav = np.r_[anchor, frame.nav_close.to_numpy(float)]/anchor
        italian_labels = dict(BASE="Base", STATIC_75="Base al 75%", PRICE_ROTATION="Protezione prezzi",
                              TERM_ROTATION="Protezione + struttura volatilità")
        label = italian_labels.get(arm, arm.replace("_", " ")) if locale == "it" else arm.replace("_", " ")
        color_key = arm.removesuffix("_ROTATION")
        width = 2.1 if color_key in ("BASE", "TERM") else 1.5
        nav_ax.plot(x, nav, color=colors[color_key], linestyle=styles[color_key], linewidth=width, label=label)
        wealth, sample_dates, _, _ = _sample_chain(frame, anchor, anchor_date, anchor_idx)
        dd_ax.plot(pd.to_datetime(sample_dates), wealth/np.maximum.accumulate(wealth)-1,
                   color=colors[color_key], linestyle=styles[color_key], linewidth=width)
    nav_ax.set_yscale("log")
    nav_ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:g}×"))
    nav_ax.yaxis.set_minor_formatter(FuncFormatter(lambda y, _: f"{y:g}×"))
    nav_ax.set_ylabel("Capitale relativo (scala log)" if locale == "it" else "Wealth relative to anchor (log scale)", fontsize=10)
    dd_ax.set_ylabel("Drawdown" if locale == "it" else "Sampled drawdown", fontsize=10)
    dd_ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{100*y:.0f}%"))
    dd_ax.tick_params(axis="y", labelleft=True)
    dd_ax.axhline(0, color="#aaa", linewidth=.7)
    dd_ax.xaxis.set_major_locator(mdates.YearLocator())
    dd_ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for ax in (nav_ax, dd_ax):
        ax.grid(axis="both", color="#d9dee4", linewidth=.6, alpha=.75)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=9)
        ax.margins(x=.005)
    title = f"{study} · primary execution · common post-warmup" if postwarmup else f"{study} · primary execution · full historical window"
    if postwarmup:
        subtitle = (f"Returns: {readiness['postwarmup_start_date']}–{frame.date.iloc[-1]} · "
                    f"each path anchored to its actual preceding close on {anchor_date}")
        if locale == "it":
            title = "Protezione e rientro — confronto dal luglio 2022"
            subtitle = (f"Rendimenti: {readiness['postwarmup_start_date']}–{frame.date.iloc[-1]} · "
                        f"capitale di riferimento: chiusura effettiva del {anchor_date}")
        nav_ax.axvline(pd.Timestamp(readiness["postwarmup_start_date"]), color="#777", linewidth=.9)
        dd_ax.axvline(pd.Timestamp(readiness["postwarmup_start_date"]), color="#777", linewidth=.9)
    else:
        subtitle = "Returns: 2020-03-02–2026-10-30 · initial wealth €10,000 · shaded region is model warmup"
        for ax in (nav_ax, dd_ax):
            ax.axvspan(pd.Timestamp(anchor_date), pd.Timestamp(readiness["all_heads_first_ready_date"]),
                       color="#8894a5", alpha=.1)
            ax.axvline(pd.Timestamp(readiness["postwarmup_start_date"]), color="#777", linewidth=.9)
        nav_ax.text(pd.Timestamp(readiness["postwarmup_start_date"])+pd.Timedelta(days=25), .98,
            f"Post-warmup starts {readiness['postwarmup_start_date']}", transform=nav_ax.get_xaxis_transform(),
            ha="left", va="top", fontsize=8.5, color="#555")
    fig.suptitle(title, x=.08, y=.97, ha="left", fontsize=16, fontweight="semibold")
    fig.text(.08, .925, subtitle, ha="left", fontsize=10, color="#4b5563")
    nav_ax.legend(ncol=2 if locale == "it" else len(arms), loc="upper left", bbox_to_anchor=(0, 1.16), frameon=False,
                  fontsize=9, handlelength=2.5, columnspacing=1.4)
    footer = ("Chiusura successiva accettata · €1 + 15 punti base per ordine eseguito · drawdown prima dei costi e a chiusura.\n"
              "Studio storico esplorativo; le curve non dimostrano un vantaggio futuro. Valori del conto invariati nell’audit."
              if locale == "it" else
              "Following accepted close · €1 + 15 bp per filled order · drawdown includes pre-fee and closing marks.\n"
              "Exploratory historical study. Unsupported source marks, if any, are flagged separately; NAV is never revised by this audit.")
    fig.text(.08, .035, footer,
        fontsize=8.5, color="#555", ha="left")
    fig.subplots_adjust(left=.08, right=.98, top=.83, bottom=.12)
    fig.canvas.draw()
    fig.savefig(destination, dpi=180, facecolor="white", metadata={"Software": f"{study} independent diagnostics"})
    plt.close(fig)


def run_audit(root):
    root = Path(root).resolve()
    results = root / "results"
    panel_path = root / "../olc110/source/data/XETRA_EUR_ETF.npz"
    with np.load(panel_path, allow_pickle=False) as source:
        panel = {key: source[key] for key in ("dates", "names", "C", "observed")}
    readiness = json.loads((results / "FIT_READINESS.json").read_text())
    manifest = json.loads((results / "RUN_MANIFEST.json").read_text())
    scores = _read_csv(results / "SCORES.csv")
    expected = [f"{arm}__{scenario}" for arm in ARMS for scenario in SCENARIOS]
    if (manifest["completed_paths"] != len(expected)
            or set(manifest["completed_path_ids"]) != set(expected)
            or len(scores) != len(expected) or set(scores.path_id) != set(expected)):
        raise ValueError("INCOMPLETE_18_PATH_MATRIX")
    ready_idx = int(readiness["all_heads_first_ready_idx"])
    post_idx = int(readiness["postwarmup_start_idx"])
    dates = np.asarray(panel["dates"], dtype="datetime64[D]")
    if (post_idx != ready_idx+1 or str(dates[ready_idx]) != readiness["all_heads_first_ready_date"]
            or str(dates[post_idx]) != readiness["postwarmup_start_date"]):
        raise ValueError("READINESS_CALENDAR_MISMATCH")
    if scores.start_idx.nunique() != 1 or scores.end_idx.nunique() != 1:
        raise ValueError("INCONSISTENT_RESULT_WINDOWS")
    begin, end = int(scores.start_idx.iloc[0]), int(scores.end_idx.iloc[0])
    if end != len(dates)-1:
        raise ValueError("RESULTS_DO_NOT_REACH_PANEL_END")
    hashes = {}
    for path in (panel_path, results / "SCORES.csv", results / "RUN_MANIFEST.json",
                 results / "FIT_READINESS.json", results / "PREQUENTIAL_FORECASTS.csv.gz",
                 results / "FORECAST_SCORES.csv", root / "docs/DESIGN_AND_PROTOCOL.md",
                 Path(__file__)):
        hashes[str(path.relative_to(root)) if path.is_relative_to(root) else str(path)] = _sha256(path)
    paths = {}
    for path_id in expected:
        folder = results / path_id
        loaded = {}
        for key, filename in (("daily", "DAILY.csv.gz"), ("orders", "ORDERS.csv.gz"),
                              ("trace", "POLICY_TRACE.csv.gz"), ("instructions", "INSTRUCTIONS.csv.gz")):
            loaded[key] = _read_csv(folder / filename)
            hashes[str((folder / filename).relative_to(root))] = _sha256(folder / filename)
        loaded["native"] = json.loads((folder / "METRICS.json").read_text())
        hashes[str((folder / "METRICS.json").relative_to(root))] = _sha256(folder / "METRICS.json")
        validate_result_calendar(loaded["daily"], dates, start_idx=begin, end_idx=end)
        paths[path_id] = loaded
    diagnostics, compact, cash_rows, event_rows, violations, annual_rows = {}, [], [], [], [], []
    for path_id in expected:
        arm, scenario = path_id.split("__")
        loaded = paths[path_id]
        daily, orders, trace = loaded["daily"], loaded["orders"], loaded["trace"]
        whole = performance_window(daily)
        post = performance_window(daily, start_idx=post_idx)
        years = whole["days"]/YEAR_DAYS
        nav_by_date = daily.set_index("date").nav_open
        whole.update(orders=len(orders), costs=float(orders.cost.sum()),
            trading_days=int(orders.date.nunique()), instructions=len(loaded["instructions"]),
            trading_days_per_year=float(orders.date.nunique()/years),
            two_sided_turnover_per_year=float((orders.notional.to_numpy()/nav_by_date.loc[orders.date].to_numpy()).sum()/years))
        recorded = scores.loc[scores.path_id == path_id].iloc[0].to_dict()
        parity = dict(metrics_whole=metric_parity(whole, loaded["native"]),
                      metrics_post=metric_parity(post, loaded["native"], prefix="post_"),
                      scores_whole=metric_parity(whole, recorded),
                      scores_post=metric_parity(post, recorded, prefix="post_"))
        warmup = (warmup_replication(paths[f"BASE__{scenario}"]["daily"], daily, ready_idx=ready_idx)
                  if arm in ("MEAN", "PRICE", "VIX", "TERM") else None)
        actions, events = intervention_summary(trace, orders, last_idx=end)
        held, issues = held_mark_audit(daily, orders, panel)
        spells = cash_spells(daily)
        max_cash = max((row["cash_sessions"] for row in spells), default=0)
        state_trace = trace_diagnostics(trace, ready_idx=ready_idx)
        diagnostics[path_id] = dict(arm=arm, scenario=scenario, whole=whole, post=post, metric_parity=parity,
            warmup_against_same_scenario_base=warmup, interventions=actions,
            held_marks=held, cash_spells=spells, longest_cash_spell_sessions=max_cash, trace=state_trace,
            promotion_eligible=False)
        compact.append(dict(path_id=path_id, arm=arm, scenario=scenario, cagr=whole["cagr"],
            sampled_maxdd=whole["maxdd_sampled"], end_equity=whole["end_equity"],
            post_cagr=post["cagr"], post_sampled_maxdd=post["maxdd_sampled"],
            post_anchor_nav=post["initial_nav"], post_anchor_date=post["anchor_date"],
            post_start_date=post["start_date"], mean_exposure=whole["mean_exposure"],
            post_mean_exposure=post["mean_exposure"], full_cash_days=whole["full_cash_days"],
            longest_cash_spell_sessions=max_cash, orders=whole["orders"], costs=whole["costs"],
            cash_filled_instructions=actions["CASH"]["realized_instructions"],
            cash_separated_completed21=actions["CASH"]["separated_completed21_episodes"],
            fresh_filled_instructions=actions["FRESH"]["realized_instructions"],
            fresh_separated_completed21=actions["FRESH"]["separated_completed21_episodes"],
            entry_filled_instructions=actions["ENTRY"]["realized_instructions"],
            entry_separated_completed21=actions["ENTRY"]["separated_completed21_episodes"],
            max_continuous_holding_age_sessions=held["max_continuous_holding_age_sessions"],
            max_source_age_calendar_days=held["max_source_age_calendar_days"],
            stale_held_asset_closes=held["stale_held_asset_closes"],
            max_nav_reconstruction_error=held["max_nav_reconstruction_error"],
            max_cash_reconstruction_error=held["max_cash_reconstruction_error"],
            valuation_support_pass=held["valuation_support_pass"],
            ledger_reconciliation_pass=held["ledger_reconciliation_pass"],
            whole_post_metric_parity=all(value["pass_all"] for value in parity.values()),
            exact_learned_warmup=None if warmup is None else warmup["exact_match"]))
        for table, destination in ((events, event_rows), (issues, violations)):
            table.insert(0, "path_id", path_id)
            destination.append(table)
        cash_rows.extend(dict(path_id=path_id, **spell) for spell in spells)
        years_in_path = pd.to_datetime(daily.date).dt.year
        for year in sorted(years_in_path.unique()):
            indices = daily.loc[years_in_path == year, "k"]
            metrics = performance_window(daily, start_idx=int(indices.min()), end_idx=int(indices.max()))
            annual_rows.append(dict(path_id=path_id, year=int(year), annual_return=metrics["cumulative"],
                log_growth=metrics["log_growth"], sampled_maxdd_in_year=metrics["maxdd_sampled"],
                initial_nav=metrics["initial_nav"], end_equity=metrics["end_equity"],
                start_date=metrics["start_date"], end_date=metrics["end_date"]))
    paired, paired_annual = {}, []
    for scenario in SCENARIOS:
        for window, start_idx in (("whole", None), ("post", post_idx)):
            summary, annual = term_vix_comparison(paths[f"TERM__{scenario}"]["daily"],
                paths[f"VIX__{scenario}"]["daily"], start_idx=start_idx)
            paired[f"{scenario}__{window}"] = summary
            annual.insert(0, "window", window)
            annual.insert(0, "scenario", scenario)
            paired_annual.append(annual)
    forecast = forecast_audit(results)
    checks = dict(complete_18_path_matrix=True, identical_complete_daily_calendars=True,
        whole_post_metric_parity=all(value["pass_all"] for path in diagnostics.values() for value in path["metric_parity"].values()),
        exact_warmup_all12_learned_paths=all(path["warmup_against_same_scenario_base"]["exact_match"]
            for path in diagnostics.values() if path["warmup_against_same_scenario_base"] is not None),
        account_reconstruction_all18_paths=all(path["held_marks"]["ledger_reconciliation_pass"] for path in diagnostics.values()),
        held_quote_support_all18_paths=all(path["held_marks"]["valuation_support_pass"] for path in diagnostics.values()),
        forecast_metric_parity=all(row["pass_all"] for row in forecast["metric_parity"]),
        forecast_maturity_and_reporting_cutoff=forecast["maturity_and_reporting_cutoff_pass"])
    report = dict(study="OLC111", audit="independent_results_only_v1", readiness=readiness,
        checks=checks, paths=diagnostics, term_vs_vix=paired, forecast=forecast,
        source_sha256=hashes, performance_modified=False, models_refit=False, policies_changed=False,
        discovered_alpha=False, promotion_eligible=False,
        conclusion="No discovered alpha. TERM does not improve VIX forecast MSE on any head; action reliability evidence is insufficient.",
        limitations=["Prior research and this historical period have already been inspected; this is not untouched validation.",
            "Native ETF panel catalog, survivorship and adjustment-vintage limitations remain.",
            "Held source ages are audited at each recorded post-order close; no new intraday execution certification is made.",
            "Completed 21-session intervention counts establish temporal spacing only, not independent or unbiased treatment effects.",
            "Counterfactual bank outcomes and frozen model fits are not rebuilt by this audit."])
    (results / "INDEPENDENT_DIAGNOSTICS.json").write_text(json.dumps(_jsonable(report), indent=2, allow_nan=False)+"\n")
    pd.DataFrame(compact).to_csv(results / "INDEPENDENT_SCORES.csv", index=False)
    pd.DataFrame(cash_rows).to_csv(results / "INDEPENDENT_CASH_SPELLS.csv", index=False)
    nonempty_events = [frame for frame in event_rows if len(frame)]
    (pd.concat(nonempty_events, ignore_index=True) if nonempty_events else event_rows[0]).to_csv(
        results / "INDEPENDENT_INTERVENTIONS.csv", index=False)
    pd.concat(violations, ignore_index=True).to_csv(results / "INDEPENDENT_HELD_MARK_VIOLATIONS.csv.gz", index=False,
                                                compression={"method": "gzip", "mtime": 0})
    pd.DataFrame(annual_rows).to_csv(results / "INDEPENDENT_ANNUAL_RETURNS.csv", index=False)
    pd.concat(paired_annual, ignore_index=True).to_csv(results / "INDEPENDENT_TERM_VIX_ANNUAL.csv", index=False)
    plot_primary(paths, readiness, results / "INDEPENDENT_PRIMARY_FULL.png", postwarmup=False)
    plot_primary(paths, readiness, results / "INDEPENDENT_PRIMARY_POSTWARMUP.png", postwarmup=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    arguments = parser.parse_args()
    output = run_audit(arguments.root)
    print(json.dumps(dict(checks=output["checks"], discovered_alpha=output["discovered_alpha"],
                          promotion_eligible=output["promotion_eligible"]), indent=2))
    if not all(output["checks"].values()):
        raise SystemExit(1)
