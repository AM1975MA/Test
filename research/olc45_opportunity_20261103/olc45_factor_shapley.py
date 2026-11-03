#!/usr/bin/env python3
"""OLC45 retrospective sector opportunity decomposition, not an investable strategy.
Exact Shapley attribution of monthly EX-POST top1/top2 opportunity to candidate ETFs.
No model trained, no CAGR claim, no use of future target in strategy selection.
"""
from __future__ import annotations
from itertools import permutations
from pathlib import Path
import numpy as np
import pandas as pd
import json
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results";OUT.mkdir(exist_ok=True)
ART=ROOT/"source_artifact"
BASE=ROOT.parent/"sector_opportunity_e1_20261103"/"baseline_oracle_2021_2024.csv"
CANDIDATES={
"EU":{
"G2X.DE":"GOLD_MINERS",
"USPY.DE":"CYBERSECURITY",
"WTIC.DE":"DIVERSIFIED_COMMODITY",
"2B76.DE":"ROBOTICS",
},
"USA":{
"BOTZ":"ROBOTICS",
"LIT":"LITHIUM_BATTERY",
"PAVE":"INFRASTRUCTURE",
}
}
# E1 CMOD.MI excluded from risk-enabled screening due to 539/2400 bad OHLC.
EXCLUDED={"CMOD.MI":"Incoherent intraday OHLC despite observed open-only prices."}

def top2_val(best, second, values):
    return np.mean(sorted([best,second]+list(values),reverse=True)[:2])

