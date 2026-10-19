#!/usr/bin/env python3
"""Original149 K1 is a risk model ABOVE frozen F3/H1 selectors, not a new selector.

No new model fit. F3/H1 names immutable. 51 K1 tail forecasts and original
64 21-session trading blocks. Genuine next-open cash-funded positions.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from oasis149.canonical import sha,SRC
from research_reset.predict149.complementarity.run import (
    from_archive,monthly_weights,trade_policy,metrics,bootstrap,K)
ROOT=Path(__file__).resolve().parents[3]
FROZEN=ROOT/"research_reset/predict149/walkforward_stacking/results"
PRIOR=ROOT/"research_reset/predict149/complementarity/results"
WARMUP=13
SEED=20261019
N_MONTHS=64
BASIS=("F3","H1","H3","B0_STATIC_50")
CHALLENGERS=("L1_WITHIN_BASKET_DOWNTAIL",
             "L2_EXPERT_TAIL_BUDGET","L3_BOTH_LEVELS")
CONTROL=("L0_PRIOR_ONLY_NEGATIVE_CONTROL","L4_REVERSED_RISK_FALSIFIER")
ARMS=BASIS+CHALLENGERS+CONTROL

def load_archive():
    archive,old,roster,O,C,days,signals,ids,selected=from_archive()
    f=pd.read_csv(FROZEN/"ALL_9536_PREQUENTIAL_STACKING_FORECASTS.csv")
    if len(f)!=9536 or f.block.nunique()!=64:
        raise AssertionError("Not original149 frozen stacking K1 predictions")
    if set(f.columns).isdisjoint({"P_DOWN5","NULL_DOWN5","event_down","is_model_warmup"}):
        raise AssertionError("Missing real K1 predictions")
    if not {"block","ticker","P_DOWN5","NULL_DOWN5","event_down",
            "future_log","future_excess","is_model_warmup",
            "latest_training_maturity","signal"}<=set(f):
        raise AssertionError("Stacking output lacked relevant evidence")
    if f.groupby("block").size().ne(149).any():
        raise AssertionError("F3/H1 current cohort changed")
    if set(f.block.unique())!=set(ids):
        raise AssertionError("Evaluation signal dates changed")
    assert sha(SRC/"universe.csv")==json.loads(
        (FROZEN/"RESULT.json").read_text())["source_roster_sha"]
    if f[["block","ticker"]].duplicated().any():
        raise AssertionError("Duplicate monthly ETF prediction")
    for k,b in enumerate(ids):
        sub=f[f.block==b]
        if sub.signal.nunique()!=1 or sub.signal.iloc[0]!=str(
               pd.Timestamp(signals[b*K]).date()):
            raise AssertionError("As-of signal date changed")
        if k<WARMUP:
            if not sub.is_model_warmup.astype(bool).all():
                raise AssertionError("K1 model trained too early")
        else:
            if sub.is_model_warmup.astype(bool).any():
                raise AssertionError("Unexpected K1 warm-up after 13 months")
            if (pd.to_datetime(sub.latest_training_maturity)>=pd.Timestamp(
                  signals[b*K])).any():
                raise AssertionError("Future labels used in K1 estimate")
            if not np.isfinite(sub[["P_DOWN5","NULL_DOWN5"]].to_numpy(float)).all():
                raise AssertionError("Nonfinite K1 posterior/prior")
            if not ((sub.P_DOWN5>0)&(sub.P_DOWN5<1)).all():
                raise AssertionError("Bad K1 tail probability")
            if not ((sub.NULL_DOWN5>0)&(sub.NULL_DOWN5<1)).all():
                raise AssertionError("Bad K1 training prior probability")
    oldwealth=pd.read_csv(PRIOR/"EXPERTS_AND_REAL_COSTED_MIXTURES_DAILY.csv")
    if len(oldwealth)!=1345:raise AssertionError("Original baseline source lost")
    return f,roster,O,C,days,signals,ids,selected,oldwealth

def basket_tilt(names,prob):
    """Keep all FIVE chosen names, risk redistribute only, no replacements."""
    v=np.asarray([prob[t] for t in names],float)
    if len(v)!=5 or np.any(v<=0) or not np.isfinite(v).all():
        raise AssertionError("bad basket risk")
    ratio=np.clip(v.mean()/v,.5,1.5)
    weights=ratio/ratio.sum()
    if abs(weights.sum()-1)>1e-12:raise AssertionError("unfunded basket")
    return dict(zip(names,map(float,weights)))

def merge_baskets(F,H,prob,within,expert,reverse=False):
    original=dict(prob)
    if reverse:
        values=np.asarray([prob[t] for t in set(F+H)],float)
        lo=float(values.min());hi=float(values.max())
        risk={t:max(1e-6,hi+lo-prob[t]) for t in prob}
    else:risk=original
    fp=float(np.mean([risk[t] for t in F]))
    hp=float(np.mean([risk[t] for t in H]))
    F_share=float(np.clip(.5+2*(hp-fp),.25,.75)) if expert else .5
    componentF=basket_tilt(F,risk) if within else {t:.2 for t in F}
    componentH=basket_tilt(H,risk) if within else {t:.2 for t in H}
    out={}
    for t,v in componentF.items():out[t]=out.get(t,0)+F_share*v
    for t,v in componentH.items():out[t]=out.get(t,0)+(1-F_share)*v
    assert len(out)<=10 and abs(sum(out.values())-1)<1e-12
    assert set(out)==set(F+H)
    return out,F_share,fp,hp

def aggregate_selected_scores(sub,F,H):
    """Use 50:50 F3/H1 equal shares; repeated ETF overlaps count twice."""
    at=sub.set_index("ticker")
    selected=F+H
    return {
        "tickers":selected,
        "p":[float(at.loc[t,"P_DOWN5"]) for t in selected],
        "null":[float(at.loc[t,"NULL_DOWN5"]) for t in selected],
        "event":[float(at.loc[t,"event_down"]) for t in selected],
        "absolute_event":[float(at.loc[t,"future_log"]<-.05) for t in selected]}

def grouped_brier(anchor_records):
    """Average each date equally, not 510 correlated ETF-name rows as iid."""
    test=anchor_records[anchor_records["warmup"]==False].copy()
    assert len(test)==51
    scores={}
    for label in ("relative","absolute"):
        col=("prob_error_gain" if label=="relative" else "nominal_error_gain")
        vals=test[col].to_numpy(float)
        scores[label]=dict(mean=float(vals.mean()),ci95=ci(vals,SEED+91))
    return scores

def ci(series,seed=SEED,rep=2500):
    x=np.asarray(series,float)
    n=len(x)
    if n<25:raise AssertionError("not enough independent months")
    r=np.random.default_rng(seed)
    res=[]
    for _ in range(rep):
        ix=[]
        while len(ix)<n:
            j=int(r.integers(n))
            ix.extend((j+d)%n for d in range(3))
        res.append(float(np.mean(x[np.asarray(ix[:n],int)])))
    return np.quantile(res,[.025,.975]).tolist()

def per_period_event_risk(frame,F,H):
    score=aggregate_selected_scores(frame,F,H)
    p=np.asarray(score["p"],float)
    q=np.asarray(score["null"],float)
    e=np.asarray(score["event"],float)
    absolute=np.asarray(score["absolute_event"],float)
    # Fixed 50:50 double-counting overlap = true economic weight at baseline.
    brier=float(np.mean((q-e)**2-(p-e)**2))
    loss=lambda x,y: -y*np.log(np.clip(x,1e-6,1-1e-6))-(
                             1-y)*np.log(1-np.clip(x,1e-6,1-1e-6))
    return dict(
        selected_relative_negative_tail_event_rate=float(e.mean()),
        selected_nominal_negative_tail_event_rate=float(absolute.mean()),
        selected_pred_pdown=float(p.mean()),
        selected_prior_pdown=float(q.mean()),
        prob_error_gain=brier,
        logloss_gain=float(np.mean(loss(q,e)-loss(p,e))),
        nominal_error_gain=float(np.mean((q-absolute)**2-(p-absolute)**2)),
        # Mechanism must work within the two frozen SELECTED top5s,
        # not only among generic unchosen junk tickers.
        selected_probability_discrimination=float(
            np.mean([(p[i]-p[j])*(e[i]-e[j])>0
                     for i in range(10) for j in range(i+1,10)
                     if (e[i]-e[j])!=0])) if
            len([(i,j) for i in range(10) for j in range(i+1,10)
                 if (e[i]-e[j])!=0])>0 else None)

def run(outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=False)
    forecasts,roster,O,C,days,signals,ids,selected,ref=load_archive()
    weights={s:[] for s in ARMS}
    history=[]
    control_audit=[]
    for k,b in enumerate(ids):
        f=selected["F3"][k];h=selected["H1"][k]
        s=forecasts[forecasts.block==b]
        p=(dict(zip(s.ticker,s.P_DOWN5.to_numpy(float))) if k>=WARMUP
            else None)
        pri=(dict(zip(s.ticker,s.NULL_DOWN5.to_numpy(float))) if k>=WARMUP
             else None)
        base=monthly_weights([("F3",.5,f),("H1",.5,h)])
        weights["F3"].append(monthly_weights([("F3",1.,f)]))
        weights["H1"].append(monthly_weights([("H1",1.,h)]))
        weights["H3"].append(monthly_weights([("H3",1.,selected["H3"][k])]))
        weights["B0_STATIC_50"].append(base)
        a=dict(block=b,k=k,signal=str(pd.Timestamp(signals[b*K]).date()),
               before_next_open=str(pd.Timestamp(days[b*K]).date()),
               warmup=k<WARMUP,F3_tick=";".join(f),H1_tick=";".join(h))
        if k<WARMUP:
            for m in CHALLENGERS+CONTROL:
                weights[m].append(base.copy())
                a[m+"_F3_fraction"]=.5
            a.update(selected_pred_pdown=None,selected_prior_pdown=None,
                prob_error_gain=None,logloss_gain=None,
                nominal_error_gain=None)
        else:
            ev=per_period_event_risk(s,f,h)
            a.update(ev)
            for m in CHALLENGERS+CONTROL:
                use_prior=m=="L0_PRIOR_ONLY_NEGATIVE_CONTROL"
                w,Ffrac,fp,hp=merge_baskets(
                    f,h,pri if use_prior else p,
                    within=m in ("L1_WITHIN_BASKET_DOWNTAIL",
                                 "L3_BOTH_LEVELS",
                                 "L0_PRIOR_ONLY_NEGATIVE_CONTROL",
                                 "L4_REVERSED_RISK_FALSIFIER"),
                    expert=m in ("L2_EXPERT_TAIL_BUDGET",
                                 "L3_BOTH_LEVELS",
                                 "L0_PRIOR_ONLY_NEGATIVE_CONTROL",
                                 "L4_REVERSED_RISK_FALSIFIER"),
                    reverse=m=="L4_REVERSED_RISK_FALSIFIER")
                weights[m].append(w)
                a[m+"_F3_fraction"]=Ffrac
                a[m+"_meanFdown"]=fp
                a[m+"_meanHdown"]=hp
                a[m+"_max_weight"]=float(max(w.values()))
                a[m+"_n_positions"]=len(w)
        if weights["L0_PRIOR_ONLY_NEGATIVE_CONTROL"][-1]!=base:
            raise AssertionError("Historical K1 prior-only negative-control changed 50:50")
        history.append(a)
    months=pd.DataFrame(history)
    window=days[ids[0]*K:(ids[-1]+1)*K+1]
    returninfo={}
    curves={}
    for m in ARMS:
        w,turn=trade_policy(weights[m],O,days,ids,list(roster.ticker))
        if m in BASIS:
            old_col=m if m!="B0_STATIC_50" else "STATIC_F3_H1_50"
            if np.max(abs(w-ref[old_col].to_numpy(float)))>1e-9:
                raise AssertionError("Not identical to frozen F3/H1/H3/50:50 "+m)
        if m=="L0_PRIOR_ONLY_NEGATIVE_CONTROL":
            if np.max(abs(w-curves["B0_STATIC_50"]))>1e-12:
                raise AssertionError("Prior-only negative control violated identical cash path")
        curves[m]=w
        returninfo[m]=metrics(w,window,turn)
        print("T149L_K1_OVERLAY_PORTFOLIO",m,
              json.dumps(returninfo[m],allow_nan=False),flush=True)
    # Full period includes 13 deliberately original static warmup months:
    # report post-warmup returns separately for economic fairness.
    warm_start=WARMUP*K
    after={}
    for m in ARMS:
        x=curves[m][warm_start:]
        wt=window[warm_start:]
        after[m]=metrics(x,wt,dict(postwarmup_only=True))
    prop=grouped_brier(months)
    relscores=months.loc[months.warmup==False]
    assert len(relscores)==51 and not relscores.prob_error_gain.isna().any()
    paired={}
    gates={}
    base=returninfo["B0_STATIC_50"]
    refnet=np.diff(np.log(curves["B0_STATIC_50"][::K]))
    refnet_active=refnet[WARMUP:]
    years=np.asarray([pd.Timestamp(signals[b*K]).year for b in ids])
    for m in CHALLENGERS:
        net=np.diff(np.log(curves[m][::K]))
        dif=net-refnet
        direct=(net[WARMUP:]-refnet_active)
        paired[m]=dict(
            full64_mean_log_gain=float(dif.mean()),
            full64_ci=ci(dif,SEED+8),
            mature51_mean_log_gain=float(direct.mean()),
            mature51_ci=ci(direct,SEED+9),
            2021_2023_month_log_gain=float(np.mean(dif[years<=2023])),
            2024_2026_month_log_gain=float(np.mean(dif[years>=2024])),
            good_months=int((dif>0).sum()))
        for key in ("2021_2023_month_log_gain","2024_2026_month_log_gain"):
            if not np.isfinite(paired[m][key]):raise AssertionError("Invalid year split")
        yes=(paired[m]["mature51_ci"][0]>0 and
             paired[m]["full64_ci"][0]>0 and
             prop["relative"]["ci95"][0]>0 and
             returninfo[m]["cagr"]>=base["cagr"] and
             returninfo[m]["maxdd_daily_open"]>=base["maxdd_daily_open"] and
             returninfo[m]["es5_daily"]>=base["es5_daily"] and
             paired[m]["2021_2023_month_log_gain"]>0 and
             paired[m]["2024_2026_month_log_gain"]>0)
        if m=="L3_BOTH_LEVELS":
            alt=np.diff(np.log(curves["L4_REVERSED_RISK_FALSIFIER"][::K]))
            versus=net-alt
            paired[m]["against_reversed_mean"]=float(versus.mean())
            paired[m]["against_reversed_ci"]=ci(versus,SEED+10)
            yes=yes and paired[m]["against_reversed_ci"][0]>0
        gates[m]=bool(yes)
    dailyframe=pd.DataFrame({"day":window})
    for m in ARMS:dailyframe[m]=curves[m]
    dailyframe.to_csv(out/"K1_TRUE_CASH_FUNDED_DAILY_EQUITY.csv",index=False)
    # Explicit saved holdings and weights for posthoc audit.
    chosen=[]
    for k,b in enumerate(ids):
        for name in ARMS:
            for t,w in weights[name][k].items():
                chosen.append(dict(block=b,signal=months.loc[k,"signal"],
                     policy=name,ticker=t,notional_weight=float(w)))
    pd.DataFrame(chosen).to_csv(out/"ALL_64_ASOF_POSITIONS_WEIGHTS.csv",index=False)
    months.to_csv(out/"ALL_64_K1_RISK_DECISION_AND_OUTCOME.csv",index=False)
    records=dict(status="ORIGINAL149_K1_DOWNSIDE_RISK_OVERLAY_RESULTS_COMPLETE",
       exact_original_149_universe_sha=sha(SRC/"universe.csv"),
       n_original_etfs=149,n_months=64,n_postwarmup_k1_months=51,
       n_full_daily_open_wealth_points=1345,
       source_classifier_retrained=False,
       f3_h1_h3_exact_original_holdings_unchanged=True,
       forecasts_and_meta_labels_asof_strict=True,
       actual_underlying_share_costs_10bps_per_buy_and_sale=True,
       prior_only_must_exactly_replay_static=True,
       trained_K1_target="P(21d benchmark relative log excess < -5pct)",
       actual_portfolio_loss_is_NOT_equivalent_to_K1_label=True,
       arms_full_period=returninfo,
       arms_postwarmup=after,
       conditional_K1_selected_held_event_skill_vs_matured_prior=prop,
       paired_net_monthly_and_reverse_controls=paired,
       strict_precommitted_risk_and_return_gates=gates,
       no_independent_out_of_sample_validation=True,
       warnings=["149 historical U.S. survivor-selected tickers repeatedly investigated",
          "51 K1 test anchor months; hundreds of held events share common market factor",
          "K1 predicts underperformance vs 60/40, not absolute ETF loss or intramonth drawdown",
          "ES of daily Open returns estimated with no broker spread/EUR FX and fixed 10bp cost",
          "Neither return enhancement nor 30% CAGR is guaranteed; no production deployment"])
    (out/"RESULT.json").write_text(json.dumps(records,allow_nan=False,indent=2)+"\n")
    print("T149L_K1_RISK_OVERLAY_FINAL",json.dumps(records,allow_nan=False),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    run(p.parse_args().out)
