#!/usr/bin/env python3
"""T149-E truly raw OHLCV bars vs engineered market activity as-of predictors."""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import ExtraTreesClassifier
from lightgbm import LGBMClassifier
from oasis149.canonical import load_149,SRC,sha
from research_reset.predict149.tournament import dataset,portfolio,FEATS
from research_reset.predict149.feature_objective.run import bootstrap

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"research_reset/predict149/results"
SEED=20261019;STEP=21;N=149
GROUPS=tuple(f"g{i}" for i in range(6))
RAW=tuple(f"bar_{j:02d}_{kind}" for j in range(21) for kind in
          ("open_gap","candle","upperwick","lowerwick","volume_change"))
EXTRA=("parkinson21","parkinson63","garman_klass21","garman_klass63",
       "gapvol21","gapvol63","gapret21","gapret63","intraday_ret21","intraday_ret63",
       "highloc21","lowloc63","range_ratio21to63",
       "logvol_z21vs126","logvol_z21vs63",
       "signed_flow21","signed_flow63","amihud21","amihud63",
       "return_vol_corr63","intraday_vol_corr21")
METHODS=("B0_ARCHIVED_N4","O1_RAW_BAR21_LGBM","O2_ENG_OHLCV_LGBM",
         "O3_ENG_OHLCV_EXTRA_TREES","O4_ENG_OHLCV_LOGISTIC")
COLRAW=RAW+GROUPS
COLENG=tuple(FEATS)+EXTRA+GROUPS

def load_bars(roster):
    h={};l={}
    for t in roster.ticker:
        p=SRC/(t+".csv")
        x=pd.read_csv(p,parse_dates=["date"]).set_index("date").sort_index()
        if not {"High","Low","Open","Close","Volume"}<=set(x):
            raise AssertionError("Source no full OHLCV "+t)
        h[t]=x.High.astype(float)
        l[t]=x.Low.astype(float)
    high=pd.concat(h,axis=1);low=pd.concat(l,axis=1)
    return high,low

def feature_frames(O,H,L,C,V):
    """Causal intraday movement and volume, 21 precommitted engineered features."""
    if not O.index.equals(C.index):
        raise AssertionError("OHLC index mismatch")
    H=H.reindex(index=O.index,columns=O.columns)
    L=L.reindex(index=O.index,columns=O.columns)
    V=V.reindex(index=O.index,columns=O.columns)
    if (H<=0).any().any() or (L<=0).any().any():
        raise AssertionError("Nonpositive historical High/Low")
    ln=lambda x: np.log(x.where(x>0))
    cc=ln(C/C.shift(1))
    gap=ln(O/C.shift(1))
    candle=ln(C/O)
    wickup=ln(H/np.maximum(O,C))
    wickdown=ln(np.minimum(O,C)/L)
    dollar=(V.clip(lower=0)*C.clip(lower=0))
    lv=np.log1p(V.clip(lower=0))
    dvol=lv.diff()
    ranged=ln(H/L)
    if any(x.shape!=O.shape for x in (gap,candle,wickup,wickdown,dvol)):
        raise AssertionError("Candle raw axis mismatch")
    raw=[gap,candle,wickup,wickdown,dvol]
    par=lambda n:np.sqrt(ranged.pow(2).rolling(n,min_periods=n).mean()/(4*math.log(2)))
    gkvar=(.5*ranged.pow(2)-(2*math.log(2)-1)*candle.pow(2)).clip(lower=0)
    gk=lambda n:np.sqrt(gkvar.rolling(n,min_periods=n).mean().clip(lower=1e-12))
    flow=lambda n:(np.sign(cc)*dollar).rolling(n,min_periods=n).sum()/dollar.rolling(n,min_periods=n).sum().clip(lower=1)
    amih=lambda n:np.log1p((cc.abs()/dollar.clip(lower=1)).rolling(
        n,min_periods=n).mean()*1e8)
    volz=lambda n:(lv.rolling(21,min_periods=21).mean()-
        lv.rolling(n,min_periods=n).mean())/lv.rolling(n,min_periods=n).std().clip(lower=.01)
    extras={
        "parkinson21":par(21),"parkinson63":par(63),
        "garman_klass21":gk(21),"garman_klass63":gk(63),
        "gapvol21":gap.rolling(21,min_periods=21).std(),
        "gapvol63":gap.rolling(63,min_periods=63).std(),
        "gapret21":gap.rolling(21,min_periods=21).sum(),
        "gapret63":gap.rolling(63,min_periods=63).sum(),
        "intraday_ret21":candle.rolling(21,min_periods=21).sum(),
        "intraday_ret63":candle.rolling(63,min_periods=63).sum(),
        "highloc21":ln(C/H.rolling(21,min_periods=21).max()),
        "lowloc63":ln(C/L.rolling(63,min_periods=63).min()),
        "range_ratio21to63":ranged.rolling(21,min_periods=21).mean()/
            ranged.rolling(63,min_periods=63).mean().clip(lower=1e-5),
        "logvol_z21vs126":volz(126),"logvol_z21vs63":volz(63),
        "signed_flow21":flow(21),"signed_flow63":flow(63),
        "amihud21":amih(21),"amihud63":amih(63),
        "return_vol_corr63":cc.rolling(63,min_periods=63).corr(lv),
        "intraday_vol_corr21":candle.rolling(21,min_periods=21).corr(lv)}
    assert tuple(extras)==EXTRA and len(extras)==21
    return raw,extras

