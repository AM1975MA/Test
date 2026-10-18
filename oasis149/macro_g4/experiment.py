#!/usr/bin/env python3
"""OASIS149 G4: observe quarantined FRED macro as-of, predict paired net ETF edge.

Killer checks: source dated, conservative >=7-calendar-day lag, no future
label within fit, same 149 original universe, model G5 uncertainty veto.
PIT vintage of FRED revisions is UNVERIFIED; no trading from these signals.
"""
from __future__ import annotations
import argparse,hashlib,io,json,math
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from oasis149.canonical import load_149,sha,SRC
from oasis_v2.g1.pairwise import make_dataset,summarize, GROUPS, COST
SERIES=("VIXCLS","DGS2","DGS10","BAMLH0A0HYM2")
BASE="https://fred.stlouisfed.org/graph/fredgraph.csv?id="
EVAL_START=pd.Timestamp("2021-01-01")
SEED=20261018
PIT_PROOF=False

def get_series(series,out):
    url=BASE+series
    resp=requests.get(url,timeout=60,headers={"User-Agent":"OASIS149-Scientific-Research/1.0"})
    resp.raise_for_status()
    raw=resp.content
    if len(raw)<15000:raise AssertionError(f"FRED returned too little historical data: {series}: {len(raw)}")
    parsed=pd.read_csv(io.BytesIO(raw))
    dates=parsed.columns[0]
    if not ({"observation_date","DATE","date"} & {dates}):
        raise AssertionError(f"Unexpected FRED series schema: {series}: {list(parsed)}")
    if series not in parsed.columns:raise AssertionError(f"FRED series column missing {series}")
    date=pd.to_datetime(parsed[dates],errors="coerce")
    values=pd.to_numeric(parsed[series].replace(".",np.nan),errors="coerce")
    df=pd.DataFrame({"observation_date":date,"value":values}).dropna()
    if df.observation_date.duplicated().any() or df.empty:raise AssertionError(f"duplicate/empty series {series}")
    df=df[(df.observation_date>=pd.Timestamp("2014-01-01"))&
          (df.observation_date<=pd.Timestamp("2026-07-31"))]
    if len(df)<1900 or df.observation_date.min()>pd.Timestamp("2016-01-01"):
        raise AssertionError(f"Not enough historical macro observations for {series}: {len(df)}")
    df.to_csv(out/(series+".csv"),index=False)
    return df.set_index("observation_date").sort_index().value.astype(float)

