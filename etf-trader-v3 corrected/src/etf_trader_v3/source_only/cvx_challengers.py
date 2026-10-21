"""Source-only CVX challengers.

The category prior and stable-4of4 gate are regenerated from the current
source-only score panel. Historical CVX calendars, selections and TIT_R are
never consumed.

Policies:
- concentration_lock: CVX70 reranks baseline top-3 when gate is active, but
  100/0 vs 75/25 is fixed by the ORIGINAL baseline score gap >= 0.12.
- confidence_switch: when gate is active, baseline gap >=0.12 uses CVX70_TOP3
  and 100/0; baseline gap <0.12 uses CVX25_TOP5 and 75/25.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _prior_and_gate(scores, cols, category, stable_months=4):
    panel=scores.pivot(index="signal_date",columns="ticker",values="score").reindex(columns=cols)
    cat_names=sorted(set(category.values()))
    prior=[];leaders=[]
    for dt,row in panel.iterrows():
        raw={}
        for c in cat_names:
            vals=sorted(
                [float(row[t]) for t in cols if category[t]==c and np.isfinite(row[t])],
                reverse=True,
            )
            raw[c]=np.mean(vals[:2]) if len(vals)>=2 else np.nan
        rank=pd.Series(raw,dtype=float).rank(method="average",pct=True)
        prior.append(rank.rename(dt))
        leaders.append(rank.sort_values(ascending=False,kind="mergesort").index[0])
    prior=pd.DataFrame(prior)
    stable=[]
    for i in range(len(leaders)):
        stable.append(
            i>=stable_months-1
            and len(set(leaders[i-stable_months+1:i+1]))==1
        )
    gate=pd.DataFrame({"signal_date":panel.index,"leader":leaders,"stable_4of4":stable})
    return panel,prior,gate


def allocation_tables(
    scores,
    baskets,
    dates,
    cols,
    category,
    *,
    threshold=.12,
    top_weight=.75,
    stable_months=4,
):
    panel,prior,gate=_prior_and_gate(scores,cols,category,stable_months)
    signal_dates=list(panel.index)
    out={"baseline":[],"cvx70":[],"concentration_lock":[],"confidence_switch":[]}

    for i,(dt,row) in enumerate(panel.iterrows()):
        if i+1>=len(signal_dates):
            break
        ep=dates.searchsorted(dt,side="right")
        xp=dates.searchsorted(signal_dates[i+1],side="right")
        if ep>=len(dates) or xp>=len(dates) or xp<=ep:
            continue
        gate_on=bool(gate.iloc[i].stable_4of4)

        for bid,basket in enumerate(baskets):
            local=sorted(
                [(t,float(row[t])) for t in basket if t in row.index and np.isfinite(row[t])],
                key=lambda x:(-x[1],x[0]),
            )
            if len(local)<5:
                raise ValueError(f"need >=5 eligible names: {dt} basket {bid}")

            (b1,bs1),(b2,bs2)=local[:2]
            base_gap=float(bs1-bs2)
            base_w1=1.0 if base_gap>=threshold else top_weight
            common={"signal_date":dt,"entry_date":dates[ep],"exit_date":dates[xp],"basket":str(bid),
                    "gate_active":gate_on,"baseline_gap":base_gap}

            out["baseline"].append({**common,"top1":b1,"top2":b2,"w1":base_w1,"w2":1-base_w1})

            # canonical source-only CVX70_TOP3: blended score also controls sizing
            if gate_on:
                ranked70=sorted(
                    [(t,.30*s+.70*float(prior.loc[dt,category[t]])) for t,s in local[:3]],
                    key=lambda x:(-x[1],x[0]),
                )
            else:
                ranked70=local[:2]
            (c1,cs1),(c2,cs2)=ranked70[:2]
            cvx_w1=1.0 if float(cs1-cs2)>=threshold else top_weight
            out["cvx70"].append({**common,"top1":c1,"top2":c2,"w1":cvx_w1,"w2":1-cvx_w1})

            # Same CVX70 ranking, native baseline concentration state.
            out["concentration_lock"].append({
                **common,"top1":c1,"top2":c2,"w1":base_w1,"w2":1-base_w1
            })

            # Existing V2 threshold switches aggressiveness without a new threshold.
            if not gate_on:
                s1,s2=b1,b2
            elif base_gap>=threshold:
                ranked=ranked70
                s1,s2=ranked[0][0],ranked[1][0]
            else:
                ranked25=sorted(
                    [(t,.75*s+.25*float(prior.loc[dt,category[t]])) for t,s in local[:5]],
                    key=lambda x:(-x[1],x[0]),
                )
                s1,s2=ranked25[0][0],ranked25[1][0]
            out["confidence_switch"].append({
                **common,"top1":s1,"top2":s2,"w1":base_w1,"w2":1-base_w1,
                "mode":"V2" if not gate_on else ("CVX70_TOP3" if base_gap>=threshold else "CVX25_TOP5"),
            })

    return {k:pd.DataFrame(v) for k,v in out.items()},gate
