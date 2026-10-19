#!/usr/bin/env python3
"""T149-J: falsifiable value-of-F3-versus-H1 portfolio opportunity.

Frozen nonexchangeable historical 149 ETF dataset; never a prospective backtest.
A deliberate ONE-OPEN embargo on strategy labels prevents current-block leakage.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from oasis149.canonical import sha,SRC
from research_reset.predict149.complementarity.run import (
    from_archive,monthly_weights,trade_policy,metrics,bootstrap,K)
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"research_reset/predict149/complementarity/results"
MECHANISM=ROOT/"research_reset/predict149/complementarity/mechanisms/results"
SEED=20261019
MIN_MATURE=18
BETA=("SPY","QQQ","IWM","VEA","EEM","TLT","HYG","GLD","USO","IEF")
FEATURES=(
    "F3_holding_relative_score_advantage",
    "H1_holding_relative_score_advantage",
    "score_advantage_difference",
    "F3_H1_basket_past63_momentum_diff",
    "F3_H1_basket_past63_vol_ratio",
    "F3_H1_past63_basket_corr",
    "F3_H1_quoted_factor_beta_distance",
    "F3_H1_residual_quantile_width_difference",
    "USO_minus_QQQ_past63",
    "SPY_vol21_over_vol63")
SMALL_FEATURES=(2,3,4,8,9)
ARM_NAMES=("F3","H1","H3","STATIC_F3_H1_50",
    "J1_SCORE_DIFFERENCE_RULE","J2_ONLINE_RIDGE_PROB","J3_ONLINE_ANALOG_SIGN")

def strictly_asof_state(close,roster,pred_asof,signal,group_F3,group_H1):
    """Every value is from frozen current forecasts or market Close <= signal."""
    current=pred_asof.set_index("ticker")
    if len(current)!=149 or not current.index.is_unique:
        raise AssertionError("No exact 149 complete model predictions")
    for name in group_F3+group_H1:
        if name not in current.index:raise AssertionError("frozen expert missing "+name)
    needed=("B0_F3_FROZEN","H1_FACTOR_ONLY","R_Q10","R_Q90",
            *tuple("beta_"+f for f in BETA))
    if not set(needed)<=set(current):
        raise AssertionError("Missing frozen expected market and residual features")
    spread_f3=float(current.loc[group_F3,"B0_F3_FROZEN"].mean()-
                    current.loc[group_H1,"B0_F3_FROZEN"].mean())
    spread_h1=float(current.loc[group_H1,"H1_FACTOR_ONLY"].mean()-
                    current.loc[group_F3,"H1_FACTOR_ONLY"].mean())
    sd_f3=max(1e-9,float(current.B0_F3_FROZEN.std(ddof=1)))
    sd_h1=max(1e-9,float(current.H1_FACTOR_ONLY.std(ddof=1)))
    advantage_f3=spread_f3/sd_f3
    advantage_h1=spread_h1/sd_h1
    if advantage_f3 < -1e-10 or advantage_h1 < -1e-10:
        raise AssertionError("Frozen selected score not actually maximized")
    names=list(dict.fromkeys(group_F3+group_H1+["USO","QQQ","SPY"]))
    log=np.log(close.loc[:signal,names])
    if len(log)<128 or not np.isfinite(log.tail(128).to_numpy()).all():
        raise AssertionError("Short or nonfinite prior-close feature history")
    bars=log.diff().tail(63)
    ret_f=bars[group_F3].mean(axis=1).to_numpy(float)
    ret_h=bars[group_H1].mean(axis=1).to_numpy(float)
    vol_f=float(np.std(ret_f,ddof=1))
    vol_h=float(np.std(ret_h,ddof=1))
    if min(vol_f,vol_h)<1e-8:raise AssertionError("nonfinite basket risk")
    beta_cols=["beta_"+f for f in BETA]
    delta_beta=current.loc[group_F3,beta_cols].mean(axis=0).to_numpy(float)-\
               current.loc[group_H1,beta_cols].mean(axis=0).to_numpy(float)
    predspread=(current.R_Q90-current.R_Q10)
    spyvol21=float(bars.SPY.tail(21).std(ddof=1))
    spyvol63=float(bars.SPY.std(ddof=1))
    state=np.asarray([
        advantage_f3,
        advantage_h1,
        advantage_f3-advantage_h1,
        float((log.iloc[-1][group_F3]-log.iloc[-64][group_F3]).mean()-
              (log.iloc[-1][group_H1]-log.iloc[-64][group_H1]).mean()),
        float(np.log(vol_f/vol_h)),
        float(np.corrcoef(ret_f,ret_h)[0,1]),
        float(np.linalg.norm(delta_beta)),
        float(predspread[group_F3].mean()-predspread[group_H1].mean()),
        float(log.USO.iloc[-1]-log.USO.iloc[-64]-
              log.QQQ.iloc[-1]+log.QQQ.iloc[-64]),
        float(spyvol21/max(spyvol63,1e-8))],dtype=float)
    if state.shape!=(10,) or not np.isfinite(state).all():
        raise AssertionError("Invalid predeclared full economic opportunity feature")
    return state

def online_model_predictions(states,expert_deltas,days,signals,ids):
    """Dates determine valid training labels before current Close, not a row split."""
    n=len(ids)
    states=np.asarray(states,float)
    realized=np.asarray(expert_deltas,float)
    assert n==64 and states.shape==(64,10) and realized.shape==(64,)
    rows=[]
    for k,b in enumerate(ids):
        signal=pd.Timestamp(signals[b*K])
        mature=[]
        for j in range(k):
            maturity_open=pd.Timestamp(days[(ids[j]+1)*K])
            if maturity_open<signal:
                mature.append(j)
        if mature != list(range(max(0,k-1))):
            raise AssertionError("Outcome maturity embargo violated: "+str(k))
        if any(pd.Timestamp(days[(ids[j]+1)*K])>=signal for j in mature):
            raise AssertionError("Future returns in meta training")
        if k-1>=0 and pd.Timestamp(days[(ids[k-1]+1)*K])<signal:
            raise AssertionError("Newest month incorrectly available")
        ntrain=len(mature)
        if ntrain:
            prior=float(realized[mature].mean())
            oldsign=float(np.mean(realized[mature]>0))
        else:
            prior=0.;oldsign=.5
        values=dict(eval_block=k,original_block=b,signal=str(signal.date()),
            n_matured_expert_spreads=ntrain,
            latest_allowed_matured_eval_block=(mature[-1] if mature else -1),
            training_signal_date_before_entry_open=True,
            matured_delta_prior=prior,
            online_sign_prior=float(np.clip(oldsign,.00001,.99999)),
            realized_F3_minus_H1_log_differential=float(realized[k]))
        margin=float(states[k,2])
        values["J1_weight_F3"]=(.75 if margin>.5 else (.25 if margin<-.5 else .5))
        values["J1_expected_relative_delta_proxy"]=margin
        if ntrain<MIN_MATURE:
            for key in ("J2","J3"):
                values[key+"_weight_F3"]=.5
                values[key+"_predicted_signed_excess"]=prior
                values[key+"_prediction_sigma"]=None
                values[key+"_forecast_sign_prob"]=float(np.clip(oldsign,.00001,.99999))
                values[key+"_reason"]="warmup_baseline"
        else:
            trainx=states[mature,:]
            trainy=realized[mature]
            # Train-only transform for a high-regularization economic meta-forecast.
            scaler=StandardScaler()
            xx=scaler.fit_transform(trainx)
            model=Ridge(alpha=25.,fit_intercept=True)
            model.fit(xx,trainy)
            ridge_score=float(model.predict(scaler.transform(states[k:k+1]))[0])
            sigma=max(.03,float(np.std(trainy,ddof=1)))
            x_scaled=scaler.transform(states[k:k+1])[0]
            smalltrain=xx[:,list(SMALL_FEATURES)]
            nearest=np.argsort(np.sum((smalltrain-x_scaled[list(SMALL_FEATURES)])**2,axis=1),
                               kind="stable")[:8]
            neighbors=trainy[nearest]
            analog_score=float(neighbors.mean())
            analog_sigma=max(.03,float(np.std(neighbors,ddof=1)))
            for key,estimate,ss in (
                ("J2",ridge_score,sigma),("J3",analog_score,analog_sigma)):
                z=estimate/ss
                values[key+"_weight_F3"]=(.75 if z>.5 else (.25 if z<-.5 else .5))
                values[key+"_predicted_signed_excess"]=estimate
                values[key+"_prediction_sigma"]=ss
                values[key+"_forecast_sign_prob"]=float(
                    np.clip(norm.cdf(z),1e-5,1-1e-5))
                values[key+"_reason"]="learned_exante"
        rows.append(values)
    return pd.DataFrame(rows)

def prob_brier(y,p):
    a=np.asarray(y,float);b=np.asarray(p,float)
    return dict(brier=float(np.mean((a-b)**2)),
        log_loss=float(np.mean(-a*np.log(b)-(1-a)*np.log(1-b))),
        base_event_rate=float(a.mean()),
        probability_mean=float(b.mean()))

def ci_diff(x,seed=SEED):
    a=np.asarray(x,float);n=len(a)
    assert n>20
    rng=np.random.default_rng(seed)
    sims=[]
    for _ in range(2400):
        ix=[]
        while len(ix)<n:
            st=int(rng.integers(n))
            ix.extend((st+j)%n for j in range(3))
        sims.append(float(a[np.asarray(ix[:n],int)].mean()))
    return dict(mean=float(a.mean()),
        block3_95pct=np.quantile(sims,[.025,.975]).tolist(),n=n)

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    out=Path(p.parse_args().out);out.mkdir(parents=True,exist_ok=False)
    pred,archive,roster,O,C,days,signals,ids,chosen=from_archive()
    previous=pd.read_csv(BASE/"EXPERTS_AND_REAL_COSTED_MIXTURES_DAILY.csv")
    former=pd.read_csv(MECHANISM/"MECHANISM_TRUE_SHARES_NEXT_OPEN_CASH_PATHS.csv")
    if len(previous)!=1345 or len(former)!=1345:raise AssertionError("original archive missing")
    reference=json.loads((BASE/"RESULT.json").read_text())
    group=pred.groupby("block",sort=True)
    features=[]
    for k,b in enumerate(ids):
        rows=group.get_group(b).copy()
        asof=pd.Timestamp(signals[b*K])
        if str(asof.date())!=rows.signal.iloc[0]:
            raise AssertionError("Model and archived signal asof drift")
        features.append(strictly_asof_state(
            C,roster,rows,asof,chosen["F3"][k],chosen["H1"][k]))
    X=np.vstack(features)
    future_f3=np.diff(np.log(previous.F3.to_numpy(float)[::K]))
    future_h1=np.diff(np.log(previous.H1.to_numpy(float)[::K]))
    diff=future_f3-future_h1
    meta=online_model_predictions(X,diff,days,signals,ids)
    for idx,f in enumerate(FEATURES):meta[f]=X[:,idx]
    strategies={}
    for k,b in enumerate(ids):
        f3=chosen["F3"][k];h1=chosen["H1"][k];h3=chosen["H3"][k]
        weights={
            "F3":monthly_weights([("F3",1.,f3)]),
            "H1":monthly_weights([("H1",1.,h1)]),
            "H3":monthly_weights([("H3",1.,h3)]),
            "STATIC_F3_H1_50":monthly_weights([("F3",.5,f3),("H1",.5,h1)])}
        for full,key in (
            ("J1_SCORE_DIFFERENCE_RULE","J1"),
            ("J2_ONLINE_RIDGE_PROB","J2"),
            ("J3_ONLINE_ANALOG_SIGN","J3")):
            wf=float(meta.loc[k,key+"_weight_F3"])
            weights[full]=monthly_weights([("F3",wf,f3),("H1",1-wf,h1)])
        for key,val in weights.items():
            strategies.setdefault(key,[]).append(val)
    curve={};results={}
    window=days[ids[0]*K:(ids[-1]+1)*K+1]
    for name in ARM_NAMES:
        w,t=trade_policy(strategies[name],O,days,ids,list(roster.ticker))
        if name in ("F3","H1","H3","STATIC_F3_H1_50"):
            err=float(np.max(np.abs(w-previous[name].to_numpy(float))))
            if err>1e-9:raise AssertionError("Frozen prior share wealth parity "+name+" "+str(err))
        curve[name]=w
        results[name]=metrics(w,window,t)
        print("T149J_META_ECONOMIC_POLICY",name,
              json.dumps(results[name]),flush=True)
    # Confirm additional old adversarial comparator complete, but NEVER promote
    # based on a known posthoc 29.38%-CAGR ticker cherry pick.
    other=former.OIL_VS_GROWTH_63.to_numpy(float)
    oldresult=reference["portfolio_results"]["STATIC_F3_H1_50"]["cagr"]
    if abs(results["STATIC_F3_H1_50"]["cagr"]-oldresult)>1e-10:
        raise AssertionError("Original costed 50/50 benchmark changed")
    past_meta=previous.ONLINE_RIDGE_GATE.to_numpy(float)
    scalar=np.std(diff)
    proper={}
    warm=(meta.n_matured_expert_spreads>=MIN_MATURE).to_numpy()
    assert warm.sum()>30
    yy=diff[warm]
    prior=meta.matured_delta_prior.to_numpy(float)[warm]
    y_pos=(yy>0).astype(float)
    oldprob=meta.online_sign_prior.to_numpy(float)[warm]
    for key in ("J2","J3"):
        predicted=meta.loc[warm,key+"_predicted_signed_excess"].to_numpy(float)
        postprob=meta.loc[warm,key+"_forecast_sign_prob"].to_numpy(float)
        uplift=(yy-prior)**2-(yy-predicted)**2
        brier_uplift=(y_pos-oldprob)**2-(y_pos-postprob)**2
        proper[key]=dict(test_n=int(warm.sum()),
            MSE=float(np.mean((yy-predicted)**2)),
            matured_prior_MSE=float(np.mean((yy-prior)**2)),
            MSE_improvement_vs_prior_ci=ci_diff(uplift,SEED+31),
            positive_sign=prob_brier(y_pos,postprob),
            online_prior_sign=prob_brier(y_pos,oldprob),
            sign_brier_improvement_ci=ci_diff(brier_uplift,SEED+32),
            sign_accuracy=float(np.mean((postprob>=.5)==(yy>0))),
            fraction_signal_switches=float(np.mean(
                meta.loc[warm,key+"_weight_F3"].to_numpy(float)!=.5)),
            prediction_vs_realized_corr=float(np.corrcoef(predicted,yy)[0,1]))
    net={m:np.diff(np.log(c[::K])) for m,c in curve.items()}
    comparator={
        "OIL_VS_GROWTH_63":np.diff(np.log(other[::K])),
        "OLD_ONLINE_RIDGE_GATE":np.diff(np.log(past_meta[::K]))}
    for name in comparator:
        m=comparator[name]
        results[name]=metrics(other if name=="OIL_VS_GROWTH_63" else past_meta,window,
            {"note":"Archived control with existing trade fees"})
    paired={};gates={}
    reference50=results["STATIC_F3_H1_50"]
    years=np.asarray([pd.Timestamp(signals[b*K]).year for b in ids])
    for name in ARM_NAMES[4:]:
        a=net[name];base=net["STATIC_F3_H1_50"]
        dif=a-base
        paired[name]=dict(
            vs_static50=ci_diff(dif,SEED+44),
            vs_f3=ci_diff(a-net["F3"],SEED+45),
            vs_h1=ci_diff(a-net["H1"],SEED+46),
            number_months_better_than_50=int(np.sum(dif>0)),
            early_2021_2023_mean_gain=float(np.mean(dif[years<=2023])),
            late_2024_2026_mean_gain=float(np.mean(dif[years>=2024])))
        valid_predictor=(True if name=="J1_SCORE_DIFFERENCE_RULE" else
            (proper["J2" if name.startswith("J2") else "J3"]
             ["MSE_improvement_vs_prior_ci"]["block3_95pct"][0]>0 and
             proper["J2" if name.startswith("J2") else "J3"]
             ["sign_brier_improvement_ci"]["block3_95pct"][0]>0))
        gates[name]=bool(valid_predictor and
            paired[name]["vs_static50"]["block3_95pct"][0]>0 and
            results[name]["cagr"]>reference50["cagr"] and
            results[name]["maxdd_daily_open"]>=reference50["maxdd_daily_open"] and
            results[name]["es5_daily"]>=reference50["es5_daily"] and
            paired[name]["early_2021_2023_mean_gain"]>0 and
            paired[name]["late_2024_2026_mean_gain"]>0)
    regime=[]
    for year in sorted(set(years)):
        idx=years==year
        monthly={"year":int(year),"anchors":int(idx.sum())}
        for m in ARM_NAMES:
            monthly[m+"_mean_monthly_net_log"]=float(net[m][idx].mean())
        regime.append(monthly)
    for m in ARM_NAMES:
        meta["net_monthly_log_"+m]=net[m]
        meta["positions_"+m]=[len(w) for w in strategies[m]]
    meta.to_csv(out/"FROZEN_64_ASOF_EXPERT_RELATIVE_FEATURES_PROB_AND_DECISIONS.csv",index=False)
    df=pd.DataFrame({"day":window})
    for m,w in curve.items():df[m]=w
    df["OIL_VS_GROWTH_63"]=other
    df["OLD_ONLINE_RIDGE_GATE"]=past_meta
    df.to_csv(out/"COSTED_DAILY_PORTFOLIOS_AND_KNOWN_CONTROLS.csv",index=False)
    result=dict(status="ORIGINAL149_RELATIVE_EXPERT_UTILITY_META_TEST_COMPLETED",
        original_etfs=149,original_universe_sha=sha(SRC/"universe.csv"),
        total_21day_anchor_periods=64,test_149_etf_model_signals_from_frozen_archive=9536,
        input_10_asof_features=list(FEATURES),
        minimum_fully_matured_meta_training_samples=MIN_MATURE,
        strict_full_one_open_period_label_embargo=True,
        no_expost_selection_of_market_states=True,
        all_original_daily_wealth_paths_replayed_within_1e_minus_9=True,
        same_next_open_cash_self_funding_and_10bp_each_side=True,
        no_forecaster_training_or_hyperparam_tuning_on_future_labels=True,
        portfolio_metrics=results,
        signed_relative_advantage_predictive_proper_score=proper,
        matched_64_anchor_paired_economic_statistics=paired,
        declared_joint_skill_and_economic_gates=gates,
        year_condition_diagnostics=regime,
        original_50_50_reference=result if False else reference50,
        no_live_or_point_in_time_validation=True,
        experiment_reuses_heavily_mined_2021_2026_historical_cohort=True,
        _not_new_causal_market_information=True,
        warnings=["Only 64 monthly chronological observations; first 19 are meta warmup",
           "No independent proper prospective test, not a 30%-CAGR claimed strategy",
           "Original 149 selected from survivor USD ETF universe and prices retro-adjusted",
           "Residual/factor distributional expert scores have different non-calibrated units",
           "One-open maturity embargo conservatively forbids just finished month label",
           "Probabilistic Normal interpretation is a convenience; requires ex-ante calibration",
           "Historical portfolio log spread is not identical to payoff for mixed book",
           "True euro costs, spreads, taxes, ETF issuer holdings vintages not verified"])
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("T149J_FINAL_METAMODEL_RESULT "+json.dumps(result,allow_nan=False),flush=True)
if __name__=="__main__":main()
