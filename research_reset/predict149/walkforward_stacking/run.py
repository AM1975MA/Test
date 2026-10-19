#!/usr/bin/env python3
"""T149-K: genuinely prequential 149×time ticker ML using F3/H1 predictions.

All base forecasts precomputed as-of Close by earlier frozen models.
Only matured post-entry-open ETF outcomes train stacking. Historical repeated
149 US ETF survivor cohort does NOT demonstrate prospective performance.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingRegressor
from lightgbm import LGBMRanker
from oasis149.canonical import sha,SRC
from research_reset.predict149.complementarity.run import (
    from_archive,monthly_weights,trade_policy,metrics,bootstrap,K)
ROOT=Path(__file__).resolve().parents[3]
PREVIOUS=ROOT/"research_reset/predict149/complementarity/results"
SEED=20261019
TRAIN_MIN_ANCHORS=12
REFIT_EVERY=3
TOP=5
BASIS=("F3","H1","H3","STATIC_F3_H1_50")
ARM_NAMES=BASIS+("EQUAL_RANK_TOP5","K1_SIGNED_TAIL_HEADS",
    "K2_SIGNED_MEAN_GBDT","K3_GRADED_LAMBDARANK",
    "K4_PREDICTED_BASKET_GATE")
FCS=("f3_rank","h1_rank","rank_mean","rank_disagreement",
     "v63_rank","asof_quantile_width_rank")
DIMS=tuple(FCS)+tuple("g"+str(i) for i in range(6))

def prepare_features(frame):
    p=frame.copy()
    required={"block","ticker","signal","maturity","future_excess","future_log",
        "v63","R_Q10","R_Q90","category","B0_F3_FROZEN","H1_FACTOR_ONLY",
        "top15","bottom15"}
    if not required<=set(p):raise AssertionError("Frozen sample missing prequential columns")
    if len(p)!=149*64 or p.groupby("block").size().ne(149).any():
        raise AssertionError("Changed original149 complete evaluation panel")
    roster=tuple(sorted(p.category.unique()))
    if len(roster)!=6:raise AssertionError("original six macroclasses drift")
    p["f3_rank"]=p.groupby("block").B0_F3_FROZEN.rank(pct=True)
    p["h1_rank"]=p.groupby("block").H1_FACTOR_ONLY.rank(pct=True)
    p["rank_mean"]=(p.f3_rank+p.h1_rank)/2
    p["rank_disagreement"]=p.f3_rank-p.h1_rank
    p["v63_rank"]=p.groupby("block").v63.rank(pct=True)
    p["asof_quantile_width_rank"]=(p.R_Q90-p.R_Q10).groupby(
        p.block).rank(pct=True)
    for j,c in enumerate(roster):
        p["g"+str(j)]=(p.category==c).astype(float)
    p["target_signed_clipped"]=p.future_excess.clip(-.20,.20)
    p["event_up"]=(p.future_excess>.03).astype(int)
    p["event_down"]=(p.future_excess<-.05).astype(int)
    # Future relative-return rank labels ONLY accessed after maturity.
    order=p.groupby("block").future_excess.rank(method="first",ascending=False)
    p["future_graded"]=np.select(
        [order<=5,order<=15,order<=30],[3,2,1],default=0).astype(int)
    if not np.isfinite(p[list(DIMS)].to_numpy(float)).all():
        raise AssertionError("Invalid as-of stacking design matrix")
    assert p.groupby("block").future_graded.apply(
        lambda x: tuple(x.value_counts().reindex([3,2,1,0],fill_value=0))).nunique()==1
    return p

def training_rows(p,k,ids):
    """The previous month label is not mature before today's preceding Close."""
    b=ids[k]
    current=p.loc[p.block==b]
    s=pd.Timestamp(current.signal.iloc[0])
    raw=p.loc[pd.to_datetime(p.maturity)<s]
    # This experiment may ONLY meta-learn from the same 64 archived
    # prequential base signals; no synthetic in-sample base predictions.
    historical=set(ids[:k])
    if not set(raw.block.unique())<=historical:
        raise AssertionError("Current or future outcomes used to train meta-model")
    if k>0:
        prior=p[p.block==ids[k-1]]
        if pd.Timestamp(prior.maturity.iloc[0])<s:
            raise AssertionError("Previous just-closed block should be embargoed")
    if len(raw)!=149*len(raw.block.unique()):
        raise AssertionError("Incomplete maturity date per 149 ticker group")
    if len(raw) and pd.to_datetime(raw.maturity).max()>=s:
        raise AssertionError("Immature label acquired")
    if list(sorted(raw.block.unique()))!=ids[:max(0,k-1)]:
        raise AssertionError("Unexpected nonconsecutive mature anchor list")
    return raw,current

