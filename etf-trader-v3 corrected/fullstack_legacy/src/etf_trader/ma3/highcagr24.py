"""Frozen High-CAGR 24 risk transform selected on 2017-2022."""
from __future__ import annotations

import numpy as np


C4_GROSS = 0.945
SEVERE_GROSS = 0.66
TOP1_MARGIN = 0.03


def apply_highcagr24(
    ddfirst_gross: np.ndarray,
    base_weight1: np.ndarray,
    score_margin: np.ndarray,
    *,
    c4: float = C4_GROSS,
    severe: float = SEVERE_GROSS,
    top1_margin: float = TOP1_MARGIN,
) -> tuple[np.ndarray,np.ndarray]:
    """Apply the frozen 2026-09-23 High-CAGR24 transform.

    DD-first 3-vote state (.95) is restored to 100% gross.
    DD-first 4+ vote state (.75) becomes 94.5% gross.
    DD-first severe (.25) becomes 66% gross.
    When gross is 100% and the producer top1/top2 score margin is >=3%,
    concentrate the risky sleeve 100% in top1.
    """
    g=np.asarray(ddfirst_gross,dtype=float).copy()
    wg=np.asarray(base_weight1,dtype=float).copy()
    margin=np.asarray(score_margin,dtype=float)
    if wg.shape!=margin.shape:
        raise ValueError("weight1 and score_margin shapes differ")
    if wg.shape[1]!=len(g):
        raise ValueError("daily gross length differs from allocation horizon")

    g[np.isclose(g,.95)]=1.0
    g[np.isclose(g,.75)]=float(c4)
    g[g<=.251]=float(severe)
    wg[(g[None,:]>=.999)&(margin>=float(top1_margin))]=1.0
    return g,wg
