"""Experimental economic targets for the ETF Trader level-2 redesign.

Read-only transformation of frozen source-only OHLCV panels. Does not replace
the canonical rank target or modify production. A training caller MUST apply
strict exit-date maturity via mature_training_rows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_HORIZONS = (21, 42, 63)


def _price_panel(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError(f"{name} must be a nonempty DataFrame")
    out = frame.copy()
    dates = pd.DatetimeIndex(pd.to_datetime(out.index, errors="raise"))
    if dates.hasnans or dates.tz is not None or not dates.is_unique or not dates.is_monotonic_increasing:
        raise ValueError(f"{name}: invalid trading calendar")
    out.index = dates
    if not out.columns.is_unique:
        raise ValueError(f"{name}: duplicate ticker columns")
    numbers = out.apply(pd.to_numeric, errors="raise").to_numpy(dtype=float)
    if np.isinf(numbers).any() or (numbers[np.isfinite(numbers)] <= 0).any():
        raise ValueError(f"{name}: infinite or nonpositive prices")
    return out


def _date_column(panel: pd.DataFrame, field: str, *, required: bool = False) -> pd.DatetimeIndex:
    if field not in panel:
        raise ValueError(f"Missing date column: {field}")
    dates = pd.DatetimeIndex(pd.to_datetime(panel[field], errors="raise"))
    if dates.tz is not None or (required and dates.hasnans):
        raise ValueError(f"Invalid date column: {field}")
    return dates


def build_forward_targets(
    panel: pd.DataFrame,
    open_prices: pd.DataFrame,
    low_prices: pd.DataFrame,
    *,
    cash_ticker: str = "BIL",
    market_ticker: str = "SPY",
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    side_cost: float = 0.001,
) -> pd.DataFrame:
    """Attach realized, not predicted, economic outcomes to original rows.

    Contract:
      - signal at month-end close; entry at next trading-session OPEN;
      - exit at entry + h trading sessions, also at OPEN;
      - alpha_cash is log of ETF after two assumed execution-cost legs divided
        by the cash ETF's gross adjusted-open growth (buy-and-hold proxy);
      - alpha_market is analogous against SPY gross adjusted-open growth;
      - adverse_excursion is worst adjusted intraday LOW from entry through
        the session before exit, including the final exit OPEN;
      - BIL/market unavailable at a date => missing alpha; NEVER backfilled.
    """
    if not 0 <= side_cost < 1 or not np.isfinite(side_cost):
        raise ValueError("side_cost must be a finite fraction in [0, 1)")
    if not horizons or len(set(horizons)) != len(horizons) or any(not isinstance(h, int) or h < 1 for h in horizons):
        raise ValueError("horizons must be unique positive integers")
    if not {"signal_date", "ticker", "entry_date"}.issubset(panel):
        raise ValueError("Missing panel keys or entry_date")
    if panel[["signal_date", "ticker"]].isna().any().any():
        raise ValueError("Missing signal or ticker")
    if panel.duplicated(["signal_date", "ticker"]).any():
        raise ValueError("Duplicate signal/ticker keys")

    opening = _price_panel(open_prices, "Open")
    lows = _price_panel(low_prices, "Low")
    if not opening.index.equals(lows.index):
        raise ValueError("Open/Low calendars differ")
    if set(opening.columns) != set(lows.columns):
        raise ValueError("Open/Low tickers differ")
    lows = lows.loc[:, opening.columns]
    for t in (cash_ticker, market_ticker):
        if t not in opening.columns:
            raise ValueError(f"Missing reference ETF: {t}")

    symbols = panel.ticker.astype(str).to_numpy()
    lookup = {str(t): j for j, t in enumerate(opening.columns)}
    unknown = sorted(set(symbols) - set(lookup))
    if unknown:
        raise ValueError(f"Unknown tickers: {unknown[:5]}")
    col = np.array([lookup[s] for s in symbols], dtype=int)
    sig = _date_column(panel, "signal_date", required=True)
    entry = _date_column(panel, "entry_date")
    calendar = opening.index
    sig_pos = calendar.get_indexer(sig)
    ent_pos = calendar.get_indexer(entry)
    has_entry = ~entry.isna()
    if (sig_pos < 0).any() or (has_entry & (ent_pos != sig_pos + 1)).any():
        raise ValueError("Signal/entry violates next-session-open convention")

    O = opening.to_numpy(dtype=float)
    L = lows.to_numpy(dtype=float)
    out = panel.copy()
    fee_factor = (1.0 - side_cost) ** 2

    for h in horizons:
        exit_field = f"exit_date_{h}"
        exits = _date_column(panel, exit_field)
        ex_pos = calendar.get_indexer(exits)
        complete = np.asarray(has_entry & ~exits.isna())
        if (complete & (ex_pos != ent_pos + h)).any():
            raise ValueError(f"{exit_field}: expected exactly {h} sessions after entry")
        valid = complete & (ent_pos >= 0) & (ex_pos >= 0)
        n = len(panel)
        gross = np.full(n, np.nan)
        net = np.full(n, np.nan)
        cash_alpha = np.full(n, np.nan)
        market_alpha = np.full(n, np.nan)
        downside = np.full(n, np.nan)
        if valid.any():
            rows = np.flatnonzero(valid)
            e, x, j = ent_pos[rows], ex_pos[rows], col[rows]
            buy, sell = O[e, j], O[x, j]
            asset_good = np.isfinite(buy) & np.isfinite(sell) & (buy > 0) & (sell > 0)
            gross[rows[asset_good]] = sell[asset_good] / buy[asset_good] - 1.0
            net[rows[asset_good]] = (sell[asset_good] / buy[asset_good]) * fee_factor - 1.0

            for ref_ticker, destination in ((cash_ticker, cash_alpha), (market_ticker, market_alpha)):
                ref_col = lookup[ref_ticker]
                ref_buy, ref_sell = O[e, ref_col], O[x, ref_col]
                reference_good = asset_good & np.isfinite(ref_buy) & np.isfinite(ref_sell) & (ref_buy > 0) & (ref_sell > 0)
                eligible = rows[reference_good]
                destination[eligible] = (
                    np.log1p(net[eligible])
                    - np.log(ref_sell[reference_good] / ref_buy[reference_good])
                )

            # rolling(h).min().shift(1) at exit day spans [entry, exit).
            rolling_lows = pd.DataFrame(L).rolling(h, min_periods=h).min().shift(1).to_numpy()
            path_low = rolling_lows[x, j]
            worst = np.minimum(path_low, sell)
            risk_good = asset_good & np.isfinite(worst) & (worst > 0)
            downside[rows[risk_good]] = np.maximum(0.0, 1.0 - worst[risk_good] / buy[risk_good])

        if f"fwd_ret_{h}" in panel:
            old = pd.to_numeric(panel[f"fwd_ret_{h}"], errors="raise").to_numpy(dtype=float)
            old_valid, now_valid = np.isfinite(old), np.isfinite(gross)
            if not np.array_equal(old_valid, now_valid) or not np.allclose(
                old[old_valid], gross[old_valid], rtol=1e-9, atol=1e-11
            ):
                raise ValueError(f"fwd_ret_{h} differs from recomputed next-open outcome")

        out[f"gross_ret_{h}"] = gross
        out[f"net_ret_{h}"] = net
        out[f"alpha_cash_log_{h}"] = cash_alpha
        out[f"alpha_spy_log_{h}"] = market_alpha
        out[f"adverse_excursion_{h}"] = downside
    return out


def mature_training_rows(
    labeled: pd.DataFrame,
    cutoff: str | pd.Timestamp,
    *,
    horizon: int = 21,
    target: str = "alpha_cash_log",
) -> pd.DataFrame:
    """Keep ONLY strictly mature economic labels for a causal annual fit."""
    field = f"{target}_{horizon}"
    if field not in labeled:
        raise ValueError(f"Missing target: {field}")
    signals = _date_column(labeled, "signal_date", required=True)
    exits = _date_column(labeled, f"exit_date_{horizon}")
    limit = pd.Timestamp(cutoff)
    if pd.isna(limit) or limit.tz is not None:
        raise ValueError("Invalid training cutoff")
    y = pd.to_numeric(labeled[field], errors="raise").to_numpy(dtype=float)
    mask = np.asarray((signals < limit) & (exits < limit) & np.isfinite(y))
    rows = labeled.iloc[np.flatnonzero(mask)].copy()
    if not rows.empty and not ((pd.to_datetime(rows.signal_date) < limit) &
                               (pd.to_datetime(rows[f"exit_date_{horizon}"]) < limit)).all():
        raise RuntimeError("Immature training label: fail closed")
    return rows
