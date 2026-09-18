from __future__ import annotations

import numpy as np
import pandas as pd


def _category_prior(row: pd.Series, cols, category, top_n=2):
    raw={}
    for c in sorted(set(category.values())):
        vals=[float(row[t]) for t in cols if category.get(t)==c and t in row.index and np.isfinite(row[t])]
        raw[c]=np.mean(sorted(vals,reverse=True)[:top_n]) if vals else np.nan
    return pd.Series(raw).rank(method="average",pct=True)


def build_category_state(scores, cols, category):
    panel=scores.pivot(index="signal_date",columns="ticker",values="score").reindex(columns=cols)
    priors=[]; leaders=[]
    for dt,row in panel.iterrows():
        p=_category_prior(row,cols,category)
        priors.append(p.rename(dt))
        leaders.append(p.sort_values(ascending=False,kind="stable").index[0])
    prior=pd.DataFrame(priors)
    stable4=[]
    for i in range(len(leaders)):
        stable4.append(i>=3 and len(set(leaders[i-3:i+1]))==1)
    state=pd.DataFrame({"signal_date":panel.index,"category_leader":leaders,"stable4":stable4}).set_index("signal_date")
    return panel,prior,state


def allocation_table(scores,baskets,dates,cols,category,*,mode="cvx70_top3",
                     threshold=.12,top_weight=.75):
    """Causal category-reranking variants from regenerated scores only.

    modes:
      cvx70_top3: stable4 -> 30% base + 70% category on base top3
      cvx25_top5: stable4 -> 75% base + 25% category on base top5
      concentration_lock: same ranking as cvx70_top3, sizing from original base gap
      confidence_switch: original base gap >= .12 -> cvx70/top3/100%; else cvx25/top5/75-25
    """
    panel,prior,state=build_category_state(scores,cols,category)
    signal_dates=list(panel.index); rows=[]
    for i,(dt,row) in enumerate(panel.iterrows()):
        if i+1>=len(signal_dates): break
        ep=dates.searchsorted(dt,side="right")
        xp=dates.searchsorted(signal_dates[i+1],side="right")
        if ep>=len(dates) or xp>=len(dates) or xp<=ep: continue
        gate=bool(state.loc[dt,"stable4"])
        for bid,basket in enumerate(baskets):
            local=sorted([(t,float(row[t])) for t in basket if t in row.index and np.isfinite(row[t])],
                         key=lambda x:(-x[1],x[0]))
            if len(local)<5: raise ValueError(f"insufficient names {dt} basket {bid}")
            base1,base2=local[0],local[1]
            base_gap=base1[1]-base2[1]
            if not gate:
                chosen=[base1,base2]
                w1=1. if base_gap>=threshold else top_weight
            else:
                if mode=="cvx70_top3":
                    k,catw=3,.70
                elif mode=="cvx25_top5":
                    k,catw=5,.25
                elif mode=="concentration_lock":
                    k,catw=3,.70
                elif mode=="confidence_switch":
                    if base_gap>=threshold: k,catw=3,.70
                    else: k,catw=5,.25
                else:
                    raise ValueError(mode)
                chosen=sorted([(t,(1-catw)*s+catw*float(prior.loc[dt,category[t]]))
                               for t,s in local[:k]],key=lambda x:(-x[1],x[0]))[:2]
                if mode in {"concentration_lock","confidence_switch"}:
                    w1=1. if base_gap>=threshold else top_weight
                else:
                    w1=1. if chosen[0][1]-chosen[1][1]>=threshold else top_weight
            rows.append({"signal_date":dt,"entry_date":dates[ep],"exit_date":dates[xp],
                         "basket":str(bid),"top1":chosen[0][0],"top2":chosen[1][0],
                         "w1":float(w1),"w2":float(1-w1),"gate_active":gate,
                         "base_gap":float(base_gap),"mode":mode})
    return pd.DataFrame(rows),state.reset_index()
