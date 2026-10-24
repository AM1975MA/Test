#!/usr/bin/env python3
"""Exact matched Euro48 one-account next-open 10bps Top1 leaf capacity check.

Read 6 annual diagnostics (15/31/63/127 fixed leaves), require original
127 Euro48 economic results and old Compact125 exact CAGR and maxDD parity.
No tuning: this is a single exploratory diagnostic on previously researched
2021–26 months and does not approve any model for production.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from europe_only75.f3h1_original_transfer.run import costed_path
from isin_first2026.predict48.tournament import price_data,monthly_data
BASE=Path("isin_first2026/compact21_base48/results/FITTED_3SEED_ANNUAL")
REPORT=Path("etf-trader-v3 corrected/experiments/europe48_transfer/results/native_alloc_20261024/tables")
ORIGINAL=dict(V2=(.04727914934059951,-.2589315757861944),
              V3_127=(-.0022568935436829696,-.411835572775344),
              V3_127_TREE=(.04705988111123438,-.411835572775344))
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--diagnostics",required=True)
    a.add_argument("--prep",required=True)
    a.add_argument("--out",required=True)
    args=a.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    master,names,op,cl=price_data(args.prep)
    n=list(names)
    _,calendar=monthly_data(master,n,op,cl)
    calendar=calendar[calendar.signal_date.ge(pd.Timestamp("2021-01-01"))].reset_index(drop=True)
    assert len(calendar)==65 and len(n)==48
    old=pd.read_csv(BASE/"BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv",parse_dates=["signal_date"])
    assert len(old)==65*48
    base=old.pivot(index="signal_date",columns="ticker",values="pred").reindex(
             index=calendar.signal_date,columns=n)
    assert base.notna().all().all()
    oldchoice={date:row.idxmax() for date,row in base.iterrows()}
    data=[]
    for year in range(2021,2027):
        path=Path(args.diagnostics)/str(year)/"EUR48_CAPACITY_MONTHLY.csv"
        d=pd.read_csv(path,parse_dates=["signal_date"])
        assert len(d)==4*len(d.signal_date.unique())
        data.append(d)
    d=pd.concat(data,ignore_index=True)
    assert len(d)==65*4 and not d.duplicated(["signal_date","leaf"]).any()
    assert list(sorted(d.signal_date.unique()))==list(calendar.signal_date)
    for dt,group in d.groupby("signal_date"):
        assert group.old_ticker.nunique()==1 and group.old_ticker.iloc[0]==oldchoice[dt]
    # Also independently reconstruct original V3 tree to ensure source
    # cash/money execution against prior successfully published result.
    oldtree=pd.read_csv(REPORT/"EUR48_FULL_UNRESTRICTED_CHOICE_LOG.csv",
                         parse_dates=["signal_date"])
    assert len(oldtree)==65
    treechoice=oldtree.set_index("signal_date").tree_top1.to_dict()
    assert all(d[(d.signal_date.eq(dt))&(d.leaf.eq(127))].ticker.iloc[0]==r.original_top1
               for dt,r in oldtree.set_index("signal_date").iterrows())
    arms={"V2":oldchoice,"V3_127_TREE":treechoice}
    for leaf in (15,31,63,127):
        dd=d[d.leaf.eq(leaf)].set_index("signal_date")
        arms[f"V3_{leaf}"]=dd.ticker.to_dict()
    metrics=[];nav=[];ledger=[];yr=[]
    for tag,selected in arms.items():
        assert len(selected)==65
        allocations=[{selected[date]:1.} for date in calendar.signal_date]
        score,curve,trades=costed_path(allocations,calendar,op,op.index)
        if tag in ORIGINAL:
            cagr,dd=ORIGINAL[tag]
            np.testing.assert_allclose(score["cagr"],cagr,atol=1e-10,rtol=0)
            np.testing.assert_allclose(score["maxdd_daily_open"],dd,atol=1e-10,rtol=0)
        metrics.append(dict(model=tag,**score))
        nav.append(curve.rename(tag))
        ledger.append(trades.assign(model=tag,
            ticker=[selected[date] for date in calendar.signal_date]))
        for year,g in curve.groupby(curve.index.year):
            start=curve[curve.index<g.index[0]]
            baseline=float(start.iloc[-1]) if len(start) else 1.
            yr.append(dict(model=tag,year=int(year),
                   year_return=float(g.iloc[-1]/baseline-1),
                   year_terminal=float(g.iloc[-1])))
        print("EU48_CONTROLLED_LEAF_ECON",tag,
              score["cagr"],score["maxdd_daily_open"],flush=True)
    pd.DataFrame(metrics).to_csv(out/"CAPACITY_REAL_EUR_SCORECARD.csv",index=False)
    pd.concat(nav,axis=1).rename_axis("date").to_csv(out/"CAPACITY_REAL_EUR_DAILY_NAV.csv")
    pd.concat(ledger,ignore_index=True).to_csv(out/"CAPACITY_REAL_EUR_MONTHLY_LEDGER.csv",index=False)
    pd.DataFrame(yr).to_csv(out/"CAPACITY_REAL_EUR_CALENDAR_YEARLY.csv",index=False)
    d.to_csv(out/"CAPACITY_REAL_65_SIGNAL_OOS.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
        same_48_europe_unique_isin=True,same_65_months=True,
        no_meta_policy_except_certified_tree_reference=True,
        EUR_next_open_execution=True,identical_original_costed_path=True,
        original_V2_original_V3_original_tree_parity_1e_10=True,
        n_sessions=1374,one_way_trade_fee=0.001,
        train_first_stage_125features_equal=True,
        reference_first_stage_127_exact_reproduction=True,
        comparison_is_posthoc_explanatory_not_holdout=True,
        model_promotion_authorized=False,production_unchanged=True),indent=2))
    print("EU48_CAPACITY_EXACT_PORTFOLIO_AUDIT_PASS",flush=True)
    print(pd.DataFrame(metrics)[["model","cagr","maxdd_daily_open",
             "sharpe_daily_log","gross_turnover"]].to_string(index=False),flush=True)
if __name__=="__main__":main()
