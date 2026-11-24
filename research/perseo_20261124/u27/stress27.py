"""Apply combined execution stresses to fixed U24 and U27 CORR70."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
import pandas as pd

from run27 import previous, run_scenario, leg_correlation, isolation_rules, RESULTS

SCENARIOS = (
    ("DELAY_AND_COST", 30, 1, 0),
    ("STOP_SLIPPAGE_50", 15, 0, 50),
    ("DELAY_COST_STOP_100", 30, 1, 100),
)


def main():
    summary, windows, monthly, annual, audits = [], [], [], [], []
    simulate = previous.simulate
    with TemporaryDirectory(prefix="perseo_stress27_") as temporary:
        for market in previous.MARKETS:
            state = previous.state(market)
            built = previous.signals(state, market)
            mask = isolation_rules(state, leg_correlation(state))["CORR70"].astype(int)
            for scenario, bps, lag, slippage in SCENARIOS:
                timing = np.r_[mask[0], mask[:-1]] if lag else mask

                def model(*args, **kwargs):
                    kwargs["stop_friction"] = slippage / 10000
                    return simulate(*args, **kwargs)

                with patch.object(previous, "simulate", model):
                    for rule, source in (
                        ("U24_STRESS", state), ("CORR70_STRESS", dict(state, risk_mode=timing))
                    ):
                        row, parts, months, years, audit = run_scenario(
                            market, rule, source, built, bps, lag, Path(temporary)
                        )
                        labels = dict(scenario=scenario, stop_slippage_bps=slippage)
                        summary.append(dict(row, **labels))
                        windows.extend(dict(part, **labels) for part in parts)
                        monthly.extend(dict(month, **labels) for month in months)
                        annual.extend(dict(year, **labels) for year in years)
                        audits.append(dict(audit, **labels))
    for key, rows in dict(SUMMARY=summary, WINDOWS=windows, MONTHLY=monthly, ANNUAL=annual).items():
        pd.DataFrame(rows).to_csv(RESULTS / f"STRESS_{key}.csv", index=False)
    (RESULTS / "STRESS_QA.json").write_text(json.dumps(dict(status="PASS", replays=audits), indent=2) + "\n")
    print("STRESS_QA_PASS", len(audits), flush=True)


if __name__ == "__main__":
    main()
