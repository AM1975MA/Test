#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, platform, time
from pathlib import Path

import numpy as np
import pandas as pd

from etf_trader.source_only import kernel as k
from etf_trader.source_only.features import build as build_extra_features
from etf_trader.source_only.models import fit_predict, variants
from etf_trader.source_only.execution import replay
from etf_trader.source_only.statistics import metrics, paired_bootstrap, holm, subpath
from etf_trader.source_only.dispersion_allocation import allocation_tables
from etf_trader.source_only.category_overlay import allocation_table as category_allocation
from etf_trader.source_only.raw_io import load_ticker_csv_folder, load_baskets

PERIODS={
    "development":("2017-02-01","2021-12-31"),
    "validation":("2022-01-01","2023-12-31"),
    "confirmation_retrospective":("2024-01-01","2026-07-01"),
    "full":("2017-02-01","2026-07-01"),
}

def mask_for(dates,lo,hi):
    return np.asarray((dates>=pd.Timestamp(lo))&(dates<=pd.Timestamp(hi)))

def eval_path(name,dates,e,turn):
    rows=[]
    for period,(lo,hi) in PERIODS.items():
        m=mask_for(dates,lo,hi)
        if m.sum()<2: continue
        x=metrics(subpath(e,m),turn[:,m] if turn is not None else None)
        rows.append({"variant":name,"period":period,**x})
    for year in sorted(set(dates.year)):
        m=np.asarray(dates.year==year)
        if m.sum()<2: continue
        x=metrics(subpath(e,m),turn[:,m] if turn is not None else None)
        rows.append({"variant":name,"period":str(year),**x})
    return rows

def compare_pair(base_dates,base_e,dates,e,period):
    if not dates.equals(base_dates): raise ValueError("calendar mismatch")
    lo,hi=PERIODS[period];m=mask_for(dates,lo,hi)
    b=subpath(base_e,m);o=subpath(e,m)
    return {str(block):paired_bootstrap(b,o,block=block,reps=2000) for block in (21,63)}

def pick_validation_winner(score,family_names,baseline_name):
    v=score[(score.period=="validation")&score.variant.isin(family_names)].copy()
    base=v[v.variant==baseline_name].iloc[0]
    # Primary objective CAGR; guardrail against materially worse drawdown/Sharpe.
    eligible=v[(v.mean_maxdd>=base.mean_maxdd-.01)&(v.mean_sharpe_rf0>=base.mean_sharpe_rf0-.02)]
    if eligible.empty:
        return baseline_name
    return str(eligible.sort_values(["mean_cagr","mean_sharpe_rf0"],ascending=False).iloc[0].variant)

