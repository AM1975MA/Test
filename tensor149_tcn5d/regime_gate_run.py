"""Strictly causal 2020–26 RMT-vs-basic HMM regime gate, frozen Original149 experts.

Inputs: ALREADY OOS weekly per-ETF TinyTCN(B) and XGB125(E) scores, frozen
momentum21 values. Gate receives only matured prior weekly expert returns.
No expert retraining, no target data in market regime detection.
"""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import softmax
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM

from tensor149_tcn5d.features import load_frozen
from tensor149_tcn5d.regime_features import (
    weekly_regime_features,forward_hmm_probabilities,BASE,ALL)
from tensor149_tcn5d.run import HORIZON,nav_path,SEED

EXPERTS=("MOM21","B_DAILY_BASE","E_XGB_BASE")
STRATEGIES=EXPERTS+("STATIC_EQUAL","TRAILING_ONLY","BASIC_HMM","RMT_HMM","SIMPLE_BUCKET")
HALF_LIFE_WEEKS=52.
HISTORY_WEEKS=104
SHRINK_PSEUDO_COUNT=24.
TEMPERATURE=0.01
ADAPTIVE_MIX=0.5
FIRST_EVAL_YEAR=2020
LAST_EVAL_YEAR=2026

def _result(root):
    files=list(Path(root).rglob("RESULT.json"))
    if len(files)!=1:raise ValueError(f"Expected exactly one RESULT.json in {root}, got {len(files)}")
    path=files[0]
    return json.loads(path.read_text()),path.parent

