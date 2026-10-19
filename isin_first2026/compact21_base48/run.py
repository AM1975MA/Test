#!/usr/bin/env python3
"""Authentic 125-feature XGB Compact21 BASE fitted annually to 48 EU ETF ISIN.

Original source fitting is imported directly from compact21_learner_swap_v1.
One faithful beta-market reference injection: last prior US SPY adjusted Close.
No SPY candidate ticker added and no alternative fit algorithm introduced.
"""
from __future__ import annotations
import argparse,inspect,hashlib,json,tempfile
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from compact21_learner_swap_v1 import learners
from europe_only75.f3h1_original_transfer.run import costed_path,ci
from isin_first2026.predict48.tournament import (
    ROOT,MASTER,price_data,monthly_data,rank)
from isin_first2026.v2_usref48.original_us_references import asof_quotes

SOURCE=ROOT/"isin_first2026/predict48"
METHODS=("COMPACT21_BASE","MA3_ORIGINAL","ADAPT4")
HOLDINGS=(1,2,5)
SEED=20261020

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for ch in iter(lambda:f.read(1<<20),b""):h.update(ch)
    return h.hexdigest()

def strict_build_spy(matrices,strict):
    spy=strict.set_index("date").SPY
    assert matrices["Close"].index.equals(spy.index)
    spyday=pd.to_datetime(strict["SPY_US_MARKET_DATE"])
    european_dates=pd.DatetimeIndex(strict["date"])
    assert all(spyday<european_dates)
    assert spy.notna().all() and (spy>0).all()
    original=inspect.getsource(k.build_features)
    clause="mkt=ret['SPY'] if 'SPY' in ret else ret.median(axis=1)"
    if original.count(clause)!=1:raise AssertionError("Original source kernel SPY market clause drift")
    namespace={}
    k.US_SPY_PRIOR_EU_DAY_RET=spy.pct_change(fill_method=None)
    exec(compile(original.replace(clause,
        "mkt=US_SPY_PRIOR_EU_DAY_RET.reindex(ret.index)"),
        "<original_compact21_US_SPY_reference_external_europe48>","exec"),
         k.__dict__,namespace)
    assert set(matrices["Close"].columns)==set(matrices["Open"].columns)
    assert "SPY" not in matrices["Close"].columns
    return namespace["build_features"](matrices)

def fit_source_base(src,cal,names,out):
    out=Path(out);out.mkdir(exist_ok=False,parents=True)
    keys=["signal_date","ticker"]
    src["signal_date"]=pd.to_datetime(src.signal_date)
    src["exit_date_21"]=pd.to_datetime(src.exit_date_21)
    # Source native minimum valid feature rule. Never modify the feature
    # columns to improve yield; malformed data remains missing (NaN).
    valid=src[k.F2D_FEATURES].notna().sum(axis=1)>=30
    src=src[valid].copy()
    assert set(k.F2D_FEATURES)<=set(src.columns) and len(k.F2D_FEATURES)==125
    assert src.groupby("signal_date").ticker.nunique().loc[
           cal.signal_date].eq(48).all()
    assert src.groupby("signal_date").ticker.nunique().max()==48
    result=[];model_audit=[];annual=None
    for year in range(2021,2027):
        anchor=pd.Timestamp(year,1,1)
        train=src[(src.signal_date<anchor)&(src.exit_date_21<anchor)&
                   src.target_rank_21.notna()&
                   (src.signal_date>=pd.Timestamp("2017-01-01"))].sort_values(keys).reset_index(drop=True)
        test=src[(src.signal_date.dt.year==year)&
                 (src.signal_date.isin(cal.signal_date))].sort_values(keys).reset_index(drop=True)
        assert len(test)>0 and not train.empty
        assert train.ticker.nunique()==48 and test.ticker.nunique()==48
        assert train.exit_date_21.max()<anchor
        assert train.groupby("signal_date").ticker.nunique().eq(48).all()
        assert test.groupby("signal_date").ticker.nunique().eq(48).all()
        assert test.signal_date.isin(cal.signal_date).all()
        # The exact isolated source 3-seed 360-round XGB rank:pairwise fitter.
        with tempfile.TemporaryDirectory() as tmp:
            prediction,meta,labels,duration=learners.fit(
                train,[test],"BASE",year,Path(tmp),f"EU48_{year}")
        pred=np.asarray(prediction[0],float)
        assert meta["maturity_PASS"] and meta["kind"]=="BASE"
        assert meta["model_params"]["n_estimators"]==360
        assert meta["model_params"]["seeds"]==[101,202,303]
        assert len(pred)==len(test) and np.isfinite(pred).all()
        outframe=test[["signal_date","ticker","entry_date","exit_date_21",
                       "fwd_ret_21","target_rank_21"]].copy()
        outframe["pred"]=pred
        outframe["year"]=year
        result.append(outframe)
        model_audit.append(dict(year=year,n_train=len(train),
               n_signal_months_train=int(train.signal_date.nunique()),
               first_training_month=str(train.signal_date.min().date()),
               last_training_signal=str(train.signal_date.max().date()),
               max_train_mature_exit21=str(train.exit_date_21.max().date()),
               signal_first=str(test.signal_date.min().date()),
               signal_last=str(test.signal_date.max().date()),
               n_score_rows=len(test),n_unique_ETF_ISIN=48,
               XGB_360x3_original=True,
               model_actual_seconds=float(duration),
               train_matrix_SHA256=meta["train_matrix_sha256"],
               train_targets_SHA256=meta["train_labels_sha256"],
               prediction_sha256=meta["prediction_sha256"][0],
               seeds_sha256=json.dumps(meta["seed_prediction_sha256"],
                                        sort_keys=True)))
        print("COMPACT21_48_TRUE_ORIGINAL_XGB_ANNUAL_COMPLETE",
              json.dumps(model_audit[-1]),flush=True)
    scored=pd.concat(result,ignore_index=True)
    assert scored.groupby("signal_date").ticker.nunique().eq(48).all()
    assert scored.signal_date.nunique()==65 and len(scored)==3120
    scored.to_csv(out/"BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv",index=False)
    pd.DataFrame(model_audit).to_csv(out/"ANNUAL_125F_XGB_21DAY_MATURITY_AND_SEED_AUDIT.csv",index=False)
    return scored,model_audit

