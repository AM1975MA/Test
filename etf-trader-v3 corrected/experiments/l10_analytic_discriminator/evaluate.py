#!/usr/bin/env python3
"""L10.D1: frozen analytical residual persistence/downside signal, research only.

ONE formula; no model fitting, no forward labels in signal; one equal-capacity
pool contrast; OOS monthly inference respects overlapping 500 baskets.
See reports/L10/20261022_L10D1_RESIDUAL_PERSISTENCE_PROTOCOL.md.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder

BASKET_SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
WEIGHT=np.array([.5,.3,.2],dtype=float)

def analytical_signal(close):
    """Completely causal: beta from preceding 126 observations, not future data."""
    assert "SPY" in close.columns and "VTI" in close.columns
    logc=np.log(close.where(close>0))
    lr=logc.diff()
    # Composite equally-weighted reference prevents SPY-on-SPY exact degeneracy.
    market=0.5*lr["SPY"]+0.5*lr["VTI"]
    var=market.rolling(126,min_periods=100).var()
    beta=lr.rolling(126,min_periods=100).cov(market).div(var,axis=0).shift(1)
    residual=lr-beta.mul(market,axis=0)
    numerator=residual.rolling(63,min_periods=63).sum()
    den=np.sqrt(residual.clip(upper=0).pow(2).rolling(63,min_periods=63).sum())
    val=numerator.div(den.where(den>1e-12))
    return val.replace([np.inf,-np.inf],np.nan)

def prefix_invariance_test():
    """Changing prices AFTER t may not change AP(t)."""
    ix=pd.bdate_range("2020-01-01",periods=350)
    n=np.arange(len(ix),dtype=float)
    data=pd.DataFrame({
        "SPY":100*np.exp(.0007*n+.017*np.sin(n*.13)),
        "VTI":102*np.exp(.00068*n+.016*np.sin(n*.12)),
        "AAA":90*np.exp(.0011*n+.03*np.cos(n*.085)),
        "BBB":75*np.exp(-.0001*n+.025*np.sin(n*.075)),
    },index=ix)
    checkpoint=ix[275]
    original=analytical_signal(data).loc[checkpoint]
    modified=data.copy()
    modified.loc[ix[276]:,"AAA"]*=2.5
    modified.loc[ix[276]:,"BBB"]*=0.35
    modified.loc[ix[276]:,"SPY"]*=1.7
    modified.loc[ix[276]:,"VTI"]*=1.6
    new=analytical_signal(modified).loc[checkpoint]
    np.testing.assert_allclose(original.to_numpy(),new.to_numpy(),rtol=0,atol=1e-12)
    assert np.isfinite(original).all()
    return True

def calc_baskets(ref,top,pure,targets,baskets):
    """Within a single month: same basket and target for ALL contenders."""
    names=list(ref.index)
    ticker_index={t:i for i,t in enumerate(names)}
    ii=np.array([[ticker_index[t] for t in row] for row in baskets],dtype=int)
    y=targets.to_numpy(float)[ii]
    r=ref.to_numpy(float)[ii]
    t=top.to_numpy(float)[ii]
    analytic=pure.to_numpy(float)[ii]
    order_r=np.argsort(-r,axis=1,kind="stable")
    order_t=np.argsort(-t,axis=1,kind="stable")
    target_rank=np.argsort(-y,axis=1,kind="stable")
    quality=np.empty_like(y)
    quality[np.arange(len(baskets))[:,None],target_rank]=np.linspace(1,0,24)
    best=np.argmax(y,axis=1)
    all_rows=[]
    unique_union=set()
    for j in range(len(baskets)):
        base=list(map(int,order_r[j,:3]))
        novel=[int(k) for k in order_t[j,:3] if int(k) not in base]
        match=[int(k) for k in order_r[j,3:3+len(novel)]]
        union=base+novel
        matched=base+match
        assert len(union)==len(matched)==3+len(novel)
        assert len(set(union))==len(union) and len(set(matched))==len(matched)
        for k in union:
            unique_union.add(int(ii[j,k]))
        # Fitted as-of-date analytic coverage is required on BASE+UNION+MATCHED.
        included=set(base+novel+match)
        eligible=all(np.isfinite(analytic[j,k]) for k in included)
        if not eligible:
            all_rows.append({"eligible":False})
            continue
        # Identical candidate capacity, one predeclared standalone analytical
        # ranking intervention for two candidate-retrieval arms.
        an_union=sorted(union,key=lambda k:(-analytic[j,k],int(k)))[:3]
        an_matched=sorted(matched,key=lambda k:(-analytic[j,k],int(k)))[:3]
        worst=set(map(int,target_rank[j,-3:]))
        row={"eligible":True,"added_count":len(novel)}
        for key,picks in [("BASE",base),("UNION_ANALYTIC",an_union),
                          ("MATCHED_ANALYTIC",an_matched)]:
            picks=np.asarray(picks,int)
            yy=y[j,picks]
            row[key+"_weighted_regret"]=float(np.max(y[j])-WEIGHT@yy)
            row[key+"_weighted_rank"]=float(WEIGHT@quality[j,picks])
            row[key+"_loss10_weight"]=float(WEIGHT@(yy<=-.10))
            row[key+"_bottom3_weight"]=float(WEIGHT@np.array([int(i in worst) for i in picks]))
            row[key+"_winner_weight"]=float(WEIGHT@np.array([int(i==best[j]) for i in picks]))
            row[key+"_top3_winner"]=float(int(best[j] in picks))
        # Same union candidate names; no leakage into analytic score.
        if len(union)>=3:
            r_true=y[j,union]
            row["union_analytic_spearman"]=float(
                spearmanr(analytic[j,union],r_true).statistic)
            row["union_corrected_spearman"]=float(
                spearmanr(r[j,union],r_true).statistic)
        all_rows.append(row)
    f=pd.DataFrame(all_rows)
    eligible=f.loc[f.eligible==True].copy()
    pooled_idx=sorted(unique_union)
    yy=targets.to_numpy(float)[pooled_idx]
    score=pure.to_numpy(float)[pooled_idx]
    corr=ref.to_numpy(float)[pooled_idx]
    valid=np.isfinite(score)&np.isfinite(yy)
    unique={"n_union_unique":len(pooled_idx),
            "n_union_unique_signal_valid":int(valid.sum()),
            "n_union_unique_actual_losses":int((yy[valid]<=-.1).sum())}
    event=(yy[valid]<=-.1).astype(int)
    if len(np.unique(event))==2:
        unique["analytic_unique_loss_auc"]=float(roc_auc_score(event,-score[valid]))
        unique["corrected_unique_loss_auc"]=float(roc_auc_score(event,-corr[valid]))
    else:
        unique["analytic_unique_loss_auc"]=np.nan
        unique["corrected_unique_loss_auc"]=np.nan
    result={"n_baskets":len(baskets),"n_eligible":len(eligible),
            "coverage":len(eligible)/len(baskets),**unique}
    for col in eligible.columns:
        if col!="eligible":
            result[col]=float(eligible[col].mean()) if len(eligible) else np.nan
    return result

def bootstrap_delta(df,a,b,reps=6000,width=6):
    clean=df[[a,b]].dropna()
    # Strictly require all 101 months for main comparisons: no cherry-picking.
    if len(clean)!=101:
        return {"delta":np.nan,"ci95_low":np.nan,"ci95_high":np.nan,"months":len(clean)}
    d=(clean[a]-clean[b]).to_numpy(float)
    n=len(d)
    rng=np.random.default_rng(20261022)
    starts=rng.integers(0,n,size=(reps,math.ceil(n/width)))
    ix=((starts[:,:,None]+np.arange(width))%n).reshape(reps,-1)[:,:n]
    bs=d[ix].mean(axis=1)
    return {"delta":float(np.mean(d)),"ci95_low":float(np.quantile(bs,.025)),
        "ci95_high":float(np.quantile(bs,.975)),"months":n}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",required=True)
    ap.add_argument("--scores",required=True)
    ap.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    ap.add_argument("--out",required=True)
    x=ap.parse_args()
    out=Path(x.out);out.mkdir(parents=True,exist_ok=True)
    assert prefix_invariance_test(),"causal prefix-invariance failed"
    assert hashlib.sha256(Path(x.baskets).read_bytes()).hexdigest()==BASKET_SHA
    b=pd.read_csv(x.baskets);b.ticker=b.ticker.astype(str).str.upper()
    baskets=[g.ticker.tolist() for _,g in b.sort_values(["basket","ticker"]).groupby("basket")]
    assert len(baskets)==500 and all(len(k)==24 for k in baskets)
    mats,cats,raw_audit=load_ticker_csv_folder(x.raw)
    assert len(cats)==149
    scores=pd.read_csv(x.scores,parse_dates=["signal_date"])
    models={}
    for name in ["CORRECTED","L10_TOP5_PAIR127"]:
        frame=scores[scores.variant.eq(name)][["signal_date","ticker","pred","fwd_ret_21"]].copy()
        frame["ticker"]=frame.ticker.astype(str).str.upper()
        assert len(frame)==15198 and frame.signal_date.nunique()==102
        assert frame.ticker.nunique()==149
        assert not frame.duplicated(["signal_date","ticker"]).any()
        models[name]=frame
    close=mats["Close"].sort_index()
    analytic=analytical_signal(close)
    monthly=[]
    snap=[]
    dates=sorted(models["CORRECTED"].signal_date.unique())
    for date in dates:
        base=models["CORRECTED"][models["CORRECTED"].signal_date.eq(date)].sort_values("ticker").reset_index(drop=True)
        add=models["L10_TOP5_PAIR127"][models["L10_TOP5_PAIR127"].signal_date.eq(date)].sort_values("ticker").reset_index(drop=True)
        pd.testing.assert_series_equal(base.ticker,add.ticker)
        np.testing.assert_allclose(base.fwd_ret_21,add.fwd_ret_21,atol=1e-14,rtol=0,equal_nan=True)
        assert len(base)==149
        if base.fwd_ret_21.isna().any():
            assert base.fwd_ret_21.isna().all()
            continue
        day=pd.Timestamp(date)
        if day not in analytic.index:
            raise ValueError("raw adjusted close calendar missing signal date "+str(day))
        tickers=list(base.ticker)
        a=analytic.loc[day,tickers].to_numpy(float)
        ref=base.pred.rank(pct=True,method="average").to_numpy(float)
        alt=add.pred.rank(pct=True,method="average").to_numpy(float)
        y=base.fwd_ret_21.to_numpy(float)
        one=calc_baskets(
            pd.Series(ref,index=tickers),
            pd.Series(alt,index=tickers),
            pd.Series(a,index=tickers),
            pd.Series(y,index=tickers),baskets)
        valid=np.isfinite(a)&np.isfinite(y)
        if valid.sum()<2:
            one["analytic_universe_rankIC"]=np.nan
        else:
            one["analytic_universe_rankIC"]=float(spearmanr(a[valid],y[valid]).statistic)
        one["corrected_universe_rankIC"]=float(spearmanr(ref,y).statistic)
        one["analytic_universe_coverage"]=float(valid.mean())
        one["signal_date"]=str(day.date())
        one["year"]=day.year
        monthly.append(one)
        snap.extend([{"signal_date":str(day.date()),"ticker":ticker,
            "analytical_residual_persistence":float(a[i]) if np.isfinite(a[i]) else None,
            "frozen_corrected_score":float(ref[i]),
            "frozen_top5_score":float(alt[i]),
            "future_21d_return_AUDIT_ONLY":float(y[i])}
            for i,ticker in enumerate(tickers)])
    f=pd.DataFrame(monthly).sort_values("signal_date").reset_index(drop=True)
    assert len(f)==101 and f.n_baskets.eq(500).all()
    f.to_csv(out/"ANALYTIC_MONTHLY.csv",index=False)
    pd.DataFrame(snap).to_csv(out/"ANALYTIC_SIGNAL_AND_TARGET_AUDIT.csv",index=False)
    float_cols=[c for c in f if c not in ["signal_date","year"]]
    pd.DataFrame([{"metric":col,"monthly_mean":float(f[col].mean()),
                   "n_nonmissing_months":int(f[col].notna().sum())}
                   for col in float_cols]).to_csv(out/"ANALYTIC_SUMMARY.csv",index=False)
    f.groupby("year")[float_cols].mean().to_csv(out/"ANALYTIC_YEARLY.csv")
    variants=["UNION_ANALYTIC","MATCHED_ANALYTIC","BASE"]
    deltas=[]
    for metric in ["weighted_regret","weighted_rank","loss10_weight","bottom3_weight",
                   "winner_weight","top3_winner"]:
        for trial,reference in [(variants[0],variants[1]),(variants[0],variants[2]),
                                 (variants[1],variants[2])]:
            a=trial+"_"+metric;b=reference+"_"+metric
            deltas.append({"contrast":trial+"__"+reference,"metric":metric,
                           **bootstrap_delta(f,a,b)})
    for a,b in [
        ("union_analytic_spearman","union_corrected_spearman"),
        ("analytic_unique_loss_auc","corrected_unique_loss_auc"),
        ("analytic_universe_rankIC","corrected_universe_rankIC")
    ]:
        deltas.append({"contrast":a+"__"+b,"metric":"predictive_skill",
            **bootstrap_delta(f,a,b)})
    pd.DataFrame(deltas).to_csv(out/"ANALYTIC_BOOTSTRAP.csv",index=False)
    coverage={"n_mature_months":len(f),"complete_analytic_coverage_month_mean":float(f.coverage.mean()),
        "min_monthly_coverage":float(f.coverage.min()),
        "analytic_signal_universe_coverage":float(f.analytic_universe_coverage.mean()),
        "failing_months_lt90pct":f.loc[f.coverage<.9,"signal_date"].tolist(),
        "causal_prefix_invariance":True,
        "safe_to_compare_all_months":bool((f.coverage>=.9).all())}
    (out/"COVERAGE.json").write_text(json.dumps(coverage,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
        "experiment":"L10.D1 analytic residual-persistence/downside gate",
        "raw_run":39482809691,"frozen_scores_run":39700865721,
        "baskets_sha256":BASKET_SHA,"n_ETF":149,"n_baskets":500,
        "expected_mature_months":101,"analytic":"rolling63 residual return / sqrt(rolling63 negative residual square sum); preceding shifted126 beta against equal-weight SPY+VTI return benchmark",
        "future_prices_or_labels_used_in_signal":False,
        "forward_target_used_only_for_evaluation":True,
        "same_static_top3_weights":[.5,.3,.2],
        "no_model_training":True,"no_CAGR":True,"no_production_change":True,
        "not_virgin_holdout":True,"source_raw_manifest_tickers":raw_audit["tickers"],
        "coverage":coverage
    },indent=2))
    print("L10D1_MONTHLY_SUMMARY",pd.read_csv(out/"ANALYTIC_SUMMARY.csv").to_string(index=False),flush=True)
    print("L10D1_COVERAGE",json.dumps(coverage),flush=True)
    print("L10D1_BOOTSTRAP",pd.read_csv(out/"ANALYTIC_BOOTSTRAP.csv").to_string(index=False),flush=True)
if __name__=="__main__":
    main()