def load_weekly_data(baseline,tnn,xgb,mats,source_sha):
    ba,bp=_result(baseline)
    nb,npth=_result(tnn)
    xb,xpath=_result(xgb)
    if ba["status"]!="TENSOR149_TCN5D_EXPERIMENT_COMPLETE":raise ValueError("Invalid original baseline")
    if ba["original_roster_sha256"]!=source_sha:raise ValueError("Original baseline roster mismatch")
    for a,v in ((nb,"B_DAILY_BASE"),(xb,"E_XGB_BASE")):
        if a.get("status")!="R1R2_DAILY_ABLATION_COMPLETE" or a["variant"]!=v:
            raise ValueError("Missing immutable original expert "+v)
        if a["original149_roster_sha256"]!=source_sha or a["oos_weekly_dates"]!=476:
            raise ValueError("Expert roster or weekly dates wrong")
    b=pd.read_parquet(npth/"ALL_OOS_SCORES.parquet")
    x=pd.read_parquet(xpath/"ALL_OOS_SCORES.parquet")
    cols=("date","t_idx","ticker","ticker_id")
    b=b.sort_values(list(cols)).reset_index(drop=True)
    x=x.sort_values(list(cols)).reset_index(drop=True)
    if not b[list(cols)].equals(x[list(cols)]):raise ValueError("Expert ETF rows not same week/eligible candidates")
    for q in ("realized_fwd_percentile_centered","realized_future_5d_return"):
        if not np.allclose(b[q],x[q],atol=1e-7,rtol=1e-6,equal_nan=True):
            raise ValueError("Future label mismatch "+q)
    frozen=pd.read_csv(bp/"OOS_WEEKLY_PREDICTIONS.csv")
    frozen=frozen[frozen.model=="MOM21"].sort_values("date")
    if b.date.nunique()!=476 or b.date.drop_duplicates().tolist()!=frozen.date.tolist():
        raise ValueError("Wrong original OOS date support")
    bon=pd.read_csv(npth/"OOS_WEEKLY_SELECTIONS.csv").set_index("date")
    xon=pd.read_csv(xpath/"OOS_WEEKLY_SELECTIONS.csv").set_index("date")
    frozen=frozen.set_index("date")
    close=mats["Close"]
    mom21=close.pct_change(21,fill_method=None)
    dates=close.index
    names=list(close.columns)
    output=[]
    for date,fr in b.groupby("date",sort=True):
        fr=fr.sort_values("ticker_id")
        xfr=x.loc[fr.index] # both sorted same key, preserving identical rows
        ti=int(fr.t_idx.iloc[0])
        if not (fr.t_idx==ti).all() or date!=str(dates[ti].date()):
            raise ValueError("Misaligned next-day Open execution")
        ids=fr.ticker_id.to_numpy(dtype=int)
        if names!=list(sorted(names)) or [names[k] for k in ids]!=fr.ticker.tolist():
            raise ValueError("Original ticker id mismatch")
        outcome=fr.realized_future_5d_return.to_numpy(float)
        mom=mom21.iloc[ti,ids].to_numpy(float)
        preds=dict(MOM21=mom,B_DAILY_BASE=fr.pred_score.to_numpy(float),
                   E_XGB_BASE=xfr.pred_score.to_numpy(float))
        if any((not np.isfinite(sc).all()) for sc in preds.values()):
            raise ValueError("Non-finite as-of expert score")
        ranks=np.column_stack([pd.Series(sc).rank(method="average",pct=True).to_numpy()-.5
                               for sc in (preds[k] for k in EXPERTS)])
        winners=np.argsort(-outcome,kind="stable")[:5]
        native={}
        for j,k in enumerate(EXPERTS):
            picks=np.argsort(-preds[k],kind="stable")[:5]
            native[k]=",".join(names[ids[p]] for p in picks)
            want=frozen.loc[date,"selected"] if k=="MOM21" else (
                 bon.loc[date,"selected"] if k=="B_DAILY_BASE" else xon.loc[date,"selected"])
            if native[k]!=want:
                raise ValueError(f"Experts reconstituted Top5 mismatch {date}, {k}, got={native[k]}, expected={want}")
        portfolio_returns=np.asarray([np.mean(outcome[np.argsort(-preds[k],kind="stable")[:5]]) for k in EXPERTS])
        output.append(dict(date=date,t_idx=ti,ids=ids,tickers=fr.ticker.tolist(),
                 label=fr.realized_fwd_percentile_centered.to_numpy(float),
                 actual=outcome,scores=ranks,ret_experts=portfolio_returns,
                 oracle=set(winners.tolist()),native=native,
                 exit_date=dates[ti+HORIZON+1]))
    return output,dict(roster_sha=source_sha,week_count=len(output),
         base_frozen_status=ba["status"],expert_variants=[nb["variant"],xb["variant"]],
         all_candidate_rows=len(b))

def weight_formula(mu):
    x=np.asarray(mu,dtype=float)
    if x.shape!=(3,) or not np.isfinite(x).all():raise ValueError("Bad expert return expectancy")
    w=(1-ADAPTIVE_MIX)/3+ADAPTIVE_MIX*softmax((x-x.mean())/TEMPERATURE)
    if not np.isclose(w.sum(),1.,atol=1e-12):raise ValueError("Nonunit weight")
    return w

def history_before(weeks,week_pos,raw_dates):
    current=weeks[week_pos]
    # A training payoff exits after open(t+6). It must have actually happened BEFORE today's signal close(t).
    return [j for j in range(week_pos) if weeks[j]["exit_date"]<raw_dates[current["t_idx"]]][-HISTORY_WEEKS:]

def historical_mu(weeks,history,week_pos,state_history=None,state_now=None):
    if len(history)<80:raise ValueError("Insufficient matured expert OOS meta-history")
    age=np.arange(len(history)-1,-1,-1,dtype=float)
    decay=np.exp(-np.log(2)*age/HALF_LIFE_WEEKS)
    ret=np.stack([weeks[j]["ret_experts"] for j in history])
    general=np.sum(decay[:,None]*ret,axis=0)/decay.sum()
    if state_history is None:return general
    similarities=np.asarray(state_history,dtype=float)@np.asarray(state_now,dtype=float)
    if similarities.ndim!=1 or len(similarities)!=len(history):raise ValueError("Invalid regime-match dimensions")
    similarities=np.maximum(similarities,0.)
    wg=decay*similarities
    return (np.sum(wg[:,None]*ret,axis=0)+SHRINK_PSEUDO_COUNT*general)/(wg.sum()+SHRINK_PSEUDO_COUNT)

