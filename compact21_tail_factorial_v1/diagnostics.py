import numpy as np
import pandas as pd
CUTOFF=pd.Timestamp("2026-07-01")
def monthly_quality(score,cal,tickers,labels):
    out=[]
    labels=labels.copy();labels["signal_date"]=pd.to_datetime(labels.signal_date)
    if score.shape!=(len(cal),len(tickers)):raise ValueError("Score dimensions")
    for m,day in enumerate(pd.DatetimeIndex(cal.signal_date)):
        top=[tickers[j] for j in np.argsort(-score[m],kind="stable")[:5]]
        g=labels.loc[labels.signal_date.eq(day)]
        if len(g)!=149:raise ValueError("Monthly source mismatch")
        z=g.set_index("ticker")
        if not set(top).issubset(z.index):raise ValueError("Missing prediction target")
        complete=pd.notna(z.loc[top[0],"exit_date_21"]) and pd.Timestamp(z.loc[top[0],"exit_date_21"])<=CUTOFF
        row=dict(date=str(day.date()),mature=bool(complete),top1=top[0])
        if complete:
            values=z.target_ret_21.astype(float)
            if not np.isfinite(values).all():raise ValueError("Missing matured label")
            best=set(values.nlargest(5).index)
            row.update(ret=float(values.loc[top[0]]),
                regret=float(values.nlargest(15).mean()-values.loc[top[0]]),
                exact_hit=bool(values.loc[top[0]]==values.max()),
                top5_hit=top[0] in best,overlap=len(set(top)&best)/5.)
        out.append(row)
    if len(out)!=114 or sum(x["mature"] for x in out)!=113:
        raise ValueError("Unexpected monthly maturity coverage")
    return out
