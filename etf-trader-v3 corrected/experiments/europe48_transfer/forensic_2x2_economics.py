#!/usr/bin/env python3
"""Compare exact 65-month EU48 one-account EUR next-open net Top1 equity.

2x2 reference parity: legacy 125F maxdepth4, 127leaf legacy, and ACTUAL V3
corrected risk features each at maxdepth4 / 127 leaves. No model tuning,
no alternative future selection, one single EUR portfolio monthly, 10bps.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from isin_first2026.predict48.tournament import price_data,monthly_data
from europe_only75.f3h1_original_transfer.run import costed_path

NAMES=("LEGACY_SHALLOW","LEGACY_DEEP","CORRECTED_SHALLOW","CORRECTED_DEEP")
BENCH={
 "LEGACY_SHALLOW":dict(cagr=.04727914934059951,maxdd_daily_open=-.2589315757861944),
 "LEGACY_DEEP":dict(cagr=-.0022568935436829696,maxdd_daily_open=-.411835572775344)
}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--prep",required=True)
    ap.add_argument("--year-results",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    roster,names,O,C=price_data(a.prep)
    m,cal=monthly_data(roster,names,O,C)
    cal=cal[cal.signal_date>=pd.Timestamp("2021-01-01")].reset_index(drop=True)
    assert len(cal)==65 and len(names)==48
    permonth=[]
    for year in range(2021,2027):
        folder=Path(a.year_results)/str(year)
        f=folder/f"EU48_{year}_MONTHLY_CHOICE_AND_LABEL.csv"
        t=pd.read_csv(f,parse_dates=["signal_date"])
        assert set(t.variant)==set(NAMES),year
        assert t.groupby("variant").size().eq(5 if year==2026 else 12).all()
        permonth.append(t)
    panel=pd.concat(permonth,ignore_index=True).sort_values(["signal_date","variant"]).reset_index(drop=True)
    assert panel.groupby("variant").size().eq(65).all()
    assert panel.signal_date.isin(cal.signal_date).all()
    caldate=list(cal.signal_date)
    data={name:panel[panel.variant.eq(name)].set_index("signal_date").reindex(caldate)
          for name in NAMES}
    for name,z in data.items():
        assert z.selected.notna().all() and z.selected.isin(names).all()
        assert np.isfinite(z.selected_excess.to_numpy(float)).all()
    stats=[];curves=[];trades=[]
    for name,choice in data.items():
        weights=[{x:1.0} for x in choice.selected]
        m,nav,ledger=costed_path(weights,cal,O,O.index)
        if name in BENCH:
            for metric,expected in BENCH[name].items():
                np.testing.assert_allclose(float(m[metric]),expected,rtol=0,atol=5e-11,
                    err_msg=f"ORIGINAL one account benchmark parity failure: {name} {metric}")
        stats.append(dict(variant=name,**m,
            mean_selected_excess_21d=float(choice.selected_excess.mean()),
            top1_winner_hits=int(choice.hit_absolute_winner.sum())))
        curves.append(nav.rename(name))
        trades.append(ledger.assign(variant=name))
        print("EUROPE48_TRUE_EUR10BPS_ABLATION",name,m["cagr"],m["maxdd_daily_open"],flush=True)
    economics=pd.DataFrame(stats).set_index("variant")
    equity=pd.concat(curves,axis=1)
    assert equity.shape==(1374,4) and equity.notna().all(axis=None)
    comparison=[]
    for challenger in NAMES[1:]:
        base=equity.LEGACY_SHALLOW.to_numpy(float)
        alt=equity[challenger].to_numpy(float)
        differences=np.diff(np.log(np.r_[1.,alt]))-np.diff(np.log(np.r_[1.,base]))
        B=3000;n=len(differences);block=21;rng=np.random.default_rng(20261024)
        indices=((rng.integers(0,n,size=(B,(n+block-1)//block))[:,:,None]+
                  np.arange(block))%n).reshape(B,-1)[:,:n]
        bt=differences[indices].mean(axis=1)*252
        comparison.append(dict(variant=challenger,benchmark="LEGACY_SHALLOW",
           annual_log_alpha=float(differences.mean()*252),
           alpha_ci_low95=float(np.quantile(bt,.025)),
           alpha_ci_high95=float(np.quantile(bt,.975)),
           n_trading_days=n,block_days=block))
    economics.to_csv(out/"EU48_2X2_NET_TOP1_SCORECARD.csv")
    equity.rename_axis("date").to_csv(out/"EU48_2X2_DAILY_EUR_NET_NAV.csv")
    panel.to_csv(out/"EU48_2X2_MONTHLY_SIGNALS_RETURNS.csv",index=False)
    pd.DataFrame(trades and pd.concat(trades,ignore_index=True)).to_csv(out/"EU48_2X2_EXECUTION_LEDGER.csv",index=False)
    pd.DataFrame(comparison).to_csv(out/"EU48_2X2_PAIRED_BLOCK_CI.csv",index=False)
    annual=[]
    for name in NAMES:
        path=equity[name]
        previous=1.
        for year,g in path.groupby(path.index.year):
            cap=float(g.iloc[-1])
            annual.append(dict(variant=name,year=int(year),period_return=float(cap/previous-1)))
            previous=cap
    pd.DataFrame(annual).to_csv(out/"EU48_2X2_CALENDAR_YEAR.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
      original_ref_source_run=40086216896,
      ablation_fit_run="workflow specified in run",
      original_europe_V2_125F_exact_parity=True,
      original_europe_V3_127leaf_exact_parity=True,
      full_65_months=True,months_start="2021-01-29",months_end="2026-05-29",
      source_only_same_EUR48_open=True,basket_only_models_no_overlay=True,
      cost_bps_one_way=10,
      no_meta_tree_retraining_in_2x2_control=True,
      first_stage_hyperparams_precommitted=True,
      calendar_already_researched=True,not_independent_holdout=True,
      no_production_modifications=True),indent=2))
    print("EU48_TWO_BY_TWO_ECONOMIC_SUCCESS",flush=True)
    print(economics.to_string(),flush=True)
    print(pd.DataFrame(comparison).to_string(index=False),flush=True)
if __name__=="__main__":main()
