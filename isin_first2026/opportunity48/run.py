#!/usr/bin/env python3
"""Attribution: did EUROPE48 2021-2026 funds themselves lack opportunities?

One horizon and actual-same prices, no optimizing or selection from future in
investable baselines. Explicitly ex-post noninvestable oracle only as an upper
bound / opportunity diagnostic, NEVER a strategy recommendation.
"""
from __future__ import annotations
import argparse,collections,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from europe_only75.f3h1_original_transfer.run import costed_path,ci
from isin_first2026.build import sha

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"isin_first2026/full_eu_2017/results"
OLD=ROOT/"isin_first2026/refit48/results"
SEED=20261019
MODS=("F3_EU48","H1_EU48","H3_EU48","F3_H1_BLEND_EU48","RH_OLD60_MAPPED48")
BUCKETS=("EU_EQUITY_SECTOR","EU_EQUITY_BROAD","EU_EQUITY_COUNTRY",
         "EU_EQUITY_FACTOR","EU_PROPERTY","SOVEREIGN_EUR")
METRICS=("cagr","maxdd_daily_open","sharpe_daily_log","es5_daily",
         "ann_vol","fee_notional","gross_turnover","position_count_mean")

def check_run():
    src=json.loads((OLD/"RESULT.json").read_text())
    assert src["status"]=="EUR48_TRUE_RETRAIN_F3_H1_H3_AND_MATCHED_10BP_EXECUTION_COMPLETE"
    cal=pd.read_csv(OLD/"MONTHLY_EUROPE48_EXECUTION_DATES.csv",parse_dates=["signal_date","entry_date","exit_date"])
    assert len(cal)==65
    roster=pd.read_csv(DATA/"STRICT_EUROPE_2017_WARM_2016_UNIQUE_ISIN.csv")
    assert len(roster)==48 and roster["isin"].is_unique
    opens=pd.read_csv(DATA/"WIDE_DAILY_OPEN_2016_2026.csv",parse_dates=["date"]).set_index("date")
    names=roster["isin"].to_list()
    assert len(opens.columns)==48 and set(opens.columns)==set(names)
    opens=opens[names].astype(float)
    nav=pd.read_csv(OLD/"DAILY_COSTED_EQUITY_SAME_EUROPE_DATES.csv",parse_dates=["day"])
    days=pd.DatetimeIndex(nav.day)
    assert len(days)==1331 and not days.duplicated().any()
    assert days[0]==cal.entry_date.iloc[0] and days[-1]==cal.exit_date.iloc[-1]
    assert (opens.loc[days].notna().all(axis=1)).all() and (
              (opens.loc[days]>0).all(axis=None))
    holdings=pd.read_csv(OLD/"MONTHLY_HOLDINGS_UNIQUE_ISIN.csv",parse_dates=["signal"])
    assert set(holdings.model)==set(MODS)|{"PASSIVE_EU_60_40"}
    assert holdings.groupby(["model","block"]).weight.sum().sub(1).abs().max()<1e-10
    return src,cal,roster,opens,days,nav,holdings

def bucket_profile(roster,opens,days):
    first=opens.loc[days[0]];last=opens.loc[days[-1]]
    years=(days[-1]-days[0]).days/365.25
    # Single initial purchase at ask approximated by fee at first Open,
    # no rebalancing, no forced exit liquidation. Same cost convention.
    logg=np.log(last/first)-np.log1p(.001)
    p=roster[["isin","ticker","benchmark_bucket","sector_11","index_subsector","decision",
       "vendor_zero_volume_pct","broken_ohlc_envelope_pct"]].copy()
    p["buyhold_net_cagr"]=(np.exp(logg.reindex(p["isin"]).to_numpy(float)/years)-1)
    p["gross_log_growth_2021_2026"]=np.log(
        (last/first).reindex(p["isin"]).to_numpy(float))
    p["first_open"]=first.reindex(p["isin"]).to_numpy(float)
    p["last_open"]=last.reindex(p["isin"]).to_numpy(float)
    p=p.sort_values("buyhold_net_cagr",ascending=False).reset_index(drop=True)
    return p,years

