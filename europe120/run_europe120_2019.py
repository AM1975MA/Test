#!/usr/bin/env python3
import json
from pathlib import Path
import pandas as pd
import download_europe120 as d

# The European UCITS universe is materially younger than the original US-heavy
# universe. Require one full year of history before the evaluation start, but do
# not use any performance information for selection.
d.PRE2017_CUTOFF = pd.Timestamp("2019-01-31")
d.MIN_PRE2017_ROWS = 252

rc = d.main()
if rc == 0:
    p = Path("europe120/output/manifest.json")
    m = json.loads(p.read_text())
    m["evaluation_start"] = "2019-02-01"
    m["history_requirement"] = ">=252 observations by 2019-01-31"
    m["selection_rule"] = "frozen Yahoo query order + symbol order; economic-name filters; first 20 distinct funds per cluster with >=252 observations by 2019-01-31 and coverage through 2026-07-31; no return/performance criterion"
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
