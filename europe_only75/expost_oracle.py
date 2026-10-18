#!/usr/bin/env python3
"""Perfect-hindsight bounds on frozen Europe-only EUR60 monthly ETF selection.

Research-only cheating oracle, zero model fitting. Same real entry/exit common
EU+US market opens and 10bp turnover fee as registered simple-50/50 comparator.
"""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"europe120/eu120_retrain"),
              str(ROOT/"vendor/etf_trader_v2/src")]
import replay_audited as au
import run_eu120_retrain as eu
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from eu120_compact_return_tail_v1.run import calculate_scores,fixed_5050_common_open
from paper_ltr_v2.replay import sha

FEE=0.001
def compounding(rows,policy):
    eq=1.;prev={};gross=[];turns=[]
    for picks,ratios in rows:
        w={str(p):1./len(picks) for p in picks}
        turnover=.5*sum(abs(w.get(x,0)-prev.get(x,0)) for x in set(w)|set(prev))
        ratio=float(np.mean(ratios))
        if not np.isfinite(ratio) or ratio<=0:raise ValueError("Invalid realized ETF return")
        eq*=ratio*(1-FEE*turnover)
        gross.append(ratio-1);turns.append(turnover)
        prev=w
    return dict(policy=policy,months=len(rows),terminal_equity=float(eq),
                cagr=float(eq**(12/len(rows))-1),mean_monthly_gross_return=float(np.mean(gross)),
                mean_monthly_turnover=float(np.mean(turns)))

