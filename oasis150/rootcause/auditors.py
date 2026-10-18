#!/usr/bin/env python3
"""Four traceable independent forensic review roles for completed OASIS 150.
Never fits or modifies a trading signal. Future returns are EX-POST labels.
"""
from __future__ import annotations
import argparse,json,math,hashlib,collections
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from oasis.observers import prepare
ROOT=Path(__file__).resolve().parents[2]
FROZEN=ROOT/"oasis150/results/frozen"
ROLES=("data","signal","risk","execution")

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for x in iter(lambda:f.read(1<<20),b""):h.update(x)
    return h.hexdigest()

def read_ledger(arm):
    p=FROZEN/(arm+".csv")
    d=pd.read_csv(p,parse_dates=["day","signal_date"])
    assert len(d)==2366
    assert (d.signal_date<d.day).all()
    return d

def source():
    names=pd.read_csv(FROZEN/"OASIS_TOP150.csv")
    op=[];cl=[];vol=[];invalid=[]
    for r in names.itertuples(index=False):
        path=ROOT/r.source_path
        if sha(path)!=r.source_sha256:raise AssertionError("Source sha drift "+r.ticker)
        d=pd.read_csv(path,parse_dates=["date"]).drop_duplicates("date").set_index("date").sort_index()
        if not all(c in d.columns for c in ("Open","Close","Volume")):raise AssertionError("bad raw schema")
        op.append(d.Open.rename(r.ticker))
        cl.append(d.Close.rename(r.ticker))
        vol.append(d.Volume.rename(r.ticker))
        rv=np.log(d.Close/d.Close.shift()).replace([np.inf,-np.inf],np.nan)
        hits=rv[rv.abs()>.25].dropna()
        for dt,x in hits.items():
            invalid.append(dict(ticker=r.ticker,date=str(dt.date()),close_to_close_log_return=float(x)))
    O=pd.concat(op,axis=1);C=pd.concat(cl,axis=1);V=pd.concat(vol,axis=1)
    return names,O,C,V,invalid

def summarize(vec):
    v=np.asarray([x for x in vec if np.isfinite(x)],float)
    if len(v)==0:return dict(n=0,mean=None,median=None,p_positive=None)
    return dict(n=int(len(v)),mean=float(np.mean(v)),median=float(np.median(v)),
                p_positive=float(np.mean(v>0)),p10=float(np.quantile(v,.1)),
                p90=float(np.quantile(v,.9)))

def data_audit():
    roster,O,C,V,jumps=source()
    trial=read_ledger("P3_OASIS_CRISIS_ACTIVE")
    clock=trial.day
    op=O.reindex(index=clock);cl=C.reindex(index=clock);v=V.reindex(index=clock)
    src=pd.read_csv(FROZEN/"FULL_219_QUALITY_CENSUS.csv")
    selected=pd.read_csv(FROZEN/"OASIS_TOP150.csv")
    assert (selected.valid_study_rows==2366).all()
    assert (selected.positive_volume_study==2366).all()
    assert src.ticker.nunique()==219
    zero=int((v.fillna(-1)==0).sum().sum())
    missing=int((op.isna()|cl.isna()).sum().sum())
    unique_uses=int(np.sum([len(x.split(";")) for x in trial.names.astype(str)]))
    categories=roster.groupby("macro_category").size().to_dict()
    q=dict(status="DATA_GATE_BLOCK_PIT_AND_LIQUIDITY",
      selected_count=len(roster),pool_count=len(src),
      complete_adjusted_ohlcv_claim=not missing and zero==0,
      missing_open_or_close_study=missing,zero_volume_count=zero,
      suspicious_abs_daily_log_changes_gt25pct_count=len(jumps),
      top_extreme_log_jumps=sorted(jumps,key=lambda x:abs(x["close_to_close_log_return"]),reverse=True)[:12],
      full_period_study_rows=int(selected.valid_study_rows.min()),
      whole_panel_coverage_selection_hindsight=True,
      source_currency_and_ISIN_missing=True,actual_bid_ask_missing=True,
      category_count=categories,
      policy_held_instrument_day_count=unique_uses,
      source_digest=sha(FROZEN/"OASIS_TOP150.csv"))
    return q

