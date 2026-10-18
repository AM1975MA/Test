#!/usr/bin/env python3
"""M0: economic opportunity geometry on exactly the 149 canonical ETFs.

A hindsight winner is NOT an investable or learnable signal. This study
distinguishes upper-quality hindsight from causal baseline information.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from oasis149.canonical import load_149,sha,SRC
ROOT=Path(__file__).resolve().parents[2]
STRIDE=21
FEE=.001
SEED=20261019
DELAYS=(0,1,3,5,10)
HORIZONS=(1,3,5,10,21,42,63)
PLACEBOS=250
ARMS=("ORACLE_FUTURE_WINNER","ORACLE_IN_CAUSAL_LEADING_CLASS",
      "CAUSAL_PRIOR21","CAUSAL_PRIOR63","CAUSAL_TOP5_STICKY",
      "CAUSAL_CLASS_LEADER")
FROZEN_REF=ROOT/"oasis149/results/MANIFEST_149.json"

def choose_rank(score,allowed=None):
    row=score if allowed is None else score.reindex(allowed)
    row=row.dropna().astype(float)
    if not len(row):raise AssertionError("no as-of rank candidates")
    return sorted(row.index,key=lambda t:(-float(row[t]),t))[0]

def choices_and_evidence(roster,opens,closes,days,signals):
    names=list(roster.ticker)
    group=roster.set_index("ticker").macro_category.to_dict()
    groupmembers={g:list(roster.loc[roster.macro_category==g,"ticker"])
                  for g in sorted(set(group.values()))}
    # All past returns computed on closes available on each signal date.
    logclose=np.log(closes.where(closes>0))
    prev21=logclose-logclose.shift(21)
    prev63=logclose-logclose.shift(63)
    result={arm:[] for arm in ARMS}
    eventrows=[]
    horizonrows=[]
    sticky=None
    n=(len(days)-1)//STRIDE
    assert n==112 and len(names)==149, (n,len(names))
    price=opens.loc[days,names].to_numpy(float)
    assert np.isfinite(price).all() and (price>0).all()
    for b in range(n):
        t=b*STRIDE;end=t+STRIDE;s=signals[t]
        assert s<days[t]<days[end]
        momentum21=prev21.loc[s,names].astype(float)
        momentum63=prev63.loc[s,names].astype(float)
        if not(np.isfinite(momentum21).all() and np.isfinite(momentum63).all()):
            raise AssertionError("As-of 21/63-day returns unavailable")
        r=np.log(price[end]/price[t])
        fwd=pd.Series(r,index=names)
        oracle=choose_rank(fwd)
        past21=choose_rank(momentum21)
        past63=choose_rank(momentum63)
        selected_group=sorted(groupmembers,key=lambda g:(
            -float(momentum63[groupmembers[g]].mean()),g))[0]
        class_oracle=choose_rank(fwd,groupmembers[selected_group])
        inclass=choose_rank(momentum63,groupmembers[selected_group])
        ordered=sorted(names,key=lambda x:(-float(momentum63[x]),x))
        top5=ordered[:5]
        if sticky not in top5:sticky=ordered[0]
        selected={
            "ORACLE_FUTURE_WINNER":oracle,
            "ORACLE_IN_CAUSAL_LEADING_CLASS":class_oracle,
            "CAUSAL_PRIOR21":past21,
            "CAUSAL_PRIOR63":past63,
            "CAUSAL_TOP5_STICKY":sticky,
            "CAUSAL_CLASS_LEADER":inclass}
        for policy,ticker in selected.items():result[policy].append(ticker)
        # The benchmark is NOT given hindsight labels.
        reference=math.log(.6*price[end,names.index("SPY")]/price[t,names.index("SPY")] +
                           .4*price[end,names.index("AGG")]/price[t,names.index("AGG")])
        ranks=spearmanr(momentum63.to_numpy(float),r).statistic
        oracle_spread=float(fwd[oracle]-reference)
        winner_in5=oracle in top5
        before=math.log(price[t,names.index("SPY")]/price[max(t-21,0),names.index("SPY")]) if t>=21 else None
        market=math.log(price[end,names.index("SPY")]/price[t,names.index("SPY")])
        regime=("HINDSIGHT_SHOCK" if market<=-.06 else
            "HINDSIGHT_REBOUND" if before is not None and before<=-.06 and market>=.06 else
            "OTHER_BLOCK")
        eventrows.append(dict(block=b,signal=str(s.date()),
            start=str(days[t].date()),end=str(days[end].date()),
            perfect_future_winner=oracle,
            perfect_future_winner_category=group[oracle],
            asof_prior21=past21,asof_prior63=past63,
            asof_top5=";".join(top5),
            asof_class_leader=inclass,
            asof_chosen_class=selected_group,
            perfect_in_prior_top5=int(winner_in5),
            future_past63_spearman=float(ranks),
            oracle_gross_21d_log_spread_vs_60_40=oracle_spread,
            past63_gross_21d_log_spread_vs_60_40=float(fwd[past63]-reference),
            past21_gross_21d_log_spread_vs_60_40=float(fwd[past21]-reference),
            future_best_gross_21d_log=float(fwd[oracle]),
            hindsight_event=regime,
            benchmark_60_40_block_log=float(reference)))
        for h in HORIZONS:
            if t+h>len(days)-1:continue
            r_i=price[t+h,names.index(past63)]/price[t,names.index(past63)]
            r_b=(.6*price[t+h,names.index("SPY")]/price[t,names.index("SPY")] +
                 .4*price[t+h,names.index("AGG")]/price[t,names.index("AGG")])
            horizonrows.append(dict(block=b,signal=str(s.date()),horizon=h,
                 selected=past63,causal_prior63_gross_log_edge_vs_60_40=math.log(r_i/r_b)))
    return result,pd.DataFrame(eventrows),pd.DataFrame(horizonrows),price,names,group,groupmembers

def simulate(ticker_sequence,price,names,delay=0):
    """Exact single-position percentage fee wealth; only 21d/Open samples."""
    assert 0<=delay<STRIDE
    assert len(ticker_sequence)==112
    index={name:j for j,name in enumerate(names)}
    cur=None
    wealth=1.
    fee_log=0.
    switches=0
    tradesides=0
    daily=np.full(112*21+1,np.nan)
    blocklogs=[]
    for b,chosen in enumerate(ticker_sequence):
        t=b*STRIDE
        prior=wealth
        # First buy: if lagged oracle recognition uses incumbent SPY until
        # delayed first switch; all causal policies are instant at entry.
        if cur is None:
            cur=chosen if delay==0 else "SPY"
            wealth/=1+FEE
            tradesides+=1
            fee_log+=math.log1p(FEE)
        if delay==0 and cur!=chosen:
            wealth*=(1-FEE)/(1+FEE)
            fee_log+=math.log1p(FEE)-math.log1p(-FEE)
            tradesides+=2
            switches+=1
            cur=chosen
        daily[t]=wealth
        for k in range(1,STRIDE+1):
            x=t+k
            pxratio=price[x,index[cur]]/price[x-1,index[cur]]
            wealth*=pxratio
            if delay>0 and k==delay and cur!=chosen:
                wealth*=(1-FEE)/(1+FEE)
                fee_log+=math.log1p(FEE)-math.log1p(-FEE)
                tradesides+=2
                switches+=1
                cur=chosen
            daily[x]=wealth
        blocklogs.append(math.log(wealth/prior))
    if not np.isfinite(daily).all() or (daily<=0).any():
        raise AssertionError("bad financial path")
    return daily,np.asarray(blocklogs,float),dict(
        switches=switches,fee_sides=tradesides,total_log_fee_drag=fee_log)

def metrics(path,logs,tradefacts,days):
    annual=(days[112*21]-days[0]).days/365.25
    rr=np.diff(np.log(path))
    std=float(np.std(rr,ddof=1))
    return dict(cagr=float(path[-1]**(1/annual)-1),
        terminal_wealth_multiple=float(path[-1]),
        daily_open_maxdd=float(np.min(path/np.maximum.accumulate(path)-1)),
        sharpe_daily_log=float(np.mean(rr)/std*np.sqrt(252)) if std>0 else None,
        expected_shortfall_worst5pct_daily=float(np.mean(np.sort(np.expm1(rr))[:max(1,int(np.ceil(.05*len(rr))))])),
        net_block_mean_log=float(np.mean(logs)),net_block_positive_fraction=float(np.mean(logs>0)),
        fees=tradefacts)

def static_benchmarks(price,names,days):
    idx={v:i for i,v in enumerate(names)}
    spy=price[:,idx["SPY"]]/price[0,idx["SPY"]]
    agg=price[:,idx["AGG"]]/price[0,idx["AGG"]]
    return {"BUY_HOLD_SPY":spy/(1+FEE),"BUY_HOLD_AGG":agg/(1+FEE),
       "BUY_HOLD_60SPY_40AGG":(.6*spy+.4*agg)/(1+FEE)}

def matched_class_switch_null(selections,classes,members,rng):
    chosen=[];prior=None
    for t,target in enumerate(selections):
        g=classes[target]
        if t and selections[t]==selections[t-1]:
            n=prior
        else:
            choices=[x for x in members[g] if x!=prior]
            n=str(rng.choice(choices))
        chosen.append(n);prior=n
    assert sum(a!=b for a,b in zip(chosen[1:],chosen[:-1]))==sum(a!=b for a,b in zip(selections[1:],selections[:-1]))
    assert all(classes[x]==classes[y] for x,y in zip(chosen,selections))
    return chosen

def bootstrap_anchor_spearman(values):
    x=np.asarray(values,float)
    rng=np.random.default_rng(SEED+9)
    n=len(x);out=[]
    for _ in range(1500):
        ix=[]
        while len(ix)<n:
            k=int(rng.integers(n))
            ix.extend((k+j)%n for j in range(3))
        out.append(float(x[np.asarray(ix[:n],int)].mean()))
    return {"mean":float(x.mean()),
        "95pct_3_anchor_circular_CI":np.quantile(out,[.025,.975]).tolist(),
        "n_blocks":n}

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    roster,O,C,V,days,signals,quality=load_149()
    source=json.loads(FROZEN_REF.read_text())
    assert source["member_count"]==149 and source["roster_sha256"]==sha(SRC/"universe.csv")
    chosen,evidence,horizon,price,names,group,members=choices_and_evidence(roster,O,C,days,signals)
    rows={}
    for policy in ARMS:
        path,logs,facts=simulate(chosen[policy],price,names,0)
        rows[policy]=dict(path=path,logs=logs,
                          score=metrics(path,logs,facts,days),selection=chosen[policy])
        print("M0_POLICY "+policy+" "+json.dumps(rows[policy]["score"]),flush=True)
    lagged={}
    for d in DELAYS:
        path,logs,facts=simulate(chosen["ORACLE_FUTURE_WINNER"],price,names,delay=d)
        lagged[str(d)]={"score":metrics(path,logs,facts,days),
          "monthly_block_log":logs.tolist()}
        print("M0_CLAIRVOYANT_DELAY "+str(d)+" "+json.dumps(lagged[str(d)]["score"]),flush=True)
    passive={}
    for key,path in static_benchmarks(price,names,days).items():
        monthlog=np.log(path[np.arange(0,112*21+1,21)][1:]/path[np.arange(0,112*21+1,21)][:-1])
        passive[key]=metrics(path,monthlog,
           dict(switches=0,fee_sides=2 if key=="BUY_HOLD_60SPY_40AGG" else 1,total_log_fee_drag=math.log1p(FEE)),days)
    # matched one-position switching schedule / macro-class exposure
    rng=np.random.default_rng(SEED)
    null=[]
    momentum63=chosen["CAUSAL_PRIOR63"]
    for k in range(PLACEBOS):
        shuffled=matched_class_switch_null(momentum63,group,members,rng)
        path,_,facts=simulate(shuffled,price,names,0)
        null.append(dict(trial=k,terminal_wealth_multiple=float(path[-1]),
                 cagr=float(path[-1]**(365.25/(days[112*21]-days[0]).days)-1),
                 daily_open_maxdd=float(np.min(path/np.maximum.accumulate(path)-1)),
                 switches=facts["switches"]))
    nullframe=pd.DataFrame(null)
    oracle=evidence.oracle_gross_21d_log_spread_vs_60_40
    grosspositive=np.maximum(oracle.to_numpy(float),0)
    hist={
        "n_full_21session_nonoverlap_blocks":112,
        "n_discarded_tail_opens":int(len(days)-1-112*21),
        "oracle_best_gross_log_edge_vs_60_40":{
           "mean":float(oracle.mean()),"median":float(oracle.median()),
           "p10":float(oracle.quantile(.1)),"p90":float(oracle.quantile(.9)),
           "share_months_gt_2pct":float(np.mean(oracle>.02)),
           "share_months_gt_5pct":float(np.mean(oracle>.05)),
           "top10_periods_share_positive_gross_edge":float(
               np.sort(grosspositive)[-10:].sum()/grosspositive.sum())},
        "past63_forward21_cross_section_spearman":bootstrap_anchor_spearman(
            evidence.future_past63_spearman),
        "future_top1_in_asof_past_top5":{
            "hit_count":int(evidence.perfect_in_prior_top5.sum()),
            "hit_fraction":float(evidence.perfect_in_prior_top5.mean()),
            "random_5_over_149":5/149},
        "horizons_of_past63_selection":horizon.groupby("horizon").causal_prior63_gross_log_edge_vs_60_40.agg(
           ["size","mean","median"]).reset_index().to_dict("records"),
        "event_slices":{},
        "matched_null":dict(n=PLACEBOS,
            terminal_wealth_median=float(nullframe.terminal_wealth_multiple.median()),
            cagr_median=float(nullframe.cagr.median()),
            cagr_05=float(nullframe.cagr.quantile(.05)),
            cagr_95=float(nullframe.cagr.quantile(.95)),
            causal_prior63_cagr=rows["CAUSAL_PRIOR63"]["score"]["cagr"],
            causal_prior63_fraction_null_cagr_below=float(np.mean(
                nullframe.cagr<rows["CAUSAL_PRIOR63"]["score"]["cagr"])),
            null_mean_switch_count=float(nullframe.switches.mean()),
            causal_actual_switch_count=rows["CAUSAL_PRIOR63"]["score"]["fees"]["switches"])
    }
    for event,g in evidence.groupby("hindsight_event"):
        hist["event_slices"][event]=dict(n=len(g),
            mean_oracle_log_edge_vs_passive=float(g.oracle_gross_21d_log_spread_vs_60_40.mean()),
            mean_causal_prior63_log_edge_vs_passive=float(g.past63_gross_21d_log_spread_vs_60_40.mean()),
            prior_top5_captures_future_top1=float(g.perfect_in_prior_top5.mean()),
            note="EX-POST event label; never supplied to investment policy")
    report=dict(status="ORIGINAL149_M0_OPPORTUNITY_PHYSICS_COMPLETED",
       exact_original149=True,source_sha256=sha(SRC/"universe.csv"),
       n_research_etfs=149,n_signal_blocks=112,
       first_entry=str(days[0].date()),last_exit=str(days[112*21].date()),
       fee_one_side=FEE,forecast_prices_available_at_prior_close=True,
       original_etf_production_unchanged=True,
       hindsight_overall_oracle_not_tradeable=True,
       hindsight_delay_oracle_not_tradeable=True,
       all_paths_full_invested_single_etf=True,
       original149_priorly_mined_and_survivorship_biased=True,
       metrics_by_policy={k:rows[k]["score"] for k in ARMS},
       oracle_delays=lagged,
       passive_context=passive,
       scientific_diagnostics=hist,
       caveats=[
         "Oracle uses future outcomes by construction, its value is NOT learnable alpha",
         "Delayed clairvoyant is a recognition-latency DIAGNOSTIC, not feasible strategy",
         "Causal baselines are deliberately simplistic; failure does not prove nonexistence of all predictive skill",
         "Past Top5 hit chance benchmark 5/149 ignores serial/factor dependences",
         "149 ETF universe survivor-selected and repeatedly mined; no PIT or broker fills verified",
         "Only 112 nonoverlapping monthly-type blocks, strong regime/autocorrelation",
         "Longer horizon relative return probes overlap and share data",
         "Passive SPY and 60/40 USD benchmark cost and cash conventions differ",
         "Daily MaxDD sampled at observed adjusted market OPENS, not intraday"])
    evidence.to_csv(out/"PER_BLOCK_CAUSAL_VS_HINDSIGHT.csv",index=False)
    horizon.to_csv(out/"HORIZON_SKILL_DIAGNOSTICS.csv",index=False)
    nullframe.to_csv(out/"MATCHED_RANDOM_PLACEBO_250.csv",index=False)
    priceseries=pd.DataFrame({"day":days[:112*21+1]})
    for name,k in rows.items():priceseries[name]=k["path"]
    for delay,info in lagged.items():
        path,_,_=simulate(chosen["ORACLE_FUTURE_WINNER"],price,names,delay=int(delay))
        priceseries["ORACLE_DELAY_"+delay]=path
    for name,arr in static_benchmarks(price,names,days).items():priceseries[name]=arr
    priceseries.to_csv(out/"MATCHED_DAILY_OPEN_CURVES.csv",index=False)
    (out/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("ORIGINAL149_M0_SCIENCE_RESULT "+json.dumps(report,allow_nan=False),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);args=p.parse_args()
    run(args.out)
if __name__=="__main__":main()
