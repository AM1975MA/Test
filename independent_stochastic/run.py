#!/usr/bin/env python3
"""Independent end-to-end stochastic ETF portfolio study: no legacy ML score inputs."""
from __future__ import annotations
import argparse,hashlib,json,math,shutil,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src"),str(ROOT/"europe120/eu120_retrain")]
from etf_trader.source_only.raw_io import load_ticker_csv_folder
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
from independent_stochastic.experts import (
    ARMS,BASE,SEED,features,expert_allocations,stochastic_scenario_choose,
    weighted_mix,softmax_experts,synthetic_no_future_test)
from independent_stochastic.physics import daily_asof,common_market_filter

FEE=.001
CAGR_OLD_RH=.09978039091271884
CAGR_OLD_H7=.13423094964064108

def fee_turn(w,prev,first):
    tr=.5*sum(abs(w.get(t,0)-prev.get(t,0)) for t in set(w)|set(prev))
    if not first:
        tr+=.5*abs((1-sum(w.values()))-(1-sum(prev.values())))
    return tr

def actual_factor(w,entry,exit_,opens,fee):
    active=[t for t,x in w.items() if x>1e-10]
    if not active:raise AssertionError("empty ETF decision")
    b=opens.loc[entry,active].to_numpy(float)
    e=opens.loc[exit_,active].to_numpy(float)
    if not (np.isfinite(b).all() and np.isfinite(e).all() and
            (b>0).all() and (e>0).all()):
        raise AssertionError(f"Unobservable future open for {active} at {entry}->{exit_}")
    gross=1.-sum(w.values())+sum(w[t]*float(e[i]/b[i]) for i,t in enumerate(active))
    factor=gross*(1.-FEE*fee)
    if factor<=0 or not np.isfinite(factor):raise AssertionError("unrealistic wealth")
    return float(factor),float(gross)

def replay(decisions,calendar,opens):
    metrics={};monthly=[];logreturns={}
    for arm,positions in decisions.items():
        wealth=1.;path=[wealth];previous={};log=[];turns=[];exposures=[];breadth=[]
        for idx,(p,w) in enumerate(zip(calendar.itertuples(index=False),positions)):
            if not p.signal_date < p.entry_date < p.exit_date:
                raise AssertionError("signal entry exit ordering")
            turn=fee_turn(w,previous,idx==0)
            factor,gross=actual_factor(w,p.entry_date,p.exit_date,opens,turn)
            wealth*=factor;path.append(wealth);log.append(math.log(factor))
            turns.append(turn);exposures.append(sum(w.values()))
            breadth.append(len(w))
            monthly.append(dict(policy=arm,signal_date=str(p.signal_date.date()),
                entry_date=str(p.entry_date.date()),exit_date=str(p.exit_date.date()),
                risky_weight=float(sum(w.values())),cash_weight=float(1.-sum(w.values())),
                holdings=json.dumps(w,sort_keys=True),holding_count=len(w),
                turnover=turn,gross_return=gross-1.,net_return=factor-1.))
            previous=w.copy()
        arr=np.asarray(log);wealth_path=np.asarray(path,float);ret=np.expm1(arr)
        vol=float(np.std(arr,ddof=1))
        metrics[arm]=dict(cagr=float(wealth**(12/len(arr))-1),
          terminal_wealth=float(wealth),
          monthly_maxdd=float(np.min(wealth_path/np.maximum.accumulate(wealth_path)-1)),
          monthly_sharpe=float(np.mean(arr)/vol*np.sqrt(12)) if vol>0 else 0.,
          annual_turnover=float(np.mean(turns)*12),
          mean_equity_exposure=float(np.mean(exposures)),cash_months=int(sum(x<.99999 for x in exposures)),
          mean_number_etfs=float(np.mean(breadth)),
          worst_month=float(np.min(ret)),
          tail_es5_monthly=float(np.mean(np.sort(ret)[:math.ceil(.05*len(ret))])))
        logreturns[arm]=arr
    ledger=pd.DataFrame(monthly)
    for policy in ARMS:
        data=ledger[ledger.policy==policy]
        years=data.signal_date.str[:4].astype(int)
        months={}
        for label,mask in (("2017_2020",years<=2020),("2021_2023",years.between(2021,2023)),
                           ("2024_2026",years>=2024)):
            r=data.loc[mask,"net_return"].to_numpy(float)
            months[label]=dict(n=len(r),cagr=float(np.prod(1+r)**(12/len(r))-1) if len(r) else None)
        metrics[policy]["slices"]=months
    return metrics,ledger,logreturns

