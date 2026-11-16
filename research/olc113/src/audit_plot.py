"""Italian OLC113 figures from existing account ledgers; no policy simulation."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def plot_primary(paths, readiness, destination, *, postwarmup=True):
    """Plot four NEXT_CLOSE accounts with their own economically correct anchors.

    The upper panel uses closing NAV. The lower panel includes both recorded
    pre-fee execution marks (``nav_open``) and closing NAV in their original
    order. No account values, model outputs, or recorded returns are modified.
    ``destination`` accepts a filesystem path or a binary file-like object.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter, LogLocator, MaxNLocator, NullFormatter

    styles = (
        ("BASE", "Base", "#202b38", "-", 2.1),
        ("STATIC_75", "Base con obiettivo di esposizione al 75%", "#7b8492", "--", 1.7),
        ("PRICE_RESET", "Prezzi + rientro mensile", "#246da5", "-", 1.9),
        ("TERM_RESET", "Prezzi e struttura della volatilità + rientro mensile", "#008375", "-", 1.9),
    )
    start_idx = readiness.get("postwarmup_start_idx") if postwarmup else None
    if postwarmup and start_idx is None:
        raise ValueError("POSTWARMUP_START_REQUIRED")

    prepared = []
    reference_calendar = None
    for arm, label, color, linestyle, width in styles:
        loaded = paths[f"{arm}__NEXT_CLOSE"]
        daily = loaded["daily"]
        required = {"k", "date", "nav_open", "nav_close"}
        if not required.issubset(daily.columns) or daily.empty:
            raise ValueError("PLOT_DAILY_SCHEMA_OR_EMPTY")
        indices = daily.k.to_numpy(int)
        dates = pd.DatetimeIndex(daily.date)
        values = daily[["nav_open", "nav_close"]].to_numpy(float)
        if (dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing
                or np.any(np.diff(indices) != 1) or not np.isfinite(values).all()
                or np.any(values <= 0)):
            raise ValueError("PLOT_INVALID_ACCOUNT_OR_CALENDAR")
        calendar = np.column_stack((indices, dates.asi8))
        if reference_calendar is None:
            reference_calendar = calendar
        elif not np.array_equal(calendar, reference_calendar):
            raise ValueError("PLOT_ACCOUNT_CALENDAR_MISMATCH")

        first = 0
        if postwarmup:
            selected = np.flatnonzero(indices == int(start_idx))
            if len(selected) != 1 or selected[0] == 0:
                raise ValueError("PLOT_POSTWARMUP_ANCHOR_NOT_PRESENT")
            first = int(selected[0])
            anchor = float(daily.nav_close.iloc[first - 1])
            anchor_date = dates[first - 1]
        else:
            anchor = 10000.0
            # If no initial-decision trace is supplied, place initial capital
            # immediately before the first day's samples at that same date.
            trace = loaded.get("trace")
            anchor_date = (pd.Timestamp(trace.date.iloc[0])
                           if trace is not None and len(trace) else dates[0])
        selected_dates = dates[first:]
        selected_values = values[first:]
        x = pd.DatetimeIndex([anchor_date]).append(selected_dates)
        relative_close = np.r_[anchor, selected_values[:, 1]] / anchor
        sampled = np.r_[anchor, selected_values.ravel()]
        sampled_dates = pd.DatetimeIndex([anchor_date]).append(selected_dates.repeat(2))
        drawdown = sampled / np.maximum.accumulate(sampled) - 1.0
        prepared.append((label, color, linestyle, width, x, relative_close,
                         sampled_dates, drawdown, selected_dates, anchor_date))

    fig, (wealth_ax, dd_ax) = plt.subplots(
        2, 1, figsize=(13.0, 8.5), sharex=True,
        gridspec_kw={"height_ratios": [1.75, 1], "hspace": 0.14},
    )
    for label, color, linestyle, width, x, close, sampled_dates, drawdown, _, _ in prepared:
        wealth_ax.plot(x, close, label=label, color=color,
                       linestyle=linestyle, linewidth=width)
        dd_ax.plot(sampled_dates, drawdown, color=color,
                   linestyle=linestyle, linewidth=width)

    wealth_ax.set_yscale("log")
    wealth_ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1, 2, 5), numticks=12))
    wealth_ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}×"))
    wealth_ax.yaxis.set_minor_formatter(NullFormatter())
    wealth_ax.set_ylabel("Capitale relativo · scala logaritmica", fontsize=10)
    dd_ax.set_ylabel("Drawdown campionato", fontsize=10)
    dd_ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
    dd_ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{100 * value:.0f}%"))
    dd_ax.axhline(0, color="#8993a0", linewidth=0.7)
    dd_ax.set_ylim(top=0.012)

    selected_dates, anchor_date = prepared[0][-2:]
    if (selected_dates[-1] - selected_dates[0]).days >= 730:
        dd_ax.xaxis.set_major_locator(mdates.YearLocator())
        dd_ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    else:
        locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
        dd_ax.xaxis.set_major_locator(locator)
        dd_ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    for ax in (wealth_ax, dd_ax):
        ax.grid(color="#dce1e7", linewidth=0.6, alpha=0.8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=9)
        ax.margins(x=0.008)

    date_label = lambda value: pd.Timestamp(value).strftime("%d/%m/%Y")
    window = f"{date_label(selected_dates[0])}–{date_label(selected_dates[-1])}"
    if postwarmup:
        title = "OLC113 · rientro mensile nel periodo comune"
        subtitle = (f"Rendimenti: {window} · ogni conto riparte da 1× alla propria "
                    f"chiusura del {date_label(anchor_date)}")
    else:
        title = "OLC113 · confronto storico completo"
        subtitle = f"Rendimenti: {window} · capitale iniziale €10.000 · area grigia: apprendimento iniziale"
        ready_date = pd.Timestamp(readiness["all_heads_first_ready_date"])
        post_date = pd.Timestamp(readiness["postwarmup_start_date"])
        for ax in (wealth_ax, dd_ax):
            ax.axvspan(anchor_date, ready_date, color="#8492a5", alpha=0.10, linewidth=0)
            ax.axvline(post_date, color="#778393", linewidth=0.8, linestyle=":")

    fig.suptitle(title, x=0.09, y=0.966, ha="left", fontsize=17, fontweight="semibold")
    fig.text(0.09, 0.923, subtitle, ha="left", fontsize=10, color="#4b5563")
    handles, labels = wealth_ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.083, 0.892),
               ncol=2, frameon=False, fontsize=9, handlelength=2.8, columnspacing=2.0)
    footer = (
        "Chiusura successiva accettata · €1 + 15 punti base per ordine eseguito. "
        "Il drawdown include il valore prima dei costi e la chiusura.\n"
        "Studio storico esplorativo dopo OLC111/112; nessuna nuova stima dei modelli. "
        "Le curve non dimostrano affidabilità futura."
    )
    fig.text(0.09, 0.033, footer, ha="left", fontsize=8.4, color="#586273", linespacing=1.5)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.795, bottom=0.135)
    if isinstance(destination, (str, Path)):
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.canvas.draw()
        fig.savefig(destination, dpi=180, facecolor="white",
                    metadata={"Software": "OLC113 independent account audit"})
    finally:
        plt.close(fig)
