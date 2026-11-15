import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import horizon_selectors as hs
import cluster_selectors as cs
from test_cluster_selectors import fixture

def prepared():
    p,l,t=fixture();f=cs.prepare_features(p,l,t)
    for key in ('m63','m126','m252'):f[key][300]=[1.,.9,.8,.7,.6,.5]
    f['m126'][300]=[.6,.5,1.,.9,.8,.7]
    f['m63'][300]=[.8,.7,.6,.5,1.,.9]
    f['sma200'][300]=f['C'][300]*.5
    return p,f,{300:cs.build_snapshot(p,f,300)}

class HorizonTests(unittest.TestCase):
    def test_top1_keeps_full_concentration_on_highest_individual(self):
        p,f,s=prepared()
        w,m=hs.make_policy(p,f,s,'HORIZON252_TOP1')(300,np.zeros(6))
        np.testing.assert_array_equal(w,[1.,0.,0.,0.,0.,0.])
        self.assertEqual(len(m['selected_indices']),1)

    def test_capital_mix_is_exact_convex_sum_of_targets(self):
        p,f,s=prepared()
        baskets=[hs.make_policy(p,f,s,'HORIZON'+str(h))(300,np.zeros(6))[0] for h in (63,126,252)]
        w,m=hs.make_policy(p,f,s,'CAPITAL_3H')(300,np.zeros(6))
        np.testing.assert_allclose(w,sum(baskets)/3,rtol=0,atol=1e-15)
        for g in s[300]['groups']:self.assertLessEqual(w[g['members']].sum(),1/3+1e-12)

    def test_tilt_preserves_holdings_gross_and_group_caps(self):
        p,f,s=prepared()
        f['b21'][300]=[.01,.01,.02,.03,.30,.30];f['a21'][300]=0.
        base,_=hs.make_policy(p,f,s,'CAPITAL_3H')(300,np.zeros(6))
        w,m=hs.make_policy(p,f,s,'CAPITAL_3H_TILT')(300,np.zeros(6))
        np.testing.assert_array_equal(w>0,base>0)
        self.assertAlmostEqual(w.sum(),base.sum())
        self.assertEqual(sorted(m['sleeve_weights']),[.25,.25,.5])
        for g in s[300]['groups']:self.assertLessEqual(w[g['members']].sum(),1/3+1e-12)

    def test_no_trend_is_cash_for_all_arms(self):
        p,f,s=prepared();f['m63'][300]=-1.
        for arm in hs.ARMS:
            w,_=hs.make_policy(p,f,s,arm)(300,np.zeros(6))
            self.assertEqual(w.sum(),0.,arm)

    def test_incomplete_sleeves_keep_equal_capital(self):
        p,f,s=prepared();f['liquid_eligible'][300,2:]=False
        w,m=hs.make_policy(p,f,s,'CAPITAL_3H_TILT')(300,np.zeros(6))
        np.testing.assert_allclose(m['sleeve_weights'],[1/3]*3)
        self.assertAlmostEqual(w.sum(),1/3)

if __name__=='__main__':unittest.main()
