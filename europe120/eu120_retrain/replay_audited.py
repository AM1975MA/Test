#!/usr/bin/env python3
"""Recompute EU120 execution on common, observed market sessions.

Consumes only the predictions generated in this experiment's source-only fit.
The router is rebuilt from the audited Annual/Monthly shadow paths.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import run_eu120_retrain as m
import common_day_v6 as v6c
from bocpd_router import route_trace
from etf_trader.ma3 import ddfirst, producer
from etf_trader.source_only.raw_io import load_ticker_csv_folder


def common_calendar(raw_open: pd.DataFrame, signals: pd.DatetimeIndex) -> pd.DataFrame:
    idx = raw_open.index
    all_open = raw_open.notna().all(axis=1).to_numpy()
    rows = []
    for sd in signals:
        pos = int(idx.searchsorted(sd, side="right"))
        later = np.flatnonzero(all_open[pos:])
        if not len(later):
            raise RuntimeError(f"no common session after {sd}")
        rows.append({"signal_date":sd, "entry_date":idx[pos + later[0]]})
    cal = pd.DataFrame(rows)
    cal["exit_date"] = cal.entry_date.shift(-1)
    return cal.dropna(subset=["exit_date"]).reset_index(drop=True)


def replay(score, pm, cal, candidates, refs, tickers):
    cols = tickers + [t for t in m.REF_TICKERS if t not in tickers]
    raw_open = pd.concat([candidates["Open"][tickers], refs["Open"][cols[len(tickers):]]],axis=1).sort_index().reindex(columns=cols)
    raw_open = raw_open.reindex(raw_open.index.union(refs["Open"].index)).sort_index()
    tradeable = raw_open.notna().all(axis=1)
    mats = {}
    for f in ("Open","Low","Close"):
        raw = pd.concat([candidates[f][tickers],refs[f][cols[len(tickers):]]],axis=1).sort_index().reindex(columns=cols)
        mats[f] = raw.reindex(raw_open.index).ffill()
    start,end = pd.Timestamp(cal.entry_date.min()),pd.Timestamp(cal.exit_date.max())
    Odf = mats["Open"].loc[:end]
    Ldf = mats["Low"].reindex(Odf.index)
    Cdf = mats["Close"].reindex(Odf.index)
    st,en = Odf.index.get_loc(start),Odf.index.get_loc(end)
    ds = Odf.index[st:en+1]
    available = tradeable.reindex(ds).to_numpy(bool)
    if not available[0] or not available[-1]:
        raise RuntimeError("evaluation endpoint has no common open")
    if not set(cal.entry_date).issubset(set(ds[available])):
        raise RuntimeError("an intended rebalance has an unavailable open")
    full_gross = np.asarray(ddfirst.sync_c95_m75_gross(Cdf),float)
    gross = full_gross[st:en+1]
    g = m.risk_transform(gross)
    ex = ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
    O,L,C,PC,gap,ud1,uneg,UH,SA = [ex[x][st:en+1] for x in ("O","L","C","PC","gap","ud1","uneg","UH","SA")]
    bm = np.arange(len(tickers),dtype=np.int32)[None,:]
    bok = np.ones_like(bm,dtype=bool)
    base = producer.allocations_from_score(score,cal,ds,bm,bok,continuous=True)
    agree = m.daily_state(score,pm,cal,ds,bm,bok)
    w = m.conf_weights(base,g,agree)
    prefix = np.full((base.d1.shape[0],st),-1,dtype=base.d1.dtype)
    full_d1=np.concatenate([prefix,base.d1],axis=1)
    full_d2=np.concatenate([prefix,base.d2],axis=1)
    full_weight=np.concatenate([np.zeros((base.weight1.shape[0],st)),base.weight1],axis=1)
    state=v6c.build_v6_state(Cdf,full_d1,full_d2,full_weight,full_gross)
    alt=state.alt_idx[:,st:en+1].copy()
    alt[alt>=len(tickers)]=-1
    ti={t:i for i,t in enumerate(cols)}
    E,T,_,_=v6c.simulate_with_alt.py_func(base.d1,base.d2,w,O,L,C,PC,gap,ud1,uneg,UH,SA,ti["BIL"],ti["SHV"],g,alt,True,available,.001)
    out=m.metrics(E[0])
    out["annualized_turnover"]=float(T.mean()*252)
    return out,E[0],T[0],ds


def main():
    out=m.OUT
    u=pd.read_csv(m.ROOT/"UNIVERSE_120.csv")
    tickers=u.ticker.astype(str).tolist()
    cand,_,_=load_ticker_csv_folder(m.RAW_TARGET)
    refs,_,_=load_ticker_csv_folder(m.RAW_REF)
    a=pd.read_csv(out/"ANNUAL_PREDICTIONS_120.csv",parse_dates=["signal_date"])
    z=pd.read_csv(out/"MONTHLY_PREDICTIONS_120.csv",parse_dates=["signal_date"])
    signals=pd.DatetimeIndex(sorted(set(a.signal_date)&set(z.signal_date)))
    ro=pd.concat([cand["Open"][tickers],refs["Open"][m.REF_TICKERS]],axis=1).sort_index()
    cal=common_calendar(ro,signals)
    a=a[a.signal_date.isin(cal.signal_date)]
    z=z[z.signal_date.isin(cal.signal_date)]
    # Restore two causal pre-2017 tail lags from the same frozen EU120 panel.
    panel=pd.read_pickle(m.MA3_TRAIN/"RAW_FEATURE_PANEL.pkl")
    panel["signal_date"]=pd.to_datetime(panel.signal_date)
    panel["exit_date_63"]=pd.to_datetime(panel.exit_date_63)
    pre=[]
    for date in ("2016-11-30","2016-12-30"):
        sd=pd.Timestamp(date)
        pred=m.fit_ma3_one(panel,panel,sd,pd.DatetimeIndex([sd]),"AUDIT"+sd.strftime("%Y%m%d"),m.MODELS/"monthly")
        pre.append(pred[["signal_date","ticker","TAIL_EXTRA"]])
    pre=pd.concat(pre,ignore_index=True)
    sa,pma=m.score_from_panel(a,cal,tickers,False)
    sm,pmm=m.score_from_panel(z,cal,tickers,True,pre)
    results={}; paths={}
    for name,s,p in (("Annual",sa,pma),("Monthly",sm,pmm)):
        metrics,E,T,ds=replay(s,p,cal,cand,refs,tickers)
        results[name]=metrics;paths[name]=E
        print(name,metrics,flush=True)
    shadow=[]
    for row in cal.itertuples(index=False):
        i=int(ds.get_indexer([row.entry_date])[0]);j=int(ds.get_indexer([row.exit_date])[0])
        if i<0 or j<=i:raise RuntimeError("shadow date mismatch")
        # The simulator stores E[k] at open k+1. The interval ending at the
        # open j matures at E[j-1], strictly before the router consumes it.
        annual=paths["Annual"][j-1]/(paths["Annual"][i-1] if i else 1.)-1
        monthly=paths["Monthly"][j-1]/(paths["Monthly"][i-1] if i else 1.)-1
        ga,gm=np.log1p(annual),np.log1p(monthly)
        skill=float(np.clip((gm-ga)/(abs(gm)+abs(ga)+1e-12),-1,1))
        shadow.append({"interval_signal_date":row.signal_date,"outcome_end":row.exit_date,
                       "annual_return":annual,"monthly_return":monthly,"skill":skill})
    shadow=pd.DataFrame(shadow)
    route=route_trace(cal.signal_date,shadow)
    route["w_monthly"]=route.p_monthly.astype(float)
    route["w_annual"]=1-route.w_monthly
    if not all(pd.isna(v) or pd.Timestamp(v)<pd.Timestamp(d) for v,d in zip(route.last_matured_outcome_end,route.signal_date)):
        raise RuntimeError("unmatured shadow entered router")
    wm=route.w_monthly.to_numpy(float)[:,None];wa=1-wm
    for name,s,p in (("P42_50_50",.5*sa+.5*sm,{k:.5*pma[k]+.5*pmm[k] for k in pma}),
                     ("P45",wa*sa+wm*sm,{k:wa*pma[k]+wm*pmm[k] for k in pma})):
        metrics,E,T,ds=replay(s,p,cal,cand,refs,tickers)
        results[name]=metrics;paths[name]=E
        print(name,metrics,flush=True)
    route.to_csv(out/"AUDITED_ROUTER_TRACE.csv",index=False)
    shadow.to_csv(out/"AUDITED_SHADOW_SKILL.csv",index=False)
    rows=[]
    for year in range(2017,2027):
        mask=(ds.year==year)
        if not mask.any():continue
        rec={"year":year,"sessions":int(mask.sum())}
        for name,E in paths.items():
            rr=np.diff(np.log(np.r_[1.,E]))
            rec[name+"_return"]=float(np.expm1(rr[mask].sum()))
        rows.append(rec)
    pd.DataFrame(rows).to_csv(out/"AUDITED_ANNUAL_COMPARISON.csv",index=False)
    audit={"status":"EU120_CROSS_MARKET_COMMON_SESSION_REPLAY","source":"EU120 walk-forward trained predictions",
           "period":[str(ds.min().date()),str(ds.max().date())],
           "signal_count":len(cal),"non_common_sessions":int((~ro.notna().all(axis=1).reindex(ds)).sum()),
           "shadow_ingest_strictly_prior":True,
           "calendar_policy":"next common observed open after signal; rebalance and stops only on common sessions",
           "risk_warmup":"full pre-evaluation close history",
           "results":results}
    (out/"AUDITED_RESULT.json").write_text(json.dumps(audit,indent=2)+"\n")
    print("AUDITED_RESULT",json.dumps(audit,indent=2),flush=True)


if __name__=="__main__":
    main()