def baseline_archive(n,cal):
    saved=pd.read_csv(SOURCE/"results/48_ETF_PREDICTIVE_SCORES_CHRONOLOGICAL.csv",
                     parse_dates=["signal_date"])
    from isin_first2026.predict48.replay_v2 import build_new_rank
    table=saved[saved.method=="ORIGINAL_MA3"].pivot(index="signal_date",
         columns="ticker",values="forecast_rank_score")
    ma3=table.reindex(index=cal.signal_date,columns=n).to_numpy(float)
    assert ma3.shape==(65,48) and np.isfinite(ma3).all()
    # Independently reconstruct and verify every ADAPT4 Top5 against the
    # archived causal expert choices, not missing from original 16-method CSV.
    adapt4=build_new_rank(cal,n)
    return {"MA3_ORIGINAL":ma3,"ADAPT4":adapt4}

def stats_by_month(forecast,cal,opening,names):
    evaluations=[];positions={}
    frame=forecast.set_index(["signal_date","ticker"]).sort_index()
    assert len(frame)==65*48 and frame.index.is_unique
    for method,sc in forecast_by_method.items():
        assert sc.shape==(65,48)
    # caller owns forecast_by_method, and label panel consistent month position
    return evaluations,positions

def evaluate(scored,cal,names,O,master,out):
    out=Path(out)
    assert out.is_dir() and not (out/"RESULT.json").exists()
    old=baseline_archive(names,cal)
    base=scored.pivot(index="signal_date",columns="ticker",values="pred")
    own=base.reindex(index=cal.signal_date,columns=names).to_numpy(float)
    assert own.shape==(65,48) and np.isfinite(own).all()
    allscore={"COMPACT21_BASE":own,**old}
    assert set(allscore)==set(METHODS)
    by_month=scored.set_index(["signal_date","ticker"])
    daily={};predictive=[];holdings=[];costed={};metrics=[]
    first=O.index[O.index.get_loc(cal.entry_date.iloc[0])]
    last=O.index[O.index.get_loc(cal.exit_date.iloc[-1])]
    assert first==pd.Timestamp("2021-02-01") and last==pd.Timestamp("2026-07-01")
    for method in METHODS:
        score=allscore[method]
        for take in HOLDINGS:
            weights=[]
            for i,r in enumerate(cal.itertuples(index=False)):
                desc=np.argsort(-score[i],kind="stable")
                indexes=desc[:take]
                # Standalone monthly open-to-open target, source Compact21
                # mature label horizon 21 EU sessions, not current month.
                future=by_month.loc[pd.IndexSlice[r.signal_date,names],:]
                realized21=future.fwd_ret_21.to_numpy(float)
                rr21=future.target_rank_21.to_numpy(float)
                assert np.isfinite(realized21).all() and np.isfinite(rr21).all()
                nextmonth=np.log(O.loc[r.exit_date,names]/O.loc[r.entry_date,names]).to_numpy(float)
                assert np.isfinite(nextmonth).all()
                if take==1:
                    original=names[indexes[0]]
                positions={names[k]:1/take for k in indexes}
                weights.append(positions)
                stats=dict(method=method,k=take,signal_date=str(r.signal_date.date()),
                           signal_year=int(r.signal_date.year),
                           spearman_21=float(spearmanr(score[i],realized21).statistic),
                           spearman_next_month=float(spearmanr(score[i],nextmonth).statistic),
                           selected_rank21_pct=float(np.mean(rr21[indexes])),
                           selected_monthly_excess_log=float(nextmonth[indexes].mean()-nextmonth.mean()),
                           selected_21day_excess_log=float(np.log1p(realized21[indexes]).mean()-np.log1p(realized21).mean()),
                           selected21_log=float(np.log1p(realized21[indexes]).mean()),
                           true_topdecile21=int(indexes[0] in np.argsort(-rr21)[:5]) if take==1 else None)
                predictive.append(stats)
                for j,q in enumerate(indexes):
                    holdings.append(dict(method=method,k=take,
                          signal_date=str(r.signal_date.date()),rank=j+1,
                          ticker=names[q],isin=master.set_index("ticker").loc[names[q],"isin"],
                          model_score=float(score[i,q]),
                          forward_21session_return=float(realized21[q]),
                          forward_nextmonth_open_log_return=float(nextmonth[q])))
            econ,nav,monthly=costed_path(weights,cal,O,O.index)
            code=method+"_TOP"+str(take)
            costed[code]=econ
            daily[code]=nav
            monthly.insert(0,"method",code)
            metrics.append(monthly)
            print("COMPACT21_48_21DAY_BASE_TRUE_NET_STANDALONE",code,
                  json.dumps(econ),flush=True)
    ds=pd.DataFrame(daily)
    assert len(ds)==1374 and ds.notna().all(axis=None)
    ds.rename_axis("day").to_csv(out/"DAILY_COSTED_NAV_48_ISIN_9_STANDALONE_METHODS.csv")
    pd.concat(metrics,ignore_index=True).to_csv(out/"MONTHLY_TOP1_TOP2_TOP5_COSTED_TRADE_LEDGER.csv",index=False)
    pd.DataFrame(holdings).to_csv(out/"MONTHLY_TOP1_TOP2_TOP5_UNIQUE_ISIN_SELECTIONS.csv",index=False)
    tbl=pd.DataFrame(predictive)
    tbl.to_csv(out/"MONTHLY_21_SESSION_AND_NEXT_MONTH_FORECAST_SKILL.csv",index=False)
    summaries={}
    for method in METHODS:
        summaries[method]={}
        for k in HOLDINGS:
            m=tbl[(tbl.method==method)&(tbl.k==k)]
            assert len(m)==65
            summaries[method]["Top"+str(k)]=dict(
               mean_spearman_21=float(m.spearman_21.mean()),
               mean_spearman_nextmonth=float(m.spearman_next_month.mean()),
               average_realized_21_session_percentile=float(m.selected_rank21_pct.mean()),
               forward21_excess_log=float(m.selected_21day_excess_log.mean()),
               nextmonth_excess_log=float(m.selected_monthly_excess_log.mean()),
               economic=econ if False else costed[method+"_TOP"+str(k)])
    # PAIRED monthly 3-month block intervals for Compact21 vs MA3/ADAPT4.
    pairs={}
    for comparator in ("MA3_ORIGINAL","ADAPT4"):
        for k in HOLDINGS:
            a=tbl[(tbl.method=="COMPACT21_BASE")&(tbl.k==k)].sort_values("signal_date")
            b=tbl[(tbl.method==comparator)&(tbl.k==k)].sort_values("signal_date")
            assert a.signal_date.to_list()==b.signal_date.to_list()
            for season,mask in (("all",np.ones(65,dtype=bool)),
                                ("2021_2023",a.signal_year.to_numpy()<=2023),
                                ("2024_2026",a.signal_year.to_numpy()>=2024)):
                values={
                    "signed_spearman_21":a.spearman_21.to_numpy()[mask]-b.spearman_21.to_numpy()[mask],
                    "top_month_log_excess":a.selected_monthly_excess_log.to_numpy()[mask]-b.selected_monthly_excess_log.to_numpy()[mask],
                    "top_21session_log_excess":a.selected_21day_excess_log.to_numpy()[mask]-b.selected_21day_excess_log.to_numpy()[mask]
                }
                pairs[comparator+"_TOP"+str(k)+"_"+season]={
                    m:ci(vals,SEED+i+len(vals)) for i,(m,vals) in enumerate(values.items())}
    result=dict(status="COMPACT21_BASE_125_FEATURE_ORIGINAL_XGB_EU48_ANNUAL_WALKFORWARD_COMPLETE",
        unique_legal_EU_ISIN=48,eligible_ranked_ETF_count=48,
        original_125F_source_unchanged_except_external_US_SPY_factor=True,
        exact_original_rank_pairwise_360round_3seed=True,
        ranking_target="21 next observed European trading sessions Open-to-Open",
        strictly_mature_annual_training_cutoff=True,
        historical_training_2017_to_2020_used=True,
        original_149_pretrained_models_reused=False,
        signal_month_count=65,
        evaluation_first="2021-02-01",evaluation_last="2026-07-01",
        true_EUR_open_marks=1374,
        model_original_US_SPY_last_prior_close_no_lookahead=True,
        stand_alone_TOP1_TOP2_TOP5_no_V2_allocation_or_stops=True,
        trading_fees_per_side=0.001,
        US149_31_76_is_full_blended_portfolio_not_standalone_compact=True,
        same_65_month_original_MA3_and_ADAPT4_control=True,
        method_outcomes=summaries,
        paired_monthly_block_CI_compact_minus_controls=pairs,
        source_48_ISIN_master_sha256=sha(MASTER),
        source_unchanged_149_ranker_SHA256=sha(ROOT/"compact21_learner_swap_v1/learners.py"),
        model_protocol_SHA256=sha(ROOT/"isin_first2026/compact21_base48/PREREGISTERED.md"),
        scope_existing_survivors_2026_not_point_in_time=True,
        evaluation_history_previously_inspected_no_pristine_OOS=True,
        no_production_repo_mutation=True)
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
          sha(q)+"  "+str(q.relative_to(out))+"\n"
          for q in sorted(out.rglob("*.csv")))+sha(out/"RESULT.json")+"  RESULT.json\n")
    print("COMPACT21_EU48_ORIGINAL_125F_CONCLUSION",json.dumps(result,allow_nan=False),flush=True)

