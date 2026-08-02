#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import time
import traceback
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

OUT = Path(os.environ.get('TITANIUM_OUT', 'titanium_global150_live_output'))
OUT.mkdir(parents=True, exist_ok=True)
START_DOWNLOAD = '2005-01-01'
START_BACKTEST = pd.Timestamp('2017-01-03')
END_EXCLUSIVE = (pd.Timestamp.utcnow().normalize() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
COSTS_BPS = [0, 10, 25, 50]
PRIMARY_COST_BPS = 10
MIN_HISTORY = 252

ETF_UNIVERSE = OrderedDict({
'C01_US_BROAD_STYLE': ['DIA','IJR','SCHD','QQQ','QUAL','RSP','DGRO','IJH','IWF','HDV','MDY','SCHB','IWM','MTUM','SCHX','SPY','IVV','VTI','VO','VB','VUG','VTV','IWD','IWN','SPLV'],
'C02_US_SECTOR_THEME': ['PPA','SMH','SOXX','IGV','IHI','KBE','HACK','IYT','KRE','IBB','ICLN','ITA','FDN','TAN','XBI','XLK','XLF','XLE','XLV','XLI','XLY','XLP','XLU','XLB','XRT'],
'C03_DEVELOPED_GLOBAL': ['ACWI','EWL','EWP','EWA','EWN','IEFA','EFA','EWH','EWQ','EWC','EWD','EWJ','EWG','EWI','EWU','VEA','VEU','VGK','EWK','EWO','EIRL','EIS','EPOL','ENZL','EPP'],
'C04_EMERGING': ['EWS','EWY','FXI','ASHR','INDA','VWO','EWT','IEMG','KWEB','EEM','MCHI','TUR','AAXJ','EWZ','EZA','EIDO','EWM','THD','EPHE','SCHE','DEM','DGS','EPI','PIN','ARGT'],
'C05_BONDS_CASH_CREDIT': ['AGG','BIL','EMB','IEF','IEI','LQD','BNDX','HYG','MUB','BND','JNK','SCHP','EDV','SHY','TLT','TIP','SHV','VGSH','VGIT','VGLT','VCIT','VCSH','MBB','BKLN','ANGL'],
'C06_REAL_ASSETS': ['COMT','GLD','SLV','GSG','IYR','PPLT','CPER','DBB','VNQ','DBC','GDX','PALL','BNO','DBA','GDXJ','IAU','USO','UNG','DBO','USL','RWO','RWX','WOOD','CORN','URA'],
})
TICKERS = [t for xs in ETF_UNIVERSE.values() for t in xs]
assert len(TICKERS) == 150 and len(set(TICKERS)) == 150


def download_prices():
    print(f'Download {len(TICKERS)} ETF: {START_DOWNLOAD} -> {END_EXCLUSIVE}')
    pieces, log = [], []
    for i in range(0, len(TICKERS), 20):
        chunk = TICKERS[i:i+20]
        print(f'  batch {i//20+1}: {chunk}')
        try:
            raw = yf.download(chunk, start=START_DOWNLOAD, end=END_EXCLUSIVE,
                              auto_adjust=False, actions=False, repair=False,
                              progress=False, threads=True, group_by='ticker',
                              timeout=60, multi_level_index=True)
        except Exception as e:
            raw = pd.DataFrame(); print('batch error', repr(e))
        for t in chunk:
            try:
                if raw.empty: raise ValueError('empty batch')
                if isinstance(raw.columns, pd.MultiIndex):
                    if t in raw.columns.get_level_values(0): x = raw[t].copy()
                    elif t in raw.columns.get_level_values(1): x = raw.xs(t, axis=1, level=1).copy()
                    else: raise KeyError(t)
                else: x = raw.copy() if len(chunk)==1 else pd.DataFrame()
                x.index = pd.to_datetime(x.index).tz_localize(None)
                x = x[~x.index.duplicated(keep='last')].sort_index()
                col = 'Adj Close' if 'Adj Close' in x.columns else 'Close'
                s = pd.to_numeric(x[col], errors='coerce').rename(t).dropna()
                if len(s)<50: raise ValueError(f'only {len(s)} rows')
                pieces.append(s)
                log.append({'ticker':t,'status':'SUCCESS','rows':len(s),'first':s.index.min(),'last':s.index.max(),'error':''})
            except Exception as e:
                log.append({'ticker':t,'status':'FAILED','rows':0,'first':None,'last':None,'error':repr(e)})
        time.sleep(0.5)
    prices = pd.concat(pieces, axis=1).sort_index() if pieces else pd.DataFrame()
    failed = [r['ticker'] for r in log if r['status']=='FAILED']
    if failed: print('single retries:', failed)
    for t in failed:
        try:
            x = yf.download(t, start=START_DOWNLOAD, end=END_EXCLUSIVE,
                            auto_adjust=False, actions=False, repair=False,
                            progress=False, threads=False, timeout=60,
                            multi_level_index=False)
            x.index = pd.to_datetime(x.index).tz_localize(None)
            col = 'Adj Close' if 'Adj Close' in x.columns else 'Close'
            s = pd.to_numeric(x[col], errors='coerce').rename(t).dropna()
            if len(s)>=50:
                prices[t]=s
                for r in log:
                    if r['ticker']==t:
                        r.update(status='SUCCESS_RETRY',rows=len(s),first=s.index.min(),last=s.index.max(),error=''); break
        except Exception as e:
            for r in log:
                if r['ticker']==t: r['error'] += ' | retry=' + repr(e); break
    prices = prices.sort_index().loc[:,~prices.columns.duplicated()]
    req = pd.DataFrame([(cat,t) for cat,ts in ETF_UNIVERSE.items() for t in ts], columns=['category','ticker'])
    return prices,pd.DataFrame(log),req


def pct_rank_row(df):
    return df.rank(axis=1,pct=True,method='average')


def build_features(prices):
    r21=prices.pct_change(21); r63=prices.pct_change(63); r126=prices.pct_change(126)
    r252_21=prices.shift(21)/prices.shift(252)-1.0
    vol63=prices.pct_change().rolling(63).std()*np.sqrt(252)
    sma200=prices.rolling(200).mean(); dd126=prices/prices.rolling(126).max()-1.0
    accel=r21-(prices.shift(21)/prices.shift(42)-1.0)
    base=(0.34*pct_rank_row(r252_21)+0.24*pct_rank_row(r126)+0.20*pct_rank_row(r63)+
          0.10*pct_rank_row(r21)+0.07*(1-pct_rank_row(vol63))+0.05*pct_rank_row(dd126))
    base=base-0.12*(1-(prices>sma200).astype(float))
    opp=0.45*pct_rank_row(r21)+0.30*pct_rank_row(r63)+0.15*pct_rank_row(accel)+0.10*pct_rank_row(dd126)
    return {'base':base,'opp':opp}


def signal_dates(prices):
    idx=prices.index[prices.index>=START_BACKTEST]
    return pd.DatetimeIndex(pd.Series(idx,index=idx).groupby(idx.to_period('M')).max().values)


def make_targets(prices,feats):
    sdates=signal_dates(prices); cols=prices.columns
    targets={n:pd.DataFrame(0.0,index=sdates,columns=cols) for n in ['BASE','ROUTER_DIRECT','ROUTER_CAUSAL']}
    diagnostics=[]; shadow_excess=[]
    for k,d in enumerate(sdates[:-1]):
        available=prices.loc[:d].notna().sum()>=MIN_HISTORY
        scores=feats['base'].loc[d].where(available).dropna().sort_values(ascending=False)
        opps=feats['opp'].loc[d].where(available).dropna().sort_values(ascending=False)
        if len(scores)<2: continue
        t1,t2=scores.index[:2]; margin=float(scores.iloc[0]-scores.iloc[1])
        w1,w2=(1.0,0.0) if margin>=0.12 else (0.75,0.25)
        targets['BASE'].loc[d,t1]=w1
        if w2: targets['BASE'].loc[d,t2]=w2
        opp_rank=int(opps.index.get_loc(t1))+1 if t1 in opps.index else 999
        opp_gap=float(opps.loc[t1]-opps.iloc[1]) if t1 in opps.index and len(opps)>1 else -999.0
        direct=margin<0.12 and opp_rank<=3 and opp_gap>=0.03
        targets['ROUTER_DIRECT'].loc[d]=targets['BASE'].loc[d]
        if direct:
            targets['ROUTER_DIRECT'].loc[d]=0.0; targets['ROUTER_DIRECT'].loc[d,t1]=1.0
        router_on=len(shadow_excess)>=12 and np.nansum(shadow_excess[-12:])>0
        targets['ROUTER_CAUSAL'].loc[d]=targets['BASE'].loc[d]
        if direct and router_on:
            targets['ROUTER_CAUSAL'].loc[d]=0.0; targets['ROUTER_CAUSAL'].loc[d,t1]=1.0
        nd=sdates[k+1]
        ret1=prices.loc[nd,t1]/prices.loc[d,t1]-1 if pd.notna(prices.loc[nd,t1]) and pd.notna(prices.loc[d,t1]) else np.nan
        ret2=prices.loc[nd,t2]/prices.loc[d,t2]-1 if pd.notna(prices.loc[nd,t2]) and pd.notna(prices.loc[d,t2]) else np.nan
        rb=w1*ret1+w2*ret2 if pd.notna(ret1) and (w2==0 or pd.notna(ret2)) else np.nan
        rd=ret1 if direct else rb
        shadow_excess.append(float(np.log1p(rd)-np.log1p(rb)) if pd.notna(rd) and pd.notna(rb) and rd>-1 and rb>-1 else 0.0)
        diagnostics.append({'signal_date':d,'top1':t1,'top2':t2,'margin':margin,'base_w1':w1,'opp_rank_top1':opp_rank,'opp_gap':opp_gap,'direct_condition':direct,'router_on':router_on,'shadow_excess_12m':np.nansum(shadow_excess[-12:]),'eligible':len(scores)})
    return targets,pd.DataFrame(diagnostics)


def run_monthly(prices,target,cost_bps,governor):
    sdates=target.index; vals=[1.0]; out_dates=[sdates[0]]; prev=pd.Series(0.0,index=prices.columns)
    spy=prices['SPY'] if 'SPY' in prices else prices.median(axis=1)
    sma=spy.rolling(200).mean(); dd=spy/spy.rolling(126).max()-1
    for k,d in enumerate(sdates[:-1]):
        nd=sdates[k+1]; w=target.loc[d].copy(); scale=1.0
        if governor:
            if pd.notna(spy.loc[d]) and pd.notna(sma.loc[d]) and spy.loc[d]<sma.loc[d]: scale=0.5
            if pd.notna(dd.loc[d]) and dd.loc[d]<-0.15: scale=0.25
            if pd.notna(dd.loc[d]) and dd.loc[d]<-0.25: scale=0.0
        w*=scale; turnover=float((w-prev).abs().sum()); cost=turnover*cost_bps/10000.0
        rr=(prices.loc[nd]/prices.loc[d]-1).replace([np.inf,-np.inf],np.nan).fillna(0.0)
        vals.append(vals[-1]*(1+float((w*rr).sum())-cost)); out_dates.append(nd); prev=w
    return pd.Series(vals,index=pd.DatetimeIndex(out_dates))


def metrics(eq):
    eq=eq.dropna(); r=eq.pct_change().dropna(); years=(eq.index[-1]-eq.index[0]).days/365.25
    cagr=eq.iloc[-1]**(1/years)-1 if years>0 else np.nan; dd=eq/eq.cummax()-1; mdd=float(dd.min())
    return {'start':eq.index[0],'end':eq.index[-1],'months':len(r),'cagr':cagr,'maxdd':mdd,'sharpe':np.sqrt(12)*r.mean()/r.std(ddof=1) if r.std(ddof=1)>0 else np.nan,'calmar':cagr/abs(mdd) if mdd<0 else np.nan,'final_equity':eq.iloc[-1]}


def main():
    try:
        prices,logdf,req=download_prices()
        prices.to_parquet(OUT/'ADJ_CLOSE_DOWNLOADED.parquet',compression='zstd'); logdf.to_csv(OUT/'DOWNLOAD_LOG.csv',index=False); req.to_csv(OUT/'REQUESTED_UNIVERSE.csv',index=False)
        if prices.empty or prices.shape[1]<40: raise RuntimeError(f'Insufficient downloaded universe: {prices.shape}')
        targets,diag=make_targets(prices,build_features(prices)); diag.to_csv(OUT/'MONTHLY_DIAGNOSTICS.csv',index=False)
        rows=[]; curves={}
        periods=[('FULL','2017-01-01','2099-12-31'),('D1','2017-01-01','2019-12-31'),('D2','2020-01-01','2022-12-31'),('HOLD','2023-01-01','2099-12-31')]
        for cost in COSTS_BPS:
            for name,t in targets.items():
                for gov in [False,True]:
                    strat=name+('_GOV' if gov else ''); eq=run_monthly(prices,t,cost,gov); curves[(strat,cost)]=eq
                    for period,start,end in periods:
                        z=eq[(eq.index>=start)&(eq.index<=end)]
                        if len(z)>=3: rows.append({'strategy':strat,'cost_bps_one_way':cost,'period':period,**metrics(z/z.iloc[0])})
        sd=signal_dates(prices); spy=prices['SPY'].reindex(sd).dropna(); spy=spy/spy.iloc[0]
        for period,start,end in periods:
            z=spy[(spy.index>=start)&(spy.index<=end)]
            if len(z)>=3: rows.append({'strategy':'SPY','cost_bps_one_way':0,'period':period,**metrics(z/z.iloc[0])})
        score=pd.DataFrame(rows); score.to_csv(OUT/'SCORECARD.csv',index=False)
        prim=score[(score.cost_bps_one_way==PRIMARY_COST_BPS)&(score.period=='FULL')].sort_values('cagr',ascending=False); prim.to_csv(OUT/'PRIMARY_10BPS_FULL.csv',index=False)
        curve_df=pd.DataFrame({k[0]:v for k,v in curves.items() if k[1]==PRIMARY_COST_BPS}); curve_df['SPY']=spy; curve_df.to_csv(OUT/'EQUITY_CURVES_10BPS.csv')
        weights=[]
        for name,t in targets.items():
            for d,row in t.iterrows():
                for ticker,w in row[row>0].items(): weights.append({'strategy':name,'signal_date':d,'ticker':ticker,'weight':w})
        pd.DataFrame(weights).to_csv(OUT/'MONTHLY_TARGETS.csv',index=False)
        info={'created_utc':pd.Timestamp.utcnow().isoformat(),'test':'Titanium-inspired unrestricted global universe','requested_tickers':150,'downloaded_tickers':int(prices.shape[1]),'backtest_start':'2017-01-03','data_end':str(prices.index.max().date()),'price_field':'Yahoo Adj Close','execution':'month-end close-to-next-month-end close approximation','costs_bps_one_way':COSTS_BPS,'adaptive_concentration_threshold':0.12,'router':'causal trailing 12 completed months of direct-vs-base shadow log excess','governor':'SPY SMA200 and 126d drawdown exposure scaling','survivorship_bias':True,'not_frozen_titanium':True}
        (OUT/'CONFIG.json').write_text(json.dumps(info,indent=2,default=str))
        lines=['# Titanium-inspired Global150 live-data test','','New-data diagnostic; not a faithful frozen Titanium replication.','','## 10 bp one-way, full period','',prim[['strategy','cagr','maxdd','sharpe','calmar','final_equity']].to_markdown(index=False,floatfmt='.4f'),'','## Data',f'- Requested ETF: 150',f'- Downloaded ETF: {prices.shape[1]}',f'- Period: {prices.index.min().date()} to {prices.index.max().date()}','- Monthly close-to-close approximation; adjusted prices; current-universe survivorship bias.','- Router retained and estimated causally from completed prior months.']
        (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    except Exception:
        (OUT/'ERROR.txt').write_text(traceback.format_exc()); raise
    finally:
        shutil.make_archive(str(OUT),'zip',root_dir=OUT)

if __name__=='__main__': main()
