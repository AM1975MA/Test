#!/usr/bin/env python3
"""Scientific G5: CBOE implied volatility forecasting ETF future realized variance.

No trades, no model selection based on wealth, no alpha. Each monthly anchor
uses the frozen R2 ETF names, prior opens and only >=7-day-old option markets.
Matured pre-2021 labels are permitted for per-category calibration, never
within the anchor's future.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from oasis149.canonical import load_149,sha,SRC
from oasis149.cboe_g4b.experiment import load as cboe_load,macro_asof,SERIES
ROOT=Path(__file__).resolve().parents[3]
FROZEN=ROOT/"oasis149/results"
SRC_CBOE=ROOT/"oasis149/cboe_g4b/results/source"
EVAL_START=pd.Timestamp("2021-01-01")
N_NEXT=21
MAPPED=("C01_US_BROAD_STYLE","C02_US_SECTOR_THEME","C03_DEVELOPED_GLOBAL",
    "C04_EMERGING","C06_REAL_ASSETS")
BONDS="C05_BONDS_CASH_CREDIT"
MODELS=("K0_LAST63","K1_EWMA126","K2_CBOE_CALIBRATED","K3_LOG_BLEND")
SEED=20261018

def qlike(ys,ps):
    y=np.maximum(np.asarray(ys,float),1e-12)
    p=np.maximum(np.asarray(ps,float),1e-12)
    r=y/p
    return r-np.log(r)-1

def observed_and_base(O,signal,entry,end,ticker):
    valid=pd.to_numeric(O[ticker],errors="coerce").loc[:signal].dropna()
    logopen=np.log(valid.where(valid>0)).diff().dropna().to_numpy(float)
    if len(logopen)<126 or not np.isfinite(logopen).all():
        raise AssertionError("Past 126 observed opens absent for "+ticker)
    k0=float(N_NEXT*np.mean(logopen[-63:]**2))
    x=logopen[-126:]**2
    weights=.97**np.arange(len(x)-1,-1,-1)
    k1=float(N_NEXT*np.average(x,weights=weights))
    # exactly 22 opening observations and 21 chronological increments
    forward=O.loc[entry:end,ticker].astype(float).to_numpy()
    if len(forward)!=22 or (forward<=0).any() or not np.isfinite(forward).all():
        raise AssertionError("Future evaluation must have exactly 22 observed entry/exit opens")
    realized=float(np.sum(np.diff(np.log(forward))**2))
    return realized,max(k0,1e-9),max(k1,1e-9)

def implied_by_class(group,level):
    vol=np.expm1(np.asarray(level,float))
    d={n:float(v) for n,v in zip(SERIES,vol)}
    if group in ("C01_US_BROAD_STYLE","C02_US_SECTOR_THEME",
                 "C03_DEVELOPED_GLOBAL"):
        iv=d["VIX"]
    elif group=="C04_EMERGING":
        iv=d["VXEEM"]
    elif group=="C06_REAL_ASSETS":
        iv=math.sqrt(d["OVX"]*d["GVZ"])
    elif group==BONDS:
        return None
    else:raise AssertionError("new group not in frozen taxonomy")
    if not math.isfinite(iv) or iv<=0:
        raise AssertionError("invalid implied-vol class index")
    return max(N_NEXT/252.*(iv/100)**2,1e-9)

def fit_history_multiplier(history,group,signal):
    # Prior observations are anchored 21 market sessions apart, and latest
    # matured endpoint MUST be strictly earlier than this signal close.
    prev=[x["observed_RV21"]/x["unscaled_CBOE"]
         for x in history[group] if x["end"]<signal]
    if len(prev)<8:return None,len(prev)
    return float(np.clip(np.median(prev),.10,10.)),len(prev)

def generate():
    universe,O,C,V,days,signals,quality=load_149()
    metadata=json.loads((FROZEN/"MANIFEST_149.json").read_text())
    assert metadata["member_count"]==149 and metadata["roster_sha256"]==sha(SRC/"universe.csv")
    ledger=pd.read_csv(FROZEN/"R2_ONE_PER_GROUP_EQUAL.csv",parse_dates=["day","signal_date"])
    assert len(ledger)==2366 and (ledger.day==days).all()
    assert (ledger.signal_date==signals).all()
    options,receipt=cboe_load(SRC_CBOE)
    assert receipt["status"]=="OFFICIAL_CBOE_FIVE_IMPLIED_VOL_HISTORY_OBSERVED"
    groups=universe.set_index("ticker").macro_category.to_dict()
    history={g:[] for g in set(groups.values())}
    results=[]
    total_anchors=0
    for j in range(21,len(ledger)-N_NEXT,21):
        d=ledger.iloc[j]
        signal=pd.Timestamp(d.signal_date)
        entry=pd.Timestamp(d.day)
        end=pd.Timestamp(days[j+N_NEXT])
        assert signal<entry<end
        names=str(d.names).split(";")
        if len(names)!=6 or len(set(names))!=6:
            raise AssertionError("Not exactly six portfolios at anchor "+str(j))
        if set(groups[t] for t in names)!=set(history):
            raise AssertionError("One ETF per group taxonomy broken")
        observed_opt=macro_asof(options,signal)
        if observed_opt is None:
            raise AssertionError("Missing official CBOE as-of close at "+str(signal))
        level,delta,evidence=observed_opt
        candidates=[]
        # Predicted risk is calculated before revealed 21d labels, but
        # labels are computed for diagnostics in the same time loop.
        for name in names:
            category=groups[name]
            forward,k0,k1=observed_and_base(O,signal,entry,end,name)
            raw_cboe=implied_by_class(category,level)
            if raw_cboe is None:
                calibrated=float("nan")
                blended=float("nan")
                matured=0
            else:
                scale,matured=fit_history_multiplier(history,category,signal)
                if scale is None:
                    # Early development-only pre-2021 anchors have insufficient
                    # ratio history. Never backfill using later outcomes.
                    calibrated=float("nan")
                    blended=float("nan")
                else:
                    calibrated=max(raw_cboe*scale,1e-9)
                    blended=math.sqrt(k0*calibrated)
            candidate=dict(anchor=int(j),signal=str(signal.date()),
                entry=str(entry.date()),end=str(end.date()),class_group=category,
                ticker=name,realized_RV21=forward,
                K0_LAST63=k0,K1_EWMA126=k1,
                K2_CBOE_CALIBRATED=calibrated,K3_LOG_BLEND=blended,
                unscaled_CBOE=raw_cboe if raw_cboe is not None else float("nan"),
                matured_prior_category_anchors=matured,
                cboe_source_dates=json.dumps(evidence,sort_keys=True))
            candidates.append(candidate)
        # Adding current label to history is okay ONLY because subsequent
        # retrieval applies the strict end < signal maturity filter.
        for item in candidates:
            if item["class_group"]!=BONDS:
                history[item["class_group"]].append(dict(end=end,
                   observed_RV21=item["realized_RV21"],
                   unscaled_CBOE=item["unscaled_CBOE"]))
            if signal>=EVAL_START:
                if item["class_group"] in MAPPED and not np.isfinite(
                    item["K2_CBOE_CALIBRATED"]):
                    raise AssertionError("Insufficient matured CBOE calibration in test period")
                results.append(item)
        if signal>=EVAL_START:total_anchors+=1
    frame=pd.DataFrame(results)
    if len(frame)!=384 or total_anchors!=64:
        raise AssertionError(f"Original149 risk forecast sample changed: {len(frame)} {total_anchors}")
    assert (pd.to_datetime(frame.signal)<pd.to_datetime(frame.entry)).all()
    assert (pd.to_datetime(frame.entry)<pd.to_datetime(frame.end)).all()
    assert frame.groupby("anchor").size().eq(6).all()
    assert frame[frame.class_group!=BONDS].shape[0]==320
    return frame,receipt

def scores(frame):
    results={}
    for key in MODELS:
        x=frame[frame[key].notna()]
        q=qlike(x.realized_RV21,x[key])
        logs=np.log(np.maximum(x.realized_RV21,1e-12)/np.maximum(x[key],1e-12))
        results[key]={"n":len(x),"QLIKE":float(np.mean(q)),
          "log_RV_MSE":float(np.mean(logs**2)),
          "mean_predicted_RV21":float(x[key].mean()),
          "mean_realized_RV21":float(x.realized_RV21.mean()),
          "mean_predicted_over_actual":float(x[key].mean()/x.realized_RV21.mean()),
          "QLIKE_median":float(np.median(q))}
    return results

def bootstrap(frame,arm):
    # Paired loss difference, resampled at the 21d ANCHOR and not ETF-row.
    a=frame[frame.class_group.isin(MAPPED)]
    array=[]
    for _,part in a.groupby("anchor"):
        diff=float(np.mean(qlike(part.realized_RV21,part.K0_LAST63)
                   -qlike(part.realized_RV21,part[arm])))
        array.append(diff)
    array=np.array(array);n=len(array)
    assert n==64
    rng=np.random.default_rng(SEED)
    out=[]
    for _ in range(1500):
        ix=[]
        while len(ix)<n:
            k=int(rng.integers(n))
            ix.extend((k+j)%n for j in range(3))
        out.append(float(np.mean(array[np.asarray(ix[:n],int)])))
    return {"n_nonoverlapping_anchors":n,
         "improvement_QLIKE_vs_K0":float(array.mean()),
         "ci95":np.quantile(out,[.025,.975]).tolist()}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    args=p.parse_args()
    dest=Path(args.out);dest.mkdir(parents=True,exist_ok=False)
    frame,receipt=generate()
    mapped=frame[frame.class_group.isin(MAPPED)]
    overall=scores(mapped)
    by_era={}
    for era,mask in (("2021_2023",pd.to_datetime(mapped.signal).dt.year<=2023),
                     ("2024_2026",pd.to_datetime(mapped.signal).dt.year>=2024)):
        by_era[era]=scores(mapped[mask])
    by_group={group:scores(frame[frame.class_group==group])
              for group in sorted(frame.class_group.unique())}
    ci={key:bootstrap(mapped,key) for key in MODELS[1:]}
    gates={}
    for method in ("K2_CBOE_CALIBRATED","K3_LOG_BLEND"):
        x=overall[method]
        gates[method]=(all(x["QLIKE"]<overall[c]["QLIKE"] for c in ("K0_LAST63","K1_EWMA126")) and
            ci[method]["ci95"][0]>0 and
            all(by_era[e][method]["QLIKE"]<by_era[e]["K0_LAST63"]["QLIKE"]
                for e in ("2021_2023","2024_2026")))
    output=dict(status="ORIGINAL149_CBOE_G5_RISK_VARIANCE_COMPLETED",
        original149_exact_SHA=sha(SRC/"universe.csv"),
        mapped_groups=MAPPED,unmapped_group=BONDS,
        21_session_forward_open_to_open_RV_definition="sum of 21 squared open-to-open log returns",
        n_orig_149_etfs=149,n_anchors=64,n_positions=384,n_mapped_positions=320,
        no_switches_or_returns_optimized=True,
        risk_model_only_not_alpha=True,
        source_option_data=receipt,
        source_vintage_not_PIT_verified=True,
        score_mapped=overall,score_by_era=by_era,score_by_group=by_group,
        circular_3_anchor_bootstrap=ci,
        preregistered_gates={k:bool(v) for k,v in gates.items()},
        limitations=["Already-mined 149 universe", "64 anchors not 320 independent time experiments",
           "6 categories overlap economically and contain leverage/strategy risks",
           "Option IV at 30d includes risk premium, not statistically direct RV forecast",
           "No group-matched implied-vol for bonds; K2/K3 exclude bond",
           "Source historical as-of vintages and broker fills unverified",
           "Risk variance calibration is not portfolio tail or drawdown prediction"])
    frame.to_csv(dest/"FORECAST_149_21D_RV.csv",index=False)
    (dest/"RESULT.json").write_text(json.dumps(output,indent=2,allow_nan=False)+"\n")
    print("OASIS149_CBOE_G5_RISK_RESULT "+json.dumps(output,allow_nan=False),flush=True)
if __name__=="__main__":main()
