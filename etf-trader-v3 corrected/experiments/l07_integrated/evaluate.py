#!/usr/bin/env python3
"""ETF Trader V3 corrected L07 — frozen integrated economic diagnostic replay.

This is the FIRST full execution replay after locking the layer reference.
NOT a virgin holdout: 2018-2026 already influenced model/policy design.
Controls:
  V2_LEGACY_RANKER_TOP2: independently archived annual OOS original LEGACY
      ranker predictions, rank percentile, top2 75/25 or top1 if gap>=.12.
      This is the isolated V2 legacy ranker, NOT unverified complete V2 stack.
  V2_CORRECTED_RANKER_TOP2: same Top2 policy with corrected125 pairwise scores.
  V3_TAIL_TOP3_STATIC: independent frozen 45-feature Tail event classifier
      OOS 2018-2026, select 3 in each canonical basket, weights 0.5/0.3/0.2.
  V3_TAIL_TOP3_ABS_SOFT: same selected ETF names; risk calibrated strictly
      historically to P(next21D absolute ETF loss <=-10%); target weights
      normalize(base * exp(-3*p_abs_loss)). Available 2022-Jan..2026-May.

Execution: month-end close -> NEXT market open; buy/sell notional fees
on actual executed turnover with portfolio NAV fixed-point fee accounting,
no future prices in decisions. Mark to adjusted open daily; real drifting
holdings until next decision. Same 500 exact canonical 24-ticker baskets,
same frozen snapshot. Compare 53 complete mature risk-score signal months
2022-Jan..2026-May, terminal 2026-Jul01 next-month first open.
Also static vs legacy over 2018-Feb..2026-Jul01. Sensitivity cost
0, 10, 20, 50 basis points per one-way traded notional.
NO retraining, model/policy selection or production modifications.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
sys.path.insert(0,str(V3/"src"))
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder,load_baskets
from etf_trader_v3.source_only.execution import allocations as original_allocations, replay as original_replay
from etf_trader_v3.source_only.statistics import metrics

BASKET_SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
BASE=[.5,.3,.2]
FULL_START="2018-02-01"
PAIRED_START="2022-02-01"
END="2026-07-01"
FULL_ARMS=("V2_LEGACY_RANKER_TOP2","V2_CORRECTED_RANKER_TOP2","V3_TAIL_TOP3_STATIC")
MATCHED_ARMS=(*FULL_ARMS,"V3_TAIL_TOP3_ABS_SOFT")
COSTS=(0.,.001,.002,.005)


def read_model_scores(file,variant):
    df=pd.read_csv(file,parse_dates=["signal_date"])
    result=df.loc[df.variant.eq(variant),["signal_date","ticker","pred"]].copy()
    assert len(result)==15198,(file,variant,len(result))
    assert not result.duplicated(["signal_date","ticker"]).any()
    assert result.signal_date.nunique()==102 and result.ticker.nunique()==149
    assert np.isfinite(result.pred.to_numpy(float)).all()
    return result


def prepare_data(raw,bs,legacy,tail,risk,frozen):
    registry=json.loads(Path(frozen).read_text())
    assert registry["reference"]["L01"]["source_run"]==39652989033
    assert registry["reference"]["L02"]["source_run"]==39655513813
    assert registry["reference"]["L05"]["weights"]==BASE
    assert registry["reference"]["L07"]["preflight_pass"] is True
    assert registry["data"]["virgin_holdout"] is False
    assert hashlib.sha256(Path(bs).read_bytes()).hexdigest()==BASKET_SHA
    mats,cats,raw_manifest=load_ticker_csv_folder(raw)
    assert len(cats)==149
    mats={k:v.loc[v.index>=pd.Timestamp("2011-01-01")] for k,v in mats.items()}
    baskets=load_baskets(bs,cats)
    assert len(baskets)==500 and all(len(x)==24 for x in baskets)
    v2=read_model_scores(legacy,"LEGACY")
    corrected=read_model_scores(legacy,"CORRECTED")
    v3=read_model_scores(tail,"TAIL_EVENT_LOGIT45")
    for a in (corrected,v3):
        pd.testing.assert_frame_equal(v2.sort_values(["signal_date","ticker"])[["signal_date","ticker"]].reset_index(drop=True),
                                      a.sort_values(["signal_date","ticker"])[["signal_date","ticker"]].reset_index(drop=True))
    riskdf=pd.read_csv(risk,parse_dates=["signal_date"])
    assert {"ticker","signal_date","p_abs_loss"}<=set(riskdf.columns)
    assert len(riskdf)==2281 and riskdf.signal_date.nunique()==53
    assert not riskdf.duplicated(["signal_date","ticker"]).any()
    assert riskdf.signal_date.min()==pd.Timestamp("2022-01-31")
    assert riskdf.signal_date.max()==pd.Timestamp("2026-05-29")
    assert np.isfinite(riskdf.p_abs_loss).all() and riskdf.p_abs_loss.between(0,1).all()
    days=mats["Open"].index
    assert days.is_monotonic_increasing and days.is_unique
    assert pd.Timestamp(END) in days and pd.Timestamp(FULL_START) in days
    return mats,baskets,v2,corrected,v3,riskdf,raw_manifest


def build_top2(scores,baskets,dates,cols,max_signal=None):
    df=scores.copy()
    df["score"]=df.groupby("signal_date").pred.rank(pct=True,method="average")
    if max_signal is not None:df=df.loc[df.signal_date<=pd.Timestamp(max_signal)]
    assert df.groupby("signal_date").ticker.nunique().eq(149).all()
    schedule=original_allocations(df[["signal_date","ticker","score"]],
                                    baskets,dates,cols,threshold=.12,top_weight=.75)
    assert schedule
    return schedule


def build_top3(scores,baskets,dates,cols,risk_scores=None,max_signal=None,min_signal=None):
    source=scores.copy()
    if max_signal is not None: source=source.loc[source.signal_date<=pd.Timestamp(max_signal)]
    if min_signal is not None: source=source.loc[source.signal_date>=pd.Timestamp(min_signal)]
    pivot=source.pivot(index="signal_date",columns="ticker",values="pred").reindex(columns=cols)
    assert np.isfinite(pivot.to_numpy(float)).all()
    names={t:i for i,t in enumerate(cols)}
    members=np.array([[names[t] for t in sorted(b)] for b in baskets],dtype=int)
    assert members.shape==(500,24)
    schedule={}
    tail_choice={}
    probs=(None if risk_scores is None else
           risk_scores.pivot(index="signal_date",columns="ticker",values="p_abs_loss").reindex(columns=cols))
    for date,row in pivot.iterrows():
        i=dates.searchsorted(date,side="right")
        assert i<len(dates) and dates[i]>date
        values=row.to_numpy(float)[members]
        idx=np.argsort(-values,axis=1,kind="stable")[:,:3]
        chosen=np.take_along_axis(members,idx,axis=1)
        w=np.tile(np.asarray(BASE,float),(len(baskets),1))
        if probs is not None:
            assert date in probs.index,("Missing calibrated month",str(date))
            prob=np.take_along_axis(np.broadcast_to(probs.loc[date].to_numpy(float),
                         (len(baskets),len(cols))),chosen,axis=1)
            assert np.isfinite(prob).all(),("Missing prior calibrated probability",str(date))
            assert ((prob>=0)&(prob<=1)).all()
            w=w*np.exp(-3.*prob)
            w=w/w.sum(axis=1,keepdims=True)
        assert np.allclose(w.sum(axis=1),1) and (w>0).all()
        target=np.zeros((len(baskets),len(cols)),float)
        for k in range(3):target[np.arange(len(baskets)),chosen[:,k]]=w[:,k]
        assert np.allclose(target.sum(axis=1),1)
        schedule[int(i)]=target
        tail_choice[pd.Timestamp(date)]=chosen
    return schedule,tail_choice


def replay(schedule,mats,start,end,cost):
    """Independent canonical next-open self-financing executor.

    The in-repo source-only replay for Top2 is used as a numeric oracle to
    certify this implementation before displaying financial comparisons.
    """
    days=mats["Open"].index
    O=mats["Open"].to_numpy(float)
    first=int(days.searchsorted(pd.Timestamp(start)))
    end_idx=int(days.searchsorted(pd.Timestamp(end),side="right")-1)
    assert first>=0 and first<end_idx<len(days)
    B=500;N=O.shape[1]
    units=np.zeros((B,N),float)
    cash=np.ones(B,float)
    lastdesired=np.zeros((B,N),float)
    eq=[];turn=[];idx=[]
    rebalance_days=0
    for i in range(first,end_idx):
        prices=O[i]
        invalid=~np.isfinite(prices)|(prices<=0)
        if ((units>0)&invalid[None,:]).any():raise ValueError(f"Missing held ETF open {days[i]}")
        safe=np.where(invalid,1.,prices)
        effective=np.where(invalid,0.,prices)
        value=cash+units@effective
        if (value<=0).any():raise ValueError(f"Nonpositive portfolio NAV {days[i]}")
        traded_now=np.zeros(B,float)
        if i in schedule:
            desired=schedule[i]
            assert desired.shape==(B,N)
            if (desired[:,invalid]>0).any():raise ValueError(f"Missing chosen open {days[i]}")
            change=np.max(np.abs(desired-lastdesired),axis=1)>1e-12
            after=value.copy()
            for _ in range(10):
                traded=np.abs(desired*after[:,None]-units*effective).sum(axis=1)
                after=np.where(change,value-cost*traded,value)
            if (after<=0).any():raise ValueError("Fees depleted NAV")
            traded_now=np.where(change,traded/value,0)
            units=np.where(change[:,None],desired*after[:,None]/safe,units)
            cash=np.where(change,after*(1-desired.sum(axis=1)),cash)
            lastdesired=desired
            rebalance_days+=1
        nextprices=O[i+1]
        nextbad=~np.isfinite(nextprices)|(nextprices<=0)
        if ((units>0)&nextbad[None,:]).any():raise ValueError(f"Missing valuation ETF open {days[i+1]}")
        equity=cash+units@np.where(nextbad,0.,nextprices)
        if (equity<=0).any():raise ValueError(f"Bankrupt NAV {days[i+1]}")
        eq.append(equity.copy());turn.append(traded_now);idx.append(days[i+1])
    assert rebalance_days>=50
    return pd.DatetimeIndex(idx),np.asarray(eq).T,np.asarray(turn).T,rebalance_days


def annual_aggregate_path(dates,eq):
    agg=np.asarray(eq).mean(axis=0)
    s=pd.Series(agg,index=dates,name="ensemble_equity")
    year_rows=[];prior=1.
    for year,g in s.groupby(s.index.year):
        year_rows.append({"year":int(year),"ensemble_year_return":float(g.iloc[-1]/prior-1),
                          "first_date":str(g.index[0].date()),"last_date":str(g.index[-1].date()),
                          "n_sessions":len(g)})
        prior=float(g.iloc[-1])
    return s,pd.DataFrame(year_rows)


def paired_uncertainty(dates,base,other):
    """Shared calendar-block bootstrap on 500-basket-aggregated log alpha."""
    assert base.shape==other.shape
    n=base.shape[1]
    d=np.log(np.column_stack([np.ones(500),other]))[:,1:]-np.log(np.column_stack([np.ones(500),other]))[:,:-1]
    b=np.log(np.column_stack([np.ones(500),base]))[:,1:]-np.log(np.column_stack([np.ones(500),base]))[:,:-1]
    x=(d-b).mean(axis=0)
    rng=np.random.default_rng(20261021)
    rep=3000;block=21
    starts=rng.integers(0,n,size=(rep,int(np.ceil(n/block))))
    ix=((starts[:,:,None]+np.arange(block))%n).reshape(rep,-1)[:,:n]
    boot=x[ix].mean(axis=1)*252
    ci=np.quantile(boot,[.025,.975])
    return {"paired_mean_annualized_log_return_diff":float(252*x.mean()),
      "ci95_calendar21d_blocks":[float(ci[0]),float(ci[1])],
      "n_days":n,"bootstrap_reps":rep,
      "note":"Exploratory already reused calendar; resample daily blocks after averaging overlapping 500 baskets."}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--legacy",default="runs/v2_legacy")
    p.add_argument("--tail",default="runs/v3_l02")
    p.add_argument("--absolute",default="runs/v3_l06abs")
    p.add_argument("--frozen",default="etf-trader-v3 corrected/registry/V3_INTEGRATION_FREEZE.json")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",default="runs/v3_l07_integrated")
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    mats,baskets,legacy,corrected,tail,risk,raw_manifest=prepare_data(
        args.raw,args.baskets,Path(args.legacy)/"OOS_SCORES.csv",
        Path(args.tail)/"OOS_SCORES.csv",
        Path(args.absolute)/"OOS_SELECTED_ETF_ABSOLUTE_LOSS.csv",
        args.frozen)
    dates=mats["Open"].index;cols=list(mats["Open"].columns)
    assert len(cols)==149
    matched_last=risk.signal_date.max()
    periods={
      "MATCHED53":{"start":PAIRED_START,"last_signal":str(matched_last.date()),"end":END,
                   "arms":MATCHED_ARMS},
      "LONG101":{"start":FULL_START,"last_signal":"2026-06-30","end":END,
                   "arms":FULL_ARMS}
    }
    scored=[];equity_rows=[];year_rows=[];paired=[]
    check={"frozen_GitHub_runs":[39482809691,39515716383,39655513813,
                                39671493979,39672320747,39676155405],
           "preflight_pass_run":39676155405,"original_basket_sha":BASKET_SHA,
           "source_ETFs":149,"baskets":500,"only_past_OOS_inputs":True,
           "V2_is_ranking_reference_only_not_full_strategy":True,
           "all_full_panel_complete":True}
    for pname,period in periods.items():
        s2={}
        for name,frame in [
          ("V2_LEGACY_RANKER_TOP2",legacy),
          ("V2_CORRECTED_RANKER_TOP2",corrected)]:
            s2[name]=build_top2(frame,baskets,dates,cols,period["last_signal"])
        ts,_=build_top3(tail,baskets,dates,cols,max_signal=period["last_signal"])
        s2["V3_TAIL_TOP3_STATIC"]=ts
        if pname=="MATCHED53":
            rs,selected=build_top3(tail,baskets,dates,cols,risk_scores=risk,
                                    max_signal=period["last_signal"],min_signal="2022-01-31")
            s2["V3_TAIL_TOP3_ABS_SOFT"]=rs
            # ALL selected ETF names must match every calendar signal, every basket.
            for key in rs:
                assert key in ts
                assert np.array_equal(ts[key]>0,rs[key]>0)
                assert np.allclose(rs[key].sum(axis=1),1)
            check["absolute_policy_same_ETFs"]=True
            assert len(rs)==53 and len(selected)==53,(len(rs),len(selected))
        assert all(len(s2[arm])>=53 for arm in period["arms"])
        recorded={}
        for cost in COSTS if pname=="MATCHED53" else (.001,):
            for arm in period["arms"]:
                dx,eq,tr,nreb=replay(s2[arm],mats,period["start"],period["end"],cost)
                report=metrics(eq,tr)
                report.update({"period":pname,"variant":arm,"fee_per_traded_dollar":cost,
                     "begin_date":str(dx.min().date()),"end_date":str(dx.max().date()),
                     "number_of_equity_open_sessions":len(dx),"n_signals":nreb,
                     "maxdd_ensemble":report["aggregate_maxdd"]})
                scored.append(report)
                s,years=annual_aggregate_path(dx,eq)
                years["period"]=pname;years["variant"]=arm;years["fee_rate"]=cost
                year_rows.append(years)
                if cost==.001:
                    equity_rows.append(pd.DataFrame({"date":dx,"period":pname,
                        "variant":arm,"mean_basket_equity":s.values,
                        "mean_basket_gross_turnover":tr.mean(axis=0)}))
                    recorded[arm]=(dx,eq,tr)
                print("L07_ECONOMIC",pname,arm,cost,round(report["mean_cagr"],5),
                      round(report["aggregate_cagr"],5),round(report["aggregate_maxdd"],5),flush=True)
        # Exact parity test versus immutable *independent* original V2 self-financing engine.
        data=legacy.copy()
        data["score"]=data.groupby("signal_date").pred.rank(method="average",pct=True)
        data=data.loc[data.signal_date<=pd.Timestamp(period["last_signal"])]
        vdx,ve,vturn=original_replay(data[["signal_date","ticker","score"]],mats,
            baskets,start=period["start"],end=period["end"],cost=.001,
            risk=False,threshold=.12,top_weight=.75)
        cd,eq,tr=recorded["V2_LEGACY_RANKER_TOP2"]
        assert np.array_equal(vdx,cd)
        np.testing.assert_allclose(ve,eq,rtol=0,atol=1e-10,
            err_msg="Independent 2nd executor disagrees with canonical V2 reference")
        np.testing.assert_allclose(vturn,tr,rtol=0,atol=1e-10)
        check[f"{pname}_V2_execution_reference_parity"]="PASS_1e-10"

        for test in period["arms"]:
            if test=="V2_LEGACY_RANKER_TOP2":continue
            dx,eq,_=recorded[test]
            paired.append({"period":pname,"arm":test,"reference":"V2_LEGACY_RANKER_TOP2",
                 **paired_uncertainty(dx,recorded["V2_LEGACY_RANKER_TOP2"][1],eq)})
        if pname=="MATCHED53":
            dx,eq,_=recorded["V3_TAIL_TOP3_ABS_SOFT"]
            paired.append({"period":pname,"arm":"V3_TAIL_TOP3_ABS_SOFT",
                "reference":"V3_TAIL_TOP3_STATIC",
                **paired_uncertainty(dx,recorded["V3_TAIL_TOP3_STATIC"][1],eq)})
    score=pd.DataFrame(scored)
    assert len(score)==(4*4+3*1) and score.variant.nunique()==4
    score.to_csv(out/"SCORECARD_COST_SENSITIVITY.csv",index=False)
    pd.concat(year_rows,ignore_index=True).to_csv(out/"YEARLY_ENSEMBLE_RETURNS.csv",index=False)
    pd.concat(equity_rows,ignore_index=True).to_csv(out/"DAILY_EQUITY_10BPS.csv",index=False)
    pd.DataFrame(paired).to_csv(out/"PAIRED_DAILY_BLOCK_BOOTSTRAP.csv",index=False)
    (out/"VALIDATION.json").write_text(json.dumps(check,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
       "analysis":"L07 fully integrated execution-based historical diagnostic",
       "no_untouched_holdout":True,
       "production_or_model_changed":False,
       "V2_comparison_scope":"LEGACY historical 127-leaf ranker Top2 source-only; NOT full V2 upper layers",
       "V3_ranking":"frozen 45-input elite Tail logistic from 39655513813",
       "V3_selection":"top3 static [0.5,0.3,0.2]",
       "optional_L06_risk":"fixed same tickers, weights exp(-3 * causal p_abs_loss10)",
       "raw_run":39482809691,"original_source_OOS_run":39515716383,
       "frozen_risk_run":39671493979,
       "total_baskets":500,"members_per_basket":24,"n_ETFs":149,
       "execution":"month-end known-at-close score -> next available adjusted open; actual units maintained through month, 1-way fees on traded dollars",
       "fees":[0,0.001,0.002,0.005],
       "long_period":[FULL_START,END],
       "matched_risk_period":[PAIRED_START,END],
       "risk_months":53,
       "means_across_500_baskets_are_correlated_not_independent":True,
       "selection_not_optimized_on_CAGR":True,
       "calendar_repeatedly_examined":True,
       "no_lookahead_or_oracle_scores":True},indent=2))
    s=score[score.fee_per_traded_dollar.eq(.001)].copy()
    (out/"SUMMARY.md").write_text("# ETF Trader V3 L07 integrated cost-aware historical replay\n\n"+
       "**NOT an independent untouched holdout, nor a production-approved V3.**\n"+
       "Original V2 is represented here only by the frozen LEGACY ranker and Top2 policy, NOT complete original V2 upper-layer chain.\n\n"+
       s.round(6).to_markdown(index=False)+"\n\n## Paired calendar-block uncertainty\n\n"+
       pd.DataFrame(paired).round(6).to_markdown(index=False)+"\n")
    print("L07_FULL_REPLAY_COMPLETED",s[["period","variant","mean_cagr","aggregate_cagr",
       "aggregate_maxdd","mean_sharpe_rf0","mean_annualized_gross_turnover"]].to_string(index=False),flush=True)


if __name__=="__main__":
    main()
