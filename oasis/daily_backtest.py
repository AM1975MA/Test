#!/usr/bin/env python3
"""OASIS V1 matched daily-open ledger; retained-holdings vs opportunity switching.

Separate as-of signal data from later price-at-open execution. Research use ONLY.
"""
from __future__ import annotations
import argparse,hashlib,json,math,shutil,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src")]
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from oasis.observers import prepare,market_states,ranks,switch_names

FEE=.001
ARMS=("P0_MONTHLY_GREEDY","P1_DAILY_GREEDY","P2_DAILY_ECONOMIC_HYSTERESIS",
      "P3_OASIS_CRISIS_ACTIVE","P4_MONTHLY_GREEDY_CRISIS",
      "P5_DAILY_TOP5_HYSTERESIS","P6_DAILY_ECONOMIC_HYSTERESIS_ONLY_CHANGEP")
RESEARCH="OASIS_V1_NOT_LIVE"
SOURCE=ROOT/"data/eu120/raw_ticker_csv"
UNIVERSE=ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv"
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def execute(shares,cash,names,scale,open_actual,open_mark):
    """Sell first; fills only at actual observed Open, no phantom buys.

    Partial buys limited by actual available cash including fees.
    Missing Open -> order rejected, not filled; stale hold mark audited.
    """
    before=cash+sum(q*float(open_mark[t]) for t,q in shares.items())
    if before<=0 or not np.isfinite(before):raise AssertionError("invalid equity")
    budget=before/(1.+3*FEE)
    weights=dict.fromkeys(names,scale/2.)
    wanted={t:budget*w for t,w in weights.items()}
    traded=0.;unfilled=0;partial=0
    # Sells, including partial reductions, must precede buys.
    for t,q in list(shares.items()):
        px=open_actual.get(t,np.nan)
        marked=float(open_mark[t])
        if not (np.isfinite(marked) and marked>0):
            raise AssertionError("held ETF has no valid valuation mark")
        if not (np.isfinite(px) and px>0):
            target_cash=wanted.get(t,0.)
            if q*marked>target_cash+1e-10:unfilled+=1
            continue
        target_qty=wanted.get(t,0.)/float(px)
        if q>target_qty+1e-12:
            delta=q-target_qty
            value=delta*float(px)
            cash+=value*(1.-FEE)
            traded+=value
            if target_qty<=1e-12:shares.pop(t,None)
            else:shares[t]=target_qty
    # Buys, only if actually quoted at today's open and cash can fund fees.
    for t in names:
        px=open_actual.get(t,np.nan)
        if not (np.isfinite(px) and px>0):
            unfilled+=1
            continue
        target_qty=wanted[t]/float(px)
        held=shares.get(t,0.)
        if target_qty<=held+1e-12:continue
        desired=target_qty-held
        permissible=max(0.,cash)/(float(px)*(1.+FEE))
        filled=min(desired,permissible)
        if filled<desired-1e-12:partial+=1
        if filled<=0:continue
        order=filled*float(px)
        cash-=order*(1.+FEE)
        traded+=order
        shares[t]=held+filled
    shares={t:q for t,q in shares.items() if q>1e-12}
    if cash < -1e-9:raise AssertionError("negative cash / implicit leverage")
    after=max(0.,cash)+sum(q*float(open_mark[t]) for t,q in shares.items())
    if after>before+1e-9:raise AssertionError("created money by trading")
    return shares,max(cash,0.),dict(traded_value=traded,cost=before-after,
                                    blocked_orders=unfilled,partial_buys=partial)

