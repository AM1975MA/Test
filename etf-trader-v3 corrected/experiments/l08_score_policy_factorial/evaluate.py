#!/usr/bin/env python3
"""ETF Trader V3 — L08 score × selection policy controlled factorial.

Research diagnostic on previously examined years, not independent holdout.
No model refitting. Compare SAME frozen 149 ETF/500 canonical 24-member
baskets and same next-open, self-financing executor for four OOS score channels
(LEGACY ranker, corrected PAIR127, elite TAIL45, fixed RRF10 pair+tail)
crossed with THREE selection policies:
 TOP1 = 100% rank1
 TOP2 = exact V2 historical: 100% top1 if percentile gap >= .12,
        otherwise 75% top1/25% top2
 TOP3 = [50%,30%,20%] frozen L05
This lets us separate changing the model score from changing portfolio
concentration. Reporting economic metrics is purely diagnostic, NOT a
retrospective choice of a winner. Keep every arm, no CAGR-optimized search.
Historical calendar Feb 2018–July 2026 and Feb 2022–July 2026,
10bps one-way fee; 500 baskets dependent, resample common calendar time.
"""
from __future__ import annotations
import argparse,hashlib,json,sys,importlib.util
from pathlib import Path
import numpy as np,pandas as pd

HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
sys.path.insert(0,str(V3/"src"))
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder,load_baskets
from etf_trader_v3.source_only.execution import allocations as original_allocations,replay as original_replay
from etf_trader_v3.source_only.statistics import metrics

L07=V3/"experiments"/"l07_integrated"/"evaluate.py"
spec=importlib.util.spec_from_file_location("frozen_l07_replay",L07)
baseline_module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline_module)
replay=baseline_module.replay

SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
EXPERTS=("LEGACY","PAIR127","TAIL45","RRF10")
POLICIES=("TOP1","TOP2","TOP3")
COST=.001
WINDOWS={
 "LONG101":("2018-02-01","2026-07-01"),
 "MATCHED53":("2022-02-01","2026-07-01")
}

def load_scores(file,variant,rename=None):
    d=pd.read_csv(file,parse_dates=["signal_date"])
    d=d[d.variant==variant][["signal_date","ticker","pred","fwd_ret_21"]].copy()
    assert len(d)==15198 and d.signal_date.nunique()==102
    assert d.ticker.nunique()==149 and not d.duplicated(["signal_date","ticker"]).any()
    assert d.pred.notna().all()
    return d.sort_values(["signal_date","ticker"]).reset_index(drop=True)

def get_original_inputs(raw,baskets_file,legacy_file,pair_file,tail_file):
    assert hashlib.sha256(Path(baskets_file).read_bytes()).hexdigest()==SHA
    mats,cats,raw_manifest=load_ticker_csv_folder(raw)
    assert len(cats)==149
    mats={k:v.loc[v.index>=pd.Timestamp("2011-01-01")] for k,v in mats.items()}
    bs=load_baskets(baskets_file,cats)
    assert len(bs)==500 and all(len(g)==24 for g in bs)
    scored={
       "LEGACY":load_scores(legacy_file,"LEGACY"),
       "PAIR127":load_scores(pair_file,"CORRECTED"),
       "TAIL45":load_scores(tail_file,"TAIL_EVENT_LOGIT45")
    }
    base=scored["LEGACY"]
    for key,frame in scored.items():
        pd.testing.assert_frame_equal(base[["signal_date","ticker"]],
                                     frame[["signal_date","ticker"]])
        np.testing.assert_allclose(base.fwd_ret_21,frame.fwd_ret_21,
                                   rtol=0,atol=1e-14,equal_nan=True)
    pp=scored["PAIR127"].copy()
    pair_rank=pp.groupby("signal_date").pred.rank(ascending=False,method="average").to_numpy(float)
    tail_rank=scored["TAIL45"].groupby("signal_date").pred.rank(ascending=False,method="average").to_numpy(float)
    pp["pred"]=1/(10+pair_rank)+1/(10+tail_rank)
    scored["RRF10"]=pp
    assert len(scored)==4
    return mats,bs,scored,raw_manifest

