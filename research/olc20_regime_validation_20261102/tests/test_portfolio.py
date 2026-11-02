import numpy as np
from paths import P18
from portfolio_validation import prepare_state

def test_authentic_current_targets_and_v6_equal_parent():
    for m in ('EU','USA'):
        q,events,dec=prepare_state(m,'AUTH')
        old=dict(np.load(P18/f'inputs/{m}_TOP2_CONTEXT_REVALUE.npz',allow_pickle=False))
        for k in ('d1','d2','weights','alt','O','C','L','PC'):
            np.testing.assert_array_equal(q[k],old[k])
        np.testing.assert_array_equal(events,old['events'])

def test_static_targets_and_v6_equal_parent():
    for m in ('EU','USA'):
        q,events,dec=prepare_state(m,'STATIC')
        old=dict(np.load(P18/f'inputs/{m}_TOP2_STATIC_REVALUE.npz',allow_pickle=False))
        for k in ('d1','d2','alt'):np.testing.assert_array_equal(q[k],old[k])
        assert not np.any((q['alt']>=0)&((q['alt']==q['d1'])|(q['alt']==q['d2'])))
        assert (dec.signal_date<dec.entry_date).all()