def regime_state_for_year(regime,year,all_features):
    start=f"{year}-01-01"
    training=all_features.loc[all_features.date<start].copy()
    if len(training)<100:raise ValueError("Insufficient available as-of market state training")
    zfields=BASE if regime=="BASIC_HMM" else ALL
    scaler=StandardScaler().fit(training[list(zfields)].to_numpy(float))
    fit_data=np.clip(scaler.transform(training[list(zfields)].to_numpy(float)),-5,5)
    m=GaussianHMM(n_components=3,covariance_type="diag",n_iter=80,
                  min_covar=.02,random_state=SEED,implementation="log")
    m.fit(fit_data)
    # Transform full as-of date sequence but compute posterior ONLY forward,
    # so state probabilities at t cannot respond to future changes.
    current=all_features.loc[all_features.date<=f"{year}-12-31"]
    allscaled=np.clip(scaler.transform(current[list(zfields)].to_numpy(float)),-5,5)
    probs=forward_hmm_probabilities(m,allscaled)
    if not (np.isfinite(probs).all() and np.allclose(probs.sum(axis=1),1.,atol=1e-7)):
        raise ValueError("HMM nonprobabilistic state")
    p=dict(zip(current.date,probs))
    return p,dict(year=year,regime=regime,
             training_state_weeks=len(training),
             maximum_state_fit_date=str(training.date.iloc[-1]),
             converged=bool(m.monitor_.converged),
             occupancies=np.mean(probs,axis=0).tolist())

def bucket_state_for_year(year,states):
    before=states.loc[states.date<f"{year}-01-01"]
    v0=float(before.spy_vol21.median())
    c0=float(before.mean_corr126.median())
    # no use of current or OOS year to set thresholds
    frame=states[states.date<=f"{year}-12-31"].copy()
    bucket=(frame.spy_vol21.to_numpy(float)>v0).astype(int)*2+(
        frame.mean_corr126.to_numpy(float)>c0).astype(int)
    p=dict(zip(frame.date,np.eye(4)[bucket]))
    return p,dict(year=year,regime="SIMPLE_BUCKET",threshold_vol=v0,
           threshold_corr=c0,training_state_weeks=len(before))

def ci5(x,n_boot=2000,seed=20261020):
    xx=np.asarray(x,dtype=float);n=len(xx)
    rng=np.random.default_rng(seed)
    means=np.empty(n_boot,dtype=float)
    for j in range(n_boot):
        ix=(rng.integers(0,n,size=int(np.ceil(n/5)))[:,None]+np.arange(5))%n
        means[j]=xx[ix.reshape(-1)[:n]].mean()
    return list(map(float,np.quantile(means,[.025,.975])))

