#!/usr/bin/env python3
"""OLC44-A research gate (NOT authentic native OLC19 full-model refit).

Train a single, fixed Ridge model *by market* using only completed prior monthly
observations. Predict the next-open-to-next-open log-return ADVANTAGE of a new
ETF relative to the second AUTH incumbent from OLC35. The AUTH reference is
not the full OLC19 portfolio. Never represent results as OLC19 portfolio CAGR.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"
OUT.mkdir(exist_ok=True)
ART=ROOT/"source_artifact"
FROZEN=ROOT/"OLC35_AUTH_TOP2_FROZEN.csv"
FEATS=("m63","m126","vol63","dd63")
MIN_PRICES=500
MIN_TRAIN_MONTHS=10
RIDGE_ALPHA=30.0
SWITCH_BUFFER=0.005 # 50bp expected 1-month log edge, set before outcomes
ETF={"EU":("G2X.DE","USPY.DE","WTIC.DE","2B76.DE"),
     "USA":("BOTZ","LIT","PAVE")}

def features(ticker,market,signal,prices):
    p=prices[(market,ticker)]
    d=pd.Timestamp(signal)
    q=p.loc[p.index<=d, "close"].dropna()
    # 500 *observed* sessions, and look-back feature windows strictly
    # no later than decision date. If signal date missing, last prior close.
    if len(q)<MIN_PRICES or len(q)<128:return None
    arr=q.to_numpy(float); v=np.diff(np.log(arr[-64:]))
    m63=float(np.log(arr[-1]/arr[-64]))
    m126=float(np.log(arr[-1]/arr[-127]))
    vol=float(np.std(v,ddof=1)*np.sqrt(21))
    dd=float(np.log(arr[-1]/max(arr[-64:])))
    a=np.array([m63,m126,vol,dd])
    return a if np.isfinite(a).all() else None

def load_data():
    orig=pd.read_csv(FROZEN)
    assert len(orig)==96, f"Expected 48 months per market, got {len(orig)}"
    assert orig.groupby("market").size().to_dict()=={"EU":48,"USA":48}
    assert not orig.duplicated(["market","signal_date"]).any()
    orig=orig[["market","signal_date","year","top1","top2",
               "top1_return_bp","top2_return_bp"]].copy()
    lab=pd.read_csv(ART/"candidate_monthly_labels.csv")
    assert {"market","ticker","signal_date","entry_date","exit_date",
            "candidate_logbp","prior_observed_opens"}<=set(lab.columns)
    lab=lab[lab.apply(lambda x:x.ticker in ETF.get(x.market,()),axis=1)].copy()
    assert not lab.duplicated(["market","signal_date","ticker"]).any()
    lab=lab.merge(orig,on=["market","signal_date"],validate="many_to_one")
    assert len(lab)==48*(4+3),len(lab)
    prices={}
    for market,etfs in ETF.items():
        for ticker in etfs:
            p=ART/"candidate_daily"/(ticker.replace(".","_")+".csv.gz")
            d=pd.read_csv(p,compression="gzip",parse_dates=["date"]).set_index("date").sort_index()
            assert not d.index.has_duplicates
            prices[(market,ticker)]=d
    records=[]
    for r in lab.itertuples(index=False):
        x=features(r.ticker,r.market,r.signal_date,prices)
        if x is None or r.prior_observed_opens<MIN_PRICES:continue
        obs={
            "market":r.market,"ticker":r.ticker,"signal_date":str(r.signal_date),
            "entry_date":str(r.entry_date),"exit_date":str(r.exit_date),
            "incumbent1":r.top1,"incumbent2":r.top2,
            "old1_logbp":float(r.top1_return_bp),
            "old2_logbp":float(r.top2_return_bp),
            "candidate_logbp":float(r.candidate_logbp),
            "future_edge_log":(float(r.candidate_logbp)-float(r.top2_return_bp))/1e4
        }
        obs.update(dict(zip(FEATS,x)))
        records.append(obs)
    data=pd.DataFrame(records)
    data.to_csv(OUT/"candidate_asof_feature_and_forward_audit.csv",index=False)
    return data,orig

def monthly_train_and_predict(all_data,orig):
    decisions=[];training=[]
    for market in ("EU","USA"):
        md=all_data[all_data.market==market].copy()
        od=orig[orig.market==market].sort_values("signal_date")
        for r in od.itertuples(index=False):
            dt=pd.Timestamp(r.signal_date)
            now=md[md.signal_date==r.signal_date]
            if len(now)<1:continue
            past=md[pd.to_datetime(md.exit_date)<dt]
            months=int(past.signal_date.nunique())
            if dt.year<2022 or months<MIN_TRAIN_MONTHS or len(past)<25:
                training.append({"market":market,"signal_date":str(r.signal_date),
                                 "training_months":months,"training_rows":len(past),
                                 "status":"insufficient_past_or_evaluation_period"})
                continue
            assert (pd.to_datetime(past.exit_date)<dt).all()
            sx=StandardScaler().fit(past[list(FEATS)].to_numpy(float))
            X=sx.transform(past[list(FEATS)].to_numpy(float))
            y=past.future_edge_log.to_numpy(float)
            model=Ridge(alpha=RIDGE_ALPHA,fit_intercept=True)
            model.fit(X,y)
            now=now.copy()
            now["pred_edge"]=model.predict(sx.transform(now[list(FEATS)].to_numpy(float)))
            best=now.sort_values(["pred_edge","ticker"],ascending=[False,True]).iloc[0]
            pred=float(best.pred_edge)
            act=bool(pred>SWITCH_BUFFER)
            training.append({"market":market,"signal_date":str(r.signal_date),
                             "training_months":months,"training_rows":len(past),
                             "max_training_exit":str(max(past.exit_date)),
                             "status":"fit_ok","intercept":float(model.intercept_),
                             **{f"beta_{k}":float(v) for k,v in zip(FEATS,model.coef_)}})
            decisions.append({
                "market":market,"signal_date":str(r.signal_date),
                "selected_ticker":str(best.ticker),
                "pred_expected_edge_log":pred,"actual_edge_log":float(best.future_edge_log),
                "switch":act,"correct_if_switched":bool(best.future_edge_log>0),
                "incumbent1":r.top1,"incumbent2":r.top2,
                "old1_logbp":float(r.top1_return_bp),
                "old2_logbp":float(r.top2_return_bp),
                "selected_new_logbp":float(best.candidate_logbp),
                "training_n_months":months,"train_last_exit":str(max(past.exit_date))
            })
    decisions=pd.DataFrame(decisions)
    training=pd.DataFrame(training)
    decisions.to_csv(OUT/"olc44_prequential_monthly_decisions.csv",index=False)
    training.to_csv(OUT/"olc44_training_maturity_audit.csv",index=False)
    assert not decisions.duplicated(["market","signal_date"]).any()
    assert (pd.to_datetime(decisions.train_last_exit)<pd.to_datetime(decisions.signal_date)).all()
    return decisions

def summarize(dec):
    summary=[];annual=[]
    rng=np.random.default_rng(4401)
    for market,grp in dec.groupby("market"):
        grp=grp.sort_values("signal_date").copy()
        old1=grp.old1_logbp.to_numpy()/1e4
        old2=grp.old2_logbp.to_numpy()/1e4
        new=grp.selected_new_logbp.to_numpy()/1e4
        switched=grp["switch"].to_numpy(bool)
        # Exact 50/50 monthly rebalancing of two gross assets, NOT a
        # self-financing daily OLC19 ledger. Stress: 20bp per switch event.
        oldlog=np.log(.5*np.exp(old1)+.5*np.exp(old2))
        newlog=np.log(.5*np.exp(old1)+.5*np.exp(np.where(switched,new,old2)))
        costs=switched*0.002
        netlog=newlog-costs
        delta=newlog-oldlog
        monthly=(grp.assign(old_month_log=oldlog,new_month_log=newlog,
                            gross_delta_log=delta,net_delta_log=netlog-oldlog))
        monthly.to_csv(OUT/f"olc44_monthly_economic_proxy_{market}.csv",index=False)
        for yy,g in monthly.groupby(pd.to_datetime(monthly.signal_date).dt.year):
            annual.append({"market":market,"year":int(yy),
               "months":len(g),"switches":int(g.switch.sum()),
               "baseline_gross_return_pct":100*np.expm1(g.old_month_log.sum()),
               "challenger_gross_return_pct":100*np.expm1(g.new_month_log.sum()),
               "challenger_proxy_cost_return_pct":100*np.expm1(g.new_month_log.sum()-0.002*g.switch.sum())})
        n=len(monthly)
        if n<20:raise RuntimeError("Missing OOS months "+market)
        # Block bootstrap 6 actual calendar months across paired log differences
        d=delta.copy();span=6;means=[]
        for _ in range(3000):
            take=np.concatenate([np.arange(s,s+span)%n for s in rng.integers(0,n,size=int(np.ceil(n/span)))])[:n]
            means.append(np.mean(d[take]))
        ci=np.quantile(means,[.025,.975])
        info={
            "market":market,"months":n,"switches":int(switched.sum()),
            "positive_switched":int(np.sum(switched&(grp.actual_edge_log.to_numpy()>0))),
            "mean_selected_edge_bp":float(1e4*np.mean(grp.actual_edge_log)),
            "mean_acted_edge_bp":float(1e4*np.mean(grp.loc[grp.switch,"actual_edge_log"])) if switched.any() else np.nan,
            "baseline_gross_cagr_pct":100*np.expm1(oldlog.sum()/(n/12)),
            "challenger_gross_cagr_pct":100*np.expm1(newlog.sum()/(n/12)),
            "challenger_cost_proxy_cagr_pct":100*np.expm1(netlog.sum()/(n/12)),
            "paired_mean_logbp_month":1e4*float(d.mean()),
            "paired_CI95_low_logbp_month":1e4*float(ci[0]),
            "paired_CI95_high_logbp_month":1e4*float(ci[1])
        }
        summary.append(info)
    pd.DataFrame(annual).to_csv(OUT/"olc44_annual_proxy.csv",index=False)
    sm=pd.DataFrame(summary)
    sm.to_csv(OUT/"olc44_summary.csv",index=False)
    print("=== OLC44 PREQUENTIAL, AUTH reference, NOT OLC19 ===")
    print(sm.to_string(index=False,float_format=lambda a:f"{a:.5f}"),flush=True)
    return sm

def main():
    data,orig=load_data()
    dec=monthly_train_and_predict(data,orig)
    summary=summarize(dec)
    manifest={
       "experiment":"OLC44-A diagnostic prequential score gate",
       "native_original_olc19_refit":False,
       "reference":"OLC35 AUTH Top2, not exact OLC19 risk-engine holdings",
       "price_input":"frozen E1 observed adjusted daily prices, as-of signal close",
       "target":"candidate minus incumbent2 O2O future monthly log return",
       "features":FEATS,"model":"StandardScaler(train only)+Ridge(fixed alpha30)",
       "alpha":RIDGE_ALPHA,"switch_buffer_log":SWITCH_BUFFER,
       "start_validation":"2022-01-01","cutoff":"matured exit_date < signal_date",
       "no_ticker_identity_feature":True,"min_price_observations":MIN_PRICES,
       "e2_incompatibility":"does not use OLC19 risk/execution; no stop, V6, turnover; proxy only",
       "not_holdout":"2021-2024 inspected many times; ex-post ETF candidate universe",
       "markets":list(ETF)
    }
    (OUT/"olc44_manifest.json").write_text(json.dumps(manifest,indent=2))
if __name__=="__main__":main()
