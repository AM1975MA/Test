#!/usr/bin/env python3
"""Genuinely refit original vendored Titanium TIT_R on 48 Europe-only ETF source rows.

Frozen original models/features unchanged. Dates 2021+ ONLY because 48-fund
full-window strict observations appear only after 2016/2017; 2017–2020
chronologically trained samples remain used. Does not reuse USA149 TIT scores.
"""
from __future__ import annotations
import argparse,os,json,inspect,numpy as np
from pathlib import Path
import pandas as pd
from etf_trader.source_only import kernel as k
from etf_trader.source_only import features as feature_module
from etf_trader.source_only.models import fit_predict,variants
from etf_trader.source_only.raw_io import load_ticker_csv_folder
def run(data,out,usrefs):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    os.environ["ETF_TRADER_XGB_WORKERS"]="2"
    os.environ["ETF_TRADER_XGB_THREADS_PER_WORKER"]="1"
    mats,cats,manifest=load_ticker_csv_folder(data)
    names=list(mats["Close"].columns)
    k.ALL_TICKERS=sorted(names)
    k.TICKER_CATEGORY=cats
    k.CATEGORY_TICKERS={c:sorted([t for t in names if cats[t]==c]) for c in sorted(set(cats.values()))}
    dates=k.month_end_dates(mats["Close"].index)
    if len(dates) and dates[-1]==mats["Close"].index[-1]:
        dates=dates[:-1]
    print("EU48_TIT_FEATURE_BUILD",len(dates),len(names),flush=True)
    # Freeze 48 investable panels. Restore original SPY as EXTRA explanatory
    # beta/risk series, never a 49th candidate, using last strictly prior
    # American close available before each European trading session.
    us=pd.read_csv(usrefs,parse_dates=["date"]).set_index("date")
    assert us.index.equals(mats["Close"].index)
    for col in ("SPY","HYG","IEF","BIL","SHV"):
        assert (us[col]>0).all()
        assert (us.index-pd.DatetimeIndex(us[col+"_US_MARKET_DATE"])).days.min()>0
    rawsrc=inspect.getsource(k.build_features)
    pattern="mkt=ret['SPY'] if 'SPY' in ret else ret.median(axis=1)"
    assert rawsrc.count(pattern)==1
    k.US_SPY_RET=us["SPY"].pct_change(fill_method=None)
    em={}
    exec(compile(rawsrc.replace(pattern,
            'mkt=US_SPY_RET.reindex(ret.index)'),
            "<kernel_build_features_original_US_SPY_beta>", "exec"),k.__dict__,em)
    _,compact,tail,_=em["build_features"](mats)
    compact=compact[compact.signal_date.isin(dates)].copy()
    tail=tail[tail.signal_date.isin(dates)].copy()
    compact=k.add_labels(compact,mats["Open"],dates)
    tail=k.add_labels(tail,mats["Open"],dates)
    tail_no_labels=tail.drop(columns=[c for c in tail if
        c.startswith(("fwd_","target_","exit_")) or c in ["entry_date","y_tailmix"]])
    macro,mfeatures=k.build_macro_panel(tail_no_labels,tail)
    # Preserve extra feature's original US SPY log beta. Do not inject US
    # SPY into the 48 candidate cross-section and never use same-day US close.
    feature_module.US_SPY_LOGRET=np.log(us["SPY"]).diff()
    original_code=inspect.getsource(feature_module.build)
    needle="m=lr['SPY']"
    assert original_code.count(needle)==1
    namespace={}
    exec(compile(original_code.replace(needle,
       "m=US_SPY_LOGRET.reindex(lr.index)"),
       "<features_build_original_prior_US_SPY>", "exec"),
       feature_module.__dict__,namespace)
    extra=namespace["build"](mats,cats,dates)
    print("EU48_TIT_START_REAL_FITS",len(compact),len(tail),flush=True)
    pred=fit_predict(k,compact,tail,macro,mfeatures,extra,
                     out/"annual_models",years=range(2021,2027))
    assert pred.signal_date.min()>=pd.Timestamp("2021-01-01")
    pred=pred[(pred.signal_date>="2021-01-01")&
              (pred.signal_date<="2026-06-30")].copy()
    baseline=variants(pred)["baseline"].rename(columns={"score":"TIT_R"})
    cal=pred[["signal_date","ticker","entry_date","exit_date"]].drop_duplicates(
        ["signal_date","ticker"])
    panel=baseline.merge(cal,on=["signal_date","ticker"],validate="one_to_one")
    panel=panel[["signal_date","entry_date","exit_date","ticker","TIT_R"]].sort_values(
        ["signal_date","ticker"])
    assert panel.ticker.nunique()==48
    assert panel.signal_date.nunique()>=60
    panel.to_csv(out/"TIT_R_SOURCE_ONLY.csv",index=False)
    audits=list((out/"annual_models").glob("fit_audit_*.json"))
    assert len(audits)==6,[(x.name) for x in audits]
    detail=[json.loads(x.read_text()) for x in sorted(audits)]
    (out/"MANIFEST.json").write_text(json.dumps(dict(
       n_tickers=len(names),n_signal_dates=panel.signal_date.nunique(),
       rows=len(panel),model_fits=detail,no_US149_score_consumed=True,
       actual_models_retrained=True,input_source=manifest,
       dates_2021_onward_due_48_launch_calendar=True,
       original_US_SPY_beta_feature_restored=True,
       source_reference_currency_USD=True,
       strict_prior_US_close_causal=True,
       ref_US_market_count_never_tradable=True),indent=2,default=str)+"\n")
    print("EU48_TIT_RETRAIN_COMPLETE",len(panel),flush=True)
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--data",required=True);a.add_argument("--out",required=True);a.add_argument("--usrefs",required=True)
    p=a.parse_args();run(p.data,p.out,p.usrefs)