def fit_models(train):
    if train.block.nunique()<TRAIN_MIN_ANCHORS:
        raise AssertionError("Insufficient as-of prequential meta training")
    X=train[list(DIMS)].to_numpy(float)
    up=train.event_up.to_numpy(int)
    dn=train.event_down.to_numpy(int)
    if min(up.sum(),len(up)-up.sum(),dn.sum(),len(dn)-dn.sum())<30:
        raise AssertionError("not enough signed event positives and negatives")
    heads={}
    for name,y in (("up",up),("down",dn)):
        model=LogisticRegression(C=.05,max_iter=250,solver="liblinear",
                                 random_state=SEED)
        heads[name]=model.fit(X,y)
    mean=HistGradientBoostingRegressor(loss="squared_error",max_iter=70,
        max_leaf_nodes=5,max_depth=2,min_samples_leaf=100,
        l2_regularization=30,learning_rate=.03,
        random_state=SEED).fit(X,train.target_signed_clipped.to_numpy(float))
    groups=train.groupby("block",sort=True).size().to_numpy(int)
    assert (groups==149).all() and groups.sum()==len(train)
    rank=LGBMRanker(objective="lambdarank",n_estimators=70,
        num_leaves=7,max_depth=3,min_child_samples=100,
        reg_lambda=25,learning_rate=.04,label_gain=[0,1,3,7],
        random_state=SEED,n_jobs=1,verbosity=-1).fit(
            X,train.future_graded.to_numpy(int),group=groups)
    baselines=dict(
        mean_clipped=float(train.target_signed_clipped.mean()),
        prior_up=float(train.event_up.mean()),
        prior_down=float(train.event_down.mean()))
    return dict(heads=heads,mean=mean,rank=rank,priors=baselines)

def run_models(data,ids):
    results=[]
    fitted=None
    for k,b in enumerate(ids):
        tr,now=training_rows(data,k,ids)
        now=now.copy()
        now["is_model_warmup"]=k<TRAIN_MIN_ANCHORS+1
        now["training_matured_periods"]=tr.block.nunique()
        now["latest_training_maturity"]=(
            str(pd.Timestamp(tr.maturity.max()).date()) if len(tr) else "")
        now["EQUAL_RANK_TOP5"]=now.rank_mean
        for col in ("K1_SIGNED_TAIL_HEADS","K2_SIGNED_MEAN_GBDT",
                    "K3_GRADED_LAMBDARANK",
                    "P_UP3","P_DOWN5","NULL_UP3","NULL_DOWN5",
                    "NULL_SIGNED_MEAN"):
            now[col]=np.nan
        if k>=TRAIN_MIN_ANCHORS+1:
            if k==TRAIN_MIN_ANCHORS+1 or (k-TRAIN_MIN_ANCHORS-1)%REFIT_EVERY==0:
                fitted=fit_models(tr)
                print("T149K_CAUSAL_QUARTERLY_FIT",k,"date",now.signal.iloc[0],
                      "matured",tr.block.nunique(),flush=True)
            X=now[list(DIMS)].to_numpy(float)
            pu=fitted["heads"]["up"].predict_proba(X)[:,1]
            pdn=fitted["heads"]["down"].predict_proba(X)[:,1]
            now["P_UP3"]=pu
            now["P_DOWN5"]=pdn
            now["K1_SIGNED_TAIL_HEADS"]=.03*pu-.05*pdn
            now["K2_SIGNED_MEAN_GBDT"]=fitted["mean"].predict(X)
            now["K3_GRADED_LAMBDARANK"]=fitted["rank"].predict(X)
            now["NULL_UP3"]=fitted["priors"]["prior_up"]
            now["NULL_DOWN5"]=fitted["priors"]["prior_down"]
            now["NULL_SIGNED_MEAN"]=fitted["priors"]["mean_clipped"]
        results.append(now)
    prediction=pd.concat(results,ignore_index=True)
    if len(prediction)!=64*149:raise AssertionError("Wrong forecast panel size")
    actual=prediction.loc[~prediction.is_model_warmup]
    if len(actual)!=51*149:raise AssertionError("Exactly 51 test anchors after warmup")
    if not (pd.to_datetime(actual.latest_training_maturity)<
           pd.to_datetime(actual.signal)).all():
        raise AssertionError("Current ETF target entered meta-model")
    for c in ("K1_SIGNED_TAIL_HEADS","K2_SIGNED_MEAN_GBDT",
              "K3_GRADED_LAMBDARANK"):
        if not np.isfinite(actual[c].to_numpy(float)).all():
            raise AssertionError("nonfinite learned rank: "+c)
    return prediction