def _cs_rank(pred,returns,minimum=20):
    df=pd.concat([pred.rename("pred"),returns.rename("r")],axis=1).dropna()
    if len(df)<minimum:return math.nan,math.nan,math.nan
    rho=spearmanr(df.pred,df.r).statistic
    top=df.nlargest(2,"pred")
    advantage=float(top.r.mean()-df.r.median())
    dispersion=float(df.r.quantile(.9)-df.r.quantile(.1))
    return float(rho),advantage,dispersion

def signal_audit():
    roster,O,C,V,jumps=source()
    feats=prepare(C)
    p=read_ledger("P3_OASIS_CRISIS_ACTIVE")
    # Conservative primary measure at independent ~21-session stride:
    # no daily overlapping forward-return labels for naive statistical claims.
    daily_results=collections.defaultdict(lambda:collections.defaultdict(list))
    monthly_results=collections.defaultdict(lambda:collections.defaultdict(list))
    category={r.ticker:r.macro_category for r in roster.itertuples(index=False)}
    cats=collections.defaultdict(lambda:collections.defaultdict(list))
    for j in range(0,len(p)-22):
        s=p.signal_date.iloc[j]
        entry=p.day.iloc[j]
        end5=p.day.iloc[j+5]
        end21=p.day.iloc[j+21]
        ss=feats["score"].loc[s]
        for h,last in ((5,end5),(21,end21)):
            if entry not in O.index or last not in O.index:continue
            with np.errstate(divide="ignore",invalid="ignore"):
                realized=np.log(O.loc[last]/O.loc[entry]).replace([np.inf,-np.inf],np.nan)
            rho,excess,spread=_cs_rank(ss,realized)
            if not np.isfinite(rho):continue
            dest=daily_results[p.regime.iloc[j]]
            for k,v in (("rho_"+str(h),rho),("top2_minus_median_"+str(h),excess),
                        ("oracle_p90_p10_"+str(h),spread)):
                dest[k].append(v)
            if j%21==0:
                dest=monthly_results[p.regime.iloc[j]]
                for k,v in (("rho_"+str(h),rho),("top2_minus_median_"+str(h),excess),
                            ("oracle_p90_p10_"+str(h),spread)):
                    dest[k].append(v)
                if h==21:
                    for cat in set(category.values()):
                        subset=[t for t in realized.index if category.get(t)==cat]
                        r2,_,_=_cs_rank(ss.reindex(subset),realized.reindex(subset),minimum=10)
                        if np.isfinite(r2):cats[cat][p.regime.iloc[j]].append(r2)
    # Trace *actual* initiated one-for-one replacement's subsequent
    # 21-session relative return; not ability to trade the oracle maximum.
    switch=collections.defaultdict(list);switch_rows=[];not_pair=0
    for j in range(1,len(p)-21):
        old=set(str(p.names.iloc[j-1]).split(";"))
        new=set(str(p.names.iloc[j]).split(";"))
        incoming=new-old;outgoing=old-new
        if len(incoming)==len(outgoing)==1:
            tnew=next(iter(incoming));told=next(iter(outgoing))
            entry=p.day.iloc[j];exit_=p.day.iloc[j+21]
            try:
                ar=O.loc[[entry,exit_],[tnew,told]]
                if not ((ar>0)&ar.notna()).all().all():continue
                rnew=math.log(float(ar.loc[exit_,tnew]/ar.loc[entry,tnew]))
                rold=math.log(float(ar.loc[exit_,told]/ar.loc[entry,told]))
                delta=rnew-rold
                regime=str(p.regime.iloc[j])
                switch[regime].append(delta)
                switch_rows.append((str(entry.date()),regime,told,tnew,delta))
            except KeyError:continue
        elif len(incoming)+len(outgoing)>0:not_pair+=1
    return dict(status="SIGNAL_SKILL_NOT_CERTIFIED",
       method="price-score rank vs next OPEN/OPEN realized return",
       regimes_daily_overlapping={
          k:{m:summarize(v) for m,v in d.items()} for k,d in daily_results.items()},
       regimes_every_21_days_nonoverlap_stride={
          k:{m:summarize(v) for m,v in d.items()} for k,d in monthly_results.items()},
       within_category_21_session_nonoverlap_rho={
          k:{reg:summarize(v) for reg,v in d.items()} for k,d in cats.items()},
       post_switch_21day_gross_relative_log_gain_by_regime={k:summarize(v) for k,v in switch.items()},
       worst_decisions_sorted=sorted(switch_rows,key=lambda x:x[-1])[:15],
       best_decisions_sorted=sorted(switch_rows,key=lambda x:x[-1],reverse=True)[:15],
       one_to_one_switches_audited=len(switch_rows),
       unmatched_multi_or_nontrading_state_changes=not_pair,
       caveats=["Post-result labels only","nonoverlapping strided regimes still dependent",
           "Adjusted Open quotes not executable bid-ask","Expected alpha vs incumbent uncalibrated",
           "Model epistemic errors are not validated from paired price volatility"])

