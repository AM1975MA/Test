"""Explicit stop eligibility and fill assumptions. No fitting or thresholds search."""
from __future__ import annotations
import math
POLICIES=('LEGACY','PREVIOUS','PREVIOUS_UNIFORM','PREARM_WEAK','PREARM_ALL','EOD_LOW','EOD_CLOSE','NO_STOP','EOD_LOW_NET','EOD_CLOSE_NET')

def eligible(policy: str, weak: bool, market: bool) -> bool:
    if policy not in POLICIES: raise ValueError('Unknown stop policy')
    if policy=='NO_STOP': return False
    if policy=='PREARM_ALL': return True
    if policy=='PREARM_WEAK': return bool(weak)
    return bool(weak and market)

def fill(policy: str, opening: float, low: float, close: float, previous_close: float,
         next_open: float, observed: bool=True, low_observed: bool=True,
         next_observed: bool=True, friction: float|None=None) -> tuple[float,float,int]|None:
    """Return raw price, friction-adjusted price and0/1 session execution offset.

    EOD signals use the completed current bar; next_open is execution-only.
    Immediate stop prices are bar proxies, not guaranteed actual market fills.
    """
    if policy not in POLICIES: raise ValueError('Unknown stop policy')
    if friction is not None and not 0<=friction<1: raise ValueError('Invalid stop friction')
    if policy=='NO_STOP' or not observed: return None
    if not all(math.isfinite(v) and v>0 for v in [opening,previous_close]):
        raise ValueError('Invalid price')
    barrier=previous_close*(1-.055)
    if policy=='EOD_CLOSE': hit=math.isfinite(close) and close>0 and close<=barrier
    else: hit=opening<=barrier or (low_observed and math.isfinite(low) and low>0 and low<=barrier)
    if not hit:return None
    delay=int(policy in ('EOD_LOW','EOD_CLOSE'))
    if delay:
        if not next_observed:raise ValueError('Next Open is not observed; pending execution required')
        if not math.isfinite(next_open) or next_open<=0:raise ValueError('Invalid execution Open')
        raw=next_open
    else:raw=opening if opening<=barrier else barrier
    slip=friction if friction is not None else (0. if opening<=barrier else .001)
    return raw,raw*(1-slip),delay
