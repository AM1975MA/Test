import pandas as pd, numpy as np
from corporate_actions import forward_units

def test_known_split_preserves_economic_value_and_turnover():
    f=pd.DataFrame({'Open':[1000.,10.1],'High':[1001.,10.2],'Low':[990.,10.], 'Close':[1000.,10.1],'Volume':[10.,1000.]},index=pd.to_datetime(['2025-12-12','2025-12-15']))
    g=forward_units(f,'2025-12-15',100.)
    assert g.iloc[0].equals(f.iloc[0])
    assert np.isclose(g.Close.iloc[1]/g.Close.iloc[0]-1,.01)
    assert np.isclose(g.Close.iloc[1]*g.Volume.iloc[1],f.Close.iloc[1]*f.Volume.iloc[1])
    assert f.Close.iloc[1]==10.1

def test_pre_split_prefix_not_affected_by_future_action():
    f=pd.DataFrame({'Open':[1000.], 'High':[1001.],'Low':[990.],'Close':[1000.],'Volume':[10.]},index=pd.to_datetime(['2025-12-12']))
    pd.testing.assert_frame_equal(forward_units(f,'2025-12-15',100.),f)