def monthly_actual(cal,roster,opens,holdings):
    # Forward Open return is known only after month MATURITY: evaluation only.
    groups=roster.set_index("isin").benchmark_bucket.to_dict()
    sectors=roster.set_index("isin").sector_11.to_dict()
    future={}
    rows=[]
    for j,r in cal.iterrows():
        y=np.log(opens.loc[r.exit_date]/opens.loc[r.entry_date])
        assert y.notna().all()
        future[j]=y
        s=y.sort_values(ascending=False)
        rows.append(dict(block=j,signal=str(r.signal_date.date()),
          crosssection_equal_log_mean=float(y.mean()),
          sector_only_mean_log=float(y[[k for k in y.index if groups[k]=="EU_EQUITY_SECTOR"]].mean()),
          top5_oracle_log_mean=float(s.head(5).mean()),
          bottom5_oracle_log_mean=float(s.tail(5).mean()),
          crosssection_sd_log=float(y.std(ddof=1)),
          top5_minus_crosssection_log=float(s.head(5).mean()-y.mean()),
          best_etf=float(s.iloc[0]),worst_etf=float(s.iloc[-1]),
          best_ticker=str(roster.set_index("isin").loc[s.index[0],"ticker"]),
          best_bucket=groups[s.index[0]],
          worst_ticker=str(roster.set_index("isin").loc[s.index[-1],"ticker"])))
    b=pd.DataFrame(rows)
    m=[]
    for rec in holdings[holdings.model.isin(MODS)].itertuples(index=False):
        idx=int(rec.block)-int(holdings.block.min())
        if idx not in future:raise AssertionError("Unexpected block: "+str(rec.block))
        ret=float(future[idx][rec.isin])
        m.append(dict(model=rec.model,block=idx,isin=rec.isin,
            ticker=rec.ticker,weight=float(rec.weight),
            macro_bucket=groups[rec.isin],sector_11=sectors[rec.isin],
            future_log_return=ret,
            weighted_log_contribution=float(rec.weight)*ret))
    m=pd.DataFrame(m)
    diagnostics=[]
    bybucket=[]
    for (model,j),g in m.groupby(["model","block"],sort=True):
        y=future[j]
        ew=float(y.mean())
        selected_ret=float(g.weight.mul(g.future_log_return).sum())
        equal_sector=float(y[[k for k in y.index if groups[k]=="EU_EQUITY_SECTOR"]].mean())
        n_sovereign=int((g.macro_bucket=="SOVEREIGN_EUR").sum())
        concentration=float(g.weight[g.macro_bucket.isin(["SOVEREIGN_EUR","EU_PROPERTY"])].sum())
        top_pct = (g.future_log_return.to_numpy(float)[:,None] >=
             y.to_numpy(float)[None,:]).sum(axis=1).mean()/len(y)
        diagnostics.append(dict(model=model,block=j,signal=b.iloc[j].signal,
             weighted_selected_monthly_log_return=selected_ret,
             equal_weight_all48_future_log_return=ew,
             equal_weight_sector_only_future_log_return=equal_sector,
             selected_minus_equal48=selected_ret-ew,
             selected_minus_sector_avg=selected_ret-equal_sector,
             n_holdings=len(g),n_government_funds=n_sovereign,
             weight_government_property=concentration,
             selected_average_actual_crosssection_percentile=float(top_pct)))
        for bucket,z in g.groupby("macro_bucket"):
            bybucket.append(dict(model=model,block=j,bucket=bucket,
                weight=float(z.weight.sum()),
                weighted_future_log_contribution=float(z.weight.mul(z.future_log_return).sum())))
    return b,m,pd.DataFrame(diagnostics),pd.DataFrame(bybucket),future

def cast_metrics(metrics,method):
    return dict(portfolio=method,**{k:metrics[k] for k in METRICS})

