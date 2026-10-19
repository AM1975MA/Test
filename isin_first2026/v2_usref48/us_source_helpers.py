"""Patch only external market-reference imports of original frozen US DD-first/V6.

48 European funds remain the only candidates. SPY HYG IEF signals taken from
immutable original USD OHLCV archive, never rewritten as IMEU/IHYG/EUNH.
US same-day official close enters source logic only after original .shift(1)
or V6's k-1 signal consumption, so cannot leak an unfinished US session into
a European morning. Defensive BIL/SHV separately handled as investible EUR
converted US ETF references when user chooses original foreign sleeve.
"""
from __future__ import annotations
import inspect
import pandas as pd,numpy as np
from etf_trader.ma3 import ddfirst,v6

def dd_reference_us_market(usd):
    s=inspect.getsource(ddfirst.market_state)
    before='spy=close["SPY"]'
    after='spy=US_REFERENCE["SPY"].reindex(close.index)'
    assert s.count(before)==1
    s=s.replace(before,after)
    before='hygief=close["HYG"]/close["IEF"]'
    after='hygief=US_REFERENCE["HYG"].reindex(close.index)/US_REFERENCE["IEF"].reindex(close.index)'
    assert s.count(before)==1
    s=s.replace(before,after)
    dd=dict(ddfirst.__dict__);dd["US_REFERENCE"]=usd
    namespace={}
    exec(compile(s,"<original_US_SPY_HYG_IEF_DD_first_external_europe48>","exec"),dd,namespace)
    return namespace["market_state"]

def v6_reference_us_market(usd_spy):
    # Original source V6 only needs SPY for "recovery" state. Use the
    # same original USD SPY Close aligned to its US calendar then mapped to
    # the European evaluation timestamps. V6 uses lagged t-1 state.
    s=inspect.getsource(v6.build_v6_state)
    keys={
      'spy=ti["SPY"]':'spy=-1  # SPY market reference external, never eligible',
      'spy5=ret[5][:,spy]':'spy5=US_SPY.reindex(close.index).pct_change(5,fill_method=None).to_numpy(float)',
      'spy200=C[:,spy]/ma200[:,spy]-1.0': 'spy200=(US_SPY.reindex(close.index)/US_SPY.reindex(close.index).rolling(200,min_periods=200).mean()-1).to_numpy(float)'
    }
    for b,a in keys.items():
        assert s.count(b)==1,(b,s.count(b))
        s=s.replace(b,a)
    env=dict(v6.__dict__);env["US_SPY"]=usd_spy
    namespace={}
    exec(compile(s,"<original_US_SPY_V6_recovery_external_europe48>","exec"),env,namespace)
    return namespace["build_v6_state"]

def extend_execution_us_defense(O,L,C,PC,gap,UH,SA,prior_on_eu,days):
    u=prior_on_eu.set_index("date").reindex(days)
    assert u.notna().all(axis=None)
    bille=u["BIL_EUR_OPEN_EST"].to_numpy(float)
    shve=u["SHV_EUR_OPEN_EST"].to_numpy(float)
    cash=np.column_stack([bille,shve])
    prev=np.vstack([cash[:1],cash[:-1]])
    dfgap=cash/prev-1
    result=dict(
       O=np.column_stack([O,cash]),
       L=np.column_stack([L,cash]),
       C=np.column_stack([C,cash]),
       PC=np.column_stack([PC,prev]),
       gap=np.column_stack([gap,dfgap]),
       UH=np.column_stack([UH,np.zeros_like(cash,dtype=bool)]),
       SA=np.column_stack([SA,np.zeros_like(cash,dtype=bool)]),
       bil=O.shape[1],
       shv=O.shape[1]+1)
    assert result["bil"]==48 and result["shv"]==49
    assert np.isfinite(result["O"]).all()
    return result
