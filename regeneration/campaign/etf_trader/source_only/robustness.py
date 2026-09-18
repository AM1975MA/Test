"""Robust paired diagnostics for source-only strategy challengers."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .statistics import metrics, paired_bootstrap, returns, subpath


def annual_uplift(dates, base, other):
    dates=pd.DatetimeIndex(dates)
    rows=[]
    for year in sorted(set(dates.year)):
        m=np.asarray(dates.year==year)
        if m.sum()<20:
            continue
        b=metrics(subpath(base,m))
        o=metrics(subpath(other,m))
        rows.append({
            "year":int(year),
            "delta_cagr_pp":100*(o["mean_cagr"]-b["mean_cagr"]),
            "delta_maxdd_pp":100*(o["mean_maxdd"]-b["mean_maxdd"]),
            "delta_sharpe":o["mean_sharpe_rf0"]-b["mean_sharpe_rf0"],
        })
    return pd.DataFrame(rows)


def leave_one_year_out(dates, base, other):
    dates=pd.DatetimeIndex(dates)
    rows=[]
    for year in sorted(set(dates.year)):
        m=np.asarray(dates.year!=year)
        b=metrics(subpath(base,m));o=metrics(subpath(other,m))
        rows.append({
            "excluded_year":int(year),
            "delta_cagr_pp":100*(o["mean_cagr"]-b["mean_cagr"]),
            "delta_maxdd_pp":100*(o["mean_maxdd"]-b["mean_maxdd"]),
            "delta_sharpe":o["mean_sharpe_rf0"]-b["mean_sharpe_rf0"],
        })
    return pd.DataFrame(rows)


def rolling_log_uplift(dates, base, other, years=(3,4,5), step=21):
    dates=pd.DatetimeIndex(dates)
    delta=(returns(other)-returns(base)).mean(axis=0)
    rows=[]
    for y in years:
        width=int(round(252*y))
        vals=[]
        for end in range(width,len(delta)+1,step):
            start=end-width
            ann=252*float(delta[start:end].mean())
            vals.append((start,end,ann))
        arr=np.array([v[2] for v in vals],float)
        if len(arr)==0:
            continue
        rows.append({
            "years":int(y),
            "windows":int(len(arr)),
            "positive_fraction":float(np.mean(arr>0)),
            "min_annual_log_uplift":float(arr.min()),
            "median_annual_log_uplift":float(np.median(arr)),
            "max_annual_log_uplift":float(arr.max()),
        })
    return pd.DataFrame(rows)


def paired_basket_improvement(base, other):
    b=metrics(base);o=metrics(other)
    # individual basket CAGR / MaxDD
    def per(e):
        lr=returns(e);n=e.shape[1]
        c=np.expm1(lr.sum(axis=1)*252/n)
        peak=np.maximum.accumulate(np.column_stack([np.ones(len(e)),e]),axis=1)[:,1:]
        d=(e/peak-1).min(axis=1)
        return c,d
    bc,bd=per(base);oc,od=per(other)
    return {
        "cagr_improved_fraction":float(np.mean(oc>bc)),
        "maxdd_improved_fraction":float(np.mean(od>bd)),
        "both_improved_fraction":float(np.mean((oc>bc)&(od>bd))),
        "median_cagr_delta_pp":float(100*np.median(oc-bc)),
        "median_maxdd_delta_pp":float(100*np.median(od-bd)),
        "mean_cagr_delta_pp":float(100*(o["mean_cagr"]-b["mean_cagr"])),
        "mean_maxdd_delta_pp":float(100*(o["mean_maxdd"]-b["mean_maxdd"])),
    }


def battery(dates, base, other):
    return {
        "full_base":metrics(base),
        "full_other":metrics(other),
        "bootstrap":{str(b):paired_bootstrap(base,other,block=b,reps=5000) for b in (21,63,126)},
        "annual":annual_uplift(dates,base,other).to_dict("records"),
        "leave_one_year_out":leave_one_year_out(dates,base,other).to_dict("records"),
        "rolling":rolling_log_uplift(dates,base,other).to_dict("records"),
        "basket_pairing":paired_basket_improvement(base,other),
    }
