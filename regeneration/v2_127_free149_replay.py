#!/usr/bin/env python3
"""True free-149 replay of frozen ETF Trader V2 XGBRanker 127 leaves.

Inputs are source-only OHLCV and archived walk-forward predictions; no refit.
The unrestricted book is ONE 149-ETF candidate universe, not 500 baskets.
A two-name implementation must be byte-to-float equivalent to original engine.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'regeneration'/'campaign'))
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.source_only.execution import replay as canonical_replay

OFFICIAL_SHA='36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e'

def replay_free149(scores,mats,weights,legacy=False):
    dates=mats['Open'].index;cols=list(mats['Open'].columns)
    arr=scores.pivot(index='signal_date',columns='ticker',values='score').reindex(columns=cols)
    sched={}
    for dt,row in arr.iterrows():
        pos=int(dates.searchsorted(dt,side='right'))
        if pos>=len(dates):continue
        values=row.to_numpy(float)
        if not np.isfinite(values).all():raise RuntimeError('Incomplete 149-score signal')
        picks=np.argsort(-values,kind='stable')[:len(weights)]
        w=np.array(weights,float)
        if legacy:
            w=np.array([1.,0.]) if values[picks[0]]-values[picks[1]]>=.12 else np.array([.75,.25])
        W=np.zeros((1,len(cols)),float);W[0,picks]=w
        sched[pos]=W
    start_i=int(dates.searchsorted(pd.Timestamp('2017-02-01')))
    end_i=int(dates.searchsorted(pd.Timestamp('2026-07-01'),side='right')-1)
    O=mats['Open'].to_numpy(float)
    units=np.zeros((1,len(cols)));cash=np.ones(1)
    lastdesired=np.zeros_like(units);target=np.zeros_like(units)
    equity=[];turnovers=[];index=[]
    for i in range(start_i,end_i):
        prices=O[i];bad=~np.isfinite(prices)|(prices<=0)
        if ((units>0)&bad[None,:]).any():raise RuntimeError('Missing held open')
        p=np.where(bad,0.,prices);value=cash+units@p
        if i in sched:target=sched[i].copy()
        desired=target.copy()
        changed=np.max(np.abs(desired-lastdesired),axis=1)>1e-12
        if (desired[:,bad]>0).any():raise RuntimeError('Missing selected open')
        after=value.copy()
        for _ in range(10):
            traded=np.abs(desired*after[:,None]-units*p[None,:]).sum(axis=1)
            after=np.where(changed,value-.001*traded,value)
        turnover=np.where(changed,traded/value,0.)
        safe=np.where(bad,1.,prices)
        units=np.where(changed[:,None],desired*after[:,None]/safe[None,:],units)
        cash=np.where(changed,after*(1-desired.sum(axis=1)),cash)
        nextp=O[i+1];badnext=~np.isfinite(nextp)|(nextp<=0)
        if ((units>0)&badnext[None,:]).any():raise RuntimeError('Missing next open')
        equity.append((cash+units@np.where(badnext,0,nextp))[0])
        turnovers.append(turnover[0]);index.append(dates[i+1])
        lastdesired=desired
    return pd.DatetimeIndex(index),np.array(equity,float),np.array(turnovers,float)

def summarize(dates,e,tr):
    n=len(e);peaks=np.maximum.accumulate(np.r_[1,e])[1:]
    first=int(np.searchsorted(dates.to_numpy(),np.datetime64('2018-02-02')))
    return dict(cagr_full=float(e[-1]**(252/n)-1),
        cagr_invested=float(e[-1]**(252/(n-first))-1),
        maxdd=float((e/peaks-1).min()),
        turnover_year=float(tr.sum()*252/n),
        terminal_nav=float(e[-1]))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--raw',default='etf_trader_raw')
    p.add_argument('--components',default='runs/v2_127_direct_components/FROZEN_COMPONENTS.csv')
    p.add_argument('--baskets',default='regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv')
    p.add_argument('--out',default='runs/v2_127_free149')
    a=p.parse_args()
    if hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()!=OFFICIAL_SHA:
        raise RuntimeError('Official 500 basket provenance failed')
    z=pd.read_csv(a.components,parse_dates=['signal_date'],float_precision='round_trip')
    if len(z)!=15198 or z.signal_date.nunique()!=102 or z.ticker.nunique()!=149:
        raise RuntimeError('Frozen 127-leaf OOS rows expected 102x149')
    cats, metadata = None, None
    mats,cats,metadata=load_ticker_csv_folder(a.raw)
    if len(cats)!=149:raise RuntimeError('Raw universe must be 149 ETF')
    mats={k:v.loc[v.index>=pd.Timestamp(2011,1,1)] for k,v in mats.items()}
    if z.duplicated(['signal_date','ticker']).any():raise RuntimeError('Duplicated OOS prediction')
    dates=pd.DatetimeIndex(sorted(z.signal_date.unique()))
    def scores(tw,macro):
        p=z[['signal_date','ticker']].copy()
        initial=(1-tw)*z.raw_rank+tw*z.tail_rank+macro*z.macro_fired
        p['score']=initial.groupby(z.signal_date).rank(pct=True)
        return p
    frozen=z[['signal_date','ticker','score']].copy()
    actual=scores(.3,.15).sort_values(['signal_date','ticker'])
    check=frozen.sort_values(['signal_date','ticker'])
    if np.max(np.abs(actual.score.to_numpy()-check.score.to_numpy()))>1e-12:
        raise RuntimeError('Score parity with frozen 127 fails')
    xgb=scores(0.,0.);pure_tail30=scores(.3,0.)
    cfg=[
        ('V2_legacy',frozen,[.75,.25],True),
        ('V2_top3_equal',frozen,[1/3]*3,False),
        ('V2_top5_equal',frozen,[.2]*5,False),
        ('XGB_top1',xgb,[1.],False),
        ('XGB_top2_equal',xgb,[.5,.5],False),
        ('XGB_top3_equal',xgb,[1/3]*3,False),
        ('XGB_top4_equal',xgb,[.25]*4,False),
        ('XGB_top5_equal',xgb,[.2]*5,False),
        ('XGB_top10_equal',xgb,[.1]*10,False),
        ('Tail30_Macro0_top3_equal',pure_tail30,[1/3]*3,False),
    ]
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    rows=[];navs={};turns={}
    for name,signal,w,legacy in cfg:
        dt,e,t=replay_free149(signal,mats,w,legacy)
        rows.append({'strategy':name,**summarize(dt,e,t)})
        navs[name]=e;turns[name]=t
        if name in ('V2_legacy','XGB_top2_equal'):
            refdt,refe,reft=canonical_replay(signal,mats,[sorted(cats)],threshold=.12 if legacy else 999.,
                                          top_weight=.75 if legacy else .5,cost=.001,risk=False)
            if not dt.equals(refdt) or np.max(np.abs(refe[0]-e))>1e-10 or np.max(np.abs(reft[0]-t))>1e-10:
                raise RuntimeError('Free-149 replay not equal to official engine: '+name)
            print('CANONICAL_ENGINE_PARITY_PASS',name,flush=True)
        print('FREE149_RESULT',name,rows[-1],flush=True)
    pd.DataFrame(rows).to_csv(out/'UNRESTRICTED_149_RESULTS.csv',index=False)
    pd.DataFrame(navs,index=dt).to_csv(out/'UNRESTRICTED_149_NAV.csv',index_label='date')
    pd.DataFrame(turns,index=dt).to_csv(out/'UNRESTRICTED_149_TURNOVER.csv',index_label='date')
    summary={'status':'SUCCESS','source_only':True,'etfs':149,
        'basket_sha256_validated':OFFICIAL_SHA,'frozen_scores_not_refit':True,
        'gross_exposure':1.,'risk_control_enabled':False,'fee':.001,
        'effective_first_entry':'2018-02-01','last_valuation':'2026-07-01',
        'original_engine_top2_parity':True,
        'historical_model_selection_warning':True,'results':rows}
    (out/'RESULT.json').write_text(json.dumps(summary,indent=2))
    print('FREE149_COMPLETE',json.dumps(rows),flush=True)

if __name__=='__main__':main()
