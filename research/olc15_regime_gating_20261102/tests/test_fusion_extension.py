import pandas as pd,numpy as np
from run_fusion_gates import fusion_differential

def test_fused_label_is_not_native_label():
 f=pd.DataFrame({'ticker':['a','b','c'],'CUM_FIXED_MAPPED':[1,.8,.2],'CUM_FIT_MAPPED':[1,.8,.2],'CUM_FIXED_FUSION':[1,.8,.2],'CUM_FIT_FUSION':[.1,.8,.9],'fwd_ret_21':[.1,0,-.1],'fwd_ret_42':[.2,0,-.2],'fwd_ret_63':[.3,0,-.3],'exit_date_63':pd.to_datetime(['2021-05-01']*3)})
 r=fusion_differential(f);assert r['delta']<0;assert r['available']==pd.Timestamp('2021-05-01')