def _daily_metrics(frame,signal_calendar):
    value=frame.wealth.to_numpy(float)
    rets=np.diff(np.log(value))
    if len(rets)<100:raise AssertionError("insufficient test horizon")
    years=(pd.Timestamp(frame.day.iloc[-1])-pd.Timestamp(frame.day.iloc[0])).days/365.25
    cagr=float((value[-1]/value[0])**(1/years)-1)
    dd=float(np.min(value/np.maximum.accumulate(value)-1))
    v=float(np.std(rets,ddof=1))
    sharpe=float(np.mean(rets)/v*np.sqrt(252.)) if v>0 else 0.
    neg=np.expm1(rets)
    es5=float(np.mean(np.sort(neg)[:max(1,int(math.ceil(.05*len(neg))))]))
    yf=pd.to_datetime(frame.day).dt.year
    pieces={}
    for key,mask in (("2017_2020",yf<=2020),
        ("2021_2023",yf.between(2021,2023)),
        ("2024_2026",yf>=2024)):
        part=frame.loc[mask,"wealth"].to_numpy(float)
        d=frame.loc[mask,"day"]
        duration=(pd.Timestamp(d.iloc[-1])-pd.Timestamp(d.iloc[0])).days/365.25 if len(d)>1 else 0.
        pieces[key]=dict(n=int(len(part)),cagr=float((part[-1]/part[0])**(1/duration)-1)
                           if duration>.1 else None)
    return dict(n_days=len(frame),date_first=str(frame.day.iloc[0]),
       date_last=str(frame.day.iloc[-1]),terminal_wealth=float(value[-1]),
       cagr=cagr,daily_maxdd=dd,daily_sharpe=sharpe,
       daily_es5=es5,mean_cash=float(frame.cash_weight.mean()),
       mean_exposure=float(frame.risky_weight.mean()),
       n_rebalances=int(frame.action_taken.sum()),
       n_name_switches=int(frame.name_switch.sum()),
       total_bought_sold_notional=float(frame.traded_value.sum()),
       total_fee_fraction_start_wealth=float(frame.cost.sum()),
       blocked_orders=int(frame.blocked_orders.sum()),
       partial_buys=int(frame.partial_buys.sum()),
       held_quote_gaps=int(frame.stale_held_marks.sum()),
       crisis_evaluation_days=int(frame.crisis.sum()),
       slice_cagr=pieces)

def simulate(arm,observed,states,opens,dates,signal_index,volume=None):
    shares={};cash=1.;age={};month=None;last_scale=None
    mark=opens.ffill(limit=5)
    rows=[]
    for j,d in enumerate(dates):
        s=signal_index[j]
        # The close at s is known when the exchange opens at d.
        assert pd.Timestamp(s)<pd.Timestamp(d)
        signal_n=observed["score"].index.get_loc(s)
        o=opens.loc[d]
        prices=mark.loc[d]
        current_cash=cash+sum(float(prices[t])*q for t,q in shares.items())
        if not np.isfinite(current_cash):
            raise AssertionError(f"Unpriced retained instrument at {d}")
        held=list(shares)
        state=states.loc[s]
        named_policy={"P1_DAILY_GREEDY":"P1_DAILY_GREEDY",
           "P5_DAILY_TOP5_HYSTERESIS":"P5_DAILY_TOP5_HYSTERESIS",
           "P6_DAILY_ECONOMIC_HYSTERESIS_ONLY_CHANGEP":
              "P6_DAILY_ECONOMIC_HYSTERESIS_ONLY_CHANGEP"}.get(arm,"P2")
        new_month=(month!=(d.year,d.month))
        month=(d.year,d.month)
        if arm in ("P0_MONTHLY_GREEDY","P4_MONTHLY_GREEDY_CRISIS"):
            if new_month or not held:
                intended=ranks(observed,signal_n)[:2];why="MONTHLY"
            else:
                intended=held[:2];why="MONTHLY_HOLD"
        else:
            intended,why=switch_names(observed,signal_n,held,age,named_policy,
                    cp5=float(state.cp_recent))
        target_scale=.5 if arm in ("P3_OASIS_CRISIS_ACTIVE","P4_MONTHLY_GREEDY_CRISIS") and bool(state.crisis) else 1.
        if len(intended)!=2:raise AssertionError("bad selector")
        do_trade=(not held or set(held)!=set(intended)
                  or last_scale is None or abs(last_scale-target_scale)>1e-12
                  # A daily scanner does NOT mechanically rebalance when
                  # its selected names have not changed; otherwise the
                  # benchmark gets a gratuitous trading-cost handicap.
                  or (arm in ("P0_MONTHLY_GREEDY","P4_MONTHLY_GREEDY_CRISIS") and new_month))
        before=set(held)
        cost=0.;traded=0.;blocks=0;partials=0
        if do_trade:
            shares,cash,actual=execute(shares,cash,intended,target_scale,
                o.to_dict(),prices)
            cost=actual["cost"];traded=actual["traded_value"]
            blocks=actual["blocked_orders"];partials=actual["partial_buys"]
        newheld=set(shares)
        for t in newheld:
            age[t]=0 if t not in before else age.get(t,0)+1
        for t in list(age):
            if t not in newheld:age.pop(t,None)
        if do_trade:
            last_scale=target_scale
        wealth=cash+sum(q*float(prices[t]) for t,q in shares.items())
        if not np.isfinite(wealth) or wealth<=0:
            raise AssertionError("invalid end-of-day opening equity")
        held_missing=sum(not (np.isfinite(o.get(t,np.nan)) and o[t]>0) for t in shares)
        actual_exposure=(wealth-cash)/wealth
        rows.append(dict(day=d,signal_date=s,wealth=wealth,policy=arm,
            cash_weight=cash/wealth,risky_weight=actual_exposure,
            names=";".join(shares.keys()),name_switch=int(bool(before and before!=newheld)),
            traded_value=traded,action_taken=int(traded>1e-12),
            cost=cost,blocked_orders=blocks,partial_buys=partials,
            stale_held_marks=held_missing,crisis=bool(state.crisis),
            regime=str(state.state),cp_recent=float(state.cp_recent),
            high_vol_posterior=float(state.hmm_high),
            top_candidate=ranks(observed,signal_n)[0],decision=why))
    return pd.DataFrame(rows)

