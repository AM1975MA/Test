#!/usr/bin/env python3
"""Prespecified native V3 USA149/EU148 *non-ML* opportunity/control audit.

Do not call these strategies the V3 ML ranker. This is the first controlled
market-vs-model diagnostic: 101 exactly matched as-of dates, next joint
executable trading-day Open, 10bp each side, one real account, native EUR
marks (USD shares / as-of previous US close EURUSD), original 149 US history
and fixed EU148 corporate-action-corrected raw source.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
SEEDS=(21,63,126,252)
TOPS=(1,3,5)
REF_U="SPY"; REF_E="DE0002635307"
START="2018-01-01"; LAST_SIGNAL="2026-05-31"; END="2026-07-01"
FEE=.001

def load_raw(folder,roster,market):
    data={}
    for tick in roster.ticker:
        f=Path(folder)/(tick+".csv")
        assert f.is_file(),f
        d=pd.read_csv(f,parse_dates=["date"]).drop_duplicates("date",keep="last")
        d=d.set_index("date").sort_index()
        assert len(d)>300 and (d.Close>0).all(),(tick,len(d))
        data[tick]=d
    op=pd.concat({k:v.Open for k,v in data.items()},axis=1)
    cl=pd.concat({k:v.Close for k,v in data.items()},axis=1)
    vol=pd.concat({k:v.Volume for k,v in data.items()},axis=1)
    assert op.columns.nunique()==len(roster)==cl.columns.nunique()
    print("DATA_VALID",market,len(roster),op.index.min(),op.index.max(),flush=True)
    return op,cl,vol

def factors(c,calendar):
    # Quoted prices only on common calendar. Single missing date allowed ONLY
    # in causal features, never in actual executions or trades.
    observed=c.notna()
    tmp=c.ffill(limit=1)
    warm=observed.cumsum().reindex(calendar)
    valid=observed.reindex(calendar).fillna(False)&warm.ge(252)
    ret={w:(tmp/tmp.shift(w)-1).reindex(calendar).where(valid) for w in SEEDS}
    return ret,valid

def compute_nav(open_px,volume,signals,picks,cal,dates,market,segment,variant,topn):
    idx=pd.DatetimeIndex(cal)
    tdates=sorted(dates)
    execs=[idx[idx.searchsorted(pd.Timestamp(m),side="right")] for m in tdates]
    first=execs[0]
    # Strict terminal mark: first joint trade day on or after July 1, 2026
    terminal=idx[idx.searchsorted(pd.Timestamp(END))]
    exec_map={d:tdates[i] for i,d in enumerate(execs)}
    daily=idx[(idx>=first)&(idx<=terminal)]
    marks=open_px.reindex(daily).ffill()
    holdings={};cash=1.0;rows=[];trades=[];turnover=0.;fees=0.;nonexec=0;vol0=0;stale=0
    for date in daily:
        actual=open_px.loc[date]
        prices=marks.loc[date]
        owned=sum(float(sh*prices[t]) for t,sh in holdings.items())
        pre=cash+owned
        stale+=sum(int(pd.isna(actual[t])) for t in holdings)
        if date in exec_map:
            sig=exec_map[date]
            desired=picks.get(sig,[])[:topn]
            # Open cannot be used to choose an alternative ticker. An
            # unavailable fill becomes uninvested cash, never a phantom trade.
            tradable=[t for t in desired if pd.notna(actual[t]) and actual[t]>0]
            nonexec+=len(desired)-len(tradable)
            blocked=[t for t in holdings if pd.isna(actual[t]) or actual[t]<=0]
            if blocked: raise RuntimeError(f"Existing holding cannot be sold {market} {date}: {blocked}")
            alloc={t:1.0/topn for t in tradable}
            old={t:float(sh*actual[t]) for t,sh in holdings.items()}
            after=pre
            for _ in range(50):
                notion=sum(abs(after*alloc.get(t,0)-old.get(t,0)) for t in set(alloc)|set(old))
                new=pre-FEE*notion
                if abs(new-after)<1e-14: break
                after=new
            cost=pre-after;cash=after*(1-sum(alloc.values()))
            holdings={t:float(after*w/actual[t]) for t,w in alloc.items()}
            fees+=cost;turnover+=notion/pre
            zero=[t for t in set(alloc)|set(old) if abs(after*alloc.get(t,0)-old.get(t,0))>1e-10
                  and (pd.isna(volume.loc[date,t]) or volume.loc[date,t]<=0)]
            vol0+=len(zero)
            trades.append(dict(market=market,segment=segment,variant=variant,
                 top_n=topn,signal_date=str(sig.date()),exec_date=str(date.date()),
                 selections="|".join(desired),filled="|".join(tradable),
                 quote_fail_count=len(desired)-len(tradable),zero_reported_volume=len(zero),
                 cost=cost,oneway_turnover=notion/pre))
        wealth=cash+sum(float(sh*prices[t]) for t,sh in holdings.items())
        rows.append((date,wealth))
    nav=pd.DataFrame(rows,columns=["date","nav"])
    last=nav.nav.iloc[-1]; years=(daily[-1]-daily[0]).days/365.25
    cagr=float(last**(1/years)-1)
    dd=float((nav.nav/nav.nav.cummax()-1).min())
    result=dict(market=market,segment=segment,variant=variant,top_n=topn,
        signal_months=len(tdates),start=str(first.date()),end=str(terminal.date()),
        n_daily=len(nav),cagr_eur=cagr,max_dd=dd,terminal_nav=last,
        fee_total=fees,turnover_oneway=turnover,missed_fills=nonexec,
        zero_reported_volume_orders=vol0,stale_valuation_marks=stale)
    nav["market"]=market;nav["segment"]=segment;nav["variant"]=variant;nav["top_n"]=topn
    return result,nav,pd.DataFrame(trades)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--us",required=True)
    p.add_argument("--eu",required=True)
    p.add_argument("--fx",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    us=pd.read_csv(Path(a.us)/"universe.csv")
    eu=pd.read_csv(Path(a.eu)/"EU148_VERIFIED_LEGAL_ISIN_CATALOG.csv")
    assert len(us)==us.ticker.nunique()==149
    assert len(eu)==eu.ticker.nunique()==148
    assert REF_U in set(us.ticker) and REF_E in set(eu.ticker)
    uop,uc,uv=load_raw(a.us,us,"US149")
    eop,ec,ev=load_raw(Path(a.eu)/"raw_ticker_csv",eu,"EU148")
    common=uop[REF_U].dropna().index.intersection(eop[REF_E].dropna().index).sort_values()
    common=common[(common>=pd.Timestamp("2012-01-01"))&(common<=pd.Timestamp(END))]
    assert len(common)>3200 and common[-1]==pd.Timestamp(END),(len(common),common[-1])
    # Only the exchange-open common calendar may generate a model decision.
    dates=pd.Series(common,index=common)
    dates=dates[(dates>=pd.Timestamp(START))&(dates<=pd.Timestamp(LAST_SIGNAL))]
    signals=dates.groupby(dates.index.to_period("M")).last().tolist()
    assert len(signals)==101,(len(signals),signals[:2],signals[-2:])
    assert len(set(signals))==101
    # As-of prior US close at each subsequent Open: USD/EUR from original
    # audited source; this remains a provider-prior-close FX proxy, not
    # claim of executable interbank fixing. No future data at Open.
    fx=pd.read_csv(a.fx,parse_dates=["date"]).set_index("date").Close
    assert fx.index.max()>=pd.Timestamp(END)
    fx=fx.reindex(common).ffill()
    assert fx.loc[common[common>=pd.Timestamp(START)]].notna().all()
    uop=uop.reindex(common).div(fx,axis=0)
    uc=uc.reindex(common).div(fx,axis=0)
    # For original US model opportunity scores use *native USD* returns:
    # trailing momentum is currency neutral across any US ETF on a given
    # signal day because exchange rate factor is common; EUR NAV correct.
    eop=eop.reindex(common)
    ec=ec.reindex(common)
    uv=uv.reindex(common);ev=ev.reindex(common)
    sels={
       "US149":("US_FULL",set(us.ticker)),
       "US_EQUITY":("US_EQUITY",set(us.loc[us.macro_category.str.startswith(("C01","C02","C03")), "ticker"])),
       "US_CORE_SECTOR":("US_CORE_SECTOR",set(us.loc[us.macro_category.str.startswith(("C01","C02")), "ticker"])),
       "EU148":("EU_FULL",set(eu.ticker)),
       "EU_EQUITY":("EU_EQUITY",set(eu.loc[eu.macro_category.str.startswith("EU_EQUITY"),"ticker"])),
    }
    assert all(len(s)>15 for k,(g,s) in sels.items())
    # Recompute features in local quoted currency; conversion of US native
    # dollar returns is inconsequential to within-day ranking of same cohort,
    # but FX drift through dates could slightly alter historical rank ordering.
    # Use original raw USD closes for signal selection.
    uc_native=uc.mul(fx,axis=0)
    rU,validU=factors(uc_native,common)
    rE,validE=factors(ec,common)
    score=[];nav=[];trades=[];diagnostic=[];skill=[]
    for name,(segment,universe) in sels.items():
        op,vol,retn,valid=(uop,uv,rU,validU) if name.startswith("US") else (eop,ev,rE,validE)
        for period in SEEDS:
            picks={}
            for sig in signals:
                s=retn[period].loc[sig].dropna()
                s=s[s.index.isin(universe)]
                s=s.sort_values(ascending=False,kind="mergesort")
                assert len(s)>=15,(name,period,sig,len(s))
                picks[sig]=list(s.index)
                if period==126:
                    diagnostic.append(dict(market=name,signal_date=str(sig.date()),
                     n_asof_warm=len(s), n_vol_zero=int((vol.loc[sig,s.index].fillna(0)<=0).sum()),
                     top1=str(s.index[0]),momentum_126=float(s.iloc[0]),
                     cross_section_momentum126_median=float(s.median())))
                # Realized 21-joint-session future Open move, one common
                # calendar only; missing execution Open excluded ex-post
                # from skill *measurement*, never from signal selection.
                startpos=common.searchsorted(sig,side="right")
                endpos=startpos+21
                if endpos<len(common):
                    rd=op.iloc[endpos].div(op.iloc[startpos])-1
                    sub=pd.DataFrame({"pred":s,"fwd21":rd.reindex(s.index)}).dropna()
                    if len(sub)>12:
                        best=sub.index[0] if s.index[0] in sub.index else None
                        skill.append(dict(market=name,variant=f"MOM{period}",signal_date=str(sig.date()),
                          n=len(sub),spearman=float(spearmanr(sub.pred,sub.fwd21).statistic),
                          top1_excess=float(sub.loc[best,"fwd21"]-sub.fwd21.mean()) if best else np.nan,
                          top1_was_executable=best is not None))
            for n in TOPS:
                res,nv,tr=compute_nav(op,vol,signals,picks,common,signals,name,segment,f"MOM{period}",n)
                score.append(res);nav.append(nv);trades.append(tr)
                print("PARITY",name,"MOM",period,"TOP",n,"CAGR_EUR",round(res["cagr_eur"],5),"MAXDD",round(res["max_dd"],5),flush=True)
    for name,ref,op,vol in [("US149",REF_U,uop,uv),("EU148",REF_E,eop,ev)]:
        # Same 101 monthly initial control with fully unchanged passive holding:
        # initial buying at first possible Open; no rebalancing until terminal.
        first=common[common.searchsorted(signals[0],side="right")]
        sub=common[(common>=first)&(common<=pd.Timestamp(END))]
        assert op.loc[sub,ref].notna().all(),name
        navser=(1-FEE)*op.loc[sub,ref]/op.loc[first,ref]
        navser.iloc[-1]*=(1-FEE)
        years=(sub[-1]-sub[0]).days/365.25
        bench=dict(market=name,segment="PASSIVE",variant=ref,top_n=1,
            signal_months=101,start=str(first.date()),end=str(sub[-1].date()),
            n_daily=len(sub),cagr_eur=float(navser.iloc[-1]**(1/years)-1),
            max_dd=float((navser/navser.cummax()-1).min()),terminal_nav=float(navser.iloc[-1]),
            fee_total=float(2*FEE),turnover_oneway=2.0,missed_fills=0,
            zero_reported_volume_orders=0,stale_valuation_marks=0)
        score.append(bench)
        nav.append(pd.DataFrame(dict(date=sub,nav=navser.to_numpy(),
             market=name,segment="PASSIVE",variant=ref,top_n=1)))
    scores=pd.DataFrame(score)
    b=scores[scores.segment.eq("PASSIVE")].set_index("market").cagr_eur.to_dict()
    scores["market_benchmark_cagr_eur"]=scores.market.map(b)
    scores["excess_cagr_vs_home_benchmark_pp"]=100*(scores.cagr_eur-scores.market_benchmark_cagr_eur)
    scores.to_csv(out/"PARITY_STRATEGY_CAGR_EUR.csv",index=False)
    pd.concat(nav,ignore_index=True).to_csv(out/"PARITY_DAILY_NAV_EUR.csv",index=False)
    pd.concat(trades,ignore_index=True).to_csv(out/"PARITY_TRADES.csv",index=False)
    pd.DataFrame(diagnostic).to_csv(out/"PARITY_ASOF_UNIVERSE.csv",index=False)
    skill=pd.DataFrame(skill)
    skill.groupby(["market","variant"]).agg(months=("signal_date","nunique"),
         nmean=("n","mean"),spearman=("spearman","mean"),mean_top1_excess21=("top1_excess","mean")).reset_index().to_csv(out/"PARITY_MOMENTUM_SKILL.csv",index=False)
    pd.DataFrame({"month":range(1,102),"common_signal_date":signals}).to_csv(out/"PARITY_101_MATCHED_SIGNAL_DATES.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
       us_source="canonical 149 original evidence_v1/data/original149",
       eu_source="Europe148 2010+ corrected corporate actions research OHLCV",
       first_signal=str(signals[0].date()),last_signal=str(signals[-1].date()),
       common_joint_exchange_calendar=True,common_numeraire="EUR",
       US_to_EUR_fx="EURUSD_PRIOR_US_CLOSE prior US close, illustrative not a live FX executable spread",
       same_10bp_oneway_cost=True,same_101_signals=True,same_single_account=True,
       prediction_without_future_labels=True,asof_vintage_minimum_252_observed_closes=True,
       no_fake_executable_stale_quotes=True,
       alpha_targets=["matched baseline","momentum 21/63/126/252","equity-only opportunity"],
       NOT_THE_V3_ML_MODEL=True,
       categories_not_identical=True,
       full_sample_not_an_independent_holdout=True
    ),indent=2))
    print("MATCHED_NATIVE_EUR_PAIRED_CONTROL_PASS",scores.to_string(index=False),flush=True)

if __name__=="__main__":main()
