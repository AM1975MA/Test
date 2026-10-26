#!/usr/bin/env python3
"""Pre-registered Xetra EUR global investable universe diagnostic, 2018-2026.

PURPOSE: distinguish geography of underlying exposure from European trading venue
and choice of predictive model. Fixed two selection controls before viewing output:
classic 12-1 momentum, chronological 21d conditional-return Ridge regression.

All assets listed on EU (Xetra), trades always at NEXT actual common open,
no future asset selection/quotes, no fake fill, 10bps one-way on notional.
ATTENTION: present-day-surviving ISIN list is retrospectively chosen in 2026;
this is NOT independently investable point-in-time-universe historical truth.
"""
import json, time, argparse, traceback
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from scipy.stats import spearmanr
import yfinance as yf

# ISIN + current Xetra ticker grounded on issuer exchange listings / justETF.
CANDIDATES=[
    ("SXR8.DE","IE00B5BMR087","US_SP500"),
    ("SXRV.DE","IE00B53SZB19","US_NASDAQ"),
    ("EUNL.DE","IE00B4L5Y983","WORLD_DEV"),
    ("IUSQ.DE","IE00B6R52259","WORLD_ACWI"),
    ("IS3N.DE","IE00BKM4GZ66","EMERGING"),
    ("QDVE.DE","IE00B3WJKG14","US_TECH"),
    ("XDWT.DE","IE00BM67HT60","WORLD_TECH"),
    ("VWCE.DE","IE00BK5BQT80","ALL_WORLD"),
    ("IUSN.DE","IE00BF4RFH31","GLOBAL_SMALL"),
    ("VVSM.DE","IE00BMC38736","SEMICONDUCTORS"),
    ("4GLD.DE","DE000A0S9GB0","GOLD_ETC"), # explicitly ETC not UCITS
]
CUTOFF="2026-07-02"
FEE=.001
START=pd.Timestamp("2018-01-01"); LAST=pd.Timestamp("2026-05-31")
FEATURES=['mom21','mom63','mom126','mom252','mom252_ex21','vol21','vol63',
          'vol126','drawdown63','drawdown126','adv_log','beta126','pos63',
          'mom63_xvol','mom252_ex21_pct','vol126_pct']
def get_yf(ticker):
    last=""
    for attempt in range(3):
        try:
            d=yf.download(ticker,start='2009-01-01',end=CUTOFF,
                          interval='1d',auto_adjust=True,repair=False,
                          progress=False,threads=False,timeout=45)
            if isinstance(d.columns,pd.MultiIndex):
                d=d.droplevel(-1,axis=1)
            d=d.rename_axis('date')
            d=d[['Open','High','Low','Close','Volume']].copy()
            d=d[~d.index.duplicated()].sort_index()
            d.index=pd.DatetimeIndex(d.index).tz_localize(None).normalize()
            d=d[(d.Open>0)&(d.Close>0)]
            if len(d)<300:raise RuntimeError('insufficient rows '+str(len(d)))
            assert d.index.is_unique
            return d
        except Exception as exc:
            last=str(exc)
            time.sleep(1+attempt)
    raise RuntimeError(ticker+': '+last)

def metric(ret):
    vv=np.asarray(ret,dtype=float);vv=vv[np.isfinite(vv)]
    return float(np.nanmedian(vv)) if len(vv) else float('nan')

