"""Replay frozen U24 with a small set of causal proposal-selection rules."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "u24"))

import run24 as previous
import verify24 as verification

import numpy as np
import pandas as pd

STATES = ROOT.parent / "u20" / "states"
RESULTS = ROOT / "results"
RULES = (
    "U20", "U24", "LOCAL_CONTROL", "FALLBACK_RELATIVE", "FALLBACK_RETAIN",
    "FALLBACK_DEFEND", "PAIR_SWITCH", "UNIVERSAL_SWITCH",
)
SCENARIOS = ((15, 0), (30, 0), (15, 1))


def features(state, benchmark):
    observed = state.get("low_observed", state.get("observed"))
    if observed is None:
        observed = np.isfinite(state["C"]) & (state["C"] > 0)
    observed = pd.DataFrame(observed)
    close = pd.DataFrame(state["C"]).where(observed).shift(1)
    log_close = np.log(close)
    relative = log_close.sub(log_close[benchmark], axis=0)
    volatility = relative.diff().rolling(63, min_periods=50).std()
    relative_21, relative_63 = relative.diff(21), relative.diff(63)
    safe_volatility = volatility.where(volatility > 1e-8)
    score = (
        relative_21.div(safe_volatility * np.sqrt(21))
        + relative_63.div(safe_volatility * np.sqrt(63))
    ) / 2
    eligible = observed.shift(1).rolling(63, min_periods=63).mean().ge(0.90)
    eligible &= close.notna()
    return SimpleNamespace(
        absolute_21=log_close.diff(21).to_numpy(),
        absolute_63=log_close.diff(63).to_numpy(),
        relative_21=relative_21.to_numpy(),
        relative_63=relative_63.to_numpy(),
        score=score.to_numpy(),
        eligible=eligible.to_numpy(),
    )


def proposals(state, local, proxy, market, indicators):
    base_pair = np.vstack([state["d1"][0], state["d2"][0]]).T
    local_pair = np.vstack([local["d1"][0], local["d2"][0]]).T
    decisions = np.flatnonzero(state["events"])
    names = state["tickers"]
    cash = np.array(["CASH_" in name for name in names])
    cash_index = np.flatnonzero(cash)[0]
    benchmark = list(names).index(previous.BM[market])
    cash_pair = np.zeros_like(base_pair, dtype=bool)
    if proxy is not None:
        cash_pair = cash[np.vstack([proxy["d1"][0], proxy["d2"][0]]).T]
    changed_states = {}
    audit = []
    for rule in RULES[2:]:
        chosen = base_pair.copy()
        last = np.full(2, -1)
        for start, end in zip(decisions, np.r_[decisions[1:], len(base_pair)]):
            original = base_pair[start]
            candidate = local_pair[start]
            missing = cash_pair[start]
            pick = original.copy()
            score = indicators.score[start]
            relative_21 = indicators.relative_21[start]
            relative_63 = indicators.relative_63[start]
            eligible = indicators.eligible[start] & ~cash
            weak = (relative_21[original] < 0) & (relative_63[original] < 0)
            if rule == "LOCAL_CONTROL" and proxy is not None:
                pick = candidate.copy()
            elif rule in ("PAIR_SWITCH", "UNIVERSAL_SWITCH"):
                candidate_score = score[candidate].mean()
                original_score = score[original].mean()
                if (
                    (missing.any() or rule == "UNIVERSAL_SWITCH")
                    and relative_21[original].mean() < 0
                    and relative_63[original].mean() < 0
                    and (candidate >= 0).all()
                    and eligible[candidate].all()
                    and candidate_score > 0.5
                    and candidate_score - original_score >= 0.5
                ):
                    pick = candidate.copy()
            else:
                for slot in np.flatnonzero(missing & weak):
                    incumbent = original[slot]
                    if rule == "FALLBACK_DEFEND":
                        if (
                            indicators.absolute_21[start, incumbent] < 0
                            and indicators.absolute_63[start, incumbent] < 0
                        ):
                            pick[slot] = (
                                benchmark if indicators.absolute_63[start, benchmark] > 0
                                else cash_index
                            )
                    elif rule in ("FALLBACK_RELATIVE", "FALLBACK_RETAIN"):
                        options = list(candidate)
                        if rule == "FALLBACK_RETAIN":
                            options.append(last[slot])
                        options = [
                            index for index in options
                            if index >= 0 and index != pick[1 - slot] and eligible[index]
                            and score[index] > 0.5 and score[index] - score[incumbent] >= 0.5
                        ]
                        if options:
                            pick[slot] = max(options, key=score.__getitem__)
            assert (pick >= 0).all()
            chosen[start:end] = pick
            last = pick
            audit.append({
                "market": market, "rule": rule,
                "date": state["dates"][start], "last_quote": state["dates"][start - 1] if start else "",
                "missing_slots": int(missing.sum()),
                "original_a": names[original[0]], "original_b": names[original[1]],
                "chosen_a": names[pick[0]], "chosen_b": names[pick[1]],
                "changed": bool(np.any(pick != original)),
            })
        changed_states[rule] = dict(state, d1=chosen[:, 0][None, :], d2=chosen[:, 1][None, :])
    return changed_states, pd.DataFrame(audit)


def nav_tables(dates, nav, fields):
    dates = pd.DatetimeIndex(dates)
    split = dates.searchsorted("2023-01-03")
    periods = []
    for name, start, end in (("2020–2022", 0, split), ("2023–2026", split, len(nav) - 1)):
        periods.append(dict(fields, period=name, **previous.metrics(dates[start:end + 1], nav[start:end + 1])))
    months = previous.months(dates, nav)
    monthly = [dict(fields, month=str(month), ret=value) for month, value in months.items()]
    years = (1 + months).groupby(months.index.year).prod() - 1
    annual = [dict(fields, year=int(year), ret=value) for year, value in years.items()]
    return periods, monthly, annual


def run_scenario(market, name, state, built, bps, lag, directory):
    engine_rule = "BASE" if name == "U20" else "PROFIT_RAMP"
    fields = dict(market=market, rule=name, bps=bps, lag=lag)
    previous.OUT = verification.OUT = directory
    row, account, _ = previous.run(market, engine_rule, bps, lag, state, built, save=True)
    source = SimpleNamespace(market=market, rule=engine_rule, bps=bps, lag=lag)
    audit = verification.replay(source, state)
    audit["account"] = previous.tag(market, name, bps, lag)
    if name in ("U20", "U24"):
        reference = previous.ROOT / "results" / f"{previous.tag(market, engine_rule, bps, lag)}.npz"
        with np.load(reference) as saved:
            assert np.array_equal(account["ledger"], saved["ledger"]), reference
    nav = account["ledger"][:, 0]
    periods, monthly, annual = nav_tables(state["dates"], nav, fields)
    return dict(row, **fields), periods, monthly, annual, audit


def main():
    RESULTS.mkdir(exist_ok=True)
    sums, windows, monthly, annual, audit = [], [], [], [], []
    account_checks, causality = [], []
    with TemporaryDirectory(prefix="perseo_u25_") as temporary:
        for market in previous.MARKETS:
            state = previous.state(market)
            local = previous.load(STATES / f"{market}_LOCAL.npz")
            proxy = None if market == "USA" else previous.load(STATES / f"{market}_TRANSFER.npz")
            for other in (local, proxy):
                if other is not None:
                    for key in ("dates", "tickers"):
                        assert np.array_equal(state[key], other[key]), (market, key)
            if proxy is not None:
                assert np.array_equal(state["events"], proxy["events"])
            benchmark = list(state["tickers"]).index(previous.BM[market])
            signals = features(state, benchmark)
            alternatives, decisions = proposals(state, local, proxy, market, signals)
            audit.append(decisions)
            for cutoff in (300, 900, 1400):
                altered = dict(state, C=state["C"].copy())
                altered["C"][cutoff:] *= np.linspace(0.75, 1.25, altered["C"].shape[1])
                plans, _ = proposals(altered, local, proxy, market, features(altered, benchmark))
                for rule, alternative in plans.items():
                    for key in ("d1", "d2"):
                        assert np.array_equal(alternative[key][:, :cutoff + 1], alternatives[rule][key][:, :cutoff + 1])
                causality.append(dict(market=market, index=cutoff, rules=len(plans)))
            default_built = previous.signals(state, market)
            for rule in RULES:
                alternative = alternatives.get(rule, state)
                same_pair = all(np.array_equal(alternative[key], state[key]) for key in ("d1", "d2"))
                built = default_built if same_pair else previous.signals(alternative, market)
                print("REPLAY", market, rule, flush=True)
                for bps, lag in SCENARIOS:
                    result = run_scenario(market, rule, alternative, built, bps, lag, Path(temporary))
                    summary, periods, months, years, review = result
                    sums.append(summary)
                    windows.extend(periods)
                    monthly.extend(months)
                    annual.extend(years)
                    account_checks.append(review)
            pd.DataFrame(sums).to_csv(RESULTS / "SUMMARY.csv", index=False)
    pd.DataFrame(windows).to_csv(RESULTS / "WINDOWS.csv", index=False)
    pd.DataFrame(monthly).to_csv(RESULTS / "MONTHLY.csv", index=False)
    pd.DataFrame(annual).to_csv(RESULTS / "ANNUAL.csv", index=False)
    pd.concat(audit).to_csv(RESULTS / "PROPOSALS.csv", index=False)
    qa = dict(status="PASS", original_ledgers_bitwise=18, order_replays=account_checks, causal_checks=causality)
    (RESULTS / "QA.json").write_text(json.dumps(qa, indent=2) + "\n")
    print("QA_PASS", len(account_checks), flush=True)


if __name__ == "__main__":
    main()