def fill_features(df,roster,raw,extras):
    names=list(roster.ticker)
    rawmat=np.empty((len(df),105),float)
    engmat=np.empty((len(df),21),float)
    for b in sorted(df.block.unique()):
        ix=np.flatnonzero(df.block.to_numpy()==b)
        w=df.iloc[ix]
        if w.ticker.tolist()!=names or len(w)!=149:raise AssertionError("ticker membership drift")
        s=pd.Timestamp(w.signal.iloc[0])
        bars=np.stack([v.loc[:s,names].tail(21).to_numpy(float) for v in raw],axis=-1)
        if bars.shape!=(21,149,5):raise AssertionError("noncausal raw bar snapshot")
        rawmat[ix,:]=bars.transpose(1,0,2).reshape(149,105)
        engmat[ix,:]=np.stack([extras[k].loc[s,names].to_numpy(float) for k in EXTRA],axis=1)
    if not np.isfinite(rawmat).all() or not np.isfinite(engmat).all():
        raise AssertionError("Invalid OHLCV raw or engineered feature, no implicit imputation")
    for i,k in enumerate(RAW):df[k]=rawmat[:,i]
    for i,k in enumerate(EXTRA):df[k]=engmat[:,i]
    df["bottom15"]=(df.groupby("block").future_log.rank(
        method="first",ascending=True)<=15).astype(int)
    return df

def make_classifier():
    return LGBMClassifier(n_estimators=75,learning_rate=.05,num_leaves=9,
        max_depth=4,min_child_samples=90,reg_lambda=20.,
        random_state=SEED,n_jobs=1,verbosity=-1)

