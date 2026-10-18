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
SERIES=("VIX","VVIX","OVX","GVZ","VXEEM")
BASE="https://cdn-api.cboe.com/api/global/us_indices/daily_prices/"
EVAL_START=pd.Timestamp("2021-01-01")
SEED=20261018
PIT_PROOF=False

def get_series(series,out):
    """Official CBOE daily index close, FULL fetched raw file and canonical slice."""
    import subprocess
    url=BASE+series+"_History.csv"
    command=["curl","--http1.1","--compressed","-L","--max-time","28",
        "--connect-timeout","7","--fail","--silent","--show-error",
        "-A","Mozilla/5.0 (ETF scientific replication)",url]
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=34)
    if result.returncode!=0:
        raise AssertionError("CBOE URL acquisition failed "+series+": "+result.stderr.decode()[:250])
    raw=result.stdout
    if len(raw)<10000:
        raise AssertionError("CBOE full daily series too small "+series+" "+str(len(raw)))
    (out/("RAW_"+series+".csv")).write_bytes(raw)
    table=pd.read_csv(io.BytesIO(raw))
    table.columns=[str(x).strip().upper() for x in table.columns]
    if "DATE" not in table:
        raise AssertionError("CBOE date header changed "+series+" "+str(list(table)))
    if "CLOSE" not in table:
        raise AssertionError("CBOE historical close header changed "+series+" "+str(list(table)))
    date=pd.to_datetime(table["DATE"],format="%m/%d/%Y",errors="coerce")
    if date.isna().any():
        # Historical source may switch date format; do not silently discard.
        raise AssertionError("Unrecognized CBOE date format "+series)
    values=pd.to_numeric(table["CLOSE"],errors="coerce")
    if date.duplicated().any():
        raise AssertionError("Duplicate CBOE dates "+series)
    frame=pd.DataFrame({"observation_date":date,"value":values})
    if frame.value.isna().any():
        # A few historical dates have blank official close; retain source but
        # never interpolate into as-of signals.
        frame=frame.dropna(subset=["value"])
    frame=frame[(frame.observation_date>=pd.Timestamp("2014-01-01"))&
                (frame.observation_date<=pd.Timestamp("2026-07-31"))]
    if len(frame)<1900 or frame.observation_date.min()>pd.Timestamp("2016-01-01"):
        raise AssertionError("Insufficient official CBOE close history "+series+" "+str(len(frame)))
    if not np.isfinite(frame.value).all() or (frame.value<=0).any():
        raise AssertionError("Nonpositive/invalid CBOE option index Close "+series)
    frame.to_csv(out/(series+".csv"),index=False)
    return frame.set_index("observation_date").sort_index().value.astype(float)

