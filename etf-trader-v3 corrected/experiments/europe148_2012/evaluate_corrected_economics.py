#!/usr/bin/env python3
"""EUR148 real OHLCV next-open economic parity and model skill, no risk overlay.

101 out-of-sample signal months 2018-01..2026-05, dynamic eligible ISIN.
Never select using realized returns. When a vendor bar is absent, last observed
Open is used ONLY to mark existing positions, never to execute trades.
Fees: 0.10% one-way of executed EUR notional; no fee on unchanged holdings.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr

RANKERS=("V2LIKE_DEPTH4","V3_LEAF15","V3_LEAF31","V3_LEAF127")
TOPS=(1,2,3,5)
REF="DE0002635307"

def load_predictions(heads):
    frames=[]
    for year in range(2018,2027):
        p=Path(heads)/str(year)/"YEARLY_EU148_ALL_HEADS.csv"
        assert p.exists(),p
        d=pd.read_csv(p,parse_dates=["signal_date"])
        assert d.signal_date.dt.year.eq(year).all(),p
        frames.append(d)
    q=pd.concat(frames,ignore_index=True)
    assert not q.duplicated(["signal_date","ticker","variant"]).any()
    return q

def nav_sim(q,quotes,cal,rank,n):
    months=sorted(q.signal_date.unique())
    portfolio={}
    target={}
    trades=[]
    for date in months:
        y=q[(q.signal_date.eq(date))&(q.variant.eq(rank))].copy()
        assert len(y)>=24 and y.pred.notna().all(),(rank,date,len(y))
        yy=y.sort_values(["pred","ticker"],ascending=[False,True]).head(n)
        targets={str(t):1.0/len(yy) for t in yy.ticker}
        si=cal.get_loc(date)
        next_date=cal[si+1]
        assert next_date not in target,(next_date,rank)
        target[next_date]=targets
    last_signal=months[-1]
    last_next_signal=cal.to_series().loc[last_signal:].index.to_series().groupby(
        lambda dt:dt.to_period("M")).max()
    following=last_next_signal.index[last_next_signal.index>last_signal.to_period("M")][0]
    end_date=cal[cal.get_loc(last_next_signal[following])+1]
    daily=cal[(cal>=min(target))&(cal<=end_date)]
    mark=quotes.ffill()
    holdings={}
    nav_rows=[]
    fee_total=0.
    turnover_total=0.
    n_stale_marks=0
    for dt in daily:
        price=mark.loc[dt]
        market=quotes.loc[dt]
        for t in holdings:
            if not np.isfinite(price[t]) or price[t]<=0:
                raise RuntimeError(f"missing positive mark {t} {dt}")
            n_stale_marks+=int(not np.isfinite(market[t]))
        old={t:float(u*price[t]) for t,u in holdings.items()}
        pre=float(sum(old.values())) if holdings else 1.0
        if dt in target:
            weights=target[dt]
            for t in set(old)|set(weights):
                if t in weights and (not np.isfinite(market[t]) or market[t]<=0):
                    raise RuntimeError(f"not tradeable at EUR next-open {t} {dt}")
                if t in old and (not np.isfinite(market[t]) or market[t]<=0):
                    raise RuntimeError(f"cannot sell on missing EUR open {t} {dt}")
            after=pre
            for _ in range(18):
                notion=sum(abs(weights.get(t,0.0)*after-old.get(t,0.0))
                           for t in set(weights)|set(old))
                nxt=pre-0.001*notion
                if abs(nxt-after)<1e-14:break
                after=nxt
            assert after>0
            fee=pre-after
            fee_total+=fee
            turnover_total+=notion/pre
            holdings={t:float(w*after/market[t]) for t,w in weights.items()}
            trades.append(dict(date=str(dt.date()),signal_date=str(
                months[list(target).index(dt)].date()),variant=rank,top_n=n,
                positions="|".join(weights),nav_before=pre,nav_after=after,
                euro_fee=fee,turnover=notion/pre))
        wealth=float(sum(holdings[t]*price[t] for t in holdings))
        nav_rows.append((dt,wealth))
    nav=pd.DataFrame(nav_rows,columns=["date","nav"])
    assert nav.nav.notna().all() and (nav.nav>0).all()
    # Initial wealth=1 before first purchase; final NAV after final observed exit Open.
    last=float(nav.nav.iloc[-1]);span=(daily[-1]-daily[0]).days/365.25
    logrets=np.log(nav.nav).diff().dropna()
    score=dict(variant=rank,top_n=n,months=len(months),
        start=str(daily[0].date()),end=str(daily[-1].date()),
        n_daily=len(daily),cagr=(last**(1/span)-1),
        max_dd=float((nav.nav/nav.nav.cummax()-1).min()),
        sharpe_log=float(np.sqrt(252)*logrets.mean()/logrets.std(ddof=1)),
        terminal_nav=last,
        total_fees_eur_unit=fee_total,turnover_oneway_sum=turnover_total,
        n_stale_valuation_marks=n_stale_marks)
    nav["variant"]=rank;nav["top_n"]=n
    return score,nav,pd.DataFrame(trades)

def skill(q):
    rows=[];choices=[]
    for variant in RANKERS:
        for date,g in q[q.variant.eq(variant)].groupby("signal_date"):
            g=g.dropna(subset=["fwd_ret_21"]).copy()
            assert len(g)>=24
            s=g.sort_values(["pred","ticker"],ascending=[False,True])
            best=s.iloc[0]
            chosen3=set(s.head(3).ticker)
            winner=g.loc[g.fwd_ret_21.idxmax()]
            actual=float(best.fwd_ret_21)
            choices.append(dict(variant=variant,signal_date=str(date.date()),
                 n_eligible=len(g),top1_ticker=best.ticker,
                 winner_ticker=winner.ticker,
                 actual_forward21=actual,
                 mean_forward21=float(g.fwd_ret_21.mean()),
                 selected_excess_21d=actual-float(g.fwd_ret_21.mean()),
                 top1_hit=int(best.ticker==winner.ticker),
                 top3_hit=int(winner.ticker in chosen3),
                 spearman=float(spearmanr(g.pred,g.fwd_ret_21).statistic)))
        c=pd.DataFrame([e for e in choices if e["variant"]==variant])
        rows.append(dict(variant=variant,months=len(c),n_eligible_min=int(c.n_eligible.min()),
          n_eligible_median=float(c.n_eligible.median()),
          winner_top1_count=int(c.top1_hit.sum()),winner_top3_count=int(c.top3_hit.sum()),
          selected_excess_21d_mean=float(c.selected_excess_21d.mean()),
          spearman_mean=float(c.spearman.mean()),
          forward_loss_10pct_count=int((c.actual_forward21<=-0.10).sum())))
    return pd.DataFrame(rows),pd.DataFrame(choices)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--heads",required=True)
    p.add_argument("--raw",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    q=load_predictions(a.heads)
    q=q[q.variant.isin(RANKERS)].copy()
    dates=sorted(q.signal_date.unique())
    assert len(dates)==101 and str(dates[0].date())=="2018-01-31"
    assert str(dates[-1].date())=="2026-05-29"
    counts=q[q.variant.eq(RANKERS[0])].groupby("signal_date").ticker.nunique()
    assert counts.loc[pd.Timestamp("2026-03-31")]>=140
    assert counts.loc[pd.Timestamp("2026-04-30")]>=140
    assert counts.loc[pd.Timestamp("2026-05-29")]>=140
    assert q.groupby("variant").signal_date.nunique().eq(101).all()
    assert q.variant.nunique()==4
    cat=pd.read_csv(Path(a.raw)/"EU148_VERIFIED_LEGAL_ISIN_CATALOG.csv")
    quotes={}
    for isin in cat.ticker:
        d=pd.read_csv(Path(a.raw)/"raw_ticker_csv"/(isin+".csv"),parse_dates=["date"])
        quotes[isin]=d.set_index("date").Open
    O=pd.concat(quotes,axis=1).sort_index()
    cal=O[REF].dropna().index
    O=O.reindex(cal)
    sc=[];navs=[];ledgers=[]
    for v in RANKERS:
        for n in TOPS:
            a1,nv,l=nav_sim(q,O,cal,v,n)
            print("EURA148_REAL_NAV",json.dumps(a1),flush=True)
            sc.append(a1);navs.append(nv);ledgers.append(l)
    score=pd.DataFrame(sc)
    score.to_csv(out/"EUR148_REAL_ECONOMIC_SCORECARD.csv",index=False)
    pd.concat(navs,ignore_index=True).to_csv(out/"EUR148_DAILY_NAV.csv",index=False)
    pd.concat(ledgers,ignore_index=True).to_csv(out/"EUR148_MONTHLY_TRADES.csv",index=False)
    skills,choices=skill(q)
    skills.to_csv(out/"EUR148_RANKER_SKILL.csv",index=False)
    choices.to_csv(out/"EUR148_MONTHLY_PICKS.csv",index=False)
    counts.rename("n_eligible").to_csv(out/"EUR148_ASOF_ELIGIBLE_COUNTS.csv")
    (out/"MANIFEST.json").write_text(json.dumps(dict(
      n_source_legal_isins=len(cat),n_signal_months=len(dates),
      models=list(RANKERS),top_n=list(TOPS),
      native_eur_open_execution=True,one_way_fee_bps=10,
      no_use_of_future_labels_for_selection=True,
      only_one_stale_date_in_feature_kernel="2026-03-06",
      execution_marks_only_forward_filled_not_executable_quotes=True,
      stage19_and_meta_tree_not_tested=True,
      101_month_window_research_not_independent_holdout=True,
      original_production_unmodified=True),indent=2))
    print("EURA148_101_MONTH_OOS_SCORECARD_PASS",score.to_string(index=False),flush=True)
    print("EURA148_101_MONTH_OOS_SKILL_PASS",skills.to_string(index=False),flush=True)

if __name__=="__main__":main()