def paired_monthly_bootstrap(ledger,reference="P0_MONTHLY_GREEDY",reps=1500):
    per_month={}
    for name,group in ledger.groupby("policy"):
        g=group.sort_values("day").copy()
        g["month"]=pd.to_datetime(g.day).dt.to_period("M")
        last=g.groupby("month").wealth.last()
        first=g.wealth.iloc[0]
        v=np.log(np.r_[first,last.to_numpy(float)])
        per_month[name]=np.diff(v)
    if not all(len(v)==len(per_month[reference]) for v in per_month.values()):
        raise AssertionError("unmatched month calendar")
    n=len(per_month[reference]);rng=np.random.default_rng(20261018)
    res={}
    for name,monthly in per_month.items():
        if name==reference:continue
        diff=monthly-per_month[reference]
        vals=[]
        for _ in range(reps):
            ix=[]
            while len(ix)<n:
                start=int(rng.integers(0,n))
                ix.extend((start+k)%n for k in range(12))
            vals.append(float(np.mean(diff[np.asarray(ix[:n],int)])))
        res[name]=dict(mean_monthly_log_gain=float(np.mean(diff)),
          ci95=np.quantile(vals,[.025,.975]).tolist(),
          n=int(n))
    return res

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--oracle",required=True)
    parser.add_argument("--out",required=True)
    a=parser.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    roster=pd.read_csv(UNIVERSE)
    tickers=roster.ticker.astype(str).tolist()
    if len(tickers)!=60 or len(set(tickers))!=60:
        raise AssertionError("retrospective EUR60 roster has changed")
    oracle=json.loads((Path(a.oracle)/"RESULT.json").read_text())
    if oracle["compared_months"]!=113 or oracle["source_60_EUR_names_sha256"]!=sha(UNIVERSE):
        raise AssertionError("oracle calendar or EUR60 hash drift")
    cal=pd.read_csv(Path(a.oracle)/"MONTHLY_ORACLE_113.csv",
        parse_dates=["signal_date","entry_date","exit_date"])
    start=pd.Timestamp(cal.entry_date.iloc[0]);end=pd.Timestamp(cal.exit_date.iloc[-1])
    source=out/"_raw";source.mkdir()
    roster.to_csv(source/"universe.csv",index=False)
    for t in tickers:shutil.copyfile(SOURCE/(t+".csv"),source/(t+".csv"))
    mats,_,_=load_ticker_csv_folder(source)
    opens=mats["Open"].reindex(columns=tickers).astype(float)
    close=mats["Close"].reindex(columns=tickers).astype(float)
    valid=(opens.notna().sum(axis=1)>=30)&(close.notna().sum(axis=1)>=30)
    calendar=opens.index[valid]
    indices=np.flatnonzero((calendar>=start)&(calendar<=end))
    if len(indices)<1500:raise AssertionError(f"Insufficient joint open dates {len(indices)}")
    pre=calendar[indices[0]-1] if indices[0]>0 else None
    if pre is None:raise AssertionError("missing prior signal close")
    dates=calendar[indices]
    signals=[calendar[i-1] for i in indices]
    if len(dates)!=len(signals):raise AssertionError("bad next-open alignment")
    observed=prepare(close)
    states=market_states(observed)
    for i in (0,1,100,len(dates)-1):
        if not pd.Timestamp(signals[i])<pd.Timestamp(dates[i]):
            raise AssertionError("daily signal lookahead")
        if len(ranks(observed,observed["score"].index.get_loc(signals[i])))<5:
            raise AssertionError("too few eligible as-of tickers")
    allrows=[];metrics={}
    for arm in ARMS:
        x=simulate(arm,observed,states,opens,dates,signals)
        m=_daily_metrics(x,signals);metrics[arm]=m
        x.to_csv(out/(arm+".csv"),index=False)
        allrows.append(x)
        print("OASIS_ARM",arm,json.dumps(m),flush=True)
    ledger=pd.concat(allrows,ignore_index=True)
    ci=paired_monthly_bootstrap(ledger)
    prev=ledger[ledger.policy==ARMS[0]]
    sanity={"min_days":int(min(x["n_days"] for x in metrics.values())),
        "equal_endpoints":len(set((z["date_first"],z["date_last"]) for z in metrics.values()))==1,
        "zero_production_changes":True,
        "no_old_ml_scores_read":True,
        "next_open_execution_invariants":True,
        "data_open_volume_zero_observations":int((mats["Volume"].reindex(columns=tickers)
                .reindex(index=dates).fillna(-1)==0).to_numpy().sum()),
        "eligible_asof_first":int(observed["eligible"].loc[signals[0]].sum()),
        "eligible_asof_last":int(observed["eligible"].loc[signals[-1]].sum())}
    if not sanity["equal_endpoints"]:raise AssertionError("arm unequal endpoints")
    output=dict(status="OASIS_DAILY_RESEARCH_COMPLETED",periods_open=int(len(dates)),
        date_start=str(start.date()),date_end=str(end.date()),tickers=60,
        fees_one_way=FEE,portfolio_mark="daily_open_with_5_day_missing_quote_valuation_only",
        strategy_eligibility="asof_close_with_last_253_history",
        source_manifest_sha256=sha(ROOT/"data/eu120/manifest.json"),
        roster_sha256=sha(UNIVERSE),
        benchmark_old_ml_predictions_used=False,
        metrics=metrics,paired_12month_bootstrap=ci,
        daily_system_states=states.loc[signals].state.value_counts().to_dict(),
        audits=sanity,cohort_2026_survivorship_bias=True,
        no_PIT_listing_ISIN_quote_currency_validation=True,
        no_real_spreads_slippage_volume_liquidity_validation=True,
        independent_forward_holdout=False,
        conclusion="EXPLORATORY_NOT_LIVE_READY")
    (out/"MARKET_STATES.csv").write_text(states.loc[signals].to_csv())
    (out/"RESULT.json").write_text(json.dumps(output,indent=2,allow_nan=False)+"\n")
    print("OASIS_DAILY_RESULT "+json.dumps(output,allow_nan=False),flush=True)

if __name__=="__main__":main()