def download(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    series={n:get_series(n,out) for n in SERIES}
    receipt={"status":"OFFICIAL_CBOE_FIVE_IMPLIED_VOL_HISTORY_OBSERVED",
       "retrieved_utc":pd.Timestamp.now(tz="UTC").isoformat(),
       "source_historical_revision_proof_missing":True,
       "actual_asof_lag_calendar_days":7,
       "source_template":BASE+"{INDEX}_History.csv",
       "observed_through_inclusive":"2026-07-31",
       "series":{n:{"n":len(s),"start":str(s.index.min().date()),
                    "end":str(s.index.max().date()),
                    "sha256":sha(out/(n+".csv")),
                    "raw_sha256":sha(out/("RAW_"+n+".csv"))}
                 for n,s in series.items()}}
    (out/"DATA_RECEIPT.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print("OASIS_CBOE_DATA_RECEIPT "+json.dumps(receipt),flush=True)

def load(out):
    out=Path(out)
    receipt=json.loads((out/"DATA_RECEIPT.json").read_text())
    assert receipt["source_historical_revision_proof_missing"] is True
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
    """Index closings must precede signal by >=7 calendar days, never interpolate."""
    cutoff=pd.Timestamp(signal)-pd.Timedelta(days=7)
    previous_cutoff=cutoff-pd.Timedelta(days=21)
    now={};past={};dates={}
    for n,s in values.items():
        t=s.loc[:cutoff]
        p=s.loc[:previous_cutoff]
        if t.empty or p.empty:return None
        now[n]=float(t.iloc[-1]);past[n]=float(p.iloc[-1])
        seen=t.index[-1];old=p.index[-1]
        if (cutoff-seen).days>14 or (previous_cutoff-old).days>14:
            return None
        if seen>cutoff or old>previous_cutoff:
            raise AssertionError("Future option market close leak")
        dates[n]=str(seen.date())
    level=np.array([math.log1p(now[n]) for n in SERIES],float)
    earlier=np.array([math.log1p(past[n]) for n in SERIES],float)
    if not np.isfinite(level).all() or not np.isfinite(earlier).all():
        raise AssertionError("Bad implied-vol numerical source")
    return level,level-earlier,dates

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
        interactions=np.r_[level[0]*groupdiff,
            level[3]*groupdiff[5],level[2]*groupdiff[5],
            level[4]*groupdiff[3],level[1]*groupdiff[0]]
        h5=np.r_[x2,level,delta,interactions]
        if len(h5)!=33 or len(h6)!=18:
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
            ("H5_CBOE_VOL_CONDITIONAL","x5",.08),
            ("H6_CBOE_VOL_COMPACT","x6",.08)):
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
    models=("H0_PRIOR","H2_PRICE_GROUP","H5_CBOE_VOL_CONDITIONAL","H6_CBOE_VOL_COMPACT")
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
    group=overall["challenge"];primary=group["H5_CBOE_VOL_CONDITIONAL"]
    accepted=(
        all(primary[k]<group[m][k] for k in ("brier","log_loss")
            for m in ("H0_PRIOR","H2_PRICE_GROUP"))
        and bootstrap["H5_CBOE_VOL_CONDITIONAL"]["95pct_circular_block_CI"][0]>0
        and all(by_era["challenge"][era]["H5_CBOE_VOL_CONDITIONAL"]["brier"]<
            by_era["challenge"][era]["H0_PRIOR"]["brier"] for era in ("2021_2023","2024_2026")))
    shadows=[]
    for anchor,group in pred[pred.pair_type=="challenge"].groupby("anchor"):
        valid=group[(group.H5_CBOE_VOL_CONDITIONAL>.65)&
                    (group.H5_CBOE_VOL_CONDITIONAL>group.H0_PRIOR+.10)]
        if valid.empty:continue
        win=valid.nlargest(1,"H5_CBOE_VOL_CONDITIONAL").iloc[0]
        shadows.append({"anchor":int(anchor),"candidate":win.asset,"held":win.held,
            "net_return_log":float(win.realized_net_relative_log),
            "prob":float(win.H5_CBOE_VOL_CONDITIONAL)})
    return dict(status="ORIGINAL149_CBOE_G4B_EXPLORATORY_COMPLETE",
       experiment_period="2021-01 to 2026-07",
       original_149_exact=True,
       source_G0_SHA=sha(SRC/"universe.csv"),
       macros=receipt,
       CBOE_HISTORICAL_VINTAGE_VALIDATED=False,
       macro_lag_calendar_days=7,
       model_parameters_frozen_before_result=True,
       no_trading_policy_simulated=True,
       no_training_on_unmatured_forward_labels=True,
       independent_prospective_holdout=False,
       frozen_21session_anchor_count=int(pred.anchor.nunique()),
       paired_rows=len(pred),G4b_score_gate="PASS_EXPLORATORY_ONLY" if accepted else "FAIL",
       proper_scores=overall,era_scores=by_era,paired_anchor_bootstrap=bootstrap,
       H5_shadow=dict(n=len(shadows),
          n_winning=sum(x["net_return_log"]>0 for x in shadows),
          mean_net_log=float(np.mean([x["net_return_log"] for x in shadows])) if shadows else None,
          decisions=shadows),
       limitations=["CBOE published historical index values, not independently verified PIT vintage despite 7 day lag",
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