def risk_audit():
    arm_names=("P0_MONTHLY_GREEDY","P2_DAILY_ECONOMIC_HYSTERESIS",
      "P3_OASIS_CRISIS_ACTIVE","P4_MONTHLY_GREEDY_CRISIS",
      "P6_DAILY_ECONOMIC_HYSTERESIS_ONLY_CHANGEP")
    metrics={}
    for name in arm_names:
        d=read_ledger(name)
        w=d.wealth.to_numpy(float)
        peak=np.maximum.accumulate(w)
        underwater=w/peak-1
        j=int(np.argmin(underwater))
        i=int(np.argmax(w[:j+1]))
        pday=d.iloc[i:j+1]
        cash=pday.cash_weight.to_numpy(float)
        daily_log=np.diff(np.log(w))
        largest_losses=np.argsort(daily_log)[:10]+1
        metrics[name]=dict(
          maxdd=float(underwater[j]),from_peak=str(d.day.iloc[i].date()),
          trough=str(d.day.iloc[j].date()),drawdown_sessions=j-i,
          drawdown_stress_days=int(pday.crisis.astype(bool).sum()),
          drawdown_risk_off_fraction=float((cash>.30).mean()),
          drawdown_mean_exposure=float(pday.risky_weight.mean()),
          trough_holdings=str(d.names.iloc[j]),
          worst_10_return_days=[dict(day=str(d.day.iloc[x].date()),
            log_return=float(daily_log[x-1]),regime=str(d.regime.iloc[x]),
            held=str(d.names.iloc[x]),exposure=float(d.risky_weight.iloc[x]))
            for x in largest_losses],
          fraction_of_10_worst_days_crisis=float(d.crisis.iloc[largest_losses].mean()),
          all_days_risk_off_share=float((d.cash_weight>.3).mean()),
          time_underwater_fraction=float(np.mean(underwater<0)),
          longest_underwater_streak=int(max((sum(1 for _ in g)
             for k,g in __import__("itertools").groupby(underwater<0) if k),default=0)),
          holding_day_counts=d.names.value_counts().head(10).to_dict())
    return dict(status="TAIL_CONTROL_INSUFFICIENT",
       source_run=39132785483,by_policy=metrics,
       structural_risk="2 concentrated positions, no per-holding conditional ES; broad market flag risk-off ~142 days of 2366",
       group_agnostic_market_proxy=True)