def proper_scores(pred):
    p=pred.loc[~pred.is_model_warmup].copy()
    groups=[];date_records=[]
    for b,x in p.groupby("block",sort=True):
        y=x.target_signed_clipped.to_numpy(float)
        predicted=x.K2_SIGNED_MEAN_GBDT.to_numpy(float)
        base=x.NULL_SIGNED_MEAN.to_numpy(float)
        row=dict(block=int(b),signal=x.signal.iloc[0],
                 mse_gain=float(np.mean((y-base)**2-(y-predicted)**2)),
                 mean_mse=float(np.mean((y-predicted)**2)),
                 null_mse=float(np.mean((y-base)**2)))
        for suffix,target,predict,prior in (
                ("up",x.event_up,x.P_UP3,x.NULL_UP3),
                ("down",x.event_down,x.P_DOWN5,x.NULL_DOWN5)):
            truth=target.to_numpy(float)
            modelprob=np.clip(predict.to_numpy(float),1e-6,1-1e-6)
            nullprob=np.clip(prior.to_numpy(float),1e-6,1-1e-6)
            row["brier_gain_"+suffix]=float(np.mean(
                (truth-nullprob)**2-(truth-modelprob)**2))
            row["logloss_gain_"+suffix]=float(np.mean(
                -(truth*np.log(nullprob)+(1-truth)*np.log(1-nullprob))+
                 (truth*np.log(modelprob)+(1-truth)*np.log(1-modelprob))))
        date_records.append(row)
    df=pd.DataFrame(date_records)
    assert len(df)==51
    def ci(x,seed):
        a=np.asarray(x,float);n=len(a)
        rng=np.random.default_rng(seed)
        vals=[]
        for _ in range(2500):
            sample=[]
            while len(sample)<n:
                st=int(rng.integers(n))
                sample.extend((st+i)%n for i in range(3))
            vals.append(float(a[np.asarray(sample[:n],int)].mean()))
        return dict(mean=float(a.mean()),
            ci95=np.quantile(vals,[.025,.975]).tolist(),n=n)
    return dict(
        MSE_signed=ci(df.mse_gain,SEED+41),
        Brier_up=ci(df.brier_gain_up,SEED+42),
        Brier_down=ci(df.brier_gain_down,SEED+43),
        Logloss_up=ci(df.logloss_gain_up,SEED+44),
        Logloss_down=ci(df.logloss_gain_down,SEED+45),
        mean_MSE=float(df.mean_mse.mean()),
        null_MSE=float(df.null_mse.mean())),df

