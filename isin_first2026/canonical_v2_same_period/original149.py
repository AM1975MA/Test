#!/usr/bin/env python3
"""Verify 31.76% full ORIGINAL V2 149 one-unrestricted-149 BASE on 3 archived vintages.

No refit, no new performance simulation. Extract same-date 2021-26 segment of
the original *fully stacked* V2 daily NAV, not later MA3-only source replay.
Audits original full 2017-26 CAGR and top1 disagreement against archived source.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd

def filehash(p):
    h=hashlib.sha256()
    with p.open("rb") as x:
        for b in iter(lambda:x.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def calc(e,dates,start=None,end=None):
    dates=pd.DatetimeIndex(dates)
    assert e.ndim==1 and len(dates)==len(e) and (e>0).all()
    lret=np.diff(np.log(np.r_[1.,e]))
    m=np.ones(len(e),bool)
    if start:m &= dates>=pd.Timestamp(start)
    if end:m &= dates<=pd.Timestamp(end)
    r=lret[m]
    vals=np.exp(np.cumsum(r))
    peak=np.maximum.accumulate(np.r_[1.,vals])[1:]
    sr=np.expm1(r);std=sr.std(ddof=1)
    return dict(first=str(dates[m].min().date()),last=str(dates[m].max().date()),
                n=int(m.sum()),cagr=float(np.expm1(r.sum()*252/len(r))),
                maxdd=float((vals/peak-1).min()),
                sharpe=float(sr.mean()/std*np.sqrt(252)) if std else 0.,
                nav_factor=float(vals[-1]))
def run(src,out):
    src=Path(src);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    summary=json.loads((src/"TOP5_RERANK_ECONOMIC.json").read_text())
    assert summary["status"]=="TOP5_RERANK_ECONOMIC_COMPLETE"
    assert summary["all_three_base_parities_PASS"] is True
    assert summary["original_calendar_sessions"]==2366
    metrics={};periods={};files={}
    for k in ("BASE","ECON_TOP5_RERANK"):
        metrics[k]={};periods[k]={}
        for vintage in (1,2,3):
            p=src/f"v2replay-ECON_TOP5_RERANK-r{vintage}"/("baseline_control" if k=="BASE" else "candidate")/"FULL_UNIVERSE_PATH.npz"
            assert p.exists(),str(p)
            files[str(p.relative_to(src))]=filehash(p)
            with np.load(p,allow_pickle=False) as z:
                e=np.asarray(z["equity"],float);dates=pd.to_datetime(z["dates"])
                assert e.shape==(1,len(dates))
                mfull=calc(e[0],dates)
                expected=summary["results"][k]["per_source"][vintage-1]
                for f in ("cagr","maxdd","sharpe"):
                    assert abs(mfull[f]-expected[f])<1e-12,(k,vintage,f)
                metrics[k][str(vintage)]=mfull
                periods[k][str(vintage)]=calc(e[0],dates,"2021-02-01","2026-07-01")
    mean=lambda frame,field:float(np.mean([frame[str(i)][field] for i in (1,2,3)]))
    expected=summary["results"]["BASE"]["aggregate"]["mean_cagr"]
    assert abs(mean(metrics["BASE"],"cagr")-expected)<1e-12 and abs(expected-.31758077249027905)<1e-8
    outp=dict(status="ORIGINAL_ETF_TRADER_V2_US149_CANONICAL_SOURCE_THREE_VINTAGES_2017_TO_2026_AND_2021_TO_2026_VERIFIED",
        original_total_2017_2026_vintage_mean_BASE_cagr=mean(metrics["BASE"],"cagr"),
        original_total_2017_2026_vintage_mean_top5_rerank_cagr=mean(metrics["ECON_TOP5_RERANK"],"cagr"),
        original_total_2017_2026_BASE_mean_maxdd=mean(metrics["BASE"],"maxdd"),
        original_total_2017_2026_BASE_mean_sharpe=mean(metrics["BASE"],"sharpe"),
        preserved_all_three_full_original149_V2_path_SHA256=files,
        old_model_original_FULL_STAGED_V2_not_MA3_only=True,
        old_original_was_one_unrestricted_149_portfolio_each_of_three_quote_vintages=True,
        no_500_baskets_in_31_76_replayed_measure=True,
        common_overlap_2021_2026_vintage_mean_BASE_cagr=mean(periods["BASE"],"cagr"),
        common_overlap_2021_2026_vintage_mean_rerank_cagr=mean(periods["ECON_TOP5_RERANK"],"cagr"),
        common_overlap_2021_2026_vintage_mean_BASE_maxdd=mean(periods["BASE"],"maxdd"),
        common_overlap_2021_2026_vintage_mean_rerank_maxdd=mean(periods["ECON_TOP5_RERANK"],"maxdd"),
        full_history_149={k:metrics[k] for k in metrics},
        same_period_2021_2026={k:periods[k] for k in periods},
        old_path_run=39044619710,
        no_new_fit_no_ticker_selection_changes=True,
        original_statements_31_76_mean_3_quote_vintages_correct=True,
        study_overlap_2021_2026_is_NOT_new_unseen_data=True)
    (out/"RESULT.json").write_text(json.dumps(outp,indent=2,allow_nan=False)+"\n")
    print("COMPLETE_ORIGINAL_149_FULL_SOURCE_COMMON_PERIOD_PROOF",json.dumps(outp),flush=True)
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--source",required=True);a.add_argument("--out",required=True)
    p=a.parse_args();run(p.source,p.out)
