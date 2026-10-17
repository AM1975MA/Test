#!/usr/bin/env python3
"""EU120 original annual OOS margin vs next-month first/second ETF realized spread.

No model inference/fitting; original selection/margin trace must match source.
"""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"europe120/eu120_retrain"),
              str(ROOT/"vendor/etf_trader_v2/src")]
import run_eu120_retrain as eu
import replay_audited as au
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from eu120_compact_return_tail_v1.run import calculate_scores
from eu120_selection_weight_v1.run import original_reference_guard
from paper_ltr_v2.replay import sha

SEED=20261017
N_BOOT=2000
def fmt(x):
    return float(x) if np.isfinite(x) else None

def stat(frame,threshold):
    n=len(frame)
    high=frame[frame.margin>=threshold]
    low=frame[frame.margin<threshold]
    v=frame.spread.to_numpy(float)
    m=frame.margin.to_numpy(float)
    rho=float(spearmanr(m,v).statistic) if n>=3 and np.std(m)>0 and np.std(v)>0 else np.nan
    return dict(months=n,high_months=len(high),low_months=len(low),
        mean_spread=float(np.mean(v)) if n else np.nan,
        first_beats_second=float(np.mean(v>0)) if n else np.nan,
        high_mean_spread=float(high.spread.mean()) if len(high) else np.nan,
        low_mean_spread=float(low.spread.mean()) if len(low) else np.nan,
        high_minus_low_mean_spread=(float(high.spread.mean()-low.spread.mean())
                                   if len(high) and len(low) else np.nan),
        high_winner_probability=float(np.mean(high.spread>0)) if len(high) else np.nan,
        low_winner_probability=float(np.mean(low.spread>0)) if len(low) else np.nan,
        spearman_margin_spread=rho)

def newyear_bootstrap(frame,threshold,seed,N=N_BOOT):
    rng=np.random.default_rng(seed)
    years=sorted(frame.year.unique())
    choices={y:frame[frame.year.eq(y)] for y in years}
    observed=stat(frame,threshold)
    vals=[]
    for _ in range(N):
        selected=rng.choice(years,len(years),replace=True)
        sample=pd.concat([choices[y] for y in selected],ignore_index=True)
        s=stat(sample,threshold)
        vals.append([s["high_minus_low_mean_spread"],s["spearman_margin_spread"]])
    values=np.asarray(vals,float)
    if not np.isfinite(values).all():
        raise ValueError("Year-resample unable to estimate frozen threshold association")
    interval=lambda j:[float(np.percentile(values[:,j],2.5)),
                       float(np.percentile(values[:,j],97.5))]
    rng=np.random.default_rng(seed+1337)
    order_by_year=[np.flatnonzero(frame.year.to_numpy()==y) for y in years]
    actual=observed["spearman_margin_spread"]
    perm=[]
    base=frame.margin.to_numpy(float)
    target=frame.spread.to_numpy(float)
    for _ in range(N):
        shuffled=base.copy()
        for inds in order_by_year:
            shuffled[inds]=rng.permutation(shuffled[inds])
        perm.append(float(spearmanr(shuffled,target).statistic))
    perm=np.asarray(perm)
    p=float((1+np.sum(np.abs(perm)>=abs(actual)))/(N+1))
    return dict(year_cluster_bootstrap_95pct_CI_high_minus_low=interval(0),
        year_cluster_bootstrap_95pct_CI_spearman=interval(1),
        year_conditioned_margin_permutation_two_sided_p=p,
        bootstrap_iterations=N,permutations=N)