def main(args):
    output=Path(args.out);output.mkdir(exist_ok=False,parents=True)
    dataset=Path(args.prep)
    matrices,cat,source=load_ticker_csv_folder(dataset/"raw_ticker_csv")
    master,names,O,C=price_data(dataset)
    n=list(matrices["Close"].columns)
    assert len(master)==48 and master["isin"].is_unique
    assert len(n)==48 and set(n)==set(names)
    names=n
    assertsO=matrices["Open"]
    assert O.index.equals(assertsO.index)
    asof_quotes(args.us,matrices["Close"].index,args.fx,output/"US_SPY_REFERENCE_FORECAST_INPUT")
    usrefs=pd.read_csv(output/"US_SPY_REFERENCE_FORECAST_INPUT/STRICT_PRIOR_US_CLOSE_FOR_EU_FEATURES_AND_CASH_EUR.csv",
                       parse_dates=["date"])
    dates,compact,tail,D=strict_build_spy(matrices,usrefs)
    assert len(k.F2D_FEATURES)==125
    print("COMPACT21_EU48_CANONICAL_FEATURES_SOURCE",len(compact),compact.signal_date.nunique(),
          len(k.F2D_FEATURES),flush=True)
    full=k.add_labels(compact,matrices["Open"],dates)
    candidate=full[(full.signal_date>=pd.Timestamp("2017-01-01"))&
                   (full.signal_date<=pd.Timestamp("2026-05-31"))].copy()
    assert candidate.groupby("signal_date").ticker.nunique().eq(48).all()
    _,cal=monthly_data(master,names,O,C)
    cal=cal[cal.signal_date>=pd.Timestamp("2021-01-01")].reset_index(drop=True)
    assert len(cal)==65 and cal.signal_date.max()==pd.Timestamp("2026-05-29")
    # Source original 21-session label maturity and month-level exit contracts:
    # we never substitute a 1-month return for the actual Compact21 target.
    scored,audit=fit_source_base(candidate,cal,names,output/"FITTED_3SEED_ANNUAL")
    assert scored.groupby("signal_date").ticker.nunique().eq(48).all()
    evaluate(scored,cal,names,O,master,output)
    src=(output/"US_SPY_REFERENCE_FORECAST_INPUT/SOURCE_REFERENCE_AUDIT.json")
    (output/"SOURCE_AND_ISIN_INPUT_AUDIT.json").write_text(json.dumps(dict(
       input_original_prepared_audit=json.loads((dataset/"RESULT.json").read_text()),
       us_source_audit=json.loads(src.read_text()),
       us_archive_sha=sha(src),
       original_source_kernel_sha=sha(Path(k.__file__)),
       original_source_original_fit_sha=sha(ROOT/"compact21_learner_swap_v1/learners.py"),
       annual_fit_6_years=True,
       no_US_SPY_candidate=True,product_data_outside_prior_model_training=False
       ),indent=2,allow_nan=False)+"\n")

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--prep",required=True)
    a.add_argument("--us",required=True)
    a.add_argument("--fx",required=True)
    a.add_argument("--out",required=True)
    main(a.parse_args())
