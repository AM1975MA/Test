#!/usr/bin/env python3
"""Reproducible frozen-127leaf EU148 category attribution and risk controls.

Data: verified price artifact 40218758892, paired V3 prediction/economic
artifact 40227417589. Exactly 101 decisions, 2076 joint-US/EU market days.
Original V3 full/equity Top5 must replay with identical 10bps CAGR.
Never refit nor choose a parameter from this test. NO lookahead.
"""
from __future__ import annotations
import argparse,io,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd
P_EU='eu148_final_corrected_ohlcv.zip'
P_ECON='paired_v3_us149_eu148_economics.zip'
REF='DE0002635307';WARM=126
FEES=(.001,.0025,.005,.01)

def readzip(p,name):
    with zipfile.ZipFile(p) as z:return pd.read_csv(io.BytesIO(z.read(name)))
def source(root):
    p=root/P_EU;e=root/P_ECON
    cat=readzip(p,'EU148_VERIFIED_LEGAL_ISIN_CATALOG.csv')
    assert cat.ticker.nunique()==len(cat)==148
    src=readzip(e,'PAIRED_V3_127_REAL_TRADES.csv')
    src=src[(src.market=='EU148')&(src.top_n==5)].copy()
    dv=readzip(e,'PAIRED_V3_127_DAILY_NAV_EUR.csv')
    dv=dv[(dv.market=='EU148')&(dv.segment=='FULL')&(dv.top_n==5)]
    daily=pd.DatetimeIndex(pd.to_datetime(dv.date))
    assert len(daily)==2076 and daily.is_unique
    choices={}
    for seg in ('FULL','EQUITY'):
        q=src[src.segment==seg].copy()
        q['exec_date']=pd.to_datetime(q.exec_date)
        q['signal_date']=pd.to_datetime(q.signal_date)
        assert len(q)==101
        choices[seg]={r.exec_date:(r.signal_date,r.selections.split('|')) for r in q.itertuples()}
        assert all(len(t)==5 for s,t in choices[seg].values())
    assert set(choices['FULL'])==set(choices['EQUITY'])
    o={};c={};v={}
    with zipfile.ZipFile(p) as z:
        for t in cat.ticker:
            d=pd.read_csv(io.BytesIO(z.read(f'raw_ticker_csv/{t}.csv')),parse_dates=['date'])
            d=d.drop_duplicates('date',keep='last').set_index('date').sort_index()
            o[t]=d.Open;c[t]=d.Close;v[t]=d.Volume
    O=pd.concat(o,axis=1);C=pd.concat(c,axis=1);V=pd.concat(v,axis=1)
    assert set(daily).issubset(set(O.index))
    return cat,choices,daily,O,C,V,C.pct_change(fill_method=None)

def strategies(cat,choices,C,R):
    classes=cat.set_index('ticker').macro_category.to_dict()
    cal=C[REF].dropna().index
    policies={p:{} for p in ('FULL','EQUITY','REL_MOM_GATE','EQUITY_BETA_MATCH_FULL','EQUITY_VOL_MATCH_FULL')}
    log=[];risk=[]
    for execution,(signal,full) in sorted(choices['FULL'].items()):
        assert choices['EQUITY'][execution][0]==signal
        equity=choices['EQUITY'][execution][1]
        assert signal in cal
        ii=cal.get_loc(signal)
        past126=cal[ii-126] if ii>=126 else None
        past21=cal[ii-21] if ii>=21 else None
        mktmom=C.loc[signal,REF]/C.loc[past126,REF]-1 if past126 is not None else np.nan
        accepted=[];why=[]
        for t in full:
            if classes[t].startswith('EU_EQUITY'):
                accepted.append(t);why.append(t+':equity');continue
            m126=C.loc[signal,t]/C.loc[past126,t]-1 if past126 is not None and pd.notna(C.loc[past126,t]) else np.nan
            m21=C.loc[signal,t]/C.loc[past21,t]-1 if past21 is not None and pd.notna(C.loc[past21,t]) else np.nan
            yes=bool(np.isfinite(m126) and np.isfinite(m21) and m126>mktmom and m21>0)
            if yes:accepted.append(t)
            why.append(f'{t}:{classes[t]}:pass={yes}')
        nswaps=0
        for t in equity:
            if len(accepted)==5:break
            if t not in accepted:accepted.append(t);nswaps+=1
        assert len(accepted)==5
        policies['FULL'][execution]={t:.2 for t in full}
        policies['EQUITY'][execution]={t:.2 for t in equity}
        policies['REL_MOM_GATE'][execution]={t:.2 for t in accepted}
        idx=cal[max(0,ii-125):ii+1]
        hist=R.reindex(idx)[list(set(full)|set(equity)|{REF})]
        rr=hist[REF].to_numpy(float)
        fr=hist[full].mean(axis=1).to_numpy(float)
        er=hist[equity].mean(axis=1).to_numpy(float)
        def beta(y):
            ok=np.isfinite(rr)&np.isfinite(y)
            if ok.sum()<90:return np.nan
            x=rr[ok];y=y[ok]
            return float(np.mean((x-x.mean())*(y-y.mean()))/x.var()) if x.var()>0 else np.nan
        bf=beta(fr);be=beta(er)
        vf=np.nanstd(fr,ddof=1);ve=np.nanstd(er,ddof=1)
        sb=float(np.clip(bf/be,0,1)) if np.isfinite(bf) and be>0 else 1.
        sv=float(np.clip(vf/ve,0,1)) if np.isfinite(vf) and ve>0 else 1.
        policies['EQUITY_BETA_MATCH_FULL'][execution]={t:.2*sb for t in equity}
        policies['EQUITY_VOL_MATCH_FULL'][execution]={t:.2*sv for t in equity}
        risk.append(dict(signal_date=signal,execution_date=execution,full_beta=bf,equity_beta=be,
            full_vol=vf,equity_vol=ve,beta_scalar=sb,vol_scalar=sv,beta_residual=bf-sb*be,
            full_non_equity=sum(not classes[t].startswith('EU_EQUITY') for t in full),
            kept_non_equity=sum(not classes[t].startswith('EU_EQUITY') for t in accepted),
            replaced=nswaps))
        log.append(dict(signal_date=signal,execution_date=execution,full='|'.join(full),
           equity='|'.join(equity),gate='|'.join(accepted),decision=';'.join(why)))
    assert all(len(x)==101 for x in policies.values())
    return policies,pd.DataFrame(log),pd.DataFrame(risk)