def predictions(allrows):
    archive=pd.read_csv(BASE/"ALL149_FROZEN_PREQUENTIAL_PREDICTIONS.csv")
    ids=sorted(archive.block.unique())
    assert len(ids)==64
    forecasts=[];fitted={}
    for k,b in enumerate(ids):
        current=allrows.loc[allrows.block==b].copy()
        signal=pd.Timestamp(current.signal.iloc[0])
        past=allrows.loc[pd.to_datetime(allrows.maturity)<signal]
        if past.block.nunique()<40:raise AssertionError("missing matured labels")
        assert (pd.to_datetime(past.maturity)<signal).all()
        rawtrain=past[list(COLRAW)].to_numpy(float)
        engtrain=past[list(COLENG)].to_numpy(float)
        if k%3==0:
            yy=past.top15.to_numpy(int)
            fitted["raw"]=make_classifier().fit(rawtrain,yy)
            fitted["eng"]=make_classifier().fit(engtrain,yy)
            fitted["trees"]=ExtraTreesClassifier(n_estimators=120,
                min_samples_leaf=30,max_features=.7,
                random_state=SEED,n_jobs=1).fit(engtrain,yy)
            fitted["scale"]=StandardScaler().fit(engtrain)
            fitted["linear"]=LogisticRegression(C=.05,max_iter=200,
                solver="liblinear",random_state=SEED).fit(
                    fitted["scale"].transform(engtrain),yy)
            print("T149E_QTR_REFIT",k,"before",str(signal.date()),flush=True)
        xr=current[list(COLRAW)].to_numpy(float)
        xe=current[list(COLENG)].to_numpy(float)
        current["O1_RAW_BAR21_LGBM"]=fitted["raw"].predict_proba(xr)[:,1]
        current["O2_ENG_OHLCV_LGBM"]=fitted["eng"].predict_proba(xe)[:,1]
        current["O3_ENG_OHLCV_EXTRA_TREES"]=fitted["trees"].predict_proba(xe)[:,1]
        current["O4_ENG_OHLCV_LOGISTIC"]=fitted["linear"].predict_proba(
            fitted["scale"].transform(xe))[:,1]
        current["last_matured_training_exit"]=str(pd.Timestamp(past.maturity.max()).date())
        forecasts.append(current)
    prediction=pd.concat(forecasts,ignore_index=True)
    cols=["block","ticker","N4_NONLINEAR_TOP15","future_log","future_excess","top15"]
    prediction=prediction.merge(archive[cols],on=["block","ticker"],validate="one_to_one",
        suffixes=("","_ref"))
    prediction["B0_ARCHIVED_N4"]=prediction.N4_NONLINEAR_TOP15
    for k in ("future_log","future_excess","top15"):
        if not np.allclose(prediction[k],prediction[k+"_ref"],atol=1e-12,rtol=0):
            raise AssertionError("Original 149 time-target score mismatch")
    assert len(prediction)==64*149
    assert (pd.to_datetime(prediction.last_matured_training_exit)<
             pd.to_datetime(prediction.signal)).all()
    return prediction,ids

