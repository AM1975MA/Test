#!/usr/bin/env python3
"""V3 L03.2: causal RMT spectral state vs frozen market-only expert gate.

Predict next-21D winner-capture advantage of frozen Tail vs frozen Pairwise.
ONE targeted intervention: add three ex-ante 63D ETF correlation spectral
features (lambda1 share, top3 share, normalized effective rank) to the
same L2 logistic/C=.1 gate, fixed calendar, labels and mature cutoffs.
Also include market-only, RMT-only and Laplace prior diagnostics.
No expert refit, no new trading policy, no CAGR or PnL.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss

V3=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(V3/"src"))
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder

MARKET=["spy_ret21","spy_ret63","spy_ret126","spy_vol21",
        "spy_downvol63","breadth21","dispersion21"]
RMT=["rmt_lambda1_fraction","rmt_top3_fraction","rmt_effective_rank"]
ARMS={"PRIOR":[],"MARKET_ONLY":MARKET,"RMT_ONLY":RMT,"MARKET_PLUS_RMT":MARKET+RMT}
BLOCK=6

def spectral_state(close,dates):
    """All samples end on date <= signal; no zero-filling missing prices."""
    lr=np.log(close.where(close>0)).diff()
    results=[]
    for date in dates:
        at=close.index.get_indexer([date])[0]
        assert at>=63,(date,at)
        arr=lr.iloc[at-62:at+1].to_numpy(dtype=float)
        assert arr.shape[0]==63
        good=np.isfinite(arr).all(axis=0)&(np.nanstd(arr,axis=0)>1e-9)
        X=arr[:,good]
        assert X.shape[1]>=40,(date,X.shape)
        X=(X-X.mean(axis=0))/X.std(axis=0,ddof=0)
        # 63x63 Gram yields same nonzero spectrum as N-ETF correlation.
        eigen=np.linalg.eigvalsh((X@X.T)/63)
        eigen=np.maximum(eigen,0)[::-1]
        assert eigen[0]>0 and eigen.sum()>0
        weights=eigen/eigen.sum()
        nz=weights[weights>1e-12]
        erank=float(np.exp(-np.dot(nz,np.log(nz)))/min(63,X.shape[1]))
        results.append({"signal_date":pd.Timestamp(date),
             "rmt_lambda1_fraction":float(weights[0]),
             "rmt_top3_fraction":float(weights[:3].sum()),
             "rmt_effective_rank":erank,"rmt_n_tickers":int(X.shape[1])})
    out=pd.DataFrame(results)
    assert not out.signal_date.duplicated().any()
    assert np.isfinite(out[RMT].to_numpy(float)).all()
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--regime",default="runs/v3_l03_oracle")
    p.add_argument("--out",default="runs/v3_l03_rmt")
    a=p.parse_args()
    output=Path(a.out);output.mkdir(parents=True,exist_ok=True)
    old=pd.read_csv(Path(a.regime)/"EXPERT_MONTHLY_INTRINSIC.csv",
                    parse_dates=["signal_date","exit_date_21"])
    assert len(old)==101 and not old.signal_date.duplicated().any()
    assert set(old.columns)>=set(MARKET+["pair_top3","tail_top3","tail_wins"])
    mat,categories,_=load_ticker_csv_folder(a.raw)
    assert len(categories)==149
    C=mat["Close"].loc[mat["Close"].index>=pd.Timestamp("2011-01-01")]
    spec=spectral_state(C,old.signal_date)
    panel=old.merge(spec,on="signal_date",validate="one_to_one")
    assert len(panel)==101
    assert np.isfinite(panel[MARKET+RMT].to_numpy(float)).all()
    panel.to_csv(output/"CAUSAL_MARKET_SPECTRAL_FEATURES.csv",index=False)

    rows=[];fits=[]
    for year in range(2022,2027):
        cutoff=pd.Timestamp(year,1,1)
        train=panel[(panel.signal_date<cutoff)&(panel.exit_date_21<cutoff)]
        test=panel[panel.signal_date.dt.year==year]
        assert len(train)>=36 and len(test)>0
        assert train.exit_date_21.max()<cutoff
        prior=float((train.tail_wins.sum()+1)/(len(train)+2))
        for name,features in ARMS.items():
            if name=="PRIOR":pred=np.full(len(test),prior)
            else:
                m=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),
                   LogisticRegression(C=.1,max_iter=1000))
                m.fit(train[features],train.tail_wins.astype(int))
                pred=m.predict_proba(test[features])[:,1]
            x=test[["signal_date","pair_top3","tail_top3","tail_wins"]].copy()
            x["year"]=year;x["variant"]=name
            x["predicted_tail_probability"]=pred
            x["chosen_top3"]=np.where(pred>.5,x.tail_top3,x.pair_top3)
            x["model_brier"]=(pred-x.tail_wins)**2
            x["model_log_loss"]=-x.tail_wins*np.log(np.maximum(pred,1e-12))-(1-x.tail_wins)*np.log(np.maximum(1-pred,1e-12))
            rows.append(x)
        fits.append({"year":year,"train_months":len(train),"latest_mature_exit":str(train.exit_date_21.max()),
            "test_months":len(test),"train_tail_win_prevalence":float(train.tail_wins.mean()),
            "prior":prior,"fixed_C":.1,"rmt_window_trading_days":63,
            "all_expert_models_frozen":True})
        print("RMT_L03_ANNUAL",year,len(train),len(test),flush=True)
    pred=pd.concat(rows,ignore_index=True)
    assert not pred.duplicated(["signal_date","variant"]).any()
    assert all(pred.variant.value_counts().eq(53))
    pred.to_csv(output/"PAIRED_MONTHLY.csv",index=False)
    results=[]
    for name,g in pred.groupby("variant"):
        y=g.tail_wins.to_numpy(int);z=g.predicted_tail_probability.to_numpy(float)
        results.append({"variant":name,"n_months":len(g),
            "Brier":float(brier_score_loss(y,z)),"log_loss":float(log_loss(y,np.clip(z,1e-12,1-1e-12))),
            "AUC":float(roc_auc_score(y,z)),"choice_accuracy":float(np.mean((z>.5)==y)),
            "chosen_Top3":float(g.chosen_top3.mean()),
            "always_Tail_Top3":float(g.tail_top3.mean())})
    pd.DataFrame(results).to_csv(output/"RESULTS.csv",index=False)
    pred.groupby(["year","variant"])[["model_brier","model_log_loss","chosen_top3"]].mean().to_csv(output/"YEARLY.csv")
    data={}
    for name in ["RMT_ONLY","MARKET_PLUS_RMT"]:
        ref=pred[pred.variant=="MARKET_ONLY"].sort_values("signal_date").reset_index(drop=True)
        test=pred[pred.variant==name].sort_values("signal_date").reset_index(drop=True)
        pd.testing.assert_series_equal(ref.signal_date,test.signal_date)
        for metric in ["model_brier","model_log_loss","chosen_top3"]:
            dif=(test[metric]-ref[metric]).to_numpy(float)
            rng=np.random.default_rng(20261021);n=len(dif);reps=5000
            starts=rng.integers(0,n,size=(reps,int(np.ceil(n/BLOCK))))
            ix=((starts[:,:,None]+np.arange(BLOCK))%n).reshape(reps,-1)[:,:n]
            avg=dif[ix].mean(axis=1)
            data[f"{name}-{metric}"]={"delta":float(dif.mean()),
                "ci95_low":float(np.quantile(avg,.025)),"ci95_high":float(np.quantile(avg,.975))}
    (output/"PAIRED_BOOTSTRAP.json").write_text(json.dumps(data,indent=2))
    (output/"FIT_AUDIT.json").write_text(json.dumps(fits,indent=2))
    (output/"MANIFEST.json").write_text(json.dumps({
        "layer":"L03.2 RMT spectral regime forecast",
        "original_regime_run":39659065223,"immutable_raw_snapshot":39482809691,
        "mature_21d_expert_win_labels_only":True,
        "features_at_signal_month_end_only":True,
        "spectral_lookback":63,"target":"next21D which frozen expert's Top3 better",
        "model_C_fixed":.1,"no_CAGR":True,"all_downstream_layers_frozen":True,
        "holdout":"historical 2022–2026 previously examined; exploratory only"},indent=2))
    print("V3_L03_RMT_RESULT\n"+pd.DataFrame(results).to_string(index=False),flush=True)

if __name__=="__main__":main()