def run(args):
    raw_mats,raw_audit,source_sha=load_frozen(args.raw)
    dates=raw_mats["Close"].index
    weeks,audit=load_weekly_data(args.baseline,args.tnn,args.xgb,raw_mats,source_sha)
    regs=weekly_regime_features(raw_mats["Close"])
    reg_lookup=dict(zip(regs.date,regs.t_idx))
    all_test=[q for q in weeks if q["date"]>=f"{FIRST_EVAL_YEAR}-01-01"]
    if len(all_test)<280 or len(all_test)>380:raise ValueError("Unexpected 2020-26 same date test")
    for q in weeks:
        if q["date"] not in reg_lookup or reg_lookup[q["date"]]!=q["t_idx"]:
            raise ValueError("Regime data not available at date "+q["date"])
    records=[];gate_rows=[];state_folds={}
    for year in range(FIRST_EVAL_YEAR,LAST_EVAL_YEAR+1):
        yh={}
        for regime in ("BASIC_HMM","RMT_HMM"):
            yh[regime],meta=regime_state_for_year(regime,year,regs)
            state_folds[f"{year}_{regime}"]=meta
        yh["SIMPLE_BUCKET"],meta=bucket_state_for_year(year,regs)
        state_folds[f"{year}_SIMPLE_BUCKET"]=meta
        for pos,q in enumerate(weeks):
            if int(q["date"][:4])!=year:continue
            history=history_before(weeks,pos,dates)
            if len(history)<80:raise ValueError("Immature gate history "+q["date"])
            allw={k:np.eye(3)[i] for i,k in enumerate(EXPERTS)}
            allw["STATIC_EQUAL"]=np.ones(3)/3
            mu_trailing=historical_mu(weeks,history,pos)
            allw["TRAILING_ONLY"]=weight_formula(mu_trailing)
            for name in ("BASIC_HMM","RMT_HMM","SIMPLE_BUCKET"):
                states=yh[name]
                if not all(weeks[j]["date"] in states for j in history):
                    raise ValueError("Missing historical filtered state in "+name)
                current_state=states[q["date"]]
                hist_state=np.stack([states[weeks[j]["date"]] for j in history])
                mu=historical_mu(weeks,history,pos,hist_state,current_state)
                allw[name]=weight_formula(mu)
            # same ETF candidate scores and nominal next-open returns for each candidate;
            # real outcomes are read only for retrospective evaluation below, never gate.
            for name,w in allw.items():
                predicted=q["scores"]@w
                chosen=np.argsort(-predicted,kind="stable")[:5]
                actual=np.asarray(q["actual"],dtype=float)
                score_stats=spearmanr(predicted,q["label"]).statistic
                row=dict(date=q["date"],t_idx=int(q["t_idx"]),model=name,
                     n=len(actual),rank_ic=float(score_stats),
                     top5_overlap=float(len(set(chosen)&q["oracle"])/5),
                     top5_mean_future_return=float(actual[chosen].mean()),
                     selected=",".join(q["tickers"][k] for k in chosen),
                     historical_meta_weeks=int(len(history)))
                records.append(row)
                gate_rows.append(dict(date=q["date"],model=name,
                     w_mom=float(w[0]),w_tcn=float(w[1]),w_xgb=float(w[2]),
                     state_prob=(yh[name][q["date"]].tolist() if name in yh else None),
                     historically_best_expert=EXPERTS[int(np.argmax(q["ret_experts"]))],
                     predicted_largest_weight_expert=EXPERTS[int(np.argmax(w))],
                     net_ranking_return=float(actual[chosen].mean())-.002))
        print(json.dumps(dict(year=year,state_training={x:state_folds[f"{year}_{x}"]["training_state_weeks"] for x in
                             ("BASIC_HMM","RMT_HMM","SIMPLE_BUCKET")},status="fold_complete")),flush=True)
    result=pd.DataFrame(records)
    gate=pd.DataFrame(gate_rows)
    for name in STRATEGIES:
        d=result[result.model==name]
        if len(d)!=len(all_test) or d.date.tolist()!=[q["date"] for q in all_test]:
            raise ValueError("Unmatched regime evaluation date support "+name)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    result.to_csv(out/"OOS_WEEKLY_SELECTIONS.csv",index=False)
    gate.to_csv(out/"GATE_WEIGHTS.csv",index=False)
    regs.to_csv(out/"CAUSAL_REGIME_STATE_FEATURES.csv",index=False)
    meta=[]
    curves=[]
    for model in STRATEGIES:
        nav,econ=nav_path(result,dates,raw_mats,model)
        curves.append(nav.rename(model))
        sc=result[result.model==model]
        meta.append(dict(model=model,**econ,
                         mean_rankic=float(sc.rank_ic.mean()),
                         true_top5_overlap=float(sc.top5_overlap.mean()),
                         mean_5day_basket_return=float(sc.top5_mean_future_return.mean())))
    pd.concat(curves,axis=1).to_csv(out/"NET_DAILY_EQUITY.csv",index_label="date")
    perf=pd.DataFrame(meta).set_index("model")
    perf.to_csv(out/"METRICS.csv")
    paired={}
    for challenger in ("TRAILING_ONLY","BASIC_HMM","RMT_HMM","SIMPLE_BUCKET"):
        a=result[result.model==challenger].sort_values("date").reset_index(drop=True)
        paired[challenger]={}
        for reference in ("STATIC_EQUAL","TRAILING_ONLY","BASIC_HMM","MOM21","E_XGB_BASE"):
            if reference==challenger:continue
            b=result[result.model==reference].sort_values("date").reset_index(drop=True)
            paired[challenger][reference]={k:dict(
                   mean_delta=float((a[k]-b[k]).mean()),
                   block95=ci5((a[k]-b[k]).to_numpy(float)))
                     for k in ("rank_ic","top5_overlap","top5_mean_future_return")}
    yearly=[]
    for model,ff in result.groupby("model",sort=False):
        for yy,part in ff.groupby(ff.date.str.slice(0,4)):
            wealth=float(np.prod((1+part.top5_mean_future_return.to_numpy(float))*(1-.002)))
            yearly.append(dict(model=model,year=int(yy),weeks=len(part),
                               costed_weekly_compound_return=wealth-1,
                               mean_rank_ic=float(part.rank_ic.mean())))
    pd.DataFrame(yearly).to_csv(out/"YEARLY_WEEKLY_REPLAY.csv",index=False)
    for name in ("BASIC_HMM","RMT_HMM","SIMPLE_BUCKET"):
        subset=gate[gate.model==name]
        state_folds[f"SUMMARY_{name}"]=dict(weights_mean={k:float(subset[k].mean())
                 for k in ("w_mom","w_tcn","w_xgb")},
                 historical_best_accuracy=float((subset.historically_best_expert==
                    subset.predicted_largest_weight_expert).mean()))
    payload=dict(status="ORIGINAL149_CAUSAL_REGIME_GATE_COMPLETE",
      dates=int(len(all_test)),start=all_test[0]["date"],end=all_test[-1]["date"],
      original_roster_sha=source_sha,same_149_etfs=True,
      three_frozen_oos_experts=True,portfolio_policy="Top5 long only, 20bp full-roundtrip per 5-session hold",
      info_cutoff="features close(t), meta outcomes strict exit before next signal",
      forecast_horizon_sessions=HORIZON,
      HMM_inference="annual trained on past only, Hamilton forward filter, never future smoothed",
      preregistered_constants=dict(half_life_week=HALF_LIFE_WEEKS,history_weeks=HISTORY_WEEKS,
          pseudo_count=SHRINK_PSEUDO_COUNT,temp=TEMPERATURE,adaptive_share=ADAPTIVE_MIX),
      input_audit=audit,state_folds=state_folds,metrics=meta,paired=paired,
      caveat="Retrospective OOS experts and meta OOS 2020-26 are not independent after repeated hypothesis mining of 2017-26. No execution claims.")
    (out/"REPORT.json").write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":payload["status"],"weeks":len(all_test),
        "metrics":[{k:r.get(k) for k in ("model","cagr","maxdd","sharpe",
             "mean_rankic","mean_5day_basket_return","true_top5_overlap")} for r in meta],
        "paired":paired},indent=2),flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",default="evidence_v1/data/original149")
    ap.add_argument("--baseline",required=True)
    ap.add_argument("--tnn",required=True)
    ap.add_argument("--xgb",required=True)
    ap.add_argument("--out",required=True)
    run(ap.parse_args())
