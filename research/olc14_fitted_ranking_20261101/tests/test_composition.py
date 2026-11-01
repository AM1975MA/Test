import numpy as np
from build_scores import compose_current
from layer_metrics import compose

def test_unmodified_memory_and_fusion_are_exact():
 rng=np.random.default_rng(13);r=rng.random((7,6));e=rng.random((7,6));x=rng.random((7,6))
 e[2,1]=np.nan;x[4,2]=np.nan
 current,smooth,final=compose(r,e,x)
 s,f=compose_current(r,current)
 np.testing.assert_array_equal(s,smooth)
 np.testing.assert_array_equal(f,final)

def test_composition_does_not_rewrite_past_when_future_changes():
 rng=np.random.default_rng(13);r=rng.random((7,6));c=rng.random((7,6));a=compose_current(r,c)
 c[4:]=1;r[4:]=0;b=compose_current(r,c)
 np.testing.assert_array_equal(a[1][:4],b[1][:4])
