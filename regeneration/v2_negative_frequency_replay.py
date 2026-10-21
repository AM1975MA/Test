#!/usr/bin/env python3
"""Evaluate frozen raw-XGB OOS model migration as an isolated economic replay.

No Tail, Macro, risk, strategy production promotion. Common 500 fixed baskets,
next-day open fills and 10 bps traded notional. Uses *only* out-of-sample
monthly predictions from fully refitted LEGACY/CORRECTED_PLUS_FREQ/CORRECTED ensembles.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"regeneration"/"campaign"))
from etf_trader.source_only.raw_io import load_ticker_csv_folder,load_baskets
from etf_trader.source_only.execution import replay
from etf_trader.source_only.statistics import metrics,paired_bootstrap
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--scores",default="runs/v2_negative_frequency_complete/OOS_SCORES.csv")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",default="runs/v2_negative_frequency_economics")
    a=p.parse_args()
    mats,cats,_=load_ticker_csv_folder(a.raw)
    assert len(cats)==149
    mats={k:v.loc[v.index>=pd.Timestamp("2011-01-01")] for k,v in mats.items()}
    baskets=load_baskets(a.baskets,cats)
    assert len(baskets)==500
    allscores=pd.read_csv(a.scores,parse_dates=["signal_date"])
    variants=["LEGACY","CORRECTED","CORRECTED_PLUS_FREQ"]
    o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
    reports=[];by_variant={}
    coverage=None
    for variant in variants:
        x=allscores[allscores.variant==variant][["signal_date","ticker","pred"]].copy()
        assert not x[["signal_date","ticker"]].duplicated().any(),variant
        if coverage is None:
            coverage=x[["signal_date","ticker"]].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        else:
            assert x[["signal_date","ticker"]].sort_values(["signal_date","ticker"]).reset_index(drop=True).equals(coverage)
        # The execution policy expects a month-wise cross-sectional percentile
        # rank, not the uncalibrated raw score (which differs by model).
        x["score"]=x.groupby("signal_date").pred.rank(method="average",pct=True)
        dates,eq,turn=replay(x[["signal_date","ticker","score"]],mats,baskets,
            start="2018-02-01",end="2026-07-01",
            cost=.001,risk=False,threshold=.12,top_weight=.75)
        assert eq.shape[0]==500 and eq.shape[1]>1500
        m=metrics(eq,turn)
        reports.append({"variant":variant,**m,"first_date":str(dates[0].date()),"last_date":str(dates[-1].date())})
        by_variant[variant]=(dates,eq)
        print("REPLAY_DONE",variant,m["mean_cagr"],m["mean_maxdd"],flush=True)
    pd.DataFrame(reports).to_csv(o/"STRATEGY_SCORECARD.csv",index=False)
    changes=[]
    for base_name,target_name in [("LEGACY","CORRECTED"),("LEGACY","CORRECTED_PLUS_FREQ"),
                                  ("CORRECTED","CORRECTED_PLUS_FREQ")]:
        base_d,base=by_variant[base_name]
        dt,eq=by_variant[target_name]
        assert np.array_equal(base_d,dt)
        stats=paired_bootstrap(base,eq,block=21,reps=4000,seed=20261021)
        changes.append({"variant":target_name,"reference":base_name,**stats})
    (o/"PAIRED_BOOTSTRAP_ECONOMICS.json").write_text(json.dumps(changes,indent=2))
    (o/"MANIFEST.json").write_text(json.dumps({"note":"Exploratory, no virgin OOS calendar or production promotion",
        "raw_run":39482809691,"ranker":"127-leaf annual refits, 360 trees 3 seeds",
        "risk":False,"tail":False,"macro":False,
        "signal_to_trade":"signal month-end close -> next available adjusted open",
        "one_way_fee":0.001,"panier_count":500,"weight_policy":"top2 75/25, top1 100 if percentile gap>=0.12",
        "comparison":"corrected+negative-frequency vs corrected 125 and exact legacy on matched dates and baskets"},indent=2))
    print(pd.DataFrame(reports).to_string(index=False))
if __name__=="__main__":main()