def evaluate_one_policy(score,calendar,tickers,open_prices,source_trace,variant):
    dates=pd.DatetimeIndex(calendar.signal_date)
    with np.load(source_trace,allow_pickle=False) as f:
        daily_dates=pd.DatetimeIndex(f["dates"])
        original_d1=f["d1"]
        original_d2=f["d2"]
        original_margin=f["native_margin"]
        if (len(daily_dates)!=2432 or original_d1.shape!=(1,2432) or
            original_d2.shape!=(1,2432) or original_margin.shape!=(1,2432)):
            raise ValueError("Original source official selection array shapes changed")
        if score.shape!=(112,120):
            raise ValueError("Unexpected 112x120 OOS policy scores")
        margin_score=np.where(np.isfinite(score),score,-1e6)
        rows=[]
        for i,row in enumerate(calendar.itertuples(index=False)):
            sig=pd.Timestamp(row.signal_date)
            entry=pd.Timestamp(row.entry_date)
            exitday=pd.Timestamp(row.exit_date)
            if sig!=dates[i] or not (sig<entry<exitday):
                raise ValueError("Trade entered before original forecast signal")
            if entry not in daily_dates or exitday not in daily_dates:
                raise ValueError("Original daily common-open execution date lost")
            day_idx=daily_dates.get_loc(entry)
            s=margin_score[i,:]
            # Only original producer's chosen pair matters; verify the saved
            # d1/d2 were selected solely by as-of score, without future data.
            winner=int(original_d1[0,day_idx])
            runner=int(original_d2[0,day_idx])
            if not 0<=winner<120 or not 0<=runner<120 or winner==runner:
                raise ValueError("Original pair not tradable on month entry")
            expected_gap=float(s[winner]-s[runner])
            observed_gap=float(original_margin[0,day_idx])
            if abs(expected_gap-observed_gap)>1e-11 or expected_gap<0:
                raise ValueError("Saved allocation margin differs from OOS score gap")
            if np.any(s> s[winner]+1e-11) or np.count_nonzero(s>s[runner]+1e-11)>1:
                raise ValueError("Selected ETFs not original first and second scores")
            t1,t2=tickers[winner],tickers[runner]
            if entry not in open_prices.index or exitday not in open_prices.index:
                raise ValueError("Original common-open observation missing")
            pair_open=open_prices.loc[entry,[t1,t2]].to_numpy(float)
            pair_exit=open_prices.loc[exitday,[t1,t2]].to_numpy(float)
            if (not np.isfinite(pair_open).all() or not np.isfinite(pair_exit).all()
                or np.any(pair_open<=0) or np.any(pair_exit<=0)):
                raise ValueError("Unobserved actual frozen ETF adjusted open")
            ret=pair_exit/pair_open-1.
            rows.append(dict(variant=variant,signal_date=str(sig.date()),
                entry_date=str(entry.date()),exit_date=str(exitday.date()),
                year=sig.year,ticker1=t1,ticker2=t2,margin=observed_gap,
                r1=float(ret[0]),r2=float(ret[1]),spread=float(ret[0]-ret[1]),
                top1_beats_top2=bool(ret[0]>ret[1]),
                gross_benefit_50to100_first=float(.5*(ret[0]-ret[1])),
                execution_calendar_days=int((exitday-entry).days)))
    return pd.DataFrame(rows)

