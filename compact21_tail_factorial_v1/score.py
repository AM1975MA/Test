"""Diagnostic transform; used only in isolated research."""
import numpy as np
def titanium_score(panel,dates,tickers):
    p=panel.pivot(index="signal_date",columns="ticker",values="BASE")
    return p.reindex(index=dates,columns=tickers).to_numpy(float)
