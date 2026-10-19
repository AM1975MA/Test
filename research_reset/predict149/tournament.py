#!/usr/bin/env python3
"""Forecast future best ETF names rather than fitting another trading overlay.

Source: exactly 149 fixed ETFs. Features are available at previous Close.
All training labels must have fully matured strictly before each test signal.
Five economic scoring families, one pretrained classifier and exact share
accounting. The data are repeatedly studied: NOT a prospective backtest.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor,HistGradientBoostingClassifier
from sklearn.metrics import ndcg_score
from oasis149.canonical import load_149,sha,SRC
from research_reset.m0b.enrichment import rebalance_exact

ROOT=Path(__file__).resolve().parents[2]
SEED=20261019
STEP=21
NAMES=("N0_MOMENTUM63","N1_REVERSAL5","N2_RIDGE_EXCESS",
       "N3_NONLINEAR_EXCESS","N4_NONLINEAR_TOP15","N5_HIERARCHICAL_RESIDUAL")
EVAL=pd.Timestamp("2021-01-01")
FEE=.001
FEATS=("r5","r21","r63","r126","v21","v63","v126","down63",
       "draw63","draw126","beta126","res21","res63","grp21","grp63",
       "volshock","accel","rank63","trendrisk")

def precompute(C,roster):
    log=np.log(C.where(C>0))
    ret=log.diff()
    r={w:log-log.shift(w) for w in (5,21,63,126)}
    vol={w:ret.rolling(w,min_periods=w).std() for w in (21,63,126)}
    draw={w:log-log.rolling(w,min_periods=w).max() for w in (63,126)}
    down=ret.clip(upper=0).pow(2).rolling(63,min_periods=63).mean().pow(.5)
    sp=ret["SPY"]
    beta=ret.rolling(126,min_periods=126).cov(sp).div(sp.rolling(126,min_periods=126).var(),axis=0)
    groups=roster.set_index("ticker").macro_category.to_dict()
    factors={}
    pct=pd.DataFrame(index=C.index,columns=C.columns,dtype=float)
    for w in (21,63):
        f=pd.DataFrame(index=C.index,columns=C.columns,dtype=float)
        for group in sorted(set(groups.values())):
            mem=[k for k in C.columns if groups[k]==group]
            f.loc[:,mem]=r[w][mem].mean(axis=1).to_numpy()[:,None]
            if w==63:pct.loc[:,mem]=r[w][mem].rank(axis=1,pct=True)
        factors[w]=f.astype(float)
    d={
        "r5":r[5],"r21":r[21],"r63":r[63],"r126":r[126],
        "v21":vol[21],"v63":vol[63],"v126":vol[126],
        "down63":down,
        "draw63":draw[63],"draw126":draw[126],
        "beta126":beta,
        "res21":r[21]-factors[21],
        "res63":r[63]-factors[63],
        "grp21":factors[21],"grp63":factors[63],
        "volshock":vol[21]/vol[63].clip(lower=1e-5),
        "accel":r[5]-r[21]/4.2,
        "rank63":pct,
        "trendrisk":(r[21]+r[63]/3)/(vol[63].clip(lower=.001)*math.sqrt(21))}
    assert tuple(d)==FEATS and len(d)==19
    return d,groups

def dataset():
    roster,O,C,V,days,signals,quality=load_149()
    assert len(roster)==149 and len(days)==2366
    fs,cat=precompute(C,roster)
    names=list(roster.ticker)
    labels={k:i for i,k in enumerate(sorted(set(cat.values())))}
    data=[]
    n=(len(days)-1)//STEP
    assert n==112
    opens=O.loc[days,names].to_numpy(float)
    for block in range(n):
        st=block*STEP
        signal=pd.Timestamp(signals[st])
        entry=pd.Timestamp(days[st]);end=pd.Timestamp(days[st+STEP])
        assert signal<entry<end
        y=np.log(opens[st+STEP]/opens[st])
        benchmark=math.log(.6*(opens[st+STEP,names.index("SPY")]/opens[st,names.index("SPY")])+
                           .4*(opens[st+STEP,names.index("AGG")]/opens[st,names.index("AGG")]))
        top15=set(np.argsort(-y,kind="stable")[:15])
        x=np.stack([fs[f].loc[signal,names].to_numpy(float) for f in FEATS],axis=1)
        if x.shape!=(149,19) or not np.isfinite(x).all():
            raise AssertionError("19-dimensional as-of features absent at "+str(signal))
        onehot=np.zeros((149,6),float)
        for j,t in enumerate(names):onehot[j,labels[cat[t]]]=1.
        x=np.hstack((x,onehot))
        for j,t in enumerate(names):
            data.append(dict(block=block,signal=str(signal.date()),
               entry=str(entry.date()),maturity=str(end.date()),
               ticker=t,category=cat[t],category_id=int(labels[cat[t]]),
               future_log=float(y[j]),future_excess=float(y[j]-benchmark),
               top15=int(j in top15),
               **{f:float(x[j,k]) for k,f in enumerate(FEATS)},
               **{f"g{k}":float(x[j,19+k]) for k in range(6)}))
    df=pd.DataFrame(data)
    assert len(df)==112*149 and df.groupby("block").size().eq(149).all()
    assert all(pd.to_datetime(df.signal)<pd.to_datetime(df.entry))
    assert all(pd.to_datetime(df.entry)<pd.to_datetime(df.maturity))
    return df,roster,days,opens,names

def matrices(frame):
    return frame[list(FEATS)+[f"g{i}" for i in range(6)]].to_numpy(float)

def train_forecast(full):
    eval_ids=sorted(full.loc[pd.to_datetime(full.signal)>=EVAL,"block"].unique())
    assert 60<=len(eval_ids)<=70
    generated=[]
    regr=None;classifier=None
    for k,b in enumerate(eval_ids):
        current=full[full.block==b].copy()
        now=pd.Timestamp(current.signal.iloc[0])
        learned=full[pd.to_datetime(full.maturity)<now]
        assert learned.block.nunique()>=40
        # No labels of the test anchor or future anchor can enter training.
        assert (pd.to_datetime(learned.maturity)<now).all()
        X=matrices(learned);T=matrices(current)
        if np.isnan(X).any() or np.isnan(T).any():raise AssertionError("source changed")
        scaler=StandardScaler()
        xn=scaler.fit_transform(X)
        tn=scaler.transform(T)
        y=learned.future_excess.to_numpy(float)
        yr=learned.future_log.to_numpy(float)
        g=learned.category_id.to_numpy(int)
        # N2 direct net benchmark-excess prediction.
        direct=Ridge(alpha=100.)
        direct.fit(xn,y)
        current["N2_RIDGE_EXCESS"]=direct.predict(tn)
        # N5 independent residual submodel + historical group trend baseline.
        group_avg=learned.groupby(["block","category_id"]).future_log.transform("mean").to_numpy(float)
        residual=yr-group_avg
        hier=Ridge(alpha=100.)
        hier.fit(xn,residual)
        test_group_past=(current.grp63/3).to_numpy(float)
        current["N5_HIERARCHICAL_RESIDUAL"]=hier.predict(tn)+.20*test_group_past
        # Static nontrained but causal opposite mechanisms.
        current["N0_MOMENTUM63"]=current.r63.to_numpy(float)
        current["N1_REVERSAL5"]=-current.r5.to_numpy(float)
        # Quarterly refits of deliberately small nonlinear and rare-winner models.
        if (k%3==0) or regr is None:
            regr=HistGradientBoostingRegressor(
                 max_iter=65,max_leaf_nodes=7,min_samples_leaf=80,
                 learning_rate=.05,l2_regularization=20.,
                 early_stopping=False,random_state=SEED)
            regr.fit(X,y)
            classifier=HistGradientBoostingClassifier(
                 max_iter=65,max_leaf_nodes=7,min_samples_leaf=80,
                 learning_rate=.05,l2_regularization=20.,
                 early_stopping=False,random_state=SEED)
            classifier.fit(X,learned.top15.to_numpy(int))
        current["N3_NONLINEAR_EXCESS"]=regr.predict(T)
        current["N4_NONLINEAR_TOP15"]=classifier.predict_proba(T)[:,1]
        current["null_top15_probability"]=15/149
        current["n_matured_train_blocks"]=int(learned.block.nunique())
        current["latest_train_maturity"]=str(learned.maturity.max())
        current["decision_features_sha_list"]="TRAINING_LABELS_MATURED_ASOF"
        generated.append(current)
        if k in (0,10,30,len(eval_ids)-1):
            print("P149_EVAL",k+1,"of",len(eval_ids),"signal",str(now.date()),
                  "matured",learned.block.nunique(),flush=True)
    return pd.concat(generated,ignore_index=True),eval_ids

def risk_metrics(wealth,dated_index,fee_total,turnover):
    assert len(wealth)==len(dated_index)
    years=(dated_index[-1]-dated_index[0]).days/365.25
    dr=np.diff(np.log(wealth))
    s=float(np.std(dr,ddof=1))
    return dict(cagr=float((wealth[-1]/wealth[0])**(1/years)-1),
        terminal_wealth_multiple=float(wealth[-1]/wealth[0]),
        max_daily_open_drawdown=float((wealth/np.maximum.accumulate(wealth)-1).min()),
        daily_log_sharpe=float(np.mean(dr)/s*np.sqrt(252)) if s>0 else 0.,
        daily_es5=float(np.sort(np.expm1(dr))[:int(np.ceil(.05*len(dr)))].mean()),
        fee_amount_initial_units=float(fee_total),
        gross_turnover_notional_initial_units=float(turnover))

def portfolio(select,eval_ids,open_all,names,dates):
    # A single fully invested five-share portfolio; each rebalance uses the
    # exact solver also used by M0b economic counterfactuals.
    assert len(select)==len(eval_ids)
    assert all(eval_ids[i]+1==eval_ids[i+1] for i in range(len(eval_ids)-1))
    ix={n:i for i,n in enumerate(names)}
    n=len(eval_ids)
    wealth=np.zeros(n*STEP+1,float)
    shares={};cash=1.;fees=0.;turnover=0.
    for k,block in enumerate(eval_ids):
        start=block*STEP
        weights={t:1/5 for t in select[k]}
        assert len(weights)==5
        quotes={n:float(open_all[start,ix[n]]) for n in set(shares)|set(weights)}
        shares,cash,turn,fee,_=rebalance_exact(shares,cash,weights,quotes)
        fees+=fee;turnover+=turn
        wealth[k*STEP]=cash+sum(shares[t]*quotes[t] for t in shares)
        for j in range(1,STEP+1):
            wealth[k*STEP+j]=cash+sum(shares[t]*float(open_all[start+j,ix[t]]) for t in shares)
    assert np.isfinite(wealth).all() and min(wealth)>0
    window=dates[eval_ids[0]*STEP:eval_ids[-1]*STEP+STEP+1]
    return wealth,risk_metrics(wealth,window,fees,turnover)

def bootstrap_metric_by_anchor(pred,model,key="spearman",other=None):
    ordered=sorted(pred.block.unique())
    vals=[]
    for b in ordered:
        row=pred[pred.block==b]
        if key=="spearman":
            x=spearmanr(row[model],row.future_excess).statistic
            if other:
                x-=spearmanr(row[other],row.future_excess).statistic
        elif key=="precision":
            s=row.sort_values(model,ascending=False).head(10)
            x=float(s.top15.mean())
        else:raise AssertionError("bad bootstrap statistic")
        vals.append(float(x))
    x=np.asarray(vals,float)
    rng=np.random.default_rng(SEED+41)
    n=len(x);sims=[]
    for _ in range(1500):
        ids=[]
        while len(ids)<n:
            b=int(rng.integers(n));ids.extend((b+j)%n for j in range(3))
        sims.append(float(x[np.asarray(ids[:n],int)].mean()))
    return dict(mean=float(x.mean()),ci95=np.quantile(sims,[.025,.975]).tolist(),
        blocks=n,positive_months=int(sum(x>0)))

def evaluate(pred,ids,roster,days,opens,names,out):
    out=Path(out)
    selection={};metrics={};scores=[];shadows={}
    for model in NAMES:
        rank=[]
        for b in ids:
            p=pred[pred.block==b].sort_values(model,ascending=False)
            rank.append(p.ticker.head(5).tolist())
        selection[model]=rank
        path,econ=portfolio(rank,ids,opens,names,days)
        shadows[model]=path
        errs=[]
        for b in ids:
            sub=pred[pred.block==b].copy()
            # Positive economic excess only for NDCG; not return CAGR.
            actual=np.maximum(sub.future_excess.to_numpy(float),0.)
            if not any(actual>0): ndcg=None
            else:
                ndcg=float(ndcg_score(actual.reshape(1,-1),
                            sub[model].to_numpy(float).reshape(1,-1),k=10))
            winners=set(sub.nlargest(15,"future_log").ticker)
            picked=sub.nlargest(5,model)
            top1=sub.nlargest(1,model)
            errs.append(dict(anchor=int(b),model=model,signal=sub.signal.iloc[0],
                spearman=float(spearmanr(sub[model],sub.future_excess).statistic),
                precision10=float(sub.nlargest(10,model).top15.mean()),
                future_best_in_prediction_top5=int(
                    sub.loc[sub.future_log.idxmax(),"ticker"] in set(picked.ticker)),
                selected_top5_forward_excess=float(picked.future_excess.mean()),
                selected_top1_forward_excess=float(top1.future_excess.iloc[0]),
                ndcg10=ndcg,
                selected_top5_category_count=int(picked.category.nunique()),
                selected_top5_mean_prior_vol63=float(picked.v63.mean())))
        panel=pd.DataFrame(errs)
        scores.extend(errs)
        byera={}
        for title,mask in (("2021_2023",pd.to_datetime(panel.signal).dt.year<=2023),
                           ("2024_2026",pd.to_datetime(panel.signal).dt.year>=2024)):
            z=panel[mask]
            byera[title]=dict(n=int(len(z)),spearman=float(z.spearman.mean()),
                 precision10=float(z.precision10.mean()),
                 selected5_excess_log=float(z.selected_top5_forward_excess.mean()),
                 expected_future_best_hits=int(z.future_best_in_prediction_top5.sum()))
        metrics[model]=dict(economics=econ,
            mean_spearman=float(panel.spearman.mean()),
            n_winner_in_predicted_top5=int(panel.future_best_in_prediction_top5.sum()),
            precision_at10=float(panel.precision10.mean()),
            mean_net_forward5_excess_vs_60_40=float(panel.selected_top5_forward_excess.mean()),
            mean_net_forward1_excess_vs_60_40=float(panel.selected_top1_forward_excess.mean()),
            ndcg10=float(panel.ndcg10.mean()),
            mean_number_of_distinct_categories_top5=float(panel.selected_top5_category_count.mean()),
            average_selected_63d_vol=float(panel.selected_top5_mean_prior_vol63.mean()),
            by_era=byera,
            spearman_3anchor_ci=bootstrap_metric_by_anchor(pred,model))
        print("P149_MODEL_RESULT",model,json.dumps(metrics[model],allow_nan=False),flush=True)
    first=ids[0]*STEP;last=(ids[-1]+1)*STEP
    pv=opens[first:last+1]
    ix={t:i for i,t in enumerate(names)}
    spy=pv[:,ix["SPY"]]/pv[0,ix["SPY"]]/(1+FEE)
    agg=pv[:,ix["AGG"]]/pv[0,ix["AGG"]]/(1+FEE)
    passive={
        "SPY_BUY_HOLD":risk_metrics(spy,days[first:last+1],pv[0,ix["SPY"]]*0.+(1-spy[0]),spy[0]),
        "6040_SPY_AGG_NO_REBALANCE":risk_metrics(.6*spy+.4*agg,days[first:last+1],(.6*spy[0]+.4*agg[0])*FEE,1.0)}
    binary=pred[["top15","N4_NONLINEAR_TOP15","null_top15_probability"]]
    output={}
    for key in ("N4_NONLINEAR_TOP15","null_top15_probability"):
        p=np.clip(binary[key].to_numpy(float),1e-5,1-1e-5)
        y=binary.top15.to_numpy(float)
        output[key]=dict(brier=float(np.mean((y-p)**2)),
            log_loss=float(np.mean(-y*np.log(p)-(1-y)*np.log(1-p))),
            avg_p=float(p.mean()),actual_rate=float(y.mean()))
    # Strong conditions, not fitted here and NOT an investable certification.
    gate={}
    ref=passive["6040_SPY_AGG_NO_REBALANCE"]
    for model,record in metrics.items():
        v=record["economics"]
        corr=record["spearman_3anchor_ci"]["ci95"][0]>0
        eras=record["by_era"]
        candidate=(corr and v["cagr"]>ref["cagr"] and
            v["max_daily_open_drawdown"]>=-.30 and
            all(q["selected5_excess_log"]>0 for q in eras.values()))
        gate[model]=bool(candidate)
    wealth=pd.DataFrame({"day":days[first:last+1]})
    for m,arr in shadows.items():wealth[m]=arr
    wealth["SPY"]=spy
    wealth["6040"]=.6*spy+.4*agg
    wealth.to_csv(out/"WEALTH_PATHS_TOP5_NEXT_OPEN.csv",index=False)
    pd.DataFrame(scores).to_csv(out/"PER_ANCHOR_RANK_SCORES.csv",index=False)
    return metrics,passive,output,gate

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    args=p.parse_args();dest=Path(args.out);dest.mkdir(parents=True,exist_ok=False)
    src,roster,days,opens,names=dataset()
    pred,ids=train_forecast(src)
    metrics,passive,classification,gate=evaluate(pred,ids,roster,days,opens,names,dest)
    pred.drop(columns=[*FEATS,*[f"g{i}" for i in range(6)]]).to_csv(dest/"ALL149_FROZEN_PREQUENTIAL_PREDICTIONS.csv",index=False)
    out=dict(status="EXACT149_BEST_TICKER_FORECAST_TOURNAMENT_COMPLETE",
        universe_size=149,original149_roster_sha256=sha(SRC/"universe.csv"),
        n_21day_eval_anchors=len(ids),first_eval_signal=str(pred.signal.min()),
        last_eval_signal=str(pred.signal.max()),training_label_maturity_verified=bool(
            (pd.to_datetime(pred.latest_train_maturity)<pd.to_datetime(pred.signal)).all()),
        all_149_tickers_preserved=bool(pred.groupby("block").size().eq(149).all()),
        tested_models=NAMES,weekly_feature_transforms_never_fitted_on_future=True,
        first_training_year=2017,no_independent_holdout=True,
        each_future_topdecile_exactly_15=True,
        nonlinear_quarterly_training_updates=True,
        no_backtest_hyperparameter_tuning=True,fee_each_side=FEE,
        metrics=metrics,passive=passive,
        classifier_calibration=classification,
        candidate_economic_and_statistical_gates=gate,
        no_leverage_or_hindsight_or_concentration_tuning=True,
        guaranteed_30pct_CAGR=False,
        comments=["30 percent annual CAGR is an aspiration, not supported a priori",
             "Deep cross-sectional data dependence: 149 ETF labels do NOT provide 149 independent time trials",
             "149 survivor universe and Yahoo adjusted opens not point-in-time investable, reused 2017-26 sample",
             "NDCG@10 and top15 selection are research diagnostics, not investable expected utilities",
             "No EUR conversion, broker spreads, taxes, actual volumes or transaction impact",
             "Successful results only developmental, need independent new vintages and untouched prospective dates"])
    (dest/"RESULT.json").write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print("EXACT149_PREDICTOR_TOURNAMENT_RESULT "+json.dumps(out,allow_nan=False),flush=True)
if __name__=="__main__":main()
