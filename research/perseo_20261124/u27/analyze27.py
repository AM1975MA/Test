"""Compare U25–U27 with frozen U24 on common months without retuning."""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
VERSIONS = ("u25", "u26", "u27")


def collect(table):
    return pd.concat(
        [pd.read_csv(ROOT.parent / version / "results" / f"{table}.csv").assign(version=version.upper())
         for version in VERSIONS],
        ignore_index=True,
    )


def matched_differences():
    scenarios = ["market", "bps", "lag"]
    table = collect("SUMMARY")
    control = table.loc[table.rule.eq("U24"), scenarios + ["cagr", "maxdd", "orders"]]
    compared = table.merge(control, on=scenarios, validate="many_to_one", suffixes=("", "_u24"))
    compared["cagr_delta_pp"] = 100 * (compared.cagr - compared.cagr_u24)
    compared["drawdown_delta_pp"] = 100 * (compared.maxdd - compared.maxdd_u24)
    return compared


def uncertainty():
    panel = collect("MONTHLY")
    nominal = panel.loc[(panel.bps == 15) & (panel.lag == 0)]
    pairs = nominal.pivot(index="month", columns=["version", "rule", "market"], values="ret")
    keys = [key for key in pairs if key[1] not in ("U20", "U24") and key[2] in ("EU", "USA", "TR")]
    assert not pairs.isna().any().any()
    differences = np.asarray([
        np.log1p(pairs[key]) - np.log1p(pairs["U25", "U24", key[2]])
        for key in keys
    ]).T
    n = len(differences)
    rng = np.random.default_rng(20261124)
    starts = rng.integers(0, n, (3000, int(np.ceil(n / 12)), 1))
    indices = ((starts + np.arange(12)) % n).reshape(3000, -1)[:, :n]
    sampled = differences[indices].mean(axis=1) * 1200
    point = differences.mean(axis=0) * 1200
    spread = sampled.std(axis=0, ddof=1)
    informative = spread > 1e-12
    max_t = np.max(np.abs((sampled[:, informative] - point[informative]) / spread[informative]), axis=1)
    critical = np.quantile(max_t, 0.95)
    nominal_ci = np.quantile(sampled, [0.025, 0.975], axis=0)
    output = []
    for j, (version, rule, market) in enumerate(keys):
        delta = differences[:, j]
        top = np.argsort(np.abs(delta))[-2:]
        output.append(dict(
            version=version, rule=rule, market=market, ann_log_delta_pp=point[j],
            lo_nominal=nominal_ci[0, j], hi_nominal=nominal_ci[1, j],
            lo_simultaneous=point[j] - critical * spread[j],
            hi_simultaneous=point[j] + critical * spread[j],
            largest_month=pairs.index[top[1]], second_largest_month=pairs.index[top[0]],
            ann_log_delta_pp_excluding_top_two=np.delete(delta, top).mean() * 1200,
            positive_months=int((delta > 0.0005).sum()),
            negative_months=int((delta < -0.0005).sum()),
        ))
    return pd.DataFrame(output)


if __name__ == "__main__":
    matched_differences().to_csv(ROOT / "results" / "COMPARISON_U24.csv", index=False)
    uncertainty().to_csv(ROOT / "results" / "UNCERTAINTY.csv", index=False)