def main():
    p=argparse.ArgumentParser()
    for field in ("source","prior-factorial","raw149","out"):
        p.add_argument("--"+field,required=True)
    args=p.parse_args()
    src=Path(args.source).resolve();fact=Path(args.prior_factorial).resolve()
    out=Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refuse to overwrite original results")
    out.mkdir(parents=True)
    frozen=ROOT/"data/eu120"
    provenance=json.loads((frozen/"PROVENANCE.json").read_text())
    manifest=json.loads((frozen/"manifest.json").read_text())
    summary=json.loads((src/"RESULT.json").read_text())
    old=json.loads((fact/"RESULT.json").read_text())
    if (manifest.get("selected_count")!=120 or manifest.get("original149_overlap")!=0
        or provenance["source_manifest_sha256"]!=sha(frozen/"manifest.json")
        or summary["status"]!="EU120_REFITTED_5_POLICY_COMMON_OPEN_COMPLETE"
        or old["status"]!="EU120_16_ARM_MARGIN_AGREEMENT_WEIGHT_COMPLETE"
        or old["original_all_rules_active_PARITY"] is not True):
        raise ValueError("Frozen EU120 provenance or prior-run parity not certified")
    training=pd.read_csv(src/"TRAINING_AUDIT.csv")
    if len(training)!=10 or set(training.year)!=set(range(2017,2027)):
        raise ValueError("Incomplete annual leave-future-out fits")
    for r in training.itertuples(index=False):
        if (not bool(r.lookahead_guard_PASS)
            or pd.Timestamp(r.latest_training_label_exit)>=pd.Timestamp(r.year,1,1)
            or pd.Timestamp(r.ma3_latest_exit)>=pd.Timestamp(r.year,1,1)):
            raise ValueError("Lookahead in prior model training")
    cp=pd.read_parquet(src/"COMPACT_REFITTED.parquet")
    hp=pd.read_parquet(src/"HYBRID_REFITTED.parquet")
    for df in (cp,hp):
        df["signal_date"]=pd.to_datetime(df.signal_date)
        if df.duplicated(["signal_date","ticker"]).any():
            raise ValueError("Duplicate timestamp/ticker trained signal")
    target=pd.read_csv(ROOT/"europe120/eu120_retrain/UNIVERSE_120.csv")
    tickers=target.ticker.astype(str).tolist()
    if (len(tickers)!=120 or len(set(tickers))!=120
        or set(tickers)!=set(pd.read_csv(frozen/"raw_ticker_csv/universe.csv").ticker)):
        raise ValueError("ETF membership unexpectedly changed")
    raw120=out/"scratch"/"raw120";rawref=out/"scratch"/"rawref"
    os.environ["FROZEN_EU120_ROOT"]=str(frozen)
    os.environ["FROZEN_149_ROOT"]=str(Path(args.raw149).resolve())
    eu.download_folder(target,raw120)
    eu.download_folder(pd.DataFrame(dict(ticker=eu.REF_TICKERS,
        macro_category=["REF_US","REF_CREDIT","REF_BOND","REF_CASH","REF_CASH"])),rawref)
    prices,_,_=load_ticker_csv_folder(raw120)
    refs,_,_=load_ticker_csv_folder(rawref)
    common_dates=pd.DatetimeIndex(sorted(set(cp.signal_date)&set(hp.signal_date)))
    calendar=au.common_calendar(pd.concat(
        [prices["Open"][tickers],refs["Open"][eu.REF_TICKERS]],axis=1).sort_index(),common_dates)
    if len(calendar)!=112:raise ValueError("Missing full 112 original common-open month cohort")
    cp=cp[cp.signal_date.isin(calendar.signal_date)].copy()
    hp=hp[hp.signal_date.isin(calendar.signal_date)].copy()
    scores,_=calculate_scores(cp,hp,calendar,tickers)
    threshold=float(au.m.highcagr24.TOP1_MARGIN)
    if not (0<threshold<.5):raise ValueError("Original margin cutoff invalid")
    rows=[]
    for variant,score,control in (
        ("H",scores["H_ONLY"],"H_D_M1_A1"),
        ("R",scores["R_H"],"R_D_M1_A1")):
        path=fact/(control+".npz")
        data=evaluate_one_policy(score,calendar,tickers,
            prices["Open"][tickers],path,variant)
        if len(data)!=112:raise ValueError("Source policy decisions missing")
        rows.append(data)
    both=pd.concat(rows,ignore_index=True)
    both.to_csv(out/"MONTHLY_MARGIN_CALIBRATION.csv",index=False)
    # Both observed policies share same raw market entry/exit dates.
    h,r=(both[both.variant.eq(v)].reset_index(drop=True) for v in ("H","R"))
    if not h[["signal_date","entry_date","exit_date"]].equals(
        r[["signal_date","entry_date","exit_date"]]):
        raise ValueError("Different source monthly outcome dates")
    yearly=[]
    periods={}
    results={}
    for variant,frame in (("H",h),("R",r)):
        summary=stat(frame,threshold)
        if summary["high_months"]<10 or summary["low_months"]<10:
            raise ValueError("Insufficient high-vs-low original score margin sample")
        bootstrap=newyear_bootstrap(frame,threshold,SEED+(0 if variant=="H" else 17))
        quarters=pd.qcut(frame.margin,4,labels=False,duplicates="drop")
        quartiles=[]
        for i in range(quarters.nunique()):
            part=frame[quarters.eq(i)]
            quartiles.append(dict(quartile=i+1,months=len(part),
                median_margin=float(part.margin.median()),
                top1_beats_top2=float(part.top1_beats_top2.mean()),
                realized_spread=float(part.spread.mean())))
        halves={}
        for name,partition in (("2017-2021",frame[frame.year<=2021]),
                               ("2022-2026_partial",frame[frame.year>=2022])):
            halves[name]=stat(partition,threshold)
        for year,g in frame.groupby("year"):
            yearly.append(dict(variant=variant,year=int(year),**stat(g,threshold)))
        results[variant]=dict(primary=summary,uncertainty=bootstrap,
            descriptive_margin_quartiles=quartiles,chronological_halves=halves)
    pd.DataFrame(yearly).to_csv(out/"YEARLY_MARGIN_CALIBRATION.csv",index=False)
    # Paired original source months, year cluster-resampled contrast of
    # high-vs-low separation between the two independent model score policies.
    rng=np.random.default_rng(SEED+42)
    years=sorted(h.year.unique())
    delta=[]
    for _ in range(N_BOOT):
        ys=rng.choice(years,len(years),replace=True)
        s1=pd.concat([h[h.year.eq(y)] for y in ys],ignore_index=True)
        s2=pd.concat([r[r.year.eq(y)] for y in ys],ignore_index=True)
        d=stat(s2,threshold)["high_minus_low_mean_spread"]-stat(s1,threshold)["high_minus_low_mean_spread"]
        if np.isfinite(d):delta.append(float(d))
    if len(delta)<.98*N_BOOT:
        raise ValueError("Too many undefined paired block-bootstrap contrasts")
    observed=(results["R"]["primary"]["high_minus_low_mean_spread"]-
              results["H"]["primary"]["high_minus_low_mean_spread"])
    report=dict(status="EU120_MARGIN_DIRECT_FORWARD_CALIBRATION_COMPLETE",
        frozen_threshold=threshold,
        fully_verified_prediction_months=112,calendar_years=10,
        original_eu120_tickers=120,observational_study=True,
        raw_open_source_run=36597035280,
        frozen_forecast_refit_run=39063271012,
        prior_verified_daily_replay_run=39066645910,
        source_manifest_sha256=sha(frozen/"manifest.json"),
        annual_prediction_sha256=sha(src/"COMPACT_REFITTED.parquet"),
        hybrid_forecast_sha256=sha(src/"HYBRID_REFITTED.parquet"),
        protocol_sha256=sha(Path(__file__).with_name("PROTOCOL.md")),
        model_fits_run=0,threshold_tuning_run=0,
        policies=results,
        paired_R_minus_H_margin_calibration=dict(
            high_low_spread_diff=float(observed),
            year_cluster_bootstrap_95pct_CI=[
                float(np.percentile(delta,2.5)),float(np.percentile(delta,97.5))]),
        labels_used_only_in_expost_assessment=True,
        measurement="Top1 ETF raw adjusted next-common-open monthly return minus Top2 ETF return; not a V2 realized net return.",
        prospectively_independent=False,
        existing_universe_selection_bias=True,
        production_modified=False)
    (out/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("EU120_MARGIN_CALIBRATION_COMPLETE "+json.dumps(
        dict(threshold=threshold,policies=results,
             paired_R_minus_H_margin_calibration=report["paired_R_minus_H_margin_calibration"]),allow_nan=False),flush=True)

if __name__=="__main__":main()
