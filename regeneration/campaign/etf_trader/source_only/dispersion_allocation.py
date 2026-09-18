"""Predeclared source-only concentration rules for the next experiment.

All quantities are computed from the regenerated score cross-section at signal
close.  Stability uses only earlier and current signals.  The rules alter the
top-1/top-2 weights but never introduce a new security or a future observation.
"""
import numpy as np
import pandas as pd

RULES=('gap_linear','iqr_confidence','stable3_gap','stable3_iqr')

def allocation_tables(scores,baskets,dates,cols):
    panel=scores.pivot(index='signal_date',columns='ticker',values='score').reindex(columns=cols)
    signal_dates=list(panel.index); history=[[] for _ in baskets]
    rows={name:[] for name in RULES}; diagnostics=[]
    for i,(dt,row) in enumerate(panel.iterrows()):
        if i+1>=len(signal_dates):break
        ep=dates.searchsorted(dt,side='right');xp=dates.searchsorted(signal_dates[i+1],side='right')
        if ep>=len(dates) or xp>=len(dates) or xp<=ep:continue
        for bid,basket in enumerate(baskets):
            local=sorted([(t,float(row[t])) for t in basket if np.isfinite(row[t])],key=lambda x:(-x[1],x[0]))
            if len(local)<3:raise ValueError(f'insufficient eligible names: {dt} basket {bid}')
            (t1,s1),(t2,s2)=local[:2];values=np.array([x[1] for x in local],float)
            gap=s1-s2;iqr=float(np.quantile(values,.75)-np.quantile(values,.25));ratio=gap/max(iqr,1e-12)
            history[bid].append(t1);stable3=len(history[bid])>=3 and len(set(history[bid][-3:]))==1
            weights={
              'gap_linear':float(np.clip(.60+2.5*gap,.60,1.)),
              'iqr_confidence':1. if ratio>=.75 else (.75 if ratio>=.25 else .60),
              'stable3_gap':(1. if gap>=.12 else .75) if stable3 else .60,
              'stable3_iqr':(1. if ratio>=.50 else (.75 if ratio>=.25 else .60)) if stable3 else .60,
            }
            common={'signal_date':dt,'entry_date':dates[ep],'exit_date':dates[xp],
                    'basket':str(bid),'top1':t1,'top2':t2}
            for name,w1 in weights.items():rows[name].append({**common,'w1':w1,'w2':1-w1})
            diagnostics.append({'signal_date':dt,'basket':bid,'gap':gap,'local_iqr':iqr,
                                'gap_iqr_ratio':ratio,'stable3':stable3})
    return {name:pd.DataFrame(records) for name,records in rows.items()},pd.DataFrame(diagnostics)
