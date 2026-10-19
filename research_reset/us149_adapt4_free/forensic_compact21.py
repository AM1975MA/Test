#!/usr/bin/env python3
"""Read-only audit reconciling historical Compact21 BASE31.76 and new MA3 free149 10.48.

No predictive model fit. Historical 2017-26 three full-149 'BASE' source paths
from original canonical V2 run 39044619710, and NEW genuine-retrained
2021-26 single-149 ETF Trader MA3/ADAPT4 source certified run 39338133099.
Measure common-window conditional realized returns without extrapolation.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd

def sh(f):
    h=hashlib.sha256()
    with open(f,"rb") as s:
        for v in iter(lambda:s.read(1<<20),b""):h.update(v)
    return h.hexdigest()
def stats(prices,dates,reset=False,initial=1.):
    nav=np.asarray(prices,float)
    assert len(nav)==len(dates) and np.isfinite(nav).all() and (nav>0).all()
    returns=np.diff(np.log(np.r_[initial,nav]))
    r=np.expm1(returns)
    peak=np.maximum.accumulate(np.r_[initial,nav])[1:]
    std=r.std(ddof=1)
    return dict(n_days=len(nav),start=str(dates[0].date()),end=str(dates[-1].date()),
        cagr=float(np.expm1(returns.sum()*252/len(returns))),
        maxdd=float(np.min(nav/peak-1)),
        sharpe=float(r.mean()*np.sqrt(252)/std) if std>0 else 0,
        total_wealth_ratio=float(nav[-1]/initial))
def byyear(nav,dates,first):
    prev=first;result={}
    for year in sorted(set(dates.year)):
        k=dates.year==year
        later=float(nav[k][-1])
        result[str(year)]=float(later/prev-1)
        prev=later
    return result
def loadnpz(path):
    with np.load(path,allow_pickle=False) as z:
        d=pd.DatetimeIndex(pd.to_datetime(z["dates"]))
        eq=np.asarray(z["equity"],float)
        assert eq.shape==(1,len(d))
        return d,eq[0]
def main(old,new,out):
    old=Path(old);new=Path(new);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    npz=[];rows=[];annual=[]
    for i in (1,2,3):
        root=old/f"v2replay-ECON_TOP5_RERANK-r{i}"
        meta=json.loads((root/"RESULT.json").read_text())
        assert meta["audit"]["baseline_replay"]["PASS"] and meta["audit"]["input_linkage"]["PASS"]
        assert meta["baseline"]["candidate_count"]==149
        for key,dir,scope in (("COMPACT21_BASE","baseline_control","baseline"),("ECON_TOP5_RERANK","candidate","candidate")):
            path=root/dir/"FULL_UNIVERSE_PATH.npz"
            dt,e=loadnpz(path)
            assert len(dt)==2366 and dt[0]==pd.Timestamp("2017-02-01") and dt[-1]==pd.Timestamp("2026-07-01")
            full=stats(e,dt)
            prev=json.loads((root/dir/"RESULT.json").read_text())["v2_full_universe"]
            assert abs(full["cagr"]-prev["cagr"])<1e-12
            # Conditional wealth-path gain from close of 2021-01 previous US session to
            # 2026-07. Portfolio holdings continue from 2017, not newly invested at 2021.
            active=dt>=pd.Timestamp("2021-02-01")
            b=np.flatnonzero(active)[0]
            conditional=stats(e[active],dt[active],initial=float(e[b-1]))
            yearly=byyear(e[active],dt[active],float(e[b-1]))
            rows.append(dict(vintage=i,system=key,input_family="Compact21 BASE xgboost rankpairwise + unchanged frozen MA3 tail",
                   starting_engine="2017 historical full149 single portfolio",
                   risk_impl="original stage19 kernel",**{("full_"+k):v for k,v in full.items()},
                   **{("conditional_2021_"+k):v for k,v in conditional.items()},
                   source_npz_sha256=sh(path)))
            for y,v in yearly.items():annual.append(dict(vintage=i,system=key,year=int(y),return_fraction=v))
            npz.append((key,i,dt,e))
    newraw=pd.read_csv(new/"ORIGINAL_SOURCE_V2_US149_ONE_FREE_UNIVERSE_DAILY_NAV.csv",
            parse_dates=["day"]).set_index("day")
    assert len(newraw)==1360 and newraw.index[0]>=pd.Timestamp("2021-01-01")
    entries={
        "MA3_ORIGINAL_FULL_V2":"fresh_MA3_2021_26_SINGLE149",
        "ADAPT4_FULL_V2":"fresh_ADAPT4_2021_26_SINGLE149"
    }
    for k,model in entries.items():
        nav=newraw[k].to_numpy(float);days=newraw.index
        complete=stats(nav,days,initial=1.)
        rows.append(dict(vintage=0,system=model,input_family="MA3 Hybrid24 source-only annually genuine refitted 2021–2026",
            starting_engine="2021 fresh initial NAV1 and cash/position initialization",
            risk_impl="source v6.simulate_with_alt with highcagr24 apply",
            **{("conditional_2021_"+key):v for key,v in complete.items()},
            source_npz_sha256=sh(new/"ORIGINAL_SOURCE_V2_US149_ONE_FREE_UNIVERSE_DAILY_NAV.csv")))
        for y,v in byyear(nav,days,1.).items():annual.append(dict(vintage=0,system=model,year=int(y),return_fraction=v))
    f=pd.DataFrame(rows);f.to_csv(out/"ORIGINAL31_VS_LATEST10_EXACT_CAGR_AND_SOURCE_IDENTITIES.csv",index=False)
    pd.DataFrame(annual).to_csv(out/"PER_YEAR_CONDITIONAL_OLD_NEW_RECONCILIATION.csv",index=False)
    first=npz[0][2]
    day=newraw.index
    old_on_new=first[first>=pd.Timestamp("2021-02-01")]
    overlap=day.intersection(old_on_new)
    match=dict(old_price_days_since2021=len(old_on_new),new_days_2021to2026=len(day),
          exact_market_dates_old_and_new=day.equals(old_on_new),
          overlapping_common_mark_dates=len(overlap),
          days_only_in_old=[str(v.date()) for v in old_on_new.difference(day)][:200],
          days_only_in_new=[str(v.date()) for v in day.difference(old_on_new)][:200])
    old_mean_full=float(f[f.system=="COMPACT21_BASE"].full_cagr.mean())
    rerank_mean_full=float(f[f.system=="ECON_TOP5_RERANK"].full_cagr.mean())
    old_mean_cond=float(f[f.system=="COMPACT21_BASE"].conditional_2021_cagr.mean())
    new_base=float(f[f.system=="fresh_MA3_2021_26_SINGLE149"].conditional_2021_cagr.iloc[0])
    new_adapt=float(f[f.system=="fresh_ADAPT4_2021_26_SINGLE149"].conditional_2021_cagr.iloc[0])
    assert abs(old_mean_full-0.31758077249027905)<1e-13
    assert abs(rerank_mean_full-0.30957772070033845)<1e-13
    assert abs(new_base-.10479353861045033)<1e-13
    assert abs(new_adapt-.2917477276507473)<1e-13
    summary=dict(status="HISTORICAL_31_76_VS_FREE149_NEW_10_48_SAME_PERIOD_DIFFERENT_PREDICTOR_AUDIT_COMPLETE",
      old_COMPACT21_BASE_2017_2026_mean_cagr=old_mean_full,
      old_COMPACT21_ECON_TOP5_RERANK_2017_2026_mean_cagr=rerank_mean_full,
      old_COMPACT21_BASE_2021_2026_conditional_mean_cagr=old_mean_cond,
      new_fresh_MA3_2021_2026_one149_cagr=new_base,
      new_fresh_ADAPT4_2021_2026_one149_cagr=new_adapt,
      same_ETF_number_149=True,same_one_full_unconstrained_universe=True,
      same_time_window_original_reports=False,
      old_3_quotation_source_vintages_not_500_baskets=True,
      old_compact21_pretrained_score_family_is_not_new_MA3_family=True,
      old_continues_from_2017_new_initializes_from_2021=True,
      different_original_replayer_includes_stage19_confidence_weights_and_simulate_arch=True,
      new_replayer_highcagr24_apply_plus_v6_simulate_with_alt=True,
      original_raw_price_source_not_identical_or_proven_same=True,
      date_alignment=match,
      no_model_training_or_parameter_changes=True,
      detailed_experimental_replay_required_for_exact_algorithm_attribution=True,
      source_old_run=39044619710,
      source_new_run=39338133099,
      old_artifact_SHA256=sh(old/"v2replay-ECON_TOP5_RERANK-r1"/"baseline_control"/"FULL_UNIVERSE_PATH.npz"),
      new_csv_SHA256=sh(new/"ORIGINAL_SOURCE_V2_US149_ONE_FREE_UNIVERSE_DAILY_NAV.csv"))
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(sh(p)+"  "+str(p.relative_to(out))+"\n"
       for p in sorted(out.rglob("*.csv")))+sh(out/"RESULT.json")+"  RESULT.json\n")
    print("FORENSIC_31_76_VS_10_48_DIAGNOSIS",json.dumps(summary),flush=True)
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--historic",required=True);a.add_argument("--new",required=True);a.add_argument("--out",required=True)
    x=a.parse_args();main(x.historic,x.new,x.out)
