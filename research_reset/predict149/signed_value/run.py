#!/usr/bin/env python3
"""Original149: distinguish P(rise), magnitude conditional on rise/fall, quantiles.

No labels from the future enter training, including historical event-prior
comparators. Shadow five-share economics only, never live deployable.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from lightgbm import LGBMClassifier,LGBMRegressor
from oasis149.canonical import sha,SRC
from research_reset.predict149.tournament import dataset,portfolio,FEATS
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"research_reset/predict149/results"
RISK=ROOT/"research_reset/predict149/conditional_validation/results"
SEED=20261019
COLS=tuple(FEATS)+tuple(f"g{i}" for i in range(6))
ARMS=("B0_N4_TOP15","B1_PAST63","F1_SIGNED_MEAN",
      "F2_HURDLE_EXPECTED","F3_QUANTILE_EXPECTED",
      "F4_SIGNED_EVENT_VALUE","F5_MEAN_PER_UNIT_RISK",
      "N7_VOL_ONLY")
STEP=21
RETRAIN_EVERY=3
CAP=.20

def parameters():
    return dict(n_estimators=80,learning_rate=.04,num_leaves=9,max_depth=4,
        min_child_samples=100,reg_lambda=25.,
        random_state=SEED,n_jobs=1,verbosity=-1)

def classifier():
    return LGBMClassifier(**parameters())

def regressor(loss="regression",quantile=None):
    if quantile is not None:
        return LGBMRegressor(objective="quantile",alpha=quantile,**parameters())
    return LGBMRegressor(objective=loss,**parameters())

def enrich(df):
    out=df.copy()
    y=out.future_excess.to_numpy(float)
    out["signed_pos"]=(y>0).astype(int)
    out["event_up"]=(y>.03).astype(int)
    out["event_down"]=(y<-.05).astype(int)
    out["signed_clipped"]=np.clip(y,-CAP,CAP)
    out["conditional_positive"]=np.minimum(np.maximum(y,0),CAP)
    out["conditional_negative"]=np.minimum(np.maximum(-y,0),CAP)
    out["bottom15"]=(out.groupby("block").future_log.rank(method="first",ascending=True)<=15).astype(int)
    assert out.groupby("block").bottom15.sum().eq(15).all()
    return out

def history_event_prior(training,category_id,column,eps=.001):
    part=training[training.category_id==category_id]
    if len(part)==0:raise AssertionError("missing historical group")
    return float(np.clip(part[column].mean(),eps,1-eps))

def train_forecasts(df):
    original=pd.read_csv(BASE/"ALL149_FROZEN_PREQUENTIAL_PREDICTIONS.csv")
    volbased=pd.read_csv(RISK/"RISK_BASELINE_PER_TICKER_PREQUENTIAL.csv")
    ids=sorted(original.block.unique())
    assert len(ids)==64
    fitted={}
    result=[]
    for k,b in enumerate(ids):
        current=df[df.block==b].copy()
        now=pd.Timestamp(current.signal.iloc[0])
        train=df[pd.to_datetime(df.maturity)<now]
        if train.block.nunique()<40:raise AssertionError("no mature source")
        assert (pd.to_datetime(train.maturity)<now).all()
        X=train[list(COLS)].to_numpy(float)
        Q=current[list(COLS)].to_numpy(float)
        y=train.signed_clipped.to_numpy(float)
        positive=(train.signed_pos.to_numpy(int)==1)
        if not (len(y)>2500 and positive.sum()>500 and (~positive).sum()>500):
            raise AssertionError("training sign distribution degenerate")
        if k%RETRAIN_EVERY==0:
            fitted["mean"]=regressor().fit(X,y)
            fitted["sign"]=classifier().fit(X,train.signed_pos.to_numpy(int))
            fitted["positive"]=regressor("regression_l1").fit(X[positive],
                train.loc[positive,"conditional_positive"].to_numpy(float))
            fitted["negative"]=regressor("regression_l1").fit(X[~positive],
                train.loc[~positive,"conditional_negative"].to_numpy(float))
            for level in (.10,.50,.90):
                fitted[f"q{level}"]=regressor(quantile=level).fit(X,y)
            fitted["up"]=classifier().fit(X,train.event_up.to_numpy(int))
            fitted["down"]=classifier().fit(X,train.event_down.to_numpy(int))
            print("T149F_SIGNED_MODEL_FIT",k,"asof",now.date(),
                  "fully_matured_21session_blocks",train.block.nunique(),flush=True)
        current["F1_SIGNED_MEAN"]=fitted["mean"].predict(Q)
        current["P_SIGN_POS"]=np.clip(fitted["sign"].predict_proba(Q)[:,1],1e-5,1-1e-5)
        current["P_POS_MAG"]=np.clip(fitted["positive"].predict(Q),0,CAP)
        current["P_NEG_MAG"]=np.clip(fitted["negative"].predict(Q),0,CAP)
        current["F2_HURDLE_EXPECTED"]=(current.P_SIGN_POS*current.P_POS_MAG -
             (1-current.P_SIGN_POS)*current.P_NEG_MAG)
        for level in (.10,.50,.90):
            current[f"Q{int(level*100)}"]=fitted[f"q{level}"].predict(Q)
        # Enforce nondecreasing pointwise quantiles; no training on future.
        qq=np.sort(current[["Q10","Q50","Q90"]].to_numpy(float),axis=1)
        current[["Q10","Q50","Q90"]]=qq
        current["F3_QUANTILE_EXPECTED"]=(current.Q10+2*current.Q50+current.Q90)/4
        current["P_UP_3PCT"]=np.clip(fitted["up"].predict_proba(Q)[:,1],1e-5,1-1e-5)
        current["P_DOWN_5PCT"]=np.clip(fitted["down"].predict_proba(Q)[:,1],1e-5,1-1e-5)
        current["F4_SIGNED_EVENT_VALUE"]=.03*current.P_UP_3PCT-.05*current.P_DOWN_5PCT
        current["F5_MEAN_PER_UNIT_RISK"]=current.F1_SIGNED_MEAN/(
            current.v63.clip(lower=.01)*math.sqrt(STEP))
        current["B1_PAST63"]=current.r63
        current["NULL_SIGN_PRIOR"]=float(train.signed_pos.mean())
        current["NULL_SIGNED_MEAN"]=float(train.signed_clipped.mean())
        for q in (.10,.50,.90):
            current[f"NULL_Q{int(q*100)}"]=float(train.signed_clipped.quantile(q))
        for indicator in ("event_up","event_down"):
            current[f"NULL_{indicator}"]=[
                history_event_prior(train,g,indicator) for g in current.category_id]
        current["trained_last_maturity"]=str(pd.Timestamp(train.maturity.max()).date())
        result.append(current)
    pred=pd.concat(result,ignore_index=True)
    expected=original[["block","ticker","N4_NONLINEAR_TOP15",
        "future_excess","future_log","top15"]]
    pred=pred.merge(expected,on=["block","ticker"],
           validate="one_to_one",suffixes=("","_old"))
    for key in ("future_excess","future_log","top15"):
        if not np.allclose(pred[key].to_numpy(float),
                           pred[key+"_old"].to_numpy(float),atol=1e-12,rtol=0):
            raise AssertionError("Frozen 149 forecast target moved "+key)
    pred=pred.merge(volbased[["block","ticker","N7_VOL_ONLY_RANK"]],
                    on=["block","ticker"],validate="one_to_one")
    pred["B0_N4_TOP15"]=pred.N4_NONLINEAR_TOP15
    assert len(pred)==64*149 and pred.groupby("block").size().eq(149).all()
    if not (pd.to_datetime(pred.trained_last_maturity)<pd.to_datetime(pred.signal)).all():
        raise AssertionError("Immature historical label in fit")
    for k in ARMS+("P_SIGN_POS","P_UP_3PCT","P_DOWN_5PCT"):
        if not np.isfinite(pred[k]).all():raise AssertionError("bad prediction "+k)
    return pred,ids

def prob_score(label,prediction):
    y=np.asarray(label,float)
    p=np.clip(np.asarray(prediction,float),1e-6,1-1e-6)
    return dict(brier=float(np.mean((y-p)**2)),
        logloss=float(np.mean(-y*np.log(p)-(1-y)*np.log(1-p))),
        mean_prediction=float(p.mean()),event_rate=float(y.mean()))

def pinball(y,p,q):
    x=np.asarray(y,float)-np.asarray(p,float)
    return float(np.mean(np.maximum(q*x,(q-1)*x)))

def block_bootstrap(values):
    a=np.asarray(values,float)
    assert len(a)==64
    rng=np.random.default_rng(SEED+71)
    samples=[]
    for _ in range(1500):
        ix=[]
        while len(ix)<len(a):
            j=int(rng.integers(len(a)))
            ix.extend((j+k)%len(a) for k in range(3))
        samples.append(float(a[np.array(ix[:len(a)])].mean()))
    return dict(mean=float(a.mean()),ci95=np.quantile(samples,[.025,.975]).tolist())

def score(pred,ids,opens,names,days,output):
    archive=json.loads((BASE/"RESULT.json").read_text())
    metrics={}
    anchor_rows=[]
    paths={}
    for model in ARMS:
        picks=[]
        for b in ids:
            s=pred[pred.block==b].sort_values(model,ascending=False)
            top=s.head(5)
            picks.append(top.ticker.tolist())
            base=spearmanr(s.B0_N4_TOP15,s.future_excess).statistic
            current=spearmanr(s[model],s.future_excess).statistic
            anchor_rows.append(dict(model=model,block=int(b),signal=s.signal.iloc[0],
                spearman=float(current),
                spearman_delta_vs_N4=float(current-base),
                precision10_top15=float(s.head(10).top15.mean()),
                precision5_top15=float(top.top15.mean()),
                fraction_top5_positive_excess=float(top.signed_pos.mean()),
                share_bottom15=float(top.bottom15.mean()),
                mean_21d_signed_excess_log=float(top.future_excess.mean()),
                average_selected_vol63=float(top.v63.mean()),
                raw_future_best_in_top5=int(s.loc[s.future_log.idxmax(),"ticker"] in set(top.ticker))))
        path,economic=portfolio(picks,ids,opens,names,days)
        paths[model]=path
        a=pd.DataFrame([z for z in anchor_rows if z["model"]==model])
        eras={}
        for era,mask in (("2021_2023",pd.to_datetime(a.signal).dt.year<=2023),
                         ("2024_2026",pd.to_datetime(a.signal).dt.year>=2024)):
            x=a[mask]
            eras[era]=dict(n=len(x),mean_signed_excess=float(x.mean_21d_signed_excess_log.mean()),
                positive_frac=float(x.fraction_top5_positive_excess.mean()),
                bottom15=float(x.share_bottom15.mean()),
                mean_spearman=float(x.spearman.mean()),
                precision10=float(x.precision10_top15.mean()))
        metrics[model]=dict(economic=economic,
            mean_spearman=float(a.spearman.mean()),
            spearman_delta_ci=block_bootstrap(a.spearman_delta_vs_N4),
            selected_top5_mean_signed_excess=float(a.mean_21d_signed_excess_log.mean()),
            selected_top5_probability_positive=float(a.fraction_top5_positive_excess.mean()),
            selected_bottom15_fraction=float(a.share_bottom15.mean()),
            precision10_top15=float(a.precision10_top15.mean()),
            raw_future_best_found_in_top5=int(a.raw_future_best_in_top5.sum()),
            mean_selected_historical_vol63=float(a.average_selected_vol63.mean()),
            eras=eras)
        print("T149F_SIGNED_MODEL_SCORE",model,
              json.dumps(metrics[model],allow_nan=False),flush=True)
    old=archive["metrics"]["N4_NONLINEAR_TOP15"]["economics"]
    for k in ("cagr","max_daily_open_drawdown","daily_es5","fee_amount_initial_units"):
        if abs(metrics["B0_N4_TOP15"]["economic"][k]-old[k])>1e-10:
            raise AssertionError("N4 frozen equity parity changed: "+k)
    y=pred.signed_clipped.to_numpy(float)
    cal=dict(
        sign=prob_score(pred.signed_pos,pred.P_SIGN_POS),
        sign_null=prob_score(pred.signed_pos,pred.NULL_SIGN_PRIOR),
        up3=prob_score(pred.event_up,pred.P_UP_3PCT),
        up3_null=prob_score(pred.event_up,pred.NULL_event_up),
        down5=prob_score(pred.event_down,pred.P_DOWN_5PCT),
        down5_null=prob_score(pred.event_down,pred.NULL_event_down),
        mean_clipped_MSE=float(np.mean((y-pred.F1_SIGNED_MEAN)**2)),
        matured_prior_MSE=float(np.mean((y-pred.NULL_SIGNED_MEAN)**2)),
        hurdle_clipped_MSE=float(np.mean((y-pred.F2_HURDLE_EXPECTED)**2)),
        q10_pinball=pinball(y,pred.Q10,.1),
        q10_null_pinball=pinball(y,pred.NULL_Q10,.1),
        q50_pinball=pinball(y,pred.Q50,.5),
        q50_null_pinball=pinball(y,pred.NULL_Q50,.5),
        q90_pinball=pinball(y,pred.Q90,.9),
        q90_null_pinball=pinball(y,pred.NULL_Q90,.9))
    # Signed economic utility cannot be inferred from top15 event alone:
    # primary gate requires outperforming the actual N4 *and* vol-only baseline
    # on signed mean, confidence in cross-sectional rank and both eras.
    gates={}
    base=metrics["B0_N4_TOP15"]
    vol=metrics["N7_VOL_ONLY"]
    for method in ARMS[2:-1]:
        m=metrics[method]
        gates[method]=bool(
            m["spearman_delta_ci"]["ci95"][0]>0 and
            m["selected_top5_mean_signed_excess"]>max(
                base["selected_top5_mean_signed_excess"],
                vol["selected_top5_mean_signed_excess"]) and
            m["selected_bottom15_fraction"]<=base["selected_bottom15_fraction"] and
            all(m["eras"][era]["mean_signed_excess"]>
                  base["eras"][era]["mean_signed_excess"]
                  for era in ("2021_2023","2024_2026")))
    wealth=pd.DataFrame({"day":days[ids[0]*STEP:(ids[-1]+1)*STEP+1]})
    for m,p in paths.items():wealth[m]=p
    wealth.to_csv(output/"COSTED_DAILY_WEALTH_SAME_149.csv",index=False)
    pd.DataFrame(anchor_rows).to_csv(output/"ANCHOR_SIGNED_VALUE_METRICS.csv",index=False)
    return metrics,cal,gates

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    output=Path(parser.parse_args().out)
    output.mkdir(parents=True,exist_ok=False)
    frame,roster,days,opens,names=dataset()
    df=enrich(frame)
    prediction,ids=train_forecasts(df)
    metrics,cal,gates=score(prediction,ids,opens,names,days,output)
    cols=["block","ticker","signal","entry","maturity","category",
        "future_excess","future_log","signed_clipped","top15","bottom15",
        "signed_pos","event_up","event_down","trained_last_maturity",
        *ARMS,"P_SIGN_POS","P_POS_MAG","P_NEG_MAG","Q10","Q50","Q90",
        "P_UP_3PCT","P_DOWN_5PCT","NULL_SIGN_PRIOR","NULL_event_up",
        "NULL_event_down","NULL_SIGNED_MEAN"]
    prediction[cols].to_csv(output/"ALL_9536_SIGNED_VALUE_FORECASTS.csv",index=False)
    outcome=dict(status="ORIGINAL149_SIGNED_VALUE_DISTRIBUTION_TEST_COMPLETED",
        original_tickers=149,original_source_sha=sha(SRC/"universe.csv"),
        evaluation_21session_anchors=64,
        same_149_9536_predicted_ticker_months=len(prediction),
        frozen_N4_replay_parity=True,
        training_uses_only_strictly_matured_labels=True,
        no_new_actual_point_in_time_source=True,
        target="signed 21d benchmark-relative log payoff before costs",
        raw_forward_outcome_not_clipped_at_score=True,
        model_results=metrics,
        proper_scores_signed_distribution=cal,
        preregistered_directional_skill_gates=gates,
        no_promotion_or_backtest_tuning=True,
        caveats=["Original149 survivor-selected and already heavily mined 2021–26",
                 "No untouched prospective evidence, no historically delisted funds",
                 "Three quantiles do not fully define the true conditional distribution",
                 "F2 part-wise magnitude forecasts are approximate conditional means",
                 "Future 60/40 benchmark is only target label, not as-of feature",
                 "Yahoo adjusted price path does not ensure executable EUR ETF quotes",
                 "High shadow CAGR, if any, is not a validated profitable strategy"])
    (output/"RESULT.json").write_text(json.dumps(outcome,indent=2,allow_nan=False)+"\n")
    print("T149F_SIGNED_VALUE_RESULT",json.dumps(outcome,allow_nan=False),flush=True)
if __name__=="__main__":main()
