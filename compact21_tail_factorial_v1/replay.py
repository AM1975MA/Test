"""Experimental call of the original portfolio executor, with optional MA3 bypass."""
import numpy as np
from .score import titanium_score
def replay(compare,state,hybrid):
    original_score=compare.stage19.score_matrix
    original_weight=compare.stage19.confidence_weights
    try:
        if not hybrid:
            compare.stage19.score_matrix=lambda p,cal,tickers: titanium_score(p,cal.signal_date,tickers)
            def weights(a,g,agree,all_agree,mode):
                return original_weight(a,g,np.zeros_like(agree,dtype=bool),all_agree,mode)
            compare.stage19.confidence_weights=weights
        return compare.replay_full_universe(state)
    finally:
        compare.stage19.score_matrix=original_score
        compare.stage19.confidence_weights=original_weight
