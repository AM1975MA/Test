#!/usr/bin/env python3
"""Predeclared first-stage drift/diffusion exclusion BEFORE frozen annual US Ridge.

Exactly original US V2 canonical 500x24 membership, fixed basket seed and SHA.
18? US 9 fits: previously completed 2018...2026, same 101 signal dates.
NO reselection/mutation of canonical membership, no future-return labels for decisions.
Policies: NO_FILTER, PHYS_TAIL_25, MOMENTUM_25, RANDOM_25.
Top2, equal initial weights, monthly next ACTUAL open, 10bp on each traded side.
THIS IS A TWO-LAYER diagnostic, NOT original V2 Hybrid24/risk/Tail fullstack.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys,time
from pathlib import Path
import numpy as np,pandas as pd
from scipy.special import ndtr
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[2]/"fullstack_legacy"
sys.path.insert(0,str(ROOT/"src"))
from etf_trader.source_only.baskets import build_canonical_baskets
SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
SEED=20261027
FEE=.001
def annual_stats(nav,dates):
    years=(dates[-1]-dates[0]).days/365.25
    endpoint=nav[-1]
    cagr=endpoint**(1/years)-1
    pk=np.maximum.accumulate(np.vstack((np.ones((1,nav.shape[1])),nav)),axis=0)[1:]
    dd=(nav/pk-1).min(axis=0)
    return cagr,dd
def simulate(panel,sel,idx,dates,mark):
    """Same-month all portfolios start with unit capital; share quantities drift daily.
    A missing actual execution open is NEVER substituted with previous or future price.
    No lookahead on trade decisions. A missing old-holding sell quote raises.
    """
    nd,nt=panel.shape
    nb=sel.shape[1]
    assert sel.shape[2]==2 and sel.shape[0]==len(idx)
    ss=np.arange(nb)
    # last quote only for portfolio MARKS; actual trade price must be observed
    val=pd.DataFrame(panel).ffill().to_numpy(float)
    if not np.isfinite(val[idx[0]:]).all():raise RuntimeError("Open-only marks missing after start")
    cash=np.ones(nb);old_idx=np.full((nb,2),-1,dtype=np.int32)
    qty=np.zeros((nb,2));nav=np.empty((len(mark),nb),float)
    fees=np.zeros(nb);turn=np.zeros(nb);unfilled=np.zeros(nb,int)
    for k,d in enumerate(mark):
        px=val[d]
        oldv=qty*np.where(old_idx>=0,px[np.maximum(old_idx,0)[None,:] if False else np.maximum(old_idx,0)],0)
        # elementwise ticker selection for basket b and slot j
        oldv=qty*px[np.maximum(old_idx,0)]
        equity=cash+oldv.sum(axis=1)
        if d in idx:
            m=idx.index(d)
            # sell old positions only if we actually have open quotes
            live=panel[d]
            if (qty>0).any() and not np.isfinite(live[np.maximum(old_idx,0)][qty>0]).all():
                raise RuntimeError("Holding untradable at rebalance "+str(dates[d]))
            requested=sel[m].copy()
            fill=(requested>=0)&np.isfinite(live[np.maximum(requested,0)])&(
                    live[np.maximum(requested,0)]>0)
            unfilled+=(~fill).sum(axis=1)
            qidx=np.where(fill,requested,-1)
            alloc=np.where(fill,.5,0.)
            prior=np.zeros((nb,2),float)
            for jj in (0,1):
                prior[:,jj]=((old_idx==qidx[:,jj,None])*oldv).sum(axis=1)
            sold=oldv.sum(axis=1)-prior.sum(axis=1)
            after=equity.copy()
            for _ in range(30):
                volnotional=np.abs(after[:,None]*alloc-prior).sum(axis=1)+sold
                next_after=equity-FEE*volnotional
                if np.max(np.abs(next_after-after))<1.e-13:break
                after=next_after
            fees+=(equity-after)
            turn+=volnotional/np.maximum(equity,1e-15)
            cash=after*(1-alloc.sum(axis=1))
            old_idx=qidx
            qty=np.where(fill,after[:,None]*alloc/np.maximum(live[np.maximum(qidx,0)],1e-99),0.)
            equity=after
        nav[k]=cash+(qty*px[np.maximum(old_idx,0)]).sum(axis=1)
        if not np.isfinite(nav[k]).all():raise RuntimeError("nonfinite nav "+str(d))
    return nav,dict(fees=fees,turnover=turn,unfilled=unfilled)
def signal_score(close,signal,universe):
    """Causal drift-diffusion proxy from simple price *returns* (no rank labels).
    Rolling sigma per trading session annualization exactly mirrors earlier EU test.
    Candidate must have >=126 earlier observations for this veto, else risk=+inf.
    """
    at=close.index.searchsorted(signal,side="right")-1
    if at<252:raise RuntimeError("insufficient history")
    c=close.iloc[:at+1].ffill(limit=1)
    p=c.iloc[-1]
    mom={d:(p/c.iloc[-d-1]-1) for d in (21,63,126)}
    rr=c.pct_change(fill_method=None)
    std21=rr.iloc[-21:].std(ddof=1)*np.sqrt(252)
    sigma=(std21/np.sqrt(252)*np.sqrt(21)).clip(lower=.001)
    mu=.5*mom[21]+.3*mom[63]/3+.2*mom[126]/6
    tail=pd.Series(ndtr((-.05-mu)/sigma),index=universe)
    tail=tail.where(np.isfinite(tail),np.inf)
    return tail,mom[63]
def main():
    a=argparse.ArgumentParser()
    for nm in ("raw","pred","membership","out"):a.add_argument("--"+nm,required=True)
    z=a.parse_args();out=Path(z.out);out.mkdir(exist_ok=True,parents=True)
    basket_path=Path(z.membership)
    if hashlib.sha256(basket_path.read_bytes()).hexdigest()!=SHA:raise RuntimeError("500 basket SHA MISMATCH")
    member=pd.read_csv(basket_path)
    assert len(member)==12000 and member.basket.nunique()==500
    meta=pd.read_csv(Path(z.raw)/"universe.csv")
    assert meta.ticker.nunique()==149 and meta.macro_category.nunique()==6
    cats=meta[['ticker','macro_category']]
    rebuilt=build_canonical_baskets(cats,meta.ticker.tolist())
    assert rebuilt.equals(member),"Regenerated canonical baskets differ, STOP"
    assert set(member.ticker)==set(meta.ticker)
    assert member.groupby('basket').ticker.nunique().eq(24).all()
    assert member.merge(cats,on='ticker').groupby(['basket','macro_category']).size().eq(4).all()
    tickers=sorted(meta.ticker)
    tmap={t:i for i,t in enumerate(tickers)}
    B=np.array([[tmap[t] for t in member.loc[member.basket.eq(i),'ticker']] for i in range(500)],dtype=np.int32)
    frames={}
    for t in tickers:
        d=pd.read_csv(Path(z.raw)/(t+".csv"),parse_dates=['date'])
        d=d.drop_duplicates('date').set_index('date').sort_index()
        assert {'Open','Close'}.issubset(d.columns)
        frames[t]=d
    close=pd.concat({t:d.Close for t,d in frames.items()},axis=1).sort_index()
    op=pd.concat({t:d.Open for t,d in frames.items()},axis=1).sort_index()
    assert 'SPY' in close.columns
    cal=pd.DatetimeIndex(op['SPY'].dropna().index)
    op=op.reindex(cal).reindex(columns=tickers)
    close=close.reindex(cal).reindex(columns=tickers)
    signal=[];auds=[]
    for year in range(2018,2027):
        yearpath=Path(z.pred)/str(year)
        r=pd.read_csv(yearpath/"ANNUAL_TRAJECTORY_FORECASTS.csv",parse_dates=['signal_date'])
        au=json.loads((yearpath/"ANNUAL_FIT_AUDIT.json").read_text())
        assert au['year']==year and au['market']=='US149'
        assert au['train_last_63_label_exit']<f'{year}-01-01'
        r=r[r.model.eq('LM_RIDGE_PATH')].copy()
        assert len(r)==r[['ticker','signal_date']].drop_duplicates().shape[0]
        assert r.signal_date.dt.year.eq(year).all()
        assert r.groupby('signal_date').ticker.nunique().eq(149).all()
        signal.append(r)
        auds.append(au)
    forecast=pd.concat(signal,ignore_index=True)
    assert forecast.signal_date.nunique()==101 and forecast.ticker.nunique()==149
    assert len(forecast)==101*149 and not forecast.duplicated(['signal_date','ticker']).any()
    dates=sorted(forecast.signal_date.unique())
    first=cal[cal.searchsorted(dates[0],side="right")]
    end=cal[cal.searchsorted(pd.Timestamp("2026-07-01"))]
    entries=[int(cal.searchsorted(d,side="right")) for d in dates]
    mark=list(range(entries[0],int(cal.get_loc(end))+1))
    assert len(entries)==101
    full=pd.DataFrame(index=dates,columns=tickers,dtype=float)
    label=pd.DataFrame(index=dates,columns=tickers,dtype=float)
    for r in forecast.itertuples():
        full.at[r.signal_date,r.ticker]=r.forecast_21
        label.at[r.signal_date,r.ticker]=r.fwd_ret_21
    assert full.notna().all().all() and np.isfinite(full.to_numpy(float)).all()
    score=full.to_numpy(float)
    risk=[];mom=[]
    for d in dates:
        tail,m=signal_score(close,d,tickers)
        risk.append(tail.to_numpy(float));mom.append(m.to_numpy(float))
    risk=np.array(risk);mom=np.array(mom)
    # each basket-month 24 entries at its fixed canonical membership, remove 6 worst
    policies=["NO_VETO","PHYS_TAIL_25","MOMENTUM_25","RANDOM_25"]
    sel={k:np.empty((101,500,2),np.int32) for k in policies}
    audits=[];picked=[]
    for m,dt in enumerate(dates):
        f=score[m]
        seq=np.argsort(-f[B],axis=1,kind="stable")
        rrank=np.argsort(-risk[m,B],axis=1,kind="stable")
        krank=np.argsort(mom[m,B],axis=1,kind="stable")
        rng=np.random.default_rng(SEED+m)
        for bi in range(500):
            rr={"NO_VETO":set(),
                "PHYS_TAIL_25":set(rrank[bi,:6]),
                "MOMENTUM_25":set(krank[bi,:6]),
                "RANDOM_25":set(rng.choice(24,6,replace=False))}
            for policy in policies:
                allowed=[j for j in seq[bi] if j not in rr[policy]]
                assert len(allowed)==(24 if policy=='NO_VETO' else 18)
                ss=B[bi,allowed[:2]]
                assert len(set(map(int,ss)))==2
                sel[policy][m,bi]=ss
                for rank,t in enumerate(ss):
                    picked.append(dict(date=str(pd.Timestamp(dt).date()),basket=bi,policy=policy,
                          rank=rank+1,ticker=tickers[t],forecast_21=f[t],
                          mathematical_p5=risk[m,t],prior_momentum63=mom[m,t]))
                if policy!='NO_VETO':
                    baseline=set(map(int,sel['NO_VETO'][m,bi]))
                    audits.append(dict(signal_date=dt,basket=bi,policy=policy,
                            veto_of_original_top2=len(baseline-set(map(int,ss)))))
        if m%24==0:print("CAUSAL_SIGNAL_MONTH",m+1,str(pd.Timestamp(dt).date()),flush=True)
    pd.DataFrame(picked).to_csv(out/"CANONICAL500_TOP2_PICKS.csv",index=False)
    pd.DataFrame(audits).to_csv(out/"ORIGINAL_TOP2_REPLACEMENT_AUDIT.csv",index=False)
    pd.DataFrame(auds).to_csv(out/"FROZEN_ANNUAL_LM_MATURITY_AUDIT.csv",index=False)
    # Source-vintage audit: 21 US sessions from SPY calendar vs frozen EU+US joint
    # 21 sessions target may not exactly match, so keep original observed future test.
    p=op.to_numpy(float)
    true=np.empty_like(score);error=[]
    for m,si in enumerate(entries):
        ex=si+21
        true[m]=p[ex]/p[si]-1
        e=np.nanmedian(np.abs(true[m]-label.iloc[m].to_numpy(float)))
        error.append(dict(signal_date=str(pd.Timestamp(dates[m]).date()),median_label_gap_21_us_vs_joint=float(e)))
    pd.DataFrame(error).to_csv(out/"SOURCE_VINTAGE_21D_LABEL_DIFFERENCE.csv",index=False)
    econ=[];monthly_skill=[];aggregate_nav={}
    def extract_metrics(nav,policy,top='2'):
        cag,dd=annual_stats(nav,cal[mark])
        equal=nav.mean(axis=1)
        agg_cagr=float(equal[-1]**(1/((cal[mark[-1]]-cal[mark[0]]).days/365.25))-1)
        agg_dd=float((equal/np.maximum.accumulate(np.r_[1.,equal])[1:]-1).min())
        return dict(policy=policy,mean_basket_cagr=float(cag.mean()),median_basket_cagr=float(np.median(cag)),
            p10_basket_cagr=float(np.quantile(cag,.10)),
            p90_basket_cagr=float(np.quantile(cag,.90)),
            mean_basket_dd=float(dd.mean()),p10_basket_dd=float(np.quantile(dd,.10)),
            worst_basket_dd=float(dd.min()),equal_capital_aggregate_cagr=agg_cagr,
            equal_capital_aggregate_dd=agg_dd,n_baskets=500,n_months=101,topn=2)
    for name in policies:
        n,meta=simulate(p,sel[name],entries,dates,mark)
        mm=extract_metrics(n,name)
        mm.update(mean_oneway_turnover=float(meta['turnover'].mean()),
                  total_unfilled=int(meta['unfilled'].sum()),
                  mean_total_fees=float(meta['fees'].mean()))
        econ.append(mm)
        aggregate_nav[name]=n.mean(axis=1)
        for m,dt in enumerate(dates):
            vals=true[m][sel[name][m]]
            mf=score[m][sel[name][m]]
            monthly_skill.append(dict(policy=name,date=str(pd.Timestamp(dt).date()),
                mean_selected_future21=float(np.nanmean(vals)),
                selected_crash5_rate=float(np.nanmean(vals<-.05)),
                selected_future21_median=float(np.nanmedian(vals)),
                rank_score_mean=float(np.nanmean(mf)),
                n_selected=len(vals.reshape(-1))))
        print("ECON_500",name,"mean_cagr",round(mm['mean_basket_cagr']*100,4),
              "agg_cagr",round(mm['equal_capital_aggregate_cagr']*100,4),
              "mean_maxdd",round(mm['mean_basket_dd']*100,3),
              "crashrate",round(np.mean([x['selected_crash5_rate'] for x in monthly_skill if x['policy']==name])*100,3),
              flush=True)
    pd.DataFrame(econ).to_csv(out/"CANONICAL500_LM_VETO_ECONOMICS.csv",index=False)
    skill=pd.DataFrame(monthly_skill)
    skill.to_csv(out/"CANONICAL500_MONTHLY_PREDICTIVE_SKILL.csv",index=False)
    nav=pd.DataFrame({'date':cal[mark]})
    for k,v in aggregate_nav.items():nav[k]=v
    nav.to_csv(out/"CANONICAL500_EQUAL_CAPITAL_DAILY_NAV.csv",index=False)
    # Paired bootstrap across time, never pseudo-independent overlapping 500 baskets.
    rows=[];rng=np.random.default_rng(SEED)
    for policy in policies[1:]:
        aa=skill.loc[skill.policy.eq(policy)].reset_index(drop=True)
        bb=skill.loc[skill.policy.eq("NO_VETO")].reset_index(drop=True)
        assert aa.date.equals(bb.date)
        for col in ["selected_crash5_rate","mean_selected_future21"]:
            delta=aa[col].to_numpy()-bb[col].to_numpy(); boot=[]
            for _ in range(6000):
                idxs=[]
                while len(idxs)<101:
                    q=int(rng.integers(0,101));idxs.extend((q+np.arange(6))%101)
                boot.append(float(delta[np.asarray(idxs[:101])].mean()))
            rows.append(dict(policy=policy,metric=col,delta=float(delta.mean()),
                ci_95_low=float(np.quantile(boot,.025)),ci_95_high=float(np.quantile(boot,.975))))
    pd.DataFrame(rows).to_csv(out/"CANONICAL500_PAIRED_TIME_BLOCK_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
       method="pure-math first-stage veto then frozen 125-feature US LM Ridge21",
       canonical_basket_sha256=SHA,basket_count=500,size_per_basket=24,
       category_quota=4,categories=6,yearly_fits=9,oos_months=101,seed=SEED,
       alternatives=policies,actual_trading="next recorded US Open; 10 bps each side",
       reference_original_v2_complete_common_2018_mean_cagr=0.2200772062760372,
       crucial="DOES NOT simulate full historical V2 Hybrid24 Tail/DD/V6/HighCAGR stack. It is isolated LM/physics ablation.",
       label_audit="US full native21days observed future versus originally saved 21 joint calendar days. Both are retrospective only.",
       research_bias="historical months repeatedly used in previous research. no untouched OOS",
       open_price_eur="USD results, not FX converted; original 500 traded on US venues",
       no_leakage="all veto features only earlier or same signal closes; trained Ridge pre-annual, fully matured 63-session prior Jan1"
    ),indent=2))
    assert all(x['total_unfilled']==0 for x in econ),"Nonexecution detected; read scorecard"
    print("CANONICAL_500_MATH_BEFORE_LM_ALL_PASS",len(econ),flush=True)
if __name__=='__main__':main()
