#!/usr/bin/env python3
import json
from pathlib import Path
import pandas as pd
import download_europe120 as d

# Frozen transfer-test wrapper: no performance criterion is used for membership.
# The user requested 120 tickers, 20 per economic cluster. Distinct listings/share
# classes are allowed as separate tickers as long as the underlying exposure is EU.
d.PRE2017_CUTOFF = pd.Timestamp("2019-01-31")
d.MIN_PRE2017_ROWS = 252
d.norm_name = lambda s: ""  # disable fund-name deduplication; symbol uniqueness remains enforced

rc = d.main()
if rc == 0:
    p = Path("europe120/output/manifest.json")
    m = json.loads(p.read_text())
    m["evaluation_start"] = "2019-02-01"
    m["history_requirement"] = ">=252 observations by 2019-01-31"
    m["ticker_policy"] = "distinct ticker symbols; multiple listings/share classes of the same fund are allowed; exposure must remain European/EU"
    m["selection_rule"] = "frozen Yahoo query order + symbol order; economic-name filters; first 20 valid ticker symbols per cluster with >=252 observations by 2019-01-31 and coverage through 2026-07-31; no return/performance criterion"
    for rec in m.get("selected", []):
        if "pre2017_rows" in rec:
            rec["pre2019_rows"] = rec.pop("pre2017_rows")
    p.write_text(json.dumps(m, indent=2) + "\n")

    cov = Path("europe120/output/coverage.csv")
    if cov.exists():
        q = pd.read_csv(cov)
        if "pre2017_rows" in q.columns:
            q = q.rename(columns={"pre2017_rows":"pre2019_rows"})
            q.to_csv(cov, index=False)
raise SystemExit(rc)
