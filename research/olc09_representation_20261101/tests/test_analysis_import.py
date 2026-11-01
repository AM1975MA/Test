import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pytest

def test_analysis_uses_intended_evidence_helper():
    try:
        import analyze_results as a
    except ImportError as e:
        pytest.fail('Analysis dependency must resolve the feature-lab helper: '+str(e))
    assert a.daily_log.__module__=='_olc09_parent_evidence'
    np.testing.assert_allclose(a.daily_log([1.1,1.21,1.21]),[np.log(1.1),np.log(1.1),0],atol=1e-15)
    w=a.circular_weights(5,2,12,17)
    np.testing.assert_allclose(w.sum(axis=1),1.)
