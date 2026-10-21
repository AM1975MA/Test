#!/usr/bin/env python3
"""V3 L09 economic consequence ONLY AFTER target-fitting freeze.

Compare frozen score origins on exact same 149 ETF, 500 original 24-name
baskets, market-next-open self-financing execution and same transaction fees:
LEGACY original ranker, CORRECTED pair127, two predeclared 21D target
regressions. FIXED Top2 legacy (75/25 except gap >=.12 => Top1) and fixed
Top3 (50/30/20) in a 4×2 controlled factorial. Compare common 101 OOS
mature months plus same 2022–26 period. No model/weight tuning based on
CAGR, no other layers. Mark research historical time as NOT VIRGIN.
"""
from __future__ import annotations
import argparse,importlib.util,json,hashlib,sys
from pathlib import Path
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
sys.path.insert(0,str(V3/"src"))
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder,load_baskets
from etf_trader_v3.source_only.execution import replay as original_replay
from etf_trader_v3.source_only.statistics import metrics

spec=importlib.util.spec_from_file_location("v3_factorial",V3/"experiments"/"l08_score_policy_factorial"/"evaluate.py")
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
replay=f.replay
make_schedules=f.make_schedules
uncertainty=f.uncertainty

SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
MODELS=("LEGACY","CORRECTED_PAIR127","L09_EXCESS21","L09_DOWNSIDE21")
POLICIES=("TOP2","TOP3")
WINDOWS={"LONG101":("2018-02-01","2026-07-01"),
         "MATCHED53":("2022-02-01","2026-07-01")}