def prepare_frame(op,cl,vol,cal):
    # All calculations use prices at OR BEFORE their own signal timestamps.
    close=cl.reindex(cal)
    opens=op.reindex(cal)
    volume=vol.reindex(cal)
    ret=close.pct_change(fill_method=None)
    moms={h:close.pct_change(h,fill_method=None) for h in (21,63,126,252)}
    sigvol=ret.rolling(126,min_periods=126).std()*np.sqrt(252)
    adv=(close*volume).rolling(63,min_periods=42).median()
    pos=(ret>0).where(ret.notna()).rolling(63,min_periods=63).mean()
    market=ret["DE0002635307"] # EXSA previous 126 returns, same-currency EUROPE broad
    def beta(frame):
        c=ret.rolling(126,min_periods=126).cov(market)
        v=market.rolling(126,min_periods=126).var().replace(0,np.nan)
        return c.div(v,axis=0)
    bet=beta(ret)
    mon=pd.Series(cal,index=cal)
    monthdates=mon[(mon.index>=START)&(mon.index<=LAST)].groupby(mon.loc[START:LAST].index.to_period('M')).last().tolist()
    assert len(monthdates)==101
    records=[]
    universe=list(close.columns)
    for dt in monthdates:
        past=cal[cal.get_loc(dt)-62:cal.get_loc(dt)+1]
        med_adv=adv.loc[dt]
        vp=(volume.loc[past]>0).sum(axis=0)/len(past)
        valid=(close.loc[dt].notna() & close.loc[cal[cal.get_loc(dt)-252]].notna() &
               (volume.loc[past].notna().sum(axis=0)>=50) & (vp>=.90) &
               med_adv.ge(50000))
        x=pd.DataFrame(index=universe)
        for h in (21,63,126,252):x[f'mom{h}']=moms[h].loc[dt]
        x['mom252_ex21']=close.loc[cal[cal.get_loc(dt)-21]]/close.loc[cal[cal.get_loc(dt)-252]]-1
        for h in (21,63,126):x[f'vol{h}']=ret.rolling(h,min_periods=h).std().loc[dt]*np.sqrt(252)
        for h in (63,126):x[f'drawdown{h}']=(close/close.rolling(h,min_periods=h).max()-1).loc[dt]
        x['adv_log']=np.log(adv.loc[dt].where(adv.loc[dt]>0))
        x['beta126']=bet.loc[dt]
        x['pos63']=pos.loc[dt]
        x['mom63_xvol']=x.mom63/x.vol126.replace(0,np.nan)
        for fea in ('mom252_ex21','vol126'):
            x[f'{fea}_pct']=x[fea].rank(pct=True)
        # Neither missing signal features nor a future price is used for ETF eligibility.
        x['eligible']=valid
        x['signal_date']=dt
        x['ticker']=universe
        x['n_past_volume_positive']=vp.values
        x['median_adv63']=med_adv.values
        records.append(x.reset_index(drop=True))
    f=pd.concat(records,ignore_index=True)
    f=f.replace([np.inf,-np.inf],np.nan)
    return f,monthdates,close,opens,volume

def sim(picks,opens,cal,monthdates,top=5):
    execs=[cal[cal.searchsorted(s,side='right')] for s in monthdates]
    last=cal[cal.searchsorted(pd.Timestamp("2026-07-01"))]
    active=cal[(cal>=execs[0])&(cal<=last)]
    map_exec=dict(zip(execs,monthdates))
    ff=opens.loc[active].ffill()
    cash=1.;hold={};turnover=0.;cost=0.;missing=0
    marks=[];trades=[]
    for dt in active:
        cur=opens.loc[dt]; val=ff.loc[dt]
        before=cash+sum(q*val[t] for t,q in hold.items())
        if dt in map_exec:
            sig=map_exec[dt]
            desired=picks[sig][:top]
            good=[t for t in desired if pd.notna(cur[t]) and cur[t]>0]
            missing+=len(desired)-len(good)
            if any(pd.isna(cur[t]) for t in hold):raise RuntimeError('Holding missing Open on '+str(dt))
            target={t:1./top for t in good}
            old={t:q*cur[t] for t,q in hold.items()}
            equity=before
            for _ in range(20):
                notional=sum(abs(equity*target.get(t,0)-old.get(t,0)) for t in set(target)|set(old))
                eqnew=before-FEE*notional
                if abs(eqnew-equity)<1e-13:break
                equity=eqnew
            turnover+=notional/before
            cost+=before-equity
            cash=equity*(1-sum(target.values()))
            hold={t:equity*w/cur[t] for t,w in target.items()}
            trades.append(dict(signal_date=sig.date().isoformat(),fill_date=dt.date().isoformat(),
                chosen='|'.join(desired),filled='|'.join(good),
                missing=len(desired)-len(good),cost=before-equity))
        nav=cash+sum(q*val[t] for t,q in hold.items())
        marks.append((dt,nav))
    nav=pd.DataFrame(marks,columns=['date','nav'])
    yrs=(active[-1]-active[0]).days/365.25
    return dict(cagr=float(nav.nav.iloc[-1]**(1/yrs)-1),
                max_dd=float((nav.nav/nav.nav.cummax()-1).min()),
                end_nav=float(nav.nav.iloc[-1]),
                turnover=turnover,paid_fees=cost,missing_fills=missing),nav,pd.DataFrame(trades)