def main():
    p=argparse.ArgumentParser()
    for name in ("refit","raw149","out"):p.add_argument("--"+name,required=True)
    args=p.parse_args()
    refit=Path(args.refit).resolve();out=Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError("Refusing to overwrite oracle output")
    out.mkdir(parents=True)
    source=json.loads((refit/"RESULT.json").read_text())
    if (source["universe_count"]!=60 or source["completed_months"]!=113
        or source["status"]!="EU120_REFITTED_5_POLICY_COMMON_OPEN_COMPLETE"
        or not source["training_guard_ALL_PASS"] or
        source["source_europe_only_whitelist_sha256"]!=sha(ROOT/"europe_only75/UNIVERSE_EUROPE_ONLY.csv")):
        raise ValueError("EUR60 source fits not certified")
    manifest=json.loads((ROOT/"europe_only75/MANIFEST.json").read_text())
    names=pd.read_csv(ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv")
    tickers=names.ticker.astype(str).tolist()
    if len(tickers)!=60 or len(set(tickers))!=60:
        raise ValueError("Different frozen Europe-only cohort")
    frozen=ROOT/"data/eu120"
    if manifest["source_eu120_manifest_sha256"]!=sha(frozen/"manifest.json"):
        raise ValueError("Original market source hash changed")
    import shutil
    raw=out/"raw60";raw.mkdir()
    names.to_csv(raw/"universe.csv",index=False)
    for ticker in tickers:shutil.copyfile(frozen/"raw_ticker_csv"/(ticker+".csv"),raw/(ticker+".csv"))
    refs=out/"references"
    os.environ["FROZEN_149_ROOT"]=str(Path(args.raw149).resolve())
    eu.download_folder(pd.DataFrame(dict(ticker=eu.REF_TICKERS,
         macro_category=["REF_US","REF_CREDIT","REF_BOND","REF_CASH","REF_CASH"])),refs)
    cm,_,_=load_ticker_csv_folder(raw);rm,_,_=load_ticker_csv_folder(refs)
    op=cm["Open"].reindex(columns=tickers)
    cp=pd.read_parquet(refit/"COMPACT_REFITTED.parquet")
    hp=pd.read_parquet(refit/"HYBRID_REFITTED.parquet")
    for frame in (cp,hp):frame["signal_date"]=pd.to_datetime(frame.signal_date)
    days=pd.DatetimeIndex(sorted(set(cp.signal_date)&set(hp.signal_date)))
    cal=au.common_calendar(pd.concat([op,rm["Open"].reindex(columns=eu.REF_TICKERS)],axis=1).sort_index(),days)
    if len(cal)!=113:raise ValueError("EUR60 original common-open month count changed")
    cp=cp[cp.signal_date.isin(cal.signal_date)].copy()
    hp=hp[hp.signal_date.isin(cal.signal_date)].copy()
    scores,_=calculate_scores(cp,hp,cal,tickers)
    official={str(x["variant"]):x for x in source["fixed_5050"]}
    for model in ("B_ONLY","R_ONLY","H_ONLY","B_H","R_H"):
        actual=fixed_5050_common_open(scores[model],cal,tickers,op)
        if abs(actual["cagr"]-float(official[model]["cagr"]))>1e-12:
            raise ValueError("Unable to replicate prior registered 50/50 model benchmark "+model)
    policies=("MODEL_R_H_TOP1","ORACLE_ELIGIBLE_TOP1","ORACLE_ELIGIBLE_TOP2","ORACLE_ALL_TRADABLE_TOP1",
              "ORACLE_ALL_TRADABLE_TOP2","ORACLE_TOP_DECILE")
    bets={x:[] for x in policies}
    quality=[]
    for month,row in enumerate(cal.itertuples(index=False)):
        sd=pd.Timestamp(row.signal_date);entry=pd.Timestamp(row.entry_date);end=pd.Timestamp(row.exit_date)
        if entry not in op.index or end not in op.index or not (sd<entry<end):
            raise ValueError("Non-tradable original monthly as-of date")
        pe=op.loc[entry].to_numpy(float);px=op.loc[end].to_numpy(float)
        valid=np.isfinite(pe)&np.isfinite(px)&(pe>0)&(px>0)
        ratio=np.divide(px,pe,out=np.full(60,np.nan),where=valid)
        score=scores["R_H"][month]
        eligible=valid&np.isfinite(score)
        if valid.sum()<20 or eligible.sum()<5:
            raise ValueError("Insufficient originally tradable or as-of model-score names")
        # No future data in candidate universe; oracle uses future ratios solely
        # for its forbidden perfect-foresight selection decision.
        choose_model=np.argsort(-np.where(np.isfinite(score),score,-1e30),kind="stable")
        model_top1=int(choose_model[0])
        if not eligible[model_top1]:raise ValueError("Model chose unobserved ETF")
        elig_sorted=np.lexsort((np.arange(60),-np.where(eligible,ratio,-np.inf)))
        all_sorted=np.lexsort((np.arange(60),-np.where(valid,ratio,-np.inf)))
        # lexsort keys: -ratio primary, ticker index secondary, deterministic.
        winners={
            "MODEL_R_H_TOP1":[model_top1],
            "ORACLE_ELIGIBLE_TOP1":elig_sorted[:1].tolist(),
            "ORACLE_ELIGIBLE_TOP2":elig_sorted[:2].tolist(),
            "ORACLE_ALL_TRADABLE_TOP1":all_sorted[:1].tolist(),
            "ORACLE_ALL_TRADABLE_TOP2":all_sorted[:2].tolist(),
            "ORACLE_TOP_DECILE":all_sorted[:max(1,int(np.ceil(valid.sum()/10)))].tolist(),
        }
        for pol,ix in winners.items():
            if not all(valid[i] for i in ix):raise ValueError("Perfect-foresight selected an unobserved open")
            bets[pol].append(([tickers[i] for i in ix],ratio[ix].copy()))
        best_all=int(all_sorted[0]);best_el=int(elig_sorted[0])
        quality.append(dict(signal_date=str(sd.date()),entry_date=str(entry.date()),exit_date=str(end.date()),
            all_tradable=int(valid.sum()),eligible_for_R_H=int(eligible.sum()),
            model_first=tickers[model_top1],model_first_return=float(ratio[model_top1]-1),
            best_model_eligible_expost=tickers[best_el],best_model_eligible_return=float(ratio[best_el]-1),
            best_all_expost=tickers[best_all],best_all_return=float(ratio[best_all]-1),
            signed_model_regret_eligible=float(ratio[best_el]-ratio[model_top1]),
            signed_model_regret_all=float(ratio[best_all]-ratio[model_top1])))
    results=[compounding(bets[x],x) for x in policies]
    model_5050=float(official["R_H"]["cagr"])
    if abs(model_5050-.09978)>0.1: # independent replay used to check known historical range
        raise ValueError("Implausible reconstructed registered R+H simple portfolio")
    first=pd.Timestamp(cal.entry_date.min());last=pd.Timestamp(cal.exit_date.max())
    if last<=first:raise ValueError("Invalid fixed holding horizon")
    fixed_buy=op.loc[first].to_numpy(float);fixed_sell=op.loc[last].to_numpy(float)
    buyvalid=np.isfinite(fixed_buy)&np.isfinite(fixed_sell)&(fixed_buy>0)&(fixed_sell>0)
    ratios=np.divide(fixed_sell,fixed_buy,out=np.full(60,np.nan),where=buyvalid)
    if buyvalid.sum()<10:raise ValueError("Too few ETFs continuously observed at both ends")
    best_fixed_idx=int(np.nanargmax(ratios))
    annuals=pd.read_csv(refit/"ANNUAL_RETURN.csv")
    pd.DataFrame(quality).to_csv(out/"MONTHLY_ORACLE_113.csv",index=False)
    pd.DataFrame(results).to_csv(out/"ORACLE_COMPARISON.csv",index=False)
    report=dict(status="EUROPE_ONLY_EUR60_113_MONTH_EXPOST_ORACLE_CERTIFIED",
        compared_months=len(cal),candidates=60,source_refit_run=39071370480,
        model_annual_fits_no_new_fits=80,match_registered_R_H_fixed_5050=True,
        prior_registered_R_H_fixed_5050_cagr=float(model_5050),
        risk_managed_R_H_cagr=float(next(x["cagr"] for x in source["economics"] if x["variant"]=="R_H")),
        oracle_monthly_scenario_comparisons=results,
        best_single_ticker_full_period=dict(ticker=tickers[best_fixed_idx],
             ratio=float(ratios[best_fixed_idx]),
             cagr=float(ratios[best_fixed_idx]**(365.25/(last-first).days)-1),
             first_entry=str(first.date()),last_exit=str(last.date()),
             observed_fixed_candidates=int(buyvalid.sum())),
        mean_monthly_model_regret_vs_best_eligible=float(pd.DataFrame(quality).signed_model_regret_eligible.mean()),
        mean_monthly_model_regret_vs_best_all=float(pd.DataFrame(quality).signed_model_regret_all.mean()),
        oracle_uses_expost_returns_to_choose_ETFs=True,
        future_investable=False,expost_universe_membership_bias=True,
        compare_oracle_only_to_same_simple_fixed_5050_execution_not_risk_managed=True,
        source_frozen_manifest_sha256=sha(frozen/"manifest.json"),
        source_60_EUR_names_sha256=sha(ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv"))
    (out/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("EUROPE_EUR60_EXPOST_ORACLE "+json.dumps(report,allow_nan=False),flush=True)

if __name__=="__main__":main()
