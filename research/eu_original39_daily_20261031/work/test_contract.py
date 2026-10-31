import numpy as np
import pandas as pd
from research_common import training_mask, asof_external, score_blend, select_pair

def test_future_labels_excluded():
 f=pd.DataFrame({'signal_date':pd.to_datetime(['2023-11-30','2023-12-29','2024-01-31']), 'exit_date_21':pd.to_datetime(['2023-12-29','2024-01-30','2024-03-01']),'fwd_ret_21':[.1,.2,.3]})
 assert training_mask(f,2024).tolist()==[True,False,False]

def test_us_same_date_close_not_known_at_eu_prior_close():
 s=pd.Series([1.,10.,100.],index=pd.to_datetime(['2024-01-01','2024-01-02','2024-01-03']))
 out=asof_external(s,pd.to_datetime(['2024-01-02','2024-01-03']))
 assert out.tolist()==[1.,10.]

def test_missing_forecast_not_selected():
 assert select_pair(np.array([.9,np.nan,.8,-np.inf]))==[0,2]

def test_blend_preserves_exact_original_smoothing():
 b=np.full((3,2),.6);et=np.array([[.1,.8],[.2,.7],[.3,.6]]);x=et.copy()
 exp=.475*b+.525*(.4*et+.3*np.vstack([et[:1],et[:-1]])+.3*np.vstack([et[:1],et[:1],et[:-2]]))**1.1
 np.testing.assert_array_equal(score_blend(b,et,x),exp)