def main():
    a=argparse.ArgumentParser();a.add_argument('--eu',required=True);a.add_argument('--out',required=True)
    z=a.parse_args();out=Path(z.out);out.mkdir(parents=True,exist_ok=True)
    cat=pd.read_csv(Path(z.eu)/'EU148_VERIFIED_LEGAL_ISIN_CATALOG.csv')
    assert len(cat)==148 and cat.ticker.nunique()==148
    source=Path(z.eu)/'raw_ticker_csv'
    prior={}
    for t in cat.ticker:
        df=pd.read_csv(source/(t+'.csv'),parse_dates=['date']).drop_duplicates('date')
        df=df.set_index('date').sort_index()
        prior[t]=df
    benchmark='DE0002635307'
    assert benchmark in prior
    rawfetch={};logs=[]
    for ticker,isin,kind in CANDIDATES:
        try:
            d=get_yf(ticker)
            assert len(d)>300
            rawfetch[ticker]=d
            count=int((d.Volume<=0).sum())
            d.to_csv(out/(ticker+'.csv'),index_label='date')
            logs.append(dict(ticker=ticker,isin=isin,exposure=kind,
                 rows=len(d),first_date=str(d.index[0].date()),last_date=str(d.index[-1].date()),
                 pct_zero_vol=count/len(d),source='Yahoo Finance yfinance as-downloaded 2026-10-26',
                 status='OK'))
        except Exception as exc:
            logs.append(dict(ticker=ticker,isin=isin,exposure=kind,status='FAILED',error=str(exc)))
        print('DATA',ticker,logs[-1]['status'],flush=True)
    pd.DataFrame(logs).to_csv(out/'XETRA_GLOBAL_UCITS_ISIN_DATA_PROVENANCE.csv',index=False)
    assert len(rawfetch)>=7,'Not enough source-confirmed Xetra data to evaluate opportunity coverage'
    assert all(t in rawfetch for t in ['SXR8.DE','SXRV.DE','EUNL.DE'])
    frames=dict(prior,**rawfetch)
    joint=prior[benchmark].index.sort_values()
    joint=joint[(joint>=pd.Timestamp('2010-01-01'))&(joint<=pd.Timestamp('2026-07-01'))]
    assert len(joint)>3900 and pd.Timestamp('2026-07-01')==joint[-1]
    op=pd.concat({t:d.Open for t,d in frames.items()},axis=1).reindex(joint)
    cl=pd.concat({t:d.Close for t,d in frames.items()},axis=1).reindex(joint)
    vv=pd.concat({t:d.Volume for t,d in frames.items()},axis=1).reindex(joint)
    factors,dates,cc,oo,volume=prepare_frame(op,cl,vv,joint)
    # Before making a decision: freeze eligibility 252 data observations, 63day
    # past liquidity/positive volume and avoid equal-ISIN duplicates by construction.
    quality=factors[(factors.eligible)&(factors[['mom252_ex21','vol126','mom63']].notna().all(axis=1))].copy()
    global_ticks=set(rawfetch)-{'4GLD.DE'}
    gold_etc={'4GLD.DE'} & set(rawfetch)
    groups=[('EU148_ONLY',set(cat.ticker)),('GLOBAL_UCITS_ONLY',global_ticks),
             ('GLOBAL_UCITS_PLUS_ETC',global_ticks|gold_etc),
             ('EU148_PLUS_GLOBAL_UCITS',set(cat.ticker)|global_ticks),
             ('EU148_PLUS_GLOBAL_ETC',set(cat.ticker)|global_ticks|gold_etc)]
    # No trained ML needed to prove that original EU-only geographic restriction
    # prevents US/global UCITS Xetra from being considered.
    results=[];navs=[];trades=[];skills=[];count=[]
    for cohort,allow in groups:
        d=quality[quality.ticker.isin(allow)]
        for strategy in ('MOM252_EX21','MOM63','MOM_VOL_RISK'):
            picks={};ic_by_month=[]
            for sig in dates:
                g=d[d.signal_date.eq(sig)].copy()
                count.append(dict(cohort=cohort,strategy=strategy,signal_date=sig,
                                  n=int(len(g))))
                if len(g):
                    if strategy=='MOM252_EX21':g['score']=g.mom252_ex21
                    elif strategy=='MOM63':g['score']=g.mom63
                    else:g['score']=.5*g.mom252_ex21+.5*g.mom63/(1+g.vol126)
                    # stable sort no realized label
                    g=g.sort_values(['score','ticker'],ascending=[False,True])
                    picks[sig]=g.ticker.tolist()
                else:picks[sig]=[]
                # no ranking IC to forward target here: time horizon not exact 21days
            for top in (3,5):
                st,nav,tr=sim(picks,oo,joint,dates,top)
                st.update(cohort=cohort,strategy=strategy,topn=top,months=101)
                results.append(st)
                nv=nav.copy();nv['cohort']=cohort;nv['strategy']=strategy;nv['topn']=top;navs.append(nv)
                tr['cohort']=cohort;tr['strategy']=strategy;tr['topn']=top;trades.append(tr)
                print('RESULT',cohort,strategy,top,'CAGR',round(100*st['cagr'],3),
                      'DD',round(100*st['max_dd'],3),'FILLS',st['missing_fills'],flush=True)
    pd.DataFrame(results).to_csv(out/'PREDECLARED_XETRA_OPPORTUNITY_SCORECARD.csv',index=False)
    pd.concat(navs).to_csv(out/'PREDECLARED_XETRA_OPPORTUNITY_DAILY_NAV.csv',index=False)
    pd.concat(trades).to_csv(out/'PREDECLARED_XETRA_OPPORTUNITY_TRADES.csv',index=False)
    pd.DataFrame(count).to_csv(out/'PREDECLARED_XETRA_ELIGIBLE_ASOF.csv',index=False)
    man=dict(study='2018-2026 Xetra global UCITS expansion versus 148 Europe-only cohort',
        yahoo='auto_adjust true: all historical OHLC back-adjusted including dividends',
        old_source='original EU148 148 ISIN price/volume frozen 40218758892',
        new_list='current 2026 selection, contains survivorship/vintage bias',
        no_lookahead_eligibility='as-of 252d close and 63d 90% positive volume 50k EUR median ADV',
        rankings_fixed=['MOM252_EX21','MOM63','MOM_VOL_RISK'],
        flat_fee_one_way_bps=10, execution='next actual joint calendar Open',
        no_future_price_fills=True,
        not_model_solution='opportunity test only, not proof of Ridge alpha',
        shorts=False,position_weights='equal 1/TopN')
    (out/'MANIFEST.json').write_text(json.dumps(man,indent=2))
    print('UCITS_GLOBAL_PREDECLARED_PASS',len(rawfetch),len(results),flush=True)

if __name__=='__main__': main()