def ci(logreturns,baseline="D0_BROAD_LOWVOL",rep=1000):
    n=len(logreturns[baseline]);rng=np.random.default_rng(SEED+2)
    out={}
    for policy,v in logreturns.items():
        if policy==baseline:continue
        diff=v-logreturns[baseline];samples=[]
        for _ in range(rep):
            ix=[]
            while len(ix)<n:
                p=int(rng.integers(0,n))
                ix.extend((p+j)%n for j in range(12))
            samples.append(np.mean(diff[np.asarray(ix[:n])]))
        out[policy]=dict(monthly_log_diff=float(np.mean(diff)),
             ci95=np.quantile(samples,[.025,.975]).tolist())
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--oracle",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    synthetic_no_future_test()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    roster=pd.read_csv(ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv")
    tickers=roster.ticker.astype(str).tolist()
    assert len(tickers)==len(set(tickers))==60
    oracle=json.loads((Path(args.oracle)/"RESULT.json").read_text())
    assert oracle["compared_months"]==113
    assert oracle["source_60_EUR_names_sha256"]==sha(
        ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv")
    cal=pd.read_csv(Path(args.oracle)/"MONTHLY_ORACLE_113.csv",
           parse_dates=["signal_date","entry_date","exit_date"])[
           ["signal_date","entry_date","exit_date"]]
    assert len(cal)==113 and cal.signal_date.is_monotonic_increasing
    tmp=out/"_raw_source";tmp.mkdir()
    roster.to_csv(tmp/"universe.csv",index=False)
    for t in tickers:shutil.copyfile(ROOT/"data/eu120/raw_ticker_csv"/(t+".csv"),tmp/(t+".csv"))
    mats,_,_=load_ticker_csv_folder(tmp)
    close=mats["Close"].reindex(columns=tickers)
    opens=mats["Open"].reindex(columns=tickers)
    assert close.index.is_monotonic_increasing
    decisions={name:[] for name in ARMS}
    expert_prior={k:{} for k in BASE}
    prior_scen={}
    pending=[];expert_state={k:0. for k in BASE}
    asof_record=[]
    for i,row in enumerate(cal.itertuples(index=False)):
        # CRITICAL: mature experts only if exit open is ALREADY BEFORE OR AT
        # current SIGNAL CLOSE, not current entry open. Trade exit is later.
        asof=pd.Timestamp(row.signal_date)
        mature=[p for p in pending if p["exit"]<=asof]
        pending=[p for p in pending if p["exit"]>asof]
        for p in mature:
            net={}
            for k in BASE:
                factor,_=actual_factor(p["weights"][k],p["entry"],p["exit"],opens,p["turns"][k])
                net[k]=math.log(factor)
            avg=float(np.mean(list(net.values())))
            expert_state={k:.97*expert_state[k]+net[k]-avg for k in BASE}
        feat,daily,eligible=features(close,asof)
        base=expert_allocations(feat,daily)
        chosen,utilities=stochastic_scenario_choose(base,feat,daily,i,prior_scen)
        coeff=softmax_experts(expert_state)
        hedge=weighted_mix(base,coeff)
        naive=weighted_mix(base,{k:1/len(BASE) for k in BASE})
        gate=common_market_filter(daily)["flag"]
        reg={t:float(v*(.5 if gate else 1.)) for t,v in hedge.items()}
        arms={**base,"D5_STUDENT_T_SCENARIO":base[chosen],
              "D6_HEDGE_GAME":hedge,"D7_HEDGE_REGIME":reg,
              "D8_UNIFORM_EXPERTS":naive}
        for k,w in arms.items():
            if abs(sum(w.values())-(.5 if k=="D7_HEDGE_REGIME" and gate else 1.))>1e-7:
                raise AssertionError("portfolio simplex violation")
            decisions[k].append(w)
        turns={k:fee_turn(w,expert_prior[k],i==0) for k,w in base.items()}
        pending.append(dict(entry=pd.Timestamp(row.entry_date),exit=pd.Timestamp(row.exit_date),
           weights=base,turns=turns))
        expert_prior={k:w.copy() for k,w in base.items()}
        prior_scen=base[chosen]
        asof_record.append(dict(signal_date=str(asof.date()),n_eligible=len(eligible),
             scenario_selected=chosen,scenario_utility=utilities,
             expert_online_weights=coeff,expert_shadow_matured_count=len(mature),
             expert_online_log_evidence=dict(expert_state),risk_gate=bool(gate)))
        if i in (0,1,2,60,112):
            print("MONTH_SIGNAL",i,str(asof.date()),"eligible",len(eligible),
                  "game",coeff,"stochastic_opt",chosen,flush=True)
    metrics,ledger,logs=replay(decisions,cal,opens)
    if len(ledger)!=113*len(ARMS):raise AssertionError("missing ledger rows")
    if sum(p["expert_shadow_matured_count"] for p in asof_record)!=111:
        raise AssertionError("unexpected monthly expert payoff maturity lag")
    rel=ci(logs)
    ledger.to_csv(out/"MONTHLY_LEDGER.csv",index=False)
    (out/"MONTHLY_SIGNALS.json").write_text(json.dumps(asof_record,indent=2,allow_nan=False)+"\n")
    output=dict(status="INDEPENDENT_STOCHASTIC_COMPLETED",months=len(cal),ETFs=60,
       baseline_old_ml_cagr=CAGR_OLD_RH,
       baseline_old_hysteresis_regime_cagr=CAGR_OLD_H7,
       old_model_scores_read=False,old_model_training_invoked=False,
       expert_returns_matured_by_signal_close=True,
       synthetic_future_mutation_pass=True,source_manifest_sha256=sha(ROOT/"data/eu120/manifest.json"),
       metrics=metrics,paired_12month_ci_against_D0=rel,
       regime_months=int(sum(z["risk_gate"] for z in asof_record)),
       scenario_choice_counts={k:int(sum(z["scenario_selected"]==k for z in asof_record)) for k in BASE},
       expert_maturity_updates=int(sum(z["expert_shadow_matured_count"] for z in asof_record)),
       risks=["hindsight_selected_surviving_EUR60","not_PIT_verified",
              "no_FX_or_cash_carry","not_independent_future_holdout"],
       decision="HISTORICAL_EXPLORATION_ONLY")
    (out/"RESULT.json").write_text(json.dumps(output,indent=2,allow_nan=False)+"\n")
    print("INDEPENDENT_STOCHASTIC_RESULT "+json.dumps(output,allow_nan=False),flush=True)
if __name__=="__main__":main()