def read_kind(file,kind):
    d=pd.read_csv(file,parse_dates=["signal_date"])
    d=d[d.variant.eq(kind)][["signal_date","ticker","pred","fwd_ret_21"]].copy()
    assert len(d)==15198 and d.signal_date.nunique()==102 and d.ticker.nunique()==149,(kind,len(d))
    assert not d.duplicated(["signal_date","ticker"]).any()
    assert np.isfinite(d.pred).all()
    return d.sort_values(["signal_date","ticker"]).reset_index(drop=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--old",default="runs/v2_formula_reference/OOS_SCORES.csv")
    p.add_argument("--new",default="runs/v3_l09_complete/OOS_SCORES.csv")
    p.add_argument("--out",default="runs/v3_l09_economic")
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()==SHA
    mats,cats,_=load_ticker_csv_folder(a.raw)
    assert len(cats)==149
    mats={k:v.loc[v.index>=pd.Timestamp("2011-01-01")] for k,v in mats.items()}
    bs=load_baskets(a.baskets,cats)
    assert len(bs)==500 and all(len(x)==24 for x in bs)
    scored={
        "LEGACY":read_kind(a.old,"LEGACY"),
        "CORRECTED_PAIR127":read_kind(a.old,"CORRECTED"),
        "L09_EXCESS21":read_kind(a.new,"L09_EXCESS21"),
        "L09_DOWNSIDE21":read_kind(a.new,"L09_DOWNSIDE21")
    }
    base=scored["LEGACY"]
    for k,d in scored.items():
        pd.testing.assert_frame_equal(base[["signal_date","ticker"]],
                                     d[["signal_date","ticker"]])
        np.testing.assert_allclose(base.fwd_ret_21,d.fwd_ret_21,atol=1e-14,rtol=0,equal_nan=True)
    dates=mats["Open"].index
    cols=list(mats["Open"].columns)
    assert len(cols)==149
    schedule={}
    for name,d in scored.items():
        schedules,_=make_schedules(d,bs,dates,cols)
        for policy in POLICIES:
            schedule[f"{name}__{policy}"]=schedules[policy]
    rows=[];curves=[];years=[];comp=[]
    for period,(start,end) in WINDOWS.items():
        outpaths={}
        for key,sch in schedule.items():
            dx,eq,turn,nreb=replay(sch,mats,start,end,.001)
            stats=metrics(eq,turn)
            rows.append({"period":period,"variant":key,"fee_bps":10,
                 "n_rebalance_days":nreb,"n_trading_days":len(dx),**stats})
            curves.append(pd.DataFrame({"date":dx,"period":period,"variant":key,
                  "aggregate_equity":eq.mean(axis=0),"aggregate_turnover":turn.mean(axis=0)}))
            outpaths[key]=(dx,eq,turn)
            e=pd.Series(eq.mean(axis=0),index=dx)
            prior=1.
            for year,g in e.groupby(e.index.year):
                years.append({"year":int(year),"period":period,"variant":key,
                  "aggregate_year_return":float(g.iloc[-1]/prior-1),
                  "n_trading_days":len(g)})
                prior=float(g.iloc[-1])
            print("L09_NEXT_OPEN",period,key,round(stats["aggregate_cagr"],6),
                  round(stats["aggregate_maxdd"],6),flush=True)
        # Exact parity with already audited source-only original engine.
        orig=scored["LEGACY"].copy()
        orig["score"]=orig.groupby("signal_date").pred.rank(pct=True,method="average")
        day,eq,turn=original_replay(orig[["signal_date","ticker","score"]],mats,bs,
            start=start,end=end,cost=.001,risk=False,threshold=.12,top_weight=.75)
        d,e,t=outpaths["LEGACY__TOP2"]
        assert np.array_equal(day,d)
        np.testing.assert_allclose(eq,e,atol=1e-10,rtol=0)
        np.testing.assert_allclose(turn,t,atol=1e-10,rtol=0)
        contrasts=[
          ("CORRECTED_PAIR127__TOP2","LEGACY__TOP2","math corrections"),
          ("L09_EXCESS21__TOP2","CORRECTED_PAIR127__TOP2","regression return utility"),
          ("L09_DOWNSIDE21__TOP2","L09_EXCESS21__TOP2","only downside penalty"),
          ("L09_DOWNSIDE21__TOP2","CORRECTED_PAIR127__TOP2","asymmetric utility against prior pair127"),
          ("L09_EXCESS21__TOP3","CORRECTED_PAIR127__TOP3","regression return utility same Top3"),
          ("L09_DOWNSIDE21__TOP3","L09_EXCESS21__TOP3","only downside penalty same Top3"),
          ("L09_DOWNSIDE21__TOP3","CORRECTED_PAIR127__TOP3","asymmetric utility against prior pair127 Top3")]
        for trial,control,reason in contrasts:
            comp.append({"period":period,"trial":trial,"control":control,
                "one_change":reason,**uncertainty(outpaths[trial][0],
                    outpaths[control][1],outpaths[trial][1])})
    full=pd.DataFrame(rows)
    full.to_csv(out/"ECONOMIC_SCORECARD.csv",index=False)
    pd.concat(curves,ignore_index=True).to_csv(out/"DAILY_EQUITY.csv",index=False)
    pd.DataFrame(years).to_csv(out/"ANNUAL_EQUITY.csv",index=False)
    pd.DataFrame(comp).to_csv(out/"PAIRED_BLOCK_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps({
       "layer":"L09 21D utility-target integrated consequence only",
       "original_raw":39482809691,"original_OOS_legacy_corrected":39515716383,
       "new_rankers_source":"L09 21D utility completed source artifact",
       "ETF_universe":149,"baskets":500,"basket_size":24,
       "same_original_score_target_observations":True,
       "execution_source_v2_parity":"PASS 1e-10 for both windows",
       "fee_one_way_bps":10,
       "models":list(MODELS),"policies":list(POLICIES),"windows":WINDOWS,
       "old_production_or_Tail_changed":False,"CAGR_used_for_training_or_model_selection":False,
       "prior_historical_calendar_reused_not_virgin":True},indent=2))
    (out/"SUMMARY.md").write_text("# L09 true economic consequences of 21D utility target\n\n"+
       "**Exploratory reused 2018–2026 history, NOT a virgin OOS model validation.**\n\n"+
       full[["period","variant","aggregate_cagr","aggregate_maxdd",
             "mean_cagr","mean_sharpe_rf0","mean_annualized_gross_turnover"]]
       .round(6).to_markdown(index=False)+"\n\n"+
       "## Paired 21-trading-day block uncertainty\n\n"+
       pd.DataFrame(comp).round(6).to_markdown(index=False))
    print("L09_ECONOMIC_FINISH",full.to_string(index=False),flush=True)

if __name__=="__main__":main()