def main():
    old=pd.read_csv(BASE)
    c=pd.read_csv(ART/"candidate_monthly_labels.csv")
    assert len(old)==96 and old.groupby("market").size().to_dict()=={"EU":48,"USA":48}
    needed={"market","ticker","signal_date","candidate_logbp","prior_observed_opens"}
    assert needed<=set(c)
    c=c[c.apply(lambda z:z.ticker in CANDIDATES.get(z.market,{}),axis=1)]
    c=c[c.prior_observed_opens>=500]
    assert not c.duplicated(["market","ticker","signal_date"]).any()
    month=[];shap=[]
    for r in old.itertuples(index=False):
        group=c[(c.market==r.market)&(c.signal_date==r.signal_date)]
        curr=CANDIDATES[r.market]
        vals={str(z.ticker):float(z.candidate_logbp) for z in group.itertuples()}
        tks=sorted(vals)
        assert len(tks)==len(curr),(r.market,r.signal_date,len(tks),len(curr))
        first=float(r.oracle_top1_logbp)
        second=2*float(r.oracle_top2_logbp)-first
        def v1(inc):return max([first]+[vals[t] for t in inc])
        def v2(inc):return float(top2_val(first,second,[vals[t] for t in inc]))
        gain1=v1(tks)-v1([])
        gain2=v2(tks)-v2([])
        norders=0;contrib1={t:0 for t in tks};contrib2={t:0 for t in tks}
        for perm in permutations(tks):
            included=[]
            for t in perm:
                prev1,prev2=v1(included),v2(included)
                included.append(t)
                contrib1[t]+=v1(included)-prev1
                contrib2[t]+=v2(included)-prev2
            norders+=1
        for t in tks:
            z1=contrib1[t]/norders;z2=contrib2[t]/norders
            assert z1>=-1e-8 and z2>=-1e-8
            shap.append({"market":r.market,"signal_date":r.signal_date,"year":int(str(r.signal_date)[:4]),
                         "ticker":t,"theme":curr[t],
                         "shapley1_logbp":z1,"shapley2_logbp":z2,
                         "single_gain1_logbp":max(0,vals[t]-first),
                         "candidate_logbp":vals[t],"original_best1_logbp":first})
        assert abs(sum(contrib1.values())/norders-gain1)<1e-5
        assert abs(sum(contrib2.values())/norders-gain2)<1e-5
        wins=[t for t in tks if vals[t]>first]
        month.append({"market":r.market,"signal_date":r.signal_date,"year":int(str(r.signal_date)[:4]),
                      "original_top1_logbp":first,"expanded_top1_logbp":v1(tks),
                      "original_top2_logbp":float(r.oracle_top2_logbp),
                      "expanded_top2_logbp":v2(tks),
                      "gain_top1_logbp":gain1,"gain_top2_logbp":gain2,
                      "any_new_beats_old_top1":bool(wins),
                      "new_winner":max(tks,key=lambda t:vals[t]) if wins else "",
                      "n_eligible_new":len(vals)})
    monthly=pd.DataFrame(month);shapley=pd.DataFrame(shap)
    monthly.to_csv(OUT/"olc45_expost_oracle_monthly.csv",index=False)
    shapley.to_csv(OUT/"olc45_shapley_by_ticker_month.csv",index=False)
    summary=monthly.groupby("market").agg(
        months=("signal_date","count"),new_winner_months=("any_new_beats_old_top1","sum"),
        mean_oracle1_gain_logbp=("gain_top1_logbp","mean"),
        mean_oracle2_gain_logbp=("gain_top2_logbp","mean")).reset_index()
    summary.to_csv(OUT/"olc45_market_summary.csv",index=False)
    bytheme=shapley.groupby(["market","ticker","theme"]).agg(
        shapley1_total_logbp=("shapley1_logbp","sum"),
        shapley2_total_logbp=("shapley2_logbp","sum"),
        single_gain1_total_logbp=("single_gain1_logbp","sum"),
        months_positive_shapley1=("shapley1_logbp",lambda x:int((x>1e-8).sum())),
        candidate_avg_logbp=("candidate_logbp","mean")
    ).reset_index()
    for mk,g in bytheme.groupby("market"):
        den=g.shapley1_total_logbp.sum()
        bytheme.loc[g.index,"share_of_total_shapley1_pct"]=100*g.shapley1_total_logbp/(den if den>0 else 1)
        assert np.isclose(den,monthly[monthly.market==mk].gain_top1_logbp.sum(),atol=1e-5)
    bytheme.to_csv(OUT/"olc45_theme_shapley_priority.csv",index=False)
    corr_rows=[]
    for market,group in c.groupby("market"):
        wide=group.pivot(index="signal_date",columns="ticker",values="candidate_logbp")
        cor=wide.corr()
        for i,t in enumerate(cor.index):
            for t2 in list(cor.columns)[i+1:]:
                corr_rows.append({"market":market,"ticker1":t,"ticker2":t2,
                                  "corr_monthly_forward_log_returns":float(cor.loc[t,t2]),
                                  "n_months":int(wide[[t,t2]].dropna().shape[0])})
    pd.DataFrame(corr_rows).to_csv(OUT/"olc45_overlap_correlations.csv",index=False)
    years=monthly.groupby(["market","year"]).agg(
        mean_top1_gain_logbp=("gain_top1_logbp","mean"),
        mean_top2_gain_logbp=("gain_top2_logbp","mean"),
        new_best_months=("any_new_beats_old_top1","sum")
    ).reset_index()
    years.to_csv(OUT/"olc45_yearly.csv",index=False)
    print("== OLC45 EX-POST OPPORTUNITY ==")
    print(summary.to_string(index=False))
    print("== SHAPLEY THEMES ==")
    print(bytheme.to_string(index=False))
    (OUT/"olc45_manifest.json").write_text(json.dumps({
        "status":"EXPOST RESEARCH; no investable strategy, not model forecast",
        "source":"frozen original OLC32 E1 baseline, E1 Yahoo adjusted Open candidates",
        "period":"48 monthly decisions 2021-2024 per market",
        "candidate_universes":CANDIDATES,"excluded_intraday_data":EXCLUDED,
        "shapley":"exact 4! EU and 3! USA permutations for oracle maximum Top1/Top2",
        "temporal_guard":"no label-based selection in a trading decision; outcomes used ONLY for retrospective opportunity diagnosis",
        "overlap":"Pearson correlation of realized monthly returns, descriptive not future predictor",
        "nonindependent_preexisting_research":"all 2021-24 years explored many times",
    },indent=2))
if __name__=="__main__":main()