def family_stats(family,variants_,paths,base_name):
    out={}
    base_dates,base_e,_=paths[base_name]
    for name in variants_:
        if name==base_name: continue
        dates,e,_=paths[name]
        out[name]={p:compare_pair(base_dates,base_e,dates,e,p) for p in ("validation","confirmation_retrospective","full")}
    for p in ("validation","confirmation_retrospective","full"):
        for block in ("21","63"):
            raw={name:out[name][p][block]["p_one_sided_centered"] for name in out}
            adj=holm(raw) if raw else {}
            for name,val in adj.items(): out[name][p][block]["p_holm_family"]=val
    return {"family":family,"baseline":base_name,"comparisons":out}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",required=True,help="folder with universe.csv and one OHLCV CSV per ticker")
    ap.add_argument("--baskets",default="data/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    ap.add_argument("--output",default="runs/source_only_campaign")
    a=ap.parse_args()
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True);t0=time.time()

    mats,cats,data_manifest=load_ticker_csv_folder(a.data)
    cols=list(mats["Close"].columns)
    baskets=load_baskets(a.baskets,cols)
    if len(baskets)!=500: raise ValueError(f"expected 500 baskets, got {len(baskets)}")

    # Configure recovered architecture only from source/static metadata.
    k.ALL_TICKERS=sorted(cols)
    k.TICKER_CATEGORY=cats
    k.CATEGORY_TICKERS={c:sorted([t for t in cols if cats[t]==c]) for c in sorted(set(cats.values()))}

    dates=k.month_end_dates(mats["Close"].index)
    if len(dates) and dates[-1]==mats["Close"].index[-1]:
        dates=dates[:-1]  # last row alone does not prove a completed month

    _,compact,tail,_=k.build_features(mats)
    compact=compact[compact.signal_date.isin(dates)]
    tail=tail[tail.signal_date.isin(dates)]
    compact=k.add_labels(compact,mats["Open"],dates)
    tail=k.add_labels(tail,mats["Open"],dates)
    tail_no_labels=tail.drop(columns=[c for c in tail if c.startswith(("fwd_","target_","exit_")) or c in ["entry_date","y_tailmix"]])
    macro,mfeatures=k.build_macro_panel(tail_no_labels,tail)
    extra=build_extra_features(mats,cats,dates)

    pred=fit_predict(k,compact,tail,macro,mfeatures,extra,out/"annual_models")
    pred=pred[(pred.signal_date>="2017-01-31")&(pred.signal_date<="2026-06-30")]
    alpha_panels=variants(pred)

    manifest={
      "status":"SOURCE_ONLY_RAW_CSV_RECALCULATION",
      "data":data_manifest,
      "baskets":len(baskets),
      "basket_size":len(baskets[0]),
      "productive_inputs":["ticker OHLCV CSV","universe.csv","basket membership CSV","source code"],
      "forbidden_inputs_used":False,
      "historical_score_panel_used":False,
      "precomputed_gate_used":False,
      "precomputed_path_used":False,
      "python":platform.python_version(),
    }
    (out/"MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")

    paths={};score_rows=[]

    # Stage A: alpha/ranking families.
    alpha_names=[]
    for name,panel in alpha_panels.items():
        ds,e,t=replay(panel,mats,baskets)
        paths[f"alpha::{name}"]=(ds,e,t);alpha_names.append(f"alpha::{name}")
        np.savez_compressed(out/f"alpha_{name}.npz",dates=ds.values,equity=e,turnover=t)
        score_rows+=eval_path(f"alpha::{name}",ds,e,t)
    score=pd.DataFrame(score_rows)
    alpha_base="alpha::baseline"
    alpha_winner=pick_validation_winner(score,alpha_names,alpha_base)
    alpha_stats=family_stats("alpha",alpha_names,paths,alpha_base)

    # Reconstruct selected alpha panel without reading confirmation for selection.
    selected_alpha_key=alpha_winner.split("::",1)[1]
    selected_panel=alpha_panels[selected_alpha_key]
    base_dates,base_e,base_t=paths[alpha_winner]

    # Stage B1: source-only CVX/category overlays on frozen alpha winner.
    overlay_names=[alpha_winner]
    for mode in ("cvx70_top3","cvx25_top5","concentration_lock","confidence_switch"):
        table,state=category_allocation(selected_panel,baskets,mats["Open"].index,cols,cats,mode=mode)
        ds,e,t=replay(selected_panel,mats,baskets,allocation_override=table)
        name=f"overlay::{mode}"
        paths[name]=(ds,e,t);overlay_names.append(name)
        table.to_csv(out/f"{mode}_allocations.csv",index=False)
        state.to_csv(out/f"{mode}_category_state.csv",index=False)
        score_rows+=eval_path(name,ds,e,t)

    # Stage B2: source-only concentration rules on same frozen alpha winner.
    sizing_tables,sizing_diag=allocation_tables(selected_panel,baskets,mats["Open"].index,cols)
    sizing_diag.to_csv(out/"sizing_diagnostics.csv",index=False)
    for mode,table in sizing_tables.items():
        ds,e,t=replay(selected_panel,mats,baskets,allocation_override=table)
        name=f"sizing::{mode}"
        paths[name]=(ds,e,t);overlay_names.append(name)
        table.to_csv(out/f"sizing_{mode}_allocations.csv",index=False)
        score_rows+=eval_path(name,ds,e,t)

    score=pd.DataFrame(score_rows)
    overlay_winner=pick_validation_winner(score,overlay_names,alpha_winner)
    overlay_stats=family_stats("overlay_and_sizing",overlay_names,paths,alpha_winner)

    # Stage C: risk layer only on winner frozen from Stage B validation.
    risk_names=[overlay_winner]
    # simple lagged source-only distress controller, deliberately uses prior-close information only
    if overlay_winner.startswith("overlay::"):
        mode=overlay_winner.split("::",1)[1]
        table,_=category_allocation(selected_panel,baskets,mats["Open"].index,cols,cats,mode=mode)
        ds,e,t=replay(selected_panel,mats,baskets,allocation_override=table,risk=True)
    elif overlay_winner.startswith("sizing::"):
        mode=overlay_winner.split("::",1)[1]
        table=sizing_tables[mode]
        ds,e,t=replay(selected_panel,mats,baskets,allocation_override=table,risk=True)
    else:
        ds,e,t=replay(selected_panel,mats,baskets,risk=True)
    risk_name="risk::lagged_distress"
    paths[risk_name]=(ds,e,t);risk_names.append(risk_name)
    score_rows+=eval_path(risk_name,ds,e,t)
    score=pd.DataFrame(score_rows)
    risk_winner=pick_validation_winner(score,risk_names,overlay_winner)
    risk_stats=family_stats("risk",risk_names,paths,overlay_winner)

    # Freeze final candidate now; only after this is confirmation interpreted.
    final_name=risk_winner
    final_dates,final_e,final_t=paths[final_name]

    # Cost stress on final decision logic, not used for selection.
    cost_rows=[]
    if final_name=="risk::lagged_distress":
        risk_flag=True
        chosen_alloc=None
        if overlay_winner.startswith("overlay::"):
            chosen_alloc=category_allocation(selected_panel,baskets,mats["Open"].index,cols,cats,
                                             mode=overlay_winner.split("::",1)[1])[0]
        elif overlay_winner.startswith("sizing::"):
            chosen_alloc=sizing_tables[overlay_winner.split("::",1)[1]]
    else:
        risk_flag=False;chosen_alloc=None
        if final_name.startswith("overlay::"):
            chosen_alloc=category_allocation(selected_panel,baskets,mats["Open"].index,cols,cats,
                                             mode=final_name.split("::",1)[1])[0]
        elif final_name.startswith("sizing::"):
            chosen_alloc=sizing_tables[final_name.split("::",1)[1]]
    for cost in (.002,.003):
        ds,e,t=replay(selected_panel,mats,baskets,cost=cost,risk=risk_flag,allocation_override=chosen_alloc)
        for period,(lo,hi) in PERIODS.items():
            m=mask_for(ds,lo,hi)
            if m.sum()>1: cost_rows.append({"cost":cost,"period":period,**metrics(subpath(e,m),t[:,m])})
    pd.DataFrame(cost_rows).to_csv(out/"FINAL_COST_STRESS.csv",index=False)

    score=pd.DataFrame(score_rows)
    score.to_csv(out/"SCORECARD.csv",index=False)
    stats_package={"alpha":alpha_stats,"overlay_and_sizing":overlay_stats,"risk":risk_stats}
    (out/"BOOTSTRAP_FAMILY_TESTS.json").write_text(json.dumps(stats_package,indent=2)+"\n")

    val=score[score.period.eq("validation")].set_index("variant")
    conf=score[score.period.eq("confirmation_retrospective")].set_index("variant")
    baseline=alpha_base
    final_report={
      "status":"SOURCE_ONLY_CAMPAIGN_COMPLETE",
      "alpha_winner_validation_only":alpha_winner,
      "overlay_winner_validation_only":overlay_winner,
      "final_winner_validation_only":final_name,
      "baseline_full":score[(score.variant==baseline)&(score.period=="full")].iloc[0].to_dict(),
      "final_full":score[(score.variant==final_name)&(score.period=="full")].iloc[0].to_dict(),
      "final_validation":val.loc[final_name].to_dict(),
      "final_confirmation_retrospective":conf.loc[final_name].to_dict(),
      "confirmation_used_for_selection":False,
      "elapsed_seconds":time.time()-t0,
    }
    (out/"RESULT.json").write_text(json.dumps(final_report,indent=2,default=float)+"\n")
    print(json.dumps(final_report,indent=2,default=float))

if __name__=="__main__":
    main()
