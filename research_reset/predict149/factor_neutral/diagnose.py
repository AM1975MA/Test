#!/usr/bin/env python3
"""Is F3 signed excess truly informative after as-of risk and group matching?

NO new model training or backtest optimization. Uses frozen F3 forecasts and
a common set of strictly as-of class & volatility matched ETF pairs.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from oasis149.canonical import load_149,sha,SRC
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"research_reset/predict149/signed_value/results"
SEED=20261019
BAND=.20
METHODS=("F3_QUANTILE_EXPECTED","B0_N4_TOP15",
         "F2_HURDLE_EXPECTED","N7_VOL_ONLY")

def matched_pair_indices(group,vol,band=BAND):
    """Same group and <=0.20 log difference in realized 63d risk."""
    group=np.asarray(group)
    vol=np.asarray(vol,float)
    if not np.isfinite(vol).all() or np.any(vol<=0):
        raise AssertionError("Invalid as-of risk value")
    i,j=np.triu_indices(len(group),1)
    choose=(group[i]==group[j]) & (
        np.abs(np.log(vol[i]/vol[j]))<=band)
    return i[choose],j[choose]

def concordance(scores,forward,i,j):
    """1 correct signed ordering, 0 incorrect, half credit for ties."""
    score_diff=np.asarray(scores,float)[i]-np.asarray(scores,float)[j]
    ydiff=np.asarray(forward,float)[i]-np.asarray(forward,float)[j]
    if not np.isfinite(score_diff).all() or not np.isfinite(ydiff).all():
        raise AssertionError("Bad matched score")
    correct=np.sign(score_diff)*np.sign(ydiff)
    return float(np.mean(.5+.5*correct))

def bootstrap_month(values,nboot=1800):
    x=np.asarray(values,float)
    assert x.shape==(64,)
    rng=np.random.default_rng(SEED)
    sims=[]
    for _ in range(nboot):
        ix=[]
        while len(ix)<64:
            a=int(rng.integers(64))
            ix.extend((a+k)%64 for k in range(3))
        sims.append(float(np.mean(x[np.asarray(ix[:64],int)])))
    return {"mean":float(np.mean(x)),"ci95":np.quantile(sims,[.025,.975]).tolist()}

def compute():
    p=pd.read_csv(BASE/"ALL_9536_SIGNED_VALUE_FORECASTS.csv")
    roster,O,C,V,days,signals,qual=load_149()
    if len(roster)!=149 or len(p)!=9536:
        raise AssertionError("Universe/time sample changed")
    metadata=json.loads((BASE/"RESULT.json").read_text())
    if sha(SRC/"universe.csv")!=metadata["original_source_sha"]:
        raise AssertionError("149 source manifest drift")
    if p.groupby("block").size().nunique()!=1 or not p.groupby("block").size().eq(149).all():
        raise AssertionError("One 149 signal per anchor lost")
    ids=sorted(p.block.unique())
    if len(ids)!=64:raise AssertionError("Not 64 historical anchors")
    if not set(["Q10","Q50","Q90","category","future_excess",
                "signal",*METHODS])<=set(p):
        raise AssertionError("Archived prediction file missing required output")
    p["ticker"]=p.ticker.astype(str)
    logvol=np.log(C).diff().rolling(63,min_periods=63).std()
    records=[]
    metrics=[]
    for b in ids:
        row=p[p.block==b].copy()
        asof=pd.Timestamp(row.signal.iloc[0])
        quotes=logvol.loc[asof,row.ticker].to_numpy(float)
        row["N7_VOL_ONLY"]=quotes
        i,j=matched_pair_indices(row.category.to_numpy(str),quotes)
        if len(i)<30:
            raise AssertionError("Insufficient matched as-of ETF pairs on "+str(asof))
        Y=row.future_excess.to_numpy(float)
        met={"block":int(b),"signal":str(asof.date()),"n_matched_pairs":len(i),
             "n_instruments":len(row),
             "q10_below":float(np.mean(Y<row.Q10.to_numpy(float))),
             "q50_below":float(np.mean(Y<row.Q50.to_numpy(float))),
             "q90_below":float(np.mean(Y<row.Q90.to_numpy(float))),
             "q10_pinball":float(np.mean(np.maximum(.1*(Y-row.Q10),
                                                 -.9*(Y-row.Q10)))),
             "q90_pinball":float(np.mean(np.maximum(.9*(Y-row.Q90),
                                                 -.1*(Y-row.Q90))))}
        for name in METHODS:
            met[name+"_concordance"]=concordance(
                row[name].to_numpy(float),Y,i,j)
        met["F3_minus_N4"]=met["F3_QUANTILE_EXPECTED_concordance"]-met["B0_N4_TOP15_concordance"]
        met["F3_minus_F2"]=met["F3_QUANTILE_EXPECTED_concordance"]-met["F2_HURDLE_EXPECTED_concordance"]
        met["F3_minus_vol"]=met["F3_QUANTILE_EXPECTED_concordance"]-met["N7_VOL_ONLY_concordance"]
        metrics.append(met)
        for a,z in zip(i,j):
            records.append(dict(block=int(b),signal=str(asof.date()),
                  ticker_a=str(row.ticker.iloc[a]),ticker_b=str(row.ticker.iloc[z]),
                  category=str(row.category.iloc[a]),
                  asof_vol63_a=float(quotes[a]),asof_vol63_b=float(quotes[z]),
                  forward_excess_a=float(Y[a]),forward_excess_b=float(Y[z]),
                  pred_F3_a=float(row.F3_QUANTILE_EXPECTED.iloc[a]),
                  pred_F3_b=float(row.F3_QUANTILE_EXPECTED.iloc[z])))
    panel=pd.DataFrame(metrics)
    subset={}
    for key,years in (("2021_2023",(2021,2022,2023)),("2024_2026",(2024,2025,2026))):
        x=panel[pd.to_datetime(panel.signal).dt.year.isin(years)]
        subset[key]={"anchors":len(x),"F3_concordance":float(x.F3_QUANTILE_EXPECTED_concordance.mean()),
            "N4_concordance":float(x.B0_N4_TOP15_concordance.mean()),
            "vol_concordance":float(x.N7_VOL_ONLY_concordance.mean()),
            "F3_minus_N4":float(x.F3_minus_N4.mean()),
            "q10_tail_coverage":float(x.q10_below.mean()),
            "q90_tail_coverage":float(x.q90_below.mean())}
    intervals={}
    for key in ["F3_QUANTILE_EXPECTED_concordance",
                 "B0_N4_TOP15_concordance","F2_HURDLE_EXPECTED_concordance",
                 "N7_VOL_ONLY_concordance","F3_minus_N4","F3_minus_F2","F3_minus_vol"]:
        intervals[key]=bootstrap_month(panel[key].to_numpy(float))
    asofrisk=intervals["F3_QUANTILE_EXPECTED_concordance"]
    pair=intervals["F3_minus_N4"]
    gate=bool(
        asofrisk["ci95"][0]>.5 and
        pair["ci95"][0]>0 and
        all(subset[x]["F3_concordance"]>.5 for x in subset))
    result=dict(status="ORIGINAL149_F3_FACTOR_VOL_CONDITIONAL_PAIRWISE_AUDIT_COMPLETED",
        n_etfs=149,n_anchor=64,n_ticker_month_forecasts=9536,
        exact_source_roster_sha=sha(SRC/"universe.csv"),
        n_conditional_matched_pairs=int(panel.n_matched_pairs.sum()),
        per_anchor_pairs_min=int(panel.n_matched_pairs.min()),
        per_anchor_pairs_median=float(panel.n_matched_pairs.median()),
        predetermined_abs_log_risk_ratio_band=BAND,
        all_risk_vol_and_group_matches_strict_asof=True,
        no_new_training_or_rebalanced_portfolios=True,
        correct_outcome_used_only_to_score_predictions=True,
        scorer_equal_weight_each_anchor_not_independent_pairs=True,
        matched_conditional_64anchor_bootstrap=intervals,
        by_era=subset,
        quantile_coverage={"q10_future_y_below_pred_q10":float(panel.q10_below.mean()),
            "q50_future_y_below_pred_q50":float(panel.q50_below.mean()),
            "q90_future_y_below_pred_q90":float(panel.q90_below.mean()),
            "q10_pinball":float(panel.q10_pinball.mean()),
            "q90_pinball":float(panel.q90_pinball.mean())},
        preregistered_conditional_direction_skill_gate=gate,
        interpretation="Development diagnostic only, prior model/dates heavily mined",
        caveats=["6 coarse groups + 63d volatility are not fully sufficient factor matching",
                 "Pairs within each anchor are statistically dependent, hence 64 anchor bootstrap",
                 "Prospectively untouched samples not yet available",
                 "No independent PIT fund members, no EUR broker investability",
                 "Actual future group returns never fed into as-of predictions"])
    return panel,pd.DataFrame(records),result

def main():
    a=argparse.ArgumentParser();a.add_argument("--out",required=True)
    out=Path(a.parse_args().out);out.mkdir(parents=True,exist_ok=False)
    panel,pairs,r=compute()
    panel.to_csv(out/"CONCORDANCE_64_ANCHORS.csv",index=False)
    pairs.to_csv(out/"ALL_EXACT_ASOF_VOL_MATCHED_PAIRS.csv",index=False)
    (out/"RESULT.json").write_text(json.dumps(r,indent=2,allow_nan=False)+"\n")
    print("T149_G_CONDITIONAL_DIRECTION_RESULT "+json.dumps(r,allow_nan=False),flush=True)
if __name__=="__main__":main()
