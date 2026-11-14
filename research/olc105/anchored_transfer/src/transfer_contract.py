"""Hard constraints for the approved anchored portability study."""
import numpy as np
import pandas as pd
CASH={'EUR_CASH_A','EUR_CASH_B'}
def select_pair(frame,allowed):
    f=frame[frame.ticker.isin(allowed)&np.isfinite(frame.score)].sort_values(['score','ticker'],ascending=[False,True])
    if len(f)<2: raise ValueError('Fewer than two valid investable candidates')
    return tuple(f.ticker.iloc[:2])
def require_asof(signal,opening):
    if not pd.Timestamp(signal)<pd.Timestamp(opening):raise ValueError('Signal not available strictly before opening')
def require_allowed(names,allowed):
    illegal=set(names)-set(allowed)-CASH
    if illegal:raise ValueError(f'Anchor or unknown holdings: {sorted(illegal)}')
def completed_month_cutoff(asof):
    return (pd.Timestamp(asof).to_period('M')-1).end_time.normalize()
