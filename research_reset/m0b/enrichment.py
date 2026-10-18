#!/usr/bin/env python3
"""M0b: is top5 future-winner capture real information or volatility exposure?

Post-hoc after M0. All null matches use as-of class, volatility and exact
slot-survivorship. Future outcomes are NEVER used to choose placebo tickets.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from oasis149.canonical import load_149,sha,SRC
from research_reset.m0.experiment import simulate as oracle_sim,STRIDE,FEE,SEED
ROOT=Path(__file__).resolve().parents[2]
ORIGIN=ROOT/"research_reset/m0/results"
NUM=250
DAYS=112*STRIDE

def trial_surrogates(lists,dates,vol,cat,members,kind,rng):
    prev={}
    prev_orig=None
    out=[]
    diffvol=[]
    for b,current in enumerate(lists):
        if len(current)!=5 or len(set(current))!=5:raise AssertionError("bad original top5")
        mapping={}
        used=set()
        oldval=set(prev.values())
        # Keep one-to-one placeholder for each original retained identity.
        for t in current:
            if t in prev:
                name=prev[t]
                if name in used:raise AssertionError("duplicate mapped retained placeholder")
                mapping[t]=name;used.add(name)
        for t in current:
            if t in mapping:continue
            category=cat[t]
            candidates=[n for n in members[category] if n not in used and n not in oldval]
            if not candidates:raise AssertionError("No eligible same-class random ticker")
            if kind=="category_and_vol":
                # Eligible candidate may be original top5 member itself:
                # EXCLUDING it would mechanically bias the hit null downward.
                target=max(float(vol.loc[dates[b],t]),1e-9)
                candidates=sorted(candidates,key=lambda n:(
                    abs(math.log(max(float(vol.loc[dates[b],n]),1e-9)/target)),n))[:8]
            elif kind!="category_only":
                raise ValueError("unknown precommitted placebo")
            name=str(rng.choice(candidates))
            mapping[t]=name
            used.add(name)
        names=[mapping[t] for t in current]
        if len(set(names))!=5:raise AssertionError("duplicate risk exposures")
        if b>0:
            orig_survival=len(set(current)&set(prev_orig))
            null_survival=len(set(names)&set(out[-1]))
            if orig_survival!=null_survival:raise AssertionError("turnover matching broken")
        if any(cat[x]!=cat[y] for x,y in zip(current,names)):
            raise AssertionError("macro category mismatch")
        for t,z in zip(current,names):
            a=float(vol.loc[dates[b],t]);v=float(vol.loc[dates[b],z])
            if a<=0 or v<=0 or not np.isfinite([a,v]).all():
                raise AssertionError("as-of vol unavailable")
            diffvol.append(abs(math.log(v/a)))
        out.append(names)
        prev=mapping
        prev_orig=current
    return out,float(np.mean(diffvol))

def rebalance_exact(shares,cash,weights,quotes):
    """Self-financing exact all-in target net of bilateral 10bp trade costs.

    Solve final net wealth W' = initial W - fee * L1(trade target W'w
    minus observed previous holdings), with zero cash and no leverage.
    Keeping unchanged equal holdings at constant prices incurs ZERO fees.
    """
    union=set(shares)|set(weights)
    before=float(cash+sum(q*float(quotes[t]) for t,q in shares.items()))
    if before<=0 or not math.isfinite(before):raise AssertionError("invalid capital")
    current={t:float(shares.get(t,0))*float(quotes[t]) for t in union}
    if abs(sum(weights.values())-1)>1e-10:raise AssertionError("target not all invested")
    w=before
    for _ in range(80):
        turnover=sum(abs(w*weights.get(t,0.)-current[t]) for t in union)
        new=before-FEE*turnover
        if abs(new-w)<1e-14:
            w=new
            break
        w=new
    if w<=0:raise AssertionError("ruined by fees")
    targets={t:w*weight/float(quotes[t]) for t,weight in weights.items()}
    sell=sum(max(0.,current[t]-w*weights.get(t,0.)) for t in union)
    buy=sum(max(0.,w*weights.get(t,0.)-current[t]) for t in union)
    cash_after=cash+sell*(1-FEE)-buy*(1+FEE)
    if abs(cash_after)>1e-9:raise AssertionError("trade not self financing")
    return targets,0.,sell+buy,before-w,int(sell+buy>1e-12)

def portfolio(lists,price,names,days):
    """One real share/cash portfolio, 5 equal target allocations, monthly rebalance."""
    ix={ticker:i for i,ticker in enumerate(names)}
    cash=1.;shares={}
    path=np.empty(DAYS+1)
    traded=0.;nominal_fees=0.;rebals=0
    for b,selection in enumerate(lists):
        t=b*STRIDE
        marks={z:float(price[t,ix[z]]) for z in set(shares)|set(selection)}
        pre=cash+sum(q*marks[name] for name,q in shares.items())
        weights={z:1/5 for z in selection}
        shares,cash,turn,cost,orders=rebalance_exact(shares,cash,weights,marks)
        traded+=turn;nominal_fees+=cost;rebals+=int(turn>1e-12)
        post=cash+sum(q*marks[name] for name,q in shares.items())
        if post>pre+1e-9:raise AssertionError("money minted in rebalance")
        path[t]=post
        for step in range(1,STRIDE+1):
            k=t+step
            path[k]=cash+sum(q*float(price[k,ix[name]]) for name,q in shares.items())
    if not(np.isfinite(path).all() and (path>0).all()):
        raise AssertionError("invalid 5-way share wealth path")
    first,last=days[0],days[DAYS]
    years=(last-first).days/365.25
    dr=np.diff(np.log(path))
    return {
      "cagr":float(path[-1]**(1/years)-1),
      "terminal_multiple":float(path[-1]),
      "daily_open_MaxDD":float(np.min(path/np.maximum.accumulate(path)-1)),
      "worst5pct_ES_daily":float(np.mean(np.sort(np.expm1(dr))[:max(1,math.ceil(.05*len(dr)))])),
      "trade_days":rebals,
      "total_abs_traded_notional_initial_units":float(traded),
      "total_nominal_fees_initial_units":float(nominal_fees)
    },path

def read_dataset():
    roster,O,C,V,days,signals,quality=load_149()
    base=json.loads((ORIGIN/"RESULT.json").read_text())
    assert base["exact_original149"] and base["source_sha256"]==sha(SRC/"universe.csv")
    assert base["n_signal_blocks"]==112
    events=pd.read_csv(ORIGIN/"PER_BLOCK_CAUSAL_VS_HINDSIGHT.csv",parse_dates=["signal","start","end"])
    assert len(events)==112
    starts=np.array([b*STRIDE for b in range(112)],int)
    assert (events.start==pd.to_datetime(days[starts])).all()
    assert (events.signal==pd.to_datetime(signals[starts])).all()
    names=list(roster.ticker)
    price=O.loc[days,names].to_numpy(float)
    cats=roster.set_index("ticker").macro_category.to_dict()
    members={g:list(roster.loc[roster.macro_category==g,"ticker"])
             for g in sorted(set(cats.values()))}
    top=[str(s).split(";") for s in events.asof_top5]
    logC=np.log(C)
    vol=logC.diff().rolling(63,min_periods=63).std().loc[events.signal,names]
    vol.index=events.signal
    if not np.isfinite(vol.to_numpy()).all():raise AssertionError("past 63d vol missing")
    for b in range(112):
        score=np.log(price[starts[b]+STRIDE]/price[starts[b]])
        winner=sorted(range(len(names)),key=lambda i:(-float(score[i]),names[i]))[0]
        if events.perfect_future_winner.iloc[b]!=names[winner]:
            raise AssertionError("Original oracle 149 label differs")
    return roster,price,days,events,top,vol,cats,members,names

def run(out):
    dest=Path(out);dest.mkdir(parents=True,exist_ok=False)
    roster,price,days,events,original,vol,categories,groups,names=read_dataset()
    obs_hit=int(sum(events.perfect_future_winner.iloc[b] in original[b] for b in range(112)))
    if obs_hit!=15:raise AssertionError("Prior M0 result drift")
    observed,obs_path=portfolio(original,price,names,days)
    placebo=[]
    null_arrays={}
    for kind in ("category_only","category_and_vol"):
        for k in range(NUM):
            rng=np.random.default_rng(SEED+3007*k+(0 if kind=="category_only" else 100_000))
            seq,volerr=trial_surrogates(original,list(events.signal),vol,categories,groups,kind,rng)
            n_hit=sum(events.perfect_future_winner.iloc[b] in seq[b] for b in range(112))
            economics,_=portfolio(seq,price,names,days)
            placebo.append(dict(kind=kind,trial=k,hit_count=n_hit,
                avg_abs_log_vol_mismatch=volerr,**economics))
        sub=pd.DataFrame([x for x in placebo if x["kind"]==kind])
        null_arrays[kind]={
          "count":len(sub),
          "hit_count_median":float(sub.hit_count.median()),
          "hit_count_05":float(sub.hit_count.quantile(.05)),
          "hit_count_95":float(sub.hit_count.quantile(.95)),
          "original_hit_count":obs_hit,
          "fraction_null_hit_count_below_original":float(np.mean(sub.hit_count<obs_hit)),
          "empirical_rank_hit_geq_original":float((1+sum(sub.hit_count>=obs_hit))/(len(sub)+1)),
          "avg_abs_log_vol_mismatch":float(sub.avg_abs_log_vol_mismatch.mean()),
          "cagr_median":float(sub.cagr.median()),
          "cagr_05":float(sub.cagr.quantile(.05)),
          "cagr_95":float(sub.cagr.quantile(.95)),
          "original_cagr":observed["cagr"],
          "fraction_null_cagr_below_original":float(np.mean(sub.cagr<observed["cagr"])),
          "median_daily_open_MaxDD":float(sub.daily_open_MaxDD.median()),
          "original_daily_open_MaxDD":observed["daily_open_MaxDD"],
          "median_nominal_fees":float(sub.total_nominal_fees_initial_units.median()),
          "original_nominal_fees":observed["total_nominal_fees_initial_units"],
          "median_trade_days":float(sub.trade_days.median()),
          "original_trade_days":observed["trade_days"]}
        print("M0B_PLACEBO_SUMMARY "+kind+" "+json.dumps(null_arrays[kind]),flush=True)
    # Upper-quality screening bound: non-tradable oracle inside only as-of Top5.
    best_picks=[]
    idx={name:i for i,name in enumerate(names)}
    for b,shortlist in enumerate(original):
        t=b*STRIDE
        chosen=sorted(shortlist,key=lambda n:(
             -math.log(price[t+STRIDE,idx[n]]/price[t,idx[n]]),n))[0]
        best_picks.append(chosen)
    oracle_path,logs,facts=oracle_sim(best_picks,price,names,0)
    years=(days[DAYS]-days[0]).days/365.25
    restricted=dict(cagr=float(oracle_path[-1]**(1/years)-1),
        terminal_multiple=float(oracle_path[-1]),
        daily_open_maxdd=float(np.min(oracle_path/np.maximum.accumulate(oracle_path)-1)),
        executed_switches=facts["switches"],
        disclaimer="uses full next21d future return even within shortlist, no deployable alpha")
    passive=json.loads((ORIGIN/"RESULT.json").read_text())["passive_context"]["BUY_HOLD_60SPY_40AGG"]
    # The original shortlist is not a proven alpha if it fails the benchmark
    # even when its random counterpart is lower.
    main=null_arrays["category_and_vol"]
    gate=bool(
        obs_hit>main["hit_count_95"] and
        observed["cagr"]>main["cagr_median"] and
        observed["daily_open_MaxDD"]>=main["median_daily_open_MaxDD"] and
        (observed["cagr"]>passive["cagr"] and
         observed["daily_open_MaxDD"]>=passive["daily_open_maxdd"]))
    output=dict(status="ORIGINAL149_M0B_TOP5_ENRICHMENT_FALSIFIER_COMPLETED",
       preregistration_after_observing_M0=True,
       true_independent_holdout=False,original149_exact=True,
       source_sha256=sha(SRC/"universe.csv"),n_monthlike_blocks=112,
       n_placebo_runs_each=NUM,total_placebo_runs=500,
       correct_future_label_NOT_available_at_selection=True,
       same_group_every_selected_slot=True,
       exact_original_name_retention_count_matched_every_block=True,
       matched_volatility_nearest_eight_asof=True,
       observed_top5_future_winner_hits=obs_hit,
       observed_top5_equal_shares=observed,
       class_and_vol_conditional_placebos=null_arrays,
       untradeable_future_best_within_actual_past_top5=restricted,
       passive_context_spy_agg=passive,
       go_future_predictive_top5_research_preregistered_gate=gate,
       original149_dataset_survivorship_biased=True,
       caveats=[
          "150, 69 or EUR60 panels NOT substituted for canonical original149",
          "M0b formulated after M0 results, not independent discovery",
          "Shortlist risk-matched placebo only matches 63d vol and broad category, not options skew or factor covariance",
          "Hindsight best-within-five uses future returns, untradeable",
          "Historical Yahoo adjusted opens not broker executable, EUR venue and real spreads not verified",
          "Nominal gross daily marks of single-active horizon without intraday peak-to-trough",
          "Top5 and null portfolios are fully invested at each rebalance with exact self-financing 10bp fee solve"])
    pd.DataFrame(placebo).to_csv(dest/"VOL_AND_CATEGORY_MATCHED_500_PLACEBOS.csv",index=False)
    pd.DataFrame({"date":days[:DAYS+1], "top5_equal_shares":obs_path,
                  "future_best_within_past_top5_NOT_TRADABLE":oracle_path}).to_csv(
        dest/"DAILY_OPEN_TOP5_AND_RESTRICTED_ORACLE.csv",index=False)
    (dest/"RESULT.json").write_text(json.dumps(output,indent=2,allow_nan=False)+"\n")
    print("ORIGINAL149_M0B_ENRICHMENT_RESULT "+json.dumps(output,allow_nan=False),flush=True)

if __name__=="__main__":
    arg=argparse.ArgumentParser();arg.add_argument("--out",required=True)
    run(arg.parse_args().out)
