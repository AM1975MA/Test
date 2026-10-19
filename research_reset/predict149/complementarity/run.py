#!/usr/bin/env python3
"""T149-I complementary ETF forecasters and genuinely as-of expert allocation.

Freeze model predictions. Reproduce original H1/H3/F3 shares and fees
before any diagnostic or intervention. NEVER choose ex-post calendar years.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from oasis149.canonical import load_149,sha,SRC
from research_reset.m0b.enrichment import rebalance_exact

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/"research_reset/predict149/factor_residual/results"
SEED=20261019
K=21
FROZEN={"F3":"B0_F3_FROZEN",
        "H1":"H1_FACTOR_ONLY","H3":"H3_COMBINED_Q"}
STRATEGIES=("F3","H1","H3","STATIC_F3_H1_50",
            "STATIC_F3_H3_50","STATIC_3_WAY",
            "SWITCH_PAST3","SWITCH_PAST6","ONLINE_RIDGE_GATE",
            "NONCAUSAL_ORACLE_F3_H1")
MARKETS=("SPY63_positive","SPY_vol21_gt63",
         "HYG63_gt_AGG63","ETF63_breadth_gt_half")
FEATS=("spy63","spy21","spyvol21","spyvol63","credit63",
       "breadth63","dispersion63","prior_F3_H1_overlapping_fraction")

def from_archive():
    original=pd.read_csv(SOURCE/"FULL_9536_ASOF_FACTOR_AND_RESIDUAL_FORECASTS.csv")
    old=pd.read_csv(SOURCE/"MATCHED_5_ETF_DAILY_COSTED_WEALTH.csv")
    if len(original)!=64*149 or len(old)!=64*K+1:
        raise AssertionError("Frozen 149 data changed")
    roster,O,C,V,days,signals,quality=load_149()
    tickers=list(roster.ticker)
    ids=sorted(original.block.unique())
    if ids!=list(range(48,112)):
        raise AssertionError("Evaluation chronology moved")
    if not {"block","ticker","signal","maturity","category","v63",*FROZEN.values()}<=set(original.columns):
        raise AssertionError("Archived frozen predictions missing")
    if original.groupby("block").size().ne(149).any():raise AssertionError("149 incomplete block")
    if (original[["block","ticker"]].duplicated()).any():raise AssertionError("Duplicate forecast ID")
    selections={}
    for expert,score in FROZEN.items():
        selections[expert]=[]
        for b in ids:
            frame=original[original.block==b].sort_values(score,ascending=False)
            selections[expert].append(frame.ticker.head(5).tolist())
    if not np.array_equal(pd.to_datetime(old.day).to_numpy(),
                          pd.to_datetime(days[48*K:112*K+1]).to_numpy()):
        raise AssertionError("Frozen daily date axis shifted")
    for k,b in enumerate(ids):
        first=original[original.block==b]
        if first.signal.iloc[0]!=str(pd.Timestamp(signals[b*K]).date()):
            raise AssertionError("Frozen forecast signal differs from current original data")
        assert pd.Timestamp(signals[b*K])<pd.Timestamp(days[b*K])
    return original,old,roster,O,C,days,signals,ids,selections

def state_from_past(close,roster,signal,overlap):
    """Only completed closes through signal; may not access current trade open."""
    names=list(roster.ticker)
    sl=close.loc[:signal, list(dict.fromkeys(names+["SPY","HYG","AGG"]))]
    log=np.log(sl.where(sl>0))
    if len(log)<128 or not np.isfinite(log.tail(126).to_numpy()).all():
        raise AssertionError("Incomplete prior-close state")
    spy=log.SPY
    spy63=float(spy.iloc[-1]-spy.iloc[-64])
    spy21=float(spy.iloc[-1]-spy.iloc[-22])
    returns=spy.diff()
    v21=float(returns.tail(21).std(ddof=1))
    v63=float(returns.tail(63).std(ddof=1))
    a=(log.iloc[-1]-log.iloc[-64])
    breadth=float((a[names]>0).mean())
    dispersion=float(a[names].std(ddof=1))
    credit=float(a.HYG-a.AGG)
    x=np.array([spy63,spy21,v21,v63,credit,
                breadth,dispersion,overlap],float)
    if not np.isfinite(x).all():raise AssertionError("NaN as-of state")
    flags={
       "SPY63_positive":bool(spy63>0),
       "SPY_vol21_gt63":bool(v21>v63),
       "HYG63_gt_AGG63":bool(credit>0),
       "ETF63_breadth_gt_half":bool(breadth>.5)}
    return x,flags

def monthly_weights(chosen):
    """Merge underlying target shares; no equity-curve averaging."""
    weights={}
    for expert,mass,lists in chosen:
        if mass<0 or mass>1:raise AssertionError("bad policy allocation")
        if len(lists)!=5:raise AssertionError("bad expert roster")
        for ticker in lists:weights[ticker]=weights.get(ticker,0)+mass/5
    weights={t:w for t,w in weights.items() if w>1e-14}
    if abs(sum(weights.values())-1)>1e-12 or len(weights)>15:
        raise AssertionError("Portfolio cannot be funded")
    return weights

def trade_policy(weightseq,prices,days,ids,names):
    ix={t:k for k,t in enumerate(names)}
    n=len(ids)
    assert len(weightseq)==n
    shares={};cash=1.
    curve=np.empty(n*K+1)
    fees=0.;turnover=0.;turn_dates=0
    for k,b in enumerate(ids):
        off=b*K
        weights=weightseq[k]
        quotes={t:float(prices.loc[days[off],t])
                for t in set(shares)|set(weights)}
        old=cash+sum(shares[t]*quotes[t] for t in shares)
        shares,cash,turn,fee,orders=rebalance_exact(shares,cash,weights,quotes)
        new=cash+sum(shares[t]*quotes[t] for t in shares)
        if new>old+1e-10 or new<=0:
            raise AssertionError("Wealth increase during rebalance or bankruptcy")
        fees+=fee;turnover+=turn
        turn_dates+=int(turn>1e-11)
        curve[k*K]=new
        for d in range(1,K+1):
            tday=days[off+d]
            curve[k*K+d]=cash+sum(shares[t]*float(prices.loc[tday,t]) for t in shares)
    if not np.isfinite(curve).all() or min(curve)<=0:
        raise AssertionError("Nonfinite capital path")
    return curve,{"fee_notional":fees,
                  "absolute_gross_traded_initial_dollars":turnover,
                  "trade_dates":turn_dates,
                  "avg_underlying_positions":float(np.mean([len(w) for w in weightseq]))}

def metrics(wealth,days,turn):
    dr=np.diff(np.log(wealth))
    years=(days[-1]-days[0]).days/365.25
    st=float(np.std(dr,ddof=1))
    return {**turn,
        "cagr":float((wealth[-1]/wealth[0])**(1/years)-1),
        "wealth_final":float(wealth[-1]),
        "maxdd_daily_open":float(np.min(wealth/np.maximum.accumulate(wealth)-1)),
        "sharpe_daily_log":float(np.mean(dr)/st*np.sqrt(252)),
        "es5_daily":float(np.mean(np.sort(np.expm1(dr))[:int(np.ceil(.05*len(dr)))])),
        "daily_vol_annualized":float(st*np.sqrt(252))}

def bootstrap(x,seed=SEED,nrep=3000):
    arr=np.asarray(x,float);assert len(arr)==64
    rng=np.random.default_rng(seed)
    sim=[]
    for _ in range(nrep):
        inds=[]
        while len(inds)<64:
            j=int(rng.integers(0,64))
            inds.extend((j+z)%64 for z in range(3))
        sim.append(float(np.mean(arr[np.asarray(inds[:64],int)])))
    return dict(mean=float(np.mean(arr)),ci95=np.quantile(sim,[.025,.975]).tolist())

def get_diagnostic_slices(d,flags,months):
    sliced={}
    for key in MARKETS:
        yes=np.asarray([f[key] for f in flags],bool)
        for label,mask in (("true",yes),("false",~yes)):
            vals=(months["F3"]-months["H1"])[mask]
            if len(vals)>1:
                rng=np.random.default_rng(SEED+17)
                sample=np.mean(rng.choice(vals,size=(1600,len(vals)),replace=True),axis=1)
                ci=np.quantile(sample,[.025,.975]).tolist()
            else:ci=[None,None]
            sliced[key+"_"+label]=dict(n=int(mask.sum()),
                mean_F3_minus_H1_log=float(np.mean(vals)) if len(vals)>0 else None,
                F3_wins_fraction=float(np.mean(vals>0)) if len(vals)>0 else None,
                naive_iid_month_bootstrap_CI95=ci)
    return sliced

def record_predictions_for_regimes(pred,expert_selections,roster,C,days,signals,ids):
    states=[];flags=[];observations=[]
    for k,b in enumerate(ids):
        s=pd.Timestamp(signals[b*K])
        a=set(expert_selections["F3"][k]);h=set(expert_selections["H1"][k])
        x,f=state_from_past(C,roster,s,len(a&h)/5)
        states.append(x);flags.append(f)
        observations.append(dict(eval_block=k,original_block=b,signal=str(s.date()),
            signal_known_before_trade_open=str(pd.Timestamp(days[b*K]).date()),
            overlap_F3_H1=len(a&h),
            overlap_F3_H3=len(a&set(expert_selections["H3"][k])),
            overlap_H1_H3=len(h&set(expert_selections["H3"][k])),
            **{name:float(value) for name,value in zip(FEATS,x)},**f,
            F3=";".join(expert_selections["F3"][k]),
            H1=";".join(expert_selections["H1"][k]),
            H3=";".join(expert_selections["H3"][k])))
    return np.asarray(states),flags,pd.DataFrame(observations)

def causal_decisions(expert_month_returns,states,eval_dates,signal_dates):
    """One-block embargo: latest known full period is block k-2, never k-1."""
    diff=expert_month_returns["F3"]-expert_month_returns["H1"]
    assert len(diff)==64 and states.shape==(64,len(FEATS))
    ret={}
    for k in range(64):
        b=48+k
        signal=pd.Timestamp(signal_dates[b*K])
        max_known=k-2
        if max_known>=0:
            maturity=pd.Timestamp(eval_dates[(b-1)*K])
            if not maturity<signal:
                raise AssertionError("Meta label matured only at future trade open")
        if k>=4:
            selected3=float(np.sum(diff[k-4:k-1]))
            # previous slice indices k-4,k-3,k-2; excludes k-1
        if k>=7:
            selected6=float(np.sum(diff[k-7:k-1]))
        for horizon,name in ((3,"SWITCH_PAST3"),(6,"SWITCH_PAST6")):
            if k<horizon+1:
                weight=.5
            else:
                win=float(np.sum(diff[k-horizon-1:k-1]))
                weight=1. if win>0 else 0.
            ret.setdefault(name,[]).append(weight)
        if k<14:
            wridge=.5
        else:
            valid=np.arange(k-1) # indices 0,...,k-2
            if len(valid)<12:raise AssertionError("meta before maturity window")
            scaler=StandardScaler()
            X=scaler.fit_transform(states[valid])
            # Ridge fit only on realized expert spreads from strict maturity
            model=Ridge(alpha=25.,fit_intercept=True)
            model.fit(X,diff[valid])
            prediction=float(model.predict(scaler.transform(states[k:k+1]))[0])
            wridge=float(np.clip(.5+prediction/.10,.2,.8))
        ret.setdefault("ONLINE_RIDGE_GATE",[]).append(wridge)
    return ret

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",required=True)
    output=Path(parser.parse_args().out);output.mkdir(parents=True,exist_ok=False)
    pred,old,roster,opens,closes,days,signals,ids,selection=from_archive()
    names=list(roster.ticker)
    window=days[ids[0]*K:(ids[-1]+1)*K+1]
    strategy_weights={}
    standalone={}
    for policy in ("F3","H1","H3"):
        weight=[monthly_weights([(policy,1.,s)])
             for s in selection[policy]]
        strategy_weights[policy]=weight
        curve,turn=trade_policy(weight,opens,days,ids,names)
        same=old[{"F3":"B0_F3_FROZEN","H1":"H1_FACTOR_ONLY",
                  "H3":"H3_COMBINED_Q"}[policy]].to_numpy(float)
        replay_err=float(np.max(np.abs(curve-same)))
        if replay_err>1e-9:
            raise AssertionError("REPLAY ERROR "+policy+"="+str(replay_err))
        standalone[policy]=(curve,turn,replay_err)
    month={name:np.diff(np.log(v[0][::K])) for name,v in standalone.items()}
    for name,v in month.items():
        if len(v)!=64:raise AssertionError("bad month return "+name)
    # State is computed strictly as-of previous SIGNAL close, not current entry
    # Open. Prior archive forecast names were also frozen before training.
    X,flags,observations=record_predictions_for_regimes(
        pred,selection,roster,closes,days,signals,ids)
    expert_weights=causal_decisions(month,X,days,signals)
    for k in range(64):
        choices={name:selection[name][k] for name in ("F3","H1","H3")}
        strategy_weights.setdefault("STATIC_F3_H1_50",[]).append(
            monthly_weights([("F3",.5,choices["F3"]),("H1",.5,choices["H1"])]))
        strategy_weights.setdefault("STATIC_F3_H3_50",[]).append(
            monthly_weights([("F3",.5,choices["F3"]),("H3",.5,choices["H3"])]))
        strategy_weights.setdefault("STATIC_3_WAY",[]).append(
            monthly_weights([(p,1/3,choices[p]) for p in ("F3","H1","H3")]))
        for policy,series in expert_weights.items():
            w=float(series[k])
            strategy_weights.setdefault(policy,[]).append(
                monthly_weights([("F3",w,choices["F3"]),("H1",1-w,choices["H1"])]))
        # NONCAUSAL ONLY hindsight score based on realized later period:
        who="F3" if month["F3"][k]>month["H1"][k] else "H1"
        strategy_weights.setdefault("NONCAUSAL_ORACLE_F3_H1",[]).append(
            monthly_weights([(who,1.,choices[who])]))
    results={};curves={};costed_m={}
    for name in STRATEGIES:
        if name in standalone:
            curve,turn,err=standalone[name]
        else:
            curve,turn=trade_policy(strategy_weights[name],opens,days,ids,names)
        curves[name]=curve
        costed_m[name]=np.diff(np.log(curve[::K]))
        results[name]=metrics(curve,window,turn)
        print("T149I_POLICY",name,json.dumps(results[name],allow_nan=False),flush=True)
    # Distinguish structural complementarity from mere calendar-year picking
    monthlycorr=np.corrcoef(np.vstack([month["F3"],month["H1"],month["H3"]]))
    daily=np.vstack([np.diff(np.log(standalone[k][0])) for k in ("F3","H1","H3")])
    dailycorr=np.corrcoef(daily)
    yearly={}
    for year in (2021,2022,2023,2024,2025,2026):
        mask=pd.Series(window).dt.year==year
        ix=np.flatnonzero(mask)
        yearly[str(year)]=dict(n_days=len(ix),
            annual_window_open_to_open={
                name:float(curves[name][ix[-1]]/curves[name][ix[0]]-1)
                for name in ("F3","H1","H3","STATIC_F3_H1_50",
                    "STATIC_F3_H3_50","SWITCH_PAST3","SWITCH_PAST6",
                    "ONLINE_RIDGE_GATE")})
    relative={}
    for a,b in (("F3","H1"),("F3","H3"),("H3","H1")):
        diff=month[a]-month[b]
        relative[a+"__minus__"+b]=dict(
            mean_21day_log=float(np.mean(diff)),
            positive_months=int(np.sum(diff>0)),
            zero_months=int(np.sum(diff==0)),
            block3_ci=bootstrap(diff,SEED+70))
    # Require significant gain in 64 paired calendar blocks AND capital survival
    # to call conditional regime-timing productive.
    statistical={}
    best_baseline=max(results[k]["cagr"] for k in ("F3","H1","H3"))
    for name in ("SWITCH_PAST3","SWITCH_PAST6","ONLINE_RIDGE_GATE"):
        comparators={"static50":costed_m[name]-
             costed_m["STATIC_F3_H1_50"]}
        for control in ("F3","H1","H3"):
            comparators[control]=costed_m[name]-costed_m[control]
        ci={c:bootstrap(v,SEED+31)["ci95"] for c,v in comparators.items()}
        statistical[name]=dict(paired_monthly_incremental_ci=ci,
            pretrained_profit_regime_gate=bool(
                all(z[0]>0 for z in ci.values()) and
                results[name]["maxdd_daily_open"]>=
                    max(results["F3"]["maxdd_daily_open"],
                        results["H3"]["maxdd_daily_open"]) and
                results[name]["es5_daily"]>=results["F3"]["es5_daily"]))
    static=results["STATIC_F3_H1_50"]
    static_gate=bool(static["maxdd_daily_open"]>=max(
        results["F3"]["maxdd_daily_open"],results["H1"]["maxdd_daily_open"])
        and static["cagr"]>=best_baseline-.01
        and static["es5_daily"]>=results["F3"]["es5_daily"])
    overlap=observations[["overlap_F3_H1","overlap_F3_H3","overlap_H1_H3"]]
    analysis=dict(
        year_diagnostic=yearly,
        monthly_expert_correlation=monthlycorr.tolist(),
        daily_expert_correlation=dailycorr.tolist(),
        comparative_expert_returns=relative,
        overlap_mean_count=overlap.mean().to_dict(),
        overlap_frequency_F3_H1=observations.overlap_F3_H1.value_counts().sort_index().to_dict(),
        feature_condition_diagnostics=get_diagnostic_slices(
            observations,flags,month),
        expert_pairwise_monthly_log_differences={
            "F3_minus_H1":(month["F3"]-month["H1"]).tolist(),
            "F3_minus_H3":(month["F3"]-month["H3"]).tolist(),
            "H3_minus_H1":(month["H3"]-month["H1"]).tolist()})
    # Save ability for auditor to check NO b-1 outcome used for any adaptive policy
    for name in expert_weights:
        observations["F3_weight_"+name]=expert_weights[name]
        observations["latest_matured_meta_eval_block"]=[
            k-2 if k>=2 else -1 for k in range(64)]
    for key in STRATEGIES:
        observations["net_monthly_log_"+key]=costed_m[key]
        observations["n_underlyings_"+key]=[len(x) for x in strategy_weights[key]]
    dailyframe=pd.DataFrame({"day":window})
    for key,curve in curves.items():dailyframe[key]=curve
    dailyframe.to_csv(output/"EXPERTS_AND_REAL_COSTED_MIXTURES_DAILY.csv",index=False)
    observations.to_csv(output/"ASOF_64_MONTH_EXPERT_STATES_AND_CHOICES.csv",index=False)
    result=dict(status="EXACT149_F3_H1_H3_COMPLEMENTARITY_CAUSAL_REGIMES_TESTED",
        source_universe_SHA=sha(SRC/"universe.csv"),
        n_original_etfs=149,n_eval_blocks=64,n_daily_open_observations=len(window),
        original_forecast_models_unmodified=True,
        replay_max_abs_error={n:v[2] for n,v in standalone.items()},
        all_meta_labels_strictly_matured_before_signal=True,
        last_known_finished_meta_block_lag=2,
        combined_portfolio_uses_actual_weighted_ETF_shares_and_bilateral_fees=True,
        noncausal_oracle_is_DIAGNOSTIC_NOT_INVESTABLE=True,
        all_model_returns_from_preselected_2021_2026_vintage=True,
        portfolio_results=results,
        complementarity_diagnostics=analysis,
        causal_regime_statistical_gates=statistical,
        preregistered_static_50_robust_diversification_gate=static_gate,
        no_independent_holdout=True,
        no_production_or_30percent_CAGR_claim=True,
        limitations=["64 anchor periods previously mined many times, no fresh OOS",
                     "As-of market state explanatory not proven causal driver",
                     "Past observed expert strategy wealth path hypothetical, 10bp trade fee, lagged 2 blocks",
                     "Annual open-to-open windows are partial in 2021 and 2026",
                     "As-of benchmark/ETF survivor roster with no PIT delisting and USD/EUR FX broker spread",
                     "Market dynamic regime label success requires strictly prospective timestamps"])
    (output/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("T149I_COMPLEMENTARITY_FINAL "+json.dumps(result,allow_nan=False),flush=True)
if __name__=="__main__":main()