def account(name,w,daily,opens,volume,bps):
    fee=bps/10000.
    o=opens.reindex(daily)
    marks=o.ffill() # only valuation, never execution
    vols=volume.reindex(daily)
    shares={};cash=1.;nav=[];orders=[];fee_amt=0.;turn=0.;zero=0;stale=0
    for dt in daily:
        px=opens.loc[dt];mark=marks.loc[dt]
        pre=cash+sum(n*mark[t] for t,n in shares.items())
        stale+=sum(pd.isna(px[t]) for t in shares)
        if dt in w:
            allocation=w[dt]
            assert 0<=sum(allocation.values())<=1+1e-9
            assert all(0<=v<=.201 for v in allocation.values())
            old={t:n*px[t] for t,n in shares.items()}
            assert all(np.isfinite(n) for n in old.values())
            assert all(np.isfinite(px[t]) and px[t]>0 for t in allocation)
            after=pre
            for _ in range(50):
                traded=sum(abs(after*allocation.get(t,0)-old.get(t,0)) for t in set(old)|set(allocation))
                new=pre-fee*traded
                if abs(new-after)<1e-14:break
                after=new
            cash=after*(1-sum(allocation.values()))
            shares={t:after*frac/px[t] for t,frac in allocation.items() if frac>1e-14}
            fee_amt+=pre-after;turn+=traded/pre
            bad=sum((pd.isna(vols.loc[dt,t]) or vols.loc[dt,t]<=0)
                and abs(after*allocation.get(t,0)-old.get(t,0))>1e-10
                for t in set(old)|set(allocation))
            zero+=bad
            orders.append(dict(date=dt,variant=name,fee_bps=bps,
                cost=pre-after,turnover=traded/pre,cash_weight=cash/after,
                zero_volume_orders=bad,holdings='|'.join(allocation)))
        wealth=cash+sum(n*mark[t] for t,n in shares.items())
        assert wealth>0 and np.isfinite(wealth)
        nav.append((dt,wealth))
    out=pd.DataFrame(nav,columns=['date','nav'])
    years=(daily[-1]-daily[0]).days/365.25
    ret=out.nav.pct_change().dropna()
    score=dict(variant=name,fee_bps=bps,cagr=float(out.nav.iloc[-1]**(1/years)-1),
       max_dd=float((out.nav/out.nav.cummax()-1).min()),
       sharpe=float(np.sqrt(252)*ret.mean()/ret.std(ddof=1)),end_wealth=float(out.nav.iloc[-1]),
       fees_paid=fee_amt,turnover_notional=turn,n_zero_volume=zero,n_stale_marks=stale)
    out['variant']=name;out['fee_bps']=bps
    return score,out,pd.DataFrame(orders)