def make_schedules(frame,baskets,dates,cols,start_date=None):
    # Compute full-universe cross-section percentiles at each month-end.
    frame=frame.copy()
    frame["pct"]=frame.groupby("signal_date").pred.rank(method="average",pct=True)
    if start_date is not None:
        frame=frame[frame.signal_date>=pd.Timestamp(start_date)]
    panel=frame.pivot(index="signal_date",columns="ticker",values="pct").reindex(columns=cols)
    assert panel.shape[1]==149 and np.isfinite(panel.to_numpy(float)).all()
    lookup={t:i for i,t in enumerate(cols)}
    member=np.array([[lookup[t] for t in sorted(group)] for group in baskets],int)
    assert member.shape==(500,24)
    schedules={p:{} for p in POLICIES}
    choices={}
    for signal,row in panel.iterrows():
        pos=dates.searchsorted(signal,side="right")
        assert pos<len(dates) and dates[pos]>signal
        rankvalues=row.to_numpy(float)[member]
        order=np.argsort(-rankvalues,axis=1,kind="stable")[:,:3]
        choices[signal]=np.take_along_axis(member,order,axis=1)
        scores=np.take_along_axis(rankvalues,order,axis=1)
        for policy in POLICIES:
            weights=np.zeros((500,3),float)
            if policy=="TOP1":weights[:,0]=1.
            elif policy=="TOP2":
                weights[:,0]=np.where(scores[:,0]-scores[:,1]>=.12,1.,.75)
                weights[:,1]=1-weights[:,0]
            else:weights[:,:]=[.5,.3,.2]
            W=np.zeros((500,149),float)
            for k in range(3):W[np.arange(500),choices[signal][:,k]]+=weights[:,k]
            assert np.allclose(W.sum(axis=1),1)
            schedules[policy][int(pos)]=W
    # TOP2 must be numerically identical to source V2 implementation.
    original=original_allocations(frame[["signal_date","ticker","pct"]].rename(columns={"pct":"score"}),
                                  baskets,dates,cols,threshold=.12,top_weight=.75)
    assert set(original)==set(schedules["TOP2"])
    for idx in original:
        np.testing.assert_allclose(original[idx],schedules["TOP2"][idx],rtol=0,atol=0)
    return schedules,choices

def frozen_prediction_quality(scored,baskets):
    truth=scored["LEGACY"]
    data=[]
    names=truth.ticker.unique()
    tick_index={t:i for i,t in enumerate(names)}
    member=np.array([[tick_index[t] for t in sorted(x)] for x in baskets],int)
    # Forecasted 21-day label is eval ONLY, never used for allocation.
    assert member.shape==(500,24)
    for expert in EXPERTS:
        frame=scored[expert]
        for dt,group in frame.groupby("signal_date",sort=True):
            if group.fwd_ret_21.isna().any():continue
            g=group.sort_values("ticker")
            # Use per group *ticker* lookup (not one-time unique order).
            lookup={t:i for i,t in enumerate(g.ticker)}
            ix=np.array([[lookup[t] for t in sorted(x)] for x in baskets],int)
            true=g.fwd_ret_21.to_numpy(float)[ix]
            p=g.pred.to_numpy(float)[ix]
            predicted=np.argsort(-p,axis=1,kind="stable")
            actual=np.argsort(-true,axis=1,kind="stable")
            best=actual[:,0]
            best_hit1=(predicted[:,0]==best)
            best_hit2=(predicted[:,:2]==best[:,None]).any(axis=1)
            best_hit3=(predicted[:,:3]==best[:,None]).any(axis=1)
            for policy in POLICIES:
                if policy=="TOP1":weights=np.tile([1.,0.,0.],(500,1))
                elif policy=="TOP2":
                    # SAME percentile gap as implementation.
                    pct=g.pred.rank(method="average",pct=True).to_numpy(float)[ix]
                    ordpct=np.take_along_axis(pct,predicted[:,:3],axis=1)
                    x=np.where(ordpct[:,0]-ordpct[:,1]>=.12,1.,.75)
                    weights=np.stack([x,1-x,np.zeros(500)],axis=1)
                else:weights=np.tile([.5,.3,.2],(500,1))
                chosen=np.take_along_axis(true,predicted[:,:3],axis=1)
                rank=np.argsort(-true,axis=1,kind="stable")
                rel=np.empty_like(true)
                rel[np.arange(500)[:,None],rank]=np.linspace(1,0,24)
                selectedquality=np.take_along_axis(rel,predicted[:,:3],axis=1)
                top_mask=[best_hit1,best_hit2,best_hit3][POLICIES.index(policy)]
                data.append({
                  "signal_date":dt,"year":dt.year,"expert":expert,"policy":policy,
                  "basket_winner_in_top1":float(best_hit1.mean()),
                  "basket_winner_in_top2":float(best_hit2.mean()),
                  "basket_winner_in_top3":float(best_hit3.mean()),
                  "best_in_selected":float(top_mask.mean()),
                  "weighted_future_rank":float((selectedquality*weights).sum(axis=1).mean()),
                  "weighted_regret21":float((true.max(axis=1)-(chosen*weights).sum(axis=1)).mean()),
                  "n_baskets":500
                })
    result=pd.DataFrame(data)
    assert len(result)==101*len(EXPERTS)*len(POLICIES)
    return result

