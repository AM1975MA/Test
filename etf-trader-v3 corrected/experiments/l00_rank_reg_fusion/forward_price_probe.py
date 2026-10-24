#!/usr/bin/env python3
"""Network-only price availability and continuity probe; no model training."""
from __future__ import annotations
import json
import pandas as pd, yfinance as yf
from pathlib import Path
D=Path("forward_probe");D.mkdir(exist_ok=True)
res=[]
for t in ["SPY","QQQ","GLD","TUR","BIL"]:
    try:
        x=yf.download(t,start="2026-06-22",end="2026-10-25",auto_adjust=False,
                      actions=False,progress=False,threads=False)
        if isinstance(x.columns,pd.MultiIndex):
            x.columns=x.columns.get_level_values(0)
        z=dict(ticker=t,n_rows=len(x),last=str(x.index.max().date()) if len(x) else None,
               n_after_july=int((x.index>pd.Timestamp("2026-07-01")).sum()) if len(x) else 0,
               cols=list(x.columns),around_anchor=float(x.loc["2026-07-01","Adj Close"]) if len(x) and pd.Timestamp("2026-07-01") in x.index else None)
    except Exception as e:z=dict(ticker=t,error=repr(e))
    res.append(z);print("PRICE_PROBE",json.dumps(z),flush=True)
(D/"PROBE.json").write_text(json.dumps(res,indent=2))
assert sum(p.get("n_after_july",0)>=60 for p in res)>=3,"Insufficient trusted post-July data for 3+ key ETFs"
print("PRICE_PROBE_PASS",flush=True)