def bootstrap(x,y,years,block=6,seed=20261025,reps=10000):
    rng=np.random.default_rng(seed)
    a=np.log1p(x);b=np.log1p(y);N=len(a)
    sim=[]
    for _ in range(reps):
        idx=[]
        while len(idx)<N:
            start=int(rng.integers(N))
            idx.extend((start+np.arange(block))%N)
        idd=np.asarray(idx[:N],dtype=int)
        sim.append(100*(np.exp(a[idd].sum()/years)-np.exp(b[idd].sum()/years)))
    return np.quantile(sim,[.025,.975]).tolist()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    cat,picks,days,O,C,V,R=source(a.root)
    policies,decisions,risk=strategies(cat,picks,C,R)
    decisions.to_csv(a.out/'GATE_MONTHLY_DECISIONS_ASOF.csv',index=False)
    risk.to_csv(a.out/'BETA_VOL_ASOF_AUDIT.csv',index=False)
    scores=[];navs=[];ledgers=[]
    original=readzip(a.root/P_ECON,'PAIRED_V3_127_ECONOMIC_SCORECARD.csv')
    original=original[(original.market=='EU148')&(original.top_n==5)].set_index('segment')
    for bps in (10,25,50,100):
        for name,portfolio in policies.items():
            score,nav,ledger=account(name,portfolio,days,O,V,bps)
            scores.append(score);navs.append(nav);ledgers.append(ledger)
            if bps==10 and name in ('FULL','EQUITY'):
                old=float(original.loc[name,'cagr_eur'])
                assert abs(score['cagr']-old)<1e-10,(name,score['cagr'],old)
            print('CATEGORY_GATE_EU148',bps,name,score['cagr'],score['max_dd'],flush=True)
    s=pd.DataFrame(scores);n=pd.concat(navs,ignore_index=True);t=pd.concat(ledgers,ignore_index=True)
    s.to_csv(a.out/'CATEGORY_GATE_COST_SENSITIVITY.csv',index=False)
    n.to_csv(a.out/'CATEGORY_GATE_DAILY_NAV.csv',index=False)
    t.to_csv(a.out/'CATEGORY_GATE_MONTHLY_REBALANCES.csv',index=False)
    dates=sorted(picks['FULL'])+[days[-1]]
    monthly={name:n[(n.variant==name)&(n.fee_bps==10)].set_index('date').nav.reindex(dates).to_numpy() for name in policies}
    years=(days[-1]-days[0]).days/365.25
    rows=[]
    for first,second in [('EQUITY','FULL'),('REL_MOM_GATE','FULL'),
       ('EQUITY_BETA_MATCH_FULL','FULL'),('EQUITY_VOL_MATCH_FULL','FULL'),('REL_MOM_GATE','EQUITY')]:
        x=monthly[first][1:]/monthly[first][:-1]-1
        y=monthly[second][1:]/monthly[second][:-1]-1
        aa=float(s[(s.variant==first)&(s.fee_bps==10)].cagr.iloc[0])
        bb=float(s[(s.variant==second)&(s.fee_bps==10)].cagr.iloc[0])
        row=dict(first=first,second=second,delta_cagr_pp=(aa-bb)*100)
        for k in (3,6,12):
            lo,hi=bootstrap(x,y,years,block=k)
            row[f'block{k}_ci95_low_pp']=lo;row[f'block{k}_ci95_high_pp']=hi
        rows.append(row)
    pd.DataFrame(rows).to_csv(a.out/'PAIRED_BLOCK_BOOTSTRAP_10BPS.csv',index=False)
    (a.out/'MANIFEST.json').write_text(json.dumps(dict(
       test='EU148 frozen native V3 127 decision categories',months=101,daily_marks=2076,
       features='original V3 source only',retrained=False,fee_bps=[10,25,50,100],
       ex_ante_gate='126 session momentum > EXSA and 21 session momentum positive',
       ex_ante_risk='126 session daily OLS beta and volatility, cash clipping [0,1]',
       exact_baseline_replay_verified=True,
       limitations=['selection discovered on previously viewed historical OOS',
           'venue-reported zero volume trades cannot be certified',
           'beta match infeasible when full beta higher than all-equity beta',
           'no FX spread for US, no risk-free return on EUR cash',
           '2026 universe survivorship bias',
           'risk overlays not fitted or validated'],status='EXPLORATORY_NOT_PRODUCTION'),indent=2))
    print('CATEGORY_POLICY_FINAL_PASS',s[s.fee_bps==10].to_string(index=False),flush=True)
    print('CATEGORY_POLICY_REPLACEMENTS',int(risk.replaced.sum()),'MATCH_BETA_GAP_AVG',
          float(risk.beta_residual.abs().mean()),flush=True)
if __name__=='__main__':main()