def uncertainty(dates,a,b,rep=1500):
    assert a.shape==b.shape and a.shape[0]==500
    ax=np.diff(np.log(np.column_stack([np.ones(500),a])),axis=1)
    bx=np.diff(np.log(np.column_stack([np.ones(500),b])),axis=1)
    daily=(bx-ax).mean(axis=0)
    n=len(daily);block=21
    rng=np.random.default_rng(20261022)
    starts=rng.integers(0,n,size=(rep,int(np.ceil(n/block))))
    sel=((starts[:,:,None]+np.arange(block))%n).reshape(rep,-1)[:,:n]
    draws=daily[sel].mean(axis=1)*252
    return {"annual_log_alpha":float(daily.mean()*252),
            "ci95_low":float(np.quantile(draws,.025)),
            "ci95_high":float(np.quantile(draws,.975)),
            "n_common_days":n,"bootstrap_calendar_block":block}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",default="etf_trader_raw")
    ap.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    ap.add_argument("--legacy",default="runs/v2_formula_reference/OOS_SCORES.csv")
    ap.add_argument("--pair",default="runs/v3_l01_reference/OOS_SCORES.csv")
    ap.add_argument("--tail",default="runs/v3_l02_reference/OOS_SCORES.csv")
    ap.add_argument("--out",default="runs/v3_l08_factorial")
    arg=ap.parse_args()
    out=Path(arg.out);out.mkdir(parents=True,exist_ok=True)
    mats,baskets,scored,manifest=get_original_inputs(arg.raw,arg.baskets,arg.legacy,arg.pair,arg.tail)
    market_dates=mats["Open"].index;cols=list(mats["Open"].columns)
    assert len(cols)==149
    diagnostics=frozen_prediction_quality(scored,baskets)
    diagnostics.to_csv(out/"MONTHLY_FUNCTIONAL.csv",index=False)
    diagnostics.groupby(["expert","policy"],as_index=False)[
        ["best_in_selected","weighted_future_rank","weighted_regret21"]
    ].mean().to_csv(out/"FUNCTIONAL_SUMMARY.csv",index=False)
    sample_info={}
    scorecards=[];paths=[];yearly=[];comparisons=[]
    for window,(start,end) in WINDOWS.items():
        # MONTH-END Jan 2018 and Jan 2022 signals are the earliest strategy signals.
        schedules={}
        for expert in EXPERTS:
            these,choices=make_schedules(scored[expert],baskets,market_dates)
            for policy,sch in these.items():
                schedules[f"{expert}__{policy}"]=sch
        reference={}
        for name,sch in schedules.items():
            dt,eq,turn,n_reb=replay(sch,mats,start,end,COST)
            assert dt[0]>=pd.Timestamp(start) and dt[-1]<=pd.Timestamp(end)
            s=metrics(eq,turn)
            scorecards.append({"period":window,"arm":name,"fee_bps":10.,
                "n_trading_days":len(dt),"n_rebalance_dates":n_reb,
                "initial_open":start,"last_open":end,**s})
            reference[name]=(dt,eq,turn)
            agg=pd.DataFrame({"date":dt,"period":window,"arm":name,
                               "aggregate_nav":eq.mean(axis=0),
                               "average_turnover":turn.mean(axis=0)})
            paths.append(agg)
            annual_nav=agg.set_index("date").aggregate_nav
            previous=1.
            for yr,g in annual_nav.groupby(annual_nav.index.year):
                yearly.append({"period":window,"arm":name,
                  "year":int(yr),"n_sessions":len(g),
                  "aggregate_nav_year_return":float(g.iloc[-1]/previous-1)})
                previous=float(g.iloc[-1])
            print("FACTORIAL_REPLAY",window,name,
                  round(s["aggregate_cagr"],5),round(s["aggregate_maxdd"],5),flush=True)
        # Independently recheck the *same* legacy Top2 NAV and costs through
        # old production-matched source-only engine at 10 bps.
        x=scored["LEGACY"].copy()
        x["score"]=x.groupby("signal_date").pred.rank(method="average",pct=True)
        t,e,z=original_replay(x[["signal_date","ticker","score"]],mats,baskets,
                              start=start,end=end,cost=COST,risk=False,
                              threshold=.12,top_weight=.75)
        dt,eq,turn=reference["LEGACY__TOP2"]
        assert np.array_equal(t,dt)
        np.testing.assert_allclose(e,eq,rtol=0,atol=1e-10)
        np.testing.assert_allclose(z,turn,rtol=0,atol=1e-10)
        sample_info[f"{window}_legacy_top2_parity"]="PASS_1e-10"
        # Predeclared comparisons identify main-effects of factor changes.
        base="LEGACY__TOP2"
        contrasts=[
          ("PAIR127__TOP2",base,"predictor at V2 policy"),
          ("PAIR127__TOP3","PAIR127__TOP2","allocation only, central ranker"),
          ("TAIL45__TOP2",base,"model only, legacy policy"),
          ("TAIL45__TOP3","TAIL45__TOP2","allocation only, Tail model"),
          ("PAIR127__TOP3","TAIL45__TOP3","ranker vs Tail under Top3"),
          ("RRF10__TOP2","PAIR127__TOP2","RRF vs central under Top2"),
          ("RRF10__TOP3","TAIL45__TOP3","RRF vs Tail under Top3")
        ]
        for trial,ctrl,label in contrasts:
            a=reference[ctrl][1];b=reference[trial][1]
            comparisons.append({"period":window,"arm":trial,"control":ctrl,
                "comparison_label":label,**uncertainty(dt,a,b)})
    pd.DataFrame(scorecards).to_csv(out/"ECONOMIC_FACTORIAL.csv",index=False)
    pd.DataFrame(yearly).to_csv(out/"YEARLY_ENSEMBLE.csv",index=False)
    pd.DataFrame(comparisons).to_csv(out/"PAIRED_BLOCK_BOOTSTRAP.csv",index=False)
    pd.concat(paths,ignore_index=True).to_csv(out/"DAILY_ENSEMBLE_EQUITY.csv",index=False)
    (out/"VALIDATION.json").write_text(json.dumps({
       "status":"PASS","original_ETFs":149,"canonical_baskets":500,
       "basket_membership_sha":SHA,"all_score_streams_annual_OOS":True,
       "legacy_source_only_execution_parity":sample_info,
       "frozen_prediction_models_retrained":False,
       "selection_policies_predeclared":list(POLICIES),
       "fee_one_way_bps":10,"risk_gate_active":False,
       "historical_data_previously_explored":True,
       "production_changed":False},indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
        "experiment":"L08 score × selection policy fixed factorial",
        "source_runs":{
          "raw":39482809691,"legacy":39515716383,
          "central_corrected":39652989033,"tail":39655513813},
        "base": "LEGACY__TOP2","n_models":len(EXPERTS),
        "n_policies":len(POLICIES),"n_factorial_arms":len(EXPERTS)*len(POLICIES),
        "same_calendars":list(WINDOWS),"fees":"10bps traded notional",
        "no_future_in_policy":True,"CAGR_posthoc_reporting_only":True,
        "multiple_comparisons_exploratory":True,"virgin_holdout":False,
        "frozen_V3_main_unchanged":True},indent=2))
    s=pd.DataFrame(scorecards)
    (out/"SUMMARY.md").write_text(
      "# V3 L08 frozen expert vs position-sizing factorial\n\n"
      "This is historical exploratory economic analysis, NOT a new independent OOS holdout or a production change. The V2 reference is **LEGACY ranker + Top2** only.\n\n"
      "## Identical 10bp-cost economic performance\n\n"
      +s[["period","arm","aggregate_cagr","aggregate_maxdd",
          "mean_cagr","mean_sharpe_rf0","mean_annualized_gross_turnover"]].round(6).to_markdown(index=False)
      +"\n\n## Paired 21-trading-day block evidence (calendar first)\n\n"
      +pd.DataFrame(comparisons).round(6).to_markdown(index=False)+"\n")
    print("L08_FINISHED",s[["period","arm","aggregate_cagr","aggregate_maxdd","mean_sharpe_rf0"]].to_string(index=False),flush=True)

if __name__=="__main__":main()
