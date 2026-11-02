from pathlib import Path
import numpy as np
from v6_rebuild import rebuild
R=Path(__file__).resolve().parents[1]

def test_context_is_non_pickle_and_excludes_infrastructure():
 d=dict(np.load(R/'inputs/EU_V6_CONTEXT.npz',allow_pickle=False))
 assert all(v.dtype.kind!='O' for v in d.values())
 assert not d['allowed'][:,-3:].any()
 assert (d['SPY_source_date']<d['dates']).all()

def test_exact_v6_parent_streams():
 from run_v6_validation import v6_inputs
 for m in ['EU','USA']:
  q=dict(np.load(R/f'parent/olc16_contextual_rank_20261102/inputs/{m}_STATE_HALF.npz'))
  v,allowed=v6_inputs(q,m)
  np.testing.assert_array_equal(rebuild(v,allowed=allowed),q['alt'])