def download(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    sources={n:get_series(n,out) for n in SERIES}
    meta={"status":"FRED_SOURCE_VINTAGE_UNVERIFIED",
          "retrieved_utc":pd.Timestamp.now(tz="UTC").isoformat(),
          "asof_conservative_calendar_lag_days":7,
          "no_genuine_alfred_vintage_data":True,
          "observed_through_inclusive":"2026-07-31",
          "revision_risk":True,
          "source":BASE+"<series>",
          "series":{n:{"n":len(s),"start":str(s.index.min().date()),
                         "end":str(s.index.max().date()),
                         "sha256":sha(out/(n+".csv"))} for n,s in sources.items()}}
    (out/"DATA_RECEIPT.json").write_text(json.dumps(meta,indent=2)+"\n")
    print("OASIS_MACRO_DATA_RECEIPT "+json.dumps(meta),flush=True)

def load(out):
    out=Path(out)
    receipt=json.loads((out/"DATA_RECEIPT.json").read_text())
    assert receipt["no_genuine_alfred_vintage_data"] is True
    series={}
    for n in SERIES:
        csv=out/(n+".csv")
        if sha(csv)!=receipt["series"][n]["sha256"]:raise AssertionError("FRED hash drift "+n)
        r=pd.read_csv(csv,parse_dates=["observation_date"])
        s=r.set_index("observation_date").value.sort_index()
        if s.index.duplicated().any():raise AssertionError("macro date duplicate")
        series[n]=s
    return series,receipt

def macro_asof(values,signal):
    """All observations lie <= signal - 7 days; none interpolate future values."""
    cutoff=pd.Timestamp(signal)-pd.Timedelta(days=7)
    oldcut=cutoff-pd.Timedelta(days=21)
    now={}
    previous={}
    evidence={}
    for n,s in values.items():
        v=s.loc[:cutoff]
        p=s.loc[:oldcut]
        if v.empty or p.empty:return None
        seen=v.index[-1];earlier=p.index[-1]
        if (cutoff-seen).days>14 or (oldcut-earlier).days>14:
            return None
        now[n]=float(v.iloc[-1]);previous[n]=float(p.iloc[-1])
        evidence[n]=str(seen.date())
        if seen>cutoff or earlier>oldcut:raise AssertionError("MACRO FUTURE LEAK")
    # Unit transforms and advance economic structure as frozen.
    level=np.array([
        math.log1p(max(now["VIXCLS"],0.)),
        (now["DGS10"]-now["DGS2"])/100.,
        now["DGS10"]/100.,
        now["BAMLH0A0HYM2"]/100.
    ],float)
    prior=np.array([
        math.log1p(max(previous["VIXCLS"],0.)),
        (previous["DGS10"]-previous["DGS2"])/100.,
        previous["DGS10"]/100.,
        previous["BAMLH0A0HYM2"]/100.
    ])
    if not (np.isfinite(level).all() and np.isfinite(prior).all()):
        raise AssertionError("invalid FRED numeric input")
    return level,level-prior,evidence

def prepare_pairs():
    roster,O,C,V,days,signals,quality=load_149()
    # G0 and G1 original149 shadow portfolio archives have independent receipts.
    base=Path(__file__).resolve().parents[1]/"results"
    data=json.loads((base/"MANIFEST_149.json").read_text())
    assert data["member_count"]==149 and data["roster_sha256"]==sha(SRC/"universe.csv")
    p3=pd.read_csv(base/"P3_149_SHADOW.csv",parse_dates=["day","signal_date"])
    assert len(p3)==2366 and (p3.day==days).all()
    assert (p3.signal_date==signals).all()
    ds=make_dataset(roster,C,O,p3)
    assert ds.anchor.nunique()>=100
    return ds

def feature_vectors(ds,sources):
    xs=[];bad_signals=[]
    cats=set(GROUPS)
    grpindex={n:i for i,n in enumerate(GROUPS)}
    for signal in sorted(ds.signal.unique()):
        v=macro_asof(sources,pd.Timestamp(signal))
        if v is None:bad_signals.append(signal)
        else:xs.append((signal,v))
    if bad_signals:
        raise AssertionError("Macro-asof gate failed; missing dates, do not silently drop: "+str(bad_signals[:7]))
    cache=dict(xs)
    # Pass complete independent data publication evidence forward with each sample.
    feats=[]
    for rec in ds.itertuples(index=False):
        level,delta,evidence=cache[rec.signal]
        x2=np.asarray(rec.x2,float)
        if len(x2)!=13:raise AssertionError("unexpected G1 group residual dimension")
        groupdiff=np.zeros(6)
        groupdiff[grpindex[rec.source_group_a]]+=1
        groupdiff[grpindex[rec.source_group_b]]-=1
        h6=np.r_[x2,level]
        h5=np.r_[x2,level,delta,level[0]*groupdiff,level[3]*groupdiff]
        if len(h5)!=33 or len(h6)!=17:
            raise AssertionError("macro feature design drift")
        feats.append((h5.tolist(),h6.tolist(),
                      json.dumps(evidence,sort_keys=True)))
    ds=ds.copy()
    ds["x5"]=[x[0] for x in feats]
    ds["x6"]=[x[1] for x in feats]
    ds["source_observations"]=[x[2] for x in feats]
    return ds

def predict(ds):
    evalanchor=sorted(ds.loc[pd.to_datetime(ds.signal)>=EVAL_START,"anchor"].unique())
    predictions=[]
    for anchor in evalanchor:
        test=ds[ds.anchor==anchor].copy()
        now=pd.Timestamp(test.signal.iloc[0])
        train=ds[pd.to_datetime(ds.label_matures)<now].copy()
        if train.anchor.nunique()<24:continue
        y=train.y.to_numpy(int)
        if len(set(y))<2:raise AssertionError("training events degenerate")
        freq=train.groupby("pair_type").y.mean().to_dict()
        test["H0_PRIOR"]=test.pair_type.map(freq).fillna(float(np.mean(y))).clip(.1,.9).to_numpy(float)
        n_rows=train.groupby("anchor").anchor.transform("size").to_numpy(float)
        sample_weight=(len(train)/train.anchor.nunique())/n_rows
        for col,key,l2 in (
            ("H2_PRICE_GROUP","x2",.15),
            ("H5_MACRO_CONDITIONAL","x5",.08),
            ("H6_MACRO_COMPACT","x6",.08)):
            scaler=StandardScaler()
            x=scaler.fit_transform(np.stack(train[key]))
            xx=scaler.transform(np.stack(test[key]))
            model=LogisticRegression(C=l2,solver="liblinear",max_iter=400,random_state=SEED)
            model.fit(x,y,sample_weight=sample_weight)
            test[col]=model.predict_proba(xx)[:,1]
        test["latest_train_maturity"]=train.label_matures.max()
        assert (pd.to_datetime(test.latest_train_maturity)<pd.to_datetime(test.signal)).all()
        predictions.append(test)
        if len(predictions) in (1,12,40,64):
            print("G4_MACRO_FIT",len(predictions),test.signal.iloc[0],
                "matured_anchor",train.anchor.nunique(),flush=True)
    if not predictions:raise AssertionError("no macro out-of-dev")
    pred=pd.concat(predictions,ignore_index=True)
    if pred.anchor.nunique()!=64 or len(pred)!=5120:raise AssertionError(
        f"Change in previously frozen G1 anchor/test set: {pred.anchor.nunique()} {len(pred)}")
    return pred

def confidence(pred,target,ref,seed=SEED):
    sample=pred[pred.pair_type=="challenge"]
    anchor=sorted(sample.anchor.unique())
    arr=[]
    for a in anchor:
        sub=sample[sample.anchor==a]
        arr.append(float(np.mean((sub.y-sub[ref])**2-(sub.y-sub[target])**2)))
    a=np.array(arr,float);rng=np.random.default_rng(seed)
    n=len(a);reps=[]
    for _ in range(1500):
        ix=[]
        while len(ix)<n:
            j=int(rng.integers(0,n))
            ix.extend((j+i)%n for i in range(3))
        reps.append(float(a[np.array(ix[:n],int)].mean()))
    return {"paired_mean_brier_improvement":float(a.mean()),
            "95pct_circular_block_CI":np.quantile(reps,[.025,.975]).tolist(),
            "n_nonoverlapping_anchors":n}

def summarize_result(pred,receipt):
    models=("H0_PRIOR","H2_PRICE_GROUP","H5_MACRO_CONDITIONAL","H6_MACRO_COMPACT")
    overall={};by_era={}
    for task in ("challenge","probe"):
        x=pred[pred.pair_type==task]
        overall[task]={m:summarize(x.y,x[m]) for m in models}
        by_era[task]={}
        for era,mask in (("2021_2023",pd.to_datetime(x.signal).dt.year<=2023),
                         ("2024_2026",pd.to_datetime(x.signal).dt.year>=2024)):
            z=x[mask]
            by_era[task][era]={m:summarize(z.y,z[m]) for m in models}
    bootstrap={c:confidence(pred,c,"H0_PRIOR") for c in models[1:]}
    group=overall["challenge"];primary=group["H5_MACRO_CONDITIONAL"]
    accepted=(
        all(primary[k]<group[m][k] for k in ("brier","log_loss")
            for m in ("H0_PRIOR","H2_PRICE_GROUP"))
        and bootstrap["H5_MACRO_CONDITIONAL"]["95pct_circular_block_CI"][0]>0
        and all(by_era["challenge"][era]["H5_MACRO_CONDITIONAL"]["brier"]<
            by_era["challenge"][era]["H0_PRIOR"]["brier"] for era in ("2021_2023","2024_2026")))
    shadows=[]
    for anchor,group in pred[pred.pair_type=="challenge"].groupby("anchor"):
        valid=group[(group.H5_MACRO_CONDITIONAL>.65)&
                    (group.H5_MACRO_CONDITIONAL>group.H0_PRIOR+.10)]
        if valid.empty:continue
        win=valid.nlargest(1,"H5_MACRO_CONDITIONAL").iloc[0]
        shadows.append({"anchor":int(anchor),"candidate":win.asset,"held":win.held,
            "net_return_log":float(win.realized_net_relative_log),
            "prob":float(win.H5_MACRO_CONDITIONAL)})
    return dict(status="ORIGINAL149_MACRO_G4_EXPLORATORY_COMPLETE",
       experiment_period="2021-01 to 2026-07",
       original_149_exact=True,
       source_G0_SHA=sha(SRC/"universe.csv"),
       macros=receipt,
       FRED_REALTIME_VINTAGE_VALIDATED=False,
       macro_lag_calendar_days=7,
       model_parameters_frozen_before_result=True,
       no_trading_policy_simulated=True,
       no_training_on_unmatured_forward_labels=True,
       independent_prospective_holdout=False,
       frozen_21session_anchor_count=int(pred.anchor.nunique()),
       paired_rows=len(pred),G4_score_gate="PASS_EXPLORATORY_ONLY" if accepted else "FAIL",
       proper_scores=overall,era_scores=by_era,paired_anchor_bootstrap=bootstrap,
       H5_shadow=dict(n=len(shadows),
          n_winning=sum(x["net_return_log"]>0 for x in shadows),
          mean_net_log=float(np.mean([x["net_return_log"] for x in shadows])) if shadows else None,
          decisions=shadows),
       limitations=["FRED latest revised vintages: NOT PIT despite 7 day lag",
           "original149 cohort already heavily mined",
           "shared holdings/challenger outcomes within anchor correlated",
           "Yahoo adjustment does not prove open fills and real spreads",
           "group exposures labels static across sample; ETF inception/delisting not PIT"])
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    src,receipt=load(args.source)
    ds=feature_vectors(prepare_pairs(),src)
    predictions=predict(ds)
    result=summarize_result(predictions,receipt)
    predictions.drop(columns=["x1","x2","x3","x5","x6"],errors="ignore").to_csv(
        out/"PREDICTIONS_ASOF_149.csv",index=False)
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("OASIS149_G4_MACRO_RESULT "+json.dumps(result,allow_nan=False),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--download",action="store_true")
    p.add_argument("--source")
    p.add_argument("--out",required=True)
    args=p.parse_args()
    if args.download:download(args.out)
    else:
        if not args.source:raise ValueError("--source required for model")
        # Avoid nested argparser and use the same scientific function code.
        src,receipt=load(args.source)
        dest=Path(args.out);dest.mkdir(parents=True,exist_ok=False)
        ds=feature_vectors(prepare_pairs(),src)
        pred=predict(ds)
        result=summarize_result(pred,receipt)
        pred.drop(columns=["x1","x2","x3","x5","x6"],errors="ignore").to_csv(
            dest/"PREDICTIONS_ASOF_149.csv",index=False)
        (dest/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
        print("OASIS149_G4_MACRO_RESULT "+json.dumps(result,allow_nan=False),flush=True)
