#!/usr/bin/env python3
"""Posthoc F3 signed-quantile economic falsifier, with 500 asof matched nulls."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from oasis149.canonical import load_149,sha,SRC
from research_reset.predict149.tournament import dataset,portfolio
from research_reset.m0b.enrichment import trial_surrogates
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/"research_reset/predict149/signed_value/results"
SEED=20261019
PLACEBOS=250
ARMS=("F3_QUANTILE_EXPECTED","B0_N4_TOP15","N7_VOL_ONLY")

def bootstrap(x,seed=SEED):
    a=np.asarray(x,float)
    assert len(a)==64
    rng=np.random.default_rng(seed)
    out=[]
    for _ in range(2000):
        ix=[]
        while len(ix)<len(a):
            k=int(rng.integers(len(a)))
            ix.extend((k+j)%len(a) for j in range(3))
        out.append(float(a[np.asarray(ix[:len(a)],int)].mean()))
    return dict(mean=float(a.mean()),
                block_bootstrap_95pct=np.quantile(out,[.025,.975]).tolist(),
                n_monthlike_anchors=64)

def monthly_increment(wealth):
    r=np.diff(np.log(wealth[::21]))
    assert len(r)==64
    return r

def load():
    prediction=pd.read_csv(BASE/"ALL_9536_SIGNED_VALUE_FORECASTS.csv")
    full,roster,days,opens,names=dataset()
    assert len(prediction)==9536 and prediction.block.nunique()==64
    assert set(ARMS)<set(prediction.columns)
    ids=sorted(prediction.block.unique())
    assert all(a+1==b for a,b in zip(ids,ids[1:]))
    future=full.loc[full.block.isin(ids),["block","ticker","future_excess","future_log","top15","category","signal"]]
    combined=prediction.merge(future,on=["block","ticker"],suffixes=("","_fresh"),validate="one_to_one")
    for x in ("future_excess","future_log","top15","category","signal"):
        if x in ("category","signal"):
            assert (combined[x].astype(str)==combined[x+"_fresh"].astype(str)).all()
        else:np.testing.assert_allclose(combined[x],combined[x+"_fresh"],atol=1e-12,rtol=0)
    _,_,C,_,_,signals,_=load_149()
    group=roster.set_index("ticker").macro_category.to_dict()
    members={g:roster.loc[roster.macro_category==g,"ticker"].tolist()
             for g in sorted(set(group.values()))}
    ranked=combined[["block","ticker","future_excess","bottom15","top15"]].copy()
    lookup=ranked.set_index(["block","ticker"])
    vol=np.log(C).diff().rolling(63,min_periods=63).std().loc[
        pd.to_datetime(prediction.groupby("block").signal.first()),names]
    vol.index=pd.to_datetime(prediction.groupby("block").signal.first())
    assert vol.shape==(64,149) and np.isfinite(vol.to_numpy()).all()
    picks={m:[combined.loc[combined.block==b].sort_values(m,ascending=False).head(5).ticker.tolist()
              for b in ids] for m in ARMS}
    return prediction,roster,days,opens,names,ids,picks,lookup,vol,group,members

def true_scores(list_of_five,ids,lookup):
    signed=[];neg=[];positive=[]
    for b,portfolio_names in zip(ids,list_of_five):
        sub=lookup.loc[[(b,t) for t in portfolio_names]]
        signed.append(float(sub.future_excess.mean()))
        neg.append(float(sub.bottom15.mean()))
        positive.append(float((sub.future_excess>0).mean()))
    return np.array(signed),np.array(neg),np.array(positive)

def main():
    a=argparse.ArgumentParser();a.add_argument("--out",required=True)
    dest=Path(a.parse_args().out);dest.mkdir(parents=True,exist_ok=False)
    pred,roster,days,opens,names,ids,picks,lookup,vol,group,members=load()
    base={}
    paths={}
    for m in ARMS:
        signed,tail,pos=true_scores(picks[m],ids,lookup)
        wealth,eco=portfolio(picks[m],ids,opens,names,days)
        paths[m]=wealth
        base[m]=dict(economic=eco,
            signed_relative_log_mean=float(signed.mean()),
            realized_bottom15_rate=float(tail.mean()),
            signed_positive_rate=float(pos.mean()),
            signed_by_anchor=signed.tolist(),
            daily_log_returns_sample_count=len(wealth)-1)
    f=base["F3_QUANTILE_EXPECTED"]
    pair={}
    for m in ("B0_N4_TOP15","N7_VOL_ONLY"):
        s_f=np.asarray(base["F3_QUANTILE_EXPECTED"]["signed_by_anchor"])
        s_b=np.asarray(base[m]["signed_by_anchor"])
        pair[m]=dict(signed_relative_gain=bootstrap(s_f-s_b,SEED+11),
            paired_costed_monthly_growth=bootstrap(
                monthly_increment(paths["F3_QUANTILE_EXPECTED"])-
                monthly_increment(paths[m]),SEED+13))
    placebo=[]
    med_anch={}
    for kind in ("category_only","category_and_vol"):
        outcomes=[]
        for z in range(PLACEBOS):
            rng=np.random.default_rng(SEED+471*z+(0 if kind=="category_only" else 100000))
            selections,difference=trial_surrogates(
                picks["F3_QUANTILE_EXPECTED"],
                list(vol.index),
                vol,group,members,kind,rng)
            signed,tail,pos=true_scores(selections,ids,lookup)
            wealth,econ=portfolio(selections,ids,opens,names,days)
            placebo.append(dict(kind=kind,seed_index=z,
                asof_volatility_mean_abs_log_mismatch=difference,
                mean_signed_relative_log=float(signed.mean()),
                bottom15_rate=float(tail.mean()),
                positive_signed_fraction=float(pos.mean()),
                **econ))
            outcomes.append(signed)
        n=pd.DataFrame([x for x in placebo if x["kind"]==kind])
        expected=np.median(np.asarray(outcomes,float),axis=0)
        obs=np.array(f["signed_by_anchor"],float)
        med_anch[kind]=dict(
            n_trials=len(n),
            median_cagr=float(n.cagr.median()),
            cagr_p05=float(n.cagr.quantile(.05)),
            cagr_p95=float(n.cagr.quantile(.95)),
            F3_percentile_CAGR=float(np.mean(n.cagr<f["economic"]["cagr"])),
            median_drawdown=float(n.max_daily_open_drawdown.median()),
            F3_percentile_better_drawdown=float(
                np.mean(n.max_daily_open_drawdown<f["economic"]["max_daily_open_drawdown"])),
            median_signed_excess=float(n.mean_signed_relative_log.median()),
            F3_percentile_signed_excess=float(
                np.mean(n.mean_signed_relative_log<f["signed_relative_log_mean"])),
            median_bottom15=float(n.bottom15_rate.median()),
            median_positive_fraction=float(n.positive_signed_fraction.median()),
            median_fees=float(n.fee_amount_initial_units.median()),
            signed_F3_minus_anchorwise_median_null=bootstrap(obs-expected,SEED+14),
            F3_pct_above_equal_vol_and_group_conditional_CAGR=float(
                np.mean(n.cagr<f["economic"]["cagr"])))
        print("T149F2_HARD_NULL",kind,json.dumps(med_anch[kind]),flush=True)
    g=med_anch["category_and_vol"]
    # Frozen after prior F3 results. Payoff opportunity includes risk,
    # so never promote on rank-only Spearman or CAGR with loose drawdown.
    passgate=bool(
        pair["B0_N4_TOP15"]["signed_relative_gain"]["block_bootstrap_95pct"][0]>0 and
        g["signed_F3_minus_anchorwise_median_null"]["block_bootstrap_95pct"][0]>0 and
        f["economic"]["cagr"]>g["cagr_p95"] and
        f["economic"]["max_daily_open_drawdown"]>=g["median_drawdown"] and
        f["economic"]["daily_es5"]>=base["B0_N4_TOP15"]["economic"]["daily_es5"])
    report=dict(status="EXACT149_SIGNED_F3_CONDITIONAL_FALSIFICATION_COMPLETE",
        correct_149_source_sha=sha(SRC/"universe.csv"),
        original_source_already_mined=True,
        posthoc_observing_previous_F3_20pct_before_design=True,
        independent_prospective_data=False,
        n_test_monthlike_anchors=64,n_test_original_etfs=149,
        no_training_or_refit_during_stress=True,
        never_use_future_information_in_conditional_placebo_selection=True,
        placebo_total=500,
        original_and_benchmarks=base,
        paired_F3_versus_reference=pair,
        category_and_asof_vol_control=med_anch,
        preregistered_strict_economic_transfer_gate=passgate,
        decision="NO_ACTIVE_TRADING_PROMOTION" if not passgate else
                 "FURTHER_PIT_VALIDATION_REQUIRED_NOT_DEPLOYABLE",
        caveats=["post-hoc second look at already-mined 2021-2026 results",
                 "conditional null matches coarse categories, 63d volatility, identity turnover but not true underlying beta/FX",
                 "Randomized placebo percentile is NOT an independent future-trial probability",
                 "Broker spreads, true delisted instruments, actual EU availability missing"])
    pd.DataFrame(placebo).to_csv(dest/"F3_500_CATEGORY_VOL_MATCHED_PLACEBOS.csv",index=False)
    pd.DataFrame({"date":days[ids[0]*21:(ids[-1]+1)*21+1],
                  **paths}).to_csv(dest/"F3_N4_VOL_MATCHED_DAILY_PATHS.csv",index=False)
    (dest/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("T149F2_FINAL_FALSIFIER",json.dumps(report,allow_nan=False),flush=True)

if __name__=="__main__":main()