def run(out):
    path=Path(out);path.mkdir(parents=True,exist_ok=False)
    original,old,roster,O,C,days,signals,ids,selected=from_archive()
    data=prepare_features(original)
    pred=run_models(data,ids)
    economic={}
    selections={}
    panel=[]
    per_anchor_score=[]
    for k,b in enumerate(ids):
        block=pred.loc[pred.block==b].copy()
        f=selected["F3"][k];h=selected["H1"][k]
        hs=selected["H3"][k]
        for name,components in [
            ("F3",[("F3",1.,f)]),
            ("H1",[("H1",1.,h)]),
            ("H3",[("H3",1.,hs)]),
            ("STATIC_F3_H1_50",[("F3",.5,f),("H1",.5,h)])]:
            selections.setdefault(name,[]).append(monthly_weights(components))
        scored=block.sort_values("EQUAL_RANK_TOP5",ascending=False)
        names=scored.ticker.head(5).tolist()
        selections.setdefault("EQUAL_RANK_TOP5",[]).append(
            monthly_weights([("RANK",1.,names)]))
        for name in ("K1_SIGNED_TAIL_HEADS","K2_SIGNED_MEAN_GBDT",
                     "K3_GRADED_LAMBDARANK"):
            if k<TRAIN_MIN_ANCHORS+1:
                selection=monthly_weights([("F3",.5,f),("H1",.5,h)])
            else:
                ranked=block.sort_values(name,ascending=False)
                names=ranked.ticker.head(5).tolist()
                selection=monthly_weights([("META",1.,names)])
                per_anchor_score.append(dict(
                    block=int(b),signal=block.signal.iloc[0],policy=name,
                    future_signed_selected=float(ranked.head(5).future_excess.mean()),
                    share_of_future_bottom15=float(ranked.head(5).bottom15.mean()),
                    precision10=float(ranked.head(10).top15.mean()),
                    actual_next_relative_spearman=float(
                        spearmanr(ranked[name],ranked.future_excess).statistic)))
            selections.setdefault(name,[]).append(selection)
        if k<TRAIN_MIN_ANCHORS+1:
            predicted_adv=np.nan
            w=.5
        else:
            forecast=block.set_index("ticker").K2_SIGNED_MEAN_GBDT
            predicted_adv=float(forecast.loc[f].mean()-forecast.loc[h].mean())
            w=.75 if predicted_adv>.02 else (.25 if predicted_adv<-.02 else .5)
        selections.setdefault("K4_PREDICTED_BASKET_GATE",[]).append(
            monthly_weights([("F3",w,f),("H1",1-w,h)]))
        panel.append(dict(block=int(b),signal=block.signal.iloc[0],
            latest_training_maturity=block.latest_training_maturity.iloc[0],
            n_matured_training_anchors=int(block.training_matured_periods.iloc[0]),
            warmup=bool(block.is_model_warmup.iloc[0]),
            F3_picked=";".join(f),H1_picked=";".join(h),
            learned_risk_gate_weight_F3=w,
            learned_predicted_F3_minus_H1_basket_log=predicted_adv))
    wealth={};portfolio={}
    window=days[ids[0]*K:(ids[-1]+1)*K+1]
    for arm in ARM_NAMES:
        x,trade=trade_policy(selections[arm],O,days,ids,list(roster.ticker))
        if arm in BASIS:
            expected=old[{"F3":"B0_F3_FROZEN",
                "H1":"H1_FACTOR_ONLY","H3":"H3_COMBINED_Q"}.get(
                    arm, "STATIC_F3_H1_50")].to_numpy(float) if arm!="STATIC_F3_H1_50" else pd.read_csv(
                    PREVIOUS/"EXPERTS_AND_REAL_COSTED_MIXTURES_DAILY.csv"
                    )["STATIC_F3_H1_50"].to_numpy(float)
            diff=float(np.max(abs(x-expected)))
            if diff>1e-9:
                raise AssertionError("Underlying legacy expert cash curve mismatch "+arm)
        wealth[arm]=x
        portfolio[arm]=metrics(x,window,trade)
        print("T149K_TICKER_META_POLICY",arm,json.dumps(portfolio[arm],
            allow_nan=False),flush=True)
    # All legacy F3/H1/H3 are in old archived original factor-residual result;
    # previous 50:50 is in T149-I, load it rather than requiring nonexistent col.
    baseline=json.loads((PREVIOUS/"RESULT.json").read_text())
    for arm in BASIS:
        oldmetrics=baseline["portfolio_results"][arm]
        for key in ("cagr","maxdd_daily_open","es5_daily"):
            if abs(portfolio[arm][key]-oldmetrics[key])>1e-10:
                raise AssertionError("Frozen full-blend risk accounting mismatch "+arm)
    proper,score_rows=proper_scores(pred)
    net={m:np.diff(np.log(wealth[m][::K])) for m in ARM_NAMES}
    years=np.asarray([pd.Timestamp(signals[b*K]).year for b in ids])
    intervals={}
    gates={}
    base=portfolio["STATIC_F3_H1_50"]
    for model in ARM_NAMES[5:]:
        if model=="K1_SIGNED_TAIL_HEADS":
            skill=(proper["Brier_up"]["ci95"][0]>0 and
                   proper["Brier_down"]["ci95"][0]>0)
        elif model in ("K2_SIGNED_MEAN_GBDT","K4_PREDICTED_BASKET_GATE"):
            skill=proper["MSE_signed"]["ci95"][0]>0
        elif model=="K3_GRADED_LAMBDARANK":
            stacked=pd.DataFrame(per_anchor_score)
            modelp=stacked.loc[stacked.policy==model]
            rankp=pred.loc[~pred.is_model_warmup].groupby("block").apply(
                lambda df:float(df.nlargest(5,"EQUAL_RANK_TOP5").future_excess.mean()),
                include_groups=False).to_numpy(float)
            candidate=modelp.future_signed_selected.to_numpy(float)
            score_era=np.asarray([pd.Timestamp(z).year for z in modelp.signal])
            skill=all(np.mean(candidate[score_era==yearclass])>
                np.mean(rankp[score_era==yearclass])
                for yearclass in sorted(set(score_era>=2024)))
        else:
            raise AssertionError("wrong ranking model")
        gain=net[model]-net["STATIC_F3_H1_50"]
        paired=bootstrap(gain,SEED+50)
        intervals[model]=dict(
            paired_monthly_log_gain=paired,
            positive_months=int((gain>0).sum()),
            early_2021_2023=float(np.mean(gain[years<=2023])),
            later_2024_2026=float(np.mean(gain[years>=2024])))
        gate=bool(skill and paired["ci95"][0]>0 and
            portfolio[model]["cagr"]>base["cagr"] and
            portfolio[model]["maxdd_daily_open"]>=base["maxdd_daily_open"] and
            portfolio[model]["es5_daily"]>=base["es5_daily"] and
            intervals[model]["early_2021_2023"]>0 and
            intervals[model]["later_2024_2026"]>0)
        gates[model]=gate
    pred[["block","ticker","signal","maturity","category",
        "future_excess","future_log","top15","bottom15",
        "target_signed_clipped","event_up","event_down",
        "is_model_warmup","training_matured_periods",
        "latest_training_maturity",*DIMS,
        "EQUAL_RANK_TOP5","K1_SIGNED_TAIL_HEADS",
        "K2_SIGNED_MEAN_GBDT","K3_GRADED_LAMBDARANK",
        "P_UP3","P_DOWN5","NULL_UP3","NULL_DOWN5",
        "NULL_SIGNED_MEAN"]].to_csv(
            path/"ALL_9536_PREQUENTIAL_STACKING_FORECASTS.csv",index=False)
    pd.DataFrame(panel).to_csv(path/"ASOF_64_MONTH_MODEL_SELECTIONS.csv",index=False)
    pd.DataFrame(per_anchor_score).to_csv(
        path/"META_TOP5_DIRECTION_RANKING_AFTER_WARMUP.csv",index=False)
    score_rows.to_csv(path/"PROPER_SCORE_PER_MATURED_TEST_ANCHOR.csv",index=False)
    dated=pd.DataFrame({"day":window})
    for m in ARM_NAMES:dated[m]=wealth[m]
    dated.to_csv(path/"EXACT_CASH_FUNDED_DAILY_STACKED_EQUITIES.csv",index=False)
    res=dict(status="EXACT149_WALK_FORWARD_TWO_FROZEN_EXPERT_TICKER_STACKING_COMPLETE",
        original_etfs=149,n_prior_frozen_prequential_signal_rows=9536,
        source_roster_sha=sha(SRC/"universe.csv"),n_evaluation_21day_anchors=64,
        n_prequential_real_meta_months=51,
        n_meta_test_ticker_rows=51*149,
        original_f3_h1_h3_5050_equity_parity=True,
        no_current_or_previous_incomplete_period_labels=True,
        quarterly_models_fitted_on_matured_prequential_predictions_only=True,
        model_input_features=DIMS,model_results=portfolio,
        post_warmup_proper_score_vs_online_prior=proper,
        paired_monthly_gains_vs_5050=intervals,
        preregistered_strict_joint_science_gates=gates,
        exploratory_no_new_pit_source_or_untouched_149_horizon=True,
        no_live_strategy_promotion=True,
        cautions=["149 same-date ETF labels correlated; effective n dates far below 7599 independent scenarios",
          "F3 and H1 base forecasts reuse original149 prices; stacking data 2021-2026 repeatedly mined",
          "Active ranker may chase volatility, no guaranteed signed economic value",
          "Top5 share-costed 10bp per side from retrospective adjusted US ETF Open and no EU dealer spreads",
          "Warmup held static original 50:50; economic returns over full 64 anchors",
          "Model selection based on ex-post 30% CAGR would be invalid"])
    (path/"RESULT.json").write_text(json.dumps(res,indent=2,allow_nan=False)+"\n")
    print("T149K_FINAL_WALK_FORWARD_STACKING",json.dumps(res,allow_nan=False),flush=True)

if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--out",required=True)
    run(a.parse_args().out)
