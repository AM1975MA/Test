#!/usr/bin/env python3
"""2026-10-26 reproducible EU148 freeze-127 liquidity and factor forensic gate.

Reuses ORIGINAL ranker picks and identical NAV from category_gate_controlled_audit,
without fitting or hyperparameter search. Assumptions: 63 past EU trading days,
90% positive vendor volume, median(Cl*Volume)>= EUR 50k,250k,1m; cash veto.
EXSA same monthly invested fraction benchmark. Posthoc Newey-West 3-factor
regression is diagnostic only, not an independent OOS validation.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd,statsmodels.api as sm
from category_gate_controlled_audit import source,strategies,account

REF="DE0002635307"
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    cat,trade,days,O,C,V,R=source(Path(a.root))
    target,decisions,risk=strategies(cat,trade,C,R)
    assert len(days)==2076 and len(target["FULL"])==101
    classes=cat.set_index("ticker").macro_category.to_dict()
    eurocal=C[REF].dropna().index
    snapshots=[];liquidity={}
    for i,dt in enumerate(sorted(target["FULL"])):
        sig=trade["FULL"][dt][0]
        k=eurocal.get_loc(sig)
        prior=eurocal[k-62:k+1]
        assert len(prior)==63
        candidates=set().union(*(set(t[dt]) for t in target.values()))
        if i>0:
            past=sorted(target["FULL"])[i-1]
            candidates|=set().union(*(set(t[past]) for t in target.values()))
        for isin in candidates:
            v=V[isin].reindex(prior)
            c=C[isin].reindex(prior)
            ok=(v>0)&v.notna()&c.gt(0)
            n=int(ok.sum())
            adv=float((c*v).fillna(0).median())
            row=dict(signal_date=sig,execution_date=dt,ticker=isin,
                macro_category=classes[isin],positive_volume_count=n,
                n_market_days=63,positive_volume_fraction=n/63,
                median_daily_turnover_eur=adv)
            liquidity[(dt,isin)]=row
            snapshots.append(row)
    pd.DataFrame(snapshots).to_csv(out/"ASOF_63D_COHORT_VOLUME.csv",index=False)
    policies={n:target[n] for n in ("FULL","EQUITY","REL_MOM_GATE","EQUITY_BETA_MATCH_FULL")}
    veto=[]
    for base in ("FULL","EQUITY","REL_MOM_GATE"):
        for cutoff in (50000,250000,1000000):
            name=f"{base}_ADV{cutoff//1000}K_Q90"
            monthly={}
            for dt,weights in target[base].items():
                allowed={}
                for t,w in weights.items():
                    obj=liquidity[(dt,t)]
                    passgate=(obj["positive_volume_fraction"]>=0.9 and obj["median_daily_turnover_eur"]>=cutoff)
                    if passgate: allowed[t]=w
                monthly[dt]=allowed
                veto.append(dict(policy=name,signal_date=trade["FULL"][dt][0],
                    execution_date=dt,accepted=len(allowed),rejected=5-len(allowed),
                    invested_fraction=sum(allowed.values()),isin_allowed="|".join(allowed)))
            policies[name]=monthly
    pd.DataFrame(veto).to_csv(out/"CAUSAL_LIQUIDITY_VETO_DECISIONS.csv",index=False)
    # Truly exact base replay check, including cash, fees, and next-open quotes.
    paired=pd.read_csv(Path(a.root)/"ORIGINAL_PAIRED_ECONOMIC_SCORECARD.csv")
    expect=paired[(paired.market=="EU148")&(paired.top_n==5)].set_index("segment")
    for base in ("FULL","EQUITY"):
        rr,nv,tr=account(base,policies[base],days,O,V,10)
        actual=float(expect.loc[base,"cagr_eur"])
        assert abs(rr["cagr"]-actual)<1e-10,(base,rr["cagr"],actual)
    print("EXACT_127_CAGR_REPLAY_PASS",flush=True)
    score=[];nav=[];orders=[]
    for name,alloc in policies.items():
        rr,nv,tr=account(name,alloc,days,O,V,10)
        score.append(rr);nav.append(nv);orders.append(tr)
        print("EU148_ASOF_ADV",name,"CAGR",round(100*rr["cagr"],5),
            "DD",round(100*rr["max_dd"],5),flush=True)
    score=pd.DataFrame(score)
    nav=pd.concat(nav,ignore_index=True)
    score.to_csv(out/"LIQUIDITY_GATE_ECONOMICS.csv",index=False)
    nav.to_csv(out/"LIQUIDITY_GATE_DAILY_NAV.csv",index=False)
    pd.concat(orders,ignore_index=True).to_csv(out/"LIQUIDITY_GATE_ORDERS.csv",index=False)
    # Same monthly investment weight via EXSA index; no hindsight.
    dates=pd.DatetimeIndex(days)
    px=O[REF].reindex(dates)
    assert px.notna().all()
    years=(dates[-1]-dates[0]).days/365.25
    cb=[]; cbnav=[]; cbhac=[]
    for name,monthly in policies.items():
        sh=0.;cash=1.;rec=[]
        for dt,x in px.items():
            pre=cash+sh*x
            if dt in monthly:
                w=sum(monthly[dt].values())
                after=pre
                for _ in range(40):
                    delta=abs(after*w-sh*x)
                    nxt=pre-.001*delta
                    if abs(after-nxt)<1e-14:break
                    after=nxt
                sh=after*w/x;cash=after*(1-w)
            rec.append((dt,cash+sh*x))
        bench=pd.DataFrame(rec,columns=["date","nav"])
        bench["strategy"]=name
        a1=score.set_index("variant").loc[name]
        bcagr=bench.nav.iloc[-1]**(1/years)-1
        mynav=nav[nav.variant.eq(name)].set_index("date").nav.reindex(dates).to_numpy()
        diff=pd.Series(mynav).pct_change()-bench.nav.pct_change()
        diff=diff.dropna().to_numpy()
        fit=sm.OLS(diff,np.ones((len(diff),1))).fit(cov_type="HAC",cov_kwds={"maxlags":21})
        cb.append(dict(variant=name,cagr=float(a1.cagr),matched_EXSA_CAGR=bcagr,
            excess_CAGR_pp=100*(a1.cagr-bcagr),
            cash_fraction_mean=np.mean([1-sum(w.values()) for w in monthly.values()])))
        cbhac.append(dict(variant=name,expost_mean_diff_annual_pp=25200*fit.params[0],
            HAC95_lo_pp=25200*(fit.params[0]-1.96*fit.bse[0]),
            HAC95_hi_pp=25200*(fit.params[0]+1.96*fit.bse[0]),p_value=fit.pvalues[0]))
        cbnav.append(bench)
    pd.DataFrame(cb).to_csv(out/"MATCHED_CASH_EXSA_BENCHMARK.csv",index=False)
    pd.DataFrame(cbhac).to_csv(out/"MATCHED_CASH_EXSA_HAC.csv",index=False)
    pd.concat(cbnav).to_csv(out/"MATCHED_CASH_EXSA_NAV.csv",index=False)
    # Ex-post factor attribution: broad equity EXSA + property / sovereign.
    factor=pd.DataFrame(index=dates)
    factor["EXSA"]=px.pct_change(fill_method=None)
    for cname in ("EU_PROPERTY","SOVEREIGN_EUR"):
        etfs=[t for t,c in classes.items() if c==cname]
        r=O[etfs].reindex(dates).pct_change(fill_method=None)
        factor[cname]=r.mean(axis=1)
    factors=["EXSA","EU_PROPERTY","SOVEREIGN_EUR"]
    summaries=[];contras=[]
    for name in ("FULL","EQUITY","REL_MOM_GATE","EQUITY_BETA_MATCH_FULL"):
        series=nav[nav.variant.eq(name)].set_index("date").nav.reindex(dates).pct_change()
        fitdata=factor.join(series.rename("strat")).dropna()
        reg=sm.OLS(fitdata.strat,sm.add_constant(fitdata[factors])).fit(
           cov_type="HAC",cov_kwds={"maxlags":21})
        summaries.append(dict(variant=name,nobs=len(fitdata),R2=reg.rsquared,
           alpha_annual_pp=25200*reg.params["const"],
           HAC_t=reg.tvalues["const"],HAC_p=reg.pvalues["const"],
           beta_EXSA=reg.params["EXSA"],beta_PROPERTY=reg.params["EU_PROPERTY"],
           beta_SOVEREIGN=reg.params["SOVEREIGN_EUR"]))
        if name=="FULL":reference=series
        else:
            df=factor.join((series-reference).rename("difference")).dropna()
            m=sm.OLS(df.difference,sm.add_constant(df[factors])).fit(
               cov_type="HAC",cov_kwds={"maxlags":21})
            contras.append(dict(contrast=name+" MINUS FULL",
                adjusted_diff_annual_pp=25200*m.params["const"],
                HAC95_lo_pp=25200*(m.params["const"]-1.96*m.bse["const"]),
                HAC95_hi_pp=25200*(m.params["const"]+1.96*m.bse["const"]),
                HAC_p=m.pvalues["const"]))
    pd.DataFrame(summaries).to_csv(out/"EXPOST_THREE_FACTOR_HAC_ALPHA.csv",index=False)
    pd.DataFrame(contras).to_csv(out/"EXPOST_THREE_FACTOR_HAC_DIFF.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
       status="EXPLORATORY_NOT_PRODUCTION",date="2026-10-26",
       n_months=101,n_daily=2076,ranker_frozen=True,exante_63day_quote_gate=True,
       fee_bps_per_side=10,benchmark="EXSA with same monthly invested fraction and EUR cash",
       regression="EXSA/PROPERTY/SOVEREIGN Open returns HAC lag21",
       warnings=["vendor volume not consolidated and no live order book",
       "cannot confirm liquidity of selling former holdings",
       "2026 survivor selection and adjusted OHLC not point in time",
       "all 2018-2026 months already seen in research, not holdout",
       "factor-proxy regression descriptive not replicable systematic hedge"]),indent=2))
    print("LIQUIDITY_FACTOR_FROZEN_PAIRED_REPLAY_PASS",flush=True)

if __name__=="__main__":main()