def build_portfolio_tests(cal,roster,opens,days,future,nav,holdings):
    names=roster["isin"].to_list()
    buckets=roster.set_index("isin").benchmark_bucket.to_dict()
    sectors=roster.set_index("isin").sector_11.to_dict()
    tmap=roster.set_index("ticker")["isin"]
    strategies={
        "EQUAL_48_MONTHLY":names,
        "EQUAL_23_EUROPE_SECTORS": [k for k in names if buckets[k]=="EU_EQUITY_SECTOR"],
        "EQUAL_25_NONSECTORS": [k for k in names if buckets[k]!="EU_EQUITY_SECTOR"],
        "EQUAL_7_EURO_SOVEREIGN": [k for k in names if buckets[k]=="SOVEREIGN_EUR"],
        "EQUAL_6_EU_PROPERTY": [k for k in names if buckets[k]=="EU_PROPERTY"],
        "EQUAL_12_EQUITY_BROAD_COUNTRY_FACTOR": [k for k in names if buckets[k] in
                       ("EU_EQUITY_BROAD","EU_EQUITY_COUNTRY","EU_EQUITY_FACTOR")],
        "BUY_HOLD_MSCI_EUROPE_100PCT":[str(tmap["IMEU.AS"])],
        "BUY_HOLD_EURO_GOV_100PCT":[str(tmap["EUNH.DE"])]
    }
    policies={}
    for name,ids in strategies.items():
        assert len(ids)>0
        if name.startswith("BUY_HOLD_"):
            # Costed_path monthly weights of same ISIN is mathematically
            # self-funded buy-hold: share count unchanged (no extra trade).
            policies[name]=[{k:1 for k in ids} for _ in range(len(cal))]
        else:
            policies[name]=[{k:1/len(ids) for k in ids} for _ in range(len(cal))]
    # Clearly impossible upper bound and lower bound: uses hindsight future
    # price on each monthly entry date. Cannot be deployed, ever.
    policies["ORACLE_HINDSIGHT_TOP5"]=[
        {k:.2 for k in future[j].nlargest(5).index} for j in range(len(cal))]
    policies["ANTI_ORACLE_HINDSIGHT_WORST5"]=[
        {k:.2 for k in future[j].nsmallest(5).index} for j in range(len(cal))]
    for j in range(len(cal)):
        assert all(set(p[j])<=set(names) and abs(sum(p[j].values())-1)<1e-9
            for p in policies.values())
    records=[];daily={}
    for name,weights in policies.items():
        stat,curve,_=costed_path(weights,cal,opens,days)
        records.append(cast_metrics(stat,name))
        daily[name]=curve
        print("OPPORTUNITY_PORTFOLIO",name,
            json.dumps({k:stat[k] for k in ("cagr","maxdd_daily_open","es5_daily")}),flush=True)
    # Truly random *ex ante* non-learning selectors as economic opportunity
    # baseline; they do NOT predict anything. Same actual shares and fees.
    rng=np.random.default_rng(SEED)
    sims=[]
    for n in range(300):
        randomweights=[]
        for _ in range(len(cal)):
            picks=rng.choice(names,size=5,replace=False)
            randomweights.append({str(k):.2 for k in picks})
        stat,_,_=costed_path(randomweights,cal,opens,days)
        sims.append(dict(seed=SEED,simulation=n,cagr=stat["cagr"],
            maxdd=stat["maxdd_daily_open"],sharpe=stat["sharpe_daily_log"]))
    sims=pd.DataFrame(sims)
    actual=json.loads((OLD/"RESULT.json").read_text())["all_model_results"]
    rg={}
    for name in ("F3_EU48","H1_EU48","H3_EU48","F3_H1_BLEND_EU48",
                 "RH_OLD60_MAPPED48","PASSIVE_EU_60_40"):
        target=actual[name]
        rg[name]=dict(actual_cagr=target["cagr"],
            random_300_CAGR_percentile=float((sims.cagr<target["cagr"]).mean()*100),
            actual_maxdd=target["maxdd_daily_open"])
    stats=pd.DataFrame(records)
    return stats,pd.DataFrame(daily),sims,rg

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    src,cal,roster,opens,days,nav,holdings=check_run()
    equity,years=bucket_profile(roster,opens,days)
    equity.to_csv(out/"SINGLE_ISIN_BUY_AND_HOLD_CAGR_2021_2026.csv",index=False)
    months,exposure,monthlysel,bybucket,future=monthly_actual(cal,roster,opens,holdings)
    months.to_csv(out/"FUTURE_WINNER_OPPORTUNITY_PER_MONTH_NOT_TRADEABLE.csv",index=False)
    exposure.to_csv(out/"ACTUAL_MODEL_HOLDING_ISIN_NEXT_MONTH_EXPOST.csv",index=False)
    monthlysel.to_csv(out/"MODEL_VERSUS_EQUAL_WEIGHT_REALIZED_SELECTION_SKILL.csv",index=False)
    bybucket.to_csv(out/"MODEL_HOLDING_EXPOSURE_AND_WEIGHTED_FUTURE_RETURNS.csv",index=False)
    results,daily,sims,randomranking=build_portfolio_tests(
        cal,roster,opens,days,future,nav,holdings)
    results.to_csv(out/"VALID_PASSIVE_VERSUS_HINDSIGHT_ONLY_BOUNDS.csv",index=False)
    daily.to_csv(out/"NAV_PASSIVE_EQUAL_SECTOR_AND_UNTRADEABLE_ORACLE.csv",index_label="day")
    sims.to_csv(out/"NO_INFORMATION_RANDOM_TOP5_SHARE_PORTFOLIOS_SEED20261019.csv",index=False)
    # Selection quality time blocks; no fancy IID across 48 ETF rows.
    skill={}
    for name,g in monthlysel.groupby("model"):
        sm=g.selected_minus_equal48.to_numpy(float)
        skill[name]=dict(
          monthly_advantage_vs_EW48=float(sm.mean()),
          CIs_3month_bootstrap=ci(sm,SEED+21),
          positive_months=int((sm>0).sum()),
          n_months=len(g),
          mean_sov_or_property_weight=float(g.weight_government_property.mean()),
          mean_rank_percentile_selected=float(
              g.selected_average_actual_crosssection_percentile.mean()))
    group=equity.groupby("benchmark_bucket").buyhold_net_cagr.agg(
       ["size","median","mean","min","max"]).round(10).to_dict("index")
    rt=equity.buyhold_net_cagr.to_numpy(float)
    candidates=equity[["ticker","isin","benchmark_bucket","sector_11","buyhold_net_cagr"]]
    origin=src["all_model_results"]
    r={
        "status":"EU48_OPPORTUNITY_VERSUS_SELECTOR_QUALITY_FORENSIC_COMPLETED",
        "study_begin":str(days[0].date()),"study_end":str(days[-1].date()),
        "years_actual":years,"funds_dedup_isin":len(roster),
        "months":len(cal),"same_common_opens":len(days),
        "single_fund_buyhold_statistics":dict(
             mean_cagr=float(np.mean(rt)),median_cagr=float(np.median(rt)),
             q10_cagr=float(np.quantile(rt,.1)),q90_cagr=float(np.quantile(rt,.9)),
             min_cagr=float(np.min(rt)),max_cagr=float(np.max(rt)),
             funds_with_negative_CAGR=int((rt<0).sum()),
             funds_CAGR_above10pct=int((rt>.1).sum()),
             funds_CAGR_above15pct=int((rt>.15).sum()),
             funds_CAGR_above20pct=int((rt>.20).sum())),
        "by_group_buyhold":group,
        "top10_funds_by_historical_buyhold_cagr":candidates.head(10).to_dict("records"),
        "bottom10_funds_by_historical_buyhold_cagr":candidates.tail(10).to_dict("records"),
        "expost_best_five_mean_1month_log_return":float(months.top5_oracle_log_mean.mean()),
        "equal48_mean_1month_log_return":float(months.crosssection_equal_log_mean.mean()),
        "median_1month_all48_return_dispersion_sd":float(months.crosssection_sd_log.median()),
        "mean_1month_best5_minus_equal48_log":float(months.top5_minus_crosssection_log.mean()),
        "mean_1month_best5_log_returns_positive_months":int((months.top5_oracle_log_mean>0).sum()),
        "selected_vs_EW48_forward_quality":skill,
        "actual_models_65month_CAGR":{k:origin[k]["cagr"] for k in origin},
        "additional_costed_portfolios":{x.portfolio:{k:float(getattr(x,k))
            for k in METRICS} for x in results.itertuples(index=False)},
        "uninformed_300_random_top5":dict(
            median_cagr=float(sims.cagr.median()),
            low10_cagr=float(sims.cagr.quantile(.1)),
            high90_cagr=float(sims.cagr.quantile(.9)),
            best_cagr=float(sims.cagr.max()),
            worst_cagr=float(sims.cagr.min())),
        "model_performance_percentile_against_uninformed_300":randomranking,
        "oracle_is_backward_looking_and_NOT_tradeable":True,
        "realistic_quote_opens_are_vendor_prices_not_broker_guarantees":True,
        "no_2017_PIT_universe_assertion":True,
        "no_fees_excluded_in_portfolio_tests":True,
        "training_selection_2026_survivorship_not_prospective":True,
        "same_as_original_models_10bp_bilateral_commission":True,
        "no_production_code_modified":True,
        "orig_roster_sha256":sha(DATA/"STRICT_EUROPE_2017_WARM_2016_UNIQUE_ISIN.csv"),
        "orig_prediction_sha256":sha(OLD/"ALL_48_ISIN_F3_H1_H3_MATURITY_PURGED_FORECASTS.csv"),
        "run_utc":str(pd.Timestamp.now(tz="UTC"))}
    (out/"RESULT.json").write_text(json.dumps(r,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
        sha(p)+"  "+str(p.relative_to(out))+"\n"
        for p in sorted(out.rglob("*.csv")))+
        sha(out/"RESULT.json")+"  RESULT.json\n")
    print("EU48_OPPORTUNITY_FORENSIC_RESULT",json.dumps(r,allow_nan=False),flush=True)
    return r

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    run(p.parse_args().out)
