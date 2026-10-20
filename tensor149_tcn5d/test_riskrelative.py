"""Risk target tests: leakage, as-of sigma/beta, deterministic cross-sectional
distributions, nontrivial control parity and differentiability.
"""
from __future__ import annotations
import unittest
import numpy as np
import torch
from tensor149_tcn5d.features import FIELDS
from tensor149_tcn5d.risk_targets import (
    RISK_VARIANTS,CONTROL_VARIANTS,asof_risk,maturity_targets,
    risk_distribution_loss,oracle_risk_overlap
)

class RiskRelativeTests(unittest.TestCase):
    def make_data(self):
        rng=np.random.default_rng(42);T=90;N=20
        x=np.zeros((T,N,len(FIELDS)),dtype=np.float32)
        x[:,:,FIELDS.index("vol63")]=np.linspace(.12,.6,N)[None,:]
        x[:,:,FIELDS.index("beta_mkt63")]=np.linspace(.3,1.8,N)[None,:]
        x[:,:,FIELDS.index("mom21")]=rng.normal(0,.05,(T,N))
        available=np.ones((T,N),dtype=bool)
        ret=rng.normal(.005,.02,(T,N)).astype(np.float32)
        return x,available,ret

    def test_asof_sigma_beta_and_control(self):
        x,available,_=self.make_data()
        sigma,beta,control,audit=asof_risk(x,available,0)
        self.assertAlmostEqual(float(sigma[15,3]),max(float(x[15,3,FIELDS.index("vol63")])*np.sqrt(5/252),.01),places=6)
        self.assertAlmostEqual(float(beta[16,5]),float(x[16,5,FIELDS.index("beta_mkt63")]),places=6)
        self.assertEqual(audit["annual_vol_missing_on_eligible"],0)
        self.assertEqual(audit["beta_missing_on_eligible"],0)
        self.assertSetEqual(set(control),set(CONTROL_VARIANTS))
        # Altering future feature cells must not modify past as-of volatility/beta or risk controls.
        old={k:v[20].copy() for k,v in control.items()}
        xp=x.copy();xp[21:]=9e5
        sig2,b2,contr2,_=asof_risk(xp,available,0)
        self.assertTrue(np.array_equal(sig2[:21],sigma[:21]))
        self.assertTrue(np.array_equal(b2[:21],beta[:21]))
        for k in old:self.assertTrue(np.array_equal(contr2[k][20],old[k]))

    def test_future_market_used_only_for_training_label(self):
        x,available,ret=self.make_data()
        sigma,beta,controls,_=asof_risk(x,available,0)
        risk,_=maturity_targets(ret,available,sigma,beta,0)
        self.assertSetEqual(set(risk),set(RISK_VARIANTS))
        for v in risk.values():self.assertTrue(np.isfinite(v).all())
        # The SPY future return *changes the future target*, but NEVER controls.
        future_ret=ret.copy()
        future_ret[40,0]+=0.04
        new,_=maturity_targets(future_ret,available,sigma,beta,0)
        self.assertTrue(np.array_equal(new["BETA_VOL_RESID_DIST"][:40],risk["BETA_VOL_RESID_DIST"][:40]))
        self.assertFalse(np.array_equal(new["BETA_VOL_RESID_DIST"][40],risk["BETA_VOL_RESID_DIST"][40]))
        # In the plain raw cross section, subtracting a common SPY return does not alter order.
        for t in (20,40,60):
            assert np.all(np.argsort(risk["RAW_EXCESS_DIST"][t])==np.argsort(ret[t]))

    def test_softmax_group_gradient_permutation(self):
        torch.manual_seed(23)
        n=149
        targets=torch.linspace(-1.2,1.1,n)
        s=torch.randn(n)*.15
        p=torch.randperm(n)
        a=s.detach().clone().requires_grad_(True)
        loss=risk_distribution_loss(a,targets)
        loss.backward()
        self.assertTrue(bool(torch.isfinite(a.grad).all()))
        self.assertGreater(float(a.grad.norm()),1e-4)
        self.assertAlmostEqual(float(loss.detach()),float(risk_distribution_loss(s[p],targets[p])),places=5)

    def test_new_oracle_is_distinct_from_raw_top5(self):
        pred=np.arange(20,dtype=np.float32)
        tgt=-np.arange(20,dtype=np.float32)
        self.assertEqual(oracle_risk_overlap(pred,np.arange(20),tgt),0.)
        self.assertEqual(oracle_risk_overlap(pred,np.arange(20),pred),1.)

if __name__=="__main__":unittest.main()
