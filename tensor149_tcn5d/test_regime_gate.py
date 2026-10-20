"""Unit/falsification suite for causal RMT state extraction and matured-only gating."""
from __future__ import annotations
import unittest
import numpy as np
import pandas as pd
from tensor149_tcn5d.regime_features import weekly_regime_features,forward_hmm_probabilities,ALL
from tensor149_tcn5d.regime_gate_run import weight_formula,historical_mu,history_before

class DummyHMM:
    startprob_=np.array([.33,.34,.33])
    transmat_=np.array([[.91,.04,.05],[.03,.91,.06],[.06,.06,.88]])
    means_=np.array([[-.7,0.],[.2,1.],[1.,-1.]])
    covars_=np.array([[1.,.5],[.7,1.],[1.,.7]])

class CausalRegimeTests(unittest.TestCase):
    def test_markov_only_forward(self):
        r=np.random.default_rng(12)
        X=r.standard_normal((100,2))
        a=forward_hmm_probabilities(DummyHMM(),X)
        changed=X.copy();changed[59:]+=900.
        b=forward_hmm_probabilities(DummyHMM(),changed)
        np.testing.assert_allclose(a[:59],b[:59],atol=1e-12)
        self.assertTrue(np.all(np.isfinite(a)))
        np.testing.assert_allclose(a.sum(axis=1),1.,atol=1e-11)

    def test_market_feature_future_truncation(self):
        rng=np.random.default_rng(2026)
        dates=pd.bdate_range("2019-01-02",periods=430)
        names=["SPY"]+[f"ETF{i}" for i in range(148)]
        lr=rng.normal(0,.012,(430,149))+.002*np.sin(np.arange(430)[:,None]/40.)
        prices=pd.DataFrame(100*np.exp(np.cumsum(lr,axis=0)),index=dates,columns=names)
        a=weekly_regime_features(prices)
        b=weekly_regime_features(prices.iloc[:365])
        self.assertGreater(len(b),2)
        common=a[a.date.isin(b.date)].reset_index(drop=True)
        self.assertEqual(common.date.tolist(),b.date.tolist())
        np.testing.assert_allclose(common[list(ALL)],b[list(ALL)],rtol=1e-11,atol=1e-11)
        self.assertTrue((a.eligible_spectral_n==149).all())
        self.assertTrue(a.lambda1_share126.between(0,1).all())

    def test_matured_label_gate_and_weight(self):
        dates=pd.bdate_range("2020-01-01",periods=700)
        weeks=[dict(t_idx=i,exit_date=dates[i+6],ret_experts=np.array([.001,.003,-.01]))
               for i in range(0,645,5)]
        p=95
        older=history_before(weeks,p,dates)
        self.assertTrue(all(weeks[j]["exit_date"]<dates[weeks[p]["t_idx"]] for j in older))
        self.assertNotIn(p-1,older)
        self.assertIn(p-2,older)
        mu=historical_mu(weeks,older,p)
        weights=weight_formula(mu)
        self.assertEqual(weights.shape,(3,))
        self.assertAlmostEqual(weights.sum(),1.,places=12)
        self.assertTrue(np.all(weights>0))

    def test_reject_insufficient_history(self):
        weeks=[dict(ret_experts=np.array([.01,.0,-.01])) for _ in range(3)]
        with self.assertRaises(ValueError):
            historical_mu(weeks,[0,1,2],3)

if __name__=="__main__":unittest.main()
