#!/usr/bin/env python3
"""Predeclared representation and economic-family drop-one ablation.
Uses the same original 149 ETF snapshot and V2 127-leaf model implementation.
All variants are trained on identical common eligible rows; this is an
exploratory experiment, not a final independent holdout confirmation.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import v2_feature_pruning as p

BASE=list(p.k.F2D_FEATURES)
def family(n):
    return n.removesuffix("_pct").removesuffix("_dev")

def omit(name,pred):
    x=[v for v in BASE if not pred(v,family(v))]
    assert x and len(x)<len(BASE) and len(set(x))==len(x),name
    return x

p.SUBSETS.update({
    "NO_DEV": omit("NO_DEV",lambda c,f:c.endswith("_dev")),
    "NO_PCT": omit("NO_PCT",lambda c,f:c.endswith("_pct")),
    "NO_RAW": omit("NO_RAW",lambda c,f:not c.endswith(("_pct","_dev"))),
    "NO_MARKET": omit("NO_MARKET",lambda c,f:f.startswith(("beta_mkt","corr_mkt"))),
    "NO_MOMENTUM": omit("NO_MOMENTUM",lambda c,f:f.startswith(("mom","acc_mom","ma_gap","ema_gap","breakout_pos")) or f in ("rsi14","positive_frac63")),
    "NO_VOLRISK": omit("NO_VOLRISK",lambda c,f:f.startswith(("vol","downvol","drawdown","gkvol","skew","kurt","max_loss","max_gain","cvar","sign_entropy","autocorr","efficiency"))),
    "NO_LIQUIDITY": omit("NO_LIQUIDITY",lambda c,f:f.startswith(("volume_","log_adv"))),
})

if __name__=="__main__":
    for name in ("BASE125","NO_DEV","NO_PCT","NO_RAW","NO_MARKET","NO_MOMENTUM","NO_VOLRISK","NO_LIQUIDITY"):
        print("SUBSET_CONTRACT",name,len(p.SUBSETS[name]),flush=True)
    p.main()
