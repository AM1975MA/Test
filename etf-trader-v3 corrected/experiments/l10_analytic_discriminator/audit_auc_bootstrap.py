#!/usr/bin/env python3
"""Posthoc AUC uncertainty audit for L10.D1, on 101 calendar months.

Days with zero or all positive severe loss events have no defined per-month AUC.
Keep all 101 months in circular calendar-block draws; use pairwise nanmean within
each draw. Do NOT silently treat the eventless dates as independent observations.
"""
from __future__ import annotations
import argparse, math
import numpy as np
import pandas as pd

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--monthly",required=True)
    a.add_argument("--out",required=True)
    p=a.parse_args()
    f=pd.read_csv(p.monthly)
    assert len(f)==101 and f.signal_date.nunique()==101
    ac=f.analytic_unique_loss_auc.to_numpy(float)
    co=f.corrected_unique_loss_auc.to_numpy(float)
    assert np.array_equal(np.isfinite(ac),np.isfinite(co))
    assert int(np.isfinite(ac).sum())==71
    n=len(f);reps=10000;width=6
    rng=np.random.default_rng(20261022)
    starts=rng.integers(n,size=(reps,math.ceil(n/width)))
    ix=((starts[:,:,None]+np.arange(width))%n).reshape(reps,-1)[:,:n]
    contrasts=[
      ("analytic_minus_chance_AUC",ac-.5),
      ("corrected_minus_chance_AUC",co-.5),
      ("analytic_minus_corrected_risk_AUC",ac-co),
    ]
    rows=[]
    for name,z in contrasts:
        means=np.nanmean(z[ix],axis=1)
        rows.append(dict(contrast=name,mean=float(np.nanmean(z)),
            ci95_low=float(np.quantile(means,.025)),ci95_high=float(np.quantile(means,.975)),
            n_mature_months=n,n_months_with_class_both=int(np.isfinite(z).sum()),
            block=width,replications=reps,seed=20261022))
    pd.DataFrame(rows).to_csv(p.out,index=False)
    print(pd.DataFrame(rows).to_string(index=False))
if __name__=="__main__":
    main()
