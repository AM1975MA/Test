"""Test limited confirmation and fallback-loss protection on U24."""

from pathlib import Path
import json
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "u25"))

from run25 import features, previous, proposals, run_scenario, SCENARIOS, STATES

import numpy as np
import pandas as pd

RESULTS = ROOT / "results"
RULES = "RETAIN_WAIT5", "RETAIN_RECHECK5", "RETAIN_HALF", "LOSS_BREAK_CASH", "LOSS_BREAK_HALF"


def previous_closes(state):
    observed = state.get("low_observed", state.get("observed"))
    close = pd.DataFrame(state["C"])
    if observed is not None:
        close = close.where(observed)
    return close.where(close > 0).shift(1).to_numpy()


def rechecked_pair(state, retained, close, wait):
    base = np.stack([state["d1"][0], state["d2"][0]], axis=1)
    replacement = np.stack([retained["d1"][0], retained["d2"][0]], axis=1)
    picked = base.copy()
    starts = np.flatnonzero(state["events"])
    for start, end in zip(starts, np.r_[starts[1:], len(base)]):
        initial, challenger = base[start], replacement[start]
        affected = initial != challenger
        if not affected.any():
            continue
        comparisons = {}
        for review in range(start + 5, end, 5):
            if wait and review > start + 5:
                break
            with np.errstate(invalid="ignore", divide="ignore"):
                orig_perf = close[review, initial] / close[start, initial]
                retain_perf = close[review, challenger] / close[start, challenger]
            comparisons[review] = (orig_perf, retain_perf)
        live = np.zeros(2, dtype=bool) if wait else affected.copy()
        for k in range(start, end):
            if k in comparisons:
                orig_perf, retain_perf = comparisons[k]
                if wait:
                    live = affected & (retain_perf > orig_perf)
                else:
                    live &= ~(orig_perf >= retain_perf)
            picked[k] = np.where(live, challenger, initial)
            if picked[k, 0] == picked[k, 1] and initial[0] != initial[1]:
                picked[k] = initial
    return dict(state, d1=picked[:, 0][None, :], d2=picked[:, 1][None, :])


def loss_guard(state, proxy, market, close, built):
    baseline = built[0]["PROFIT_RAMP"]
    blocked_weight = np.zeros_like(baseline)
    if proxy is None:
        return blocked_weight
    base = np.stack([state["d1"][0], state["d2"][0]], axis=1)
    proxy_pair = np.stack([proxy["d1"][0], proxy["d2"][0]], axis=1)
    cash = np.array(["CASH_" in name for name in state["tickers"]])
    benchmark = list(state["tickers"]).index(previous.BM[market])
    block = np.zeros(2, dtype=bool)
    start = 0
    for k, pair in enumerate(base):
        if state["events"][k]:
            start = k
            block[:] = False
        slots = cash[proxy_pair[k]] & ~cash[pair]
        if slots.any() and built[2][k]:
            with np.errstate(invalid="ignore", divide="ignore"):
                perf = close[k, pair] / close[start, pair]
                bench_perf = close[k, benchmark] / close[start, benchmark]
                relative = perf / bench_perf
                hit = ~block & slots & (perf < 0.92) & (relative < 0.94)
                if k >= 5:
                    rebound = close[k, pair] / close[k - 5, pair]
                    rebound_bm = close[k, benchmark] / close[k - 5, benchmark]
                    block &= ~((rebound > 1) & (rebound > rebound_bm))
            block |= hit
        blocked_weight[k, pair[block & slots]] = baseline[k, pair[block & slots]]
    return blocked_weight


def replacement_data(state, local, proxy, market):
    close = previous_closes(state)
    benchmark = list(state["tickers"]).index(previous.BM[market])
    retained = proposals(state, local, proxy, market, features(state, benchmark))[0]["FALLBACK_RETAIN"]
    waiting = rechecked_pair(state, retained, close, wait=True)
    recheck = rechecked_pair(state, retained, close, wait=False)
    return close, retained, waiting, recheck


def target_override(built, targets):
    base, recovery, reviews, audit = built
    return dict(base, PROFIT_RAMP=targets), recovery, reviews, audit


def main():
    RESULTS.mkdir(exist_ok=True)
    sums, windows, monthly, annual, audits, coverage = [], [], [], [], [], []
    with TemporaryDirectory(prefix="perseo_u26_") as temporary:
        for market in previous.MARKETS:
            state = previous.state(market)
            local = previous.load(STATES / f"{market}_LOCAL.npz")
            proxy = None if market == "USA" else previous.load(STATES / f"{market}_TRANSFER.npz")
            close, retained, waiting, recheck = replacement_data(state, local, proxy, market)
            original = previous.signals(state, market)
            base = original[0]["PROFIT_RAMP"]
            cash = next(i for i, ticker in enumerate(state["tickers"]) if "CASH_" in ticker)
            gone = loss_guard(state, proxy, market, close, original)
            for cutoff in (300, 900, 1400):
                changed = dict(state, C=state["C"].copy())
                changed["C"][cutoff:] *= np.linspace(0.73, 1.27, changed["C"].shape[1])
                anew, rnew, wnew, cnew = replacement_data(changed, local, proxy, market)
                for a, b in ((retained, rnew), (waiting, wnew), (recheck, cnew)):
                    for key in ("d1", "d2"):
                        assert np.array_equal(a[key][:, :cutoff + 1], b[key][:, :cutoff + 1])
                # Hold the original missing-slot schedule and U24 target as controls.
                perturbed = loss_guard(changed, proxy, market, anew, original)
                assert np.array_equal(gone[:cutoff + 1], perturbed[:cutoff + 1])

            for rule in RULES:
                source = state
                if rule in ("RETAIN_WAIT5", "RETAIN_RECHECK5"):
                    source = waiting if rule == "RETAIN_WAIT5" else recheck
                    built = previous.signals(source, market) if proxy is not None else original
                elif rule == "RETAIN_HALF":
                    other = previous.signals(retained, market) if proxy is not None else original
                    built = target_override(original, (base + other[0]["PROFIT_RAMP"]) / 2)
                else:
                    removed = gone if rule == "LOSS_BREAK_CASH" else gone / 2
                    targets = base - removed
                    targets[:, cash] += removed.sum(axis=1)
                    built = target_override(original, targets)
                proposed = built[0]["PROFIT_RAMP"]
                assert (proposed >= 0).all() and np.allclose(proposed.sum(1), base.sum(1), atol=1e-12)
                flags = (np.abs(proposed - base) > 1e-12).any(axis=1)
                coverage.extend(dict(market=market, date=date, rule=rule) for date in state["dates"][flags])
                print("REPLAY", market, rule, np.count_nonzero(flags), flush=True)
                for bps, lag in SCENARIOS:
                    row, periods, months, years, audit = run_scenario(
                        market, rule, source, built, bps, lag, Path(temporary)
                    )
                    sums.append(row)
                    windows.extend(periods)
                    monthly.extend(months)
                    annual.extend(years)
                    audits.append(audit)
    tables = dict(SUMMARY=sums, WINDOWS=windows, MONTHLY=monthly, ANNUAL=annual, CHANGED_DAYS=coverage)
    for title, rows in tables.items():
        pd.DataFrame(rows).to_csv(RESULTS / f"{title}.csv", index=False)
    quality = dict(status="PASS", order_replays=audits, causal_cutoffs_per_market=3)
    (RESULTS / "QA.json").write_text(json.dumps(quality, indent=2) + "\n")
    print("QA_PASS", len(audits), flush=True)


if __name__ == "__main__":
    main()
