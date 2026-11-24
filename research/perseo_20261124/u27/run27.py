"""Test selective isolation of an individual stop on top of Perseo U24."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "u25"))

from run25 import previous, run_scenario, SCENARIOS

import numpy as np
import pandas as pd

RESULTS = ROOT / "results"
THRESHOLDS = dict(CORR70=0.70, CORR80=0.80, CORR90=0.90, CORR80_BREADTH=0.80)
RULES = ("LOCAL_STOP", *THRESHOLDS)


def leg_correlation(state):
    names = state["tickers"]
    cash = np.array(["CASH_" in name for name in names])
    observed = state.get("low_observed", state.get("observed"))
    close = pd.DataFrame(state["C"])
    if observed is not None:
        close = close.where(observed)
    returns = np.log(close.where(close > 0)).diff()
    dates = state["dates"]
    legs = np.stack([state["d1"][0], state["d2"][0]], axis=1)
    result = np.full(len(dates), np.nan)
    for a, b in np.unique(legs, axis=0):
        if min(a, b) < 0 or a == b or cash[[a, b]].any():
            continue
        both = (legs[:, 0] == a) & (legs[:, 1] == b)
        relation = returns[a].rolling(63, min_periods=45).corr(returns[b]).shift(1).to_numpy()
        result[both] = relation[both]
    return result


def isolation_rules(state, correlation):
    prior_negative = np.r_[np.nan, state["uneg"][:-1]]
    result = {name: correlation < threshold for name, threshold in THRESHOLDS.items()}
    result["CORR80_BREADTH"] &= prior_negative < 0.60
    return dict(LOCAL_STOP=np.ones(len(correlation), bool), **result)


def main():
    RESULTS.mkdir(exist_ok=True)
    sums, windows, monthly, annual, audits, modes = [], [], [], [], [], []
    with TemporaryDirectory(prefix="perseo_u27_") as temporary:
        for market in previous.MARKETS:
            state = previous.state(market)
            correlation = leg_correlation(state)
            rule_masks = isolation_rules(state, correlation)
            for cutoff in (300, 900, 1400):
                changed = dict(state, C=state["C"].copy())
                changed["C"][cutoff:] *= np.linspace(0.71, 1.29, changed["C"].shape[1])
                recalculated = leg_correlation(changed)
                np.testing.assert_array_equal(correlation[:cutoff + 1], recalculated[:cutoff + 1])
            built = previous.signals(state, market)
            modes.append(pd.DataFrame(dict(
                market=market, date=state["dates"], correlation=correlation, **rule_masks
            )))
            for rule in RULES:
                mask = rule_masks[rule].astype(int)
                print("REPLAY", market, rule, int(mask.sum()), flush=True)
                for bps, lag in SCENARIOS:
                    timing = np.r_[mask[0], mask[:-1]] if lag else mask
                    source = dict(state, risk_mode=timing)
                    row, periods, months, years, audit = run_scenario(
                        market, rule, source, built, bps, lag, Path(temporary)
                    )
                    sums.append(row)
                    windows.extend(periods)
                    monthly.extend(months)
                    annual.extend(years)
                    audits.append(audit)
    tables = dict(SUMMARY=sums, WINDOWS=windows, MONTHLY=monthly, ANNUAL=annual)
    for title, rows in tables.items():
        pd.DataFrame(rows).to_csv(RESULTS / f"{title}.csv", index=False)
    pd.concat(modes).to_csv(RESULTS / "RISK_SIGNALS.csv", index=False)
    quality = dict(status="PASS", order_replays=audits, causal_cutoffs_per_market=3)
    (RESULTS / "QA.json").write_text(json.dumps(quality, indent=2) + "\n")
    print("QA_PASS", len(audits), flush=True)


if __name__ == "__main__":
    main()
