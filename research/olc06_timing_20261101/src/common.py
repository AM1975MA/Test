"""Frozen local dependency and valuation-date accounting; no network or refit."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
VENDOR=ROOT/'vendor/olc05_transitions_20261031'
INPUT=VENDOR/'source/lifecycle_execution_20261031/inputs'
OUT=ROOT/'results'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(market,weight='HALF'):
    if market not in ('USA','EU') or weight not in ('HALF','ORIGINAL'):raise ValueError('Unknown scope')
    q=dict(np.load(INPUT/f'{market}_STATE_{weight}.npz',allow_pickle=False))
    dates=pd.DatetimeIndex(q['dates'])
    cal=pd.read_csv(INPUT/f'{market}_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date'])
    return q,np.asarray(dates.isin(cal.entry_date),bool),cal

def periods(dates):
    actual=pd.DatetimeIndex(dates)[1:]
    p={'FULL':(actual[0],actual[-1]),'PRE2025':('2019-02-01','2024-12-31'),
       'ACTIVE2021_2024':('2021-01-01','2024-12-31'),'CRASH2020':('2020-02-01','2020-03-31'),
       'LATE2021_2023':('2021-11-01','2023-12-31')}
    p.update({str(y):(f'{y}-01-01',f'{y}-12-31') for y in range(2019,2027)})
    return {k:(pd.Timestamp(a),pd.Timestamp(b)) for k,(a,b) in p.items()}

def metrics(q,r):
    ds=pd.DatetimeIndex(q['dates']); actual=ds[1:]
    log=np.diff(np.log(np.r_[1.,r['nav']]))[:-1]
    rows=[]
    for period,(lo,hi) in periods(ds).items():
        mask=(actual>=lo)&(actual<=hi)
        if mask.sum()<10:continue
        x=log[mask];eq=np.exp(x.cumsum());dd=eq/np.maximum.accumulate(np.r_[1.,eq])[1:]-1
        ll=r['ledger'][:-1][mask]
        rows.append(dict(period=period,first_valuation=str(actual[mask][0].date()),last_valuation=str(actual[mask][-1].date()),
             n=int(mask.sum()),cagr=float(np.expm1(x.mean()*252)),annual_log=float(x.mean()*252),period_return=float(np.expm1(x.sum())),
             maxdd=float(dd.min()),turnover_annual=float(ll[:,4].mean()*252),actual_risk_exposure=float(ll[:,12].mean()),
             mean_positions=float(ll[:,14].mean()),effective_positions=float(ll[:,15].mean()),stops=int(ll[:,8].sum()),
             blocked=int(ll[:,11].sum()),rebalances=int(ll[:,3].sum()),fee_drag_sum=float(np.sum(ll[:,5:8].sum(1)/ll[:,0])) ))
    return rows

def policy_args(strategy):
    return {'IMMEDIATE':dict(policy='IMMEDIATE'), 'DELAY3':dict(policy='DELAY',fraction=3),
            'PHASE5':dict(policy='PHASE',fraction=5)}[strategy].copy()
def mode_args(mode):return {'risk_on':mode!='RISKOFF','lag_systemic':mode=='LAG1'}
