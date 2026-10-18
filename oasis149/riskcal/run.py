#!/usr/bin/env python3
"""OASIS149 G3: falsify portfolio-specific extreme-loss probabilistic risk claims.

No trading or future-price access in signal calculation; outcome used only
afterwards to audit frozen as-of probability forecasts.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import ndtr
from oasis149.canonical import load_149,sha,SRC

ROOT=Path(__file__).resolve().parents[2]
ORIGIN=ROOT/"oasis149/results"
ARMS=("R0_TWO_REFERENCE","R2_ONE_PER_GROUP_EQUAL")
MODELS=("K0_MATURED_PRIOR","K1_GAUSSIAN","K2_T5_COVARIANCE","K3_HISTORICAL_BLOCKS")
THRESHOLD=-.08; H=21; START=pd.Timestamp("2021-01-01")

def make_risk_forecast(C,signal,names,index):
    hist=np.log(C[names]/C[names].shift()).replace([np.inf,-np.inf],np.nan).loc[:signal].tail(252)
    if len(hist)<252 or hist.isna().any().any():
        return None
    data=hist.to_numpy(float)
    n=len(names)
    w=np.repeat(1./n,n)
    # K1: 21d time-scaled normal variance of 1-day weighted log returns
    logrets=data@w
    sigma=max(float(np.std(logrets,ddof=1)),1e-5)*math.sqrt(H)
    gauss=float(ndtr(THRESHOLD/sigma))
    # K2: correlated Student-t common-tail shocks with a fixed shrunk covariance
    sample=np.atleast_2d(np.cov(data,rowvar=False))
    cov=.65*sample+.35*np.diag(np.diag(sample))
    chol=np.linalg.cholesky(cov+np.eye(n)*1e-10)
    rng=np.random.default_rng(20261018+index+307*n)
    Z=rng.normal(size=(1024,n))
    chi=rng.chisquare(5,size=1024)
    forward=(Z*np.sqrt(3./np.maximum(chi[:,None],1e-8)))@chol.T*math.sqrt(H)
    portfolio=np.log(np.maximum(np.exp(np.clip(forward,-1.5,1.5))@w,1e-12))
    t5=(float(np.sum(portfolio<THRESHOLD))+1)/(len(portfolio)+2)
    # K3: purely backward rolling 21-day forward horizons on as-of known data
    # overlapped block outcomes are NOT independent, explicit limitation.
    roll=np.cumsum(data,axis=0)
    accum=roll[H:]-roll[:-H]
    back=np.log(np.maximum(np.exp(np.clip(accum,-1.5,1.5))@w,1e-12))
    empirical=(float(np.sum(back<THRESHOLD))+1)/(len(back)+2)
    return {"K1_GAUSSIAN":gauss,"K2_T5_COVARIANCE":t5,
            "K3_HISTORICAL_BLOCKS":empirical,
            "estimated_portfolio_daily_vol":float(np.std(logrets,ddof=1)),
            "rolling_sample_size":len(back)}

def score(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float)
    p=np.clip(p,.001,.999)
    logloss=float(np.mean(-y*np.log(p)-(1-y)*np.log(1-p)))
    brier=float(np.mean((y-p)**2))
    predicted=(p>=.30)
    positives=y>0
    tp=np.sum(predicted & positives)
    npos=int(np.sum(positives))
    falsealarms=int(np.sum(predicted & ~positives))
    return {"n":len(y),"events":npos,"rate":float(y.mean()),
       "brier":brier,"logloss":logloss,"avg_pred":float(np.mean(p)),
       "alarms_30pct":int(np.sum(predicted)),
       "recall_30pct":float(tp/npos) if npos else None,
       "false_alarms_30pct":falsealarms}

def block_ci(rows,model,ref="K0_MATURED_PRIOR"):
    rng=np.random.default_rng(20261020)
    y=rows.y.to_numpy(float)
    diff=((y-rows[ref].to_numpy(float))**2-
          (y-rows[model].to_numpy(float))**2)
    n=len(diff);sims=[]
    for _ in range(1500):
        ix=[]
        while len(ix)<n:
            k=int(rng.integers(n))
            ix.extend([(k+i)%n for i in range(3)])
        sims.append(float(np.mean(diff[np.asarray(ix[:n],int)])))
    return {"brier_reduction_vs_matured_null":float(np.mean(diff)),
       "ci95":np.quantile(sims,[.025,.975]).tolist(),
       "months":n}

def main():
    a=argparse.ArgumentParser();a.add_argument("--out",required=True);args=a.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    roster,O,C,V,days,signals,quality=load_149()
    manifest=json.loads((ORIGIN/"MANIFEST_149.json").read_text())
    assert manifest["member_count"]==149 and manifest["n_shared_days"]==2366
    assert manifest["roster_sha256"]==sha(SRC/"universe.csv")
    forecasts=[]
    for arm in ARMS:
        p=pd.read_csv(ORIGIN/(arm+".csv"),parse_dates=["day","signal_date"])
        assert len(p)==len(days)
        assert (p.day==days).all()
        assert (p.signal_date==signals).all()
        history=[]
        for ix in range(21,len(p)-H,21):
            row=p.iloc[ix]
            signal=pd.Timestamp(row.signal_date)
            entry=pd.Timestamp(row.day);end=pd.Timestamp(days[ix+H])
            assert signal<entry<end
            names=str(row.names).split(";")
            if len(names)!=(2 if arm==ARMS[0] else 6):
                raise AssertionError("wrong holdings count on "+arm)
            if len(set(names))!=len(names):raise AssertionError("duplicate holding")
            risk=make_risk_forecast(C,signal,names,ix)
            if risk is None:continue
            open0=O.loc[entry,names].to_numpy(float)
            open1=O.loc[end,names].to_numpy(float)
            if not (np.isfinite(open0).all() and np.isfinite(open1).all()
                    and (open0>0).all() and (open1>0).all()):
                raise AssertionError("canonical 149 lost observed opening quote")
            realized=float(np.log(np.mean(open1/open0)))
            event=int(realized<THRESHOLD)
            # K0 fit only labels that COMPLETED before as-of signal date.
            matured=[z["y"] for z in history if pd.Timestamp(z["exit"])<signal]
            prior=(sum(matured)+1)/(len(matured)+2)
            forecast={k:risk[k] for k in MODELS[1:]}
            forecast["K0_MATURED_PRIOR"]=float(prior)
            item=dict(arm=arm,anchor=ix,
                signal=str(signal.date()),entry=str(entry.date()),
                exit=str(end.date()),names=";".join(names),
                y=event,forward_21d_log_return=realized,
                matured_event_count=len(matured),
                projected_daily_vol=risk["estimated_portfolio_daily_vol"],
                **forecast)
            history.append(item)
            if signal>=START:forecasts.append(item)
    frame=pd.DataFrame(forecasts)
    if len(frame)<110:raise AssertionError("insufficient 149 risk eval rows")
    if not (pd.to_datetime(frame.signal)<pd.to_datetime(frame.entry)).all():
        raise AssertionError("risk used post-trade close")
    scores={};period={};ci={}
    for arm in ARMS:
        part=frame[frame.arm==arm].reset_index(drop=True)
        scores[arm]={m:score(part.y,part[m]) for m in MODELS}
        ci[arm]={m:block_ci(part,m) for m in MODELS[1:]}
        period[arm]={}
        for label,mask in (
            ("2021_2023",pd.to_datetime(part.signal).dt.year<=2023),
            ("2024_2026",pd.to_datetime(part.signal).dt.year>=2024)):
            x=part[mask]
            period[arm][label]={m:score(x.y,x[m]) for m in MODELS}
    test=scores["R2_ONE_PER_GROUP_EQUAL"]
    def gate(model):
        return (all(test[model][key]<test[other][key]
                for key in ("brier","logloss")
                for other in ("K0_MATURED_PRIOR","K1_GAUSSIAN"))
           and ci["R2_ONE_PER_GROUP_EQUAL"][model]["ci95"][0]>0
           and all(period["R2_ONE_PER_GROUP_EQUAL"][era][model]["brier"]<
                period["R2_ONE_PER_GROUP_EQUAL"][era]["K0_MATURED_PRIOR"]["brier"]
                for era in ("2021_2023","2024_2026")))
    passes={m:gate(m) for m in ("K2_T5_COVARIANCE","K3_HISTORICAL_BLOCKS")}
    result=dict(status="OASIS149_G3_PREQUENTIAL_RISK_COMPLETED",
        severe_21day_loss_threshold_log=THRESHOLD,
        original149_exact_sha256=sha(SRC/"universe.csv"),
        no_risk_trades_generated=True,
        verified_future_label_not_available_at_signal=True,
        period_from=str(frame.signal.min()),period_to=str(frame.signal.max()),
        n_forecast_rows=len(frame),prediction_models=MODELS,
        by_policy=scores,by_era=period,bootstrap_block_ci=ci,
        gates=passes,
        caveats=["These are recurring equal-weight snapshots, NOT independently executable full-portfolio live paths",
            "2017-2026 original149 cohort repeatedly studied, not independent PIT data",
            "21day historical blocks overlapped heavily; bootstrap unit=21day anchor",
            "event_count_can_be_very_low","actual spreads and ETF quote currencies not verified"])
    frame.to_csv(out/"RISK_FORECASTS_149.csv",index=False)
    (out/"RESULT_149_G3.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("OASIS149_G3_RESULT "+json.dumps(result,allow_nan=False),flush=True)

if __name__=="__main__":main()
