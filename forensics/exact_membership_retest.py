#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PACKAGE = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path("EXACT_MEMBERSHIP_RETEST").resolve()
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(PACKAGE / "source"))
import titanium_reconstruction_v6 as v6  # noqa: E402
import titanium_retrained_current_data_audit as base  # noqa: E402


def load_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        x = pd.read_parquet(path)
    else:
        x = pd.read_csv(path)
    for c in ["signal_date", "entry_date", "exit_date"]:
        if c in x.columns:
            x[c] = pd.to_datetime(x[c])
    return x


pred = load_frame(PACKAGE / "panels" / "SUPER_GOLD_OOS_SCORE_PANEL.parquet")
opp = load_frame(PACKAGE / "panels" / "TITANIUM_V3_OPPORTUNITY_OOS_CLUSTER_PANEL.csv")
clusters = load_frame(PACKAGE / "panels" / "DYNAMIC_CLUSTERS_MONTHLY.csv")
cal = load_frame(PACKAGE / "panels" / "MONTHLY_CALENDAR.csv")
existing = pd.read_csv(PACKAGE / "panels" / "BASKET_MEMBERSHIP_500.csv")

mats = {}
for key in ["Open", "High", "Low", "Close", "Volume"]:
    p = PACKAGE / "data" / f"{key.upper()}.parquet"
    x = pd.read_parquet(p)
    x.index = pd.to_datetime(x.index)
    mats[key] = x

# Historical Super Gold basket eligibility was exact full OOS coverage, not >=95%.
total_dates = int(pred["signal_date"].nunique())
coverage = pred.groupby("ticker")["signal_date"].nunique().sort_index()
eligible = set(coverage[coverage.eq(total_dates)].index.astype(str))

cats = {
    c: sorted([t for t in xs if t in eligible])
    for c, xs in base.CATEGORY_TICKERS.items()
}
if any(len(v) < 4 for v in cats.values()):
    raise RuntimeError({k: len(v) for k, v in cats.items()})

rng = random.Random(20260721)
seen: set[tuple[str, ...]] = set()
baskets: list[tuple[str, ...]] = []
while len(baskets) < 500:
    selected: list[str] = []
    for c in sorted(cats):
        selected.extend(rng.sample(cats[c], 4))
    basket = tuple(sorted(selected))
    if basket not in seen:
        seen.add(basket)
        baskets.append(basket)

exact_membership = pd.DataFrame(
    [
        {"basket": b, "ticker": t, "category": base.TICKER_CATEGORY[t]}
        for b, names in enumerate(baskets)
        for t in names
    ]
)
exact_membership.to_csv(OUT / "SUPER_GOLD_BASKET_MEMBERSHIP_EXACT_REGENERATED.csv", index=False)

membership_lines = []
for b, g in exact_membership.groupby("basket", sort=True):
    membership_lines.append(f"{b}:" + ",".join(sorted(g.ticker.astype(str))))
membership_sha = hashlib.sha256("\n".join(membership_lines).encode()).hexdigest()

existing_sets = {
    int(b): set(g.ticker.astype(str)) for b, g in existing.groupby("basket", sort=True)
}
exact_sets = {
    int(b): set(g.ticker.astype(str)) for b, g in exact_membership.groupby("basket", sort=True)
}
jacc = []
exact_same = 0
for b in range(500):
    a, e = existing_sets[b], exact_sets[b]
    jacc.append(len(a & e) / len(a | e))
    exact_same += int(a == e)

# Use the already fitted OOS predictions to isolate ONLY basket membership.
idx, EB, ED, ER, active, margin, cond, bs, bw, ds, dw = v6.simulate_all(
    baskets, pred, opp, clusters, mats, cal
)

rows = []
for b in range(500):
    for name, arr in [("BASE", EB[b]), ("DIRECT", ED[b]), ("ROUTER", ER[b])]:
        cagr, maxdd, sharpe, final_equity = v6.metrics(arr, idx)
        rows.append(
            {
                "basket": b,
                "strategy": name,
                "cagr": cagr,
                "maxdd": maxdd,
                "sharpe": sharpe,
                "final_equity": final_equity,
                "router_active_months": int(active.sum()),
                "direct_condition_months": int(cond[b].sum()),
            }
        )
results = pd.DataFrame(rows)
results.to_csv(OUT / "BASKET_RESULTS_EXACT_MEMBERSHIP.csv", index=False)

# Global result under the common router schedule derived from the exact 500 baskets.
global_universe = [sorted(pred.ticker.astype(str).unique())]
idxg, EBg, EDg, ERg, activeg, marging, condg, *_ = v6.simulate_all(
    global_universe, pred, opp, clusters, mats, cal, forced_active=active
)
grows = []
for name, arr in [("BASE", EBg[0]), ("DIRECT", EDg[0]), ("ROUTER", ERg[0])]:
    cagr, maxdd, sharpe, final_equity = v6.metrics(arr, idxg)
    grows.append({"strategy": name, "cagr": cagr, "maxdd": maxdd, "sharpe": sharpe, "final_equity": final_equity})
global_score = pd.DataFrame(grows)
global_score.to_csv(OUT / "GLOBAL_SCORECARD_EXACT_MEMBERSHIP_SCHEDULE.csv", index=False)

# Existing package result for direct comparison.
old = pd.read_csv(PACKAGE / "backtest" / "BASKET_RESULTS_500.csv")
compare_rows = []
for strategy in ["BASE", "DIRECT", "ROUTER"]:
    qnew = results[results.strategy.eq(strategy)]
    qold = old[old.strategy.eq(strategy)]
    compare_rows.append(
        {
            "strategy": strategy,
            "aug6_mean_cagr": float(qold.cagr.mean()),
            "exact_membership_mean_cagr": float(qnew.cagr.mean()),
            "delta_pp": float((qnew.cagr.mean() - qold.cagr.mean()) * 100),
            "exact_membership_median_cagr": float(qnew.cagr.median()),
            "p05": float(qnew.cagr.quantile(.05)),
            "p95": float(qnew.cagr.quantile(.95)),
            "median_maxdd": float(qnew.maxdd.median()),
        }
    )
comparison = pd.DataFrame(compare_rows)
comparison.to_csv(OUT / "MEMBERSHIP_EFFECT_SCORECARD.csv", index=False)

summary = {
    "oos_dates": total_dates,
    "pred_tickers": int(pred.ticker.nunique()),
    "fully_observed_tickers": len(eligible),
    "eligible_by_category": {k: len(v) for k, v in cats.items()},
    "excluded_from_full_coverage": sorted(set(pred.ticker.astype(str).unique()) - eligible),
    "membership_sha256": membership_sha,
    "existing_vs_exact_baskets_identical": exact_same,
    "existing_vs_exact_mean_jaccard": float(np.mean(jacc)),
    "router_active_months": int(active.sum()),
    "frozen_reference": {"BASE": 0.21654064, "ROUTER": 0.22742810},
    "new_means": {
        s: float(results.loc[results.strategy.eq(s), "cagr"].mean())
        for s in ["BASE", "DIRECT", "ROUTER"]
    },
    "global": global_score.set_index("strategy").to_dict("index"),
}
(OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2, default=str))

print(json.dumps(summary, indent=2, default=str))
print("\nMembership effect:\n", comparison.to_string(index=False))
print("\nGlobal:\n", global_score.to_string(index=False))