def evaluate(pred,ids,prices,names,days,out):
    reference=json.loads((BASE/"RESULT.json").read_text())
    models={}
    anchors=[]
    wealths={}
    for name in METHODS:
        choices=[]
        for b in ids:
            d=pred.loc[pred.block==b].sort_values(name,ascending=False)
            top=d.head(5)
            choices.append(top.ticker.tolist())
            ref=spearmanr(d.B0_ARCHIVED_N4,d.future_excess).statistic
            own=spearmanr(d[name],d.future_excess).statistic
            anchors.append(dict(model=name,block=int(b),signal=d.signal.iloc[0],
                spearman=float(own),spearman_delta=float(own-ref),
                precision10=float(d.head(10).top15.mean()),
                precision5=float(top.top15.mean()),
                top5_forward_excess=float(top.future_excess.mean()),
                bottom15_frac=float(top.bottom15.mean()),
                best_future_in_top5=int(d.loc[d.future_log.idxmax(),"ticker"] in set(top.ticker)),
                category_count=int(top.category.nunique())))
        w,eco=portfolio(choices,ids,prices,names,days)
        wealths[name]=w
        a=pd.DataFrame([x for x in anchors if x["model"]==name])
        probs=pred[name].clip(.00001,.99999).to_numpy(float)
        y=pred.top15.to_numpy(float)
        proper=dict(brier=float(np.mean((y-probs)**2)),
            logloss=float(np.mean(-y*np.log(probs)-(1-y)*np.log(1-probs))))
        eras={}
        for nm,cond in (("2021_2023",pd.to_datetime(a.signal).dt.year<=2023),
                        ("2024_2026",pd.to_datetime(a.signal).dt.year>=2024)):
            z=a[cond]
            eras[nm]=dict(n=len(z),spearman=float(z.spearman.mean()),
                delta=float(z.spearman_delta.mean()),
                p10=float(z.precision10.mean()),bottom15=float(z.bottom15_frac.mean()))
        models[name]=dict(economic=eco,mean_spearman=float(a.spearman.mean()),
            precision10=float(a.precision10.mean()),
            precision5=float(a.precision5.mean()),
            actual_winner_found_top5=int(a.best_future_in_top5.sum()),
            top5_future_excess_log=float(a.top5_forward_excess.mean()),
            false_bottom15_fraction=float(a.bottom15_frac.mean()),
            source_risk_group_count=float(a.category_count.mean()),
            calibrated_proper_score=proper,
            spearman_uplift_ci=bootstrap(a.spearman_delta.to_numpy(float)),
            eras=eras)
        print("T149E_MODEL_SCORE",name,json.dumps(models[name],allow_nan=False),flush=True)
    original=reference["metrics"]["N4_NONLINEAR_TOP15"]["economics"]
    for metric in ("cagr","max_daily_open_drawdown","daily_es5","fee_amount_initial_units"):
        if abs(models["B0_ARCHIVED_N4"]["economic"][metric]-original[metric])>1e-10:
            raise AssertionError("Archived 149 N4 backtest parity mismatch "+metric)
    base=models["B0_ARCHIVED_N4"]
    gate={}
    for key in METHODS[1:]:
        v=models[key]
        gate[key]=bool(v["spearman_uplift_ci"]["ci95"][0]>0 and
            v["precision10"]>base["precision10"] and
            v["false_bottom15_fraction"]<base["false_bottom15_fraction"] and
            all(v["eras"][e]["delta"]>0 and v["eras"][e]["bottom15"]<
                base["eras"][e]["bottom15"] for e in ("2021_2023","2024_2026")))
    wframe=pd.DataFrame({"day":days[ids[0]*21:(ids[-1]+1)*21+1]})
    for m,w in wealths.items():wframe[m]=w
    wframe.to_csv(out/"DAILY_OPEN_COSTED_TOP5_WEALTH.csv",index=False)
    pd.DataFrame(anchors).to_csv(out/"ANCHOR_PREDICTIVE_METRICS.csv",index=False)
    return models,gate

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    out=Path(p.parse_args().out);out.mkdir(parents=True,exist_ok=False)
    df,roster,days,prices,names=dataset()
    _,O,C,V,_,_,_=load_149()
    hi,lo=load_bars(roster)
    raw,extr=feature_frames(O,hi,lo,C,V)
    df=fill_features(df,roster,raw,extr)
    pred,ids=predictions(df)
    models,gate=evaluate(pred,ids,prices,names,days,out)
    pred[["block","ticker","signal","entry","maturity","future_log","future_excess",
        "top15","bottom15","last_matured_training_exit",*METHODS]].to_csv(
        out/"ALL_9536_OHLCV_PREDICTIONS.csv",index=False)
    final=dict(status="ORIGINAL149_TRUE_OHLCV_FEATURE_CHALLENGE_COMPLETED",
        original149_source_sha256=sha(SRC/"universe.csv"),
        n_etfs=149,n_anchors=64,n_ticker_prediction_rows=len(pred),
        feature_dimensions=dict(raw_21bar=105,engineered_original=19,
            engineered_OHLCV_additions=21,category_dummies=6),
        frozen_original_N4_economic_parity=True,
        original_149_source_historical_vintage_not_true_pit=True,
        train_labels_strictly_matured=True,
        model_scores=models,
        preregistered_proper_skill_gates=gate,
        exploratory_not_promoted_to_live_strategy=True,
        notes=["Volume is ETF secondary-market traded volume, NOT primary-market fund inflows",
               "OHLCV source adjusted retrospectively; no broker spread or EUR quote",
               "149 survivor universe already repeatedly studied; further trials risk multiple-testing inflation",
               "A positive backtest CAGR is not prospective calibrated ETF alpha"])
    (out/"RESULT.json").write_text(json.dumps(final,indent=2,allow_nan=False)+"\n")
    print("T149E_OHLCV_FINAL_RESULT",json.dumps(final,allow_nan=False),flush=True)

if __name__=="__main__":main()