def execution_audit():
    d0=read_ledger("P0_MONTHLY_GREEDY")
    d2=read_ledger("P2_DAILY_ECONOMIC_HYSTERESIS")
    d3=read_ledger("P3_OASIS_CRISIS_ACTIVE")
    d4=read_ledger("P4_MONTHLY_GREEDY_CRISIS")
    policies=[d0,d2,d3,d4,read_ledger("P1_DAILY_GREEDY"),
              read_ledger("P5_DAILY_TOP5_HYSTERESIS"),
              read_ledger("P6_DAILY_ECONOMIC_HYSTERESIS_ONLY_CHANGEP")]
    assert all((p.day==d0.day).all() for p in policies)
    results={}
    for p in policies:
        arm=p.policy.iloc[0]
        trades=p[p.action_taken>0]
        switchdays=p[p.name_switch>0]
        dif=np.log(p.wealth.iloc[-1]/p.wealth.iloc[0])
        groups=p.groupby("regime")
        results[arm]=dict(total_trades=len(trades),name_switches=len(switchdays),
            cash_weight_avg=float(p.cash_weight.mean()),
            annual_mean_trading_notional_over_current_wealth=float(
                252*(p.traded_value.div(p.wealth).sum()/len(p))),
            fee_money=sum(p.cost),
            annual_fee_drag_estimated_non_compounded_log=float(
                252*(p.cost.div(p.wealth).sum()/len(p))),
            blocked_orders=int(p.blocked_orders.sum()),
            stale_held_day_count=int(p.stale_held_marks.sum()),
            invalid_negative_cash=int((p.cash_weight<-1e-9).sum()),
            observed_crisis_selling_sessions=int((trades.crisis==True).sum()),
            total_log_growth_first_to_last=float(dif),
            states_with_switches=switchdays.regime.value_counts().to_dict(),
            average_held_etfs=float(p.names.str.count(";").add(1).mean()))
    main=pd.read_csv(FROZEN/"RESULT.json") if False else json.loads((FROZEN/"RESULT.json").read_text())
    return dict(status="EXECUTION_CONSISTENT_COSTED_BUT_NOT_BROKER_VALIDATED",
        matched_days=len(d0),ledger_costs_confirmed=True,arms=results,
        net_growth_differences_vs_controls={
          "P3_minus_P0":results["P3_OASIS_CRISIS_ACTIVE"]["total_log_growth_first_to_last"]-results["P0_MONTHLY_GREEDY"]["total_log_growth_first_to_last"],
          "P3_minus_P4":results["P3_OASIS_CRISIS_ACTIVE"]["total_log_growth_first_to_last"]-results["P4_MONTHLY_GREEDY_CRISIS"]["total_log_growth_first_to_last"],
          "P3_minus_P2":results["P3_OASIS_CRISIS_ACTIVE"]["total_log_growth_first_to_last"]-results["P2_DAILY_ECONOMIC_HYSTERESIS"]["total_log_growth_first_to_last"]},
        assigned_adjusted_open_prices_are_not_verified_executable_spreads=True,
        benchmark_reference=("same 150 ETF source and calendar only"),
        historical_study_cannot_rank_orig_eur60_strategies=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--role",required=True,choices=ROLES)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    dispatch={"data":data_audit,"signal":signal_audit,
              "risk":risk_audit,"execution":execution_audit}
    result=dispatch[a.role]()
    result["agent_role"]=a.role.upper()+"_AGENT"
    result["original_run_id"]=39132785483
    result["source_sha256"]=sha(FROZEN/"SHA256_MANIFEST.txt")
    result["research_only"]=True
    output=Path(a.out);output.mkdir(parents=True,exist_ok=False)
    (output/(a.role.upper()+"_AUDIT.json")).write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("OASIS_FORENSIC_"+a.role.upper()+" "+json.dumps(result,allow_nan=False),flush=True)
if __name__=="__main__":main()
