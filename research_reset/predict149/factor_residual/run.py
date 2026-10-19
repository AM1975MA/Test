#!/usr/bin/env python3
"""Factor-residual distributional forecasting with rigorous as-of factor estimates.

Original149 is a repeatedly-mined survivor-only ETF set. This is NOT a PIT
investment strategy or a validated 30%-CAGR return system.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from lightgbm import LGBMRegressor
from oasis149.canonical import load_149,sha,SRC
from research_reset.predict149.tournament import dataset,portfolio,FEATS
from research_reset.predict149.factor_neutral.diagnose import (
    matched_pair_indices,concordance)

ROOT=Path(__file__).resolve().parents[3]
PARENT=ROOT/"research_reset/predict149/signed_value/results"
FROZEN=("B0_F3_FROZEN","B1_N4_FROZEN","B2_VOL63_RANK")
ARMS=FROZEN+("H1_FACTOR_ONLY","H2_RESIDUAL_Q",
             "H3_COMBINED_Q","H4_F3_EXPOSURE_NEUTRAL")
FACTORS=("SPY","QQQ","IWM","VEA","EEM","TLT","HYG","GLD","USO","IEF")
BETA_RIDGE=.005
FACTOR_RIDGE=60.
SEED=20261019
CLIP=.20
HORIZON=21
INPUT=tuple(FEATS)+tuple(f"g{i}" for i in range(6))+tuple(
    f"beta_{k}" for k in FACTORS)+("resid_momentum21","resid_momentum63")
QUANTILES=(.10,.50,.90)

def asof_betas_and_context(C,names,asof):
    """126 observed daily C/C returns; centered, regularized; no future."""
    close=np.log(C.loc[:asof,names+list(FACTORS)+["AGG"]])
    close=close.loc[:,~close.columns.duplicated()]
    if len(close)<200:raise AssertionError("insufficient historical close data")
    daily=close.diff().tail(126)
    if len(daily)!=126 or not np.isfinite(daily.to_numpy()).all():
        raise AssertionError("Missing as-of daily factor or ETF returns")
    riskbase=.6*daily["SPY"].to_numpy()+.4*daily["AGG"].to_numpy()
    X=daily[list(FACTORS)].to_numpy()-riskbase[:,None]
    Y=daily[names].to_numpy()-riskbase[:,None]
    X=X-X.mean(axis=0)
    Y=Y-Y.mean(axis=0)
    coefs=np.linalg.solve(X.T@X+BETA_RIDGE*np.eye(len(FACTORS)),X.T@Y).T
    if coefs.shape!=(149,10) or not np.isfinite(coefs).all():
        raise AssertionError("As-of factor model missing coefficients")
    if np.abs(coefs).max()>20:raise AssertionError("unstable betas")
    # As-of factor forward predictors: previous 5/21/63 CLOSE changes.
    factor_past={}
    eps={}
    for w in (5,21,63):
        r=(close.iloc[-1]-close.iloc[-w-1])
        factor_past[w]=(r[list(FACTORS)].to_numpy()-
             .6*float(r["SPY"])-.4*float(r["AGG"]))
        etf_relative=(r[names].to_numpy()-
             .6*float(r["SPY"])-.4*float(r["AGG"]))
        eps[w]=etf_relative-coefs@factor_past[w]
    factor_context=np.concatenate([factor_past[k] for k in (5,21,63)])
    return coefs,np.stack([eps[21],eps[63]],axis=1),factor_context

def add_factor_labels(base,roster,days,Opens,Close):
    names=list(roster.ticker)
    name_idx={k:j for j,k in enumerate(names)}
    if not all(t in name_idx for t in FACTORS+("AGG",)):
        raise AssertionError("missing prechosen economic proxy ETF")
    months=np.empty((112,10),float)
    month_context=np.empty((112,30),float)
    data=[]
    for b in range(112):
        t=b*HORIZON
        orig=base.iloc[b*149:(b+1)*149].copy()
        if orig.ticker.tolist()!=names or len(orig)!=149:
            raise AssertionError("ticker order not frozen at "+str(b))
        signal=pd.Timestamp(orig.signal.iloc[0])
        assert signal<pd.Timestamp(days[t])
        betas,epsilon,context=asof_betas_and_context(Close,names,signal)
        bench=float((orig.future_log-orig.future_excess).iloc[0])
        if np.max(np.abs((orig.future_log-orig.future_excess).to_numpy()-bench))>1e-12:
            raise AssertionError("benchmark-dependent label inconsistent")
        f_return=np.log(Opens[t+HORIZON,
            [name_idx[k] for k in FACTORS]]/
            Opens[t,[name_idx[k] for k in FACTORS]])
        Z=f_return-bench
        y=orig.future_excess.to_numpy(float)
        # Mathematically clean projected conditional residual target:
        # actual factor return is used ONLY to label a matured training event.
        resid=y-betas@Z
        orig["future_factor_component"]=betas@Z
        orig["future_idiosyncratic_residual"]=resid
        orig["clip_target_resid"]=np.clip(resid,-CLIP,CLIP)
        for j,factor in enumerate(FACTORS):
            orig["beta_"+factor]=betas[:,j]
        orig["resid_momentum21"]=epsilon[:,0]
        orig["resid_momentum63"]=epsilon[:,1]
        data.append(orig)
        months[b]=Z
        month_context[b]=context
    result=pd.concat(data,ignore_index=True)
    if not np.isfinite(result[list(INPUT)].to_numpy(float)).all():
        raise AssertionError("as-of factor snapshot contains NaN")
    if not np.allclose(result.future_excess.to_numpy(),
                       result.future_factor_component+
                       result.future_idiosyncratic_residual,
                       rtol=0,atol=1e-12):
        raise AssertionError("factor-residual identity failed")
    return result,months,month_context

def residual_quantile():
    return lambda level:LGBMRegressor(objective="quantile",alpha=level,
        n_estimators=80,learning_rate=.04,num_leaves=9,max_depth=4,
        min_child_samples=100,reg_lambda=25.,
        random_state=SEED,n_jobs=1,verbosity=-1)

def prospective_predictions(full,Z,context):
    old=pd.read_csv(PARENT/"ALL_9536_SIGNED_VALUE_FORECASTS.csv")
    testblocks=sorted(old.block.unique())
    if len(testblocks)!=64:raise AssertionError("frozen F3 wrong anchor sample")
    allpred=[]
    fitted={}
    factory=residual_quantile()
    for k,b in enumerate(testblocks):
        now=pd.Timestamp(full.loc[full.block==b,"signal"].iloc[0])
        train=full.loc[pd.to_datetime(full.maturity)<now].copy()
        mature_blocks=sorted(train.block.unique())
        if len(mature_blocks)<40:raise AssertionError("factor training starts prematurely")
        assert (pd.to_datetime(train.maturity)<now).all()
        current=full[full.block==b].copy()
        if k%3==0:
            trainx=train[list(INPUT)].to_numpy(float)
            target=train.clip_target_resid.to_numpy(float)
            fitted["quantiles"]={level:factory(level).fit(trainx,target)
                                 for level in QUANTILES}
            scaled=StandardScaler()
            XX=scaled.fit_transform(context[mature_blocks])
            ridge=Ridge(alpha=FACTOR_RIDGE,fit_intercept=True)
            ridge.fit(XX,Z[mature_blocks])
            fitted["factor"]=ridge
            fitted["scale"]=scaled
            # training-only unconditional comparator, never current factor Z
            fitted["factor_null"]=np.mean(Z[mature_blocks],axis=0)
            fitted["residual_null_q"]={
                q:float(np.quantile(target,q)) for q in QUANTILES}
            print("T149H_PREQUENTIAL_QTR_FIT",k,"asof",now.date(),
                "n_matured_months",len(mature_blocks),flush=True)
        asofbetas=current[["beta_"+j for j in FACTORS]].to_numpy(float)
        predicted_factor=fitted["factor"].predict(
            fitted["scale"].transform(context[b][None,:]))[0]
        current["H1_FACTOR_ONLY"]=asofbetas@predicted_factor
        residual_q=np.sort(np.column_stack(
            [fitted["quantiles"][level].predict(current[list(INPUT)].to_numpy(float))
             for level in QUANTILES]),axis=1)
        current[["R_Q10","R_Q50","R_Q90"]]=residual_q
        current["H2_RESIDUAL_Q"]=(residual_q[:,0]+2*residual_q[:,1]+
                                  residual_q[:,2])/4
        current["H3_COMBINED_Q"]=current.H2_RESIDUAL_Q+current.H1_FACTOR_ONLY
        # as-of features ONLY in neutralization, not next21d outcomes
        current["last_maturity_matured"]=str(pd.Timestamp(train.maturity.max()).date())
        current["factor_true_future"]=float(np.mean(Z[b]))
        current["factor_forecast_mse"]=float(np.mean((predicted_factor-Z[b])**2))
        current["factor_null_mse"]=float(np.mean((fitted["factor_null"]-Z[b])**2))
        for f,z in zip(FACTORS,predicted_factor):
            current["estimated_future_factor_"+f]=z
        for level in QUANTILES:
            current["UNCOND_R_Q"+str(int(level*100))]=fitted["residual_null_q"][level]
        allpred.append(current)
    pred=pd.concat(allpred,ignore_index=True)
    archive=old[["block","ticker","F3_QUANTILE_EXPECTED",
        "B0_N4_TOP15","N7_VOL_ONLY","future_excess","future_log"]]
    pred=pred.merge(archive,on=["block","ticker"],suffixes=("","_ref"),
                    validate="one_to_one")
    for lab in ("future_excess","future_log"):
        np.testing.assert_allclose(pred[lab],pred[lab+"_ref"],rtol=0,atol=1e-12)
    pred["B0_F3_FROZEN"]=pred.F3_QUANTILE_EXPECTED
    pred["B1_N4_FROZEN"]=pred.B0_N4_TOP15
    pred["B2_VOL63_RANK"]=pred.v63
    neutral=[]
    for b in testblocks:
        p=pred[pred.block==b]
        bmat=p[["beta_"+t for t in FACTORS]].to_numpy(float)
        x=p.B0_F3_FROZEN.to_numpy(float)
        z=x-x.mean()
        # ridge projection removes linear exposure component from score only.
        gamma=np.linalg.solve(bmat.T@bmat+np.eye(10),bmat.T@z)
        neutral.extend(x-bmat@gamma)
    pred["H4_F3_EXPOSURE_NEUTRAL"]=neutral
    if len(pred)!=64*149:raise AssertionError("wrong 149x64 predictors")
    assert (pd.to_datetime(pred.last_maturity_matured)<
            pd.to_datetime(pred.signal)).all()
    for name in ARMS:
        if not np.isfinite(pred[name].to_numpy(float)).all():
            raise AssertionError("non-finite signal "+name)
    return pred,testblocks

def boot(x):
    values=np.asarray(x,float)
    assert len(values)==64
    rng=np.random.default_rng(SEED+152)
    out=[]
    for _ in range(1600):
        ix=[]
        while len(ix)<len(values):
            k=int(rng.integers(len(values)))
            ix.extend((k+j)%len(values) for j in range(3))
        out.append(float(values[np.asarray(ix[:len(values)],int)].mean()))
    return dict(mean=float(values.mean()),ci95=np.quantile(out,[.025,.975]).tolist())

def pinball(y,p,q):
    x=np.asarray(y,float)-np.asarray(p,float)
    return float(np.mean(np.maximum(q*x,(q-1)*x)))

def evaluate(pred,ids,open_prices,names,days,out):
    records=[];allmetrics={};paths={}
    previous=json.loads((PARENT/"RESULT.json").read_text())
    for model in ARMS:
        selections=[]
        for b in ids:
            p=pred[pred.block==b].copy()
            p=p.sort_values(model,ascending=False)
            selected=p.head(5)
            selections.append(selected.ticker.tolist())
            y=p.future_excess.to_numpy(float)
            group=p.category.to_numpy(str)
            risk=p.v63.to_numpy(float)
            i,j=matched_pair_indices(group,risk,band=.20)
            if len(i)<30:raise AssertionError("no same-risk group pairs")
            score=concordance(p[model].to_numpy(float),y,i,j)
            original=concordance(p.B0_F3_FROZEN.to_numpy(float),y,i,j)
            records.append(dict(block=int(b),signal=p.signal.iloc[0],
                model=model,matched_pairs=len(i),
                conditional_concordance=score,
                conditional_uplift_vs_F3=score-original,
                all_ETF_spearman=float(spearmanr(p[model],y).statistic),
                mean_top5_signed_excess=float(selected.future_excess.mean()),
                selected_bottom15_fraction=float(
                    (selected.future_log.rank(method="first")<=15).mean())
                    if False else float(selected.bottom15.mean()),
                precision10=float(p.head(10).top15.mean())))
        w,economics=portfolio(selections,ids,open_prices,names,days)
        paths[model]=w
        scores=pd.DataFrame([r for r in records if r["model"]==model])
        periods={}
        for era,mask in (("2021_2023",pd.to_datetime(scores.signal).dt.year<=2023),
                         ("2024_2026",pd.to_datetime(scores.signal).dt.year>=2024)):
            data=scores[mask]
            periods[era]=dict(n=len(data),
                concordance=float(data.conditional_concordance.mean()),
                improvement_vs_F3=float(data.conditional_uplift_vs_F3.mean()),
                selected_signed_excess=float(data.mean_top5_signed_excess.mean()),
                selected_bottom15=float(data.selected_bottom15_fraction.mean()))
        allmetrics[model]=dict(economics=economics,
            conditional_concordance=boot(scores.conditional_concordance),
            matched_delta_vs_F3=boot(scores.conditional_uplift_vs_F3),
            raw_crosssectional_spearman=float(scores.all_ETF_spearman.mean()),
            selected5_signed_excess=float(scores.mean_top5_signed_excess.mean()),
            selected_bottom15_fraction=float(scores.selected_bottom15_fraction.mean()),
            precision10=float(scores.precision10.mean()),
            periods=periods)
        print("T149H_FACTOR_RESIDUAL_MODEL",model,json.dumps(allmetrics[model],
              allow_nan=False),flush=True)
    # Keep the exact frozen 2021-26 F3 top5 portfolio share accounting intact.
    frozen=previous["model_results"]["F3_QUANTILE_EXPECTED"]["economic"]
    for key in ("cagr","max_daily_open_drawdown","daily_es5","fee_amount_initial_units"):
        err=abs(allmetrics["B0_F3_FROZEN"]["economics"][key]-frozen[key])
        if err>1e-10:raise AssertionError("F3 historical equity parity failed "+key+" "+str(err))
    factor_mse=pred.drop_duplicates("block")[["factor_forecast_mse","factor_null_mse"]]
    factors=dict(estimated_factor_mse=float(factor_mse.factor_forecast_mse.mean()),
                 simple_matured_mean_mse=float(factor_mse.factor_null_mse.mean()),
                 n_months=len(factor_mse))
    qloss={}
    yr=pred.clip_target_resid
    for q in QUANTILES:
        tag=str(int(q*100))
        qloss[tag]=dict(model_pinball=pinball(yr,pred["R_Q"+tag],q),
            historical_prior_pinball=pinball(yr,pred["UNCOND_R_Q"+tag],q),
            below_pred_fraction=float(np.mean(pred.future_idiosyncratic_residual<
                                             pred["R_Q"+tag])))
    first=ids[0]*HORIZON;last=(ids[-1]+1)*HORIZON
    dated=pd.DataFrame({"day":days[first:last+1]})
    for model,curve in paths.items():dated[model]=curve
    dated.to_csv(out/"MATCHED_5_ETF_DAILY_COSTED_WEALTH.csv",index=False)
    pd.DataFrame(records).to_csv(out/"CONDITIONAL_MATCHED_64_ANCHOR_RANK.csv",index=False)
    baseline=allmetrics["B0_F3_FROZEN"]
    gates={}
    for model in ARMS[3:]:
        m=allmetrics[model]
        gates[model]=bool(
            m["conditional_concordance"]["ci95"][0]>.5 and
            m["matched_delta_vs_F3"]["ci95"][0]>0 and
            all(m["periods"][z]["improvement_vs_F3"]>0 and
                m["periods"][z]["selected_signed_excess"]>
                    baseline["periods"][z]["selected_signed_excess"]
                for z in ("2021_2023","2024_2026")) and
            m["selected_bottom15_fraction"]<=baseline["selected_bottom15_fraction"] and
            m["economics"]["cagr"]>baseline["economics"]["cagr"] and
            m["economics"]["max_daily_open_drawdown"]>=
                    baseline["economics"]["max_daily_open_drawdown"] and
            (model!="H3_COMBINED_Q" or
                 factors["estimated_factor_mse"]<factors["simple_matured_mean_mse"]))
    return allmetrics,factors,qloss,gates

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=False)
    base,roster,days,open_prices,names=dataset()
    roster2,O,C,V,d2,signal,quality=load_149()
    if not names==list(roster2.ticker) or not (d2==days).all():
        raise AssertionError("original149 roster/calendar changed")
    full,Z,context=add_factor_labels(base,roster,days,open_prices,C)
    full["bottom15"]=(full.groupby("block").future_log.rank(
        method="first",ascending=True)<=15).astype(int)
    pred,ids=prospective_predictions(full,Z,context)
    metrics,factors,quantile,gates=evaluate(pred,ids,open_prices,names,days,out)
    pcols=["block","ticker","signal","maturity","future_excess","future_log",
          "category","v63","beta_SPY","beta_QQQ","beta_IWM","beta_VEA",
          "beta_EEM","beta_TLT","beta_HYG","beta_GLD","beta_USO","beta_IEF",
          "future_factor_component","future_idiosyncratic_residual",
          "clip_target_resid","bottom15","top15","last_maturity_matured",
          "R_Q10","R_Q50","R_Q90",*ARMS]
    pred[pcols].to_csv(out/"FULL_9536_ASOF_FACTOR_AND_RESIDUAL_FORECASTS.csv",index=False)
    summary=dict(status="ORIGINAL149_FACTOR_RESIDUAL_DISTRIBUTIONAL_EXPERIMENT_COMPLETE",
        source_roster_SHA=sha(SRC/"universe.csv"),n_original_etfs=149,
        n_study_full_21day_blocks=112,n_eval_anchors=64,n_eval_ticker_rows=len(pred),
        ten_factor_proxy_tickers=FACTORS,
        asof_factor_beta_lookback=126,
        beta_ridge=BETA_RIDGE,quarterly_training_matured_only=True,
        original_F3_frozen_economic_parity=True,
        no_realized_future_factors_used_at_prediction=True,
        no_point_in_time_holdings_or_macro_vintages=True,
        factor_forecast_MSE_vs_matured_mean=factors,
        residual_quantile_pinball=quantile,
        per_model_evaluation=metrics,
        preregistered_mandatory_skill_and_economic_gates=gates,
        no_production_approval=True,
        caveats=["historical 149 ETF roster selected as of 2026 with survivorship bias",
                 "2017–2026 panel repeatedly mined; no true independent test",
                 "US ETF factor proxies and group categories do NOT capture all fund mechanisms",
                 "factor prediction is itself uncertain; forward factors are never provided as test-time inputs",
                 "ETF adjusted open data not verified broker fills and not EUR-tradable",
                 "Some factor proxies are correlated; ridge 126d β remains an approximation",
                 "No strategy should be promoted solely because retrospective CAGR rose"])
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    print("T149H_FACTOR_RESIDUAL_FINAL "+json.dumps(summary,allow_nan=False),flush=True)
if __name__=="__main__":main()
